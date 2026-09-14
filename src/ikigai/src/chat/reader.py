"""Chat file reader."""
from __future__ import annotations
import json
from pathlib import Path


def read_thread(vault_root, thread_id):
    chat_dir = vault_root / "ikigai" / "runtime" / "chat" / thread_id
    md = chat_dir / "chat.md"
    js = chat_dir / "chat.json"
    return {
        "thread_id": thread_id,
        "chat_md": md.read_text(encoding="utf-8") if md.exists() else "",
        "chat_json": json.loads(js.read_text(encoding="utf-8")) if js.exists() else None,
    }
