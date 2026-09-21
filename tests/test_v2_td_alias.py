"""M101b tests: `life v2 td` short aliases for `life taskdog *`.

Per M101b: `life v2 td <cmd>` is a thin alias for `life taskdog <cmd>`,
exposing the 26 MCP tools under shorter names (e.g. `list` vs
`list-tasks`, `create` vs `create-task`).

Tests verify:
- sub-app registers without import error
- `--help` lists aliases
- An alias invocation routes through to the full taskdog command
- IKIGAI_DISABLE_MCP_TASKDOG escape hatch shows clean error
"""
from __future__ import annotations

import json
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


def _run_cli(ikigai_python: str, *args: str, timeout: int = 60, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [ikigai_python, "-m", "life.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_v2_td_subapp_registered(ikigai_python: str) -> None:
    """`life v2 --help` must list the `td` subcommand."""
    r = _run_cli(ikigai_python, "v2", "--help")
    assert r.returncode == 0
    assert "td" in r.stdout
    assert "Short aliases for" in r.stdout


def test_v2_td_lists_short_aliases(ikigai_python: str) -> None:
    """`life v2 td --help` must list aliases with shorter names."""
    r = _run_cli(ikigai_python, "v2", "td", "--help")
    assert r.returncode == 0
    expected_short = ["list", "create", "delete", "cancel", "decompose", "add", "remove"]
    found = sum(1 for s in expected_short if s in r.stdout)
    assert found >= 5, f"expected ≥5 short aliases, found {found}: {r.stdout[:300]}"


def test_v2_td_list_alias_works(ikigai_python: str) -> None:
    """`life v2 td list --status PENDING` must return taskdog JSON."""
    r = _run_cli(ikigai_python, "v2", "td", "list", "--status", "PENDING", timeout=30)
    assert r.returncode == 0, f"stderr: {r.stderr}"
    data = json.loads(r.stdout)
    assert "tasks" in data
    assert isinstance(data["tasks"], list)


def test_v2_td_create_alias_roundtrip(ikigai_python: str) -> None:
    """`life v2 td create --name X --priority 5 --tags a,b` works + cleanup."""
    # CREATE via short alias
    r = _run_cli(
        ikigai_python,
        "v2", "td", "create",
        "--name", "M101b test (pytest)",
        "--priority", "5",
        "--tags", "smoke,m101",
        timeout=30,
    )
    assert r.returncode == 0, f"create stderr: {r.stderr}"
    created = json.loads(r.stdout)
    task_id = created["id"]
    try:
        # Verify tags parsed correctly (array)
        r2 = _run_cli(ikigai_python, "v2", "td", "get", "--task-id", str(task_id), timeout=30)
        assert r2.returncode == 0
        fetched = json.loads(r2.stdout)
        tags = fetched.get("tags", [])
        assert "smoke" in tags and "m101" in tags, f"tags not parsed as list: {tags}"
    finally:
        # CLEANUP via short alias
        _run_cli(
            ikigai_python, "v2", "td", "delete",
            "--task-id", str(task_id),
            "--hard", "true",
            timeout=30,
        )


def test_v2_td_disable_mcp_escape_hatch(ikigai_python: str) -> None:
    """IKIGAI_DISABLE_MCP_TASKDOG=1 → placeholder shows clean error."""
    r = _run_cli(
        ikigai_python, "v2", "td", "--help",
        env_extra={"IKIGAI_DISABLE_MCP_TASKDOG": "1"},
        timeout=15,
    )
    # Sub-app still registered but with placeholder message
    # When invoked (not --help), should error with the disable message
    r2 = _run_cli(
        ikigai_python, "v2", "td", "list",
        env_extra={"IKIGAI_DISABLE_MCP_TASKDOG": "1"},
        timeout=15,
    )
    # Either the placeholder text or a graceful error
    assert r.returncode == 0  # --help exits 0
    assert "langchain-mcp-adapters" in r2.stdout + r2.stderr or "MCP" in r2.stdout + r2.stderr
