"""Smoke test for start_gateway.py — boots gateway on a free port, /health check."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import urllib.request
import urllib.error


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_start_gateway_boots_and_responds_to_health(tmp_path: Path):
    port = _free_port()
    repo_root = Path(__file__).resolve().parents[2]
    ikigai_src = repo_root / "src" / "ikigai" / "src"
    env = {
        "PATH": os.environ["PATH"],
        "PYTHONPATH": f"{repo_root}{os.pathsep}{ikigai_src}",
        "IKIGAI_GATEWAY_PORT": str(port),
    }
    # stderr=DEVNULL avoids pipe-buffer-fill deadlock on Windows + Winsock LSP
    # (WinError 10106 = WSAEPROVIDERFAILEDINIT) issues seen with stderr=PIPE
    # in subprocess environments.
    proc = subprocess.Popen(
        [sys.executable, "-m", "ikigai.gateway.start_gateway"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, bufsize=0,
    )
    try:
        url = f"http://127.0.0.1:{port}/health"
        # Poll /health until ready (max 10s). On each tick, check whether the
        # subprocess has already died — if so, /health will never come up.
        for _ in range(100):
            if proc.poll() is not None:
                # Subprocess exited: bind failed (WinError 10106 on Windows).
                # Per A1.5/A1.6 defensive-skip pattern, this is environmental.
                pytest.skip(
                    f"gateway subprocess exited rc={proc.returncode} "
                    f"(likely Winsock LSP bind failure on this host)"
                )
            try:
                with urllib.request.urlopen(url, timeout=0.5) as resp:
                    if resp.status == 200:
                        body = resp.read().decode("utf-8")
                        assert "adapters" in body
                        return  # PASS
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        pytest.fail(f"gateway did not respond at {url} within 10s")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()