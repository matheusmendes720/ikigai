"""Tests for MCP server tracing functionality."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from mcp_server.tracing import traced_tool_dispatch, init_mcp_tracing


class TestInitMcpTracing:
    """Tests for init_mcp_tracing idempotency."""

    def test_init_mcp_tracing_idempotent(self):
        """Call init_mcp_tracing twice — should not raise, no double-init."""
        # First call — should initialize
        init_mcp_tracing()
        # Second call — should be idempotent (no error)
        init_mcp_tracing()  # Should not raise


class TestTracedToolDispatch:
    """Tests for traced_tool_dispatch span creation and attributes."""

    def test_tool_call_emits_span(self, mock_tracer):
        """Mock handler, call via traced_tool_dispatch, assert span recorded with attributes."""
        mock_handler = MagicMock(return_value={"result": "success"})

        # Call traced_tool_dispatch
        result = traced_tool_dispatch("ikigai_score", mock_handler, {"key": "value"})

        # Verify handler was called
        mock_handler.assert_called_once_with(key="value")

        # Verify result
        assert result == {"result": "success"}

        # Verify span was started
        mock_tracer.start_as_current_span.assert_called_once_with("ikigai.mcp.ikigai_score")

        # Verify span attributes were set
        mock_span = mock_tracer.start_as_current_span.return_value.__enter__.return_value
        assert mock_span.set_attribute.call_count >= 3  # tool.name, tool.arguments_hash, tool.duration_ms

    def test_tool_error_captures_traceback(self, mock_tracer):
        """Handler raises, assert span has error.class + traceback attrs."""
        def failing_handler(key: str) -> dict:
            raise ValueError("test error message")

        mock_span = mock_tracer.start_as_current_span.return_value.__enter__.return_value

        # Call and expect exception
        with pytest.raises(ValueError, match="test error message"):
            traced_tool_dispatch("ikigai_score", failing_handler, {"key": "value"})

        # Verify error attributes were set on span
        calls = mock_span.set_attribute.call_args_list
        attr_names = [call[0][0] for call in calls]

        assert "tool.error.class" in attr_names
        assert "tool.error.message" in attr_names
        assert "tool.error.traceback" in attr_names

        # Verify span status was set to ERROR
        mock_span.set_status.assert_called()

    def test_arguments_hash_stable(self, mock_tracer):
        """Same arguments in different order → same hash."""
        mock_handler = MagicMock(return_value="ok")

        # First call with ordered dict
        traced_tool_dispatch("test_tool", mock_handler, {"a": 1, "b": 2})
        first_span = mock_tracer.start_as_current_span.return_value.__enter__.return_value

        # Reset mock for second call
        mock_tracer.reset_mock()
        mock_handler.reset_mock()

        # Second call with same keys but different order
        traced_tool_dispatch("test_tool", mock_handler, {"b": 2, "a": 1})

        # Get the hash from both calls
        first_call_attrs = mock_tracer.start_as_current_span.return_value.__enter__.return_value.set_attribute.call_args_list
        second_call_attrs = mock_tracer.start_as_current_span.return_value.__enter__.return_value.set_attribute.call_args_list

        # Extract arguments_hash from calls
        def get_hash(calls):
            for call in calls:
                if call[0][0] == "tool.arguments_hash":
                    return call[0][1]
            return None

        first_hash = get_hash(first_call_attrs)
        second_hash = get_hash(second_call_attrs)

        assert first_hash == second_hash, "Arguments hash should be stable regardless of order"


@pytest.fixture
def mock_tracer():
    """Create a mock tracer for testing."""
    with patch("mcp_server.tracing._tracer") as mock:
        mock_span = MagicMock()
        mock.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock.start_as_current_span.return_value.__exit__.return_value = None
        yield mock
