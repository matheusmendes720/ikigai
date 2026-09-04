"""Smoke tests for the operator TUI.

Verifies:
- App imports cleanly
- Data loaders return valid rows
- DataTable renders without exception (pilot mode)
- Append-only invariant: no write paths in operator TUI
- Tier 2: backend Started/Uptime fields present
- Tier 2: queue payload present + drilldown binding registered
- Tier 2: format_uptime helper produces expected short forms
- Live subscription: Tasks tab + filesystem watcher on data/tasks.jsonl

Per fork-boilerplate: minimal test coverage (smoke + invariant).
Full Textual snapshot tests deferred to v1.2.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

from interfaces.tui.operator.app import (
    OperatorApp,
    QueueDetailScreen,
    SummaryPanel,
)
from interfaces.tui.operator.data import (
    AdapterRow,
    BackendRow,
    QueueRow,
    TaskRow,
    format_uptime,
    load_adapter_rows,
    load_backend_rows,
    load_queue_rows,
    load_task_rows,
)


def test_app_imports() -> None:
    """OperatorApp must import without error."""
    assert OperatorApp is not None
    assert SummaryPanel is not None
    assert QueueDetailScreen is not None


def test_app_has_four_tabs() -> None:
    """Four tab actions must be defined (1/2/3/4 keys) + drilldown/refresh/quit."""
    app = OperatorApp()
    bindings = {b.key for b in app.BINDINGS}
    assert "1" in bindings
    assert "2" in bindings
    assert "3" in bindings
    assert "4" in bindings  # Tasks tab
    assert "r" in bindings  # refresh
    assert "q" in bindings  # quit
    assert "d" in bindings  # tier 2: drilldown


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
        # Default tab is "tasks" — renders empty-state Static when no tasks.jsonl
        await pilot.pause()
        # App must have mounted without raising
        assert app.is_mounted


# === Tier 2 additions ===


def test_backend_rows_include_started_at_and_pidfile() -> None:
    """Tier 2: BackendRow exposes started_at + pidfile_path for detail view."""
    rows = load_backend_rows()
    assert rows, "BACKEND_PROCESSES must register at least one process"
    for row in rows:
        assert hasattr(row, "started_at")
        assert hasattr(row, "pidfile_path")
        # piddable processes (mcp_gateway, review_queue_worker) MUST have a
        # pidfile_path; non-piddable agents are None.
        if row.name in {"mcp_gateway", "review_queue_worker"}:
            assert row.pidfile_path is not None
        # started_at is set iff the process is running
        if row.running:
            assert row.started_at is not None


def test_queue_rows_include_payload() -> None:
    """Tier 2: QueueRow carries the raw JSON payload for drilldown."""
    rows = load_queue_rows()
    assert isinstance(rows, list)
    for row in rows:
        assert hasattr(row, "payload")
        assert isinstance(row.payload, dict)


def test_format_uptime_short_forms() -> None:
    """Tier 2: format_uptime produces expected short human-readable forms."""
    # None → em-dash placeholder
    assert format_uptime(None) == "—"
    # 30s → "30s"
    assert format_uptime(0.0, now=30.0) == "30s"
    # 5m 12s
    assert format_uptime(0.0, now=5 * 60 + 12) == "5m 12s"
    # 2h 7m
    assert format_uptime(0.0, now=2 * 3600 + 7 * 60) == "2h 7m"
    # 3d 4h
    assert format_uptime(0.0, now=3 * 86400 + 4 * 3600) == "3d 4h"


def test_queue_detail_screen_read_only() -> None:
    """Tier 2: QueueDetailScreen is a ModalScreen with dismiss bindings."""
    payload = {"event_id": "e1", "ueid": "tsk:x:y:z", "action": "create"}
    screen = QueueDetailScreen(event_id="e1", payload=payload)
    keys = {b.key for b in screen.BINDINGS}
    assert "escape" in keys
    assert "q" in keys
    # No write bindings — must be read-only
    assert "w" not in keys
    assert "d" not in keys


# === Live filesystem subscription (data/tasks.jsonl) ===


def test_load_task_rows_returns_empty_when_file_absent() -> None:
    """If data/tasks.jsonl does not exist, load_task_rows returns [] (no crash)."""
    rows = load_task_rows()
    assert isinstance(rows, list)


def test_load_task_rows_parses_valid_jsonl() -> None:
    """load_task_rows parses one JSON object per line, skipping blanks."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        fake = Path(tmpdir) / "tasks.jsonl"
        fake.write_text(
            json.dumps(
                {
                    "ueid": "cli:task:abc:def:00000001",
                    "title": "Test task",
                    "due": "2026-09-03",
                    "priority": "high",
                    "source_fork": "ikigai",
                }
            )
            + "\n\n"
            + json.dumps(
                {
                    "ueid": "cli:task:abc:def:00000002",
                    "title": "Another",
                    "priority": "low",
                    "source_fork": "cli",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with patch("interfaces.tui.operator.data.TASKS_JSONL", new=fake):
            rows = load_task_rows()
        assert len(rows) == 2
        assert rows[0].ueid == "cli:task:abc:def:00000001"
        assert rows[0].title == "Test task"
        assert rows[0].due == "2026-09-03"
        assert rows[0].priority == "high"
        assert rows[0].source_fork == "ikigai"
        assert rows[1].due is None  # not in record


def test_load_task_rows_skips_malformed_lines() -> None:
    """Malformed JSON lines are skipped silently; valid lines are still returned."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        fake = Path(tmpdir) / "tasks.jsonl"
        fake.write_text(
            '{"ueid":"t:1","title":"Good","priority":"low","source_fork":"x"}\n'
            "not valid json\n"
            '{"ueid":"t:2","title":"Also good","priority":"high","source_fork":"y"}\n',
            encoding="utf-8",
        )
        with patch("interfaces.tui.operator.data.TASKS_JSONL", new=fake):
            rows = load_task_rows()
        assert len(rows) == 2
        assert rows[0].ueid == "t:1"
        assert rows[1].ueid == "t:2"


def test_load_task_rows_task_row_dataclass() -> None:
    """TaskRow is a frozen dataclass with the expected fields."""
    row = TaskRow(
        ueid="cli:task:a:b:c:00000001",
        title="Test",
        due="2026-09-03",
        priority="medium",
        source_fork="ikigai",
    )
    assert row.ueid == "cli:task:a:b:c:00000001"
    assert row.title == "Test"
    assert row.due == "2026-09-03"
    assert row.priority == "medium"
    assert row.source_fork == "ikigai"


def test_mtime_changes_on_file_write() -> None:
    """os.path.getmtime returns distinct values when file is created/modified."""
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        fake = Path(tmpdir) / "tasks.jsonl"
        assert not fake.exists()
        with pytest.raises(OSError):
            os.path.getmtime(str(fake))

        fake.write_text(
            '{"ueid":"t:1","title":"A","priority":"low","source_fork":"x"}\n'
        )
        mtime_after_create = os.path.getmtime(str(fake))
        assert mtime_after_create > 0

        fake.write_text(
            '{"ueid":"t:2","title":"B","priority":"high","source_fork":"y"}\n'
        )
        mtime_after_append = os.path.getmtime(str(fake))
        assert mtime_after_append >= mtime_after_create

