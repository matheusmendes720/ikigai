"""Smoke test for td chat REPL.

Verifies that td chat:
- starts the REPL
- accepts input
- streams events from the v2 graph
- shows a proposal block
- awaits approval
- exits cleanly on /quit
"""
import subprocess
import sys
import textwrap

# Use the project's Python so PYTHONPATH and venv are correct
PYTHON = r"C:\Python314\python.exe"


def _run_chat_scripted(inputs: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run `td chat` with a scripted input stream and capture output."""
    repo_root = r"C:\Users\mathe\code_space\life-oss\life"
    bootstrap = (
        "import sys; "
        f"sys.path.insert(0, r'{repo_root}'); "
        f"sys.path.insert(0, r'{repo_root}\\src'); "
        f"sys.path.insert(0, r'{repo_root}\\src\\ikigai\\src'); "
        "from src.mesh.taskdog_chat import main; "
        "sys.exit(main(['--no-color']))"
    )
    payload = "\n".join(inputs) + "\n"
    return subprocess.run(
        [PYTHON, "-c", bootstrap],
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_chat_repl_starts_and_exits():
    """REPL accepts /quit and exits cleanly."""
    proc = _run_chat_scripted(["/quit"])
    assert proc.returncode == 0, f"exit code {proc.returncode}: {proc.stderr}"
    assert "ikigai-chat" in proc.stdout
    assert "thread closed" in proc.stdout


def test_chat_repl_shows_help():
    """REPL shows /help text."""
    proc = _run_chat_scripted(["/help", "/quit"])
    assert proc.returncode == 0
    assert "Commands:" in proc.stdout
    assert "/skill" in proc.stdout


def test_chat_repl_invokes_graph_and_streams():
    """REPL sends request to v2 graph, streams events, awaits approval."""
    proc = _run_chat_scripted(
        [
            "olá, resuma minha semana",  # user request
            "--approve",  # approve
            "/quit",
        ],
        timeout=120,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    # v2 graph should emit at least one node event
    assert "[recall]" in proc.stdout or "[observe]" in proc.stdout
    # Should show approval prompt
    assert "PROPOSAL" in proc.stdout or "COMMIT" in proc.stdout
    # Should end cleanly
    assert "thread closed" in proc.stdout


def test_chat_repl_handles_empty_request():
    """Empty input is ignored, no crash."""
    proc = _run_chat_scripted(["", "  ", "/quit"])
    assert proc.returncode == 0
    assert "ikigai-chat" in proc.stdout


def test_chat_repl_handles_slash_skill():
    """Slash-skill prefix is parsed and shown in stream."""
    proc = _run_chat_scripted(
        [
            "/skill daily bom dia",
            "--approve",
            "/quit",
        ],
        timeout=120,
    )
    assert proc.returncode == 0
    assert "[recall]" in proc.stdout or "[observe]" in proc.stdout


def test_chat_repl_handles_unknowm_approval():
    """Unrecognized approval command does not crash, treated as new request."""
    proc = _run_chat_scripted(
        [
            "olá",
            "garbage input",
            "/quit",
        ],
        timeout=120,
    )
    assert proc.returncode == 0
    assert "ikigai-chat" in proc.stdout
