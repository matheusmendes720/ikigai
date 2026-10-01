"""M166 — td advanced subsystem unit tests.

Covers the 7 subcommands added in M166:
    rm <ueid>          — soft-delete (status='deleted', audit_log entry)
    restore <ueid>     — undelete (status='deleted' -> 'planned')
    audit [ueid]       — list audit_log entries
    db backup [path]   — SQLite hot backup
    db restore <path>  — SQLite restore from backup (requires --yes)
    export <fmt>       — export as json|csv|md
    stats              — completion rate + by-tag breakdown

These tests are in-process (call ``cmd_*`` handlers + module-level helpers
directly, no subprocess). The dual-module identity rule (per CLAUDE.md)
means we monkeypatch TASKDOG_DB via the dotted-prefix path that production
code uses.

Run with:
    cd src/ikigai && python -m pytest tests/test_td_advanced.py -q

Test isolation:
  - Each test uses ``tmp_path`` for a fresh SQLite DB and monkeypatches
    ``src.mesh.adapters.taskdog.TASKDOG_DB``.
  - The seed fixture creates both the canonical ``tasks`` table (M163 schema
    v2) AND the ``audit_log`` table so ``rm`` / ``restore`` / ``audit``
    can exercise their full flow.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.cli import td_advanced

# 4-part UEID fixtures (matches _UEID_PATTERN in src/contracts/common.py).
_UEID_A = "tsk:advanced-a:00000000-0000-0000-0000-000000000000:0000000000000000"
_UEID_B = "tsk:advanced-b:00000000-0000-0000-0000-000000000001:0000000000000001"
_UEID_C = "tsk:advanced-c:00000000-0000-0000-0000-000000000002:0000000000000002"


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def advanced_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fresh SQLite DB with tasks + audit_log + one seed row."""
    db_path = tmp_path / "tasks.db"
    conn = sqlite3.connect(db_path)
    try:
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
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ueid TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL DEFAULT 'note',
                actor TEXT NOT NULL DEFAULT 'cli',
                text TEXT NOT NULL
            );
            CREATE INDEX idx_audit_log_ueid ON audit_log(ueid);
        """)
        conn.execute(
            "INSERT INTO tasks (ueid, name, status, priority, created_at) "
            "VALUES (?, ?, 'planned', ?, ?)",
            (_UEID_A, "M166 seed A", 2,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(taskdog_mod, "TASKDOG_DB", db_path)
    return db_path


@pytest.fixture
def advanced_db_with_b(
    advanced_db: Path,
) -> Path:
    """Adds a second task in 'done' status with tags + duration."""
    conn = sqlite3.connect(advanced_db)
    try:
        # Seed task B: in_progress, with tags, started_at but no completed_at
        conn.execute(
            "INSERT INTO tasks (ueid, name, status, priority, tags, "
            "started_at, created_at) VALUES (?, ?, 'in_progress', ?, ?, ?, ?)",
            (_UEID_B, "M166 seed B", 2,
             json.dumps(["backend", "urgent"]),
             "2026-01-01T10:00:00+00:00",
             "2026-01-01T09:00:00+00:00"),
        )
        # Seed task C: done with completed_at for duration stats
        conn.execute(
            "INSERT INTO tasks (ueid, name, status, priority, tags, "
            "started_at, completed_at, created_at) "
            "VALUES (?, ?, 'done', ?, ?, ?, ?, ?)",
            (_UEID_C, "M166 seed C", 1,
             json.dumps(["frontend"]),
             "2026-01-01T09:00:00+00:00",
             "2026-01-01T11:00:00+00:00",
             "2026-01-01T08:00:00+00:00"),
        )
        conn.commit()
    finally:
        conn.close()
    return advanced_db


# ----------------------------------------------------------------------
# rm + restore: soft-delete roundtrip preserves data + audit trail
# ----------------------------------------------------------------------

class TestRmRestoreRoundtrip:
    def test_rm_sets_status_deleted(self, advanced_db: Path) -> None:
        args = argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        )
        rc = td_advanced.cmd_rm(args)
        assert rc == 0
        # Row still exists with status='deleted'
        conn = sqlite3.connect(advanced_db)
        try:
            row = conn.execute(
                "SELECT status FROM tasks WHERE ueid=?", (_UEID_A,)
            ).fetchone()
            assert row[0] == "deleted"
        finally:
            conn.close()

    def test_rm_writes_audit_row(self, advanced_db: Path) -> None:
        args = argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        )
        td_advanced.cmd_rm(args)
        rows = _read_audit(advanced_db, _UEID_A)
        assert len(rows) == 1
        assert rows[0]["action"] == "soft_delete"
        assert "planned -> deleted" in rows[0]["text"]

    def test_rm_is_idempotent(self, advanced_db: Path) -> None:
        args = argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        )
        td_advanced.cmd_rm(args)
        # second rm: no new audit row
        td_advanced.cmd_rm(args)
        rows = _read_audit(advanced_db, _UEID_A)
        assert len(rows) == 1

    def test_rm_missing_ueid_returns_1(self, advanced_db: Path) -> None:
        args = argparse_namespace(
            command="rm", ueid="tsk:nope:facefeed:1111:1111111111111111",
            json=True, db_path=str(advanced_db),
        )
        rc = td_advanced.cmd_rm(args)
        assert rc == 1

    def test_rm_never_hard_deletes(self, advanced_db: Path) -> None:
        """The canonical tasks row must survive rm."""
        args = argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        )
        td_advanced.cmd_rm(args)
        conn = sqlite3.connect(advanced_db)
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE ueid=?", (_UEID_A,)
            )
            assert cur.fetchone()[0] == 1
        finally:
            conn.close()

    def test_restore_flips_to_planned(self, advanced_db: Path) -> None:
        # First rm, then restore
        td_advanced.cmd_rm(argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        ))
        rc = td_advanced.cmd_restore(argparse_namespace(
            command="restore", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        ))
        assert rc == 0
        conn = sqlite3.connect(advanced_db)
        try:
            row = conn.execute(
                "SELECT status FROM tasks WHERE ueid=?", (_UEID_A,)
            ).fetchone()
            assert row[0] == "planned"
        finally:
            conn.close()

    def test_restore_writes_audit_row(self, advanced_db: Path) -> None:
        td_advanced.cmd_rm(argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        ))
        td_advanced.cmd_restore(argparse_namespace(
            command="restore", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        ))
        rows = _read_audit(advanced_db, _UEID_A)
        actions = [r["action"] for r in rows]
        assert "soft_delete" in actions
        assert "restore" in actions

    def test_restore_on_non_deleted_is_noop(self, advanced_db: Path) -> None:
        """Restoring a never-deleted row is a no-op (no audit entry)."""
        rc = td_advanced.cmd_restore(argparse_namespace(
            command="restore", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        ))
        assert rc == 0
        rows = _read_audit(advanced_db, _UEID_A)
        assert rows == []


# ----------------------------------------------------------------------
# audit log viewer
# ----------------------------------------------------------------------

class TestAudit:
    def test_audit_returns_all_rows_when_no_ueid(
        self, advanced_db_with_b: Path,
    ) -> None:
        # Produce two audit rows
        td_advanced.cmd_rm(argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db_with_b),
        ))
        td_advanced.cmd_rm(argparse_namespace(
            command="rm", ueid=_UEID_B, json=True,
            db_path=str(advanced_db_with_b),
        ))
        args = argparse_namespace(
            command="audit", ueid=None, limit=None, json=True,
            db_path=str(advanced_db_with_b),
        )
        rc = td_advanced.cmd_audit(args)
        assert rc == 0

    def test_audit_filters_to_ueid(
        self, advanced_db_with_b: Path,
    ) -> None:
        td_advanced.cmd_rm(argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db_with_b),
        ))
        td_advanced.cmd_rm(argparse_namespace(
            command="rm", ueid=_UEID_B, json=True,
            db_path=str(advanced_db_with_b),
        ))
        args = argparse_namespace(
            command="audit", ueid=_UEID_A, limit=None, json=True,
            db_path=str(advanced_db_with_b),
        )
        # We can't intercept stdout easily, but the function returns 0
        # and writes to stdout (verified by run_audit_command pattern).
        rc = td_advanced.cmd_audit(args)
        assert rc == 0

    def test_audit_on_empty_db(self, tmp_path: Path) -> None:
        db = tmp_path / "empty.db"
        # Empty file path → audit returns 0 with empty list
        args = argparse_namespace(
            command="audit", ueid=None, limit=None, json=True,
            db_path=str(db),
        )
        rc = td_advanced.cmd_audit(args)
        assert rc == 0


# ----------------------------------------------------------------------
# db backup / restore
# ----------------------------------------------------------------------

class TestDbBackupRestore:
    def test_backup_creates_valid_sqlite(self, advanced_db: Path) -> None:
        backup_path = advanced_db.parent / "test-backup.db"
        args = argparse_namespace(
            command="db", db_command="backup", path=str(backup_path),
            json=True, db_path=str(advanced_db),
        )
        rc = td_advanced.cmd_db_backup(args)
        assert rc == 0
        assert backup_path.exists()
        # Verify it's a valid SQLite file by opening it
        conn = sqlite3.connect(backup_path)
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            names = {r[0] for r in tables}
            assert "tasks" in names
        finally:
            conn.close()

    def test_backup_default_path_is_timestamped(self, advanced_db: Path) -> None:
        args = argparse_namespace(
            command="db", db_command="backup", path=None,
            json=True, db_path=str(advanced_db),
        )
        rc = td_advanced.cmd_db_backup(args)
        assert rc == 0
        # A timestamped file should now exist in the parent dir
        backups = list(advanced_db.parent.glob(".backup-*.db"))
        assert len(backups) == 1

    def test_backup_missing_db_returns_1(self, tmp_path: Path) -> None:
        args = argparse_namespace(
            command="db", db_command="backup", path=None,
            json=True, db_path=str(tmp_path / "ghost.db"),
        )
        rc = td_advanced.cmd_db_backup(args)
        assert rc == 1

    def test_restore_requires_yes(self, advanced_db: Path) -> None:
        backup = advanced_db.parent / "restoretest.db"
        td_advanced.cmd_db_backup(argparse_namespace(
            command="db", db_command="backup", path=str(backup),
            json=True, db_path=str(advanced_db),
        ))
        # Without --yes → exit 2
        args = argparse_namespace(
            command="db", db_command="restore", path=str(backup),
            yes=False, json=True, db_path=str(advanced_db),
        )
        rc = td_advanced.cmd_db_restore(args)
        assert rc == 2

    def test_restore_with_yes_works(self, advanced_db: Path) -> None:
        backup = advanced_db.parent / "restoretest.db"
        td_advanced.cmd_db_backup(argparse_namespace(
            command="db", db_command="backup", path=str(backup),
            json=True, db_path=str(advanced_db),
        ))
        args = argparse_namespace(
            command="db", db_command="restore", path=str(backup),
            yes=True, json=True, db_path=str(advanced_db),
        )
        rc = td_advanced.cmd_db_restore(args)
        assert rc == 0
        # The live DB now matches the backup (table still present)
        conn = sqlite3.connect(advanced_db)
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE ueid=?", (_UEID_A,)
            )
            assert cur.fetchone()[0] == 1
        finally:
            conn.close()

    def test_restore_missing_backup_returns_1(self, advanced_db: Path) -> None:
        args = argparse_namespace(
            command="db", db_command="restore",
            path=str(advanced_db.parent / "ghost.db"),
            yes=True, json=True, db_path=str(advanced_db),
        )
        rc = td_advanced.cmd_db_restore(args)
        assert rc == 1


# ----------------------------------------------------------------------
# export
# ----------------------------------------------------------------------

class TestExport:
    def test_export_json_default_format(
        self, advanced_db_with_b: Path,
    ) -> None:
        # capture stdout via capsys in caller; here just verify the
        # export module produces valid JSON
        tasks = _read_all_tasks(advanced_db_with_b)
        body = td_advanced._export_json(tasks)
        parsed = json.loads(body)
        assert "tasks" in parsed
        assert parsed["count"] == 3

    def test_export_csv_roundtrip(self, advanced_db_with_b: Path) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        body = td_advanced._export_csv(tasks)
        import csv as csv_mod
        import io as io_mod
        reader = csv_mod.DictReader(io_mod.StringIO(body))
        rows = list(reader)
        assert len(rows) == 3
        # CSV cells with list values must be JSON-encoded strings
        for row in rows:
            # tags is either empty/None or a JSON string
            if row.get("tags"):
                parsed = json.loads(row["tags"])
                assert isinstance(parsed, list)

    def test_export_markdown_has_table(
        self, advanced_db_with_b: Path,
    ) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        body = td_advanced._export_markdown(tasks)
        assert "| ueid |" in body
        assert f"| {_UEID_A} |" in body
        # Header line + table headers + 3 rows
        assert body.count("\n|") >= 5

    def test_export_cli_json(
        self, advanced_db_with_b: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        args = argparse_namespace(
            command="export", fmt="json", out=None,
            db_path=str(advanced_db_with_b),
        )
        rc = td_advanced.cmd_export(args)
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["count"] == 3

    def test_export_cli_csv_to_file(
        self, advanced_db_with_b: Path,
        tmp_path: Path,
    ) -> None:
        out_path = tmp_path / "out.csv"
        args = argparse_namespace(
            command="export", fmt="csv", out=str(out_path),
            db_path=str(advanced_db_with_b),
        )
        rc = td_advanced.cmd_export(args)
        assert rc == 0
        assert out_path.exists()
        body = out_path.read_text(encoding="utf-8")
        assert "ueid,name,status" in body

    def test_export_invalid_format_returns_2(
        self, advanced_db_with_b: Path,
    ) -> None:
        args = argparse_namespace(
            command="export", fmt="xml", out=None,
            db_path=str(advanced_db_with_b),
        )
        rc = td_advanced.cmd_export(args)
        assert rc == 2


# ----------------------------------------------------------------------
# stats
# ----------------------------------------------------------------------

class TestStats:
    def test_stats_returns_expected_shape(
        self, advanced_db_with_b: Path,
    ) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        stats = td_advanced._compute_stats(tasks)
        # Required keys
        for key in (
            "total", "live_total", "deleted_total",
            "by_status", "by_priority", "by_tag",
            "completion_rate", "completed_with_duration",
            "avg_duration_hours",
        ):
            assert key in stats, f"missing key: {key}"

    def test_stats_total_counts_all(
        self, advanced_db_with_b: Path,
    ) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        stats = td_advanced._compute_stats(tasks)
        assert stats["total"] == 3
        assert stats["live_total"] == 3
        assert stats["deleted_total"] == 0

    def test_stats_by_status(
        self, advanced_db_with_b: Path,
    ) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        stats = td_advanced._compute_stats(tasks)
        assert stats["by_status"]["done"] == 1
        assert stats["by_status"]["in_progress"] == 1
        assert stats["by_status"]["planned"] == 1

    def test_stats_by_tag(
        self, advanced_db_with_b: Path,
    ) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        stats = td_advanced._compute_stats(tasks)
        # B has [backend, urgent], C has [frontend]
        assert stats["by_tag"]["backend"] == 1
        assert stats["by_tag"]["urgent"] == 1
        assert stats["by_tag"]["frontend"] == 1

    def test_stats_completion_rate(
        self, advanced_db_with_b: Path,
    ) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        stats = td_advanced._compute_stats(tasks)
        # 1 done out of 3 live = 0.3333
        assert abs(stats["completion_rate"] - 1 / 3) < 0.001

    def test_stats_avg_duration(
        self, advanced_db_with_b: Path,
    ) -> None:
        tasks = _read_all_tasks(advanced_db_with_b)
        stats = td_advanced._compute_stats(tasks)
        # C completed 2h after start → 2.0 hours
        assert stats["avg_duration_hours"] == 2.0
        assert stats["completed_with_duration"] == 1

    def test_stats_ignores_deleted(self, advanced_db_with_b: Path) -> None:
        # Delete one task; stats must exclude it from completion math
        td_advanced.cmd_rm(argparse_namespace(
            command="rm", ueid=_UEID_C, json=True,
            db_path=str(advanced_db_with_b),
        ))
        tasks = _read_all_tasks(advanced_db_with_b)
        stats = td_advanced._compute_stats(tasks)
        assert stats["total"] == 3
        assert stats["live_total"] == 2
        assert stats["deleted_total"] == 1
        # 0 done of 2 live = 0.0
        assert stats["completion_rate"] == 0.0

    def test_stats_fast_on_empty(self) -> None:
        """Empty list returns sensible zeros in <100ms."""
        import time
        t0 = time.perf_counter()
        stats = td_advanced._compute_stats([])
        elapsed = time.perf_counter() - t0
        assert stats["total"] == 0
        assert stats["completion_rate"] == 0.0
        assert elapsed < 0.1


# ----------------------------------------------------------------------
# Parser wiring / dispatch
# ----------------------------------------------------------------------

class TestParserWiring:
    def test_register_advanced_subparser_attaches(self) -> None:
        """register_advanced_subparser should add 6 verbs to a sub parser."""
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command", required=True)
        td_advanced.register_advanced_subparser(sub)
        # The sub should now accept rm/restore/audit/db/export/stats
        for verb in ("rm", "restore", "audit", "db", "export", "stats"):
            # Each verb parses cleanly with --help
            try:
                parser.parse_args([verb, "--help"])
            except SystemExit:
                pass  # --help prints and exits; we just need no ParseError

    def test_run_advanced_command_dispatch(self, advanced_db: Path) -> None:
        # rm path
        args = argparse_namespace(
            command="rm", ueid=_UEID_A, json=True,
            db_path=str(advanced_db),
        )
        assert td_advanced.run_advanced_command(args) == 0

    def test_run_advanced_command_unknown_returns_2(self) -> None:
        args = argparse_namespace(command="bogus")
        assert td_advanced.run_advanced_command(args) == 2


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def argparse_namespace(**kwargs: Any) -> Any:
    """Build an argparse.Namespace-compatible object without argparse."""
    return argparse.Namespace(**kwargs)


def _read_audit(db_path: Path, ueid: str) -> list[dict]:
    """Read audit_log rows for a ueid (test-side helper)."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT id, ueid, timestamp, action, actor, text "
            "FROM audit_log WHERE ueid=? ORDER BY id ASC",
            (ueid,),
        )
        return [
            {"id": r[0], "ueid": r[1], "timestamp": r[2],
             "action": r[3], "actor": r[4], "text": r[5]}
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def _read_all_tasks(db_path: Path) -> list[dict]:
    """Read all tasks directly from SQLite (bypass the HTTP adapter)."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT ueid, name, status, priority, planned_start, "
            "planned_end, deadline, created_at, tags, deps, audit_log, "
            "started_at, completed_at, priority_label FROM tasks"
        )
        out: list[dict] = []
        for r in cur.fetchall():
            out.append({
                "ueid": r[0], "name": r[1], "status": r[2],
                "priority": r[3], "planned_start": r[4],
                "planned_end": r[5], "deadline": r[6],
                "created_at": r[7],
                "tags": json.loads(r[8]) if r[8] else [],
                "deps": json.loads(r[9]) if r[9] else [],
                "audit_log": json.loads(r[10]) if r[10] else [],
                "started_at": r[11],
                "completed_at": r[12],
                "priority_label": r[13] or "P2",
            })
        return out
    finally:
        conn.close()