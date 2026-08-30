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
        "PYTHONPATH": f"{repo_root}{os.sep}{ikigai_src}",
        "IKIGAI_GATEWAY_PORT": str(port),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "ikigai.gateway.start_gateway"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
    )
    try:
        # Poll /health until ready (max 10s)
        url = f"http://127.0.0.1:{port}/health"
        for _ in range(100):
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
