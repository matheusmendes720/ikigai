"""Fixture smoke tests (T9).

Verifies the conftest fixtures work and the fixture vault can be
ingested end-to-end.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


class TestFixtureVault:
    def test_fixture_vault_has_seven_files(self, fixture_vault: Path):
        md_files = list(fixture_vault.rglob("*.md"))
        assert len(md_files) == 7

    def test_fixture_vault_has_six_valid_one_broken(self, fixture_vault: Path):
        broken = fixture_vault / "2_projeto" / "broken.md"
        assert broken.exists()
        content = broken.read_text(encoding="utf-8")
        assert "[unclosed bracket" in content


class TestTempFixtures:
    def test_temp_vault_isolated(self, temp_vault: Path, fixture_vault: Path):
        assert temp_vault.exists()
        assert temp_vault != fixture_vault
        # All 7 files copied.
        assert len(list(temp_vault.rglob("*.md"))) == 7

    def test_temp_db_has_planning_entities(self, temp_db: Path):
        with sqlite3.connect(str(temp_db)) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='planning_entities'"
            ).fetchone()
        assert row is not None


class TestSyncEngineFixture:
    def test_sync_engine_ingests_seven(self, sync_engine, temp_db: Path):
        result = sync_engine.sync_vault_to_code()
        assert result["ingested"] == 6
        assert result["errors"] == 1  # broken.md
        with sqlite3.connect(str(temp_db)) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM planning_entities"
            ).fetchone()[0]
        assert total == 6

    def test_populated_sync_engine_is_idempotent(self, populated_sync_engine, temp_db: Path):
        # Re-running should not change row count.
        result = populated_sync_engine.sync_vault_to_code()
        assert result["ingested"] == 0
        assert result["skipped"] == 6
        with sqlite3.connect(str(temp_db)) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM planning_entities"
            ).fetchone()[0]
        assert total == 6