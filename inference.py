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
  - Live webcam demo  (run: python inference.py)

Plug in YOLO here — tile_predict() is the only function that calls YOLO.
"""
import base64
import time
import urllib.request
import json as _json
import numpy as np
import cv2
from ultralytics import YOLO

from config import (
    YOLO_MODEL, CONF, TILE_GRID, TILE_OVERLAP, NMS_IOU,
    HEATMAP_GRID, HEATMAP_W, HEATMAP_H,
    NORMAL_MAX, BUSY_MAX, MODEL_SERVER_URL,
)

# ── Load tiling model (used by API inference loop) ────────────────
print("[inference] Loading YOLOv11x …")
yolo_model = YOLO(YOLO_MODEL)
print("[inference] YOLO ready.")

# ── Live demo model (yolov8n — lightweight, no tiling, real-time) ─
LIVE_YOLO_MODEL = "yolov8n.pt"
_live_yolo: YOLO | None = None     # loaded lazily only when demo runs

def _get_live_yolo() -> YOLO:
    global _live_yolo
    if _live_yolo is None:
        print(f"[inference] Loading {LIVE_YOLO_MODEL} for live demo …")
        _live_yolo = YOLO(LIVE_YOLO_MODEL)
        print("[inference] Live YOLO ready.")
    return _live_yolo


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
def _run_yolo_on_tiles(frame: np.ndarray, grid: int) -> tuple[list, list]:
    """Run YOLO on a frame split into grid×grid tiles. Returns (boxes, scores)."""
    h, w   = frame.shape[:2]
    th, tw = h // grid, w // grid
    ph, pw = int(th * TILE_OVERLAP), int(tw * TILE_OVERLAP)
    all_boxes, all_scores = [], []
    for row in range(grid):
        for col in range(grid):
            y1 = max(0, row * th - ph);  y2 = min(h, (row + 1) * th + ph)
            x1 = max(0, col * tw - pw);  x2 = min(w, (col + 1) * tw + pw)
            tile = frame[y1:y2, x1:x2]
            results = yolo_model.predict(
                source=tile, conf=CONF, verbose=False, classes=[0],
                imgsz=640, iou=0.4, agnostic_nms=True,
            )
            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                all_boxes.append([bx1 + x1, by1 + y1, bx2 + x1, by2 + y1])
                all_scores.append(float(box.conf[0]))
    return all_boxes, all_scores


# close-up threshold: if any detected box covers >8% of the frame area → person is near
_CLOSE_UP_RATIO = 0.08


def _filter_person_boxes(boxes: list, frame_w: int, frame_h: int) -> list:
    """
    Remove boxes that clearly aren't people:
      - Must have minimum height (>= 5% of frame height) — removes tiny noise
      - Width must not be more than 2.5x the height — removes very wide horizontal objects
      - Must not be entirely in the top 10% of frame — removes ceiling/clock artifacts
    """
    out = []
    min_h = frame_h * 0.05
    for x1, y1, x2, y2 in boxes:
        bw = x2 - x1
        bh = y2 - y1
        if bh < min_h:
            continue                        # too small — noise
        if bw > 0 and bh / bw < 0.4:
            continue                        # extremely wide — definitely not a person
        if y2 < frame_h * 0.10:
            continue                        # entirely in top 10% — ceiling artifact
        out.append([x1, y1, x2, y2])
    return out


def tile_predict(frame: np.ndarray) -> list[list[float]]:
    """
    Adaptive tiling:
      1. Run a fast single-pass (no tiling) first.
      2. If detected boxes are large (person is close) → return result as-is.
      3. If boxes are small or none (person is far) → re-run with 2×2 tiling
         so small/distant people are detected accurately.
    """
    h, w       = frame.shape[:2]
    frame_area = h * w

    # Step 1 — single pass (fast)
    boxes_1, scores_1 = _run_yolo_on_tiles(frame, grid=1)

    # Step 2 — check if any box is large (close-up person)
    if boxes_1:
        avg_area = np.mean(
            [(x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in boxes_1]
        ) / frame_area
        if avg_area >= _CLOSE_UP_RATIO:
            keep = _nms(np.array(boxes_1), np.array(scores_1), NMS_IOU)
            return _filter_person_boxes([boxes_1[i] for i in keep], w, h)

    # Step 3 — person is far or not detected in single pass → use 2×2 tiling
    boxes_2, scores_2 = _run_yolo_on_tiles(frame, grid=2)
    all_boxes  = boxes_1  + boxes_2
    all_scores = scores_1 + scores_2
    if not all_boxes:
        return []
    keep = _nms(np.array(all_boxes), np.array(all_scores), NMS_IOU)
    return _filter_person_boxes([all_boxes[i] for i in keep], w, h)


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
        # small label above each box
        cv2.putText(out, "person", (int(x1), max(int(y1) - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_color, 1, cv2.LINE_AA)
    return out


# ─────────────────────────────────────────────────────────────────
# Live demo  —  fast single-frame detection (no tiling)
# ─────────────────────────────────────────────────────────────────
def detect_live(frame: np.ndarray) -> dict:
    """
    Run yolov8n on a single full frame (no tiling — fast enough for real-time).
    Returns structured output ready for display and model server.

    Output:
        {
            "people_count": int,
            "density":      float,
            "boxes":        [[x1,y1,x2,y2], ...],
        }
    """
    model   = _get_live_yolo()
    results = model.predict(source=frame, conf=CONF, verbose=False, classes=[0])
    boxes_raw = results[0].boxes
    boxes = []
    if boxes_raw is not None and len(boxes_raw):
        boxes = [b.xyxy[0].tolist() for b in boxes_raw]
    count   = len(boxes)
    density = density_from_count(count)
    return {"people_count": count, "density": density, "boxes": boxes}



def _risk_label(count: int) -> str:
    if count > BUSY_MAX:   return "Critical"
    if count > NORMAL_MAX: return "Busy"
    return "Normal"


def run_live_demo(webcam_index: int = 0) -> None:
    """
    Open webcam, run real-time YOLO detection, and display annotated feed.

    Overlays:
      - Green/orange/red bounding boxes (colour = risk level)
      - HUD: People count  |  Density  |  Risk level
      - FPS counter

    Press  Q  or  ESC  to quit.
    """
    from camera import live_webcam_frames   # import here to avoid circular at module level

    RISK_COLOR = {"Critical": (0, 0, 220), "Busy": (0, 165, 255), "Normal": (0, 200, 80)}

    print("\n[demo] Starting live crowd detection — press Q or ESC to quit\n")
    _get_live_yolo()   # warm up before first frame

    fps_t   = time.perf_counter()
    fps_val = 0.0
    frames  = 0
    api_state: dict = {}   # authoritative numbers from the API (same source as dashboard)

    def _fetch_api_state():
        """Pull latest metrics from the running API — same numbers the dashboard shows."""
        try:
            with urllib.request.urlopen(
                f"{MODEL_SERVER_URL.replace('8001', '8000')}/api/v1/metrics/latest",
                timeout=1
            ) as r:
                return _json.loads(r.read())
        except Exception:
            return {}

    for frame in live_webcam_frames(webcam_index):
        # Fast local detection — used only for bounding boxes (visual)
        det   = detect_live(frame)
        boxes = det["boxes"]

        # Sync with API every 3 frames so HUD matches the dashboard exactly
        if frames % 3 == 0:
            fresh = _fetch_api_state()
            if fresh:
                api_state = fresh

        # HUD numbers come from API state (same as dashboard) with local fallback
        count    = api_state.get("peoplePred",      det["people_count"])
        density  = api_state.get("avgDensity",      det["density"])
        risk     = api_state.get("riskLevel",        _risk_label(det["people_count"]))
        forecast = api_state.get("predDensity15",   round(min(9.0, density + 0.3), 1))

        # ── Draw bounding boxes (colour = risk) ──────────────────
        box_color = RISK_COLOR.get(risk, (0, 255, 80))
        out = frame.copy()
        for x1, y1, x2, y2 in boxes:
            cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), box_color, 2)

        # ── HUD overlay ─────────────────────────────────────────
        h, w = out.shape[:2]
        cv2.rectangle(out, (0, 0), (w, 56), (10, 16, 36), -1)

        cv2.putText(out, f"People: {count}",
                    (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(out, f"Density: {density:.1f}",
                    (180, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 220, 255), 2, cv2.LINE_AA)

        risk_color_text = {
            "Critical": (80, 80, 255), "Busy": (80, 180, 255), "Normal": (80, 230, 120)
        }.get(risk, (255, 255, 255))
        cv2.putText(out, f"Risk: {risk.upper()}",
                    (360, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, risk_color_text, 2, cv2.LINE_AA)
        cv2.putText(out, f"15-min forecast: {forecast:.1f}  |  FPS: {fps_val:.1f}  |  synced w/ dashboard",
                    (12, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 180, 140), 1, cv2.LINE_AA)

        # ── Risk badge (bottom-right) ────────────────────────────
        badge_bg = {"Critical": (0, 0, 180), "Busy": (0, 120, 200), "Normal": (0, 150, 50)}
        bx, by = w - 140, h - 40
        cv2.rectangle(out, (bx, by), (w - 8, h - 8), badge_bg.get(risk, (60, 60, 60)), -1)
        cv2.putText(out, risk.upper(), (bx + 8, h - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        # ── FPS ─────────────────────────────────────────────────
        frames += 1
        if frames % 10 == 0:
            fps_val = 10.0 / (time.perf_counter() - fps_t)
            fps_t   = time.perf_counter()

        cv2.imshow("Live Crowd Detection  |  Q to quit", out)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
            break

    cv2.destroyAllWindows()
    print("[demo] Stopped.")


# ─────────────────────────────────────────────────────────────────
# Entry point:  python inference.py
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_live_demo(webcam_index=0)
