#!/usr/bin/env python
"""MVP Marco CLI smoke — proves the CLI wrappers work in isolation.

Calls the SAME functions `plan-add` and `plan-list --all-forks` call:
  - do_task_add (writes CliAdapter slice + enqueues TaskChange)
  - show_mesh (reads cross-fork view from all 3 adapters)

Combined with `scripts/smoke/mvp_marco.py` (which tests the adapter
chain directly), this proves the CLI commands work end-to-end.

Isolated: uses tmp_path for all data; does NOT touch production data/.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))  # noqa: E402

from src.mesh import queue as queue_mod  # noqa: E402
from src.mesh.adapters import cli as cli_mod  # noqa: E402
from src.mesh.adapters import solverforge_calendar as solforge_mod  # noqa: E402
from src.mesh.adapters import taskdog as taskdog_mod  # noqa: E402
from src.mesh.review_queue_worker import run_once  # noqa: E402

# Import the same functions the CLI wraps
from interfaces.cli.read_tasks import do_task_add, show_mesh  # noqa: E402


def _setup_isolated_paths(tmp: Path) -> None:
    cli_mod.TASKS_JSONL = tmp / "tasks.jsonl"
    taskdog_mod.TASKDOG_DB = tmp / "tasks.db"
    solforge_mod.UPI_DB = tmp / "unified_planning.db"
    queue_mod.QUEUE_DIR = tmp / "review_queue"
    (tmp / "review_queue").mkdir(parents=True, exist_ok=True)


def main() -> int:
    failures: list[str] = []
    summary: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="mvp_marco_cli_smoke_"))
    print(f"[setup] isolated tmp dir: {tmp}", flush=True)

    try:
        _setup_isolated_paths(tmp)

        # 1. Mimic `plan-add "Smoke CLI test" "2026-12-31"` (positional)
        result = do_task_add(
            title="Smoke CLI test",
            due="2026-12-31",
            priority="medium",
        )
        ueid = result["ueid"]
        summary.append(f"[1] do_task_add returned ueid={ueid}")

        # 2. Drain queue (mimics worker behavior)
        from src.mesh.adapters.cli import CliAdapter
        from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter
        from src.mesh.adapters.taskdog import TaskdogAdapter

        wr = run_once([CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()])
        if wr.consumed != 1 or wr.approved != 1 or wr.partial != 0:
            failures.append(
                f"Worker drain unexpected: consumed={wr.consumed} "
                f"approved={wr.approved} partial={wr.partial}"
            )
        else:
            summary.append("[2] run_once drained 1 event ✓")

        # 3. Mimic `plan-list --all-forks` — call show_mesh (the same function)
        mesh = show_mesh(ueid)
        view = mesh.get("view", {})
        cli_ok = bool(view.get("cli"))
        td_ok = bool(view.get("taskdog"))
        sf_ok = bool(view.get("solverforge_calendar"))
        summary.append(
            f"[3] show_mesh returned 3-fork view: "
            f"cli={'OK' if cli_ok else 'MISS'} "
            f"taskdog={'OK' if td_ok else 'MISS'} "
            f"solverforge_calendar={'OK' if sf_ok else 'MISS'}"
        )
        if not (cli_ok and td_ok and sf_ok):
            failures.append(
                f"Missing fork view: cli={cli_ok} taskdog={td_ok} sf={sf_ok}"
            )

        # 4. Confirm the title is present somewhere in each fork's view
        title = "Smoke CLI test"
        for fork_name, rec in view.items():
            if isinstance(rec, dict) and title not in json.dumps(rec, default=str):
                failures.append(f"{fork_name} view missing title")

        # 5. Mimic `plan-list` (CLI fork only) — read tasks.jsonl
        tasks_path = cli_mod.TASKS_JSONL
        if tasks_path.exists():
            rows = [
                json.loads(line)
                for line in tasks_path.read_text().splitlines()
                if line.strip()
            ]
            summary.append(
                f"[4] CLI fork has {len(rows)} task(s); first ueid={rows[0].get('ueid')}"
            )

        print("\n--- MVP MARCO CLI SMOKE SUMMARY ---", flush=True)
        for line in summary:
            print(line, flush=True)
        if failures:
            print("\n--- FAILURES ---", flush=True)
            for f in failures:
                print(f"  X {f}", flush=True)
            return 1
        print("\nALL CHECKS PASSED - CLI wrappers work end-to-end", flush=True)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())