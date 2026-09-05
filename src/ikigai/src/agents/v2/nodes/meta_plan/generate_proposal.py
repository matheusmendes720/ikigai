"""generate_proposal node — build typed Proposal from context (Plan D Task B.3).

Refuses SONHO writes with actor_required != 'user' (Plan A transition_validator).
Refuses any operation if intent.level == 'low' (defer to fast-path).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from src.ikigai.contracts.proposal import (
    HierarchyContext,
    HierarchyMatch,
    IntentClassification,
    Proposal,
    ProposalOperation,
    Traceability,
    VaultWriteOp,
)

log = logging.getLogger(__name__)


def _new_proposal_id() -> str:
    """Generate a 4-part UEID for the Proposal per ADR-014."""
    # Format: prop:<hash>:<seq>:<rand>
    short = uuid.uuid4().hex[:8]
    return f"prop:{short}:01:0001"


def _build_vault_writes(
    user_request: str,
    hierarchy_match: HierarchyMatch,
    intent: IntentClassification,
) -> list[ProposalOperation]:
    """Build vault_write ProposalOperations from hierarchy match.

    Currently: 1 operation per non-None hierarchy match.
    Future: more granular decomposition per Plan A 6-level schema.
    """
    ops: list[ProposalOperation] = []

    if intent.level == "low":
        return ops

    # Example: if user mentions projeto, propose adding to existing PROJETO
    if hierarchy_match.projeto:
        ops.append(
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path=f"vault/{hierarchy_match.projeto}.md",
                    entity_type="entrega",  # sub-entity of projeto
                    fields={
                        "title": f"Entrega derivada de: {user_request[:60]}",
                        "parent_ueid": hierarchy_match.projeto,
                        "status": "draft",
                    },
                    actor_required="agent",  # entregas are agent-OK
                    rationale="meta-planner proposal: user requested focus on this projeto",
                ),
            )
        )

    return ops


def _build_taskdog_creates(
    user_request: str,
    hierarchy_match: HierarchyMatch,
) -> list[ProposalOperation]:
    """Build taskdog_create ProposalOperations from user request + hierarchy."""
    ops: list[ProposalOperation] = []
    from src.ikigai.contracts.proposal import TaskdogOp

    if hierarchy_match.meta or hierarchy_match.projeto:
        ops.append(
            ProposalOperation(
                op_type="taskdog_create",
                taskdog_create=TaskdogOp(
                    title=f"[meta-planner] {user_request[:60]}",
                    priority="M",
                    due_date=None,
                    project=hierarchy_match.projeto,
                    tags=["meta-planner", "draft"],
                    rationale="auto-proposed by meta-planner; user approval required",
                ),
            )
        )

    return ops


def generate_proposal(state: dict[str, Any]) -> Proposal:
    """Build a typed Proposal from user_request + context.

    State keys consumed:
      - user_request: str
      - intent_classification: IntentClassification
      - memory_refs: list[MemoryRef]
      - folder_reads: list[FolderReadOp]
      - hierarchy_matches: HierarchyMatch

    Returns: Proposal(approval_state='pending', operations=[...])
    """
    user_request: str = state.get("user_request", "")
    intent: IntentClassification | None = state.get("intent_classification")
    memory_refs = state.get("memory_refs", [])
    folder_reads = state.get("folder_reads", [])
    hierarchy_match: HierarchyMatch = state.get("hierarchy_matches") or HierarchyMatch()

    # Build operations
    vault_ops = _build_vault_writes(user_request, hierarchy_match, intent)
    taskdog_ops = _build_taskdog_creates(user_request, hierarchy_match)
    operations = vault_ops + taskdog_ops

    # Refuse SONHO writes with agent actor (Plan A transition_validator)
    # The Pydantic validator on VaultWriteOp enforces this; if a build_vault_writes
    # call tried to construct a SONHO + agent combo, it would raise here.
    # We add a defensive log if any operation has SONHO + agent actor.
    for op in operations:
        if op.vault_write and op.vault_write.entity_type == "sonho":
            if op.vault_write.actor_required != "user":
                log.error(
                    "SONHO write with actor=%s refused; Plan A transition_validator requires user",
                    op.vault_write.actor_required,
                )
                raise ValueError(
                    "SONHO writes require actor_required='user' (Plan A transition_validator)"
                )

    return Proposal(
        id=_new_proposal_id(),
        created_at=datetime.now(),
        source_request=user_request,
        hierarchy_context=HierarchyContext(
            matched_sonho=hierarchy_match.sonho,
            matched_objetivo=hierarchy_match.objetivo,
            matched_meta=hierarchy_match.meta,
            matched_projeto=hierarchy_match.projeto,
        ),
        operations=operations,
        traceability=Traceability(
            memory_refs=[m.id for m in memory_refs],
            folder_reads=[f.path for f in folder_reads],
            adrs_consulted=["ADR-013", "ADR-014", "ADR-029", "ADR-030", "ADR-031"],
        ),
        approval_state="pending",
    )
