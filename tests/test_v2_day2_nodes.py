"""M89: Tests for v2 graph tag_and_persist + commit real implementations.

Replaces the prior stubs that just surfaced "mcp_bridge missing" errors.
Now uses wrap_vault_write (tag_and_persist) and taskdog_create_task
(commit) directly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Path setup - mirror test_reasoning_chain.py
import sys

sys.path.insert(0, "src/ikigai/src/agents")

from v2.nodes.commit import (
    _summarize_cycle,
    _taskdog_create_task_via_bridge,
    commit_node,
)
from v2.nodes.tag_and_persist import tag_and_persist_node


# ============================================================================
# tag_and_persist tests
# ============================================================================


def test_tag_and_persist_missing_proposed_entity():
    """M89: missing proposed_entity + vault_path returns persisted=False + error."""
    out = tag_and_persist_node({})
    assert out["persisted"] is False
    assert out["last_step"] == "tag_and_persist"
    assert "missing proposed_entity" in out["error_channel"][0]


def test_tag_and_persist_missing_vault_path():
    """M89: proposed_entity without vault_path returns persisted=False."""
    out = tag_and_persist_node({"proposed_entity": {"foo": "bar"}})
    assert out["persisted"] is False
    assert "missing proposed_entity" in out["error_channel"][0]


def test_tag_and_persist_succeeds(monkeypatch: pytest.MonkeyPatch):
    """M89: with proposed_entity + vault_path + wrap_vault_write, returns persisted=True."""
    # Stub wrap_vault_write at the proposal_executor module level
    # (tag_and_persist imports it lazily from there).
    fake_wrapper = MagicMock(return_value=MagicMock(ok=True, error=None))
    monkeypatch.setattr(
        "v2.nodes.proposal_executor.wrap_vault_write",
        fake_wrapper,
        raising=False,
    )

    out = tag_and_persist_node(
        {
            "proposed_entity": {"title": "Test", "ueid": "test:01:01:01"},
            "vault_path": "ikigai/test.md",
            "actor": "agent",
        }
    )

    assert out["persisted"] is True
    assert out["vault_path"] == "ikigai/test.md"
    assert out["actor"] == "agent"
    assert out["last_step"] == "tag_and_persist"
    assert out["error_channel"] == []
    # Wrapper called with right kwargs
    fake_wrapper.assert_called_once()
    call_kwargs = fake_wrapper.call_args.kwargs
    assert call_kwargs["actor"] == "agent"
    assert call_kwargs["vault_path"] == "ikigai/test.md"


def test_tag_and_persist_vault_write_failure(monkeypatch: pytest.MonkeyPatch):
    """M89: wrap_vault_write returning ok=False surfaces in error_channel."""
    fake_wrapper = MagicMock(return_value=MagicMock(ok=False, error="permission denied"))
    monkeypatch.setattr(
        "v2.nodes.proposal_executor.wrap_vault_write",
        fake_wrapper,
        raising=False,
    )

    out = tag_and_persist_node(
        {
            "proposed_entity": {"title": "X"},
            "vault_path": "x.md",
        }
    )

    assert out["persisted"] is False
    assert "permission denied" in out["error_channel"][0]


def test_tag_and_persist_accepts_dict_entity(monkeypatch: pytest.MonkeyPatch):
    """M89: when proposed_entity is a plain dict, fields is used directly."""
    captured: dict[str, Any] = {}

    def fake_wrapper(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return MagicMock(ok=True)

    monkeypatch.setattr(
        "v2.nodes.proposal_executor.wrap_vault_write",
        fake_wrapper,
        raising=False,
    )

    out = tag_and_persist_node(
        {
            "proposed_entity": {"title": "Plain", "ueid": "ik:plain:01:01"},
            "vault_path": "ikigai/plain.md",
            "actor": "user",
        }
    )

    assert out["persisted"] is True
    assert captured["fields"] == {"title": "Plain", "ueid": "ik:plain:01:01"}
    assert captured["actor"] == "user"


# ============================================================================
# commit tests
# ============================================================================


def test_summarize_cycle_daily_tier():
    """M89: tier defaults to 'daily' when no dream/goal UEIDs set."""
    s = _summarize_cycle({"cycle_id": "c-001", "draft_proposal": {"proposal_id": "p-1"}})
    assert s == "COMMIT cycle=c-001 tier=daily proposal=p-1 ok=True"


def test_summarize_cycle_dream_tier():
    """M89: active_dream_ueid bumps tier to 'dream'."""
    s = _summarize_cycle(
        {
            "cycle_id": "c-002",
            "active_dream_ueid": "dream:foo:01:01",
            "draft_proposal": {"proposal_id": "p-2"},
        }
    )
    assert "tier=dream" in s


def test_summarize_cycle_goal_tier():
    """M89: active_goal_ueids bumps tier to 'goal' (when no dream)."""
    s = _summarize_cycle(
        {
            "cycle_id": "c-003",
            "active_goal_ueids": ["goal:foo:01:01"],
            "draft_proposal": {"proposal_id": "p-3"},
        }
    )
    assert "tier=goal" in s


def test_summarize_cycle_no_proposal():
    """M89: missing draft_proposal falls back to proposal=none."""
    s = _summarize_cycle({"cycle_id": "c-004"})
    assert "proposal=none" in s


def test_commit_node_produces_summary():
    """M89: commit_node writes commit_summary + sets terminated=True."""
    out = commit_node(
        {
            "cycle_id": "test-cycle",
            "draft_proposal": {"proposal_id": "p-test", "operations": []},
        }
    )
    assert out["terminated"] is True
    assert out["last_step"] == "commit"
    assert "COMMIT cycle=test-cycle" in out["commit_summary"]
    assert "p-test" in out["commit_summary"]


def test_commit_node_no_proposal():
    """M89: missing draft_proposal still produces a valid commit_summary."""
    out = commit_node({"cycle_id": "no-prop"})
    assert out["terminated"] is True
    assert "proposal=none" in out["commit_summary"]


def test_commit_node_fires_taskdog_for_task_create(monkeypatch: pytest.MonkeyPatch):
    """M89: task.create operations fire taskdog_create_task via bridge."""
    fired: list[dict[str, Any]] = []

    def fake_invoke(payload: dict[str, str]) -> dict[str, Any]:
        fired.append(payload)
        return {"ok": True, "id": 999, "name": payload["name"]}

    fake_tools = MagicMock()
    fake_tools.taskdog_create_task = MagicMock()
    fake_tools.taskdog_create_task.invoke = fake_invoke

    monkeypatch.setitem(sys.modules, "agents.tools", fake_tools)

    out = commit_node(
        {
            "cycle_id": "td-cycle",
            "draft_proposal": {
                "proposal_id": "p-td",
                "operations": [
                    {"type": "task.create", "target": "Apply to BYD"},
                    {"type": "vault_write", "path": "/foo"},  # not task.create - skip
                ],
            },
        }
    )

    assert len(fired) == 1
    assert fired[0]["name"] == "Apply to BYD"
    assert out["commit"]["taskdog_results"][0]["target"] == "Apply to BYD"
    assert out["commit"]["taskdog_results"][0]["ok"] is True


def test_commit_node_taskdog_failure_graceful(monkeypatch: pytest.MonkeyPatch):
    """M89: taskdog_create_task failure is captured in commit result, not crashed."""
    def fake_invoke(payload: dict[str, str]) -> dict[str, str]:
        raise ConnectionError("taskdog-server unreachable")

    fake_tools = MagicMock()
    fake_tools.taskdog_create_task = MagicMock()
    fake_tools.taskdog_create_task.invoke = fake_invoke

    monkeypatch.setitem(sys.modules, "agents.tools", fake_tools)

    out = commit_node(
        {
            "cycle_id": "fail-cycle",
            "draft_proposal": {
                "proposal_id": "p-fail",
                "operations": [{"type": "task.create", "target": "Will fail"}],
            },
        }
    )

    # commit_summary still produced, terminated=True, error captured
    assert out["terminated"] is True
    assert out["commit"]["taskdog_results"][0]["ok"] is False
    assert "taskdog-server unreachable" in out["commit"]["taskdog_results"][0]["error"]


def test_commit_node_skips_non_task_create(monkeypatch: pytest.MonkeyPatch):
    """M89: operations with type != task.create are skipped."""
    fired: list[dict[str, Any]] = []

    def fake_invoke(payload: dict[str, str]) -> dict[str, str]:
        fired.append(payload)
        return {"ok": True}

    fake_tools = MagicMock()
    fake_tools.taskdog_create_task = MagicMock()
    fake_tools.taskdog_create_task.invoke = fake_invoke

    monkeypatch.setitem(sys.modules, "agents.tools", fake_tools)

    out = commit_node(
        {
            "cycle_id": "skip-cycle",
            "draft_proposal": {
                "proposal_id": "p-skip",
                "operations": [
                    {"type": "vault_write", "path": "/foo.md"},
                    {"type": "reflect.intention", "target_ueid": "x"},
                ],
            },
        }
    )

    assert fired == []  # nothing fired
    assert out["commit"]["taskdog_results"] == []


def test_commit_node_no_tools_module():
    """M89: missing agents.tools module produces ok=False in result."""
    # Simulate both names absent
    monkeypatch_modules = {
        k: None
        for k in [
            "agents",
            "agents.tools",
            "src.ikigai.src.agents",
            "src.ikigai.src.agents.tools",
        ]
    }
    for name, val in monkeypatch_modules.items():
        if val is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = val

    out = _taskdog_create_task_via_bridge("test")
    assert out["ok"] is False
    assert "not importable" in out["error"] or "not found" in out["error"]
