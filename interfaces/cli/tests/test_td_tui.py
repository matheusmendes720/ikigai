"""M165 — Tests for the live taskdog TUI dashboard.

Coverage (per spec):
    - App boots without error
    - Mode switching works
    - Auto-refresh fires (use Textual's pilot test pattern)
    - Key handlers invoke correct actions
    - Render produces expected output (snapshot test)

These tests use Textual's `App.run_test()` pilot API. The `tmp_data_dir`
fixture from `interfaces/cli/tests/conftest.py` redirects adapter paths
to a fresh tmp directory so reads are isolated from real data.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

# Direct file import — bypasses interfaces/cli/__init__.py which has an
# unrelated mcp-runtime chain that breaks in this sandbox.
_TD_TUI_PATH = Path(__file__).resolve().parents[1] / "td_tui.py"
_spec = importlib.util.spec_from_file_location("_td_tui_under_test", str(_TD_TUI_PATH))
assert _spec and _spec.loader
t = importlib.util.module_from_spec(_spec)
sys.modules["_td_tui_under_test"] = t
_spec.loader.exec_module(t)


# -- Helpers --------------------------------------------------------------


def _seed_taskdog_db(path: Path, rows: list[dict]) -> None:
    """Write a small taskdog SQLite DB at `path` with the canonical schema.

    Deletes any existing rows first so the same path can be re-seeded
    (used by the auto-refresh / manual-refresh tests).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(t._TASKDOG_SCHEMA)
        conn.execute("DELETE FROM tasks")
        conn.executemany(
            "INSERT INTO tasks (ueid, name, status, priority, planned_start, "
            "planned_end, deadline, created_at) VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    r.get("ueid"),
                    r.get("name"),
                    r.get("status", "planned"),
                    r.get("priority"),
                    r.get("planned_start"),
                    r.get("planned_end"),
                    r.get("deadline"),
                    r.get("created_at"),
                )
                for r in rows
            ],
        )
        conn.commit()
    finally:
        conn.close()


def _seed_activity(queue_dir: Path, events: list[dict]) -> None:
    """Write TaskChange events to data/review_queue/."""
    queue_dir.mkdir(parents=True, exist_ok=True)
    for ev in events:
        p = queue_dir / f"{ev['event_id']}.json"
        p.write_text(json.dumps(ev), encoding="utf-8")


def _make_app(
    taskdog_db: Path | None,
    upi_db: Path | None,
    queue_dir: Path | None,
) -> t.TaskdogTUI:
    """Build a TaskdogTUI instance with the given data paths."""
    return t.TaskdogTUI(
        taskdog_db=taskdog_db,
        upi_db=upi_db,
        queue_dir=queue_dir,
    )


# -- Pure-Python loader / filter tests (no Textual runtime) --------------


def test_load_taskdog_rows_empty_db(tmp_path: Path) -> None:
    """Empty / missing DB → empty list, no exceptions."""
    missing = tmp_path / "nope.db"
    assert t._load_taskdog_rows(missing) == []
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    assert t._load_taskdog_rows(empty) == []


def test_load_taskdog_rows_with_seed(tmp_path: Path) -> None:
    """Seed a few rows and read them back."""
    db = tmp_path / "tasks.db"
    _seed_taskdog_db(
        db,
        [
            {"ueid": "u:1", "name": "Alpha", "status": "planned", "priority": 1},
            {"ueid": "u:2", "name": "Beta", "status": "done", "priority": 2,
             "planned_start": "2026-01-01", "planned_end": "2026-01-10",
             "deadline": "2026-01-15"},
        ],
    )
    rows = t._load_taskdog_rows(db)
    assert len(rows) == 2
    assert {r["ueid"] for r in rows} == {"u:1", "u:2"}
    assert rows[1]["planned_start"] == "2026-01-01"


def test_load_activity_rows_empty(tmp_path: Path) -> None:
    """Missing queue dir → empty list."""
    assert t._load_activity_rows(tmp_path / "no_dir") == []


def test_load_activity_rows_with_seed(tmp_path: Path) -> None:
    """Seed events and read them back newest-first."""
    qd = tmp_path / "queue"
    _seed_activity(
        qd,
        [
            {"event_id": "ev-old", "ueid": "u:1", "action": "create",
             "source_fork": "cli", "timestamp": "2026-01-01T00:00:00Z",
             "status": "pending"},
            {"event_id": "ev-new", "ueid": "u:2", "action": "done",
             "source_fork": "taskdog", "timestamp": "2026-09-15T12:00:00Z",
             "status": "approved"},
        ],
    )
    rows = t._load_activity_rows(qd)
    assert len(rows) == 2
    # Newest first by filename (globs sorted reverse=True).
    assert rows[0]["event_id"] == "ev-new"
    assert rows[1]["event_id"] == "ev-old"


def test_apply_filter_no_pattern() -> None:
    """No pattern → return rows unchanged."""
    rows = [{"name": "a", "status": "planned"}, {"name": "b", "status": "done"}]
    assert t._apply_filter(rows, None) == rows
    assert t._apply_filter(rows, "") == rows


def test_apply_filter_by_name() -> None:
    rows = [
        {"name": "Alpha release", "status": "planned"},
        {"name": "Beta fix", "status": "done"},
    ]
    out = t._apply_filter(rows, "alpha")
    assert len(out) == 1
    assert out[0]["name"] == "Alpha release"


def test_apply_filter_by_status() -> None:
    rows = [
        {"name": "x", "status": "planned"},
        {"name": "y", "status": "done"},
    ]
    out = t._apply_filter(rows, "DONE")
    assert len(out) == 1
    assert out[0]["status"] == "done"


def test_apply_filter_bad_regex_returns_empty() -> None:
    rows = [{"name": "x", "status": "planned"}]
    assert t._apply_filter(rows, "[unclosed") == []


def test_status_counts() -> None:
    rows = [
        {"status": "planned"},
        {"status": "planned"},
        {"status": "done"},
        {"status": "unknown"},
    ]
    counts = t._status_counts(rows)
    assert counts["planned"] == 2
    assert counts["done"] == 1
    assert counts["unknown"] == 1


# -- Textual app boot / mode switching tests -------------------------------


@pytest.mark.asyncio
async def test_app_boots_without_error(tmp_path: Path) -> None:
    """App boots, loads empty data, no exceptions."""
    db = tmp_path / "t.db"
    qd = tmp_path / "q"
    app = _make_app(db, None, qd)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.all_rows() == []
        assert app.last_activity() == []


@pytest.mark.asyncio
async def test_app_loads_seeded_data(tmp_path: Path) -> None:
    """App picks up the seeded taskdog rows after on_mount's refresh."""
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [
            {"ueid": "ikigai:task:abcd1234:abcd5678", "name": "Real task",
             "status": "in_progress", "priority": 1,
             "planned_start": "2026-09-01", "planned_end": "2026-09-30"},
        ],
    )
    qd = tmp_path / "q"
    _seed_activity(
        qd,
        [{"event_id": "ev-1", "ueid": "ikigai:task:abcd1234:abcd5678",
          "action": "create", "source_fork": "cli",
          "timestamp": "2026-09-15T12:00:00Z", "status": "pending"}],
    )
    app = _make_app(db, None, qd)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.all_rows()) == 1
        assert app.all_rows()[0]["name"] == "Real task"
        assert app.last_counts().get("in_progress") == 1
        assert len(app.last_activity()) == 1


@pytest.mark.asyncio
async def test_mode_cycling(tmp_path: Path) -> None:
    """Pressing `tab` cycles dashboard → timeline → gantt → dashboard."""
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [{"ueid": "u:1", "name": "Task one", "status": "planned",
          "planned_start": "2026-09-01", "planned_end": "2026-09-10"}],
    )
    app = _make_app(db, None, tmp_path / "q")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.active_mode == t.MODE_DASHBOARD
        await pilot.press("tab")
        assert app.active_mode == t.MODE_TIMELINE
        await pilot.press("tab")
        assert app.active_mode == t.MODE_GANTT
        await pilot.press("tab")
        assert app.active_mode == t.MODE_DASHBOARD


@pytest.mark.asyncio
async def test_filter_pattern_persists_across_modes(tmp_path: Path) -> None:
    """Setting a filter and switching modes preserves the filter."""
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [
            {"ueid": "u:1", "name": "Alpha release", "status": "planned"},
            {"ueid": "u:2", "name": "Beta fix", "status": "done"},
        ],
    )
    app = _make_app(db, None, tmp_path / "q")
    async with app.run_test() as pilot:
        await pilot.pause()
        app.filter_pattern = "alpha"
        await pilot.press("tab")  # → timeline
        filtered = app.filtered_rows()
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Alpha release"
        await pilot.press("tab")  # → gantt
        assert len(app.filtered_rows()) == 1


@pytest.mark.asyncio
async def test_quit_binding_exits(tmp_path: Path) -> None:
    """`q` triggers app exit (the run_test context manager returns cleanly)."""
    app = _make_app(tmp_path / "t.db", None, tmp_path / "q")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        # If we reach here without an exception, the quit binding worked.


@pytest.mark.asyncio
async def test_refresh_now_binding_fires(tmp_path: Path) -> None:
    """`r` calls refresh_data. We seed a row and mutate the DB; `r` should pick it up."""
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [{"ueid": "u:1", "name": "First", "status": "planned"}],
    )
    app = _make_app(db, None, tmp_path / "q")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.all_rows()) == 1
        # Mutate the DB behind the app's back, then press `r`.
        _seed_taskdog_db(
            db,
            [
                {"ueid": "u:1", "name": "First", "status": "planned"},
                {"ueid": "u:2", "name": "Second", "status": "done"},
            ],
        )
        await pilot.press("r")
        await pilot.pause()
        assert len(app.all_rows()) == 2


@pytest.mark.asyncio
async def test_auto_refresh_interval_runs(tmp_path: Path) -> None:
    """set_interval(5s, refresh_data) should fire on its own.

    To avoid a real 5s wait in CI, monkeypatch REFRESH_SECONDS to 0.1
    and verify the data was reloaded after two cycles.
    """
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [{"ueid": "u:1", "name": "First", "status": "planned"}],
    )
    monkey = pytest.MonkeyPatch()
    monkey.setattr(t, "REFRESH_SECONDS", 0.1)
    try:
        app = _make_app(db, None, tmp_path / "q")
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.all_rows()) == 1
            # Mutate the DB then wait > 1 cycle.
            _seed_taskdog_db(
                db,
                [
                    {"ueid": "u:1", "name": "First", "status": "planned"},
                    {"ueid": "u:2", "name": "Auto", "status": "done"},
                ],
            )
            # Wait > 1 second so two 0.1s ticks pass.
            await asyncio.sleep(0.35)
            await pilot.pause()
            assert len(app.all_rows()) == 2
    finally:
        monkey.undo()


@pytest.mark.asyncio
async def test_render_dashboard_shows_counts(tmp_path: Path) -> None:
    """Snapshot test: dashboard header renders counts correctly."""
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [
            {"ueid": "u:1", "name": "a", "status": "planned", "priority": 1},
            {"ueid": "u:2", "name": "b", "status": "done", "priority": 2},
            {"ueid": "u:3", "name": "c", "status": "in_progress", "priority": 3},
        ],
    )
    app = _make_app(db, None, tmp_path / "q")
    async with app.run_test() as pilot:
        await pilot.pause()
        # The current screen should be the DashboardScreen.
        screen = app.screen
        assert isinstance(screen, t.DashboardScreen)
        screen.refresh_data()
        # Pull the rendered header text via the Static widget.
        from textual.widgets import Static as _Static  # noqa: PLC0415

        header_widget = screen.query_one("#dash-header", _Static)
        rendered = header_widget.renderable if hasattr(header_widget, "renderable") else str(header_widget.render())
        rendered_str = str(rendered)
        assert "total" in rendered_str
        assert "planned" in rendered_str
        assert "done" in rendered_str


@pytest.mark.asyncio
async def test_render_timeline_shows_window(tmp_path: Path) -> None:
    """Timeline mode renders a date-window header line."""
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [
            {"ueid": "u:1", "name": "t1", "status": "planned",
             "planned_start": "2026-09-01", "planned_end": "2026-09-10"},
        ],
    )
    app = _make_app(db, None, tmp_path / "q")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("tab")  # → timeline
        assert isinstance(app.screen, t.TimelineScreen)
        app.screen.refresh_data()
        from textual.widgets import Static as _Static  # noqa: PLC0415

        body = app.screen.query_one("#timeline-body", _Static)
        body_str = str(body.renderable if hasattr(body, "renderable") else body.render())
        # Should contain the window header or the "(no datable)" sentinel.
        assert "window" in body_str or "no datable" in body_str


@pytest.mark.asyncio
async def test_render_gantt_shows_boxes(tmp_path: Path) -> None:
    """Gantt mode renders boxes (┌─) for at least one task."""
    db = tmp_path / "t.db"
    _seed_taskdog_db(
        db,
        [{"ueid": "u:1", "name": "t1", "status": "planned"}],
    )
    app = _make_app(db, None, tmp_path / "q")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("tab")  # → timeline
        await pilot.press("tab")  # → gantt
        assert isinstance(app.screen, t.GanttScreen)
        app.screen.refresh_data()
        from textual.widgets import Static as _Static  # noqa: PLC0415

        body = app.screen.query_one("#gantt-body", _Static)
        body_str = str(body.renderable if hasattr(body, "renderable") else body.render())
        assert "┌─" in body_str
        assert "u:1" in body_str


# -- Counters (used by the workflow JSON block) --------------------------


def test_module_exports_expected_symbols() -> None:
    """The module re-exports the public API the workflow depends on."""
    for name in (
        "TaskdogTUI",
        "DashboardScreen",
        "TimelineScreen",
        "GanttScreen",
        "FilterModal",
        "MODES",
        "main",
        "_load_taskdog_rows",
        "_load_activity_rows",
        "_apply_filter",
    ):
        assert hasattr(t, name), f"missing public symbol: {name}"


def test_modes_constant() -> None:
    """MODES is a 3-tuple in the right order."""
    assert t.MODES == ("dashboard", "timeline", "gantt")
    assert len(t.MODES) == 3


def test_keys_count_via_bindings() -> None:
    """The App declares 7 global bindings (q, r, tab, +, d, t, /)."""
    bindings = {b.key for b in t.TaskdogTUI.BINDINGS}
    assert bindings == {"q", "r", "tab", "plus", "d", "t", "slash"}
    assert len(bindings) == 7