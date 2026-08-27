"""Decorator that wraps a tool call with an OTel span + exception capture.

Captures the two error surfaces the IKIGAI harness hits in practice:

- ``UnicodeDecodeError`` — when the deepagents ``FilesystemBackend`` reads a
  binary file (e.g. ``.db``, ``.pdf``) as text.
- ``FileNotFoundError`` — when a path the agent invented points at an empty
  scaffold directory.

Both classes get a span attribute ``error.class`` so the Langfuse dashboard
can group by failure mode. The full stack trace is captured via
``span.record_exception()`` and shows up in the Langfuse trace detail view.

Usage::

    from observability import observed_tool

    @observed_tool("ikigai.read_entity")
    def read_entity(path: str) -> str:
        return open(path, encoding="utf-8").read()
"""
from __future__ import annotations

import functools
import inspect
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .otel_init import get_tracer

# Lazy tracer — module load doesn't depend on init having run.
_tracer = get_tracer("ikigai.tools")


def observed_tool(tool_name: str) -> Callable:
    """Wrap a tool function with span + exception capture.

    Args:
        tool_name: Stable identifier for the tool, used as ``tool.name`` span
            attribute and as the span name (``tool.<tool_name>``). Pick a name
            that survives renames — it's how you'll filter in Langfuse.
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Bind arg names so we capture them as span attributes even if the
            # caller passed kwargs. Truncate to 200 chars to keep spans small.
            try:
                bound = sig.bind_partial(*args, **kwargs)
                bound.apply_defaults()
                attrs = {
                    f"tool.arg.{k}": repr(v)[:200]
                    for k, v in bound.arguments.items()
                }
            except Exception:  # noqa: BLE001 — bind failures shouldn't kill the tool
                attrs = {}

            with _tracer.start_as_current_span(f"tool.{tool_name}") as span:
                span.set_attribute("tool.name", tool_name)
                for k, v in attrs.items():
                    span.set_attribute(k, v)
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("tool.status", "ok")
                    return result
                except UnicodeDecodeError as e:
                    # The dcode "byd-tracker.db" failure mode.
                    span.set_status(Status(StatusCode.ERROR, "binary file read as text"))
                    span.record_exception(e)
                    span.set_attribute("error.class", "UnicodeDecodeError")
                    span.set_attribute(
                        "error.hint",
                        "File is binary — add extension to deepagents "
                        "_EXTENSION_TO_FILE_TYPE or use a binary read tool",
                    )
                    raise
                except FileNotFoundError as e:
                    # The dcode "entities/ops/__init__.py" failure mode.
                    span.set_status(Status(StatusCode.ERROR, "file not found"))
                    span.record_exception(e)
                    span.set_attribute("error.class", "FileNotFoundError")
                    raise
                except Exception as e:  # noqa: BLE001 — catch-all for unknown errors
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator