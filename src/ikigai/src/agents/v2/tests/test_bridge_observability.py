"""OTel bridge observability tests — verifies mcp_bridge._call emits
`ikigai.bridge.{tool_name}` spans with the expected attributes.

Uses InMemorySpanExporter to capture spans without a real OTel collector.
The exporter is attached to a fresh TracerProvider so it doesn't interfere
with the production `init_tracing()` call in graph.py.

T-8.3.1 invariant: client-side spans (ikigai.bridge.*) are distinct from
server-side spans (ikigai.mcp.*) — see mcp_server/tracing.py:23 — so the
two layers never double-count in trace exporters.
"""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.ikigai.src.agents.v2 import mcp_bridge
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import FakeMcpServer


@pytest.fixture
def span_exporter(monkeypatch):
    """Attach an InMemorySpanExporter to a private TracerProvider.

    We swap mcp_bridge._tracer for the private provider's tracer so
    spans emitted by _call() land in our exporter. Production graph.py
    keeps using the real OpenTelemetry tracer.
    """
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    private_tracer = provider.get_tracer("ikigai.bridge")
    monkeypatch.setattr(mcp_bridge, "_tracer", private_tracer)
    return exporter


@pytest.fixture
def fake_server(monkeypatch):
    server = FakeMcpServer()
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)
    return server


def test_call_emits_bridge_span(span_exporter, fake_server):
    """Success path: span name = ikigai.bridge.<tool>, attrs tool.name + tool.duration_ms."""
    fake_server.canned_response("ikigai_observe_pav_state", qhe_score=0.75, regime="FOCUS")
    result = mcp_bridge.ikigai_observe_pav_state(date="2026-09-08")
    assert result == {"qhe_score": 0.75, "regime": "FOCUS"}

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "ikigai.bridge.ikigai_observe_pav_state"
    attrs = dict(span.attributes or {})
    assert attrs["tool.name"] == "ikigai_observe_pav_state"
    assert isinstance(attrs["tool.arguments_hash"], str)
    assert len(attrs["tool.arguments_hash"]) == 16
    assert isinstance(attrs["tool.duration_ms"], (int, float))
    assert attrs["tool.duration_ms"] >= 0


def test_call_emits_error_span_on_bridge_raise(span_exporter, monkeypatch):
    """Error path: StatusCode.ERROR set + tool.error.class/message populated; exception propagates."""

    class _BoomServer:
        def call(self, tool_name: str, args: dict) -> dict:
            raise RuntimeError("kaboom: synthetic MCP failure")

    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", _BoomServer())

    with pytest.raises(RuntimeError, match="kaboom"):
        mcp_bridge.ikigai_observe_pav_state(date="2026-09-08")

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "ikigai.bridge.ikigai_observe_pav_state"
    # OTel SDK sets span.status.status_code to StatusCode.ERROR on error spans.
    assert span.status.status_code.name == "ERROR"
    attrs = dict(span.attributes or {})
    assert attrs["tool.error.class"] == "RuntimeError"
    assert "kaboom" in attrs["tool.error.message"]
    assert isinstance(attrs["tool.error.traceback"], str)
    assert "RuntimeError" in attrs["tool.error.traceback"]
    assert isinstance(attrs["tool.duration_ms"], (int, float))
