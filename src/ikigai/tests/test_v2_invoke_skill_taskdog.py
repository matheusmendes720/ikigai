"""W3.6 — invoke_skill() taskdog_create_task post-processor tests.

Per W3.6 brief:
- invoke_skill("quarterly") triggers taskdog_create_task via existing @tool
- invoke_skill("daily") does NOT trigger taskdog (outputs=[])
- invoke_skill("weekly") triggers taskdog (outputs declares it)
- invoke_skill("monthly") does NOT trigger taskdog (only vault_write)
- Taskdog success → return dict has ``taskdog_result``
- Taskdog failure → return dict has ``taskdog_pending_review_queue: True`` AND
  data/review_queue/<file>.json created with the canonical record shape
- actor=user doesn't block; skill's outputs is the gate

The tests use IKIGAI_FAKE_LLM=1 to bypass the LLM API and monkeypatch
``src.ikigai.src.agents.tools.taskdog_create_task`` so the @tool function
is replaced with a deterministic mock that records invocations.

Path setup mirrors test_v2_daily_skill.py: import pytest at top; insert
<repo>/src/ikigai/src on sys.path BEFORE importing agents.v2.*.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — match test_v2_daily_skill.py + test_v2_graph_smoke.py patterns
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent  # <repo-root>
_SRC_ROOT = _REPO_ROOT / "src"  # <repo-root>/src/
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo-root>/src/ikigai/src/

for _p in [str(_REPO_ROOT), str(_SRC_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TaskdogMock:
    """Stand-in for taskdog_create_task @tool that records invocations.

    Has the same surface as langchain_core.tools.StructuredTool.invoke()
    (callable with a dict, returns a string).
    """

    def __init__(self, return_value: str = "Added task 42 ✓", raise_exc: Exception | None = None):
        self.return_value = return_value
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    def invoke(self, params: dict) -> str:
        self.calls.append(dict(params))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.return_value


@pytest.fixture
def taskdog_mock(monkeypatch):
    """Patch ``src.ikigai.src.agents.tools.taskdog_create_task`` with a mock.

    The dual-module-identity bug: _v2_skills imports from the full
    dotted-prefix path, so the patch must target the same sys.modules entry.
    """
    import sys as _sys
    from src.ikigai.src.agents import tools as _tools_mod

    _sys.modules["src.ikigai.src.agents.tools"] = _tools_mod
    mock = _TaskdogMock()
    monkeypatch.setattr(_tools_mod, "taskdog_create_task", mock)
    return mock


@pytest.fixture
def taskdog_mock_failing(monkeypatch):
    """Patch taskdog_create_task to raise ConnectionError on invoke."""
    import sys as _sys
    from src.ikigai.src.agents import tools as _tools_mod

    _sys.modules["src.ikigai.src.agents.tools"] = _tools_mod
    mock = _TaskdogMock(raise_exc=ConnectionError("taskdog unavailable (simulated)"))
    monkeypatch.setattr(_tools_mod, "taskdog_create_task", mock)
    return mock


@pytest.fixture
def fake_server(monkeypatch):
    """Bind FakeMcpServer to mcp_bridge._server so graph nodes run without a real daemon.

    Binds directly on the imported module object (not via string path) to ensure
    the binding is visible to all code paths that hold a reference to mcp_bridge.
    """
    from src.ikigai.src.agents.v2 import mcp_bridge as _bridge_mod
    from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import FakeMcpServer

    server = FakeMcpServer()
    # Provide canned responses for every MCP wrapper the graph might call
    server.canned_response("ikigai_observe_pav_state", qhe_score=0.75)
    server.canned_response("ikigai_score_vectors", priorities=[])
    server.canned_response("ikigai_heuristics", actions=[])
    server.canned_response("ikigai_balance", delta=0.0)
    server.canned_response("ikigai_decompose", subtasks=[])
    server.canned_response("ikigai_plan", plan_id="p1")
    server.canned_response("ikigai_reflect", lessons=[])
    server.canned_response("ikigai_tag_and_persist", tags=[])
    server.canned_response("ikigai_commit_summary", verdict="PASS")
    # Direct attribute assignment on the module object — avoids string-path
    # resolution issues with monkeypatch.setattr
    _bridge_mod._server = server
    return server


def _list_review_queue(tmp_path: Path) -> list[dict]:
    """Return parsed JSON records from the per-test review_queue dir."""
    files = sorted(tmp_path.glob("*.json"))
    out: list[dict] = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# Tests — outputs gate
# ---------------------------------------------------------------------------


def test_invoke_skill_skips_taskdog_for_daily(tmp_path, monkeypatch, taskdog_mock, fake_server):
    """invoke_skill("daily") does NOT fire taskdog (outputs is empty).

    daily.md has ``outputs: []`` (surface-only skill per W3.5). Even if a
    mock is wired up, the post-processor must short-circuit before calling it.
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli._v2_skills import invoke_skill

    result = invoke_skill("daily")

    assert isinstance(result, dict)
    assert "taskdog_result" not in result
    assert "taskdog_pending_review_queue" not in result
    assert taskdog_mock.calls == [], "taskdog must NOT be called for daily skill"


def test_invoke_skill_fires_taskdog_for_quarterly(tmp_path, monkeypatch, taskdog_mock, fake_server):
    """invoke_skill("quarterly") fires taskdog_create_task exactly once.

    quarterly.md outputs declares ``taskdog_create_task: quarterly OKRs``,
    so the post-processor must invoke the @tool with the derived title.
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli._v2_skills import invoke_skill

    invoke_skill("quarterly")

    assert len(taskdog_mock.calls) == 1, (
        f"taskdog must be called exactly once for quarterly; got {taskdog_mock.calls}"
    )


def test_invoke_skill_taskdog_called_with_state_derived_params(tmp_path, monkeypatch, taskdog_mock, fake_server):
    """The taskdog invoke payload derives from skill description + date.

    Per quarterly.md: ``taskdog_create_task: quarterly OKRs``. The derived
    title is ``"<description> <YYYY-MM-DD>"`` so the task is traceable to
    the skill invocation that produced it.
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli._v2_skills import invoke_skill

    invoke_skill("quarterly")

    today = date.today().isoformat()
    assert taskdog_mock.calls[0]["name"] == f"quarterly OKRs {today}"


def test_invoke_skill_taskdog_success_includes_result(tmp_path, monkeypatch, taskdog_mock, fake_server):
    """Success path returns ``taskdog_result`` populated with @tool stdout."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    taskdog_mock.return_value = "Added task 7 ✓ quarterly OKRs 2026-09-04"
    from interfaces.cli._v2_skills import invoke_skill

    result = invoke_skill("quarterly")

    assert "taskdog_result" in result
    assert "Added task 7" in result["taskdog_result"]
    assert "taskdog_pending_review_queue" not in result


def test_invoke_skill_taskdog_failure_returns_pending_review_queue(
    tmp_path, monkeypatch, taskdog_mock_failing, fake_server
):
    """Failure path returns ``taskdog_pending_review_queue: True``.

    Per Wave 3 partial-success invariant: a taskdog failure becomes a
    warning + review_queue entry, NOT a CLI crash. The return dict carries
    a flag so downstream consumers can detect the partial state.
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli._v2_skills import invoke_skill

    result = invoke_skill("quarterly")

    assert "taskdog_pending_review_queue" in result
    assert result["taskdog_pending_review_queue"] is True
    assert "taskdog_result" not in result


def test_invoke_skill_taskdog_failure_writes_to_review_queue(
    tmp_path, monkeypatch, taskdog_mock_failing, fake_server
):
    """Failure path enqueues a TaskChange to data/review_queue/.

    Per the W3.6 brief the persisted record has:
      action: create, target_fork: taskdog, error: <msg>,
      original_params: {...}, actor: agent, created_at: ISO.
    These are encoded in the canonical TaskChange schema (mesh.queue.enqueue
    is the canonical writer; ``test_review_queue_append_only`` invariant).
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    # Isolated review queue dir (autouse fixture in conftest)
    from src.mesh import queue as queue_mod

    monkeypatch.setattr(queue_mod, "QUEUE_DIR", tmp_path / "review_queue")
    from interfaces.cli._v2_skills import invoke_skill

    invoke_skill("quarterly")

    records = _list_review_queue(tmp_path / "review_queue")
    assert len(records) == 1, f"expected 1 review_queue record; got {records}"
    rec = records[0]
    assert rec["action"] == "create"
    assert rec["source_fork"] == "taskdog"
    # Brief-required fields live under `fields` (TaskChange has no top-level
    # target_fork/actor slots; canonical schema stores them in fields).
    f = rec["fields"]
    assert f["target_fork"] == "taskdog"
    assert f["actor"] == "agent"
    assert "created_at" in f
    assert "error" in f
    assert "taskdog unavailable" in f["error"]
    assert f["original_params"]["name"].startswith("quarterly OKRs ")
    # UEID must be canonical 4-part format (test_review_queue_append_only
    # and test_ueid_canonical_regex_enforced invariants).
    import re

    assert re.match(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$", rec["ueid"])


def test_invoke_skill_taskdog_weekly_triggers(tmp_path, monkeypatch, taskdog_mock, fake_server):
    """invoke_skill("weekly") fires taskdog (weekly.md declares it).

    weekly.md outputs declares ``taskdog_create_task: weekly priorities`` —
    expected behavior is to fire, just like quarterly.
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli._v2_skills import invoke_skill

    invoke_skill("weekly")

    assert len(taskdog_mock.calls) == 1
    today = date.today().isoformat()
    assert taskdog_mock.calls[0]["name"] == f"weekly priorities {today}"


def test_invoke_skill_taskdog_monthly_skips(tmp_path, monkeypatch, taskdog_mock, fake_server):
    """invoke_skill("monthly") does NOT fire taskdog.

    monthly.md outputs only declares ``vault_write`` — no taskdog entry.
    The post-processor must short-circuit and return the graph result unchanged.
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    from interfaces.cli._v2_skills import invoke_skill

    result = invoke_skill("monthly")

    assert taskdog_mock.calls == [], "taskdog must NOT be called for monthly skill"
    assert "taskdog_result" not in result
    assert "taskdog_pending_review_queue" not in result


def test_invoke_skill_actor_user_does_not_block_taskdog(tmp_path, monkeypatch, taskdog_mock, fake_server):
    """actor=user does NOT prevent taskdog firing — skill.outputs is the gate.

    Per W3.6 brief, post-processor is driven by the manifest's `outputs`
    list, NOT by the skill's `actor`. This test patches daily.md's manifest
    to declare taskdog_create_task (simulating a future skill where a
    user-actor skill still has taskdog outputs) and verifies it fires.
    """
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    monkeypatch.setenv("IKIGAI_VAULT_ROOT", str(tmp_path / "vault"))
    # Override daily.md to declare taskdog_create_task in its outputs.
    skills_dir = _REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "v2" / "skills"
    daily_md = skills_dir / "daily.md"
    original = daily_md.read_text(encoding="utf-8")
    patched = original.replace(
        "outputs: []",
        "outputs:\n  - taskdog_create_task: daily followups",
    )
    assert patched != original, "test setup failed: could not patch daily.md"
    daily_md.write_text(patched, encoding="utf-8")
    try:
        from interfaces.cli._v2_skills import invoke_skill

        invoke_skill("daily")

        assert len(taskdog_mock.calls) == 1, (
            "actor=user must NOT block taskdog firing — manifest.outputs is the gate"
        )
        today = date.today().isoformat()
        assert taskdog_mock.calls[0]["name"] == f"daily followups {today}"
    finally:
        # Restore daily.md to its committed state
        daily_md.write_text(original, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests — helpers
# ---------------------------------------------------------------------------


def test_manifest_declares_taskdog_handles_bare_string():
    """_manifest_declares_taskdog returns '' for bare-string entries."""
    from interfaces.cli._v2_skills import _manifest_declares_taskdog

    assert _manifest_declares_taskdog(["taskdog_create_task"]) == ""
    assert _manifest_declares_taskdog([{"vault_write": "x"}]) is None
    assert _manifest_declares_taskdog([]) is None
    assert _manifest_declares_taskdog(None) is None


def test_manifest_declares_taskdog_handles_dict_entry():
    """_manifest_declares_taskdog returns the description string for dict entries."""
    from interfaces.cli._v2_skills import _manifest_declares_taskdog

    assert (
        _manifest_declares_taskdog([{"taskdog_create_task": "quarterly OKRs"}]) == "quarterly OKRs"
    )
    assert (
        _manifest_declares_taskdog(
            [{"vault_write": "x"}, {"taskdog_create_task": "weekly priorities"}]
        )
        == "weekly priorities"
    )


def test_derive_taskdog_title_includes_date():
    """_derive_taskdog_title composes ``<description> <YYYY-MM-DD>``."""
    from interfaces.cli._v2_skills import _derive_taskdog_title

    today = date.today().isoformat()
    assert _derive_taskdog_title("ikigai-quarterly", "quarterly OKRs") == (
        f"quarterly OKRs {today}"
    )
    # When no description, fall back to skill name
    assert _derive_taskdog_title("ikigai-x", "") == f"ikigai-x {today}"
