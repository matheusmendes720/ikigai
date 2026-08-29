"""Tests for B3.5 mcp_inspect.py contract test script.

Validates:
  - scripts/mcp_inspect.py exists and is parseable
  - --help exits 0 and prints usage
  - module file compiles (no SyntaxError)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "mcp_inspect.py"


def test_mcp_inspect_script_exists() -> None:
    assert SCRIPT.exists(), f"missing {SCRIPT}"
    assert SCRIPT.is_file()


def test_mcp_inspect_script_compiles() -> None:
    """Source file is parseable Python (no SyntaxError)."""
    with open(SCRIPT, "rb") as f:
        source = f.read()
    compile(source, str(SCRIPT), "exec")


def test_mcp_inspect_script_help() -> None:
    """`python scripts/mcp_inspect.py --help` exits 0 and prints usage."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
    )
    assert proc.returncode == 0, f"--help failed: {proc.stderr}"
    assert "usage" in proc.stdout.lower() or "mcp" in proc.stdout.lower()
