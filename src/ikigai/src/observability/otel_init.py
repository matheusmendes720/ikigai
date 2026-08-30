"""Single init function for IKIGAI tracing. Called once per process.

Configures:

- LangSmith OTLP exporter (LLM observability) — endpoint and headers from env.
- Langfuse OTLP exporter (stack traces + custom events) — Basic auth.
- Auto-instrumentation: langchain, requests, sqlite3, logging (best-effort).

Idempotent via a process-wide lock + flag, so module-level imports in
``deepagents_harness.py`` and ``graph.py`` don't double-init.

Env vars consumed (see ``.env.example`` for the template):

- ``LANGSMITH_API_KEY`` — if set, LangSmith exporter is enabled.
- ``LANGSMITH_PROJECT`` — defaults to ``ikigai``.
- ``LANGSMITH_OTEL_ENDPOINT`` — defaults to the public LangSmith OTLP ingest.
- ``LANGFUSE_PUBLIC_KEY`` + ``LANGFUSE_SECRET_KEY`` — both required for Langfuse.
- ``LANGFUSE_HOST`` — defaults to ``https://cloud.langfuse.com``.
- ``OTEL_SERVICE_NAME`` — defaults to ``ikigai-maintainer``.
- ``IKIGAI_ENV`` — deployment.environment attribute (default ``local``).
"""

from __future__ import annotations

import base64
import os
import sys
import threading
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

_INIT_LOCK = threading.Lock()
_INITIALIZED = False

# Default endpoints. Override via env vars if LangSmith or Langfuse publish
# new OTLP base URLs.
_LANGSMITH_OTEL_ENDPOINT_DEFAULT = "https://api.smith.langchain.com/api/v1/otel/v1/traces"
_LANGFUSE_OTEL_PATH = "/api/public/otel/v1/traces"
_LANGFUSE_HOST_DEFAULT = "https://cloud.langfuse.com"


def _build_langsmith_exporter() -> OTLPSpanExporter:
    """Build the LangSmith OTLP HTTP exporter with auth headers."""
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    endpoint = os.environ.get("LANGSMITH_OTEL_ENDPOINT", _LANGSMITH_OTEL_ENDPOINT_DEFAULT)
    return OTLPSpanExporter(
        endpoint=endpoint,
        headers={
            "x-api-key": api_key,
            "Langsmith-Project": os.environ.get("LANGSMITH_PROJECT", "ikigai"),
        },
    )


def _build_langfuse_exporter() -> OTLPSpanExporter:
    """Build the Langfuse OTLP HTTP exporter with HTTP Basic auth."""
    host = os.environ.get("LANGFUSE_HOST", _LANGFUSE_HOST_DEFAULT).rstrip("/")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    # Langfuse Basic auth header is base64(public_key:secret_key).
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    return OTLPSpanExporter(
        endpoint=f"{host}{_LANGFUSE_OTEL_PATH}",
        headers={"Authorization": f"Basic {auth}"},
    )


def init_tracing() -> None:
    """Initialize OpenTelemetry with LangSmith + Langfuse exporters.

    Idempotent — safe to call from multiple entry points in the same process.
    No-op if called twice. Each exporter is added only if its credentials are
    present in the environment, so this works for local-only development too.
    """
    global _INITIALIZED
    with _INIT_LOCK:
        if _INITIALIZED:
            return

        resource = Resource.create(
            {
                SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "ikigai-maintainer"),
                "deployment.environment": os.environ.get("IKIGAI_ENV", "local"),
            }
        )

        provider = TracerProvider(resource=resource)

        # LangSmith — primary, LLM observability
        if os.environ.get("LANGSMITH_API_KEY"):
            provider.add_span_processor(BatchSpanProcessor(_build_langsmith_exporter()))

        # Langfuse — secondary, stack traces + custom events
        if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
            provider.add_span_processor(BatchSpanProcessor(_build_langfuse_exporter()))

        trace.set_tracer_provider(provider)

        # Auto-instrumentation (best-effort; one missing lib shouldn't kill init).
        _try_instrument("opentelemetry.instrumentation.langchain", "LangchainInstrumentor")
        _try_instrument("opentelemetry.instrumentation.requests", "RequestsInstrumentor")
        _try_instrument("opentelemetry.instrumentation.sqlite3", "SQLite3Instrumentor")
        _try_instrument("opentelemetry.instrumentation.logging", "LoggingInstrumentor")

        _INITIALIZED = True


def _try_instrument(module_name: str, class_name: str) -> None:
    """Load and call .instrument() on a contrib instrumentor if importable.

    Any failure (ImportError, version mismatch, runtime error) is logged to
    stderr and swallowed — observability is best-effort and must never block
    the host application from starting.
    """
    try:
        import importlib

        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        cls().instrument()
    except Exception as e:  # noqa: BLE001 — best-effort, log and move on
        print(f"[otel_init] {class_name} not loaded: {e}", file=sys.stderr)


def get_tracer(name: str = "ikigai") -> trace.Tracer:
    """Return a tracer for manual spans. Safe to call before ``init_tracing()``.

    If init hasn't run yet, returns a proxy tracer from the no-op default
    provider — spans are dropped silently, no exception is raised. After
    ``init_tracing()`` runs (even from another module in the same process),
    subsequent calls return a real tracer bound to the configured provider.
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Flush all pending spans to both exporters.

    Call at process exit / end of CLI run. Without this, BatchSpanProcessor
    may drop the last few spans if the process exits before the next flush
    interval (default 5 s).
    """
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()  # type: ignore[attr-defined]
