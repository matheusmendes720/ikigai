"""Chat file reader — thread-aware entry + proposal enumeration.

Pydantic-typed where possible (decision #3). Returns ([entries], [proposals])
tuple per tests/test_chat_system.py::test_read_thread_missing_returns_empty
plus round-trip tests.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

from .schema import Entry, EntryRole, Proposal


# Tolerant metadata parser for our write_entry format: `## [role] eid\n\n{content}`
_ENTRY_HEADER_RE = re.compile(r"^##\s*\[([^\]]+)\]\s+(\S+)\s*$", re.MULTILINE)


def read_thread(thread_id: str, *, base_dir) -> tuple[list[Entry], list[Proposal]]:
    """Read all entries + proposals for a thread.

    Returns ([Entry, ...], [Proposal, ...]). Empty lists when thread directory is missing.
    Layout: `base_dir/{thread_id}/{entry_id}.md` and `base_dir/{thread_id}/proposals/{prop_id}.md`.
    """
    base = Path(base_dir) / thread_id
    if not base.exists():
        return [], []

    entries: list[Entry] = []
    proposals: list[Proposal] = []

    # Entries: *.md files (skip chat.md roll-up, skip proposals/ subdir)
    for md in sorted(base.glob("*.md")):
        if md.name == "chat.md":
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        header = _ENTRY_HEADER_RE.search(text)
        if header:
            role_str = header.group(1).strip()
            eid_in_md = header.group(2).strip()
            body = text[header.end():].strip("\n")
        else:
            role_str = "user"
            eid_in_md = md.stem
            body = text
        eid = eid_in_md or md.stem
        try:
            role = EntryRole(role_str)
        except ValueError:
            role = EntryRole.USER
        entries.append(Entry(id=eid, thread_id=thread_id, role=role, content=body))

    # Proposals: sidecar JSON in same thread dir
    sidecar = base / "chat.json"
    if sidecar.exists():
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            for pid, prop in (payload.get("proposals") or {}).items():
                try:
                    kwargs = {k: v for k, v in prop.items() if k in {"action", "target_ueid", "rationale", "status"}}
                    proposals.append(Proposal(id=pid, thread_id=thread_id, **kwargs))
                except Exception:
                    continue
        except Exception:
            pass

    return entries, proposals
