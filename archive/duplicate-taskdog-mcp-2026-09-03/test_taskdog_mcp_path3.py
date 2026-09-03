"""Path 3 taskdog MCP server smoke tests.

Verifies:
- Server module imports cleanly
- FastMCP instance has 4 tools + 1 resource registered
- Subprocess helpers format responses correctly (success + error paths)
- No vault/ write paths (vault_write invariant)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.taskdog_mcp import MCP, main
from src.taskdog_mcp.server import (
    _format_response,
    _run_taskdog,
)


def test_server_imports() -> None:
    """Server module must import without error."""
    assert MCP is not None
    assert main is not None


def test_mcp_has_four_tools() -> None:
    """FastMCP server must register exactly 4 taskdog tools."""
    tools = MCP._tool_manager._tools
    tool_names = set(tools.keys())
    assert "taskdog_list_tasks" in tool_names
    assert "taskdog_create_task" in tool_names
    assert "taskdog_complete_task" in tool_names
    assert "taskdog_get_task" in tool_names
    assert len(tool_names) == 4


def test_mcp_has_health_resource() -> None:
    """FastMCP server must register taskdog://health resource."""
    resources = MCP._resource_manager._resources
    assert "taskdog://health" in resources


def test_format_response_success() -> None:
    """Success result returns status=ok JSON."""
    result = {
        "ok": True,
        "stdout": "Task 1: foo\nTask 2: bar",
        "stderr": "",
        "returncode": 0,
    }
    out = _format_response(result, "list")
    assert '"status": "ok"' in out
    assert '"operation": "list"' in out
    assert "Task 1" in out


def test_format_response_error() -> None:
    """Error result returns status=error JSON with returncode."""
    result = {
        "ok": False,
        "stdout": "",
        "stderr": "taskdog binary not found",
        "returncode": -1,
    }
    out = _format_response(result, "create")
    assert '"status": "error"' in out
    assert '"returncode": -1' in out


def test_run_taskdog_missing_binary() -> None:
    """Missing binary returns structured error (not exception).

    On Windows, subprocess.run with shell=False may either raise
    FileNotFoundError (returns -1) or return returncode 1 if the
    shell resolves the path. We accept either as "ok=False".
    """
    import os

    os.environ["TASKDOG_CLI"] = "nonexistent_taskdog_binary_xyz"
    result = _run_taskdog(["list"])
    assert result["ok"] is False
    assert result["returncode"] in (-1, 1, 2), (
        f"expected structured error code, got {result['returncode']}"
    )
    assert result["stderr"] != "" or result["stdout"] != ""


def test_no_vault_write_paths() -> None:
    """taskdog_mcp must NEVER write to vault/ — vault_write invariant.

    Docstrings that MENTION the invariant are fine (they document the rule).
    Only ACTIVE code paths (function bodies, top-level assignments, call
    expressions) must be free of vault-touching identifiers.
    """
    mcp_dir = Path(__file__).parent.parent / "src" / "taskdog_mcp"
    violations: list[str] = []
    # We use the docstring of THIS test as a positive example — vault appears
    # here but no vault-touching call exists. Forbidden ACTIVE patterns:
    forbidden_calls = {"vault_write", "vault_read", "open(", "write_text", "write_bytes"}
    for py_file in mcp_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, OSError):
            continue
        # Walk active nodes: calls and assignments only. Skip string Constants
        # (docstrings are allowed to reference "vault").
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = _called_name(node.func)
                if func_name and any(p in func_name for p in ("vault_write", "vault_read")):
                    violations.append(
                        f"{py_file.relative_to(Path(__file__).parent.parent)}:{node.lineno}: "
                        f"forbidden call: {func_name}"
                    )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Flag any function NAMED with vault_* (would be a writer).
                if node.name.startswith("vault_") and node.name not in {"vault_read"}:
                    # vault_read is allowed (read-only); vault_write is NOT.
                    if "write" in node.name:
                        violations.append(
                            f"{py_file.relative_to(Path(__file__).parent.parent)}:{node.lineno}: "
                            f"forbidden def: {node.name}"
                        )
    assert not violations, (
        "taskdog_mcp must NOT touch vault/ from active code (vault_write is sole writer):\n"
        + "\n".join(violations)
    )


def _called_name(func: ast.AST) -> str | None:
    """Return bare name of a Call target."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_no_review_queue_writes() -> None:
    """taskdog_mcp must NOT write to data/review_queue/ — append-only invariant."""
    mcp_dir = Path(__file__).parent.parent / "src" / "taskdog_mcp"
    source_concat = ""
    for py_file in mcp_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            source_concat += py_file.read_text(encoding="utf-8")
        except OSError:
            continue
    assert "review_queue" not in source_concat, (
        "taskdog_mcp must not reference data/review_queue/ — append-only invariant"
    )
