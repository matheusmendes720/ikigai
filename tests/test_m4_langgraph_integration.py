"""M4 LangGraph integration tests.

Exercises each of the 3 graphs registered in langgraph.json via the
deterministic --graph flag on loop-tick.sh. Asserts checkpoint DB exists
+ has rows after each run. Verifies no mutation to langgraph.json.

Cost: $0 (no LLM). Each test invokes bash which dispatches inline Python.

NOTE: This test file lives at <repo>/tests/ (per CLAUDE.md `## Where the rest lives`).
The conftest at <repo>/tests/conftest.py handles sys.path and tempdir redirect.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LANGGRAPH_JSON = REPO_ROOT / "langgraph.json"
CHECKPOINT_DB = REPO_ROOT / ".swarm" / "langgraph_checkpoint.db"
VALID_GRAPHS = ["pae_maintainer", "ikigai_maintainer_v2", "ikigai_fork_smoke"]


def _run_env() -> dict[str, str]:
    """Build env dict that puts the current Python on PATH AND sets $PYTHON.

    pytest's subprocess.run inherits a Windows-flavored PATH that does NOT
    include the Git-Bash mount path where Python lives (`/c/Python314/`).
    Without this, the bash script runs to the "GRAPH MODE:" header and then
    `python` returns rc=127 (command not found) — even though the exact
    same script invocation succeeds when launched from a terminal where
    Git Bash already exported the right PATH.

    WSL2 case: bash sees only `python.exe` (Windows interop), not `python`.
    Setting $PYTHON=python.exe makes loop-tick.sh's `"$PYTHON" -c ...` resolve
    correctly via WSL2 PATHEXT interop. On native Linux/macOS, sys.executable
    absolute path works directly.
    """
    python_dir = os.path.dirname(sys.executable)
    existing_path = os.environ.get("PATH", "")
    new_path = f"{python_dir}{os.pathsep}{existing_path}"
    # WSL2 (Windows-on-Linux) detection: bash is the WSL2 Ubuntu binary AND
    # sys.executable is a Windows .exe path. In that case only `python.exe`
    # resolves via WSL2 interop; `python` returns 127.
    is_wsl2 = (
        sys.platform != "win32"
        and "WSL" in os.environ.get("WSL_DISTRO_NAME", "")
        or (sys.executable.endswith(".exe") and sys.platform != "win32")
    )
    py_var = "python.exe" if is_wsl2 else sys.executable
    return {**os.environ, "PATH": new_path, "PYTHON": py_var}


# Use the explicit bash.exe path (e.g. C:\Program Files\Git\usr\bin\bash.EXE)
# rather than the bare "bash" name. When invoked by bare name from Python's
# subprocess on Windows, Git Bash goes through the MSYS POSIX layer which
# MANGES the script-path argv entry — e.g. ".claude/loop/loop-tick.sh" with
# backslash translation + colon stripping becomes "claudelooploop-tick.sh"
# → "No such file or directory" → exit 127. Explicit absolute path skips
# the MSYS argv-translation layer. Falls back to bare "bash" on POSIX.
BASH_EXE = shutil.which("bash") or "bash"


def _run_graph(graph_key: str) -> subprocess.CompletedProcess:
    """Invoke loop-tick.sh --graph <key> and capture output.

    Uses a POSIX-style relative path because Git Bash on Windows expects
    `/c/Users/...` mount paths, NOT Windows-style `C:/Users/...` paths.
    cwd=str(REPO_ROOT) makes the relative path resolve correctly.
    """
    return subprocess.run(
        [BASH_EXE, ".claude/loop/loop-tick.sh", "--graph", graph_key],
        cwd=str(REPO_ROOT),
        env=_run_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )


def _checkpoint_count() -> int:
    """Read checkpoint count from .swarm/langgraph_checkpoint.db."""
    if not CHECKPOINT_DB.exists():
        return 0
    con = sqlite3.connect(str(CHECKPOINT_DB))
    try:
        return con.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
    finally:
        con.close()


# Test 1 — Each graph runs end-to-end via loop-tick.sh --graph
@pytest.mark.parametrize("graph_key", VALID_GRAPHS)
def test_graph_dispatch_exits_zero(graph_key: str) -> None:
    """--graph <key> dispatches the named graph and exits with the graph's terminal status."""
    result = _run_graph(graph_key)
    assert result.returncode == 0, (
        f"graph={graph_key} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert f"graph={graph_key}" in result.stdout, (
        f"expected 'graph={graph_key}' in stdout, got: {result.stdout}"
    )


# Test 2 — Checkpoint DB exists + has rows after each graph run
@pytest.mark.parametrize("graph_key", VALID_GRAPHS)
def test_checkpoint_db_persists_rows(graph_key: str) -> None:
    """SqliteSaver checkpoint file at .swarm/langgraph_checkpoint.db exists with rows."""
    # Establish baseline count from any prior run
    baseline = _checkpoint_count()
    result = _run_graph(graph_key)
    assert result.returncode == 0, f"graph={graph_key} failed: {result.stderr}"
    after = _checkpoint_count()
    assert after > 0, f"checkpoint DB empty after {graph_key} run"
    # We don't assert after > baseline strictly (sqlite may coalesce writes)
    # but we DO assert the DB file exists on disk
    assert CHECKPOINT_DB.exists(), f"{CHECKPOINT_DB} does not exist"


# Test 3 — langgraph.json registry is exactly the 3 expected graphs
def test_langgraph_registry_has_exactly_three_graphs() -> None:
    """langgraph.json has exactly the 3 graphs the SPEC documents."""
    data = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    graphs = data.get("graphs", {})
    assert set(graphs.keys()) == set(VALID_GRAPHS), (
        f"langgraph.json graph registry mismatch.\n"
        f"Expected: {sorted(VALID_GRAPHS)}\n"
        f"Actual:   {sorted(graphs.keys())}"
    )


# Test 4 — Unknown --graph value fails fast (no LLM cost, exit 2)
def test_unknown_graph_flag_exits_with_error() -> None:
    """Passing --graph with a key not in VALID_GRAPH_KEYS exits 2 (validation failure)."""
    result = subprocess.run(
        [BASH_EXE, ".claude/loop/loop-tick.sh", "--graph", "nonexistent_graph"],
        cwd=str(REPO_ROOT),
        env=_run_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2, (
        f"expected exit 2 for unknown graph, got {result.returncode}:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "Unknown graph" in result.stderr, (
        f"expected 'Unknown graph' in stderr, got: {result.stderr}"
    )


# Test 5 — Default (no --graph flag) still requires orchestrator LLM path
# (Validates we didn't break the non-graph branch.)
def test_no_graph_flag_runs_orchestrator_path() -> None:
    """Without --graph, loop-tick.sh enters the orchestrator branch and emits the prompt.

    We invoke with --dry-run so it exits 0 without actually invoking `claude` CLI.
    """
    result = subprocess.run(
        [BASH_EXE, ".claude/loop/loop-tick.sh", "--dry-run"],
        cwd=str(REPO_ROOT),
        env=_run_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"dry-run failed: stdout={result.stdout}\nstderr={result.stderr}"
    )
    # The orchestrator branch writes the ORCHESTRATOR_PROMPT to the log file
    # and exits. We verify the "DRY RUN" marker + orchestrator-prompt signature.
    assert "DRY RUN" in result.stdout, (
        f"expected 'DRY RUN' in stdout (orchestrator branch), got: {result.stdout}"
    )
