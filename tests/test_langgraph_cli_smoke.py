"""M101c tests: `langgraph-cli` install + `langgraph validate` smoke.

Per M101c: install langgraph-cli[inmem] in src/ikigai/.venv so users can
boot the visual debugger. The dev server itself can't load the v2
graph (relative imports fail when loaded standalone — known issue,
fix tracked separately), but `validate` works and confirms the
langgraph.json config is well-formed.

Tests verify:
- `langgraph_cli` is installed and importable
- `langgraph_cli validate` exits 0 with the langgraph.json in repo root
- `langgraph_cli --help` lists the `dev` subcommand
"""
from __future__ import annotations

import os
import subprocess

import pytest

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir)
) if "__file__" in globals() else os.getcwd()


@pytest.fixture
def ikigai_python():
    p = os.path.join(REPO_ROOT, "src", "ikigai", ".venv", "Scripts", "python.exe")
    if not os.path.exists(p):
        pytest.skip(f"ikigai venv not found: {p}")
    return p


def test_langgraph_cli_installed(ikigai_python: str) -> None:
    """`langgraph_cli` must be importable in ikigai venv."""
    r = subprocess.run(
        [ikigai_python, "-c", "import langgraph_cli; print(langgraph_cli.__file__)"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert r.returncode == 0, f"langgraph_cli import failed: {r.stderr}"
    assert "langgraph_cli" in r.stdout


def test_langgraph_cli_help_lists_dev(ikigai_python: str) -> None:
    """`langgraph_cli --help` must list the `dev` subcommand (visual debugger)."""
    r = subprocess.run(
        [ikigai_python, "-m", "langgraph_cli", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert r.returncode == 0
    assert "dev" in r.stdout
    assert "Run LangGraph API server" in r.stdout or "dev server" in r.stdout.lower()


def test_langgraph_cli_validate_passes(ikigai_python: str) -> None:
    """`langgraph_cli validate` must succeed for repo's langgraph.json."""
    r = subprocess.run(
        [ikigai_python, "-m", "langgraph_cli", "validate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert r.returncode == 0, f"validate failed: {r.stderr}"
    assert "is valid" in r.stdout
    # Should find the registered graphs (pae_maintainer + ikigai_maintainer_v2)
    assert "graph" in r.stdout.lower()


def test_langgraph_cli_version(ikigai_python: str) -> None:
    """Capture installed langgraph-cli version for diagnostics."""
    r = subprocess.run(
        [ikigai_python, "-m", "langgraph_cli", "--version"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    # --version may or may not be supported; either way, just confirm
    # langgraph_cli is importable + executable.
    assert r.returncode in (0, 2)  # 0 = success, 2 = no --version flag (acceptable)
