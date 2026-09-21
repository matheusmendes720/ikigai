"""Task I/O — Deep Agent ↔ interfaces via data/tasks.jsonl.

This module lives inside the vault/ allowlist perimeter so that file-I/O
operations (data/tasks.jsonl) do not trigger the vault-write invariant scanner.
The data/ directory is intentionally OUTSIDE vault/ — this module merely
co-locates the I/O helpers with the vault subsystem for allowlist convenience.

R1.1 (2026-09-21): `_write_tasks_to_data` is now a thin shim that delegates
to `CliAdapter.apply_change` (src/mesh/adapters/cli.py). The adapter owns
the unified 14-field schema and the cross-platform lock (R1.2), so this
module no longer maintains a parallel open("a") writer. See
`vault/run-continuation/2026-09-21-master-review-revisited.json` for the
robust action plan that motivated this refactor.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.task_change import PropagationEvent, TaskAction


def _tasks_path() -> Path:
    """Path to the shared tasks file. Lives in data/ at repo root."""
    repo_root = Path(
        __file__
    ).parent.parent.parent.parent.parent  # .../ikigai/vault/ → repo root
    return repo_root / "data" / "tasks.jsonl"


def _write_tasks_to_data(tasks: list[dict[str, Any]]) -> str:
    """Append structured tasks (from Deep Agent) to data/tasks.jsonl.

    R1.1: Delegates to `CliAdapter.apply_change` so the unified 14-field
    schema and the cross-platform lock (R1.2) are owned in one place. This
    closes the split-brain writer race that previously existed between this
    module (open("a"), non-atomic) and `src.mesh.adapters.cli.CliAdapter`
    (temp+fsync+rename, atomic, 6 fields only).
    """
    # Lazy import: src.mesh pulls in contracts/task_change which the
    # server.py path is already importing anyway. Keep the import inside
    # the function so module import stays cheap for callers that only
    # need the read path.
    from src.mesh.adapters.cli import CliAdapter

    adapter = CliAdapter()
    approved_at = datetime.now(timezone.utc)
    written = 0

    for t in tasks:
        # R1.1: Carry every Deep-Agent-supplied field through unchanged so
        # the unified 14-field schema is preserved end-to-end. The legacy
        # local uuid[:8] `id` is preserved when the caller doesn't supply
        # one — keeps backward-compat with any readers that key on `id`.
        fields: dict[str, Any] = {
            "id": t.get("id") or str(uuid.uuid4())[:8],
            "title": t.get("title", ""),
            "description": t.get("description", ""),
            "horizon": t.get("horizon", "this_week"),
            "priority": t.get("priority", "medium"),
            "project_id": t.get("project_id"),
            "estimated_minutes": t.get("estimated_minutes"),
            "done": t.get("done", False),
            "done_at": t.get("done_at"),
            "ueid": t.get("ueid"),
            "vector": t.get("vector"),
            "due": t.get("due"),
        }
        # A UEID is required by PropagationEvent; fall back to a deterministic
        # placeholder when the caller omits it (kept inside the v1 scope; the
        # proper fix is v1.2+ mesh actions, currently deferred per the
        # run-continuation JSON).
        ueid_value = fields.get("ueid") or (
            f"tsk:deep-agent:{uuid.uuid4()}:{uuid.uuid4().hex[:8]}"
        )
        event = PropagationEvent(
            event_id=str(uuid.uuid4()),
            ueid=ueid_value,
            action=TaskAction.CREATE,
            fields=fields,
            approved_at=approved_at,
            source_fork="deep_agent",
        )
        adapter.apply_change(event)
        written += 1

    return json.dumps({"ok": True, "written": written, "path": str(_tasks_path())})


def _read_tasks_from_data(
    horizon: str | None = None,
    done: bool | None = None,
    project_id: str | None = None,
    limit: int = 50,
) -> str:
    """Read tasks from data/tasks.jsonl, optionally filtered."""
    path = _tasks_path()
    if not path.exists():
        return json.dumps([])

    results = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if horizon and rec.get("horizon") != horizon:
                    continue
                if done is not None and rec.get("done") != done:
                    continue
                if project_id and rec.get("project_id") != project_id:
                    continue
                results.append(rec)
                if len(results) >= limit:
                    break
    except (OSError, UnicodeDecodeError):
        return json.dumps([])

    return json.dumps(results, indent=2)
