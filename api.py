"""
FIFA WC 2034  —  Crowd AI Backend  v3.0
────────────────────────────────────────
Pipeline:
  Camera → YOLO (3×3 tiling) → Feature Extraction
       → Model Server (LightGBM + TensorFlow)
       → Alerts → State → FastAPI → Dashboard

Modules:
  config.py      — all settings (reads config.yaml)
  camera.py      — frame generator: video / webcam / RTSP / mock
  inference.py   — YOLOv11x tiling, NMS, features, heatmap, annotated frame
  state.py       — shared in-memory state + history ring buffer
  alerts.py      — alert rules + alert history
  model_server.py — separate process on :8001 (LightGBM + TensorFlow)

Run:
  # Terminal 1 — model microservice (LightGBM + TF)
  .venv/bin/python -m uvicorn model_server:app --port 8001 --reload

  # Terminal 2 — main backend (YOLO + API)
  .venv/bin/python -m uvicorn api:app --port 8000 --reload
"""

import base64
import time
import threading
import urllib.request
import json as _json

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
import camera
import inference
import state
import alerts
import supabase_writer

# ─────────────────────────────────────────────────────────────────
# MODEL SERVER  (LightGBM + TensorFlow on port 8001)
# ─────────────────────────────────────────────────────────────────
_model_server_ok = False


def _call_model_server(count, density, time_of_day,
                       cx_std, cy_std, avg_box_area) -> dict:
    """POST features to model_server.py → returns {predictedDensity, predictedRisk}."""
    global _model_server_ok
    try:
        payload = _json.dumps({
            "count": count, "density": density, "time_of_day": time_of_day,
            "cx_std": cx_std, "cy_std": cy_std, "avg_box_area": avg_box_area,
        }).encode()
        req = urllib.request.Request(
            f"{config.MODEL_SERVER_URL}/predict",
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


# ─────────────────────────────────────────────────────────────────
# BACKGROUND INFERENCE LOOP  (runs in daemon thread)
# ─────────────────────────────────────────────────────────────────
def _inference_loop():
    frame_gen   = camera.frame_generator()
    time_of_day = 10.0           # fixed for now; replace with real clock if needed

    while True:
        # 1. Get next frame from camera source
        frame, source_name = next(frame_gen)
        frame_h, frame_w   = frame.shape[:2]

        # 2. YOLO detection (plug-in point: inference.tile_predict)
        boxes   = inference.tile_predict(frame)
        feats   = inference.extract_features(boxes, frame_w, frame_h)
        count   = feats["count"]
        density = inference.density_from_count(count)

        # 3. LightGBM forecast + TensorFlow classification (via model_server)
        ms      = _call_model_server(count, density, time_of_day,
                                     feats["cx_std"], feats["cy_std"],
                                     feats["avg_box_area"])
        forecast = ms.get("predictedDensity", round(min(9.0, density + 0.6), 1))
        risk     = ms.get("predictedRisk",
                          "Critical" if count > config.BUSY_MAX
                          else "Busy" if count > config.NORMAL_MAX
                          else "Normal")

        # 4. Alert system + save to Supabase
        new_alerts = alerts.check_and_dispatch(risk, count, density, source_name)
        for a in new_alerts:
            supabase_writer.push_alert(a["level"], a["message"])

        # 5. Heatmap (base64 JPEG)
        state.set_heatmap(
            inference.build_heatmap(feats["centres"], frame_w, frame_h)
        )

        # 6. Annotated frame for /stream/frame endpoint
        annotated = inference.annotate_frame(frame, boxes, count, risk)
        _, buf    = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 72])
        state.set_annotated_frame(base64.b64encode(buf).decode("utf-8"))

        # 7. Update shared state
        ts = time.strftime("%H:%M:%S")
        state.update({
            "timestamp":       ts,
            "source":          source_name,
            "peoplePred":      count,
            "trackedIDs":      count,
            "avgDensity":      density,
            "riskLevel":       risk,
            "activeIncidents": alerts.active_incidents(risk),
            "accuracy":        0.0,
            "cameraConnected": config.SOURCE in ("webcam", "rtsp"),
        })
        state.push_history({
            "t":             ts,
            "density":       density,
            "predDensity15": forecast,
            "peoplePred":    count,
            "trackedIDs":    count,
        })

        # 8. Push to Supabase (non-blocking — batched every 5 s)
        arrivals = count / max(config.UPDATE_EVERY_SEC, 1)
        supabase_writer.push_metric_window(
            density_ppm2     = density,
            arrivals_per_min = arrivals,
        )
        supabase_writer.push_prediction(
            density_pred = forecast,
            severity     = risk,
            horizon_min  = 15,
        )
        supabase_writer.push_system_log(
            level    = "INFO",
            source   = source_name,
            message  = f"Inference cycle: {count} people, density={density:.2f}, risk={risk}",
            metadata = {"count": count, "density": density, "risk": risk, "forecast": forecast},
        )

        time.sleep(config.UPDATE_EVERY_SEC)


threading.Thread(target=_inference_loop, daemon=True).start()


# ─────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="FIFA WC 2034 Crowd AI Backend",
    version="3.0.0",
    description="Camera → YOLOv11x (3×3 tiling) → LightGBM → TensorFlow → Dashboard",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Existing endpoints  (response format unchanged — frontend keeps working) ──

@app.get("/api/v1/health", tags=["Health"])
def health():
    return {
        "status":           "ok",
        "service":          "crowd-ai-backend",
        "version":          "3.0.0",
        "mode":             config.SOURCE,
        "lgbm_loaded":      _model_server_ok,
        "tf_loaded":        _model_server_ok,
        "model_server":     _model_server_ok,
        "camera_connected": config.SOURCE in ("webcam", "rtsp"),
    }


@app.get("/api/v1/metrics/latest", tags=["Metrics"])
def metrics_latest():
    return state.latest


@app.get("/api/v1/metrics/history", tags=["Metrics"])
def metrics_history():
    return list(state.history)


@app.get("/api/v1/predictions/15min", tags=["Predictions"])
def prediction_15min():
    if not state.history:
        return {"forecastHorizon": "15 minutes",
                "predictedDensity": 0.0, "predictedRisk": "Normal"}
    pd15 = state.history[-1]["predDensity15"]
    return {
        "forecastHorizon":  "15 minutes",
        "predictedDensity": pd15,
        "predictedRisk":    ("Critical" if pd15 >= 5.0
                             else "Busy" if pd15 >= 3.0
                             else "Normal"),
    }


@app.get("/api/v1/heatmap", tags=["Metrics"])
def heatmap():
    return {"heatmap": state.last_heatmap}


# ── New endpoints ──────────────────────────────────────────────────

@app.get("/api/v1/alerts", tags=["Alerts"])
def get_alerts():
    """Alert history — last 50 events with level, message, action, timestamp."""
    return {"alerts": alerts.get_alerts()}


@app.get("/api/v1/camera/status", tags=["Camera"])
def camera_status():
    """Current camera source configuration (video / webcam / rtsp)."""
    return camera.camera_status()


@app.get("/api/v1/stream/frame", tags=["Stream"])
def stream_frame():
    """Latest annotated frame as base64 JPEG — bounding boxes + HUD overlay."""
    return {"frame": state.last_annotated_frame}


# ── Live camera endpoint ───────────────────────────────────────────

_live_thread: threading.Thread | None = None
_live_results: dict = {}


def _live_inference_worker():
    """Background worker: reads webcam, runs yolov8n, updates _live_results."""
    from camera import live_webcam_frames
    global _live_results
    for frame in live_webcam_frames(0):
        det   = inference.detect_live(frame)
        feats = inference.extract_features(det["boxes"], frame.shape[1], frame.shape[0])
        ms    = _call_model_server(
            det["people_count"], det["density"], float(time.strftime("%H")),
            feats["cx_std"], feats["cy_std"], feats["avg_box_area"],
        )
        _live_results = {
            "people_count": det["people_count"],
            "density":      det["density"],
            "risk_level":   ms.get("predictedRisk", inference._risk_label(det["people_count"])),
            "forecast_15m": ms.get("predictedDensity", round(min(9.0, det["density"] + 0.3), 1)),
            "source":       "webcam:0",
        }
        time.sleep(0.5)   # ~2 Hz for API; demo uses full framerate


@app.get("/live", tags=["Live"])
def live():
    """
    Start live webcam inference (background) and return latest detection result.
    For the visual window demo run:  python inference.py
    """
    global _live_thread
    if _live_thread is None or not _live_thread.is_alive():
        _live_thread = threading.Thread(target=_live_inference_worker, daemon=True)
        _live_thread.start()
        return {"status": "started", "message": "Live inference running. Poll this endpoint for updates."}
    return _live_results if _live_results else {"status": "warming_up"}


# ── Pi edge frame ingest ──────────────────────────────────────────

@app.post("/api/v1/ingest/frame", tags=["Ingest"])
async def ingest_frame(payload: dict):
    """
    Receives a base64-encoded JPEG frame from the Raspberry Pi edge agent.
    Decodes it and pushes into the relay queue so the inference loop
    processes it like any other camera frame.

    Pi sends:  { "frame": "<base64 JPEG>", "camera_id": "cam3", "ts": "..." }
    """
    b64 = payload.get("frame")
    if not b64:
        raise HTTPException(status_code=400, detail="Missing 'frame' field")

    try:
        raw   = base64.b64decode(b64)
        arr   = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("imdecode returned None")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid frame data: {e}")

    camera.push_relay_frame(frame)
    return {"status": "ok", "camera_id": payload.get("camera_id", "cam3")}


# ── Config switch hints ────────────────────────────────────────────

@app.post("/api/v1/mode/camera", tags=["Config"])
def switch_to_camera():
    return {"message": "Edit config.yaml → set source: webcam — then restart the server."}


@app.post("/api/v1/mode/video", tags=["Config"])
def switch_to_video():
    return {"message": "Edit config.yaml → set source: video — then restart the server."}


@app.post("/api/v1/mode/rtsp", tags=["Config"])
def switch_to_rtsp():
    return {"message": "Edit config.yaml → set source: rtsp and fill in rtsp.url — then restart."}
