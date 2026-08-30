"""Deep Agent propagator: emits approved events to all relevant forks + vault."""
from dataclasses import dataclass
import logging
from pathlib import Path

from src.contracts.task_change import TaskChange, PropagationEvent
from src.mesh import queue as _queue
from src.mesh.agent_consumer import ValidationResult
from src.mesh.adapters.base import ForkAdapter


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PropagationResult:
    fork_name: str
    success: bool
    error: str = ""


def propagate(
    event: TaskChange,
    validation: ValidationResult,
    adapters: list[ForkAdapter],
) -> list[PropagationResult]:
    """Propagate approved event to all adapters. Per-adapter failures are isolated.

    On partial propagation (any adapter fails), the queue event is acked as
    'partial_propagation' so consume_pending() does not re-process it.
    """
    if validation.decision.value != "approve":
        return []

    propagation = PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=validation.approved_fields or event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    )

    results = []
    for adapter in adapters:
        try:
            adapter.apply_change(propagation)
            results.append(PropagationResult(fork_name=adapter.name, success=True))
        except Exception as e:
            results.append(
                PropagationResult(
                    fork_name=adapter.name,
                    success=False,
                    error=str(e),
                )
            )

    # Vault write is best-effort and never crashes propagation.
    # Convention per spec Q1=B: source_fork=="vault" signals vault-bound events.
    if event.source_fork == "vault":
        try:
            # Lazy import — agent_propagator lives in src/mesh/ not src/ikigai/.
            # The cross-tree import is intentional: src/ikigai/ is the system
            # of record; src/mesh/ consumes it.
            from src.ikigai.src.ikigai.vault.vault_write import (
                vault_write as _vault_write_impl,
            )

            vault_root = Path(__file__).resolve().parents[2] / "vault"
            # Fallback for tests/CI: env var or cwd
            if not vault_root.exists():
                vault_root = Path.cwd() / "vault"

            # Prefer vault_path from event.fields if present, otherwise derive from UEID
            vault_path = event.fields.get("vault_path")
            if not vault_path:
                vault_path = f"{event.ueid.split(':')[-1]}.md"
                if vault_path == ".md":
                    vault_path = "tasks.md"

            result = _vault_write_impl(
                vault_root=vault_root,
                vault_path=vault_path,
                frontmatter_fields={
                    "ueid": str(event.ueid),
                    "status": event.fields.get("status", "planned"),
                    "title": event.fields.get("title", ""),
                },
                body=f"# {event.fields.get('title', '')}\n\nStatus: `{event.fields.get('status', 'planned')}`\n",
            )
            logger.info(
                "vault write ok: %s (sha256=%s)", result["vault_path"], result["sha256"]
            )
        except Exception as exc:
            # Best-effort: vault write failures must not crash propagation
            logger.error("vault write failed for %s: %s", event.ueid, exc)

    if results and any(not r.success for r in results):
        _queue.ack(event.event_id, "partial_propagation")

    return results
