from datetime import datetime


def manage_block(action: str, name: str) -> dict:
    """
    Domain logic for managing a time allocation block.
    """
    now = datetime.now().isoformat()  # noqa: DTZ005 — log entries use naive local timestamps
    return {
        "ok": True,
        "action": action,
        "block_name": name,
        "timestamp": now,
        "message": f"Block {action} recorded for {name}.",
    }
