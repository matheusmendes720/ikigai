"""Subprocess entry point for operational CLI to invoke PeriodReportSync.

Operational CLI cannot import vibe-ops directly (per plan guardrail).
This module is invoked via: python -m vibe_ops.src.cli.period_sync_cli <cmd> [args]

When invoked directly (as a script), Python only adds the script's directory
(``vibe-ops/src/cli``) to ``sys.path``. To make ``from middleware.period_sync``
work, we must prepend the parent ``vibe-ops/src`` directory.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


# Ensure vibe-ops/src is on sys.path so ``from middleware.X`` / ``from models.Y``
# resolve correctly when this file is invoked as a standalone script.
_SCRIPT_DIR = Path(__file__).resolve().parent            # vibe-ops/src/cli
_VIBE_OPS_SRC = _SCRIPT_DIR.parent                        # vibe-ops/src
if str(_VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(_VIBE_OPS_SRC))


def cmd_sync(args: argparse.Namespace) -> int:
    """Sync period reports from vault to DB."""
    from middleware.period_sync import PeriodReportSync
    vault = Path(args.vault).resolve()
    db = Path(args.db).resolve()
    sync = PeriodReportSync(vault, db, template_folder=args.folder)
    stats = sync.sync_vault_to_db()
    if args.json:
        print(json.dumps(stats.model_dump(), indent=2))
    else:
        print(f"Ingested: {stats.ingested}")
        print(f"Updated:  {stats.updated}")
        print(f"Skipped:  {stats.skipped}")
        print(f"Errors:   {stats.errors}")
        print(f"Orphans:  {stats.orphans}")
        if stats.file_errors:
            print("\nFile errors:")
            for fe in stats.file_errors:
                print(f"  {fe['path']}: {fe['error']}")
    return 0 if stats.errors == 0 else 1


def cmd_list(args: argparse.Namespace) -> int:
    """List recent period reports."""
    db = Path(args.db).resolve()
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        if args.period:
            rows = conn.execute(
                """SELECT id, period, date_start, verdict, verdict_score,
                          policy_recommendation, vault_path
                   FROM period_reports WHERE period = ?
                   ORDER BY date_start DESC LIMIT ?""",
                (args.period, args.limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, period, date_start, verdict, verdict_score,
                          policy_recommendation, vault_path
                   FROM period_reports ORDER BY date_start DESC LIMIT ?""",
                (args.limit,),
            ).fetchall()
    items = [dict(r) for r in rows]
    if args.json:
        print(json.dumps(items, indent=2))
    else:
        for item in items:
            print(
                f"{item['date_start']} | {item['period']:9} | "
                f"{item['verdict']:25} | score={item['verdict_score']:.2f} | "
                f"{item['id']}"
            )
    return 0


def cmd_hierarchy(args: argparse.Namespace) -> int:
    """Show hierarchy tree for a sonho."""
    from middleware.period_sync import PeriodReportSync
    vault = Path(args.vault).resolve()
    db = Path(args.db).resolve()
    sync = PeriodReportSync(vault, db)
    tree = sync.get_period_hierarchy(args.sonho)
    if args.json:
        print(json.dumps(tree, indent=2))
    else:
        _print_tree(tree["tree"], 0)
    return 0


def _print_tree(nodes: list, depth: int) -> None:
    for node in nodes:
        prefix = "  " * depth
        print(
            f"{prefix}- {node['id']} [{node['period']}] "
            f"verdict={node['verdict']} score={node['verdict_score']}"
        )
        _print_tree(node.get("children", []), depth + 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Period reports sync CLI")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync vault to DB")
    p_sync.add_argument("--vault", required=True)
    p_sync.add_argument("--db", required=True)
    p_sync.add_argument("--folder", default="_templates_periodos")
    p_sync.add_argument("--json", action="store_true")
    p_sync.set_defaults(func=cmd_sync)

    # list
    p_list = subparsers.add_parser("list", help="List period reports")
    p_list.add_argument("--db", required=True)
    p_list.add_argument("--period", help="Filter by period")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    # hierarchy
    p_h = subparsers.add_parser("hierarchy", help="Show hierarchy tree")
    p_h.add_argument("--vault", required=True)
    p_h.add_argument("--db", required=True)
    p_h.add_argument("--sonho", required=True)
    p_h.add_argument("--json", action="store_true")
    p_h.set_defaults(func=cmd_hierarchy)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())