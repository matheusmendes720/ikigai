"""E2E test: full month simulation of period_reports sync.

Source: .omo/plans/period-reports-sync.md T8

Simulates 1 user completing a full month:
- 1 sonho (root, 365 days)
- 1 onda (45-day focused effort)
- 3 weekly reports (within the onda)
- 21 daily reports (7 days x 3 weeks)

Total: 26 reports organized in 4-level hierarchy.
"""
from __future__ import annotations

import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[2] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from middleware.period_sync import PeriodReportSync


def _md(period: str, id_: str, date_: date, end: date | None = None,
        parent: str | None = None, verdict: str = "PASS", score: float = 0.8,
        sonho_id: str | None = None) -> str:
    """Generate a period report markdown file content."""
    if end is None:
        end = date_
    frontmatter = f"""---
type: period_report
entity_type: period_report
period: {period}
id: {id_}
date_start: {date_.isoformat()}
date_end: {end.isoformat()}
verdict: {verdict}
verdict_score: {score}
template_version: '1.0'
ikigai_cluster: plan
ikigai_vector: skill
status: active
tags: [period/{period}]
"""
    if parent:
        frontmatter += f"parent_period: {parent}\n"
    if sonho_id:
        frontmatter += f"sonho_id: {sonho_id}\n"
    frontmatter += "---\n\n# Body\n"
    return frontmatter


@pytest.mark.e2e
class TestFullMonthSimulation:

    def test_full_cycle_one_sonho_one_onda_three_weeks_twenty_one_days(
        self, tmp_path
    ):
        """Full E2E: 26 reports across 4-level hierarchy."""
        vault = tmp_path / "vault"
        templates = vault / "_templates_periodos"
        templates.mkdir(parents=True)

        sonho_id = "e2e-sonho-2026"
        onda_id = "e2e-onda-Q1"
        week_ids = ["e2e-week-01", "e2e-week-02", "e2e-week-03"]

        # 1 Sonho (root, 365 days)
        (templates / "01-sonho.md").write_text(
            _md("sonho", sonho_id, date(2026, 1, 1), date(2026, 12, 31),
                verdict="ACTIVE", score=0.70, sonho_id=sonho_id),
            encoding="utf-8",
        )

        # 1 Onda (45 days, child of sonho)
        (templates / "02-onda.md").write_text(
            _md("onda", onda_id, date(2026, 1, 1), date(2026, 2, 14),
                parent=sonho_id, verdict="CONTINUE_WAVE", score=0.78,
                sonho_id=sonho_id),
            encoding="utf-8",
        )

        # 3 Weeks (children of onda)
        week_start = date(2026, 1, 1)
        for i, week_id in enumerate(week_ids):
            week_start_d = week_start + timedelta(weeks=i)
            week_end_d = week_start_d + timedelta(days=6)
            (templates / f"03-week-{i+1:02d}.md").write_text(
                _md("weekly", week_id, week_start_d, week_end_d,
                    parent=onda_id, score=0.85, sonho_id=sonho_id),
                encoding="utf-8",
            )

        # 21 Days (7 per week, children of respective weeks)
        day_counter = 0
        for week_idx, week_id in enumerate(week_ids):
            week_start_d = week_start + timedelta(weeks=week_idx)
            for day_idx in range(7):
                day_date = week_start_d + timedelta(days=day_idx)
                day_id = f"e2e-day-w{week_idx+1}-d{day_idx+1}"
                (templates / f"04-{day_id}.md").write_text(
                    _md("daily", day_id, day_date, day_date,
                        parent=week_id, score=0.82, sonho_id=sonho_id),
                    encoding="utf-8",
                )
                day_counter += 1

        assert day_counter == 21

        # Now run sync with multi-pass to resolve all orphans
        db = tmp_path / "e2e_test.db"
        sync = PeriodReportSync(vault, db)

        start = time.perf_counter()

        # Multiple passes until no orphans remain
        max_passes = 5
        for pass_num in range(1, max_passes + 1):
            stats = sync.sync_vault_to_db()
            if stats.orphans == 0 and stats.ingested == 0:
                break
        else:
            pytest.fail(
                f"After {max_passes} passes, {stats.orphans} orphans remain: "
                f"{stats.file_errors}"
            )

        duration = time.perf_counter() - start

        # Assertions
        with sqlite3.connect(db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM period_reports").fetchone()[0]
            assert count == 26, f"Expected 26 reports (1+1+3+21), got {count}"

            # Verify hierarchy
            tree = sync.get_period_hierarchy(sonho_id)
            assert tree["count"] == 26, f"Hierarchy count {tree['count']}, expected 26"
            assert len(tree["tree"]) == 1, "Should have 1 root (sonho)"

            # Verify hierarchy depth
            root = tree["tree"][0]
            assert root["id"] == sonho_id
            assert len(root["children"]) == 1, "Sonho should have 1 child (onda)"

            onda = root["children"][0]
            assert onda["id"] == onda_id
            assert len(onda["children"]) == 3, "Onda should have 3 children (weeks)"

            # Each week has 7 days
            for week in onda["children"]:
                assert len(week["children"]) == 7, (
                    f"Week {week['id']} should have 7 children (days)"
                )

        # Performance: full E2E should complete in < 5 seconds
        assert duration < 5.0, f"E2E took {duration:.2f}s, expected < 5s"

        print(f"\nE2E PASSED: 26 reports in {duration*1000:.1f}ms")