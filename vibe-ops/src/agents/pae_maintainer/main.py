"""PAE-Maintainer CLI entry point.

Usage:
    python -m pae_maintainer run [--once] [--dry-run] [--verbose]
    python -m pae_maintainer daemon [--interval 300] [--verbose]
    python -m pae_maintainer status
    python -m pae_maintainer balance

Source: .omo/plans/agentic-markdown-system.md T11
Linked: ADR-006 (period schema), operational constants (Q_HE + 5x3x3)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

from .state import (
    PAEState,
)
from .graph import (
    restore_from_checkpoint,
    execute_pae_maintainer_once,
    should_terminate,
)

# Default paths (configurable via env or args)
DEFAULT_DB_PATH = Path("./vibe_ops.db")


def cmd_run(args: argparse.Namespace) -> int:
    """Run one cycle."""
    if args.dry_run:
        # Dry-run: load state in-memory (or create fresh), run cycle, skip write.
        state = restore_from_checkpoint(args.cycle_id, Path(args.db))
        if state is None:
            state = PAEState(
                cycle_id=args.cycle_id,
                cycle_start=date.fromisoformat(args.start),
                cycle_end=date.fromisoformat(args.end),
            )
        from .graph import run_pae_cycle
        state = run_pae_cycle(state)
        if args.verbose:
            print("[dry-run] no checkpoint written")
    else:
        state = execute_pae_maintainer_once(
            cycle_id=args.cycle_id,
            cycle_start=date.fromisoformat(args.start),
            cycle_end=date.fromisoformat(args.end),
            db_path=Path(args.db),
        )
    if args.json:
        print(json.dumps(state.model_dump(mode="json"), indent=2))
    else:
        print(f"PAE cycle '{state.cycle_id}' completed:")
        print(f"  iteration:    {state.iteration}")
        print(f"  last_step:    {state.last_step}")
        print(f"  balancer:     {state.balancer.state.value}")
        print(f"  qhe_score:    {state.balancer.qhe_score:.2f}")
        print(f"  terminated:   {state.terminated}")
        if state.kill_switch_triggered:
            print("  KILL SWITCH:  TRIGGERED")
        if args.verbose:
            print(f"  tier:         {state.current_tier().value}")
            print(f"  cycle_start:  {state.cycle_start}")
            print(f"  cycle_end:    {state.cycle_end}")
    return 0 if not state.kill_switch_triggered else 1


def cmd_daemon(args: argparse.Namespace) -> int:
    """Run cycles in a loop."""
    print(f"PAE daemon starting (interval={args.interval}s, db={args.db})")
    try:
        while True:
            state = execute_pae_maintainer_once(
                cycle_id=args.cycle_id,
                cycle_start=date.fromisoformat(args.start),
                cycle_end=date.fromisoformat(args.end),
                db_path=Path(args.db),
            )
            print(f"[{datetime.utcnow().isoformat()}] cycle {state.iteration}: "
                  f"balancer={state.balancer.state.value} terminated={state.terminated}")
            if should_terminate(state):
                print("Terminated, exiting daemon.")
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nDaemon stopped by user.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show last persisted state."""
    state = restore_from_checkpoint(args.cycle_id, Path(args.db))
    if state is None:
        print(f"No state found for cycle_id={args.cycle_id} in {args.db}")
        return 1
    if args.json:
        print(json.dumps(state.model_dump(mode="json"), indent=2))
    else:
        print(f"Cycle: {state.cycle_id} ({state.cycle_start} to {state.cycle_end})")
        print(f"  iteration:    {state.iteration}")
        print(f"  last_step:    {state.last_step}")
        print(f"  balancer:     {state.balancer.state.value}")
        print(f"  qhe_score:    {state.balancer.qhe_score:.2f}")
        print(f"  active_nodes: {len(state.active_nodes)}")
        print(f"  terminated:   {state.terminated}")
    return 0


def cmd_balance(args: argparse.Namespace) -> int:
    """Run only the balance node and show result."""
    state = restore_from_checkpoint(args.cycle_id, Path(args.db))
    if state is None:
        print(f"No state found for cycle_id={args.cycle_id}")
        return 1
    from .nodes import balance_node
    state = balance_node(state)
    bal = state.balancer
    print(f"Balance check for cycle {state.cycle_id}:")
    print(f"  workload:    {bal.workload_estimate}h")
    print(f"  capacity:     {bal.capacity_estimate}h")
    print(f"  qhe_score:    {bal.qhe_score:.2f}")
    print(f"  state:        {bal.state.value}")
    print(f"  reason:       {bal.reason}")
    print(f"  histerese:    {bal.days_in_current_state} day(s) — "
          f"{'ACTIVE' if bal.is_histerese_active else 'pending'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PAE-Maintainer — Always-on strategic planning agent"
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # Common args shared by all subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=str(DEFAULT_DB_PATH))
    common.add_argument("--cycle-id", default="default-cycle")
    common.add_argument("--start", default=date.today().isoformat())
    common.add_argument("--end", default=date(date.today().year + 1, 12, 31).isoformat())

    # run-only flags (parent parser so they inherit cleanly)
    run_flags = argparse.ArgumentParser(add_help=False)
    run_flags.add_argument(
        "--dry-run",
        action="store_true",
        help="Run cycle in-memory only, skip DB checkpoint write.",
    )
    run_flags.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print additional diagnostic information.",
    )

    # run
    p_run = subparsers.add_parser(
        "run", parents=[common, run_flags], help="Run one cycle"
    )
    p_run.add_argument("--json", action="store_true")
    p_run.add_argument(
        "--once",
        action="store_true",
        default=True,
        help="Run exactly one cycle (default; explicit for clarity).",
    )
    p_run.set_defaults(func=cmd_run)

    # daemon
    p_daemon = subparsers.add_parser(
        "daemon", parents=[common], help="Run cycles in a loop"
    )
    p_daemon.add_argument("--interval", type=int, default=300, help="Seconds between cycles")
    p_daemon.set_defaults(func=cmd_daemon)

    # status
    p_status = subparsers.add_parser(
        "status", parents=[common], help="Show last persisted state"
    )
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    # balance
    p_balance = subparsers.add_parser(
        "balance", parents=[common], help="Show balance node output"
    )
    p_balance.set_defaults(func=cmd_balance)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())