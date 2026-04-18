"""
camera.py — Camera ingestion layer.

Supports three sources (set in config.yaml):
  "video"  — cycles through MP4 files in VIDEO_FOLDER (default / testing)
  "webcam" — USB webcam via OpenCV
  "rtsp"   — NVR/DVR RTSP stream (plug in when camera is wired)

Falls back to mock (black frames) if no source is reachable.
"""
import os
import glob
import time
import numpy as np
import cv2

from config import (
    SOURCE, VIDEO_FOLDER, VIDEO_FRAME_SKIP,
    WEBCAM_INDEX, RTSP_URL, RTSP_RECONNECT_DELAY,
)


def frame_generator():
    """
    Main entry point.  Yields (frame: np.ndarray, source_name: str) forever.
    Switch source in config.yaml — no code changes needed.
    """
    if SOURCE == "webcam":
        yield from _webcam_gen()
    elif SOURCE == "rtsp":
        yield from _rtsp_gen()
    else:
        yield from _video_gen()


# ─────────────────────────────────────────────────────────────────
# Video file mode  (testing / demo)
# ─────────────────────────────────────────────────────────────────
def _video_gen():
    files = sorted(glob.glob(os.path.join(VIDEO_FOLDER, "*.mp4")))
    if not files:
        print("[camera] No MP4 files found — switching to mock mode")
        yield from _mock_gen()
        return

    print(f"[camera] Video mode — {len(files)} files in {VIDEO_FOLDER}")
    idx = 0
    while True:
        vp    = files[idx % len(files)]
        cap   = cv2.VideoCapture(vp)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        pos   = 0
        while pos < total:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if not ret:
                break
            yield frame, os.path.basename(vp)
            pos += VIDEO_FRAME_SKIP
        cap.release()
        idx += 1


# ─────────────────────────────────────────────────────────────────
# USB Webcam mode
# ─────────────────────────────────────────────────────────────────
def _webcam_gen():
    print(f"[camera] Webcam mode — index {WEBCAM_INDEX}")
    cap = cv2.VideoCapture(WEBCAM_INDEX)
    if not cap.isOpened():
        print("[camera] Webcam not found — switching to mock mode")
        yield from _mock_gen()
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        yield frame, f"webcam:{WEBCAM_INDEX}"


# ─────────────────────────────────────────────────────────────────
# RTSP stream mode  (NVR / DVR — plug in when camera is wired)
# ─────────────────────────────────────────────────────────────────
def _rtsp_gen():
    # Hide credentials from logs
    display_url = RTSP_URL.split("@")[-1] if "@" in RTSP_URL else RTSP_URL
    print(f"[camera] RTSP mode — {display_url}")
    while True:
        cap = cv2.VideoCapture(RTSP_URL)
        if not cap.isOpened():
            print(f"[camera] RTSP not reachable — retrying in {RTSP_RECONNECT_DELAY}s")
            time.sleep(RTSP_RECONNECT_DELAY)
            continue
        print(f"[camera] RTSP connected — {display_url}")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[camera] RTSP stream lost — reconnecting")
                break
            yield frame, display_url
        cap.release()


# ─────────────────────────────────────────────────────────────────
# Mock mode  (fallback — system works even with no camera)
# ─────────────────────────────────────────────────────────────────
def _mock_gen():
    print("[camera] Mock mode — generating synthetic frames")
    rng = np.random.default_rng(0)
    while True:
        frame = rng.integers(0, 60, (480, 640, 3), dtype=np.uint8)
        yield frame, "mock"
        time.sleep(1)


# ─────────────────────────────────────────────────────────────────
# Status helper  (exposed via /api/v1/camera/status)
# ─────────────────────────────────────────────────────────────────
def camera_status() -> dict:
    display_url = RTSP_URL.split("@")[-1] if "@" in RTSP_URL else RTSP_URL
    return {
        "source":        SOURCE,
        "video_folder":  VIDEO_FOLDER  if SOURCE == "video"  else None,
        "frame_skip":    VIDEO_FRAME_SKIP if SOURCE == "video" else None,
        "webcam_index":  WEBCAM_INDEX  if SOURCE == "webcam" else None,
        "rtsp_url":      display_url   if SOURCE == "rtsp"   else None,
        "connected":     SOURCE in ("webcam", "rtsp"),
    }
