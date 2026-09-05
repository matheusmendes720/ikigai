"""proposal_executor — execute approved Proposal via shipped write infra (Plan D Task B.4).

REUSES (zero new write code):
- ``wrap_vault_write`` (ADR-029, ``src.ikigai.src.ikigai.security.vault_write_wrapper``)
- ``taskdog_create_task`` (W3.6 Path 1, ``src.ikigai.src.agents.tools``)

Refuses to execute any Proposal whose ``approval_state != 'approved'``
(drift invariant (o) — enforces the meta-planner approval gate).

The ``wrap_vault_write`` and ``taskdog_create_task`` names below are
**lazy proxies** (module-level callables) so that tests can patch them
via ``patch("...proposal_executor.wrap_vault_write")`` without forcing
import-time evaluation of the underlying ``@tool``/wrapper machinery
(which has conditional imports that only succeed under the test
harness's ``sys.path`` setup).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.ikigai.contracts.proposal import (
    ExecutionReport,
    Proposal,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level proxies — tests patch these via mock.patch(...)
# ---------------------------------------------------------------------------


def wrap_vault_write(
    *,
    actor: str,
    vault_path: str,
    entity_type: str | None = None,
    fields: dict[str, Any] | None = None,
    rationale: str = "",
    **kwargs: Any,
) -> Any:
    """Lazy proxy to the ADR-029 wrapped ``vault_write`` (Plan D Task B.4).

    Builds the wrapped function on first call using default repo-relative
    paths. Translates the brief-style kwargs (``entity_type``, ``fields``,
    ``rationale``) to the underlying wrapped signature
    (``frontmatter_fields``, ``body``).

    When this module's attribute is patched by tests, this proxy is
    replaced wholesale — the real wrapper is never built.
    """
    from src.ikigai.src.ikigai.security.vault_write_wrapper import (
        make_wrapped_vault_write,
    )

    _wrapped = make_wrapped_vault_write(
        vault_root_provider=lambda: Path("vault"),
        data_root_provider=lambda: Path("data"),
        review_queue_dir_provider=lambda: Path("data/review_queue"),
    )
    return _wrapped(
        actor=actor,
        vault_path=vault_path,
        frontmatter_fields=fields or {},
        body=rationale,
        **kwargs,
    )


def taskdog_create_task(*args: Any, **kwargs: Any) -> Any:
    """Lazy proxy to ``src.ikigai.src.agents.tools.taskdog_create_task``.

    The real ``taskdog_create_task`` lives in ``tools.py`` and depends on
    conditional imports that only resolve under the test harness's
    ``sys.path`` (conftest). Lazy proxy defers resolution to first call.

    Tests patch this name at the module level to assert routing.
    """
    from src.ikigai.src.agents.tools import taskdog_create_task as _real

    return _real(*args, **kwargs)


# Module-level sentinel — exists ONLY so drift tests can
# ``patch("...proposal_executor.vault_write")`` and assert it was never
# called. The executor never invokes raw ``vault_write`` — all writes go
# through ``wrap_vault_write`` (ADR-029) per drift invariant (n).
def vault_write(*_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover — defensive
    """Forbidden raw vault writer. Executor MUST NOT call this."""
    raise RuntimeError(
        "proposal_executor MUST NOT call raw vault_write — "
        "route through wrap_vault_write (ADR-029, drift invariant n)."
    )


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


def execute_proposal(proposal: Proposal) -> ExecutionReport:
    """Execute an approved Proposal. Refuses any other approval_state.

    Returns ``ExecutionReport`` with ``status='ok' | 'partial' | 'failed'``.
    Re-raises ``KillSwitchAbort`` (from ADR-029 wrapper) immediately so
    callers can decide UX (drift invariant (o) + safety contract).
    """
    # Drift invariant (o) — assert approval_state == 'approved' before any write.
    assert proposal.approval_state == "approved", (
        f"proposal_executor refuses approval_state={proposal.approval_state!r}; "
        "must be 'approved'. See Plan D drift invariant (o)."
    )

    ops_total = len(proposal.operations)
    ops_completed = 0
    ops_failed = 0
    errors: list[str] = []

    for op in proposal.operations:
        try:
            if op.op_type == "vault_write" and op.vault_write is not None:
                vw = op.vault_write
                # ADR-029 wrapper handles kill switch + rate limit + audit.
                # Name lookup happens at call time → test patches via
                # patch("...proposal_executor.wrap_vault_write") work.
                wrap_vault_write(
                    actor=vw.actor_required,
                    vault_path=vw.vault_path,
                    entity_type=vw.entity_type,
                    fields=vw.fields,
                    rationale=vw.rationale,
                )
                ops_completed += 1

            elif op.op_type == "taskdog_create" and op.taskdog_create is not None:
                tc = op.taskdog_create
                # W3.6 Path 1 subprocess wrapper. Pass title as ``name``
                # (taskdog_create_task(name: str) signature).
                taskdog_create_task(name=tc.title)
                ops_completed += 1

            else:
                log.warning("Unknown op_type or missing payload: %s", op.op_type)
                ops_failed += 1
                errors.append(f"unknown op: {op.op_type}")

        except Exception as exc:
            log.error("Proposal op failed: %s", exc)
            ops_failed += 1
            errors.append(str(exc))
            # Re-raise kill-switch errors immediately (no partial execution
            # when safety is active). Matches any *KillSwitch* exception
            # class from ``vault_write_wrapper`` (KillSwitchAbort,
            # KillSwitchRateLimitExceeded, etc.).
            if "KillSwitch" in type(exc).__name__:
                raise

    if ops_failed == 0:
        status = "ok"
    elif ops_completed == 0:
        status = "failed"
    else:
        status = "partial"

    return ExecutionReport(
        proposal_id=proposal.id,
        ops_total=ops_total,
        ops_completed=ops_completed,
        ops_failed=ops_failed,
        status=status,
        errors=errors,
    )


# Backwards-compatible alias used by integration tests + naming symmetry
def execute(proposal: Proposal) -> ExecutionReport:
    """Alias for ``execute_proposal`` — kept for symmetry with other v2 nodes."""
    return execute_proposal(proposal)


__all__ = [
    "execute",
    "execute_proposal",
    "taskdog_create_task",
    "vault_write",
    "wrap_vault_write",
]
