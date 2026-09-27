"""M146 tests: production binding for .claude/loop/mcp_bridge.py.

Verifies:
  1. `init_observability()` is idempotent and safe without creds
  2. `_parse_resource_envelope()` handles all 5 FastMCP shapes correctly
  3. `bind_server()` raises a clear error if subprocess can't start
  4. `unbind_server()` is safe to call when never bound (no-op)
  5. End-to-end smoke (xfail if `python -m mcp_server` unreachable):
     `bind_server()` → real subprocess → `ikigai_health()` returns dict

The end-to-end smoke is `@pytest.mark.xfail(strict=False)` because most
test machines don't have the IKIGAI venv installed. Production users
who DO have it will see the smoke pass.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_bridge.py"
RUNTIME_PATH = REPO_ROOT / ".claude" / "loop" / "mcp_runtime.py"


# ---------------------------------------------------------------------------
# Module fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bridge():
    """Load `.claude/loop/mcp_bridge.py` as a module object.

    Registers in sys.modules so `mcp_runtime._get_mcp_bridge()` can find
    it (it iterates sys.modules looking for the bridge path).
    """
    spec = importlib.util.spec_from_file_location("loop_mcp_bridge_m146", BRIDGE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["loop_mcp_bridge_m146"] = mod  # register so mcp_runtime can find it
    spec.loader.exec_module(mod)
    mod._server = None
    return mod


@pytest.fixture(scope="module")
def runtime():
    """Load `.claude/loop/mcp_runtime.py` as a module object."""
    spec = importlib.util.spec_from_file_location("loop_mcp_runtime_m146", RUNTIME_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Acceptance #1: init_observability is idempotent
# ---------------------------------------------------------------------------


def test_init_observability_returns_bool(runtime):
    """Returns True on first call, False on subsequent calls."""
    # We can't easily test the True case without actually initializing OTel,
    # but we can verify the function exists and is callable, and that calling
    # it twice doesn't raise.
    try:
        result1 = runtime.init_observability()
        result2 = runtime.init_observability()
        # Either both True (initialized then re-noop) or both False (already
        # initialized by another module); idempotency means no exception.
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)
    except ImportError:
        # IKIGAI venv not on PYTHONPATH — acceptable, skip
        pytest.skip("IKIGAI observability module not importable")


# ---------------------------------------------------------------------------
# Acceptance #2: _parse_resource_envelope handles all 5 shapes
# ---------------------------------------------------------------------------


def test_parse_envelope_shape_1_single_dict(bridge):
    """Shape 1: single dict with 'uri' or 'text' or 'mimeType' keys → as-is."""
    result = bridge._parse_resource_envelope(
        {"uri": "ueid://x", "mimeType": "text/plain", "text": "hello"}
    )
    assert result == {"uri": "ueid://x", "mimeType": "text/plain", "text": "hello"}


def test_parse_envelope_shape_1_dict_without_envelope_keys(bridge):
    """Dict without envelope-shape keys → wrapped in `{"raw": payload}`."""
    result = bridge._parse_resource_envelope({"foo": "bar", "baz": 1})
    assert result == {"raw": {"foo": "bar", "baz": 1}}


def test_parse_envelope_shape_2_list_of_dicts(bridge):
    """Shape 2: list of dicts → concat `.text`, return joined + items."""
    payload = [
        {"uri": "u://a", "mimeType": "text/plain", "text": "foo"},
        {"uri": "u://b", "mimeType": "text/plain", "text": "bar"},
    ]
    result = bridge._parse_resource_envelope(payload)
    assert result["text"] == "foo\nbar"
    assert len(result["items"]) == 2


def test_parse_envelope_shape_2_list_with_json_text(bridge):
    """List with JSON-typed text → parse the joined text into a dict."""
    import json as _json

    class JsonContent:
        def __init__(self, text):
            self.uri = None
            self.mimeType = "application/json"
            self.text = text

    payload = [JsonContent(_json.dumps({"foo": 1, "bar": [1, 2, 3]}))]
    result = bridge._parse_resource_envelope(payload)
    assert result == {"foo": 1, "bar": [1, 2, 3]}


def test_parse_envelope_shape_2_list_with_blob(bridge):
    """List with blob (binary) → wrap as `{"blob": ...}`."""
    class BlobContent:
        def __init__(self, blob):
            self.uri = "u://x"
            self.mimeType = "application/octet-stream"
            self.blob = blob

    payload = [BlobContent("base64data==")]
    result = bridge._parse_resource_envelope(payload)
    assert result == {
        "contents": [
            {"uri": "u://x", "mimeType": "application/octet-stream", "blob": "base64data=="}
        ]
    }


def test_parse_envelope_shape_3_str(bridge):
    """Shape 3: raw string → `{"raw": payload}`."""
    result = bridge._parse_resource_envelope("just a string")
    assert result == {"raw": "just a string"}


def test_parse_envelope_shape_3_bytes(bridge):
    """Shape 3: raw bytes → `{"raw": payload}`."""
    result = bridge._parse_resource_envelope(b"\x00\x01\x02")
    assert result == {"raw": b"\x00\x01\x02"}


def test_parse_envelope_shape_4_fallback(bridge):
    """Shape 4: anything else → `{"raw": payload}`."""
    result = bridge._parse_resource_envelope(42)
    assert result == {"raw": 42}


def test_parse_envelope_empty_list(bridge):
    """Empty list → `{"contents": []}`."""
    result = bridge._parse_resource_envelope([])
    assert result == {"contents": []}


def test_parse_envelope_list_with_mixed_items(bridge):
    """List with non-dict, non-content items → `{"raw": str(item)}` fallback."""
    payload = [42, "string-item", None]
    result = bridge._parse_resource_envelope(payload)
    assert "contents" in result
    assert len(result["contents"]) == 3
    assert result["contents"][0] == {"raw": "42"}


# ---------------------------------------------------------------------------
# Acceptance #3: bind_server raises a clear error when subprocess can't start
# ---------------------------------------------------------------------------


def test_bind_server_raises_when_ikigai_src_missing(runtime, monkeypatch):
    """If IKIGAI_SRC_DIR doesn't exist, bind_server raises FileNotFoundError."""
    # Force IKIGAI_SRC_DIR to a nonexistent path
    monkeypatch.setattr(runtime, "IKIGAI_SRC_DIR", Path("/nonexistent/path"))
    with pytest.raises(FileNotFoundError) as exc_info:
        runtime.bind_server()
    assert "IKIGAI source dir not found" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Acceptance #4: unbind_server is safe when never bound
# ---------------------------------------------------------------------------


def test_unbind_server_is_safe_when_never_bound(runtime, bridge):
    """unbind_server() should no-op if bind_server() was never called."""
    bridge._server = None
    bridge._runtime_loop = None
    bridge._runtime_thread = None
    # Should not raise
    runtime.unbind_server()
    # And again (idempotent)
    runtime.unbind_server()


# ---------------------------------------------------------------------------
# Acceptance #5: end-to-end smoke (xfail if MCP server unreachable)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (REPO_ROOT / "src" / "ikigai" / ".venv" / "Scripts" / "python.exe").exists(),
    reason="IKIGAI venv not installed at src/ikigai/.venv",
)
def test_bind_server_smoke_ikigai_health(runtime, bridge):
    """bind_server() → subprocess → ikigai_health() returns dict.

    The real production binding smoke test. M147 fixed the Windows stdio
    hang so this should PASS on machines with the IKIGAI venv installed.
    Skip (not xfail) on machines without the venv so CI stays green.
    """
    runtime.bind_server()
    try:
        result = bridge.ikigai_health()
        assert isinstance(result, dict)
        # Real response should have name + version fields
        assert "name" in result
        assert "version" in result
    finally:
        runtime.unbind_server()


# ---------------------------------------------------------------------------
# Acceptance #6: mcp_bridge + mcp_runtime coexist without circular import
# ---------------------------------------------------------------------------


def test_runtime_imports_bridge_without_circular(bridge, runtime):
    """bind_server() must be able to import mcp_bridge without a cycle."""
    # Just verify both modules loaded successfully — no ImportError.
    assert bridge is not None
    assert runtime is not None
    # And the runtime has the expected public API
    assert hasattr(runtime, "bind_server")
    assert hasattr(runtime, "unbind_server")
    assert hasattr(runtime, "init_observability")
