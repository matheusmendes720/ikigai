"""Profile switching (decision #1) + thread UUIDs (decision #7)."""
from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.ikigai.souls.loader import known_profiles

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def new_thread_id() -> str:
    return str(uuid.uuid4())


def is_valid_thread_id(thread_id: str) -> bool:
    return bool(thread_id and _UUID_RE.match(thread_id))


def parse_profile_command(text: str) -> str | None:
    text = text.strip()
    if not text.startswith("/profile"):
        return None
    parts = text.split(None, 1)
    if len(parts) < 2:
        return None
    name = parts[1].strip()
    return name if name in known_profiles() else None


def log_switch(vault_root, thread_id, from_profile, to_profile, reason=""):
    log_dir = vault_root / "ikigai" / "runtime" / "chat" / thread_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "profile-switches.log"
    ts = datetime.now(timezone.utc).isoformat()
    entry = f"{ts} {from_profile} -> {to_profile} {reason}\n"
    existing = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    log_file.write_text(existing + entry, encoding="utf-8")
    return log_file
