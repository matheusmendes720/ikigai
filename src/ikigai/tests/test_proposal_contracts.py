"""Unit tests for proposal contracts (Plan D Task A.1)."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError
from src.ikigai.contracts.proposal import (
    ExecutionReport,
    FolderReadOp,
    HierarchyContext,
    HierarchyMatch,
    IntentClassification,
    MemoryRef,
    Proposal,
    ProposalOperation,
    TaskdogOp,
    Traceability,
    VaultWriteOp,
)


def test_intent_classification_frozen():
    ic = IntentClassification(level="high", score=3)
    with pytest.raises(ValidationError):
        ic.level = "low"  # type: ignore[misc]


def test_intent_classification_extra_forbid():
    with pytest.raises(ValidationError):
        IntentClassification(level="high", score=3, rogue="x")  # type: ignore[call-arg]


def test_intent_classification_score_ge_zero():
    with pytest.raises(ValidationError):
        IntentClassification(level="high", score=-1)


def test_folder_read_op_required_fields():
    f = FolderReadOp(path="vault/x.md", excerpt="abc", reason="test")
    assert f.path == "vault/x.md"


def test_memory_ref_relevance_score_bounds():
    with pytest.raises(ValidationError):
        MemoryRef(id="mem:abc:01:0001", vault_path="x", relevance_score=1.5)
    with pytest.raises(ValidationError):
        MemoryRef(id="mem:abc:01:0001", vault_path="x", relevance_score=-0.1)


def test_hierarchy_match_all_optional():
    h = HierarchyMatch()
    assert h.sonho is None
    assert h.objetivo is None


def test_hierarchy_context_required_fields():
    hc = HierarchyContext(
        matched_sonho=None, matched_objetivo=None, matched_meta=None, matched_projeto=None
    )
    assert hc.matched_sonho is None


def test_vault_write_op_actor_enum():
    with pytest.raises(ValidationError):
        VaultWriteOp(
            vault_path="vault/x.md",
            entity_type="meta",
            fields={"title": "x"},
            actor_required="robot",  # type: ignore[arg-type]
            rationale="test",
        )


def test_vault_write_op_sonho_requires_user():
    """SONHO writes must declare actor_required='user' per Plan A transition_validator."""
    with pytest.raises(ValidationError):
        VaultWriteOp(
            vault_path="vault/x.md",
            entity_type="sonho",
            fields={"title": "x"},
            actor_required="agent",
            rationale="test",
        )


def test_taskdog_op_priority_enum():
    with pytest.raises(ValidationError):
        TaskdogOp(
            title="x",
            priority="URGENT",  # type: ignore[arg-type]
            due_date=None,
            project=None,
            tags=[],
            rationale="test",
        )


def test_traceability_required_lists():
    with pytest.raises(ValidationError):
        # Traceability fields are required; empty list is allowed only if value is list
        Traceability(memory_refs="not-a-list", folder_reads=[], adrs_consulted=[])  # type: ignore[arg-type]


def test_proposal_operation_op_type_enum():
    with pytest.raises(ValidationError):
        ProposalOperation(op_type="unknown")  # type: ignore[arg-type]


def test_proposal_approval_state_enum():
    with pytest.raises(ValidationError):
        Proposal(
            id="prop:abc:01:0001",
            created_at=datetime(2026, 9, 4),
            source_request="x",
            hierarchy_context=HierarchyContext(
                matched_sonho=None, matched_objetivo=None, matched_meta=None, matched_projeto=None
            ),
            operations=[],
            traceability=Traceability(memory_refs=[], folder_reads=[], adrs_consulted=[]),
            approval_state="drafted",  # type: ignore[arg-type]
        )


def test_proposal_frozen():
    p = Proposal(
        id="prop:abc:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="x",
        hierarchy_context=HierarchyContext(
            matched_sonho=None, matched_objetivo=None, matched_meta=None, matched_projeto=None
        ),
        operations=[],
        traceability=Traceability(memory_refs=[], folder_reads=[], adrs_consulted=[]),
        approval_state="pending",
    )
    with pytest.raises(ValidationError):
        p.approval_state = "approved"  # type: ignore[misc]


def test_proposal_id_must_match_ueid_regex():
    with pytest.raises(ValidationError):
        Proposal(
            id="bad-id",  # not 4-part
            created_at=datetime(2026, 9, 4),
            source_request="x",
            hierarchy_context=HierarchyContext(
                matched_sonho=None, matched_objetivo=None, matched_meta=None, matched_projeto=None
            ),
            operations=[],
            traceability=Traceability(memory_refs=[], folder_reads=[], adrs_consulted=[]),
            approval_state="pending",
        )


def test_execution_report_status_enum():
    with pytest.raises(ValidationError):
        ExecutionReport(
            proposal_id="prop:abc:01:0001",
            ops_total=1,
            ops_completed=1,
            ops_failed=0,
            status="partial-success",  # type: ignore[arg-type]
            errors=[],
        )
