"""Tests for mcp_gateway_probe — pidfile + process-alive check.

The health resource probe is deferred to B3.5 (gated on a sidecar JSON
file the gateway writes on startup). For B3.4, probe_mcp_gateway
answers only "is the gateway process alive?" via pidfile.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


def test_pidfile_alive_returns_running() -> None:
    """Pidfile pointing to current PID → running=True, pid=os.getpid()."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway
    current_pid = os.getpid()

    with tempfile.TemporaryDirectory() as tmpdir:
        pidfile = Path(tmpdir) / "mcp_gateway.pid"
        pidfile.write_text(str(current_pid))

        result = probe_mcp_gateway(pidfile_path=pidfile)

    assert result["running"] is True
    assert result["pid"] == current_pid
    assert result["started_at"] is not None  # file mtime


def test_pidfile_stale_returns_not_running() -> None:
    """Pidfile pointing to a dead PID → running=False, pid=None."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    with tempfile.TemporaryDirectory() as tmpdir:
        pidfile = Path(tmpdir) / "mcp_gateway.pid"
        pidfile.write_text("99999")  # very unlikely to be alive

        result = probe_mcp_gateway(pidfile_path=pidfile)

    assert result["running"] is False
    assert result["pid"] is None


def test_pidfile_missing_returns_not_running() -> None:
    """Missing pidfile → running=False, pid=None."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    with tempfile.TemporaryDirectory() as tmpdir:
        result = probe_mcp_gateway(pidfile_path=Path(tmpdir) / "missing.pid")

    assert result["running"] is False
    assert result["pid"] is None


def test_pidfile_invalid_content_returns_not_running() -> None:
    """Pidfile with non-numeric content → running=False, pid=None (no crash)."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    with tempfile.TemporaryDirectory() as tmpdir:
        pidfile = Path(tmpdir) / "mcp_gateway.pid"
        pidfile.write_text("not-a-number")

        result = probe_mcp_gateway(pidfile_path=pidfile)

    assert result["running"] is False
    assert result["pid"] is None
