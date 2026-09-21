"""Chat file writer — Atomic Pydantic-to-disk (ADR-012 via tmp+rename).

Routes through atomic write so drift detection can audit writer.py the same
way it audits vault_write. Layout: `base_dir/{thread_id}/{entry.id}.md` and
`base_dir/{thread_id}/proposals/{proposal.id}.md` per tests/test_chat_system.py.

Dual-signature style (kept for back-compat with `scripts/chat_repl.py` and any
a5b1146c-era callers):
  - New style:   write_entry(entry, base_dir=Path)
  - Legacy 3-arg: write_entry(vault_root, thread_id, entry)
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _atomic_write_text(target: Path, content: str) -> None:
    """Write `content` to `target` atomically (tempfile + os.replace)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    import tempfile

    fd, tmp = tempfile.mkstemp(prefix=".chat-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _detect_signature(args, kwargs):
    """Resolve to (entry, base_dir) regardless of signature style.

    New style: entry=Proposal/Entry, base_dir=Path
    Legacy:    vault_root=Path, thread_id=str, entry=Entry/dict (positional)

    Returns (entry, base_dir). Raises TypeError on ambiguity.
    """
    if "entry" in kwargs and "base_dir" in kwargs:
        # Explicit new-style kwargs
        return kwargs["entry"], kwargs.get("base_dir")
    if "base_dir" in kwargs:
        # New-style with pos entry
        if len(args) < 1:
            raise TypeError("write_entry: missing entry (positional)")
        return args[0], kwargs["base_dir"]
    # Legacy positional: write_entry(vault_root, thread_id, entry)
    if len(args) == 3 and "vault_root" not in kwargs and "thread_id" not in kwargs:
        vault_root, thread_id, entry = args
        base_dir = Path(vault_root) / "ikigai" / "runtime" / "chat" / thread_id
        return entry, base_dir
    if len(args) == 2 and "vault_root" in kwargs:
        vault_root = kwargs["vault_root"]
        thread_id = args[0]
        entry = args[1]
        base_dir = Path(vault_root) / "ikigai" / "runtime" / "chat" / thread_id
        return entry, base_dir
    raise TypeError(
        "write_entry: cannot resolve entry/base_dir. "
        "Use new style (entry, base_dir=...) or legacy (vault_root, thread_id, entry)."
    )


def write_entry(*args, **kwargs):
    """Persist a chat entry. See module docstring for signature styles."""
    entry, base_dir = _detect_signature(args, kwargs)
    if base_dir is None:
        raise TypeError(
            "write_entry: base_dir is required (new API) or vault_root+thread_id (legacy)"
        )
    if hasattr(entry, "model_dump"):
        d = entry.model_dump()
    elif isinstance(entry, dict):
        d = entry
    else:
        raise TypeError(f"write_entry: unsupported entry type {type(entry)!r}")

    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)

    # Normalize the layout: tests expect base/{thread_id}/{entry.id}.md,
    # but legacy callers passed a flat dict so thread_id may not be set.
    if "thread_id" not in d and base.name.startswith("thr-"):
        # base was already the thread subdir; treat stem as thread_id
        d = {**d, "thread_id": base.name}

    eid = d.get("id", "unknown")
    role = str(d.get("role", d.get("actor", "user")))
    content = d.get("content", "")
    thread_id = d.get("thread_id") or "_"

    # If base_dir is the chat root (not the thread subdir), nest under thread_id.
    target_base = base if (base.name == thread_id or base.name == eid) else (base / thread_id)
    target_base.mkdir(parents=True, exist_ok=True)
    target = target_base / f"{eid}.md"

    md = f"\n## [{role}] {eid}\n\n{content}\n"
    _atomic_write_text(target, md)
    return target


def write_proposal(*args, **kwargs):
    """Persist a Proposal. Same dual-signature style as write_entry."""
    # Same resolver
    if "proposal" in kwargs and "base_dir" in kwargs:
        proposal, base_dir = kwargs["proposal"], kwargs.get("base_dir")
    elif "base_dir" in kwargs:
        if len(args) < 1:
            raise TypeError("write_proposal: missing proposal (positional)")
        proposal, base_dir = args[0], kwargs["base_dir"]
    elif len(args) == 3 and "vault_root" not in kwargs and "thread_id" not in kwargs:
        vault_root, thread_id, proposal = args
        base_dir = Path(vault_root) / "ikigai" / "runtime" / "chat" / thread_id
    elif len(args) == 2 and "vault_root" in kwargs:
        vault_root = kwargs["vault_root"]
        thread_id = args[0]
        proposal = args[1]
        base_dir = Path(vault_root) / "ikigai" / "runtime" / "chat" / thread_id
    else:
        raise TypeError(
            "write_proposal: cannot resolve proposal/base_dir. "
            "Use new style (proposal, base_dir=...) or legacy (vault_root, thread_id, proposal)."
        )

    if base_dir is None:
        raise TypeError("write_proposal: base_dir is required")

    if hasattr(proposal, "model_dump"):
        try:
            d = proposal.model_dump(mode="json")
        except (TypeError, ValueError):
            d = proposal.model_dump()
    elif isinstance(proposal, dict):
        d = proposal
    else:
        raise TypeError(f"write_proposal: unsupported proposal type {type(proposal)!r}")

    thread_id = d.get("thread_id") or "_"
    pid = d.get("id") or d.get("proposal_id", "unknown")

    base = Path(base_dir) if not (Path(base_dir).name == thread_id) else Path(base_dir).parent
    base.mkdir(parents=True, exist_ok=True)
    proposals_dir = base / thread_id / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    target = proposals_dir / f"{pid}.md"

    md = f"\n# Proposal {pid}\n\n"
    md += f"- **action**: {d.get('action', '?')}\n"
    md += f"- **target_ueid**: {d.get('target_ueid', '?')}\n"
    md += f"- **rationale**: {d.get('rationale', '?')}\n"
    _atomic_write_text(target, md)

    # Sidecar JSON at base/{thread_id}/chat.json so read_thread can enumerate
    sidecar = base / thread_id / "chat.json"
    payload = {"proposals": {}}
    if sidecar.exists():
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or "proposals" not in payload:
                payload = {"proposals": {}}
        except Exception:
            payload = {"proposals": {}}
    payload.setdefault("proposals", {})[pid] = dict(d.items())
    _atomic_write_text(sidecar, json.dumps(payload, indent=2, default=str))
    return target
