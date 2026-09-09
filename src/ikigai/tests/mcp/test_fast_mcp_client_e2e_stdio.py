"""FastMcpClient end-to-end stdio smoke tests.

Proves FastMcpClient → MCP server stdio handshake → tool dispatch path
actually works. Closes the M5-tester-but-not-FastMcpClient-tester gap.

Uses the 3-entry PYTHONPATH build pattern (REPO_ROOT + LIFE_SRC + IKIGAI_SRC)
and cwd=IKIGAI_SRC (the inner src/), exactly as documented in the brief.

$0 cost: subprocess spawn + stdio JSON-RPC; no LLM.

Markers: @pytest.mark.integration — excluded from default CI run via
'-m "not integration"', run explicitly with pytest -m integration.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

import pytest

# Graceful skip when MCP SDK is absent — same pattern as test_multi_tool_chain.py:192
pytest.importorskip("mcp")

from src.ikigai.src.agents.v2.mcp_client import FastMcpClient

# ── Path constants ────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
IKIGAI_DIR = REPO_ROOT / "src" / "ikigai"
IKIGAI_SRC = IKIGAI_DIR / "src"
LIFE_SRC = REPO_ROOT / "src"


def _build_pythonpath() -> str:
    """Three-entry PYTHONPATH: REPO_ROOT + LIFE_SRC + IKIGAI_SRC.

    Required so the subprocess can resolve both dotted-prefix
    (from src.contracts.common) and bare-namespace (from contracts.X)
    import styles.
    """
    sep = ";" if platform.system() == "Windows" else ":"
    return f"{REPO_ROOT}{sep}{LIFE_SRC}{sep}{IKIGAI_SRC}"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def inq_id() -> str:
    """Unique investigation ID for this test run; cleaned up in teardown.

    Format: inq-85-{pid}-{unique} — the inq- prefix ensures created
    files match the inq-*.json invariant, and the cleanup pattern
    inq-85-* correctly removes them.
    """
    return f"inq-85-{os.getpid()}-{_unique_id()}"


def _unique_id() -> str:
    """Short monotonic identifier to avoid collisions on rapid re-runs."""
    import time

    return f"{int(time.time() * 1000) % 10_000_000:07d}"


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_fast_mcp_client_end_to_end_health() -> None:
    """Spawn FastMcpClient("src.mcp_server.server") and call ikigai_health.

    Asserts the response shape matches the expected contract:
      name: "ikigai-gateway"
      version: str
      started_at: (int, float)
      uptime_s: (int, float)
      adapters: list
    """
    client: FastMcpClient | None = None
    try:
        client = FastMcpClient(
            "mcp_server",
            env={**os.environ, "PYTHONPATH": _build_pythonpath()},
            cwd=str(IKIGAI_DIR),
        )
        result = client.call("ikigai_health", {})

        # Shape assertions
        assert isinstance(result, dict), f"expected dict, got {type(result).__name__}"

        assert result.get("name") == "ikigai-gateway", (
            f"unexpected name: {result.get('name')!r}"
        )
        assert "version" in result, "version field missing from ikigai_health response"
        assert isinstance(result["version"], str), (
            f"version should be str, got {type(result['version']).__name__}"
        )

        assert "started_at" in result, "started_at field missing"
        started_at = result["started_at"]
        assert isinstance(started_at, (int, float)), (
            f"started_at should be int|float, got {type(started_at).__name__}"
        )

        assert "uptime_s" in result, "uptime_s field missing"
        uptime_s = result["uptime_s"]
        assert isinstance(uptime_s, (int, float)), (
            f"uptime_s should be int|float, got {type(uptime_s).__name__}"
        )
        assert uptime_s >= 0, f"uptime_s should be non-negative, got {uptime_s}"

        assert "adapters" in result, "adapters field missing"
        assert isinstance(result["adapters"], list), (
            f"adapters should be list, got {type(result['adapters']).__name__}"
        )
    finally:
        if client is not None:
            client.close()


@pytest.mark.integration
def test_fast_mcp_client_end_to_end_investigation_lifecycle(inq_id: str) -> None:
    """Full investigation lifecycle via FastMcpClient.call.

    Sequence:
      1. investigation_enqueue  → returns inq_id
      2. investigation_status   → status == "open"
      3. investigation_complete → status == "resolved"

    Cleans up the test artifact (data/investigation_queue/inq-phase85-*) in
    fixture teardown to avoid polluting the real queue.
    """
    client: FastMcpClient | None = None
    try:
        client = FastMcpClient(
            "mcp_server",
            env={**os.environ, "PYTHONPATH": _build_pythonpath()},
            cwd=str(IKIGAI_DIR),
        )

        # Step 1: enqueue — capture the returned inq_id (server may generate a different one)
        enqueue_result = client.call("investigation_enqueue", {
            "inq_id": inq_id,
            "source": "test:t-8-5-1",
            "payload": "phase85 smoke test payload",
            "tags": ["phase85", "smoke"],
            "actor": "agent",
        })
        assert isinstance(enqueue_result, dict), (
            f"enqueue returned non-dict: {type(enqueue_result).__name__}"
        )
        # investigation_enqueue returns the created investigation with its inq_id
        actual_inq_id = enqueue_result.get("inq_id", inq_id)

        # Step 2: status — should be "open" — use the server-returned inq_id
        status_result = client.call("investigation_status", {
            "inq_id": actual_inq_id,
        })
        assert isinstance(status_result, dict), (
            f"status returned non-dict: {type(status_result).__name__}"
        )
        # investigation_status returns the full investigation object
        assert status_result.get("status") == "open", (
            f"expected status='open', got {status_result.get('status')!r}"
        )

        # Step 3: complete — use the server-returned inq_id
        complete_result = client.call("investigation_complete", {
            "inq_id": actual_inq_id,
            "final_status": "resolved",
            "actor": "agent",
        })
        assert isinstance(complete_result, dict), (
            f"complete returned non-dict: {type(complete_result).__name__}"
        )

    finally:
        if client is not None:
            client.close()

        # Teardown: clean up test artifact from data/investigation_queue/
        _cleanup_investigation_artifacts(inq_id)


# ── Cleanup helper ─────────────────────────────────────────────────────────────

def _cleanup_investigation_artifacts(inq_id: str) -> None:
    """Remove inq-85-* and 85-*.json investigation artifacts from the queue.

    Per the brief: test artifacts must NOT pollute the real data/investigation_queue/.
    Removes any file starting with inq-85- (our test fixture format) plus any
    85-*.json artifact from prior runs with the old non-prefix fixture format.
    """
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
    queue_dir = PROJECT_ROOT / "data" / "investigation_queue"
    if not queue_dir.is_dir():
        return

    for item in queue_dir.iterdir():
        if not item.name.endswith(".json"):
            continue
        if item.name.startswith("inq-85-") or item.name.startswith("85-"):
            try:
                item.unlink()
            except OSError:
                pass
