#!/usr/bin/env python3
"""
pi_edge_agent.py — Runs on the Raspberry Pi.

Captures frames from the NVR RTSP stream (CAM 3) and POSTs them
to the Mac/server backend for AI inference.

Usage on Pi:
    pip install opencv-python-headless requests
    python pi_edge_agent.py

Environment variables (override defaults):
    RTSP_URL        — RTSP source (default: CAM 3)
    BACKEND_URL     — Mac backend address (default: http://<your-mac-ip>:8000)
    CAMERA_ID       — label for this camera (default: cam3)
    FRAME_INTERVAL  — seconds between sent frames (default: 3)
"""
import os
import time
import base64
import logging
import cv2
import requests

# ── Configuration ─────────────────────────────────────────────────
RTSP_URL       = os.environ.get("RTSP_URL",
    "rtsp://192.168.2.10:554/avstream/channel=3/stream=0.sdp")
BACKEND_URL    = os.environ.get("BACKEND_URL",
    "http://192.168.2.2:8000")          # change to your Mac's IP on the same network
CAMERA_ID      = os.environ.get("CAMERA_ID", "cam3")
FRAME_INTERVAL = float(os.environ.get("FRAME_INTERVAL", "0.1"))  # 10 fps
RECONNECT_WAIT = int(os.environ.get("RECONNECT_WAIT", "5"))
JPEG_QUALITY   = int(os.environ.get("JPEG_QUALITY", "50"))      # smaller payload = faster transfer
SEND_WIDTH     = int(os.environ.get("SEND_WIDTH", "640"))        # resize before sending

INGEST_ENDPOINT = f"{BACKEND_URL}/api/v1/ingest/frame"
HEALTH_ENDPOINT = f"{BACKEND_URL}/api/v1/health"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [pi-edge] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pi_edge")


# ── Backend health check ──────────────────────────────────────────
def wait_for_backend(timeout: int = 60):
    log.info(f"Waiting for backend at {BACKEND_URL} …")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(HEALTH_ENDPOINT, timeout=3)
            if r.status_code == 200:
                log.info("Backend is up ✓")
                return True
        except Exception:
            pass
        time.sleep(3)
    log.error("Backend not reachable — starting anyway, will retry on each frame")
    return False


# ── Frame sender ─────────────────────────────────────────────────
def send_frame(frame_bgr) -> bool:
    h, w = frame_bgr.shape[:2]
    if w > SEND_WIDTH:
        frame_bgr = cv2.resize(frame_bgr, (SEND_WIDTH, int(h * SEND_WIDTH / w)),
                               interpolation=cv2.INTER_LINEAR)
    _, buf = cv2.imencode(".jpg", frame_bgr,
                          [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    b64 = base64.b64encode(buf).decode("utf-8")
    payload = {
        "frame":     b64,
        "camera_id": CAMERA_ID,
        "ts":        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        r = requests.post(INGEST_ENDPOINT, json=payload, timeout=15)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        log.warning("Backend unreachable — frame dropped")
        return False
    except Exception as e:
        log.warning(f"Send failed: {e}")
        return False


# ── RTSP capture loop ─────────────────────────────────────────────
def capture_loop():
    display = RTSP_URL.split("@")[-1] if "@" in RTSP_URL else RTSP_URL
    consecutive_fails = 0

    while True:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|buffer_size;1048576|max_delay;500000|loglevel;quiet"
        )
        log.info(f"Connecting to RTSP: {display}")
        cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            consecutive_fails += 1
            wait = min(RECONNECT_WAIT * consecutive_fails, 30)
            log.warning(f"RTSP not reachable — retrying in {wait}s")
            time.sleep(wait)
            continue

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        log.info(f"RTSP connected ✓ — {w}×{h} — sending every {FRAME_INTERVAL}s")
        consecutive_fails = 0
        last_sent = 0.0
        frames_sent = 0
        frames_dropped = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                log.warning("Stream lost — reconnecting …")
                break

            now = time.time()
            if now - last_sent < FRAME_INTERVAL:
                continue   # skip — wait for next interval

            ok = send_frame(frame)
            if ok:
                frames_sent += 1
                last_sent = now
                if frames_sent % 20 == 0:
                    log.info(f"Sent {frames_sent} frames | dropped {frames_dropped}")
            else:
                frames_dropped += 1
                last_sent = now  # still advance timer to avoid hammering backend

        cap.release()
        time.sleep(RECONNECT_WAIT)


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"Pi Edge Agent starting — CAM: {CAMERA_ID}")
    log.info(f"RTSP source : {RTSP_URL.split('@')[-1]}")
    log.info(f"Backend     : {BACKEND_URL}")
    log.info(f"Interval    : {FRAME_INTERVAL}s per frame")
    wait_for_backend()
    capture_loop()
