"""Review queue worker: drains pending events from the filesystem queue.

This module wires together:
- queue.py: filesystem queue (enqueue/consume_pending/ack)
- agent_consumer.py: validate(event) -> ValidationResult (APPROVE/REJECT/CLARIFY)
- agent_propagator.py: propagate(event, validation, adapters) -> list[PropagationResult]

The worker operates in two modes:
1. run_once(): single drain pass (idempotent, safe to call repeatedly)
2. start_worker(): daemon mode with pidfile-based liveness (loop until SIGTERM/KeyboardInterrupt)

For cross-platform pidfile management, we reuse _is_pid_alive from
interfaces.cli.mcp_gateway_probe.
"""
from __future__ import annotations

import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.mesh import queue
from src.mesh.agent_consumer import Decision, validate
from src.mesh.agent_propagator import propagate
from src.mesh.adapters.base import ForkAdapter


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
    from interfaces.cli.mcp_gateway_probe import _is_pid_alive

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


def worker_status(pidfile_path: Path) -> dict[str, Any]:
    """Same shape as probe_mcp_gateway: {running: bool, pid: int|None, started_at: str|None}.

    Reuses _is_pid_alive from interfaces.cli.mcp_gateway_probe for cross-platform probe.
    """
    from interfaces.cli.mcp_gateway_probe import _is_pid_alive

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
