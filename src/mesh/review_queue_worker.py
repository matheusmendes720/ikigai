"""Review queue worker: drains pending events from the filesystem queue.

This module wires together:
- queue.py: filesystem queue (enqueue/consume_pending/ack)
- agent_consumer.py: validate(event) -> ValidationResult (APPROVE/REJECT/CLARIFY)
- agent_propagator.py: propagate(event, validation, adapters) -> list[PropagationResult]

The worker operates in two modes:
1. run_once(): single drain pass (idempotent, safe to call repeatedly)
2. start_worker(): daemon mode with pidfile-based liveness (loop until SIGTERM/KeyboardInterrupt)

For cross-platform pidfile management, we inline _is_pid_alive here.
"""

from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.mesh import queue
from src.mesh.adapters.base import ForkAdapter
from src.mesh.agent_consumer import Decision, validate
from src.mesh.agent_propagator import propagate


@dataclass(frozen=True)
class RunResult:
    """Counts from a single drain pass."""

    consumed: int  # number of events processed this run
    approved: int  # approved + propagated
    rejected: int  # rejected by validation
    clarified: int  # need clarification
    partial: int  # propagated but with at least one adapter failure


def run_once(adapters: list[ForkAdapter]) -> RunResult:
    """Single drain pass: for each pending event, validate + propagate + ack.

    Returns RunResult with counts. Idempotent (safe to call repeatedly).

    Flow:
    1. consume_pending() yields events with status='pending'
    2. validate(event) returns APPROVE/REJECT/CLARIFY
    3. If APPROVE: propagate() to all adapters (handles ack on success/partial)
    4. If REJECT: ack(event_id, 'rejected')
    5. If CLARIFY: ack(event_id, 'clarify')
    """
    consumed = 0
    approved = 0
    rejected = 0
    clarified = 0
    partial = 0

    for event in queue.consume_pending():
        consumed += 1
        validation = validate(event)

        if validation.decision == Decision.APPROVE:
            # propagate() handles ack on partial failure, we ack on success
            results = propagate(event, validation, adapters)
            if results:
                # Check if any failed for partial count
                if any(not r.success for r in results):
                    partial += 1
                else:
                    # All succeeded, ack as propagated
                    queue.ack(event.event_id, "propagated")
                approved += 1
            else:
                # No results (shouldn't happen on APPROVE, but handle gracefully)
                approved += 1
        elif validation.decision == Decision.REJECT:
            queue.ack(event.event_id, "rejected")
            rejected += 1
        elif validation.decision == Decision.CLARIFY:
            queue.ack(event.event_id, "clarified")
            clarified += 1

    return RunResult(
        consumed=consumed,
        approved=approved,
        rejected=rejected,
        clarified=clarified,
        partial=partial,
    )


def start_worker(
    adapters: list[ForkAdapter],
    pidfile_path: Path,
    poll_interval: float = 1.0,
) -> None:
    """Write pidfile, then run run_once in a loop until KeyboardInterrupt.

    On exit (KeyboardInterrupt/SIGTERM), removes pidfile.

    Args:
        adapters: ForkAdapter list to propagate approved events
        pidfile_path: path to write PID (e.g. data/run/review_queue_worker.pid)
        poll_interval: seconds between poll loops
    """
    # Write pidfile
    pidfile_path.parent.mkdir(parents=True, exist_ok=True)
    pidfile_path.write_text(str(os.getpid()))

    try:
        while True:
            run_once(adapters)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup pidfile on exit
        if pidfile_path.exists():
            pidfile_path.unlink()


def stop_worker(pidfile_path: Path) -> bool:
    """Read pidfile, kill PID (cross-platform), remove pidfile.

    Returns True if killed (pidfile existed and process was alive).
    Returns False if no pidfile or process already dead (idempotent).
    """
    if not pidfile_path.exists():
        return False

    try:
        pid = int(pidfile_path.read_text().strip())
    except (ValueError, OSError):
        # Invalid content, just remove
        pidfile_path.unlink(missing_ok=True)
        return False

    # Check if alive and kill
    if _is_pid_alive(pid):
        try:
            sig = signal.SIGTERM if hasattr(signal, "SIGTERM") else signal.SIGABRT
            os.kill(pid, sig)
        except OSError:
            pass  # Process already died
        pidfile_path.unlink(missing_ok=True)
        return True
    else:
        # Stale pidfile, remove it
        pidfile_path.unlink(missing_ok=True)
        return False


def _is_pid_alive(pid: int) -> bool:
    """Cross-platform check whether pid is a running process.

    Windows: uses kernel32 OpenProcess + GetExitCodeProcess.
    POSIX: uses os.kill(pid, 0) signal-0 probe (raises if dead).
    """
    if pid <= 0:
        return False
    try:
        if os.name == "nt":  # Windows
            import ctypes

            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle == 0:
                return False
            try:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                return exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        else:  # POSIX
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def worker_status(pidfile_path: Path) -> dict[str, Any]:
    """Same shape as probe_mcp_gateway: {running: bool, pid: int|None, started_at: str|None}.

    Cross-platform probe via local _is_pid_alive.
    """
    result: dict[str, Any] = {
        "running": False,
        "pid": None,
        "started_at": None,
    }

    if not pidfile_path.exists():
        return result

    try:
        pid = int(pidfile_path.read_text().strip())
    except (ValueError, OSError):
        return result

    # Capture pidfile mtime as started_at
    result["started_at"] = str(pidfile_path.stat().st_mtime)

    if _is_pid_alive(pid):
        result["running"] = True
        result["pid"] = pid

    return result


# Graceful exit helper for SIGTERM
# On Windows, signal.SIGTERM doesn't exist, so we catch KeyboardInterrupt only
_SIGTERM_AVAILABLE = hasattr(signal, "SIGTERM")


__all__ = ["RunResult", "run_once", "start_worker", "stop_worker", "worker_status"]


# === CLI entrypoint (B2: enables `python -m src.mesh.review_queue_worker {start,stop,run-once}`) ===

DEFAULT_PIDFILE = (
    Path(__file__).resolve().parents[2] / "data" / "run" / "review_queue_worker.pid"
)


def _build_adapters() -> list[ForkAdapter]:
    """Default adapter list for the worker (same as `interfaces/cli/server.py` registry)."""
    # Lazy imports — these paths need the worktree root on sys.path.
    # `python -m src.mesh.review_queue_worker run-once` should be invoked
    # with PYTHONPATH=<worktree>;<worktree>/src set, or from the worktree
    # root directory. The CLI wrapper in interfaces/cli/ handles this.
    from mesh.adapters import CliAdapter, TaskdogAdapter
    from mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter

    return [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]


# === B5 fix 2026-09-10: CLI entrypoint path fix ===
#
# When invoked as `python -m src.mesh.review_queue_worker ...`, the
# worker's import of `mesh.X` (bare namespace, no `src.` prefix)
# requires the worktree ROOT on sys.path. Python's runpy puts the
# current dir on sys.path by default, which is <worktree>/src/mesh/ —
# wrong. This helper bootstraps sys.path before any mesh imports happen.
def _bootstrap_sys_path() -> None:
    """Ensure worktree root and src/ are on sys.path for bare-namespace imports.

    Idempotent. Safe to call multiple times.
    """
    import sys
    from pathlib import Path

    module_path = Path(__file__).resolve()
    # src/mesh/review_queue_worker.py → <worktree>/src/mesh/ → <worktree>/src/ → <worktree>/
    worktree_src = module_path.parents[2]  # <worktree>/src/
    worktree_root = module_path.parents[3]  # <worktree>/

    for path in (str(worktree_root), str(worktree_src)):
        if path not in sys.path:
            sys.path.insert(0, path)


# Bootstrap on import so `python -m src.mesh.review_queue_worker ...`
# works regardless of cwd or explicit PYTHONPATH.
_bootstrap_sys_path()


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m src.mesh.review_queue_worker",
        description="Review queue worker CLI (B2): start daemon, stop daemon, or run a single pass.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser(
        "start", help="Write pidfile, loop run_once() until SIGTERM/KeyboardInterrupt."
    )
    p_start.add_argument(
        "--pidfile",
        type=Path,
        default=DEFAULT_PIDFILE,
        help=f"Pidfile path (default: {DEFAULT_PIDFILE})",
    )
    p_start.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds between drain passes (default: 1.0)",
    )

    p_stop = sub.add_parser(
        "stop", help="Read pidfile, kill PID, remove pidfile. Idempotent."
    )
    p_stop.add_argument(
        "--pidfile",
        type=Path,
        default=DEFAULT_PIDFILE,
        help=f"Pidfile path (default: {DEFAULT_PIDFILE})",
    )

    sub.add_parser(
        "run-once", help="Single drain pass; exits with RunResult counts on stdout."
    )

    args = parser.parse_args()

    if args.cmd == "start":
        start_worker(
            _build_adapters(),
            pidfile_path=args.pidfile,
            poll_interval=args.poll_interval,
        )
        return 0
    if args.cmd == "stop":
        killed = stop_worker(args.pidfile)
        print("killed" if killed else "no-op")
        return 0
    if args.cmd == "run-once":
        result = run_once(_build_adapters())
        print(
            f"consumed={result.consumed} approved={result.approved} "
            f"rejected={result.rejected} clarified={result.clarified} partial={result.partial}"
        )
        return 0

    parser.error(f"unknown subcommand: {args.cmd}")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(_cli())
