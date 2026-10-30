"""Paperclip Dynamic workflow-spec tests.

Three tests (per M191 spec):

* ``test_harness_builder_emits_valid_markdown`` — output starts with
  ``# Workflow:``, contains ``## Sub-agents`` section, etc.
* ``test_subagent_task_has_required_keys`` — every task dict has the
  keys the runtime depends on: ``id``, ``role``, ``prompt``,
  ``max_attempts``, ``success_criteria``.
* ``test_global_evaluator_returns_cross_findings`` — even with mock
  results, ``global_evaluator_node`` returns a non-empty
  ``cross_check_findings`` list (locked-in behaviour so the synthesizer
  always has findings to fold in).

These tests are pure-function tests — they don't build the graph or
invoke any LLM. They lock in the contract shapes downstream nodes +
tests can rely on.
"""

from __future__ import annotations

from typing import Any, cast

from src.ikigai.src.agents.paperclip_dynamic.nodes.global_evaluator import (
    global_evaluator_node,
)
from src.ikigai.src.agents.paperclip_dynamic.nodes.harness_builder import (
    _build_workflow_spec_md,
    harness_builder_node,
)
from src.ikigai.src.agents.paperclip_dynamic.nodes.planner import planner_node
from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState


def _sample_state() -> DynamicWorkflowState:
    """Build a representative state for the harness_builder + planner."""
    return {
        "user_query": "research the topic of paperclip dynamic workflows",
        "command": "research",
        "subagent_tasks": [
            {
                "id": "t1",
                "role": "researcher",
                "prompt": "Research: foo",
                "tools": ["search"],
                "data_sources": ["docs"],
                "output_schema": {"type": "object"},
                "success_criteria": "returns markdown findings",
                "max_attempts": 3,
            },
            {
                "id": "t2",
                "role": "auditor",
                "prompt": "Audit: foo",
                "tools": [],
                "data_sources": [],
                "output_schema": {"type": "object"},
                "success_criteria": "returns severity list",
                "max_attempts": 3,
            },
            {
                "id": "t3",
                "role": "synthesizer",
                "prompt": "Synthesize: foo",
                "tools": [],
                "data_sources": [],
                "output_schema": {"type": "object"},
                "success_criteria": "returns aggregated report",
                "max_attempts": 2,
            },
        ],
    }


def test_harness_builder_emits_valid_markdown() -> None:
    """Harness builder output starts with ``# Workflow:`` and contains
    the documented §5 sections.
    """
    state = _sample_state()
    spec_md = _build_workflow_spec_md(state)
    # Header
    assert spec_md.startswith("# Workflow: "), (
        f"workflow spec must start with '# Workflow: ' header, got first 30 chars: {spec_md[:30]!r}"
    )
    # Required sections per §5 schema
    for section in (
        "## Problem",
        "## Stop criterion",
        "## Synthesis criterion",
        "## Sub-agents",
        "## Aggregation",
    ):
        assert section in spec_md, f"missing required section {section!r} in workflow spec"

    # Sub-agent block markers
    for marker in ("### subagent-1", "### subagent-2", "### subagent-3"):
        assert marker in spec_md, f"missing sub-agent block {marker!r}"

    # Sub-agent block carries the required per-task fields
    assert "- role: researcher" in spec_md
    assert "- role: auditor" in spec_md
    assert "- role: synthesizer" in spec_md
    assert "- max_attempts: 3" in spec_md
    assert "- max_attempts: 2" in spec_md


def test_subagent_task_has_required_keys() -> None:
    """Every planner-emitted task carries the keys the harness builder
    + runtime depend on.
    """
    state = _sample_state()
    plan_out = planner_node(state)
    tasks = plan_out.get("subagent_tasks") or []
    assert isinstance(tasks, list), f"subagent_tasks must be a list, got {type(tasks)}"
    assert len(tasks) >= 1, "planner must emit at least one task"
    required = {"id", "role", "prompt", "max_attempts", "success_criteria"}
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue  # sentinel degenerate task — allowed by planner
        missing = required - set(task.keys())
        assert not missing, f"task {i} ({task.get('id', '?')!r}) missing keys: {sorted(missing)}"

    # Now check harness_builder's view of the same tasks. The spec
    # uses slot-based identification (``subagent-1``/etc) so we check
    # that every task's role + prompt + max_attempts are mirrored in
    # the markdown.
    hb_out = harness_builder_node(state)
    spec_md = cast(str, hb_out.get("workflow_spec_md") or "")
    for task in tasks:
        if not isinstance(task, dict):
            continue
        role = str(task.get("role") or "synthesizer")
        assert role in spec_md, f"role {role!r} missing from workflow_spec_md"
        # max_attempts value (str-comparable) appears in the spec
        max_attempts = str(task.get("max_attempts", 3))
        assert f"- max_attempts: {max_attempts}" in spec_md, (
            f"max_attempts={max_attempts!r} missing from workflow_spec_md"
        )
        # And each task maps to a numbered sub-agent slot.
        assert f"### subagent-{tasks.index(task) + 1}" in spec_md, (
            f"task at index {tasks.index(task)} not mapped to a slot in workflow_spec_md"
        )


def test_global_evaluator_returns_cross_findings() -> None:
    """Global evaluator always returns a non-empty findings list, even
    with an empty result set (so the synthesizer always has findings
    to fold in).
    """
    # Empty results path
    empty_state: DynamicWorkflowState = {}
    out_empty = global_evaluator_node(empty_state)
    findings_empty = out_empty.get("cross_check_findings") or []
    assert isinstance(findings_empty, list)
    assert len(findings_empty) >= 1, (
        f"global_evaluator must return >=1 finding even with empty state, got {findings_empty}"
    )
    confidence_empty = float(cast(Any, out_empty.get("confidence")) or 0.0)
    assert confidence_empty == 0.0, (
        f"expected confidence=0.0 on empty state, got {confidence_empty}"
    )

    # Multi-result path
    state: DynamicWorkflowState = {
        "subagent_results": {
            "t1": {"role": "researcher", "ok": True, "markdown": "## finding"},
            "t2": {"role": "auditor", "ok": True, "markdown": "## finding"},
            "t3": {"role": "synthesizer", "ok": True, "markdown": "## finding"},
        }
    }
    out_full = global_evaluator_node(state)
    findings_full = out_full.get("cross_check_findings") or []
    assert isinstance(findings_full, list)
    assert len(findings_full) >= 1, (
        f"global_evaluator must return >=1 finding on multi-result state, got {findings_full}"
    )
    confidence_full = float(cast(Any, out_full.get("confidence")) or 0.0)
    # 3 results → full coverage → _DEFAULT_CONFIDENCE (0.75)
    assert confidence_full > 0.0, f"expected confidence > 0 with 3 results, got {confidence_full}"
