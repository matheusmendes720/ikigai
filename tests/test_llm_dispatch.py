"""M87: Tests for _fake_llm_dispatch, _real_llm_dispatch, _llm_dispatch.

Coverage:
- _fake_llm_dispatch: deterministic, sets llm_stub=True
- _real_llm_dispatch: missing API key -> fallback path, llm_stub=False, ok_reason
- _real_llm_dispatch: import failure -> fallback path
- _llm_dispatch: IKIGAI_FAKE_LLM=1 -> fake path; otherwise real path
- _llm_dispatch: real path with valid key + stub LLM returns parsed graph_state
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from interfaces.cli.invoke_skill import (
    _fake_llm_dispatch,
    _llm_dispatch,
    _real_llm_dispatch,
)


@pytest.fixture
def manifest() -> dict[str, Any]:
    return {
        "name": "ikigai-test",
        "description": "Test manifest",
        "entry_point": "observe",
        "actor": "agent",
        "inputs": [],
        "outputs": [{"taskdog_create_task": "test"}],
    }


# ============================================================================
# _fake_llm_dispatch tests
# ============================================================================


def test_fake_llm_dispatch_deterministic(manifest):
    """M87: fake dispatch returns deterministic skeleton."""
    result = _fake_llm_dispatch(manifest)
    assert result["skill"] == "ikigai-test"
    assert result["entry_point"] == "observe"
    assert result["llm_stub"] is True
    assert result["graph_state"]["iteration"] == 0
    assert result["graph_state"]["last_step"] == "observe"


def test_fake_llm_dispatch_handles_missing_fields():
    """M87: fake dispatch with empty manifest uses defaults."""
    result = _fake_llm_dispatch({})
    assert result["skill"] == "unknown"
    assert result["entry_point"] == "observe"
    assert result["actor"] == "agent"
    assert result["llm_stub"] is True


# ============================================================================
# _real_llm_dispatch tests - missing key path
# ============================================================================


def test_real_llm_dispatch_missing_api_key(manifest, monkeypatch):
    """M87: missing API key falls back to fake with ok_reason."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    result = _real_llm_dispatch(manifest)
    assert result["llm_stub"] is False
    assert "missing" in result["ok_reason"].lower()
    assert result["skill"] == "ikigai-test"


def test_real_llm_dispatch_claude_api_key_alias(manifest, monkeypatch):
    """M87: CLAUDE_API_KEY env var should be picked up as ANTHROPIC_API_KEY alias."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-test-claude-key")
    # Stub ChatAnthropic to capture the api_key arg
    captured: dict[str, Any] = {}

    def fake_chat(*args, **kwargs):
        captured.update(kwargs)
        return MagicMock()

    # Mock the import + ChatAnthropic call
    fake_anthropic_module = MagicMock()
    fake_anthropic_module.ChatAnthropic = fake_chat
    fake_messages = MagicMock()
    with patch.dict(
        "sys.modules",
        {
            "langchain_anthropic": fake_anthropic_module,
            "langchain_core.messages": fake_messages,
        },
    ):
        result = _real_llm_dispatch(manifest)

    assert captured["api_key"] == "sk-test-claude-key", (
        f"expected api_key passed to ChatAnthropic, got {captured}"
    )
    assert result["llm_stub"] is False
    # Init succeeded but invoke would have been called; check it didn't crash on init
    assert result["skill"] == "ikigai-test"


def test_real_llm_dispatch_import_failure(manifest, monkeypatch):
    """M87: langchain_anthropic not installed -> fallback."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    # Simulate import failure by hiding the module
    with patch.dict("sys.modules", {"langchain_anthropic": None, "langchain_core.messages": None}):
        result = _real_llm_dispatch(manifest)
    assert result["llm_stub"] is False
    assert "import_failed" in result["ok_reason"]


def test_real_llm_dispatch_parse_responses(manifest, monkeypatch):
    """M87: real LLM returning JSON-string is parsed correctly."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    # Mock ChatAnthropic with a response object
    mock_response = MagicMock()
    mock_response.content = json.dumps(
        {
            "analysis": "Test analysis",
            "outputs": ["action1", "action2"],
            "next_action": "test next",
        }
    )

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    mock_anthropic = MagicMock()
    mock_anthropic.ChatAnthropic.return_value = mock_llm

    mock_messages = MagicMock()  # HumanMessage/SystemMessage are no-op MagicMocks

    with patch.dict(
        "sys.modules",
        {
            "langchain_anthropic": mock_anthropic,
            "langchain_core.messages": mock_messages,
        },
    ):
        result = _real_llm_dispatch(manifest)

    assert result["llm_stub"] is False
    assert "llm_model" in result
    assert result["graph_state"]["analysis"] == "Test analysis"
    assert result["graph_state"]["outputs"] == ["action1", "action2"]
    assert result["graph_state"]["next_action"] == "test next"


def test_real_llm_dispatch_strips_markdown_fences(manifest, monkeypatch):
    """M87: real LLM with ```json fences should still parse."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    mock_response = MagicMock()
    mock_response.content = (
        "```json\n"
        '{"analysis": "fenced", "outputs": ["x"], "next_action": "y"}\n'
        "```"
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    mock_anthropic = MagicMock()
    mock_anthropic.ChatAnthropic.return_value = mock_llm
    mock_messages = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "langchain_anthropic": mock_anthropic,
            "langchain_core.messages": mock_messages,
        },
    ):
        result = _real_llm_dispatch(manifest)

    assert result["graph_state"]["analysis"] == "fenced"


def test_real_llm_dispatch_handles_invoke_failure(manifest, monkeypatch):
    """M87: invoke raises -> fallback with invoke_failed reason."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError("401 unauthorized")

    mock_anthropic = MagicMock()
    mock_anthropic.ChatAnthropic.return_value = mock_llm
    mock_messages = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "langchain_anthropic": mock_anthropic,
            "langchain_core.messages": mock_messages,
        },
    ):
        result = _real_llm_dispatch(manifest)

    assert result["llm_stub"] is False
    assert "invoke_failed" in result["ok_reason"]
    assert "401" in result["ok_reason"]


# ============================================================================
# _llm_dispatch tests - the umbrella selector
# ============================================================================


def test_llm_dispatch_uses_fake_when_env_set(manifest, monkeypatch):
    """M87: IKIGAI_FAKE_LLM=1 -> _fake_llm_dispatch path."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "1")
    result = _llm_dispatch(manifest)
    assert result["llm_stub"] is True


def test_llm_dispatch_uses_real_by_default(manifest, monkeypatch):
    """M87: no IKIGAI_FAKE_LLM -> _real_llm_dispatch path."""
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    result = _llm_dispatch(manifest)
    # No key -> real path tried, fell back to fake with ok_reason
    assert result["llm_stub"] is False
    assert "missing" in result["ok_reason"].lower()


def test_llm_dispatch_with_zero_env(manifest, monkeypatch):
    """M87: IKIGAI_FAKE_LLM=0 should also use real path."""
    monkeypatch.setenv("IKIGAI_FAKE_LLM", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    result = _llm_dispatch(manifest)
    assert result["llm_stub"] is False


def test_llm_dispatch_default_does_not_call_fake(manifest, monkeypatch):
    """M87: with IKIGAI_FAKE_LLM unset and no key, fallback is from real path."""
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)
    # Both key vars absent
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    result = _llm_dispatch(manifest)
    assert "missing" in result["ok_reason"]
    # fake dispatch wouldn't set llm_stub=False with this reason
    assert result["llm_stub"] is False
