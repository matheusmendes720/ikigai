"""M163 schema migration: taskdog tasks.db v1 → v2.

Adds 6 new columns to the ``tasks`` table:

  1. tags           TEXT NOT NULL DEFAULT '[]'      -- JSON array of strings
  2. deps           TEXT NOT NULL DEFAULT '[]'      -- JSON array of UEID strings
  3. audit_log      TEXT NOT NULL DEFAULT '[]'      -- JSON array of audit objects
  4. started_at     TEXT                            -- ISO8601, nullable
  5. completed_at   TEXT                            -- ISO8601, nullable
  6. priority_label TEXT NOT NULL DEFAULT 'P2'      -- P0/P1/P2/P3 textual

Idempotent — safe to run multiple times. Each ALTER TABLE is wrapped
in try/except; duplicate-column errors are swallowed silently so
re-running the script is a no-op.

Backups the source DB to ``<db_path>.backup-v1`` BEFORE mutating
(``shutil.copy2`` preserves metadata). Skips backup if it already
exists AND the source mtime is older — avoids clobbering a fresh
backup with stale data.

Also bumps ``SCHEMA_VERSION`` from 1 to 2 in
``src/mesh/adapters/taskdog.py``. If the constant is already at 2
(or absent), the script reports and exits cleanly.

Usage::

    python scripts/migrate_taskdog_schema_v2.py
    python scripts/migrate_taskdog_schema_v2.py --db /path/to/tasks.db
    python scripts/migrate_taskdog_schema_v2.py --dry-run

Reference: M163 — taskdog schema v2 (canonical 14-column slice).
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

# Make src/ importable so we can read the current SCHEMA_VERSION.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

# Path to the taskdog adapter — its SCHEMA_VERSION is the canonical source.
TASKDOG_ADAPTER = REPO_ROOT / "src" / "mesh" / "adapters" / "taskdog.py"
DEFAULT_DB = REPO_ROOT / "data" / "taskdog" / "tasks.db"

# Column specs: name → DDL fragment after ADD COLUMN.
COLUMN_SPECS: dict[str, str] = {
    "tags":           "TEXT NOT NULL DEFAULT '[]'",
    "deps":           "TEXT NOT NULL DEFAULT '[]'",
    "audit_log":      "TEXT NOT NULL DEFAULT '[]'",
    "started_at":     "TEXT",
    "completed_at":   "TEXT",
    "priority_label": "TEXT NOT NULL DEFAULT 'P2'",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="M163: Migrate taskdog tasks.db from schema v1 to v2.",
    )
    p.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Path to the SQLite DB (default: {DEFAULT_DB})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned SQL without executing it.",
    )
    p.add_argument(
        "--adapter",
        type=Path,
        default=TASKDOG_ADAPTER,
        help=f"Path to taskdog.py adapter (default: {TASKDOG_ADAPTER})",
    )
    return p.parse_args()


def backup_db(db_path: Path, dry_run: bool) -> Path | None:
    """Copy db_path to db_path.backup-v1 if not already fresh enough.

    Returns the backup path, or None on dry-run.
    """
    backup = db_path.with_suffix(db_path.suffix + ".backup-v1")
    if backup.exists():
        # If backup is newer than source, skip — we already have a fresh copy.
        if backup.stat().st_mtime >= db_path.stat().st_mtime:
            print(f"[skip-backup] Backup already fresh: {backup}")
            return backup
    if dry_run:
        print(f"[dry-run] Would backup {db_path} → {backup}")
        return backup
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup)
    print(f"[backup] Created {backup}")
    return backup


def migrate_db(db_path: Path, dry_run: bool) -> dict[str, str]:
    """Apply the v1 → v2 ALTERs to db_path. Returns per-column status."""
    statuses: dict[str, str] = {}
    if not db_path.exists():
        print(f"[error] DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        for col, ddl in COLUMN_SPECS.items():
            print(f"[dry-run] ALTER TABLE tasks ADD COLUMN {col} {ddl}")
        print("[dry-run] (no actual changes made)")
        return {col: "dry-run" for col in COLUMN_SPECS}

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("PRAGMA table_info(tasks)")
        existing = {row[1] for row in cur.fetchall()}

        for col, ddl in COLUMN_SPECS.items():
            if col in existing:
                statuses[col] = "skipped (already present)"
                continue
            sql = f"ALTER TABLE tasks ADD COLUMN {col} {ddl}"
            try:
                conn.execute(sql)
                statuses[col] = "added"
            except sqlite3.OperationalError as exc:
                if "duplicate column" in str(exc).lower():
                    statuses[col] = "skipped (race)"
                    continue
                raise
            # Backfill for JSON list columns — defensive against NULLs.
            if col in ("tags", "deps", "audit_log"):
                conn.execute(
                    f"UPDATE tasks SET {col}='[]' WHERE {col} IS NULL"
                )
        conn.commit()
    finally:
        conn.close()

    return statuses


def bump_schema_version(adapter_path: Path, dry_run: bool) -> str:
    """Bump SCHEMA_VERSION from 1 → 2 in taskdog.py. Idempotent."""
    if not adapter_path.exists():
        return "adapter file not found"

    text = adapter_path.read_text(encoding="utf-8")
    if "SCHEMA_VERSION = 2" in text:
        return "already at 2"
    if "SCHEMA_VERSION = 1" not in text:
        return "no SCHEMA_VERSION constant found (skipped)"

    if dry_run:
        return "would bump 1 → 2 (dry-run)"

    new_text = text.replace("SCHEMA_VERSION = 1", "SCHEMA_VERSION = 2", 1)
    adapter_path.write_text(new_text, encoding="utf-8")
    return "bumped 1 → 2"


def main() -> int:
    args = parse_args()

    print(f"M163 schema migration (v1 → v2)")
    print(f"  DB:           {args.db}")
    print(f"  Adapter:      {args.adapter}")
    print(f"  Dry-run:      {args.dry_run}")
    print()

    # 1. Backup first (before any mutation).
    backup_db(args.db, args.dry_run)

    # 2. Apply ALTERs.
    print("[migrate-db] Adding columns:")
    statuses = migrate_db(args.db, args.dry_run)
    for col in COLUMN_SPECS:
        print(f"  - {col:<14} → {statuses.get(col, 'unknown')}")

    # 3. Bump SCHEMA_VERSION.
    print()
    result = bump_schema_version(args.adapter, args.dry_run)
    print(f"[schema-version] {result}")

    print()
    print("[done] Migration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
