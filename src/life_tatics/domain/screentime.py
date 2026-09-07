from datetime import datetime


def log_screentime(mode: str, duration: int) -> dict:
    """
    Domain logic for tracking developer/screen time.
    """
    now = datetime.now().isoformat()  # noqa: DTZ005 — log entries use naive local timestamps
    return {
        "ok": True,
        "mode": mode,
        "duration_minutes": duration,
        "timestamp": now,
        "message": f"Logged {duration} minutes of {mode} screentime.",
    }
