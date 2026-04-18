"""
alerts.py — Alert rules and alert history.

Rules:
  Critical crowd → emit CRITICAL alert (max once every 30 s)
  Normal → Busy transition → emit WARNING alert
  Busy/Critical → Normal transition → emit INFO (cleared) alert
"""
import time
from collections import deque

_alert_history: deque = deque(maxlen=50)
_last_risk             = "Normal"
_last_critical_time    = 0.0


def check_and_dispatch(risk: str, count: int, density: float, source: str) -> list[dict]:
    """
    Evaluate current risk level and emit alerts on state changes.
    Returns list of new alerts emitted this cycle (may be empty).
    """
    global _last_risk, _last_critical_time
    now    = time.time()
    emitted = []

    if risk == "Critical" and (now - _last_critical_time) > 30:
        alert = _make("CRITICAL",
                       f"Critical crowd density — {count} people, density={density:.1f}",
                       "Open gates / redirect flow immediately", source)
        _alert_history.append(alert)
        emitted.append(alert)
        _last_critical_time = now

    elif risk == "Busy" and _last_risk == "Normal":
        alert = _make("WARNING",
                       f"Crowd becoming busy — {count} people, density={density:.1f}",
                       "Monitor closely / prepare redirect", source)
        _alert_history.append(alert)
        emitted.append(alert)

    elif risk == "Normal" and _last_risk in ("Busy", "Critical"):
        alert = _make("INFO",
                       f"Crowd returned to normal — {count} people",
                       "Resume normal monitoring", source)
        _alert_history.append(alert)
        emitted.append(alert)

    _last_risk = risk
    return emitted


def get_alerts() -> list[dict]:
    """Return full alert history (last 50 events)."""
    return list(_alert_history)


def active_incidents(risk: str) -> int:
    if risk == "Critical": return 3
    if risk == "Busy":     return 1
    return 0


def _make(level: str, message: str, action: str, source: str) -> dict:
    return {
        "time":    time.strftime("%H:%M:%S"),
        "level":   level,
        "message": message,
        "action":  action,
        "source":  source,
    }
