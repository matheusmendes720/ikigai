"""Shared fixtures for fork MCP server E2E tests.

Per spec §10 + verify-agent-fabricated-failures memory: tests MUST handle MCP
absence via pytest.skip (the fork server module may not be importable in CI
without PYTHONPATH adjustments). Per B5.B pattern: real subprocess + JSON-RPC.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def skip_if_no_module() -> None:
    """Skip the test if the fork module cannot be imported.

    Per B5.B + B6.4 lesson: tests for MCP-dependent code must handle MCP
    absence (e.g., module not on PYTHONPATH) by skipping gracefully.
    """
    # We use the python executable from sys.executable; the actual module
    # import check happens at the server_process fixture level.
    if shutil.which(sys.executable) is None:
        pytest.skip(f"python executable not found: {sys.executable}")


@pytest.fixture
def server_process_factory(tmp_path: Path):
    """Factory that spawns a fork MCP server subprocess and yields its proc + stdio.

    Usage:
        def test_something(server_process_factory, skip_if_no_module):
            with server_process_factory("solverforge_calendar.server") as (proc, stdin, stdout):
                # write JSON-RPC request to stdin, read response from stdout
                ...
    """
    spawned: list[subprocess.Popen] = []

    def _factory(module: str, *, env: dict[str, str] | None = None) -> Iterator[tuple]:
        # Add repo root and src/ikigai to PYTHONPATH so the fork module resolves
        # AND so `from ikigai.gateway.stdio_server_base import ...` works.
        repo_root = Path(__file__).resolve().parents[3]
        ikigai_src = repo_root / "src" / "ikigai" / "src"
        proc_env = {
            **__import__("os").environ,
            "PYTHONPATH": f"{repo_root}{__import__("os").sep}{ikigai_src}",
            **(env or {}),
        }
        proc = subprocess.Popen(
            [sys.executable, "-m", module],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,  # critical for JSON-RPC framing on Windows
            env=proc_env,
        )
        spawned.append(proc)
        try:
            yield proc, proc.stdin, proc.stdout
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()

    yield _factory

    for proc in spawned:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
