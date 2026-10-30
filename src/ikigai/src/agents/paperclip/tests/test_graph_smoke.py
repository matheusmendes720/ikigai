"""Paperclip smoke tests — verify the graph compiles and is wired correctly.

Nine tests, all fast (no subprocess / no DB writes beyond the SqliteSaver
file in tmp_path):

* ``test_graph_compiles`` — ``make_paperclip_graph()`` returns a Compiled
  StateGraph with the 10 nodes registered (M180 added
  ``hil_apply_user_resolution``).
* ``test_factory_signature`` — the 2-arg ``(runtime, config)`` signature
  required by ``langgraph_api/_factory_utils.py`` works (no TypeError).
* ``test_state_has_required_fields`` — ``PaperclipStateDict`` declares all
  the fields the nodes read (and that the OPEN-3 ``messages`` channel is
  present).
* ``test_claude_adapter_protocol`` — ``ClaudeAdapter`` satisfies the
  ``AgentAdapter`` ``runtime_checkable`` Protocol structurally.
* ``test_pi_adapter_protocol`` — ``PiAdapter`` satisfies the
  ``AgentAdapter`` ``runtime_checkable`` Protocol structurally.
* ``test_pi_adapter_runs_subprocess`` — ``PiAdapter.run`` invokes
  ``subprocess.run`` with ``["pi", prompt]`` + cwd + timeout.
* ``test_omo_adapter_protocol`` — ``OmoAdapter`` satisfies the
  ``AgentAdapter`` ``runtime_checkable`` Protocol structurally.
* ``test_omo_adapter_runs_subprocess`` — ``OmoAdapter.run`` invokes
  ``subprocess.run`` with ``["omo", prompt]`` + cwd + timeout.
* ``test_node_modules_importable`` — all 5 node modules import cleanly
  (catches ``ImportError`` regressions on the namespace rename or
  absolute-import conversion).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from src.ikigai.src.agents.paperclip.agents.base import AgentAdapter
from src.ikigai.src.agents.paperclip.agents.claude import ClaudeAdapter
from src.ikigai.src.agents.paperclip.agents.omo import OmoAdapter
from src.ikigai.src.agents.paperclip.agents.openclaw import OpenClawAdapter
from src.ikigai.src.agents.paperclip.agents.pi import PiAdapter
from src.ikigai.src.agents.paperclip.graph import (
    NODES,
    _build_paperclip_graph,
    make_paperclip_graph,
)
from src.ikigai.src.agents.paperclip.state import PaperclipStateDict

EXPECTED_NODES = {
    "read_spec",
    "spec_analyzer",
    "hil_pause",
    "hil_apply_user_resolution",
    "merge_user_resolution",
    "worktree_create",
    "implement",
    "worktree_commit",
    "worktree_merge",
    "worktree_cleanup",
}


def _isolated_graph(tmp_path: Path | None = None) -> tuple[Any, Any]:
    """Build a paperclip graph with an isolated checkpointer.

    Returns ``(graph, conn)`` so the caller can ``conn.close()`` before
    Windows reaps the tmp dir (SqliteSaver keeps the connection open
    which blocks ``rmtree`` on Windows — the test infra hits
    ``PermissionError [WinError 32]`` otherwise).
    """
    if tmp_path is None:
        td_ctx: Any = tempfile.TemporaryDirectory()
        td = Path(td_ctx.__enter__())
    else:
        td = tmp_path
        td_ctx = None
    ckpt = str(td / "paperclip.db")
    g = _build_paperclip_graph(checkpoint_db=ckpt, entry_point="read_spec")
    return g, g._paperclip_checkpoint_conn


def test_graph_compiles(tmp_path: Path) -> None:
    """The factory returns a Compiled StateGraph with all 10 expected nodes."""
    g, conn = _isolated_graph(tmp_path=tmp_path)
    try:
        # LangGraph stores nodes on ``builder.nodes`` during build; on the
        # compiled object we look for the ``_paperclip_nodes`` attribute we
        # attached in ``_build_paperclip_graph``.
        actual = set(getattr(g, "_paperclip_nodes", ()))
        assert actual == EXPECTED_NODES, (
            f"node set mismatch.\nexpected={sorted(EXPECTED_NODES)}\nactual={sorted(actual)}"
        )
        # And NODES (module-level tuple) matches.
        assert set(NODES) == EXPECTED_NODES
    finally:
        conn.close()


def test_factory_signature(tmp_path: Path) -> None:
    """``make_paperclip_graph(runtime, config)`` is the langgraph_api-mandated
    signature.  Both arguments should be optional (default None) and the
    factory must not raise TypeError when invoked with no args or with
    a mock config dict.
    """
    # No-args invoke (entry_point defaults to "read_spec")
    g0 = make_paperclip_graph()
    assert g0 is not None
    try:
        conn0 = g0._paperclip_checkpoint_conn
    except AttributeError:
        conn0 = None
    if conn0 is not None:
        conn0.close()

    # With a config dict carrying checkpoint_db / entry_point overrides
    ckpt = str(tmp_path / "paperclip-overrides.db")
    g1 = make_paperclip_graph(
        runtime=None,
        config={"configurable": {"checkpoint_db": ckpt, "entry_point": "spec_analyzer"}},
    )
    try:
        assert g1._paperclip_entry_point == "spec_analyzer"
        assert g1._paperclip_checkpoint_db == ckpt
    finally:
        g1._paperclip_checkpoint_conn.close()


def test_state_has_required_fields() -> None:
    """``PaperclipStateDict`` declares the fields the nodes read."""
    annotations = PaperclipStateDict.__annotations__
    required = {
        "task_id",
        "spec_text",
        "spec_gaps",
        "gap_iteration",
        "implement_iteration",
        "tests_ok",
        "worktree_path",
        "branch_name",
        "commit_sha",
        "user_resolution",
        "test_output",
        "originating_node",
        "error_type",
        "error_message",
        "traceback_str",
        "last_step",
        "messages",  # OPEN-3 — required for Cloud Studio chat
    }
    missing = required - set(annotations.keys())
    assert not missing, f"PaperclipStateDict missing fields: {sorted(missing)}"
    # ``messages`` must be a NotRequired field with a list-deduce reducer
    # (LangGraph convention: ``Annotated[list[...], operator.add]``).
    assert "messages" in annotations, "messages field missing entirely"


def test_claude_adapter_protocol() -> None:
    """``ClaudeAdapter`` structurally satisfies ``AgentAdapter`` Protocol.

    The Protocol is ``runtime_checkable`` so ``isinstance(adapter, AgentAdapter)``
    works as a structural conformance check.
    """
    adapter = ClaudeAdapter()
    assert isinstance(adapter, AgentAdapter), (
        "ClaudeAdapter does not satisfy AgentAdapter protocol — missing "
        "``name``/``timeout_s``/``run(...)``?"
    )
    assert adapter.name == "claude"
    assert isinstance(adapter.timeout_s, int)
    assert adapter.timeout_s > 0


def test_pi_adapter_protocol() -> None:
    """``PiAdapter`` structurally satisfies ``AgentAdapter`` Protocol.

    Mirror of ``test_claude_adapter_protocol`` — verifies the M170
    real-implementation conforms to the same runtime_checkable contract
    (duck typing via name/timeout_s/run()).
    """
    adapter = PiAdapter()
    assert isinstance(adapter, AgentAdapter), (
        "PiAdapter does not satisfy AgentAdapter protocol — missing "
        "``name``/``timeout_s``/``run(...)``?"
    )
    assert adapter.name == "pi"
    assert isinstance(adapter.timeout_s, int)
    assert adapter.timeout_s > 0


def test_pi_adapter_runs_subprocess(tmp_path: Path, monkeypatch: Any) -> None:
    """``PiAdapter.run`` invokes ``subprocess.run`` with ``["pi", prompt]``.

    Mocks ``subprocess.run`` (a module-level reference inside ``pi.py``)
    via ``monkeypatch.setattr`` — verifies the call args are
    ``["pi", prompt]`` plus ``cwd``, ``timeout``, ``capture_output``,
    ``text=True``, ``check=False``. The mock returns a successful
    ``CompletedProcess`` so the adapter reports ``success=True``.
    """
    adapter = PiAdapter()
    prompt = "implement spec M170"
    cwd = tmp_path  # use pytest-provided tmp dir as the worktree path

    fake_completed = MagicMock(spec=subprocess.CompletedProcess)
    fake_completed.returncode = 0
    fake_completed.stdout = "pi did the thing\n"
    fake_completed.stderr = ""

    calls: list[Any] = []

    def fake_run(args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return fake_completed

    # Patch the ``subprocess`` module as imported into ``pi.py`` (NOT the
    # stdlib ``subprocess`` itself, so we don't break other call sites).
    monkeypatch.setattr(
        "src.ikigai.src.agents.paperclip.agents.pi.subprocess.run",
        fake_run,
    )

    result = adapter.run(prompt, cwd, timeout_s=42)

    assert len(calls) == 1, f"expected 1 subprocess call, got {len(calls)}"
    call_args, call_kwargs = calls[0]
    # The argv must be exactly ``["pi", prompt]`` — no extra flags.
    assert list(call_args) == ["pi", prompt], (
        f"unexpected argv: {list(call_args)} — adapter must invoke ``pi <prompt>`` only"
    )
    # cwd should be the stringified Path the caller passed in.
    assert call_kwargs.get("cwd") == str(cwd)
    # Hard timeout must be applied so the graph can't hang forever.
    assert call_kwargs.get("timeout") == 42
    # Capture stdout/stderr so downstream nodes can surface agent output.
    assert call_kwargs.get("capture_output") is True
    assert call_kwargs.get("text") is True
    assert call_kwargs.get("check") is False
    # And the returned AgentResult should reflect a successful pi invocation.
    assert result.success is True
    assert result.output == "pi did the thing\n"
    assert result.error is None
    assert result.duration_s >= 0.0


def test_omo_adapter_protocol() -> None:
    """``OmoAdapter`` structurally satisfies ``AgentAdapter`` Protocol.

    Mirror of ``test_claude_adapter_protocol`` and ``test_pi_adapter_protocol``
    — verifies the M171 real-implementation conforms to the same
    ``runtime_checkable`` contract (duck typing via ``name``/``timeout_s``/
    ``run()``).
    """
    adapter = OmoAdapter()
    assert isinstance(adapter, AgentAdapter), (
        "OmoAdapter does not satisfy AgentAdapter protocol — missing "
        "``name``/``timeout_s``/``run(...)``?"
    )
    assert adapter.name == "omo"
    assert isinstance(adapter.timeout_s, int)
    assert adapter.timeout_s > 0


def test_omo_adapter_runs_subprocess(tmp_path: Path, monkeypatch: Any) -> None:
    """``OmoAdapter.run`` invokes ``subprocess.run`` with ``["omo", prompt]``.

    Mocks ``subprocess.run`` (the module-level reference inside ``omo.py``)
    via ``monkeypatch.setattr`` — verifies the call args are
    ``["omo", prompt]`` plus ``cwd``, ``timeout``, ``capture_output``,
    ``text=True``, ``check=False``. The mock returns a successful
    ``CompletedProcess`` so the adapter reports ``success=True``.
    """
    adapter = OmoAdapter()
    prompt = "implement spec M171"
    cwd = tmp_path  # use pytest-provided tmp dir as the worktree path

    fake_completed = MagicMock(spec=subprocess.CompletedProcess)
    fake_completed.returncode = 0
    fake_completed.stdout = "omo did the thing\n"
    fake_completed.stderr = ""

    calls: list[Any] = []

    def fake_run(args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return fake_completed

    # Patch the ``subprocess`` module as imported into ``omo.py`` (NOT the
    # stdlib ``subprocess`` itself, so we don't break other call sites).
    monkeypatch.setattr(
        "src.ikigai.src.agents.paperclip.agents.omo.subprocess.run",
        fake_run,
    )

    result = adapter.run(prompt, cwd, timeout_s=42)

    assert len(calls) == 1, f"expected 1 subprocess call, got {len(calls)}"
    call_args, call_kwargs = calls[0]
    # The argv must be exactly ``["omo", prompt]`` — no extra flags.
    assert list(call_args) == ["omo", prompt], (
        f"unexpected argv: {list(call_args)} — adapter must invoke ``omo <prompt>`` only"
    )
    # cwd should be the stringified Path the caller passed in.
    assert call_kwargs.get("cwd") == str(cwd)
    # Hard timeout must be applied so the graph can't hang forever.
    assert call_kwargs.get("timeout") == 42
    # Capture stdout/stderr so downstream nodes can surface agent output.
    assert call_kwargs.get("capture_output") is True
    assert call_kwargs.get("text") is True
    assert call_kwargs.get("check") is False
    # And the returned AgentResult should reflect a successful omo invocation.
    assert result.success is True
    assert result.output == "omo did the thing\n"
    assert result.error is None
    assert result.duration_s >= 0.0


def test_openclaw_adapter_protocol() -> None:
    """``OpenClawAdapter`` structurally satisfies ``AgentAdapter`` Protocol.

    Mirror of ``test_claude_adapter_protocol`` and ``test_omo_adapter_protocol``
    — verifies the M172 real-implementation conforms to the same
    ``runtime_checkable`` contract (duck typing via ``name``/``timeout_s``/
    ``run()``).
    """
    adapter = OpenClawAdapter()
    assert isinstance(adapter, AgentAdapter), (
        "OpenClawAdapter does not satisfy AgentAdapter protocol — missing "
        "``name``/``timeout_s``/``run(...)``?"
    )
    assert adapter.name == "openclaw"
    assert isinstance(adapter.timeout_s, int)
    assert adapter.timeout_s > 0


def test_openclaw_adapter_runs_subprocess(tmp_path: Path, monkeypatch: Any) -> None:
    """``OpenClawAdapter.run`` invokes ``subprocess.run`` with the discovered
    ``["openclaw", "agent", "--local", "--no-color", "--message", prompt]``
    argv shape.

    Mocks ``subprocess.run`` (the module-level reference inside
    ``openclaw.py``) via ``monkeypatch.setattr`` — verifies the call args
    match the subcommand + flag shape discovered by running
    ``openclaw --help`` and ``openclaw agent --help`` on 2026-10-11
    (OpenClaw 2026.7.1-2 0790d9f), plus ``cwd``, ``timeout``,
    ``capture_output``, ``text=True``, ``check=False``. The mock returns a
    successful ``CompletedProcess`` so the adapter reports ``success=True``.
    """
    adapter = OpenClawAdapter()
    prompt = "implement spec M172"
    cwd = tmp_path  # use pytest-provided tmp dir as the worktree path

    fake_completed = MagicMock(spec=subprocess.CompletedProcess)
    fake_completed.returncode = 0
    fake_completed.stdout = "openclaw did the thing\n"
    fake_completed.stderr = ""

    calls: list[Any] = []

    def fake_run(args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return fake_completed

    # Patch the ``subprocess`` module as imported into ``openclaw.py`` (NOT
    # the stdlib ``subprocess`` itself, so we don't break other call sites).
    monkeypatch.setattr(
        "src.ikigai.src.agents.paperclip.agents.openclaw.subprocess.run",
        fake_run,
    )

    result = adapter.run(prompt, cwd, timeout_s=42)

    assert len(calls) == 1, f"expected 1 subprocess call, got {len(calls)}"
    call_args, call_kwargs = calls[0]
    # The argv must be exactly ``["openclaw", "agent", "--local",
    # "--no-color", "--message", prompt]`` — see openclaw.py docstring
    # for the discovery rationale.
    assert list(call_args) == [
        "openclaw",
        "agent",
        "--local",
        "--no-color",
        "--message",
        prompt,
    ], (
        f"unexpected argv: {list(call_args)} — adapter must invoke "
        "``openclaw agent --local --no-color --message <prompt>``"
    )
    # cwd should be the stringified Path the caller passed in.
    assert call_kwargs.get("cwd") == str(cwd)
    # Hard timeout must be applied so the graph can't hang forever.
    assert call_kwargs.get("timeout") == 42
    # Capture stdout/stderr so downstream nodes can surface agent output.
    assert call_kwargs.get("capture_output") is True
    assert call_kwargs.get("text") is True
    assert call_kwargs.get("check") is False
    # And the returned AgentResult should reflect a successful openclaw
    # invocation.
    assert result.success is True
    assert result.output == "openclaw did the thing\n"
    assert result.error is None
    assert result.duration_s >= 0.0


def test_node_modules_importable() -> None:
    """All 5 node modules import cleanly — catches absolute-import regressions
    on the M102 namespace rename.
    """
    from src.ikigai.src.agents.paperclip.nodes import (  # noqa: F401
        hil_pause,
        implement,
        read_spec,
        spec_analyzer,
        worktree,
    )

    # And the node callables are exposed
    from src.ikigai.src.agents.paperclip.nodes.hil_pause import (
        hil_pause_node,
        merge_user_resolution_node,
    )
    from src.ikigai.src.agents.paperclip.nodes.implement import implement_node
    from src.ikigai.src.agents.paperclip.nodes.read_spec import read_spec_node
    from src.ikigai.src.agents.paperclip.nodes.spec_analyzer import (
        spec_analyzer_node,
    )
    from src.ikigai.src.agents.paperclip.nodes.worktree import (
        worktree_cleanup_node,
        worktree_commit_node,
        worktree_create_node,
        worktree_merge_node,
    )

    # Each is callable
    for fn in (
        hil_pause_node,
        merge_user_resolution_node,
        implement_node,
        read_spec_node,
        spec_analyzer_node,
        worktree_commit_node,
        worktree_create_node,
        worktree_cleanup_node,
        worktree_merge_node,
    ):
        assert callable(fn)
