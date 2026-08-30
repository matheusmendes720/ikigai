"""Unit tests for F11-extracted helpers in deepagents_harness.run_chat."""
from __future__ import annotations

from unittest.mock import MagicMock


def test_extract_assistant_text_handles_messages_list() -> None:
    """_extract_assistant_text pulls last AI message content from result."""
    from src.ikigai.src.agents.deepagents_harness import _extract_assistant_text

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
    from src.ikigai.src.agents.deepagents_harness import _extract_assistant_text

    result = {"messages": [{"role": "assistant", "content": "ok"}]}
    assert _extract_assistant_text(result) == "ok"


def test_extract_assistant_text_returns_empty_when_no_messages() -> None:
    """_extract_assistant_text returns empty string when no messages."""
    from src.ikigai.src.agents.deepagents_harness import _extract_assistant_text

    assert _extract_assistant_text({"messages": []}) == ""


def test_route_command_dispatches_score() -> None:
    """_route_command maps 'score' to ikigai_score tool."""
    from src.ikigai.src.agents.deepagents_harness import _route_command

    mock_result = "score output"
    registry = {
        "score": MagicMock(return_value=mock_result),
        "regime": MagicMock(),
    }
    result = _route_command("score", thread_id="t1", registry=registry)
    assert result == mock_result
    registry["score"].assert_called_once()


def test_route_command_returns_none_for_unknown_command() -> None:
    """_route_command returns None when no command matches."""
    from src.ikigai.src.agents.deepagents_harness import _route_command

    registry = {"score": MagicMock()}
    assert _route_command("xyz_unknown", thread_id="t1", registry=registry) is None


def test_route_command_normalizes_case() -> None:
    """_route_command lowercases input for matching."""
    from src.ikigai.src.agents.deepagents_harness import _route_command

    mock_result = "score output"
    registry = {"score": MagicMock(return_value=mock_result)}
    result = _route_command("SCORE", thread_id="t1", registry=registry)
    assert result == mock_result


def test_register_builtin_commands_returns_expected_keys() -> None:
    """_register_builtin_commands returns dict with all known commands."""
    from src.ikigai.src.agents.deepagents_harness import _register_builtin_commands

    registry = _register_builtin_commands()
    # Spot-check the IKIGAi shortcuts that existed pre-refactor
    expected = {"score", "regime", "phase", "corrections", "plan", "sync", "checkpoint"}
    assert expected.issubset(registry.keys())


def test_invoke_agent_or_fallback_returns_agent_result() -> None:
    """_invoke_agent_or_fallback returns agent.invoke() result on success."""
    from src.ikigai.src.agents.deepagents_harness import _invoke_agent_or_fallback

    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"messages": [{"role": "assistant", "content": "ok"}]}

    result = _invoke_agent_or_fallback(mock_agent, [{"role": "user", "content": "hi"}], {}, "t1")
    assert result["messages"][0]["content"] == "ok"


def test_invoke_agent_or_fallback_returns_none_on_error() -> None:
    """_invoke_agent_or_fallback returns None on invoke exception."""
    from src.ikigai.src.agents.deepagents_harness import _invoke_agent_or_fallback

    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = RuntimeError("boom")

    result = _invoke_agent_or_fallback(mock_agent, [{"role": "user", "content": "hi"}], {}, "t1")
    assert result is None


def test_run_chat_is_orchestrator_only() -> None:
    """run_chat function body must be ≤ 60 LOC (orchestrator only)."""
    import inspect

    from src.ikigai.src.agents import deepagents_harness

    source = inspect.getsource(deepagents_harness.run_chat)
    line_count = len(source.splitlines())
    assert line_count <= 60, f"run_chat is {line_count} lines, must be ≤ 60"
