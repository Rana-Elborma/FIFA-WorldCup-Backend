"""
supabase_writer.py — Pushes inference results to Supabase.

Writes two tables after every inference cycle:
  - metric_window  : aggregated crowd metrics (density, flow, etc.)
  - prediction     : 15-min LightGBM forecast

Uses service_role key (bypasses RLS) — never exposed to the frontend.
Runs in a background thread so it never blocks the inference loop.

Configuration: supabase section in config.yaml.
"""
import threading
import time
import datetime
import yaml
import os

# ── Load supabase config from config.yaml ─────────────────────────
with open(os.path.join(os.path.dirname(__file__), "config.yaml")) as f:
    _cfg = yaml.safe_load(f)

_sb_cfg        = _cfg.get("supabase", {})
SUPABASE_URL   = _sb_cfg.get("url", "")
SERVICE_KEY    = _sb_cfg.get("service_role_key", "")
STADIUM_ID     = _sb_cfg.get("stadium_id", "")
ZONE_ID        = _sb_cfg.get("zone_id", "")
GATE_ID        = _sb_cfg.get("gate_id", "") or None   # None if blank

_client = None
_enabled = False


def _init():
    global _client, _enabled
    if not SUPABASE_URL or not SERVICE_KEY or not STADIUM_ID or not ZONE_ID:
        print("[supabase_writer] Not configured — skipping Supabase writes.")
        print("[supabase_writer] Fill in config.yaml → supabase section to enable.")
        return
    try:
        from supabase import create_client
        _client  = create_client(SUPABASE_URL, SERVICE_KEY)
        _enabled = True
        print("[supabase_writer] Connected to Supabase ✓")
    except ImportError:
        print("[supabase_writer] supabase-py not installed. Run: pip install supabase")
    except Exception as e:
        print(f"[supabase_writer] Connection failed: {e}")


_init()


# ── Write queue (fire-and-forget, non-blocking) ───────────────────
_queue: list[dict] = []
_queue_lock = threading.Lock()


def _flush_worker():
    """Background thread: drains the queue and writes to Supabase."""
    while True:
        time.sleep(5)   # batch writes every 5 s
        if not _enabled or not _client:
            continue
        with _queue_lock:
            batch = _queue.copy()
            _queue.clear()

        for item in batch:
            try:
                if item["_type"] == "metric_window":
                    _write_metric_window(item)
                elif item["_type"] == "prediction":
                    _write_prediction(item)
                elif item["_type"] == "alert":
                    _write_alert(item)
                elif item["_type"] == "system_log":
                    _write_system_log(item)
            except Exception as e:
                print(f"[supabase_writer] Write error ({item.get('_type')}): {e}")


threading.Thread(target=_flush_worker, daemon=True).start()


# ── Public API ───────────────────────────────────────────────────

def push_metric_window(
    density_ppm2: float,
    arrivals_per_min: float,
    queue_len_est: float | None = None,
    flow_rate: float | None = None,
):
    """Queue a metric_window row. Called after every inference cycle."""
    if not _enabled:
        return
    now = datetime.datetime.utcnow()
    window_start = (now - datetime.timedelta(seconds=60)).isoformat() + "Z"
    window_end   = now.isoformat() + "Z"

    with _queue_lock:
        _queue.append({
            "_type":           "metric_window",
            "ts_start":        window_start,
            "ts_end":          window_end,
            "stadium_id":      STADIUM_ID,
            "zone_id":         ZONE_ID,
            "gate_id":         GATE_ID,
            "density_ppm2":    round(density_ppm2, 4),
            "arrivals_per_min": round(arrivals_per_min, 2),
            "queue_len_est":   round(queue_len_est, 2) if queue_len_est is not None else None,
            "flow_rate":       round(flow_rate, 2) if flow_rate is not None else None,
        })


def push_prediction(
    density_pred: float,
    severity: str,
    horizon_min: int = 15,
    wait_pred_min: float | None = None,
    congestion_prob: float | None = None,
    confidence: float | None = None,
):
    """Queue a prediction row. Called after each model server response."""
    if not _enabled:
        return
    # Map risk labels to severity enum
    sev_map = {"Normal": "low", "Busy": "medium", "Critical": "critical"}
    sev = sev_map.get(severity, "low")

    with _queue_lock:
        _queue.append({
            "_type":          "prediction",
            "horizon_min":    horizon_min,
            "stadium_id":     STADIUM_ID,
            "zone_id":        ZONE_ID,
            "gate_id":        GATE_ID,
            "density_pred":   round(density_pred, 4),
            "wait_pred_min":  round(wait_pred_min, 2) if wait_pred_min is not None else None,
            "congestion_prob": round(min(1.0, max(0.0, congestion_prob)), 4) if congestion_prob is not None else None,
            "confidence":     round(min(1.0, max(0.0, confidence)), 4) if confidence is not None else None,
            "severity":       sev,
        })


def push_system_log(level: str, source: str, message: str, metadata: dict | None = None):
    """Queue an audit_log row for every inference cycle."""
    if not _enabled:
        return
    with _queue_lock:
        _queue.append({
            "_type":      "system_log",
            "table_name": "metric_window",
            "operation":  "INSERT",
            "record_id":  source,
            "payload":    {"level": level, "message": message, **(metadata or {})},
        })


def push_alert(level: str, message: str):
    """Queue an alert row. Called when alerts.check_and_dispatch emits a new alert."""
    if not _enabled:
        return
    # Map in-memory level to DB severity enum
    sev_map = {"CRITICAL": "critical", "WARNING": "high", "INFO": "low"}
    sev = sev_map.get(level, "low")
    with _queue_lock:
        _queue.append({
            "_type":      "alert",
            "stadium_id": STADIUM_ID,
            "zone_id":    ZONE_ID,
            "gate_id":    GATE_ID,
            "severity":   sev,
            "message":    message,
        })


# ── Internal writers ──────────────────────────────────────────────

def _write_metric_window(item: dict):
    payload = {k: v for k, v in item.items() if not k.startswith("_") and v is not None}
    _client.table("metric_window").insert(payload).execute()


def _write_prediction(item: dict):
    payload = {k: v for k, v in item.items() if not k.startswith("_") and v is not None}
    _client.table("prediction").insert(payload).execute()


def _write_alert(item: dict):
    payload = {k: v for k, v in item.items() if not k.startswith("_") and v is not None}
    _client.table("alert").insert(payload).execute()


def _write_system_log(item: dict):
    payload = {k: v for k, v in item.items() if not k.startswith("_") and v is not None}
    _client.table("audit_log").insert(payload).execute()
