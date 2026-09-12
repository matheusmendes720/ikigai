"""E2E tests for life plan CLI (Plan D Task E.2)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from interfaces.cli.v2 import _run_plan


def test_run_plan_happy_path():
    """Plan intent detected → Proposal generated → approve → writes happen."""
    fake_proposal_dict = {
        "id": "prop:test01:01:0001",
        "created_at": "2026-09-04T00:00:00",
        "source_request": "quero focar em X",
        "hierarchy_context": {
            "matched_sonho": None,
            "matched_objetivo": None,
            "matched_meta": None,
            "matched_projeto": None,
        },
        "operations": [
            {
                "op_type": "taskdog_create",
                "vault_write": None,
                "taskdog_create": {
                    "title": "Test task",
                    "priority": "M",
                    "due_date": None,
                    "project": None,
                    "tags": [],
                    "rationale": "test",
                },
            }
        ],
        "traceability": {
            "memory_refs": [],
            "folder_reads": [],
            "adrs_consulted": ["ADR-029"],
        },
        "approval_state": "pending",
        "actor_approving": None,
        "approval_timestamp": None,
    }

    fake_compiled = MagicMock()
    fake_compiled.invoke.return_value = {"proposal": _dict_to_proposal(fake_proposal_dict)}
    with patch("src.ikigai.src.agents.v2.subgraph.make_meta_plan_subgraph") as mock_mksg, \
         patch("src.ikigai.src.agents.v2.nodes.proposal_executor.execute_proposal") as mock_exec:
        mock_mksg.return_value = fake_compiled
        mock_exec.return_value = _fake_report()

        result = _run_plan("quero focar em X", approve=True)

    assert result["status"] == "executed"
    assert mock_mksg.called
    assert mock_exec.called


def test_run_plan_no_proposal_for_low_intent():
    """Low-intent request → no Proposal → user gets hint message."""
    fake_compiled = MagicMock()
    fake_compiled.invoke.return_value = {"proposal": None}
    with patch("src.ikigai.src.agents.v2.subgraph.make_meta_plan_subgraph") as mock_mksg:
        mock_mksg.return_value = fake_compiled

        result = _run_plan("que horas são?")

    assert result["status"] == "no_proposal"


def test_run_plan_reject_field():
    """--reject X.field → status='rejected_field'."""
    fake_compiled = MagicMock()
    fake_compiled.invoke.return_value = {"proposal": _fake_proposal()}
    with patch("src.ikigai.src.agents.v2.subgraph.make_meta_plan_subgraph") as mock_mksg:
        mock_mksg.return_value = fake_compiled

        result = _run_plan("x", reject_field="priority")

    assert result["status"] == "rejected_field"
    assert result["field"] == "priority"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dict_to_proposal(d: dict):
    from src.ikigai.contracts.proposal import Proposal

    return Proposal.model_validate(d)


def _fake_proposal():
    from src.ikigai.contracts.proposal import (
        HierarchyContext,
        Proposal,
        Traceability,
    )
    return Proposal(
        id="prop:test01:01:0001",
        created_at="2026-09-04T00:00:00",
        source_request="test",
        hierarchy_context=HierarchyContext(matched_sonho=None, matched_objetivo=None, matched_meta=None, matched_projeto=None),
        operations=[],
        traceability=Traceability(memory_refs=[], folder_reads=[], adrs_consulted=[]),
        approval_state="pending",
    )


def _fake_report():
    from src.ikigai.contracts.proposal import ExecutionReport

    return ExecutionReport(
        proposal_id="prop:test01:01:0001",
        ops_total=1,
        ops_completed=1,
        ops_failed=0,
        status="ok",
        errors=[],
    )
