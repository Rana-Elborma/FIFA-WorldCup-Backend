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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
import camera
import inference
import state
import alerts

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

        # 4. Alert system
        alerts.check_and_dispatch(risk, count, density, source_name)

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
