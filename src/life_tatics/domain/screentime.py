from datetime import datetime

def log_screentime(mode: str, duration: int) -> dict:
    """
    Domain logic for tracking developer/screen time.
    """
    now = datetime.now().isoformat()
    return {
        "ok": True,
        "mode": mode,
        "duration_minutes": duration,
        "timestamp": now,
        "message": f"Logged {duration} minutes of {mode} screentime."
    }
