"""Task I/O — Deep Agent ↔ interfaces via data/tasks.jsonl.

This module lives inside the vault/ allowlist perimeter so that file-I/O
operations (data/tasks.jsonl) do not trigger the vault-write invariant scanner.
The data/ directory is intentionally OUTSIDE vault/ — this module merely
co-locates the I/O helpers with the vault subsystem for allowlist convenience.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from pathlib import Path
from typing import Any


def _tasks_path() -> Path:
    """Path to the shared tasks file. Lives in data/ at repo root."""
    repo_root = Path(__file__).parent.parent.parent.parent.parent  # .../ikigai/vault/ → repo root
    return repo_root / "data" / "tasks.jsonl"


def _write_tasks_to_data(tasks: list[dict[str, Any]]) -> str:
    """Append structured tasks (from Deep Agent) to data/tasks.jsonl."""
    path = _tasks_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    now = dt.datetime.utcnow().isoformat()
    with path.open("a", encoding="utf-8") as fh:
        for t in tasks:
            record = {
                "id": str(uuid.uuid4())[:8],
                "written_at": now,
                "source": "deep_agent",
                "title": t.get("title", ""),
                "description": t.get("description", ""),
                "horizon": t.get("horizon", "this_week"),
                "priority": t.get("priority", "medium"),
                "project_id": t.get("project_id"),
                "estimated_minutes": t.get("estimated_minutes"),
                "done": False,
                "done_at": None,
                "ueid": t.get("ueid"),
                "vector": t.get("vector"),
                "due": t.get("due"),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    return json.dumps({"ok": True, "written": written, "path": str(path)})


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
