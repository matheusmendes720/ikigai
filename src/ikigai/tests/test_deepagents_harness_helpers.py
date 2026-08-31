"""Unit tests for F11-extracted helpers in deepagents_harness.run_chat.

Stripped 2026-08-31: `_route_command` and `_register_builtin_commands` were the
CLI dispatch helpers for the algo-execution paths (--list-checkpoints,
--run-cycle, one-shot `python -m agents.deepagents_harness` mode). Per user
scope ("o ikigai agent nao cuida de algoritmos matematicos"), those paths are
removed; the agent is a planning assistant only. The deep agent invokes tools
through deepagents' own tool-calling surface, not a bespoke `route_command`
registry.

Tests removed:
- test_route_command_dispatches_score
- test_route_command_returns_none_for_unknown_command
- test_route_command_normalizes_case
- test_register_builtin_commands_returns_expected_keys

Tests preserved (these target surviving helpers in run_chat / _make_agent):
- _extract_assistant_text (3 tests)
- _invoke_agent_or_fallback (2 tests)
- run_chat is orchestrator only (LOC budget assertion)
"""

from __future__ import annotations

from unittest.mock import MagicMock


def test_extract_assistant_text_handles_messages_list() -> None:
    """_extract_assistant_text pulls last AI message content from result."""
    from agents.deepagents_harness import _extract_assistant_text

    result = {
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello there"},
            {"role": "assistant", "content": "How can I help?"},
        ]
    }
    assert _extract_assistant_text(result) == "How can I help?"


def test_extract_assistant_text_handles_string_content() -> None:
    """_extract_assistant_text works when content is a plain string."""
    from agents.deepagents_harness import _extract_assistant_text

    result = {"messages": [{"role": "assistant", "content": "ok"}]}
    assert _extract_assistant_text(result) == "ok"


def test_extract_assistant_text_returns_empty_when_no_messages() -> None:
    """_extract_assistant_text returns empty string when no messages."""
    from agents.deepagents_harness import _extract_assistant_text

    assert _extract_assistant_text({"messages": []}) == ""


def test_invoke_agent_or_fallback_returns_agent_result() -> None:
    """_invoke_agent_or_fallback returns agent.invoke() result on success."""
    from agents.deepagents_harness import _invoke_agent_or_fallback

    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"messages": [{"role": "assistant", "content": "ok"}]}

    result = _invoke_agent_or_fallback(mock_agent, [{"role": "user", "content": "hi"}], {}, "t1")
    assert result["messages"][0]["content"] == "ok"


def test_invoke_agent_or_fallback_returns_none_on_error() -> None:
    """_invoke_agent_or_fallback returns None on invoke exception."""
    from agents.deepagents_harness import _invoke_agent_or_fallback

    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = RuntimeError("boom")

    result = _invoke_agent_or_fallback(mock_agent, [{"role": "user", "content": "hi"}], {}, "t1")
    assert result is None


def test_run_chat_is_orchestrator_only() -> None:
    """run_chat function body must be ≤ 60 LOC (orchestrator only)."""
    import inspect

    from agents import deepagents_harness

    source = inspect.getsource(deepagents_harness.run_chat)
    line_count = len(source.splitlines())
    assert line_count <= 60, f"run_chat is {line_count} lines, must be ≤ 60"
