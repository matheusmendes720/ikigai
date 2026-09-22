"""M106 tests: REPL history + built-in commands.

Per M106: `life v2 chat` REPL now has:
- History persistence (.life/chat_history, max 500 lines, pyreadline3 on Windows)
- Tab completion for built-in commands
- 6 built-in commands that don't go through the agent (/help, /exit, /quit, /thread, /reset, /history, /clear)

Tests run `run_chat()` directly via subprocess with PYTHONPATH=src/ikigai/src
(no `life.cli` import chain — that chain hits the Windows _overlapped bug).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IKIGAI_PY = REPO_ROOT / "src" / "ikigai" / ".venv" / "Scripts" / "python.exe"


def _ikigai_python() -> str:
    if IKIGAI_PY.exists():
        return str(IKIGAI_PY)
    return sys.executable


@pytest.fixture(scope="module")
def ikigai_python() -> str:
    return _ikigai_python()


def _run_repl_direct(ikigai_python: str, stdin_text: str, thread_id: str = "test-thread") -> subprocess.CompletedProcess:
    """Invoke run_chat() directly via subprocess with PYTHONPATH=src/ikigai/src.

    Avoids the `life.cli` import chain (which crashes on Windows _overlapped
    when asyncio is loaded by langchain_mcp_adapters).
    """
    code = f"""
import sys
sys.path.insert(0, r'src/ikigai/src')
sys.path.insert(0, r'src')
import os
os.environ['IKIGAI_DISABLE_MCP_TASKDOG'] = '1'

class FakeAgent:
    pass

from agents.deepagents_harness import run_chat
run_chat(FakeAgent(), '{thread_id}')
"""
    env = {k: v for k, v in os.environ.items() if k.startswith("IKIGAI_")}
    env["PYTHONPATH"] = str(REPO_ROOT / "src" / "ikigai" / "src") + os.pathsep + str(REPO_ROOT / "src")
    return subprocess.run(
        [ikigai_python, "-c", code],
        cwd=str(REPO_ROOT),
        input=stdin_text,
        capture_output=True, text=True, timeout=30,
        env=env,
    )


def test_banner_shows_history_hint(ikigai_python: str) -> None:
    """Banner mentions ↑/↓ for history and Tab for completion."""
    r = _run_repl_direct(ikigai_python, "/exit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    assert "↑/↓ for history" in r.stdout
    assert "Tab for completion" in r.stdout


def test_help_command(ikigai_python: str) -> None:
    """/help lists all built-in commands."""
    r = _run_repl_direct(ikigai_python, "/help\n/exit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    assert "Built-in commands:" in r.stdout
    for cmd in ("/help", "/exit", "/quit", "/thread", "/reset", "/history", "/clear"):
        assert cmd in r.stdout, f"{cmd} not listed in /help"


def test_exit_command(ikigai_python: str) -> None:
    """/exit exits cleanly with Goodbye message."""
    r = _run_repl_direct(ikigai_python, "/exit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    assert "Goodbye" in r.stdout


def test_quit_command(ikigai_python: str) -> None:
    """/quit exits cleanly (alias for /exit)."""
    r = _run_repl_direct(ikigai_python, "/quit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    assert "Goodbye" in r.stdout


def test_thread_command(ikigai_python: str) -> None:
    """/thread prints the current thread_id."""
    r = _run_repl_direct(ikigai_python, "/thread\n/exit\n", thread_id="my-custom-thread-42")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    assert "my-custom-thread-42" in r.stdout


def test_reset_command(ikigai_python: str) -> None:
    """/reset clears conversation and prints confirmation."""
    r = _run_repl_direct(ikigai_python, "/reset\n/exit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    assert "(conversation cleared)" in r.stdout


def test_clear_command(ikigai_python: str) -> None:
    """/clear runs without error (calls cls or clear)."""
    r = _run_repl_direct(ikigai_python, "/clear\n/exit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"


def test_history_command(ikigai_python: str) -> None:
    """/history runs without error."""
    r = _run_repl_direct(ikigai_python, "/history\n/exit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"


def test_history_file_created(ikigai_python: str) -> None:
    """REPL creates .life/chat_history file (or attempts to)."""
    history_file = REPO_ROOT / ".life" / "chat_history"
    # Just run the REPL; file creation is best-effort.
    r = _run_repl_direct(ikigai_python, "hello world\nexit\n")
    assert r.returncode == 0, f"failed: stderr={r.stderr!r}"
    # File may or may not exist depending on readline availability — just check no crash.
