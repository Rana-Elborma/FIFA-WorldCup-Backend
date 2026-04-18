"""
config.py — Single source of truth for all backend settings.
Reads config.yaml; all other modules import from here.
"""
import os
import yaml

_cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(_cfg_path) as _f:
    _cfg = yaml.safe_load(_f)

# ── Camera source ──────────────────────────────────────────────────
SOURCE = _cfg.get("source", "video")           # "video" | "webcam" | "rtsp"

VIDEO_FOLDER     = _cfg["video"]["folder"]
VIDEO_FRAME_SKIP = int(_cfg["video"].get("frame_skip", 30))

WEBCAM_INDEX     = int(_cfg["webcam"].get("index", 0))

RTSP_URL              = _cfg["rtsp"].get("url", "")
RTSP_RECONNECT_DELAY  = int(_cfg["rtsp"].get("reconnect_delay", 5))

# ── YOLO ──────────────────────────────────────────────────────────
YOLO_MODEL   = _cfg["yolo"].get("model", "yolo11x.pt")
CONF         = float(_cfg["yolo"].get("conf", 0.10))
TILE_GRID    = int(_cfg["yolo"].get("tile_grid", 3))
TILE_OVERLAP = float(_cfg["yolo"].get("tile_overlap", 0.10))
NMS_IOU      = float(_cfg["yolo"].get("nms_iou", 0.35))

# ── Inference ─────────────────────────────────────────────────────
UPDATE_EVERY_SEC = float(_cfg["inference"].get("update_every_sec", 3))

# ── Risk thresholds ───────────────────────────────────────────────
NORMAL_MAX = int(_cfg["thresholds"].get("normal_max", 10))
BUSY_MAX   = int(_cfg["thresholds"].get("busy_max", 25))

# ── Heatmap ───────────────────────────────────────────────────────
HEATMAP_GRID = int(_cfg["heatmap"].get("grid", 10))
HEATMAP_W    = int(_cfg["heatmap"].get("width", 640))
HEATMAP_H    = int(_cfg["heatmap"].get("height", 480))

# ── Models ────────────────────────────────────────────────────────
MODELS_DIR       = _cfg["models"].get("dir", "models")
MODEL_SERVER_URL = _cfg["models"].get("server_url", "http://127.0.0.1:8001")
