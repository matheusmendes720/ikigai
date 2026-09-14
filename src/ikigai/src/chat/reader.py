"""Reader — pull chat thread contents back from vault.

`read_thread(thread_id)` returns a sorted list of all Entry objects in a
thread plus all Proposal objects attached to that thread.

Proposals are returned as a separate list (the caller chooses whether to
interleave them with entries by `created_at`). The order within each list
is by `created_at` ascending, then by `id` (lexicographic) as a tiebreaker.

Missing thread directories are NOT an error: `read_thread` returns two
empty lists. The TUI/CLI consumer decides how to render an empty thread
("No messages yet.").
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .schema import CHAT_RUNTIME_DIR, Entry, EntryRole, Proposal, ProposalStatus

# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse a markdown file into (frontmatter_dict, body).

    Returns ({}, text) when no frontmatter block is present.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    fm: dict[str, str] = {}
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Handle simple `key: value` (no nested structures)
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm, body


def _coerce_dt(value: str) -> Any:
    """Best-effort parse of an ISO-8601 timestamp.

    Falls back to a sentinel (now-UTC) on parse failure — chat history
    should never crash the reader because of a malformed timestamp.
    """
    from datetime import datetime, timezone

    try:
        # Allow trailing Z → +00:00
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_thread(
    thread_id: str,
    *,
    base_dir: Path | None = None,
) -> tuple[list[Entry], list[Proposal]]:
    """Read all entries and proposals for a thread.

    Returns:
        (entries, proposals) — both sorted by (created_at, id) ascending.

    A non-existent thread is *not* an error: returns ([], []). Callers
    decide whether to render an empty state.

    Args:
        thread_id: Thread identifier (matches `Entry.thread_id`).
        base_dir: Override the runtime root. Tests use this to isolate to tmp.
    """
    root = base_dir if base_dir is not None else CHAT_RUNTIME_DIR
    thread_dir = root / thread_id
    proposals_dir = thread_dir / "proposals"

    entries: list[Entry] = []
    if thread_dir.is_dir():
        for path in sorted(thread_dir.glob("*.md")):
            # Skip the proposals/ subdir if glob somehow surfaces it
            if path.parent.name == "proposals":
                continue
            text = path.read_text(encoding="utf-8")
            fm, body = _parse_frontmatter(text)
            entries.append(
                Entry(
                    id=fm.get("id", path.stem),
                    thread_id=fm.get("thread_id", thread_id),
                    role=EntryRole(fm.get("role", "user")),
                    content=body.strip(),
                    created_at=_coerce_dt(fm.get("created_at", "")),
                )
            )

    proposals: list[Proposal] = []
    if proposals_dir.is_dir():
        for path in sorted(proposals_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            fm, body = _parse_frontmatter(text)
            proposals.append(
                Proposal(
                    id=fm.get("id", path.stem),
                    thread_id=fm.get("thread_id", thread_id),
                    action=fm.get("action", ""),
                    target_ueid=fm.get("target_ueid", ""),
                    rationale=body.strip(),
                    status=ProposalStatus(fm.get("status", "open")),
                    created_at=_coerce_dt(fm.get("created_at", "")),
                )
            )

    entries.sort(key=lambda e: (e.created_at, e.id))
    proposals.sort(key=lambda p: (p.created_at, p.id))

    return entries, proposals


__all__ = ["read_thread"]