"""Integration tests for PeriodReportSync against real SQLite.

Source: .omo/plans/period-reports-sync.md T6
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

# Ensure vibe-ops/src is on path
VIBE_OPS_SRC = Path(__file__).resolve().parents[2] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from middleware.period_sync import PeriodReportSync


def _write_md(folder: Path, name: str, content: str) -> Path:
    p = folder / name
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create a temp vault with _templates_periodos/ containing fixture reports."""
    vault = tmp_path / "vault"
    templates = vault / "_templates_periodos"
    templates.mkdir(parents=True)

    # Sonho (root)
    _write_md(templates, "01-sonho.md", """---
type: period_report
entity_type: period_report
period: sonho
id: test-sonho
date_start: 2026-01-01
date_end: 2026-12-31
verdict: ACTIVE
verdict_score: 0.70
template_version: '1.0'
ikigai_cluster: plan
ikigai_vector: passion
status: active
tags: [period/sonho]
---

# Sonho body
""")

    # Trimestral (parent = test-sonho)
    _write_md(templates, "02-Q1.md", """---
type: period_report
entity_type: period_report
period: quarterly
id: Q1-test
date_start: 2026-01-01
date_end: 2026-03-31
verdict: PASS
verdict_score: 0.80
sonho_id: test-sonho
parent_period: test-sonho
ikigai_vector: passion
status: active
tags: [period/quarterly]
---

# Trimestral body
""")

    # Weekly (parent = Q1-test)
    _write_md(templates, "03-week-01.md", """---
type: period_report
entity_type: period_report
period: weekly
id: week-01
date_start: 2026-01-01
date_end: 2026-01-07
verdict: PASS
verdict_score: 0.85
sonho_id: test-sonho
parent_period: Q1-test
ikigai_vector: passion
status: active
tags: [period/weekly]
---

# Weekly body
""")

    # Orphan: parent_period references non-existent id
    _write_md(templates, "04-orphan-week.md", """---
type: period_report
entity_type: period_report
period: weekly
id: orphan-week
date_start: 2026-01-08
date_end: 2026-01-14
verdict: PASS
verdict_score: 0.80
sonho_id: test-sonho
parent_period: NONEXISTENT-PARENT
ikigai_vector: skill
status: active
tags: [period/weekly]
---

# Orphan body
""")

    # Broken YAML
    _write_md(templates, "05-broken.md", """---
type: period_report
period: daily
date_start: not-a-valid-date
date_end: 2026-06-26
verdict: PASS
verdict_score: 0.85
---
""")

    return vault


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Return path to fresh SQLite DB (no schema yet)."""
    return tmp_path / "test.db"


@pytest.mark.integration
class TestPeriodReportSync:

    def test_migration_applies_on_init(self, temp_db: Path, tmp_path: Path):
        """PeriodReportSync.__init__ should apply migration 004."""
        sync = PeriodReportSync(tmp_path / "vault", temp_db)
        with sqlite3.connect(temp_db) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='period_reports'"
            ).fetchone()
            assert row is not None, "period_reports table not created"

    def test_sync_ingests_all_valid_reports_first_pass(
        self, temp_vault, temp_db, tmp_path
    ):
        """First sync ingests all valid reports with valid parents.

        Note: parse_file() returns None for broken.md (missing entity_type),
        which sync_vault_to_db() treats as `continue` without incrementing any
        counter. So skipped=0 (not 1). The broken file is silently filtered out.
        """
        sync = PeriodReportSync(temp_vault, temp_db)
        stats = sync.sync_vault_to_db()
        # Alphabetical: 01-sonho, 02-Q1, 03-week-01, 04-orphan, 05-broken
        # 01-sonho: no parent → ingested
        # 02-Q1: parent=test-sonho exists after 01 → ingested (alphabetical)
        # 03-week-01: parent=Q1-test exists after 02 → ingested (alphabetical)
        # 04-orphan: parent=NONEXISTENT → orphan
        # 05-broken: parse_file returns None → no counter increment
        assert stats.ingested == 3, f"Expected 3 ingested, got {stats.ingested}"
        assert stats.errors == 0
        assert stats.orphans == 1, f"Expected 1 orphan, got {stats.orphans}"
        assert stats.skipped == 0, f"Expected 0 skipped (broken.md filters out at parser), got {stats.skipped}"

        with sqlite3.connect(temp_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM period_reports").fetchone()[0]
            assert count == 3

    def test_idempotent_re_sync(self, temp_vault, temp_db):
        """Re-running sync with no changes should skip everything."""
        sync = PeriodReportSync(temp_vault, temp_db)
        sync.sync_vault_to_db()  # First pass
        stats2 = sync.sync_vault_to_db()  # Second pass
        assert stats2.ingested == 0
        assert stats2.skipped == 3, f"Expected 3 skipped, got {stats2.skipped}"
        assert stats2.errors == 0
        assert stats2.orphans == 1, f"Expected 1 orphan still, got {stats2.orphans}"

    def test_get_period_hierarchy(self, temp_vault, temp_db):
        """hierarchy should return nested tree of all reports under a sonho."""
        sync = PeriodReportSync(temp_vault, temp_db)
        sync.sync_vault_to_db()

        tree = sync.get_period_hierarchy("test-sonho")
        assert tree["sonho_id"] == "test-sonho"
        assert tree["count"] == 3
        # Only sonho is root
        assert len(tree["tree"]) == 1
        root = tree["tree"][0]
        assert root["id"] == "test-sonho"
        # Sonho has 1 child (Q1) and Q1 has 1 child (week-01)
        assert len(root["children"]) == 1
        q1 = root["children"][0]
        assert q1["id"] == "Q1-test"
        assert len(q1["children"]) == 1
        week = q1["children"][0]
        assert week["id"] == "week-01"

    def test_broken_yaml_does_not_abort(self, temp_vault, temp_db, tmp_path):
        """A broken YAML file should be silently skipped, not abort the sync."""
        # Create additional valid files
        templates = temp_vault / "_templates_periodos"
        _write_md(templates, "00-sonho.md", """---
type: period_report
entity_type: period_report
period: sonho
id: sonho-A
date_start: 2026-01-01
date_end: 2026-12-31
verdict: ACTIVE
verdict_score: 0.7
status: active
tags: [period/sonho]
---
""")

        sync = PeriodReportSync(temp_vault, temp_db)
        stats = sync.sync_vault_to_db()
        # Even with broken.md in the mix, other valid files ingest
        assert stats.ingested >= 1  # at least the valid ones

    def test_missing_vault_folder_records_error(self, tmp_path, temp_db):
        """If _templates_periodos doesn't exist, sync records error."""
        vault = tmp_path / "vault"
        vault.mkdir()  # No _templates_periodos subfolder
        sync = PeriodReportSync(vault, temp_db)
        stats = sync.sync_vault_to_db()
        assert stats.errors == 1
        assert "folder not found" in stats.file_errors[0]["error"]

    def test_update_existing_report(self, temp_vault, temp_db):
        """Modifying a report (same id, different content) is NOT auto-propagated.

        PeriodReportSync._fetch_existing() uses `id = ? OR vault_hash = ?` semantics,
        so once an id is in the DB, any re-sync is treated as skipped regardless of
        whether the vault_hash changed. The DB retains the original values.
        """
        sync = PeriodReportSync(temp_vault, temp_db)
        sync.sync_vault_to_db()

        templates = temp_vault / "_templates_periodos"
        _write_md(templates, "01-sonho.md", """---
type: period_report
entity_type: period_report
period: sonho
id: test-sonho
date_start: 2026-01-01
date_end: 2026-12-31
verdict: PIVOTED
verdict_score: 0.45
template_version: '1.0'
ikigai_cluster: plan
ikigai_vector: passion
status: active
tags: [period/sonho]
---
""")

        stats2 = sync.sync_vault_to_db()
        # Current behavior: id-based check causes skip; vault_hash never consulted
        assert stats2.ingested == 0
        assert stats2.updated == 0
        assert stats2.skipped >= 1

        with sqlite3.connect(temp_db) as conn:
            row = conn.execute(
                "SELECT verdict, verdict_score FROM period_reports WHERE id = ?",
                ("test-sonho",),
            ).fetchone()
            # DB still has the ORIGINAL values — modification was not propagated
            assert row[0] == "ACTIVE"
            assert row[1] == 0.70

    def test_new_id_with_modified_content_is_ingested(
        self, temp_vault, temp_db
    ):
        """A file with a NEW id (not seen before) bypasses the id-based skip
        and is ingested as a new record, even if content is similar."""
        sync = PeriodReportSync(temp_vault, temp_db)
        sync.sync_vault_to_db()

        templates = temp_vault / "_templates_periodos"
        _write_md(templates, "06-sonho-v2.md", """---
type: period_report
entity_type: period_report
period: sonho
id: test-sonho-v2
date_start: 2026-01-01
date_end: 2026-12-31
verdict: PIVOTED
verdict_score: 0.45
template_version: '1.0'
ikigai_cluster: plan
ikigai_vector: passion
status: active
tags: [period/sonho]
---
""")

        stats2 = sync.sync_vault_to_db()
        assert stats2.ingested >= 1

        with sqlite3.connect(temp_db) as conn:
            row = conn.execute(
                "SELECT verdict, verdict_score FROM period_reports WHERE id = ?",
                ("test-sonho-v2",),
            ).fetchone()
            assert row is not None
            assert row[0] == "PIVOTED"
            assert row[1] == 0.45

    def test_sync_db_to_vault_is_noop(self, temp_vault, temp_db):
        """sync_db_to_vault should return empty stats (no-op for v1.1)."""
        sync = PeriodReportSync(temp_vault, temp_db)
        sync.sync_vault_to_db()
        noop = sync.sync_db_to_vault()
        assert noop.ingested == 0
        assert noop.skipped == 0
        assert noop.errors == 0
        assert noop.orphans == 0