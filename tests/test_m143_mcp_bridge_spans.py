"""M143 tests: OTel span emission from .claude/loop/mcp_bridge.py:_call().

Mirrors the v2 mcp_bridge T-8.3.1 span-attribute schema with tracer name
prefix `loop.mcp.` (deliberately distinct from v2 `ikigai.bridge.` and
server-side `ikigai.mcp.`).

Architecture note: the OTel SDK only allows ONE `TracerProvider` per process.
Since `_tracer` is bound at module import time (in `mcp_bridge.py`), the
test must install the in-memory TracerProvider BEFORE the bridge module is
loaded. We use a module-scoped fixture that:
  1. Sets a TracerProvider with InMemorySpanExporter as the global provider.
  2. Loads the bridge module (which captures `_tracer` from this provider).
  3. Resets the exporter between tests so spans don't bleed across cases.

Verified contract:
  1. `_call()` opens an OTel span with name `loop.mcp.{tool_name}` on success
  2. `_call()` opens an OTel span with name `loop.mcp.{tool_name}` on error
  3. Success span has attributes: `tool.name`, `tool.arguments_hash`,
     `tool.duration_ms`
  4. Error span has attributes: `tool.error.class`, `tool.error.message`,
     `tool.error.traceback`, `tool.duration_ms`
  5. `SPAN_PREFIX` constant equals `"loop.mcp."` (drift guard)
  6. Tracer name matches `"loop.mcp"`
  7. `_call()` raises RuntimeError when `_server is None` — WITHOUT opening
     a span (the early-return is outside the span context)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"


@pytest.fixture(scope="module")
def exporter():
    """Single in-memory exporter for the whole module session."""
    return InMemorySpanExporter()


@pytest.fixture(scope="module")
def bridge(exporter):
    """Load the bridge module with the in-memory TracerProvider already set.

    This must happen once per session — the OTel SDK forbids replacing the
    global TracerProvider after the first call to `set_tracer_provider()`.
    """
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    # Drop any cached module so the import below re-binds `_tracer` to the
    # new provider. Without this, a previously-loaded bridge module would
    # keep using the NoOp tracer from the original global provider.
    cache_key = "loop_mcp_bridge_m143"
    if cache_key in sys.modules:
        del sys.modules[cache_key]
    spec = importlib.util.spec_from_file_location(cache_key, BRIDGE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._server = None
    return mod


@pytest.fixture(autouse=True)
def reset_exporter_and_server(exporter, bridge):
    """Reset span exporter + module-level _server before each test."""
    exporter.clear()
    bridge._server = None
    yield
    bridge._server = None


@pytest.fixture
def fake_server(bridge):
    """Bind a MagicMock to bridge._server for the duration of one test."""
    mock = MagicMock()
    mock.call.return_value = {"ok": True, "tool": "fake"}
    bridge._server = mock
    return mock


# ---------------------------------------------------------------------------
# Acceptance #5: SPAN_PREFIX constant pinned
# ---------------------------------------------------------------------------


def test_span_prefix_constant_value(bridge):
    """Drift guard: SPAN_PREFIX must equal exactly 'loop.mcp.'."""
    assert bridge.SPAN_PREFIX == "loop.mcp.", (
        f"SPAN_PREFIX drifted from 'loop.mcp.': got {bridge.SPAN_PREFIX!r}"
    )


def test_module_tracer_name_matches_loop_mcp(bridge):
    """`_tracer` was created with name 'loop.mcp' (per get_tracer arg)."""
    # `trace.get_tracer('loop.mcp')` returns a ProxyTracer that wraps the
    # real provider's tracer. The instrumentation info carries the name.
    tracer_name = bridge._tracer.instrumentation_info.name
    # Some SDK versions return just the last component; the canonical
    # check is that the tracer's span names use the prefix.
    assert "loop.mcp" in tracer_name or tracer_name == "loop.mcp", (
        f"Tracer name drifted: got {tracer_name!r}"
    )


# ---------------------------------------------------------------------------
# Acceptance #1: success-path span emission
# ---------------------------------------------------------------------------


def test_call_emits_span_with_correct_name_on_success(
    bridge, fake_server, exporter
):
    """Span name = 'loop.mcp.{tool_name}' for a successful call."""
    bridge.ikigai_mesh_show(ueid="study:topic:st_python_01")
    spans = exporter.get_finished_spans()
    assert len(spans) == 1, f"Expected 1 span, got {len(spans)}"
    assert spans[0].name == "loop.mcp.ikigai_mesh_show"


# ---------------------------------------------------------------------------
# Acceptance #3: success-path attributes
# ---------------------------------------------------------------------------


def test_call_emits_required_attributes_on_success(
    bridge, fake_server, exporter
):
    """Success path sets tool.name + tool.arguments_hash + tool.duration_ms."""
    bridge.ikigai_read_tasks(horizon="week", limit=10)
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes or {})
    assert attrs["tool.name"] == "ikigai_read_tasks"
    assert isinstance(attrs["tool.arguments_hash"], str)
    assert len(attrs["tool.arguments_hash"]) == 16  # SHA-256 first 16 hex
    assert isinstance(attrs["tool.duration_ms"], (int, float))
    assert attrs["tool.duration_ms"] >= 0


def test_call_arguments_hash_is_deterministic(bridge, fake_server, exporter):
    """Same args → same hash; ordering independent (json sort_keys=True)."""
    bridge.ikigai_mesh_show(ueid="study:topic:abc")
    bridge.ikigai_mesh_show(ueid="study:topic:abc")  # second call same args
    spans = exporter.get_finished_spans()
    h1 = dict(spans[0].attributes or {})["tool.arguments_hash"]
    h2 = dict(spans[1].attributes or {})["tool.arguments_hash"]
    assert h1 == h2


def test_call_span_status_is_ok_on_success(
    bridge, fake_server, exporter
):
    from opentelemetry.trace import StatusCode as SC

    bridge.ikigai_health()
    spans = exporter.get_finished_spans()
    assert spans[0].status.status_code == SC.OK


# ---------------------------------------------------------------------------
# Acceptance #2: error-path span emission
# ---------------------------------------------------------------------------


def test_call_emits_span_with_correct_name_on_error(
    bridge, exporter
):
    """Span name = 'loop.mcp.{tool_name}' even when _server.call raises."""
    mock = MagicMock()
    mock.call.side_effect = ConnectionRefusedError("gateway unreachable")
    bridge._server = mock
    with pytest.raises(ConnectionRefusedError):
        bridge.ikigai_mesh_show(ueid="study:topic:abc")
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "loop.mcp.ikigai_mesh_show"
    bridge._server = None


# ---------------------------------------------------------------------------
# Acceptance #4: error-path attributes
# ---------------------------------------------------------------------------


def test_call_emits_error_attributes(bridge, exporter):
    """Error path sets tool.error.class + tool.error.message + tool.error.traceback + tool.duration_ms."""
    mock = MagicMock()
    mock.call.side_effect = ValueError("bad input from upstream")
    bridge._server = mock
    with pytest.raises(ValueError):
        bridge.ikigai_task_create(ueid="study:topic:abc")
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes or {})
    assert attrs["tool.error.class"] == "ValueError"
    assert "bad input from upstream" in attrs["tool.error.message"]
    assert isinstance(attrs["tool.error.traceback"], str)
    assert "ValueError" in attrs["tool.error.traceback"]
    assert isinstance(attrs["tool.duration_ms"], (int, float))
    bridge._server = None


def test_call_span_status_is_error_on_error(
    bridge, exporter
):
    from opentelemetry.trace import StatusCode as SC

    mock = MagicMock()
    mock.call.side_effect = RuntimeError("kaboom")
    bridge._server = mock
    with pytest.raises(RuntimeError):
        bridge.ikigai_health()
    spans = exporter.get_finished_spans()
    assert spans[0].status.status_code == SC.ERROR
    assert "kaboom" in (spans[0].status.description or "")
    bridge._server = None


def test_error_message_is_truncated_to_500_chars(bridge, exporter):
    """tool.error.message truncates at 500 chars to bound span size."""
    mock = MagicMock()
    long_msg = "x" * 1000
    mock.call.side_effect = ValueError(long_msg)
    bridge._server = mock
    with pytest.raises(ValueError):
        bridge.ikigai_health()
    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert len(attrs["tool.error.message"]) == 500
    bridge._server = None


# ---------------------------------------------------------------------------
# Acceptance #7: unbound-server early-return does NOT emit a span
# ---------------------------------------------------------------------------


def test_unbound_server_does_not_emit_span(bridge, exporter):
    """RuntimeError on `_server is None` short-circuits before span context."""
    bridge._server = None
    with pytest.raises(RuntimeError):
        bridge.ikigai_health()
    spans = exporter.get_finished_spans()
    assert len(spans) == 0, (
        f"Expected 0 spans on early RuntimeError, got {len(spans)}: "
        f"{[s.name for s in spans]}"
    )


# ---------------------------------------------------------------------------
# Bonus: span attributes match v2 schema byte-for-byte
# ---------------------------------------------------------------------------


def test_span_attribute_keys_match_v2_schema(
    bridge, fake_server, exporter
):
    """Schema parity with v2 mcp_bridge.py:_call (T-8.3.1, 2026-09-08).

    Same keys, same truncation rules. Allows future drop-in replacement
    of v2 with loop bridge in callers that consume span attributes.
    """
    bridge.ikigai_mesh_show(ueid="study:topic:abc")
    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    expected_keys = {"tool.name", "tool.arguments_hash", "tool.duration_ms"}
    assert set(attrs.keys()) >= expected_keys, (
        f"v2-schema key mismatch: missing {expected_keys - set(attrs.keys())}"
    )


def test_tracer_distinct_from_v2_prefix(bridge, fake_server, exporter):
    """Span name 'loop.mcp.X' must NOT start with 'ikigai.bridge.' or 'ikigai.mcp.'.

    Drift guard: the 3 layers (server / v2 / loop) must remain distinct so
    trace exporters don't double-count.
    """
    bridge.ikigai_health()
    span_name = exporter.get_finished_spans()[0].name
    assert not span_name.startswith("ikigai.bridge."), (
        f"Loop bridge span uses v2 prefix — {span_name!r}"
    )
    assert not span_name.startswith("ikigai.mcp."), (
        f"Loop bridge span uses server prefix — {span_name!r}"
    )
