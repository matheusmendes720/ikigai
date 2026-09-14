"""Writer — atomic markdown persistence for chat entries and proposals.

Layout (relative to CHAT_RUNTIME_DIR = vault/ikigai/runtime/chat/):

    {thread_id}/
        {entry_id}.md            ← chat entry (frontmatter + body)
        proposals/
            {proposal_id}.md    ← proposal (frontmatter + body)

Atomic write protocol:
    1. Compute target path
    2. mkdir -p parent
    3. Write to {target}.tmp
    4. os.replace(tmp, target)  ← atomic on POSIX and Windows (since Py 3.3)

This mirrors the protocol used by `src/mesh/queue.py` for the review queue
and `sys_ikigai/vault/vault_write.py` for vault markdown. Re-using the
same shape keeps the Drift net happy.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from .schema import CHAT_RUNTIME_DIR, Entry, Proposal

# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------


def _to_frontmatter(d: dict[str, Any]) -> str:
    """Render a flat dict as YAML frontmatter.

    Timestamps go through `.isoformat()`; everything else through `str()`.
    Single-line scalars only — multi-line content lives in the body, not
    the frontmatter.
    """
    lines = ["---"]
    for key in sorted(d.keys()):
        value = d[key]
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        else:
            value = str(value)
        # Quote values that contain YAML special chars
        if any(c in value for c in (":", "#", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`")):
            value = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _entry_to_markdown(entry: Entry) -> str:
    """Serialize an Entry to markdown frontmatter + body."""
    fm = _to_frontmatter(
        {
            "id": entry.id,
            "thread_id": entry.thread_id,
            "role": entry.role.value,
            "created_at": entry.created_at,
            "entity_type": entry.entity_type,
        }
    )
    return f"{fm}\n\n{entry.content}\n"


def _proposal_to_markdown(proposal: Proposal) -> str:
    """Serialize a Proposal to markdown frontmatter + body."""
    fm = _to_frontmatter(
        {
            "id": proposal.id,
            "thread_id": proposal.thread_id,
            "action": proposal.action,
            "target_ueid": proposal.target_ueid,
            "status": proposal.status.value,
            "created_at": proposal.created_at,
            "entity_type": proposal.entity_type,
        }
    )
    body = proposal.rationale if proposal.rationale else f"Proposal {proposal.id}"
    return f"{fm}\n\n{body}\n"


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def _atomic_write_text(target: Path, content: str) -> None:
    """Write `content` to `target` atomically.

    Uses the standard tmp-file-in-same-dir + os.replace pattern. The tmp
    file is closed before the rename so the rename is a single metadata
    op on POSIX (and on Windows since Python 3.3 — `os.replace` is
    `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING`).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except Exception:
        # Clean up tmp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_entry(entry: Entry, *, base_dir: Path | None = None) -> Path:
    """Write a chat entry to `{base_dir or CHAT_RUNTIME_DIR}/{thread_id}/{id}.md`.

    Returns the absolute path to the written file.

    Args:
        entry: Validated Entry model (frozen=True).
        base_dir: Override the runtime root. Tests use this to isolate to tmp.

    Raises:
        OSError: If the atomic write fails.
    """
    root = base_dir if base_dir is not None else CHAT_RUNTIME_DIR
    target = root / entry.thread_id / f"{entry.id}.md"
    _atomic_write_text(target, _entry_to_markdown(entry))
    return target


def write_proposal(proposal: Proposal, *, base_dir: Path | None = None) -> Path:
    """Write a proposal to `{base_dir or CHAT_RUNTIME_DIR}/{thread_id}/proposals/{id}.md`.

    Returns the absolute path to the written file.

    Args:
        proposal: Validated Proposal model (frozen=True, target_ueid already
                  validated against UEID_PATTERN by the field_validator).
        base_dir: Override the runtime root. Tests use this to isolate to tmp.

    Raises:
        OSError: If the atomic write fails.
    """
    root = base_dir if base_dir is not None else CHAT_RUNTIME_DIR
    target = root / proposal.thread_id / "proposals" / f"{proposal.id}.md"
    _atomic_write_text(target, _proposal_to_markdown(proposal))
    return target


__all__ = ["write_entry", "write_proposal"]