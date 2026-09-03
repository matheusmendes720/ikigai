"""OpenTelemetry tracing helpers for MCP server tool dispatch.

Provides traced_tool_dispatch() that opens a span ikigai.mcp.{tool_name}
per MCP tool call, capturing tool.name, tool.arguments_hash, tool.duration_ms,
and on error: tool.error.class, tool.error.message, tool.error.traceback.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import time
import traceback
from collections.abc import Callable
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from observability.otel_init import init_tracing

_tracer = trace.get_tracer("ikigai.mcp_server")


def _dispatch_args(fn: Callable[..., Any], arguments: dict[str, Any]) -> Any:
    """Call fn with arguments using the protocol that matches its signature.

    Two handler protocols coexist after Phase 8.2 re-registration:

      1. Dict protocol — handler signature is ``(arguments: dict[str, Any])``
         used by all 8 re-registered observation wrappers (ikigai_score,
         ikigai_regime, ikigai_phase, ikigai_corrections, ikigai_plan_cycle,
         ikigai_checkpoint, ikigai_sync_vault, ikigai_decompose). The
         dispatcher passes the dict positionally.

      2. Kwargs protocol — handler signature is ``(vault_path: str, ...)``
         used by vault_write and vault_read (Phase B6/B7). The dispatcher
         unpacks the dict as ``**arguments``.

    Detection: inspect the first parameter. If its name is ``arguments`` AND
    its annotation is ``dict[...]``, use protocol 1; otherwise protocol 2.

    This keeps existing handler signatures untouched — the bug was that the
    dispatcher assumed protocol 2 universally, which broke protocol 1.
    """
    try:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
    except (TypeError, ValueError):
        return fn(**arguments)

    if params:
        first = params[0]
        if first.name == "arguments":
            ann = first.annotation
            ann_str = str(ann) if ann is not inspect.Parameter.empty else ""
            if "dict" in ann_str:
                return fn(arguments)
    return fn(**arguments)


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
            result = _dispatch_args(fn, arguments)
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
