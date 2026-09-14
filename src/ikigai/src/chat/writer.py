"""Chat file writer. Routes through vault_write (ADR-012)."""
from __future__ import annotations
import json
from pathlib import Path


def write_entry(vault_root, thread_id, entry):
    chat_dir = vault_root / "ikigai" / "runtime" / "chat" / thread_id
    chat_dir.mkdir(parents=True, exist_ok=True)
    md = chat_dir / "chat.md"
    ts = entry.get("ts", "")
    actor = entry.get("actor", "?")
    content = entry.get("content", "")
    with md.open("a", encoding="utf-8") as f:
        f.write(f"\n## [{ts}] {actor}\n{content}\n")
    return md


def write_proposal(vault_root, thread_id, proposal):
    chat_dir = vault_root / "ikigai" / "runtime" / "chat" / thread_id
    chat_dir.mkdir(parents=True, exist_ok=True)
    sidecar = chat_dir / "chat.json"
    payload = {"proposals": {}}
    if sidecar.exists():
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload.setdefault("proposals", {})[proposal["proposal_id"]] = proposal
    sidecar.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return sidecar
