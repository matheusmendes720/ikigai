"""M144 tests: write-side IKIGAI MCP wrappers added to .claude/loop/mcp_bridge.py.

Adds 6 wrappers on top of M142's 6 read-only ones:
  - vault_read(vault_path)
  - ikigai_write_tasks(tasks)
  - vault_write(vault_path, frontmatter, body)  — all 3 required
  - investigation_enqueue(inq_id, source, payload, tags=None, actor="loop-agent")
  - investigation_status(inq_id=None)
  - investigation_complete(inq_id, final_status="resolved", actor="loop-agent", inq_ueid=None)

Verified contract:
  1. Each wrapper delegates to `_call()` with the right tool_name + args dict
  2. `vault_write` has NO defaults — all 3 kwargs required (loud-fail on typo)
  3. `investigation_*` default actor is "loop-agent" (distinct from v2 "agent")
  4. `investigation_complete` defaults `final_status="resolved"`
  5. M142 drift test split: 6 read-only + 6 write = 12 total
  6. PAV-math tools (8 names) STILL forbidden per ADR-013
  7. Wrappers don't accept `_server=` kwarg (callers use module-level handle)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"


@pytest.fixture(scope="module")
def bridge():
    """Load `.claude/loop/mcp_bridge.py` as a module object."""
    spec = importlib.util.spec_from_file_location("loop_mcp_bridge_m144", BRIDGE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._server = None
    return mod


@pytest.fixture
def fake_server(bridge):
    """Bind a MagicMock to bridge._server for the duration of one test."""
    mock = MagicMock()
    mock.call.return_value = {"ok": True, "tool": "fake"}
    bridge._server = mock
    yield mock
    bridge._server = None


# ---------------------------------------------------------------------------
# Acceptance #1: each wrapper delegates to _call with correct args
# ---------------------------------------------------------------------------


def test_vault_read_calls_with_vault_path(bridge, fake_server):
    bridge.vault_read("drafts/folha-norte-projeto-META-INDEX.md")
    fake_server.call.assert_called_once_with(
        "vault_read",
        {"vault_path": "drafts/folha-norte-projeto-META-INDEX.md"},
    )


def test_ikigai_write_tasks_calls_with_tasks(bridge, fake_server):
    tasks = [{"ueid": "study:topic:abc", "title": "test"}]
    bridge.ikigai_write_tasks(tasks=tasks)
    fake_server.call.assert_called_once_with(
        "ikigai_write_tasks", {"tasks": tasks}
    )


def test_vault_write_calls_with_all_three_kwargs(bridge, fake_server):
    bridge.vault_write(
        vault_path="drafts/test.md",
        frontmatter={"title": "Test"},
        body="# Hello\n",
    )
    fake_server.call.assert_called_once_with(
        "vault_write",
        {
            "vault_path": "drafts/test.md",
            "frontmatter": {"title": "Test"},
            "body": "# Hello\n",
        },
    )


def test_investigation_enqueue_calls_with_required_args(bridge, fake_server):
    bridge.investigation_enqueue(
        inq_id="inq:abc-123",
        source="loop-agent",
        payload="observation text",
    )
    fake_server.call.assert_called_once_with(
        "investigation_enqueue",
        {
            "inq_id": "inq:abc-123",
            "source": "loop-agent",
            "payload": "observation text",
            "actor": "loop-agent",
        },
    )


def test_investigation_enqueue_with_tags(bridge, fake_server):
    bridge.investigation_enqueue(
        inq_id="inq:abc",
        source="loop-agent",
        payload="x",
        tags=["urgent", "drift"],
    )
    args = fake_server.call.call_args[0][1]
    assert args["tags"] == ["urgent", "drift"]


def test_investigation_enqueue_omits_tags_when_none(bridge, fake_server):
    """When tags is None, omit the kwarg entirely (don't pass None to server)."""
    bridge.investigation_enqueue(
        inq_id="inq:abc", source="loop-agent", payload="x"
    )
    args = fake_server.call.call_args[0][1]
    assert "tags" not in args


def test_investigation_status_passes_inq_id(bridge, fake_server):
    bridge.investigation_status(inq_id="inq:abc")
    fake_server.call.assert_called_once_with(
        "investigation_status", {"inq_id": "inq:abc"}
    )


def test_investigation_status_summary_when_no_inq_id(bridge, fake_server):
    """inq_id=None → summary across all investigations."""
    bridge.investigation_status()
    fake_server.call.assert_called_once_with(
        "investigation_status", {"inq_id": None}
    )


def test_investigation_complete_calls_with_required(bridge, fake_server):
    bridge.investigation_complete(inq_id="inq:abc")
    args = fake_server.call.call_args[0][1]
    assert args == {
        "inq_id": "inq:abc",
        "final_status": "resolved",
        "actor": "loop-agent",
    }


def test_investigation_complete_with_inq_ueid(bridge, fake_server):
    """`inq_ueid` is optional — omit when None to keep server payload clean."""
    bridge.investigation_complete(
        inq_id="inq:abc",
        final_status="resolved",
        inq_ueid="study:topic:st_python_01",
    )
    args = fake_server.call.call_args[0][1]
    assert args == {
        "inq_id": "inq:abc",
        "final_status": "resolved",
        "actor": "loop-agent",
        "inq_ueid": "study:topic:st_python_01",
    }


def test_investigation_complete_archived_status(bridge, fake_server):
    """`final_status="archived"` for abandoned investigations."""
    bridge.investigation_complete(
        inq_id="inq:abc", final_status="archived"
    )
    args = fake_server.call.call_args[0][1]
    assert args["final_status"] == "archived"


# ---------------------------------------------------------------------------
# Acceptance #2: vault_write has NO defaults (all 3 kwargs required)
# ---------------------------------------------------------------------------


def test_vault_write_rejects_missing_vault_path(bridge, fake_server):
    """vault_write is keyword-only and all 3 kwargs are required."""
    with pytest.raises(TypeError):
        bridge.vault_write(frontmatter={}, body="")  # no vault_path


def test_vault_write_rejects_missing_frontmatter(bridge, fake_server):
    with pytest.raises(TypeError):
        bridge.vault_write(vault_path="x", body="")  # no frontmatter


def test_vault_write_rejects_missing_body(bridge, fake_server):
    with pytest.raises(TypeError):
        bridge.vault_write(vault_path="x", frontmatter={})  # no body


# ---------------------------------------------------------------------------
# Acceptance #3: investigation_* default actor is "loop-agent"
# ---------------------------------------------------------------------------


def test_investigation_enqueue_default_actor_is_loop_agent(bridge, fake_server):
    """Distinct from v2 graph's "agent" default — easy to grep by source."""
    bridge.investigation_enqueue(
        inq_id="inq:abc", source="x", payload="y"
    )
    args = fake_server.call.call_args[0][1]
    assert args["actor"] == "loop-agent"


def test_investigation_complete_default_actor_is_loop_agent(bridge, fake_server):
    bridge.investigation_complete(inq_id="inq:abc")
    args = fake_server.call.call_args[0][1]
    assert args["actor"] == "loop-agent"


def test_investigation_envelope_actor_override(bridge, fake_server):
    """Caller can override actor (e.g. operator-TUI driving the bridge)."""
    bridge.investigation_enqueue(
        inq_id="inq:abc", source="x", payload="y", actor="custom"
    )
    args = fake_server.call.call_args[0][1]
    assert args["actor"] == "custom"


# ---------------------------------------------------------------------------
# Acceptance #4: investigation_complete default final_status="resolved"
# ---------------------------------------------------------------------------


def test_investigation_complete_default_final_status(bridge, fake_server):
    bridge.investigation_complete(inq_id="inq:abc")
    args = fake_server.call.call_args[0][1]
    assert args["final_status"] == "resolved"


# ---------------------------------------------------------------------------
# Acceptance #5: M142 drift test split — see tests/test_m142_mcp_bridge.py
# ---------------------------------------------------------------------------
# (Lives in M142 test file. Re-verified here for cross-check.)


def test_total_wrapper_count_is_14(bridge):
    """M142 (6) + M144 (6) + M145 (2) = 14 total wrappers."""
    prefixes = ("ikigai_", "taskdog_", "vault_", "investigation_")
    actual = {
        name
        for name in dir(bridge)
        if not name.startswith("_")
        and name.startswith(prefixes)
        and callable(getattr(bridge, name))
    }
    assert len(actual) == 14, (
        f"Expected 14 wrappers (8 read + 6 write), got {len(actual)}: "
        f"{sorted(actual)}"
    )


# ---------------------------------------------------------------------------
# Acceptance #6: PAV-math tools still absent (ADR-013)
# ---------------------------------------------------------------------------


PAV_MATH_NAMES = {
    "ikigai_observe_pav_state",
    "ikigai_score_vectors",
    "ikigai_heuristics",
    "ikigai_balance",
    "ikigai_plan",
    "ikigai_reflect",
    "ikigai_tag_and_persist",
    "ikigai_commit_summary",
}


def test_pav_math_tools_still_forbidden(bridge):
    """M144 invariant: PAV-math stubs (registered in server.py for v2-graph
    drift detection) MUST NOT appear in the loop bridge per ADR-013.
    """
    exported = set(dir(bridge))
    leaked = exported & PAV_MATH_NAMES
    assert not leaked, f"PAV-math tools leaked (ADR-013 violation): {leaked}"


# ---------------------------------------------------------------------------
# Acceptance #7: wrappers don't accept _server positional/kw arg
# ---------------------------------------------------------------------------


def test_write_wrappers_do_not_accept_server_kwarg(bridge, fake_server):
    """If a caller tries to pass `_server=...`, it's a usage bug — surface it."""
    for fn_name in (
        "vault_read",
        "ikigai_write_tasks",
        "vault_write",
        "investigation_enqueue",
        "investigation_status",
        "investigation_complete",
    ):
        fn = getattr(bridge, fn_name)
        with pytest.raises(TypeError):
            fn(_server=fake_server)
