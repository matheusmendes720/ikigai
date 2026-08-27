"""Unit tests for :mod:`operational.persistence.runner`."""
from __future__ import annotations

from pathlib import Path

import pytest

from operational.persistence.exceptions import MigrationError
from operational.persistence.runner import MigrationRunner, get_applied_migrations
from operational.persistence.sqlite import get_connection


@pytest.fixture
def conn() -> Any:
    c = get_connection(":memory:")
    yield c
    c.close()


@pytest.fixture
def migration_dir(tmp_path: Path) -> Path:
    d = tmp_path / "migrations"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# MigrationRunner construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_default_migration_dir(self, conn: Any) -> None:
        runner = MigrationRunner(conn)
        assert runner._dir.name == "migrations"  # noqa: SLF001

    def test_custom_migration_dir(self, conn: Any, migration_dir: Path) -> None:
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        assert runner._dir == migration_dir  # noqa: SLF001


# ---------------------------------------------------------------------------
# apply_one
# ---------------------------------------------------------------------------


class TestApplyOne:
    def test_apply_one_creates_table(self, conn: Any, migration_dir: Path) -> None:
        sql = "CREATE TABLE test_apply (id INT);"
        (migration_dir / "001_test.sql").write_text(sql, encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        assert runner.apply_one("001_test") is True
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_apply'",
        ).fetchall()
        assert len(rows) == 1

    def test_apply_one_idempotent(self, conn: Any, migration_dir: Path) -> None:
        sql = "CREATE TABLE test_idem (id INT);"
        (migration_dir / "001_idem.sql").write_text(sql, encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        assert runner.apply_one("001_idem") is True
        assert runner.apply_one("001_idem") is False

    def test_apply_one_records_success(self, conn: Any, migration_dir: Path) -> None:
        sql = "CREATE TABLE test_record (id INT);"
        (migration_dir / "001_record.sql").write_text(sql, encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        runner.apply_one("001_record")
        applied = get_applied_migrations(conn)
        assert "001_record" in applied

    def test_apply_one_records_failure(self, conn: Any, migration_dir: Path) -> None:
        sql = "CREATE BAD SQL;"
        (migration_dir / "001_bad.sql").write_text(sql, encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        with pytest.raises(MigrationError, match="001_bad"):
            runner.apply_one("001_bad")

    def test_apply_one_missing_file(self, conn: Any, migration_dir: Path) -> None:
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        with pytest.raises(MigrationError, match="not found"):
            runner.apply_one("nonexistent")


# ---------------------------------------------------------------------------
# apply_all
# ---------------------------------------------------------------------------


class TestApplyAll:
    def test_apply_all_pending(self, conn: Any, migration_dir: Path) -> None:
        (migration_dir / "001_a.sql").write_text("CREATE TABLE a (id INT);", encoding="utf-8")
        (migration_dir / "002_b.sql").write_text("CREATE TABLE b (id INT);", encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        applied = runner.apply_all()
        assert applied == ["001_a", "002_b"]

    def test_apply_all_empty_when_none_pending(
        self, conn: Any, migration_dir: Path,
    ) -> None:
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        applied = runner.apply_all()
        assert applied == []

    def test_apply_all_skips_existing(self, conn: Any, migration_dir: Path) -> None:
        (migration_dir / "001_a.sql").write_text("CREATE TABLE a (id INT);", encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        runner.apply_one("001_a")
        second = runner.apply_all()
        assert second == []


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


class TestQuery:
    def test_applied_returns_list(self, conn: Any, migration_dir: Path) -> None:
        (migration_dir / "001_x.sql").write_text("CREATE TABLE x (id INT);", encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        assert runner.applied() == []
        runner.apply_one("001_x")
        assert runner.applied() == ["001_x"]

    def test_pending_returns_list(self, conn: Any, migration_dir: Path) -> None:
        (migration_dir / "001_a.sql").write_text("CREATE TABLE a (id INT);", encoding="utf-8")
        (migration_dir / "002_b.sql").write_text("CREATE TABLE b (id INT);", encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        runner.apply_one("001_a")
        assert runner.pending() == ["002_b"]


# ---------------------------------------------------------------------------
# get_applied_migrations standalone
# ---------------------------------------------------------------------------


class TestGetApplied:
    def test_returns_empty_when_no_table(self, conn: Any) -> None:
        # _migrations table does not exist
        assert get_applied_migrations(conn) == []

    def test_returns_only_successful(self, conn: Any, migration_dir: Path) -> None:
        (migration_dir / "001_good.sql").write_text("CREATE TABLE g (id INT);", encoding="utf-8")
        runner = MigrationRunner(conn, migration_dir=migration_dir)
        runner.apply_one("001_good")
        assert get_applied_migrations(conn) == ["001_good"]
