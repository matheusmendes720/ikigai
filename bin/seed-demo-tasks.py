"""R1.6: Bootstrap the TUI Tasks tab with 3 demo tasks on first run.

Writes 3 example tasks via CliAdapter.apply_change so the Tasks tab is
populated when the TUI is opened on a fresh install. Idempotent: if a
demo task's UEID already exists in data/tasks.jsonl, CliAdapter skips
the write (per R1.1 dedup logic).

Tasks seeded:
  1. "Welcome to your Tasks tab" — todo, low priority
  2. "Review the Life OS architecture" — in_progress, medium priority
  3. "Set up your first dream SONHO" — done, high priority

Usage:
    python bin/seed-demo-tasks.py
    python bin/seed-demo-tasks.py --force   # overwrite (rare; CI/dev only)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Repo root = parent of bin/
REPO_ROOT = Path(__file__).resolve().parent.parent

# Add repo root AND src/ to sys.path. Both are needed because the codebase
# uses two import styles:
#   - `from src.contracts.X import ...`  → resolves via <repo>/
#   - `from contracts.X import ...`      → resolves via <repo>/src/
# Adding both is the same pattern tests/conftest.py uses (see CLAUDE.md
# "Dual-module identity bug class" — patching one without the other
# silently no-ops).
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from src.contracts.common import UEID  # noqa: E402
from src.contracts.task_change import PropagationEvent, TaskAction  # noqa: E402
from src.mesh.adapters.cli import CliAdapter  # noqa: E402


def _stable_ueid(slug: str, idx: int) -> UEID:
    """Build a deterministic UEID for a demo task.

    Format: tsk:<slug>:<uuid_with_idx>:<sha256(slug)[:16]>
    The hash segment is hex-only (matches UEID regex `[a-f0-9]{4,8}`)
    and is stable per slug, so re-running this script dedups on UEID.
    """
    # Index ensures distinct UUIDs even if two slugs collide.
    uuid_segment = f"{idx:08d}-0000-0000-0000-000000000000"
    hash_segment = hashlib.sha256(slug.encode()).hexdigest()[:16]
    return UEID(f"tsk:{slug}:{uuid_segment}:{hash_segment}")


# Demo tasks — UEIDs are deterministic so re-running is idempotent.
_DEMO_TASKS = [
    {
        "slug": "welcome-tasks-tab",
        "fields": {
            "title": "Welcome to your Tasks tab",
            "description": (
                "This is a demo task. Open the TUI and press 'd' to mark it done. "
                "Delete me when you're ready to use the system for real."
            ),
            "priority": "low",
            "horizon": "today",
            "done": False,
        },
    },
    {
        "slug": "review-life-os-arch",
        "fields": {
            "title": "Review the Life OS architecture",
            "description": (
                "Skim CLAUDE.md at the repo root to understand the 3-layer "
                "architecture (Interface / Agent / Data)."
            ),
            "priority": "medium",
            "horizon": "this_week",
            "done": False,
        },
    },
    {
        "slug": "set-up-first-sonho",
        "fields": {
            "title": "Set up your first dream SONHO",
            "description": (
                "SONHO = Strategic Objective, Nested Hierarchy, Outcome. "
                "Start with one dream and decompose it into metas → "
                "objetivos → projetos → entregas → tarefas."
            ),
            "priority": "high",
            "horizon": "this_month",
            "done": True,
            "done_at": datetime.now(timezone.utc).date().isoformat(),
        },
    },
]

# Pre-build UEIDs so the script is introspectable.
for _idx, _task in enumerate(_DEMO_TASKS, start=1):
    _task["ueid"] = _stable_ueid(_task["slug"], _idx)


def seed(force: bool = False) -> dict[str, list[str]]:
    """Seed demo tasks via CliAdapter.apply_change.

    Returns a dict with `created` and `skipped` UEID lists.
    Idempotent: CliAdapter dedups on UEID match (R1.1).
    """
    adapter = CliAdapter()
    created: list[str] = []
    skipped: list[str] = []

    for task in _DEMO_TASKS:
        ueid = task["ueid"]
        if not force and adapter.read(ueid) is not None:
            skipped.append(str(ueid))
            continue

        event = PropagationEvent(
            event_id=f"seed_{uuid.uuid4().hex[:12]}",
            ueid=ueid,
            action=TaskAction.CREATE,
            fields=task["fields"],
            approved_at=datetime.now(timezone.utc),
            source_fork="bin/seed-demo-tasks",
        )
        adapter.apply_change(event)
        created.append(str(ueid))

    return {"created": created, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass dedup; overwrite existing demo tasks (rare).",
    )
    args = parser.parse_args()

    result = seed(force=args.force)
    n_created = len(result["created"])
    n_skipped = len(result["skipped"])

    if n_created == 0 and n_skipped == len(_DEMO_TASKS):
        print(f"[seed-demo-tasks] All {n_skipped} demo tasks already exist. Skipping.")
    else:
        print(
            f"[seed-demo-tasks] Created {n_created} tasks, "
            f"skipped {n_skipped} (already present)."
        )
        for ueid in result["created"]:
            print(f"  + {ueid}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())