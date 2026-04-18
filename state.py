"""
state.py — Shared in-memory state for the inference pipeline.

All modules read/write through these functions — no direct dict access
across files, which prevents race conditions between the inference
thread and the API request handlers.
"""
import threading
from collections import deque

_lock = threading.Lock()

# ── Latest snapshot (served by /api/v1/metrics/latest) ────────────
latest: dict = {
    "timestamp":       "",
    "source":          "",
    "peoplePred":      0,
    "trackedIDs":      0,
    "avgDensity":      0.0,
    "riskLevel":       "Normal",
    "activeIncidents": 0,
    "accuracy":        0.0,
    "cameraConnected": False,
}

# ── Rolling history (served by /api/v1/metrics/history) ───────────
history: deque = deque(maxlen=60)

# ── Heatmap and annotated frame (base64 JPEGs) ────────────────────
last_heatmap:         str = ""
last_annotated_frame: str = ""


def update(data: dict) -> None:
    """Merge data into the latest snapshot (thread-safe)."""
    global latest
    with _lock:
        latest = {**latest, **data}


def push_history(entry: dict) -> None:
    history.append(entry)


def set_heatmap(b64: str) -> None:
    global last_heatmap
    last_heatmap = b64


def set_annotated_frame(b64: str) -> None:
    global last_annotated_frame
    last_annotated_frame = b64
