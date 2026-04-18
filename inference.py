"""
inference.py — YOLO inference pipeline.

Responsibilities:
  - Load YOLOv11x once at startup
  - 3×3 tiled detection (detects small/distant people)
  - Cross-tile NMS deduplication
  - Spatial feature extraction (cx_std, cy_std, avg_box_area)
  - Heatmap generation (OpenCV COLORMAP_JET → base64 JPEG)
  - Annotated frame generation (bounding boxes + count overlay)
  - density_from_count helper

Plug in YOLO here — tile_predict() is the only function that calls YOLO.
"""
import base64
import numpy as np
import cv2
from ultralytics import YOLO

from config import (
    YOLO_MODEL, CONF, TILE_GRID, TILE_OVERLAP, NMS_IOU,
    HEATMAP_GRID, HEATMAP_W, HEATMAP_H,
)

# ── Load model once ───────────────────────────────────────────────
print("[inference] Loading YOLOv11x …")
yolo_model = YOLO(YOLO_MODEL)
print("[inference] YOLO ready.")


# ─────────────────────────────────────────────────────────────────
# Non-Maximum Suppression  (deduplicates boxes across tile borders)
# ─────────────────────────────────────────────────────────────────
def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas  = (x2 - x1) * (y2 - y1)
    order  = scores.argsort()[::-1]
    keep   = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1   = np.maximum(x1[i], x1[order[1:]])
        yy1   = np.maximum(y1[i], y1[order[1:]])
        xx2   = np.minimum(x2[i], x2[order[1:]])
        yy2   = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou   = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[np.where(iou <= iou_thr)[0] + 1]
    return keep


# ─────────────────────────────────────────────────────────────────
# YOLO  —  plug-in point
# ─────────────────────────────────────────────────────────────────
def tile_predict(frame: np.ndarray) -> list[list[float]]:
    """
    Split frame into TILE_GRID×TILE_GRID overlapping tiles.
    Run YOLOv11x on each tile, map boxes back to frame coordinates,
    deduplicate with NMS.

    Returns: list of [x1, y1, x2, y2] in original frame pixel coords.

    To swap YOLO version: replace `yolo_model.predict(...)` below.
    """
    h, w   = frame.shape[:2]
    th, tw = h // TILE_GRID, w // TILE_GRID
    ph, pw = int(th * TILE_OVERLAP), int(tw * TILE_OVERLAP)

    all_boxes, all_scores = [], []

    for row in range(TILE_GRID):
        for col in range(TILE_GRID):
            y1 = max(0, row * th - ph);  y2 = min(h, (row + 1) * th + ph)
            x1 = max(0, col * tw - pw);  x2 = min(w, (col + 1) * tw + pw)
            tile    = frame[y1:y2, x1:x2]

            # ── YOLO inference (swap model here if needed) ──
            results = yolo_model.predict(
                source=tile, conf=CONF, verbose=False, classes=[0]   # classes=[0] = person only
            )
            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                # remap to original frame coordinates
                all_boxes.append([bx1 + x1, by1 + y1, bx2 + x1, by2 + y1])
                all_scores.append(float(box.conf[0]))

    if not all_boxes:
        return []
    keep = _nms(np.array(all_boxes), np.array(all_scores), NMS_IOU)
    return [all_boxes[i] for i in keep]


# ─────────────────────────────────────────────────────────────────
# Feature extraction  (feeds LightGBM + TensorFlow)
# ─────────────────────────────────────────────────────────────────
def extract_features(boxes: list[list[float]], frame_w: int, frame_h: int) -> dict:
    """
    Compute spatial features from detected bounding boxes.
    These features are sent to model_server.py (LightGBM + TF).
    """
    count = len(boxes)
    if not boxes:
        return {
            "count": 0, "centres": [],
            "cx_std": 0.0, "cy_std": 0.0, "avg_box_area": 0.0,
        }
    centres      = [(0.5 * (x1 + x2), 0.5 * (y1 + y2)) for x1, y1, x2, y2 in boxes]
    frame_area   = max(1, frame_w * frame_h)
    return {
        "count":        count,
        "centres":      centres,
        "cx_std":       float(np.std([c[0] for c in centres])),
        "cy_std":       float(np.std([c[1] for c in centres])),
        "avg_box_area": float(np.mean([(x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in boxes])) / frame_area,
    }


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────
def density_from_count(count: int) -> float:
    """Convert person count to crowd density (people/m²-equivalent, capped at 7.5)."""
    return round(min(7.5, count / 12.0), 1)


def build_heatmap(centres: list, frame_w: int = HEATMAP_W, frame_h: int = HEATMAP_H) -> str:
    """
    Build a COLORMAP_JET heatmap from person centre coordinates.
    Returns base64-encoded JPEG string for the /api/v1/heatmap endpoint.
    """
    heat = np.zeros((HEATMAP_GRID, HEATMAP_GRID), dtype=np.float32)
    for cx, cy in centres:
        col = min(HEATMAP_GRID - 1, int(cx / frame_w * HEATMAP_GRID))
        row = min(HEATMAP_GRID - 1, int(cy / frame_h * HEATMAP_GRID))
        heat[row, col] += 1.0
    if heat.max() > 0:
        heat = heat / heat.max()
    heat_u8  = (heat * 255).astype(np.uint8)
    heat_big = cv2.resize(heat_u8, (HEATMAP_W, HEATMAP_H), interpolation=cv2.INTER_LINEAR)
    coloured = cv2.applyColorMap(heat_big, cv2.COLORMAP_JET)
    _, buf   = cv2.imencode(".jpg", coloured)
    return base64.b64encode(buf).decode("utf-8")


def annotate_frame(frame: np.ndarray, boxes: list[list[float]],
                   count: int, risk: str = "") -> np.ndarray:
    """
    Draw bounding boxes and HUD overlay on a copy of the frame.
    Returns annotated np.ndarray — encode to JPEG for /api/v1/stream/frame.
    """
    RISK_COLOR = {"Critical": (0, 0, 220), "Busy": (0, 165, 255), "Normal": (0, 200, 80)}
    box_color  = RISK_COLOR.get(risk, (0, 255, 80))

    out = frame.copy()
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), box_color, 2)

    # HUD banner
    h, w = out.shape[:2]
    cv2.rectangle(out, (0, 0), (w, 44), (10, 18, 40), -1)
    cv2.putText(out,
                f"People: {count}  |  Risk: {risk or 'N/A'}  |  YOLOv11x 3x3 Tiling",
                (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return out
