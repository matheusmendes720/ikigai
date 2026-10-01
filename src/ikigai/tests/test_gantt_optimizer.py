"""M167 tests: gantt_engine + optimizer + td gantt/optimize CLI wiring.

Six focused tests:
  1. gantt ascii — 5 tasks + 3 deps, snapshot-check the box-drawing output.
  2. gantt html — output parses as valid HTML5 (html.parser).
  3. gantt json — structured data, includes all 5 ueids + days axis.
  4. optimize produces valid topological order (priority_weighted).
  5. optimize respects all hard deps (every dep is upstream of its dependent).
  6. optimize priority weighting is correct (weight = score x (1 + blockers)).

Plus an extra smoke test (7) that runs the full CLI wiring through
the taskdog_cli main() entrypoint to ensure argparse dispatch works.

Fixtures are pure dicts (no DB) so tests run hermetically. The CLI
test uses the same taskdog_db fixture pattern as tests/mesh/test_taskdog_cli.py.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.gantt_engine import GanttConfig, GanttEngine
from src.mesh.optimizer import OptimizeConfig, Optimizer, OptimizeStrategy
from src.mesh.taskdog_cli import main as td_main

# ─────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ─────────────────────────────────────────────────────────────────────


def _mk_task(
    ueid: str,
    name: str,
    *,
    status: str = "planned",
    priority: int | None = 2,
    planned_start: str | None = None,
    planned_end: str | None = None,
    deadline: str | None = None,
    deps: list[str] | None = None,
) -> dict[str, Any]:
    """Build a taskdog-shaped slice dict for tests (no DB needed)."""
    return {
        "ueid": ueid,
        "name": name,
        "status": status,
        "priority": priority,
        "planned_start": planned_start,
        "planned_end": planned_end,
        "deadline": deadline,
        "created_at": "2026-09-01T00:00:00+00:00",
        "tags": [],
        "deps": deps or [],
        "audit_log": [],
        "started_at": None,
        "completed_at": None,
        "priority_label": "P2",
    }


@pytest.fixture
def five_task_fixture() -> list[dict[str, Any]]:
    """5 tasks, 3 dep edges. Used by all gantt tests.

    Graph (arrows point to "depends on"):

        foundation ──► framing ──► roofing
                            └────► siding ──► painting

    Tasks:
        t1 = foundation  (priority=1 high, planned 2030-09-01..02)
        t2 = framing     (priority=2 med,  planned 2030-09-03..05)
        t3 = roofing     (priority=2 med,  planned 2030-09-06..07)
        t4 = siding      (priority=3 low,  planned 2030-09-06..09)
        t5 = painting    (priority=1 high, planned 2030-09-10..12)

    Dates are in 2030 to keep the chart "not overdue" regardless of
    when tests run (today=2026-10-01 per the system reminder).
    """
    return [
        _mk_task(
            "tsk:foundation:11111111-1111-1111-1111-111111111111:1111111111111111",
            "Foundation",
            priority=1,
            planned_start="2030-09-01",
            planned_end="2030-09-02",
            deadline="2030-09-05",
        ),
        _mk_task(
            "tsk:framing:22222222-2222-2222-2222-222222222222:2222222222222222",
            "Framing",
            priority=2,
            planned_start="2030-09-03",
            planned_end="2030-09-05",
            deadline="2030-09-08",
            deps=[
                "tsk:foundation:11111111-1111-1111-1111-111111111111:1111111111111111",
            ],
        ),
        _mk_task(
            "tsk:roofing:33333333-3333-3333-3333-333333333333:3333333333333333",
            "Roofing",
            priority=2,
            planned_start="2030-09-06",
            planned_end="2030-09-07",
            deadline="2030-09-12",
            deps=[
                "tsk:framing:22222222-2222-2222-2222-222222222222:2222222222222222",
            ],
        ),
        _mk_task(
            "tsk:siding:44444444-4444-4444-4444-444444444444:4444444444444444",
            "Siding",
            priority=3,
            planned_start="2030-09-06",
            planned_end="2030-09-09",
            deadline="2030-09-15",
            deps=[
                "tsk:framing:22222222-2222-2222-2222-222222222222:2222222222222222",
            ],
        ),
        _mk_task(
            "tsk:painting:55555555-5555-5555-5555-555555555555:5555555555555555",
            "Painting",
            priority=1,
            planned_start="2030-09-10",
            planned_end="2030-09-12",
            deadline="2030-09-20",
            deps=[
                "tsk:roofing:33333333-3333-3333-3333-333333333333:3333333333333333",
                "tsk:siding:44444444-4444-4444-4444-444444444444:4444444444444444",
            ],
        ),
    ]


# ─────────────────────────────────────────────────────────────────────
# gantt tests
# ─────────────────────────────────────────────────────────────────────


class TestGanttAscii:
    """ASCII renderer: box-drawing snapshot."""

    def test_five_tasks_three_deps_snapshot(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        cfg = GanttConfig(mode="ascii", day_width=3, title="Build Gantt")
        out = GanttEngine(five_task_fixture).render(cfg)

        # ── Structural sanity ──────────────────────────────────────
        assert "Build Gantt" in out, "title missing"
        assert out.startswith("Build Gantt"), "title must be on first line"

        # 5 task rows present (one per ueid short-prefix).
        assert out.count("Foundation") == 1
        assert out.count("Framing") == 1
        assert out.count("Roofing") == 1
        assert out.count("Siding") == 1
        assert out.count("Painting") == 1

        # ── Box-drawing characters used ────────────────────────────
        for ch in "─│┌┐└┘├┤┬┴┼":
            assert ch in out, f"missing box char: {ch!r}"

        # ── Status glyphs: all tasks are 'planned' so we expect ░ ─
        # Count of ░ (data cells) should equal total day-cells covered
        # by tasks: 2 + 3 + 2 + 4 + 3 = 14. The legend line also contains
        # ░, so subtract 1 to get the data-cell count.
        data_cell_count = out.count("░") - 1
        assert data_cell_count == 14, f"expected 14 ░ data cells, got {data_cell_count}"

        # ── Dep arrows: t1 is depended-on by t2 (↓), t2 by t3+t4 (↓),
        # t3+t4 by t5 (↓). All four rows that have downstream tasks
        # should show → in the deps column.
        # Rows with downstream: t1, t2, t3, t4 (each has at least one ↓ or →).
        # Specifically: t1 has 1 downstream → should contain "→t"
        assert "→t" in out, "expected downstream dep arrow somewhere"

        # ── Day axis: D1..D12 (12 days from 2030-09-01 to 2030-09-12).
        for i in range(1, 13):
            assert f"D{i}" in out, f"missing day label D{i}"

        # ── ISO date row: 2030-09-01 should appear under the chart.
        assert "2030-09-01" in out
        assert "2030-09-12" in out

        # ── Legend printed.
        assert "legend:" in out
        assert "planned" in out
        assert "in_progress" in out


class TestGanttHtml:
    """HTML renderer: well-formed HTML5."""

    def test_html_output_parses(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        cfg = GanttConfig(mode="html", title="Build Gantt")
        out = GanttEngine(five_task_fixture).render(cfg)

        # Use the stdlib HTML parser to confirm it's well-formed.
        # A simple subclass that just records whether parsing succeeded.
        class _StrictParser(HTMLParser):
            def __init__(self) -> None:
                super().__init__(convert_charrefs=True)
                self.errors: list[str] = []
                self.tag_count = 0

            def error(self, message: str) -> None:
                self.errors.append(message)

            def handle_starttag(self, tag: str, attrs: list) -> None:
                self.tag_count += 1

        parser = _StrictParser()
        parser.feed(out)
        parser.close()

        # HTML5 tables contain <table>, <thead>, <tbody>, <tr>, <th>, <td>.
        assert "<table" in out, "missing <table> tag"
        assert "<thead" in out, "missing <thead>"
        assert "<tbody" in out, "missing <tbody>"
        assert parser.tag_count > 10, "expected >10 HTML tags in chart"

        # All 5 task names rendered.
        for name in ("Foundation", "Framing", "Roofing", "Siding", "Painting"):
            assert name in out, f"missing task name {name!r} in HTML"


class TestGanttJson:
    """JSON renderer: structured data."""

    def test_json_shape_and_content(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        cfg = GanttConfig(mode="json", title="Build Gantt")
        out = GanttEngine(five_task_fixture).render(cfg)
        data = json.loads(out)

        assert data["title"] == "Build Gantt"
        assert data["config"]["mode"] == "json"
        # 12 days from 2030-09-01 to 2030-09-12.
        assert len(data["days"]) == 12
        assert data["days"][0] == "2030-09-01"
        assert data["days"][-1] == "2030-09-12"
        # 5 tasks.
        assert len(data["tasks"]) == 5
        ueids = {t["ueid"] for t in data["tasks"]}
        assert len(ueids) == 5
        # Each task has a glyph row of length == days length.
        for t in data["tasks"]:
            assert len(t["glyphs"]) == 12
            # span_start < span_end.
            assert t["span_start"] < t["span_end"]
            # Dep fields are lists (possibly empty).
            assert isinstance(t["deps_down"], list)
            assert isinstance(t["deps_out"], list)


# ─────────────────────────────────────────────────────────────────────
# optimizer tests
# ─────────────────────────────────────────────────────────────────────


class TestOptimizer:
    """Topological sort + priority weighting."""

    def test_priority_weighted_produces_valid_topo_order(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        cfg = OptimizeConfig(strategy=OptimizeStrategy.PRIORITY_WEIGHTED)
        result = Optimizer(five_task_fixture).optimize(cfg)

        # No cycle.
        assert not result.has_cycle
        # All 5 tasks present, in some order.
        assert len(result.ordered) == 5
        ueids_in_order = [t.ueid for t in result.ordered]
        assert set(ueids_in_order) == {t["ueid"] for t in five_task_fixture}
        # Positions are 0..4.
        assert [t.position for t in result.ordered] == [0, 1, 2, 3, 4]

    def test_priority_weighted_respects_all_hard_deps(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        cfg = OptimizeConfig(strategy=OptimizeStrategy.PRIORITY_WEIGHTED)
        result = Optimizer(five_task_fixture).optimize(cfg)

        # Build a position map and check that every dep appears before
        # its dependent.
        pos = {t.ueid: t.position for t in result.ordered}
        for t in five_task_fixture:
            my_pos = pos[t["ueid"]]
            for dep in t.get("deps") or []:
                assert pos[dep] < my_pos, (
                    f"dep violation: {t['ueid']} (pos {my_pos}) "
                    f"appeared before its dep {dep} (pos {pos[dep]})"
                )

    def test_priority_weighted_formula(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        """weight = priority_score x (1 + blocker_count).

        priority_score = high=3, medium=2, low=1.
        blocker_count  = how many tasks this one blocks (downstream).

        In our fixture:
          t1 foundation  priority=1 (high, score 3)  blocks t2         weight = 3*2 = 6
          t2 framing     priority=2 (med, score 2)   blocks t3, t4     weight = 2*3 = 6
          t3 roofing     priority=2 (med, score 2)   blocks t5         weight = 2*2 = 4
          t4 siding      priority=3 (low, score 1)   blocks t5         weight = 1*2 = 2
          t5 painting    priority=1 (high, score 3)  blocks nothing    weight = 3*1 = 3
        """
        cfg = OptimizeConfig(strategy=OptimizeStrategy.PRIORITY_WEIGHTED)
        result = Optimizer(five_task_fixture).optimize(cfg)

        expected_weights = {
            "tsk:foundation:11111111-1111-1111-1111-111111111111:1111111111111111": 6.0,
            "tsk:framing:22222222-2222-2222-2222-222222222222:2222222222222222": 6.0,
            "tsk:roofing:33333333-3333-3333-3333-333333333333:3333333333333333": 4.0,
            "tsk:siding:44444444-4444-4444-4444-444444444444:4444444444444444": 2.0,
            "tsk:painting:55555555-5555-5555-5555-555555555555:5555555555555555": 3.0,
        }
        actual = {t.ueid: t.weight for t in result.ordered}
        for ueid, w in expected_weights.items():
            assert actual[ueid] == pytest.approx(w), (
                f"{ueid}: expected weight {w}, got {actual[ueid]}"
            )

        # Rationale strings mention "priority" (and, for blockers, "blocks N others").
        for t in result.ordered:
            assert "priority" in t.rationale, (
                f"rationale missing 'priority': {t.rationale!r}"
            )

    def test_fifo_respects_deps_too(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        cfg = OptimizeConfig(strategy=OptimizeStrategy.FIFO)
        result = Optimizer(five_task_fixture).optimize(cfg)
        assert not result.has_cycle
        assert len(result.ordered) == 5
        # Dep check.
        pos = {t.ueid: t.position for t in result.ordered}
        for t in five_task_fixture:
            for dep in t.get("deps") or []:
                assert pos[dep] < pos[t["ueid"]]

    def test_critical_path_orders_bottleneck_first(
        self, five_task_fixture: list[dict[str, Any]]
    ) -> None:
        """The longest path in the fixture is t1→t2→t3→t5 (or t4) with 3 hops."""
        cfg = OptimizeConfig(strategy=OptimizeStrategy.CRITICAL_PATH)
        result = Optimizer(five_task_fixture).optimize(cfg)
        assert not result.has_cycle
        assert len(result.ordered) == 5
        # Foundation has the longest critical path (downstream chain).
        pos = {t.ueid: t.position for t in result.ordered}
        foundation_ueid = (
            "tsk:foundation:11111111-1111-1111-1111-111111111111:1111111111111111"
        )
        # Foundation has cp_len = 3 (chain to painting).
        # Painting has cp_len = 0 (source of its chain when reversed).
        foundation_pos = pos[foundation_ueid]
        painting_pos = pos[
            "tsk:painting:55555555-5555-5555-5555-555555555555:5555555555555555"
        ]
        assert foundation_pos < painting_pos


class TestCycleDetection:
    """The optimizer must reject cycles rather than loop forever."""

    def test_cycle_returns_has_cycle_true(self) -> None:
        cyclic = [
            _mk_task("a:b:c:d:1", "A", deps=["c:b:c:d:1"]),
            _mk_task("b:b:c:d:1", "B", deps=["a:b:c:d:1"]),
            _mk_task("c:b:c:d:1", "C", deps=["b:b:c:d:1"]),
        ]
        cfg = OptimizeConfig(strategy=OptimizeStrategy.PRIORITY_WEIGHTED)
        result = Optimizer(cyclic).optimize(cfg)
        assert result.has_cycle
        assert len(result.cycle_edges) >= 1
        assert result.ordered == ()


# ─────────────────────────────────────────────────────────────────────
# CLI wiring smoke test
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def taskdog_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Mirror tests/mesh/test_taskdog_cli.py — tmp DB on both module identities."""
    db_path = tmp_path / "tasks.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT UNIQUE,
            name TEXT,
            status TEXT,
            priority INTEGER,
            planned_start TEXT,
            planned_end TEXT,
            deadline TEXT,
            created_at TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            deps TEXT NOT NULL DEFAULT '[]',
            audit_log TEXT NOT NULL DEFAULT '[]',
            started_at TEXT,
            completed_at TEXT,
            priority_label TEXT NOT NULL DEFAULT 'P2'
        );
    """)
    conn.commit()
    conn.close()

    # Patch both identities (dual-module pattern; W6.X item 3 fix).
    original_src = taskdog_mod.TASKDOG_DB
    taskdog_mod.TASKDOG_DB = db_path
    from mesh.adapters import taskdog as taskdog_mod_for_main
    original_main = taskdog_mod_for_main.TASKDOG_DB
    taskdog_mod_for_main.TASKDOG_DB = db_path

    yield db_path

    taskdog_mod.TASKDOG_DB = original_src
    taskdog_mod_for_main.TASKDOG_DB = original_main


def _seed_event(ueid: str, title: str, due: str, priority: int = 2) -> PropagationEvent:
    return PropagationEvent(
        event_id=f"evt_{ueid[:6]}",
        ueid=ueid,
        action=TaskAction.CREATE,
        fields={"title": title, "due": due, "priority": priority},
        approved_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        source_fork="interfaces/cli",
    )


class TestCliWiring:
    """Verify the new subcommands flow through taskdog_cli.main()."""

    def test_gantt_subcommand_dispatches(
        self, taskdog_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # Seed two tasks directly via the adapter (write surface).
        adapter = TaskdogAdapter()
        adapter.apply_change(
            _seed_event(
                "tsk:foundation:11111111-1111-1111-1111-111111111111:1111111111111111",
                "Foundation",
                "2026-09-05",
                priority=1,
            )
        )
        adapter.apply_change(
            _seed_event(
                "tsk:framing:22222222-2222-2222-2222-222222222222:2222222222222222",
                "Framing",
                "2026-09-08",
                priority=2,
            )
        )

        rc = td_main(["gantt", "--mode=json", "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["title"]
        assert len(data["days"]) >= 1
        assert len(data["tasks"]) == 2

    def test_optimize_subcommand_dispatches(
        self, taskdog_db: Path, capsys: pytest.CaptureFixture
    ) -> None:
        adapter = TaskdogAdapter()
        adapter.apply_change(
            _seed_event(
                "tsk:foundation:11111111-1111-1111-1111-111111111111:1111111111111111",
                "Foundation",
                "2026-09-05",
                priority=1,
            )
        )
        adapter.apply_change(
            _seed_event(
                "tsk:framing:22222222-2222-2222-2222-222222222222:2222222222222222",
                "Framing",
                "2026-09-08",
                priority=2,
            )
        )

        rc = td_main(["optimize", "--strategy=fifo", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["strategy"] == "fifo"
        assert len(data["ordered"]) == 2
