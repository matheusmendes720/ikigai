"""OpenTelemetry tracing helpers for MCP server tool dispatch.

Provides traced_tool_dispatch() that opens a span ikigai.mcp.{tool_name}
per MCP tool call, capturing tool.name, tool.arguments_hash, tool.duration_ms,
and on error: tool.error.class, tool.error.message, tool.error.traceback.
"""

from __future__ import annotations

import hashlib
import json
import time
import traceback
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from observability.otel_init import init_tracing

_tracer = trace.get_tracer("ikigai.mcp_server")


def traced_tool_dispatch(tool_name: str, fn: Callable[..., Any], arguments: dict[str, Any]) -> Any:
    """Open a span for one MCP tool invocation. Captures traceback on error.

    Span name: ikigai.mcp.{tool_name}
    Attributes:
      - tool.name (string)
      - tool.arguments_hash (string, SHA-256 of canonicalized JSON)
      - tool.duration_ms (number)
      - tool.error.class (string, only on error)
      - tool.error.message (string, only on error)
      - tool.error.traceback (string, truncated, only on error)
    """
    args_hash = hashlib.sha256(
        json.dumps(arguments, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    with _tracer.start_as_current_span(f"ikigai.mcp.{tool_name}") as span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.arguments_hash", args_hash)
        start = time.perf_counter()
        try:
            result = fn(**arguments)
            span.set_attribute("tool.duration_ms", (time.perf_counter() - start) * 1000)
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.set_attribute("tool.error.class", type(exc).__name__)
            span.set_attribute("tool.error.message", str(exc)[:500])
            tb_str = traceback.format_exc(limit=15)
            span.set_attribute("tool.error.traceback", tb_str[:3000])
            span.set_attribute("tool.duration_ms", (time.perf_counter() - start) * 1000)
            raise


def init_mcp_tracing() -> None:
    """Call once at module load. Idempotent."""
    init_tracing()
