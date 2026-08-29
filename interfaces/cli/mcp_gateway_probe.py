"""Probe MCP gateway status via pidfile + process-alive check.

Used by `interfaces.cli.server.backend_status()` to report real running
state for the `mcp_gateway` backend process (B3.4).

For B3.4 this answers only "is the gateway process alive?". A live
health-resource probe is deferred to B3.5 (planned via a sidecar JSON
file the gateway writes on startup, so we don't spawn a separate
MCP stdio subprocess for the probe — too expensive for status checks).

Logic:
  - pidfile missing       → running=False, pid=None
  - pidfile unreadable    → running=False, pid=None (no crash)
  - pidfile + PID alive   → running=True, pid=<pid>, started_at=<mtime>
  - pidfile + PID dead    → running=False, pid=None (stale pidfile)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _is_pid_alive(pid: int) -> bool:
    """Cross-platform check whether pid is a running process.

    Windows: uses kernel32 OpenProcess + GetExitCodeProcess.
    POSIX: uses os.kill(pid, 0) signal-0 probe (raises if dead).
    """
    if pid <= 0:
        return False
    try:
        if os.name == "nt":  # Windows
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle == 0:
                return False
            try:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                return exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        else:  # POSIX
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def probe_mcp_gateway(pidfile_path: Path) -> dict[str, Any]:
    """Probe mcp_gateway status via pidfile.

    Args:
        pidfile_path: path to pidfile (e.g. data/run/mcp_gateway.pid)

    Returns:
        {running: bool, pid: int | None, started_at: str | None}
        Shape matches other backend_status() rows (no extra fields).
    """
    result: dict[str, Any] = {
        "running": False,
        "pid": None,
        "started_at": None,
    }

    if not pidfile_path.exists():
        return result

    try:
        pid = int(pidfile_path.read_text().strip())
    except (ValueError, OSError):
        return result

    # Capture pidfile mtime as "started_at" (ISO timestamp would be nice but
    # backend_status() shape currently uses str-coerced values; defer parsing).
    result["started_at"] = str(pidfile_path.stat().st_mtime)

    if _is_pid_alive(pid):
        result["running"] = True
        result["pid"] = pid

    return result


__all__ = ["probe_mcp_gateway", "_is_pid_alive"]
