"""IKIGAI observability — OpenTelemetry init + error-capture helpers.

Single entry point: ``init_tracing()``. Call once at module load (idempotent).
After init, two helpers are available:

- ``get_tracer(name)`` — for manual spans anywhere in the harness.
- ``observed_tool(name)`` — decorator that wraps a tool function with a span
  + structured exception capture for the known error surfaces.

Configures two OTLP exporters from env vars (see ``.env.example``):

- LangSmith — primary LLM observability (project ``ikigai``).
- Langfuse — secondary stack-trace capture (cloud.langfuse.com).
"""

from .error_capture import observed_tool
from .otel_init import get_tracer, init_tracing, shutdown_tracing

__all__ = [
    "get_tracer",
    "init_tracing",
    "observed_tool",
    "shutdown_tracing",
]
