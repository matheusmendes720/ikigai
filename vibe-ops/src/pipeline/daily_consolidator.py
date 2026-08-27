"""Daily Consolidator — bridges vault planning cycles → data/tasks.jsonl.

Consumes:
  - Vault planning state (vault/ikigai/closing-2026/)
  - IkigaiScorer vector scores (for priority/vector assignment)
  - Optional: explicit cycle state from data/cycle_state.json

Produces:
  - data/tasks.jsonl  (one JSON per line, matching _write_tasks_to_data schema)
  - data/sync_log.jsonl  (audit trail of consolidations)

Schema (matching _write_tasks_to_data in server.py):
  id, written_at, source, title, description, horizon, priority,
  project_id, estimated_minutes, done, done_at, ueid, vector, due
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from pipeline.ikigai_scorer import IkigaiScorer


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    return Path(__file__).parent.parent.parent.parent  # .../vibe-ops/ → life/


# Primary vault: life-ops/ikigai/data/matheus/ (Matheus Mendes persona)
# Secondary fallback: vault/ikigai/closing-2026/ (Q3/Q4 planning dirs)
def _vault_path() -> Path:
    primary = _repo_root() / "life-ops" / "ikigai" / "data" / "matheus"
    if primary.exists():
        return primary
    return _repo_root() / "vault" / "ikigai" / "closing-2026"


def _tasks_path() -> Path:
    return _repo_root() / "data" / "tasks.jsonl"


def _sync_log_path() -> Path:
    return _repo_root() / "data" / "sync_log.jsonl"


def _cycle_state_path() -> Path:
    return _repo_root() / "data" / "cycle_state.json"


# ---------------------------------------------------------------------------
# Task schema (mirrors _write_tasks_to_data in server.py)
# ---------------------------------------------------------------------------

_TASK_SCHEMA_KEYS = [
    "id", "written_at", "source", "title", "description",
    "horizon", "priority", "project_id", "estimated_minutes",
    "done", "done_at", "ueid", "vector", "due",
]

# Horizon constants
HORIZON_TODAY = "today"
HORIZON_THIS_WEEK = "this_week"
HORIZON_ONDA = "onda"
HORIZON_SPRINT = "sprint"
HORIZON_TRIMESTER = "trimestre"

# Default IKIGAI vectors (from PRD-07)
IKIGAI_VECTORS = ["passion", "skill", "market", "revenue"]


def _make_task(
    title: str,
    description: str = "",
    horizon: str = HORIZON_THIS_WEEK,
    priority: str = "medium",
    project_id: str | None = None,
    estimated_minutes: int | None = None,
    ueid: str | None = None,
    vector: str | None = None,
    due: str | None = None,
    source: str = "consolidator",
) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    return {
        "id": str(uuid.uuid4())[:8],
        "written_at": now,
        "source": source,
        "title": title,
        "description": description,
        "horizon": horizon,
        "priority": priority,
        "project_id": project_id,
        "estimated_minutes": estimated_minutes,
        "done": False,
        "done_at": None,
        "ueid": ueid,
        "vector": vector,
        "due": due,
    }


def _write_tasks(tasks: list[dict[str, Any]]) -> int:
    """Append tasks to data/tasks.jsonl. Returns count written."""
    path = _tasks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("a", encoding="utf-8") as fh:
        for t in tasks:
            record = {k: t.get(k) for k in _TASK_SCHEMA_KEYS}
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    return written


def _log_sync(action: str, count: int, details: dict[str, Any] | None = None) -> None:
    """Append to data/sync_log.jsonl."""
    path = _sync_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "count": count,
        "details": details or {},
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Bootstrap tasks — generate initial tasks from Q3/Q4 planning dirs
# ---------------------------------------------------------------------------

def _scan_vault_dirs() -> list[dict[str, Any]]:
    """Scan the vault for .md files with IKIGAI frontmatter.

    Supports two vault layouts:
      1. Flat matheus vault (life-ops/ikigai/data/matheus/):
         dreams/, objectives/, projects/, deliverables/, ikigai_state/
         — each file has entity_type, ueid, status, horizon_days in frontmatter
      2. Closing-2026 vault (vault/ikigai/closing-2026/):
         01-q3-2026/, 02-q4-2026/ with quadrant subdirs

    Returns a list of task dicts.
    """
    tasks: list[dict[str, Any]] = []
    root = _vault_path()
    if not root.exists():
        return tasks

    # matheus vault: flat subdirs (dreams, objectives, projects, deliverables)
    matheus_dirs = ["dreams", "objectives", "projects", "deliverables"]
    is_matheus = any((root / d).exists() for d in matheus_dirs)

    if is_matheus:
        for subdir in matheus_dirs:
            dir_path = root / subdir
            if not dir_path.exists():
                continue
            for md_file in dir_path.rglob("*.md"):
                if md_file.stem in ("README",):
                    continue
                task = _parse_matheus_md(md_file)
                if task is not None:
                    tasks.append(task)
    else:
        # closing-2026 layout
        for quadrant in ["01-q3-2026", "02-q4-2026"]:
            qpath = root / quadrant
            if not qpath.exists():
                continue
            for md_file in qpath.rglob("*.md"):
                if md_file.stem in ("index", "00-index", "README", "placeholder"):
                    continue
                task = _parse_closing_md(md_file)
                if task is not None:
                    tasks.append(task)

    return tasks


def _parse_matheus_md(md_file: Path) -> dict[str, Any] | None:
    """Parse a single .md file from the matheus vault."""
    try:
        content = md_file.read_text(encoding="utf-8")
    except OSError:
        return None

    front, body = _extract_frontmatter(content)
    status = front.get("status", "")
    if status in ("done", "completed", "cancelled", "ARCHIVED"):
        return None

    entity_type = front.get("entity_type", "")
    slug = front.get("slug", md_file.stem)
    title = front.get("title", slug.replace("-", " ").replace("_", " ").title())

    # Map entity_type to horizon
    horizon = _entity_to_horizon(entity_type, front)

    # Vectors from frontmatter (comma-separated or YAML list)
    vectors_raw = front.get("ikigai_vectors", "")
    if isinstance(vectors_raw, str):
        vectors = [v.strip() for v in vectors_raw.strip("[]").split(",")]
        vector = vectors[0] if vectors else None
    elif isinstance(vectors_raw, list):
        vector = vectors_raw[0] if vectors_raw else None
    else:
        vector = None

    # Description: first non-frontmatter paragraph
    description = ""
    if body:
        desc_lines = [l.strip() for l in body if l.strip() and not l.strip().startswith("#")]
        description = " ".join(desc_lines[:2])[:300]

    return _make_task(
        title=title,
        description=description,
        horizon=horizon,
        priority="medium",
        project_id=front.get("parent_ueid"),
        vector=vector,
        due=front.get("due"),
        ueid=front.get("ueid"),
        source="vault_matheus",
    )


def _entity_to_horizon(entity_type: str, front: dict[str, Any]) -> str:
    """Map IKIGAI entity_type to horizon string."""
    horizon_days = int(front.get("horizon_days", 0)) if front.get("horizon_days") else 0
    entity = entity_type.lower()

    if entity in ("dream", "sonho"):
        return "trimestre"  # ~547d → coarse horizon
    elif entity == "objective":
        return "trimestre"  # 90d
    elif entity == "project":
        if horizon_days and horizon_days <= 30:
            return "onda"
        return "sprint"
    elif entity == "deliverable":
        return "this_week"
    else:
        return "this_week"


def _parse_closing_md(md_file: Path) -> dict[str, Any] | None:
    """Parse a single .md file from the closing-2026 vault layout."""
    try:
        content = md_file.read_text(encoding="utf-8")
    except OSError:
        return None

    front, body = _extract_frontmatter(content)
    status = front.get("status", "")
    if status in ("done", "completed", "cancelled"):
        return None

    title = front.get("title", md_file.stem.replace("-", " ").replace("_", " ").title())
    horizon = front.get("horizon", HORIZON_THIS_WEEK)
    priority = front.get("priority", "medium")
    vector = front.get("vector", None)
    project_id = front.get("project", front.get("project_id", None))
    due = front.get("due", None)

    description = ""
    if body:
        desc_lines = [l.strip() for l in body if l.strip() and not l.strip().startswith("#")]
        description = " ".join(desc_lines[:2])[:300]

    return _make_task(
        title=title,
        description=description,
        horizon=horizon,
        priority=priority,
        project_id=project_id,
        vector=vector,
        due=due,
        source="vault_closing",
    )


def _extract_frontmatter(content: str) -> tuple[dict[str, Any], list[str]]:
    """Extract YAML frontmatter and body lines from markdown."""
    front: dict[str, Any] = {}
    body_lines: list[str] = []
    in_front = False
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_front:
                in_front = True
                continue
            else:
                in_front = False
                continue
        if in_front and ":" in line:
            key, _, val = line.partition(":")
            front[key.strip()] = val.strip().strip('"').strip("'")
        elif not in_front:
            body_lines.append(line)
    return front, body_lines


# ---------------------------------------------------------------------------
# Cycle-state-driven consolidation
# ---------------------------------------------------------------------------

def _read_cycle_state() -> dict[str, Any]:
    """Read explicit cycle state from data/cycle_state.json."""
    path = _cycle_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def consolidate_from_cycle_state(cycle_state: dict[str, Any] | None = None) -> int:
    """Main entry point: produce tasks from cycle state.

    Args:
        cycle_state: explicit cycle state dict. If None, reads from data/cycle_state.json.
                     If that also doesn't exist, falls back to _scan_vault_dirs bootstrap.

    Returns:
        Number of tasks written to data/tasks.jsonl.
    """
    if cycle_state is None:
        cycle_state = _read_cycle_state()

    # Decide source of tasks
    if cycle_state and cycle_state.get("tasks"):
        source_tasks = cycle_state["tasks"]
        action = "cycle_state"
    else:
        source_tasks = _scan_vault_dirs()
        action = "vault_bootstrap"

    if not source_tasks:
        _log_sync(action, 0, {"reason": "no tasks found"})
        return 0

    written = _write_tasks(source_tasks)
    _log_sync(action, written, {
        "source": action,
        "tasks_count": len(source_tasks),
        "first_id": source_tasks[0].get("id", ""),
    })
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(dry_run: bool = False) -> None:
    """CLI entry point for daily consolidation."""
    import argparse

    parser = argparse.ArgumentParser(description="Daily task consolidator")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be written")
    parser.add_argument("--source", choices=["cycle", "vault"], default=None,
                        help="Force data source")
    args = parser.parse_args()

    # Determine source
    if args.source == "cycle":
        cs = _read_cycle_state() if _cycle_state_path().exists() else {}
        tasks = cs.get("tasks", []) if cs else _scan_vault_dirs()
        action = "cycle_state"
    elif args.source == "vault":
        tasks = _scan_vault_dirs()
        action = "vault_bootstrap"
    else:
        cs = _read_cycle_state()
        if cs and cs.get("tasks"):
            tasks = cs["tasks"]
            action = "cycle_state"
        else:
            tasks = _scan_vault_dirs()
            action = "vault_bootstrap"

    if not tasks:
        print("No tasks found to consolidate.")
        return

    print(f"Found {len(tasks)} tasks (source={action})")
    if args.dry_run:
        print(json.dumps(tasks[:3], indent=2))
        print(f"... ({len(tasks)} total)")
        return

    written = _write_tasks(tasks)
    _log_sync(action, written, {"total": len(tasks)})
    print(f"Written {written} tasks to { _tasks_path()}")


if __name__ == "__main__":
    main()
