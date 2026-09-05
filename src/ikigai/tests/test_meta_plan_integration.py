"""Integration tests for meta-planner (Plan D Tasks B.4 + E + drift).

Integration scope (vs ``test_meta_plan_unit.py`` which is pure-unit):
- exercises ``execute_proposal`` end-to-end with mocked write infra
- asserts routing through ``wrap_vault_write`` + ``taskdog_create_task``
- asserts partial-failure semantics + kill-switch propagation

Drift invariants covered (Plan D):
  (n) — vault writes must route through ``wrap_vault_write`` (ADR-029)
  (o) — executor must refuse any approval_state != 'approved'
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from src.ikigai.contracts.proposal import (
    ExecutionReport,
    HierarchyContext,
    Proposal,
    ProposalOperation,
    TaskdogOp,
    Traceability,
    VaultWriteOp,
)
from src.ikigai.src.agents.v2.nodes.proposal_executor import execute_proposal


@pytest.fixture
def approved_proposal() -> Proposal:
    """A minimal approved Proposal with one vault_write op."""
    return Proposal(
        id="prop:test01:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="test",
        hierarchy_context=HierarchyContext(
            matched_sonho=None,
            matched_objetivo=None,
            matched_meta=None,
            matched_projeto=None,
        ),
        operations=[
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test.md",
                    entity_type="entrega",
                    fields={"title": "test"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
        ],
        traceability=Traceability(
            memory_refs=[],
            folder_reads=[],
            adrs_consulted=[],
        ),
        approval_state="approved",
    )


def test_executor_refuses_pending_proposal(approved_proposal: Proposal) -> None:
    """proposal_executor MUST refuse approval_state != 'approved' (drift invariant o)."""
    pending = approved_proposal.model_copy(update={"approval_state": "pending"})
    with pytest.raises(AssertionError):
        execute_proposal(pending)


def test_executor_routes_through_wrap_vault_write(approved_proposal: Proposal) -> None:
    """All vault writes go through wrap_vault_write (ADR-029), not raw vault_write."""
    with (
        patch("src.ikigai.src.agents.v2.nodes.proposal_executor.wrap_vault_write") as mock_wrap,
        patch("src.ikigai.src.agents.v2.nodes.proposal_executor.vault_write") as mock_raw,
    ):
        report = execute_proposal(approved_proposal)
        assert mock_wrap.called
        assert not mock_raw.called, "Must not call raw vault_write — must use wrap_vault_write"
        assert isinstance(report, ExecutionReport)
        assert report.status == "ok"
        assert report.ops_completed == 1


def test_executor_routes_through_taskdog_create_task(approved_proposal: Proposal) -> None:
    """Taskdog creates use taskdog_create_task @tool (W3.6 Path 1)."""
    proposal = approved_proposal.model_copy(
        update={
            "operations": [
                ProposalOperation(
                    op_type="taskdog_create",
                    taskdog_create=TaskdogOp(
                        title="x",
                        priority="M",
                        due_date=None,
                        project=None,
                        tags=[],
                        rationale="test",
                    ),
                ),
            ],
        }
    )
    with patch("src.ikigai.src.agents.v2.nodes.proposal_executor.taskdog_create_task") as mock_task:
        report = execute_proposal(proposal)
        assert mock_task.called
        assert report.status == "ok"
        assert report.ops_completed == 1


def test_executor_partial_failure_returns_partial_status() -> None:
    """If one op fails, ExecutionReport.status = 'partial'."""
    proposal = Proposal(
        id="prop:test01:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="test",
        hierarchy_context=HierarchyContext(
            matched_sonho=None,
            matched_objetivo=None,
            matched_meta=None,
            matched_projeto=None,
        ),
        operations=[
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test.md",
                    entity_type="entrega",
                    fields={"title": "a"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test2.md",
                    entity_type="entrega",
                    fields={"title": "b"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
        ],
        traceability=Traceability(
            memory_refs=[],
            folder_reads=[],
            adrs_consulted=[],
        ),
        approval_state="approved",
    )
    with patch("src.ikigai.src.agents.v2.nodes.proposal_executor.wrap_vault_write") as mock_wrap:
        mock_wrap.side_effect = [None, RuntimeError("boom")]
        report = execute_proposal(proposal)
        assert report.status == "partial"
        assert report.ops_completed == 1
        assert report.ops_failed == 1


def test_executor_kill_switch_blocks_all_writes() -> None:
    """wrap_vault_write raising KillSwitchAbort → propagated immediately."""
    from src.ikigai.src.ikigai.security.vault_write_wrapper import KillSwitchAbort

    proposal = Proposal(
        id="prop:test01:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="test",
        hierarchy_context=HierarchyContext(
            matched_sonho=None,
            matched_objetivo=None,
            matched_meta=None,
            matched_projeto=None,
        ),
        operations=[
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test.md",
                    entity_type="entrega",
                    fields={"title": "a"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
        ],
        traceability=Traceability(
            memory_refs=[],
            folder_reads=[],
            adrs_consulted=[],
        ),
        approval_state="approved",
    )
    with patch("src.ikigai.src.agents.v2.nodes.proposal_executor.wrap_vault_write") as mock_wrap:
        mock_wrap.side_effect = KillSwitchAbort("kill switch active")
        with pytest.raises(KillSwitchAbort):
            execute_proposal(proposal)
