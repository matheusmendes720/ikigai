"""M167: td gantt / td optimize subcommands — argparse + dispatch.

Two leaf subcommands registered under ``taskdog_cli``:

    td gantt [--mode=ascii|html|json] [--status STATUS] [--limit N]
             [--db-path PATH] [--human|--json]

        Renders a Gantt chart over the taskdog store. The mode flag
        chooses between ASCII box-drawing, an HTML table, and a JSON
        structured dump.

    td optimize [--strategy=critical_path|priority_weighted|fifo]
                [--status STATUS] [--limit N] [--db-path PATH]
                [--human|--json]

        Reorders tasks via topological sort + per-strategy weighting.
        Returns the suggested order plus per-task rationale.

Output modes:
    Default (TTY): rendered ASCII/table for human consumption.
    --json: force JSON output (works with both subcommands).

Usage:
    python -m src.mesh.taskdog_cli gantt --mode=ascii
    python -m src.mesh.taskdog_cli gantt --mode=html --out chart.html
    python -m src.mesh.taskdog_cli gantt --mode=json --json
    python -m src.mesh.taskdog_cli optimize --strategy=priority_weighted
    python -m src.mesh.taskdog_cli optimize --strategy=fifo --json

Wire-in (M167 contract):
    ``register_gantt_subparser(sub)`` adds the ``gantt`` sub-parser.
    ``register_optimize_subparser(sub)`` adds the ``optimize`` sub-parser.
    ``run_gantt_command(args)`` and ``run_optimize_command(args)`` dispatch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.gantt_engine import GanttConfig, GanttEngine
from src.mesh.optimizer import (
    OptimizeConfig,
    Optimizer,
    OptimizeStrategy,
)


# Output mode choices (closed set so argparse --help is clean).
_GANTT_MODES: tuple[str, ...] = ("ascii", "html", "json")
_OPTIMIZE_STRATEGIES: tuple[str, ...] = ("critical_path", "priority_weighted", "fifo")

# Status filter choices mirror _KNOWN_STATUSES in taskdog_cli.
_KNOWN_STATUSES: tuple[str, ...] = ("planned", "in_progress", "done", "cancelled")


# ─────────────────────────────────────────────────────────────────────
# Output-mode resolution
# ─────────────────────────────────────────────────────────────────────


def _wants_human(args: argparse.Namespace) -> bool:
    """Resolve output mode: --json wins, else --human wins, else TTY default."""
    if getattr(args, "json", False):
        return False
    if getattr(args, "human", False):
        return True
    return sys.stdout.isatty()


def _apply_db_override(db_path_str: str) -> None:
    """Mutate module-level TASKDOG_DB to honor --db-path override.

    Mirrors the same helper used by td_tag.py / taskdog_cli.py — keeps
    test fixtures isolated (tests monkeypatch TASKDOG_DB on both the
    src.* and bare-namespace identities).
    """
    if str(taskdog_mod.TASKDOG_DB) != db_path_str:
        taskdog_mod.TASKDOG_DB = Path(db_path_str)


def _load_tasks(
    status_filter: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    """Read tasks from the canonical adapter and apply optional filters."""
    tasks = TaskdogAdapter().list_all()
    if status_filter is not None:
        tasks = [t for t in tasks if str(t.get("status") or "") == status_filter]
    if limit is not None and limit > 0:
        tasks = tasks[:limit]
    return tasks


# ─────────────────────────────────────────────────────────────────────
# gantt command
# ─────────────────────────────────────────────────────────────────────


def cmd_gantt(args: argparse.Namespace) -> int:
    """Render a Gantt chart in the requested mode."""
    _apply_db_override(args.db_path)
    tasks = _load_tasks(getattr(args, "status", None), getattr(args, "limit", None))

    # Always sort by planned_start for the chart (the engine also sorts,
    # but pre-sorting keeps JSON output deterministic for snapshot tests).
    tasks.sort(key=lambda t: (str(t.get("planned_start") or "9999"), str(t.get("ueid") or "")))

    cfg = GanttConfig(
        mode=args.mode,
        title=str(getattr(args, "title", "Taskdog Gantt") or "Taskdog Gantt"),
    )
    out = GanttEngine(tasks).render(cfg)

    # --out writes to file; default writes to stdout.
    out_path = getattr(args, "out", None)
    if out_path:
        Path(out_path).write_text(out, encoding="utf-8")
        # Echo a one-liner so the operator sees the write succeeded.
        if _wants_human(args):
            print(f"wrote {len(out)} chars to {out_path}", flush=True)
        else:
            print(
                json.dumps(
                    {"wrote": out_path, "chars": len(out), "tasks": len(tasks)},
                    sort_keys=True,
                ),
                flush=True,
            )
        return 0

    print(out, flush=True)
    return 0


# ─────────────────────────────────────────────────────────────────────
# optimize command
# ─────────────────────────────────────────────────────────────────────


def cmd_optimize(args: argparse.Namespace) -> int:
    """Reorder tasks via the chosen strategy."""
    _apply_db_override(args.db_path)
    tasks = _load_tasks(getattr(args, "status", None), getattr(args, "limit", None))

    try:
        strategy = OptimizeStrategy(args.strategy)
    except ValueError:
        print(f"error: unknown strategy {args.strategy!r}", file=sys.stderr)
        return 2

    cfg = OptimizeConfig(strategy=strategy)
    result = Optimizer(tasks).optimize(cfg)

    if _wants_human(args):
        if result.has_cycle:
            print(
                f"cycle detected ({len(result.cycle_edges)} back-edges); "
                "cannot optimize.",
                flush=True,
            )
            for src, dst in result.cycle_edges:
                print(f"  cycle edge: {src} -> {dst}", flush=True)
            return 1
        print(
            f"strategy={result.strategy.value}  "
            f"tasks={result.metrics.get('task_count', 0)}  "
            f"deps={result.metrics.get('dep_edge_count', 0)}",
            flush=True,
        )
        # Render a compact table of position / ueid / weight / rationale.
        for row in result.ordered:
            print(
                f"{row.position:>3}  {row.ueid}  w={row.weight:>5g}  "
                f"{row.rationale}",
                flush=True,
            )
        return 0

    # JSON mode — emit the canonical serialized result.
    print(result.to_json(), flush=True)
    return 0 if not result.has_cycle else 1


# ─────────────────────────────────────────────────────────────────────
# Parser wiring
# ─────────────────────────────────────────────────────────────────────


def _add_db_path(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--db-path",
        type=str,
        default=str(taskdog_mod.TASKDOG_DB),
        help="path to taskdog SQLite DB (default: production DB)",
    )


def _add_output_flags(p: argparse.ArgumentParser) -> None:
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--json", action="store_true", help="force JSON output")
    grp.add_argument("--human", action="store_true", help="force human-readable output")


def register_gantt_subparser(
    sub: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Attach the ``gantt`` sub-parser and return it."""
    gantt_p = sub.add_parser(
        "gantt",
        help="visualize tasks as ASCII/HTML/JSON gantt (M167)",
        description=(
            "Render a Gantt chart of taskdog tasks. The --mode flag "
            "selects the output: ascii (box-drawing chart), html (table), "
            "or json (structured data)."
        ),
    )
    gantt_p.add_argument(
        "--mode",
        choices=_GANTT_MODES,
        default="ascii",
        help="output mode (default: ascii)",
    )
    gantt_p.add_argument(
        "--status",
        choices=_KNOWN_STATUSES,
        default=None,
        help="filter by status (default: all)",
    )
    gantt_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max tasks to include (default: unlimited)",
    )
    gantt_p.add_argument(
        "--title",
        default="Taskdog Gantt",
        help="chart title (printed in HTML/JSON modes)",
    )
    gantt_p.add_argument(
        "--out",
        default=None,
        help="write rendered output to this file (default: stdout)",
    )
    _add_db_path(gantt_p)
    _add_output_flags(gantt_p)
    return gantt_p


def register_optimize_subparser(
    sub: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Attach the ``optimize`` sub-parser and return it."""
    opt_p = sub.add_parser(
        "optimize",
        help="suggest task reorder via topological sort (M167)",
        description=(
            "Reorder tasks using a topological sort. Strategy selects "
            "the weighting: critical_path (longest path first), "
            "priority_weighted (priority × blocker_count), or fifo."
        ),
    )
    opt_p.add_argument(
        "--strategy",
        choices=_OPTIMIZE_STRATEGIES,
        default="priority_weighted",
        help="optimization strategy (default: priority_weighted)",
    )
    opt_p.add_argument(
        "--status",
        choices=_KNOWN_STATUSES,
        default=None,
        help="filter by status (default: all)",
    )
    opt_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max tasks to include (default: unlimited)",
    )
    _add_db_path(opt_p)
    _add_output_flags(opt_p)
    return opt_p


def run_gantt_command(args: argparse.Namespace) -> int:
    """Single-dispatch entry point for ``td gantt``."""
    return cmd_gantt(args)


def run_optimize_command(args: argparse.Namespace) -> int:
    """Single-dispatch entry point for ``td optimize``."""
    return cmd_optimize(args)


__all__ = [
    "register_gantt_subparser",
    "register_optimize_subparser",
    "run_gantt_command",
    "run_optimize_command",
    "cmd_gantt",
    "cmd_optimize",
]
