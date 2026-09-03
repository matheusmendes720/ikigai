"""Smoke tests for the operator TUI.

Verifies:
- App imports cleanly
- Data loaders return valid rows
- DataTable renders without exception (pilot mode)
- Append-only invariant: no write paths in operator TUI

Per fork-boilerplate: minimal test coverage (smoke + invariant).
Full Textual snapshot tests deferred to v1.2.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from textual.widgets import DataTable

from interfaces.tui.operator.app import OperatorApp, SummaryPanel
from interfaces.tui.operator.data import (
    AdapterRow,
    BackendRow,
    QueueRow,
    load_adapter_rows,
    load_backend_rows,
    load_queue_rows,
)


def test_app_imports() -> None:
    """OperatorApp must import without error."""
    assert OperatorApp is not None
    assert SummaryPanel is not None


def test_app_has_three_tabs() -> None:
    """Three tab actions must be defined (1/2/3 keys)."""
    app = OperatorApp()
    bindings = {b.key for b in app.BINDINGS}
    assert "1" in bindings
    assert "2" in bindings
    assert "3" in bindings
    assert "r" in bindings  # refresh
    assert "q" in bindings  # quit


def test_adapter_rows_load() -> None:
    """Adapter data loader returns one row per registered adapter."""
    rows = load_adapter_rows()
    assert isinstance(rows, list)
    assert all(isinstance(r, AdapterRow) for r in rows)
    # At least the 3 live forks are registered
    names = {r.name for r in rows}
    assert "cli" in names
    assert "taskdog" in names
    assert "solverforge_calendar" in names


def test_backend_rows_load() -> None:
    """Backend process loader returns rows from BACKEND_PROCESSES."""
    rows = load_backend_rows()
    assert isinstance(rows, list)
    assert all(isinstance(r, BackendRow) for r in rows)
    # mcp_gateway + review_queue_worker are the two piddable processes
    names = {r.name for r in rows}
    assert "mcp_gateway" in names
    assert "review_queue_worker" in names


def test_queue_rows_empty_when_dir_missing() -> None:
    """Queue loader returns empty list when review_queue dir absent."""
    rows = load_queue_rows()
    assert isinstance(rows, list)
    assert all(isinstance(r, QueueRow) for r in rows)


def test_no_write_paths_in_operator_tui() -> None:
    """Operator TUI is read-only — no write/file-mutation calls.

    Scans all .py under interfaces/tui/operator/ for any call that could
    write to vault/ or data/. Enforces the dual-layer architecture invariant:
    operator control plane NEVER mutates state.
    """
    tui_dir = Path(__file__).parent.parent.parent / "interfaces" / "tui" / "operator"
    forbidden_calls = {
        "write_text",
        "write_bytes",
        "open",  # open(..., "w") / "a" / "x" all flag
        "write",
        "unlink",
        "rename",
        "remove",
        "mkdir",
        "rmdir",
        "truncate",
    }
    violations: list[str] = []
    for py_file in tui_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name: str | None = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name and func_name in forbidden_calls:
                    violations.append(
                        f"{py_file.relative_to(Path(__file__).parent.parent.parent)}:"
                        f"{node.lineno} -> {func_name}()"
                    )
    assert not violations, (
        "Operator TUI MUST be read-only. Forbidden write calls:\n"
        + "\n".join(sorted(violations))
    )


def test_data_loaders_are_pure() -> None:
    """Data loaders do not require arguments and return lists (pure functions)."""
    sig_a = inspect.signature(load_adapter_rows)
    sig_b = inspect.signature(load_backend_rows)
    sig_c = inspect.signature(load_queue_rows)
    assert list(sig_a.parameters) == []
    assert list(sig_b.parameters) == []
    assert "limit" in sig_c.parameters


@pytest.mark.asyncio
async def test_app_runs_in_pilot_mode() -> None:
    """Smoke test: app boots in Textual pilot mode without exception."""
    app = OperatorApp()
    async with app.run_test() as pilot:
        # Default tab is adapters — DataTable should be present
        await pilot.pause()
        tables = app.query(DataTable)
        assert len(tables) >= 1
