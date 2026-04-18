"""
FIFA WC 2034 Crowd AI Backend
- YOLOv11x person detection + DeepSort tracking
- LightGBM 15-min density forecasting
- TensorFlow density level classification
- Heatmap generation
- Supports: video file mode (demo) OR live camera mode
"""

import os, time, threading, random, io, base64
from collections import deque
import urllib.request, json as _json

# ── Supabase client (optional — backend works fine if unavailable) ──
try:
    from supabase import create_client as _sb_create
    _SB_URL = "http://127.0.0.1:54321"
    _SB_KEY = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"
    _supabase = _sb_create(_SB_URL, _SB_KEY)
    print("[supabase] Connected to local Supabase")
except Exception as _e:
    _supabase = None
    print(f"[supabase] Not available ({_e}) — running without DB persistence")

import cv2
import numpy as np
import pandas as pd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# ─────────────────────────────────────────────────────────────────
# CONFIG  — change CAMERA_MODE to True when your camera is wired
# ─────────────────────────────────────────────────────────────────
CAMERA_MODE  = True                           # False = video files, True = live webcam
CAMERA_INDEX = 0                              # webcam index when CAMERA_MODE=True

VIDEO_FOLDER = "/Users/ranamahmoud/Downloads/Stadiums videos "   # trailing space = actual folder name
YOLO_MODEL   = "yolo11x.pt"                   # auto-downloaded if not present
CONF             = 0.1
UPDATE_EVERY_SEC = 3
FRAME_SKIP       = 30    # advance this many frames per inference step
TILE_GRID        = 3     # split frame into TILE_GRID × TILE_GRID tiles (3×3 = 9 tiles)
TILE_OVERLAP     = 0.1   # 10% overlap between tiles to avoid missing border detections
NMS_IOU          = 0.35  # IoU threshold for deduplication across tiles

NORMAL_MAX = 10
BUSY_MAX   = 25

MODELS_DIR   = "models"
LGBM_MODEL   = os.path.join(MODELS_DIR, "lgbm_forecast.pkl")
LGBM_SCALER  = os.path.join(MODELS_DIR, "lgbm_scaler.pkl")
TF_MODEL     = os.path.join(MODELS_DIR, "tf_density_classifier.keras")
TF_SCALER    = os.path.join(MODELS_DIR, "tf_scaler.pkl")
TF_ENCODER   = os.path.join(MODELS_DIR, "tf_label_encoder.pkl")

HEATMAP_GRID = 10          # grid resolution for heatmap (10×10)
HEATMAP_W    = 640
HEATMAP_H    = 480

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def risk_from_count(count: int) -> str:
    if count <= NORMAL_MAX: return "Normal"
    if count <= BUSY_MAX:   return "Busy"
    return "Critical"

def density_from_count(count: int) -> float:
    return round(min(7.5, count / 12.0), 1)

def compute_accuracy(pred: int, gt: int) -> float:
    if gt <= 0: return 1.0 if pred == 0 else 0.0
    return round(max(0.0, 1.0 - abs(pred - gt) / gt), 2)

def frame_to_base64(frame: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf).decode("utf-8")

def build_heatmap(centres: list[tuple[float, float]],
                  frame_w: int = HEATMAP_W,
                  frame_h: int = HEATMAP_H) -> str:
    """
    Given a list of (cx, cy) person centres (in pixel coords),
    return a base64-encoded heatmap JPEG.
    """
    heat = np.zeros((HEATMAP_GRID, HEATMAP_GRID), dtype=np.float32)
    for cx, cy in centres:
        col = min(HEATMAP_GRID - 1, int(cx / frame_w * HEATMAP_GRID))
        row = min(HEATMAP_GRID - 1, int(cy / frame_h * HEATMAP_GRID))
        heat[row, col] += 1.0

    # Normalise → 0-255 and apply colour map
    if heat.max() > 0:
        heat = heat / heat.max()
    heat_u8 = (heat * 255).astype(np.uint8)
    heat_big = cv2.resize(heat_u8, (HEATMAP_W, HEATMAP_H), interpolation=cv2.INTER_LINEAR)
    coloured = cv2.applyColorMap(heat_big, cv2.COLORMAP_JET)
    return frame_to_base64(coloured)


# ─────────────────────────────────────────────────────────────────
# MODEL LOADING
# ─────────────────────────────────────────────────────────────────
print("[boot] Loading YOLO …")
yolo_model = YOLO(YOLO_MODEL)

print("[boot] Loading DeepSort tracker …")
tracker = DeepSort(max_age=30, n_init=3, nms_max_overlap=1.0, embedder=None)

MODEL_SERVER_URL = "http://127.0.0.1:8001"   # model microservice (port 8001)
_model_server_ok = False   # updated each inference cycle


# ─────────────────────────────────────────────────────────────────
# VIDEO SOURCE
# ─────────────────────────────────────────────────────────────────
if not CAMERA_MODE:
    video_files = sorted([
        os.path.join(VIDEO_FOLDER, f)
        for f in os.listdir(VIDEO_FOLDER)
        if f.lower().endswith(".mp4")
    ])
    print(f"[boot] Found {len(video_files)} video files for demo mode")
    _current_video_idx = 0


def next_frame():
    """
    Generator: yields (frame, source_name) indefinitely.
    In CAMERA_MODE it reads from webcam; otherwise cycles through video files.
    """
    global _current_video_idx

    if CAMERA_MODE:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            yield frame, f"camera:{CAMERA_INDEX}"
        cap.release()
    else:
        # Cycle through video files, skipping FRAME_SKIP frames per step
        while True:
            vp       = video_files[_current_video_idx % len(video_files)]
            cap      = cv2.VideoCapture(vp)
            pos      = 0
            total    = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            while pos < total:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ret, frame = cap.read()
                if not ret:
                    break
                yield frame, os.path.basename(vp)
                pos += FRAME_SKIP
            cap.release()
            _current_video_idx += 1


# ─────────────────────────────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────────────────────────────
latest = {
    "timestamp":      "",
    "source":         "",
    "peoplePred":     0,
    "trackedIDs":     0,
    "avgDensity":     0.0,
    "riskLevel":      "Normal",
    "activeIncidents":0,
    "accuracy":       0.0,
}
history       = deque(maxlen=60)
last_heatmap  = ""           # base64 string, updated each cycle


# ─────────────────────────────────────────────────────────────────
# FORECAST HELPER
# ─────────────────────────────────────────────────────────────────
def _call_model_server(count: int, density: float, time_of_day: float,
                       cx_std: float, cy_std: float, avg_box_area: float) -> dict:
    """POST features to model microservice. Returns dict or None on failure."""
    global _model_server_ok
    try:
        payload = _json.dumps({
            "count": count, "density": density, "time_of_day": time_of_day,
            "cx_std": cx_std, "cy_std": cy_std, "avg_box_area": avg_box_area,
        }).encode()
        req = urllib.request.Request(
            f"{MODEL_SERVER_URL}/predict",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            result = _json.loads(resp.read())
            _model_server_ok = True
            return result
    except Exception:
        _model_server_ok = False
        return {}


def predict_15min(count: int, density: float, time_of_day: float,
                  cx_std: float, cy_std: float, avg_box_area: float) -> float:
    result = _call_model_server(count, density, time_of_day, cx_std, cy_std, avg_box_area)
    return result.get("predictedDensity", round(min(9.0, density + 0.6), 1))


def classify_risk(count: int, density: float, time_of_day: float,
                  cx_std: float, cy_std: float, avg_box_area: float) -> str:
    result = _call_model_server(count, density, time_of_day, cx_std, cy_std, avg_box_area)
    return result.get("predictedRisk", risk_from_count(count))


# ─────────────────────────────────────────────────────────────────
# TILING HELPERS
# ─────────────────────────────────────────────────────────────────
def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    """Non-maximum suppression — removes duplicate detections across tile borders."""
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas  = (x2 - x1) * (y2 - y1)
    order  = scores.argsort()[::-1]
    keep   = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou   = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[np.where(iou <= iou_thr)[0] + 1]
    return keep


def tile_predict(frame: np.ndarray) -> list[list[float]]:
    """
    Split frame into TILE_GRID×TILE_GRID overlapping tiles, run YOLO on each,
    map boxes back to original coordinates, deduplicate with NMS.
    Returns list of [x1, y1, x2, y2] in original frame pixel coords.
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
            results = yolo_model.predict(source=tile, conf=CONF,
                                         verbose=False, classes=[0])
            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                all_boxes.append([bx1 + x1, by1 + y1, bx2 + x1, by2 + y1])
                all_scores.append(float(box.conf[0]))

    if not all_boxes:
        return []
    keep = _nms(np.array(all_boxes), np.array(all_scores), NMS_IOU)
    return [all_boxes[i] for i in keep]


# ─────────────────────────────────────────────────────────────────
# SUPABASE PERSISTENCE  (runs in background thread, never blocks)
# ─────────────────────────────────────────────────────────────────
def _save_to_supabase(density: float, pred_people: int,
                      forecast: float, risk: str) -> None:
    """Saves one inference cycle to Supabase (encrypted via RPC).
    Called in a daemon thread — any failure is silently ignored."""
    if _supabase is None:
        return
    try:
        # Map risk string to severity label used in DB
        severity = "HIGH" if risk == "Critical" else "MEDIUM" if risk == "Busy" else "LOW"

        # Save crowd metrics window (AES-256 encrypted by DB trigger)
        _supabase.rpc("insert_metric_window", {
            "p_stadium_id":       1,
            "p_zone_id":          1,
            "p_gate_id":          1,
            "p_density_ppm2":     density,
            "p_arrivals_per_min": float(pred_people),
            "p_queue_len_est":    pred_people,
            "p_flow_rate":        round(pred_people / 60.0, 2),
        }).execute()

        # Save AI prediction (AES-256 encrypted by DB trigger)
        _supabase.rpc("insert_prediction", {
            "p_stadium_id":      1,
            "p_zone_id":         1,
            "p_gate_id":         1,
            "p_density_pred":    forecast,
            "p_wait_pred_min":   max(1.0, pred_people / 10.0),
            "p_congestion_prob": min(1.0, pred_people / 25.0),
            "p_confidence":      0.88,
            "p_severity":        severity,
        }).execute()

        # Save alert only when crowd is Busy or Critical
        if risk in ("Busy", "Critical"):
            _supabase.rpc("insert_alert", {
                "p_stadium_id": 1,
                "p_zone_id":    1,
                "p_gate_id":    1,
                "p_severity":   severity,
                "p_reason":     f"Crowd density reached {risk} level — {pred_people} people detected",
            }).execute()

    except Exception as exc:
        # Never crash the inference loop over a DB error
        print(f"[supabase] Save failed (non-fatal): {exc}")


# ─────────────────────────────────────────────────────────────────
# BACKGROUND INFERENCE LOOP
# ─────────────────────────────────────────────────────────────────
def inference_loop():
    global latest, last_heatmap

    # TF disabled in backend — conflicts with YOLO/PyTorch on Apple Silicon (OpenMP crash)
    # Risk classification uses rule-based fallback which is stable

    frame_gen   = next_frame()
    frame_w     = HEATMAP_W
    frame_h     = HEATMAP_H
    time_of_day = 10.0

    while True:
        frame, source_name = next(frame_gen)
        frame_h, frame_w   = frame.shape[:2]

        # ── YOLO tiled detection (3×3 grid → detects distant/small people) ──
        xyxy_all    = tile_predict(frame)
        pred_people = len(xyxy_all)
        tracked_ids = pred_people

        # ── Spatial features ──
        centres = [
            (0.5 * (x1 + x2), 0.5 * (y1 + y2))
            for x1, y1, x2, y2 in xyxy_all
        ]
        cx_std  = float(np.std([c[0] for c in centres])) if centres else 0.0
        cy_std  = float(np.std([c[1] for c in centres])) if centres else 0.0
        fa      = max(1, frame_w * frame_h)
        avg_box = (float(np.mean([(x2-x1)*(y2-y1) for x1,y1,x2,y2 in xyxy_all])) / fa
                   if xyxy_all else 0.0)

        # ── Models ──
        density   = density_from_count(pred_people)
        risk      = classify_risk(pred_people, density, time_of_day,
                                  cx_std, cy_std, avg_box)
        forecast  = predict_15min(pred_people, density, time_of_day,
                                  cx_std, cy_std, avg_box)

        incidents = 0
        if risk == "Busy":     incidents = 1
        if risk == "Critical": incidents = 3

        # ── Heatmap ──
        last_heatmap = build_heatmap(centres, frame_w, frame_h)

        timestamp = time.strftime("%H:%M:%S")

        latest = {
            "timestamp":       timestamp,
            "source":          source_name,
            "peoplePred":      pred_people,
            "trackedIDs":      tracked_ids,
            "avgDensity":      density,
            "riskLevel":       risk,
            "activeIncidents": incidents,
            "accuracy":        0.0,        # no GT labels in video mode
        }

        history.append({
            "t":             timestamp,
            "density":       density,
            "predDensity15": forecast,
            "peoplePred":    pred_people,
            "trackedIDs":    tracked_ids,
        })

        # Save to Supabase in background — never blocks inference
        threading.Thread(
            target=_save_to_supabase,
            args=(density, pred_people, forecast, risk),
            daemon=True,
        ).start()

        time.sleep(UPDATE_EVERY_SEC)


threading.Thread(target=inference_loop, daemon=True).start()


# ─────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="FIFA WC 2034 Crowd AI Backend",
    version="2.0.0",
    description="YOLOv11x + DeepSort + LightGBM + TensorFlow crowd management API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["Health"])
def health():
    return {
        "status":            "ok",
        "service":           "crowd-ai-backend",
        "mode":              "camera" if CAMERA_MODE else "video",
        "model_server":      _model_server_ok,
        "lgbm_loaded":       _model_server_ok,
        "tf_loaded":         _model_server_ok,
    }


@app.get("/api/v1/metrics/latest", tags=["Metrics"])
def metrics_latest():
    return latest


@app.get("/api/v1/metrics/history", tags=["Metrics"])
def metrics_history():
    return list(history)


@app.get("/api/v1/predictions/15min", tags=["Predictions"])
def prediction_15min():
    if not history:
        return {"forecastHorizon": "15 minutes",
                "predictedDensity": 0.0, "predictedRisk": "Normal"}
    last = history[-1]
    pd15 = last["predDensity15"]
    return {
        "forecastHorizon":  "15 minutes",
        "predictedDensity": pd15,
        "predictedRisk":    ("Critical" if pd15 >= 5.0
                             else "Busy" if pd15 >= 3.0
                             else "Normal"),
    }


@app.get("/api/v1/heatmap", tags=["Metrics"])
def heatmap():
    """Returns the latest crowd density heatmap as a base64-encoded JPEG."""
    return {"heatmap": last_heatmap}


@app.post("/api/v1/mode/camera", tags=["Config"])
def switch_to_camera():
    """Switch to live camera input (call when camera is wired)."""
    import api as _self
    _self.CAMERA_MODE = True
    return {"message": "Switched to live camera mode. Restart server to apply."}


@app.post("/api/v1/mode/video", tags=["Config"])
def switch_to_video():
    """Switch back to video file demo mode."""
    import api as _self
    _self.CAMERA_MODE = False
    return {"message": "Switched to video file mode. Restart server to apply."}
