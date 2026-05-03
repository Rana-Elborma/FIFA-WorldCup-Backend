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
    RTSP_TRANSPORT, RTSP_FRAME_RATE,
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
    elif SOURCE == "relay":
        yield from _relay_gen()
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
# RTSP stream mode  (NVR / DVR — direct connection)
# ─────────────────────────────────────────────────────────────────
def _rtsp_gen():
    display_url = RTSP_URL.split("@")[-1] if "@" in RTSP_URL else RTSP_URL
    print(f"[camera] RTSP mode — {display_url} (transport={RTSP_TRANSPORT})")

    frame_interval = 1.0 / max(RTSP_FRAME_RATE, 0.1)  # seconds between frames
    consecutive_failures = 0

    while True:
        # Force TCP transport and reduce buffering for reliable NVR streams
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            f"rtsp_transport;{RTSP_TRANSPORT}|"
            "buffer_size;1048576|"
            "max_delay;500000"
        )
        cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimal buffer — get latest frame

        if not cap.isOpened():
            consecutive_failures += 1
            wait = min(RTSP_RECONNECT_DELAY * consecutive_failures, 30)
            print(f"[camera] RTSP not reachable — retrying in {wait}s "
                  f"(attempt {consecutive_failures})")
            time.sleep(wait)
            continue

        print(f"[camera] RTSP connected ✓ — {display_url}")
        consecutive_failures = 0
        last_frame_time = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[camera] RTSP frame lost — reconnecting …")
                break

            # Rate-limit: only yield at RTSP_FRAME_RATE fps
            now = time.time()
            if now - last_frame_time < frame_interval:
                continue
            last_frame_time = now
            yield frame, f"CAM3:{display_url}"

        cap.release()
        time.sleep(RTSP_RECONNECT_DELAY)


# ─────────────────────────────────────────────────────────────────
# Relay mode  (Pi edge agent POSTs frames to /api/v1/ingest/frame)
# Mac backend receives JPEG bytes, decodes, runs inference.
# Use when Mac cannot reach NVR directly.
# ─────────────────────────────────────────────────────────────────
_relay_queue: list = []
_relay_lock = __import__("threading").Lock()


def push_relay_frame(frame_bgr: np.ndarray) -> None:
    """Called by /api/v1/ingest/frame to enqueue a frame from the Pi."""
    with _relay_lock:
        _relay_queue.clear()          # keep only the latest frame
        _relay_queue.append(frame_bgr)


def _relay_gen():
    print("[camera] Relay mode — waiting for frames from Pi edge agent …")
    last_id = None
    while True:
        frame = None
        with _relay_lock:
            if _relay_queue:
                candidate = _relay_queue[0]
                if id(candidate) != last_id:
                    frame = candidate
                    last_id = id(candidate)
        if frame is not None:
            yield frame, "PI-CAM3-relay"
        else:
            time.sleep(0.02)  # poll at 50 Hz — pick up new frame fast


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
# Live webcam  (direct access — used by inference.py demo mode)
# Independent of config.yaml so it always opens the physical camera.
# ─────────────────────────────────────────────────────────────────
def live_webcam_frames(index: int = 0):
    """
    Yields raw frames from the webcam continuously.
    Used by inference.py run_live_demo() — does not depend on config.yaml.
    Raises RuntimeError if the camera cannot be opened.
    """
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f"[camera] Cannot open webcam at index {index}")
    print(f"[camera] Webcam {index} opened — {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}×"
          f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ "
          f"{cap.get(cv2.CAP_PROP_FPS):.0f} fps")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[camera] Frame read failed — retrying")
                time.sleep(0.05)
                continue
            yield frame
    finally:
        cap.release()
        print("[camera] Webcam released")


# ─────────────────────────────────────────────────────────────────
# Status helper  (exposed via /api/v1/camera/status)
# ─────────────────────────────────────────────────────────────────
def camera_status() -> dict:
    display_url = RTSP_URL.split("@")[-1] if "@" in RTSP_URL else RTSP_URL
    with _relay_lock:
        relay_active = len(_relay_queue) > 0
    return {
        "source":        SOURCE,
        "video_folder":  VIDEO_FOLDER     if SOURCE == "video"  else None,
        "frame_skip":    VIDEO_FRAME_SKIP if SOURCE == "video"  else None,
        "webcam_index":  WEBCAM_INDEX     if SOURCE == "webcam" else None,
        "rtsp_url":      display_url      if SOURCE == "rtsp"   else None,
        "relay_active":  relay_active     if SOURCE == "relay"  else None,
        "connected":     SOURCE in ("webcam", "rtsp") or
                         (SOURCE == "relay" and relay_active),
    }
