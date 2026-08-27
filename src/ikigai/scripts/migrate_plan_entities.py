#!/usr/bin/env python3
"""Migrate plan_entities.db from 11-col runtime schema to 24-col canonical schema."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def get_db_path() -> Path:
    """Get the plan_entities.db path (default: ~/.ikigai/plan_entities.db)."""
    return Path.home() / ".ikigai" / "plan_entities.db"


def detect_schema_cols(conn: sqlite3.Connection) -> int:
    """Detect number of columns in plan_entities table."""
    try:
        cols = conn.execute("PRAGMA table_info(plan_entities)").fetchall()
        return len(cols)
    except sqlite3.OperationalError:
        return 0


def migrate(db_path: Path) -> int:
    """Migrate an 11-col plan_entities.db to 24-col canonical schema.

    Returns number of rows migrated.
    """
    conn = sqlite3.connect(str(db_path))
    current_cols = detect_schema_cols(conn)

    if current_cols >= 24:
        print(f"Schema already has {current_cols} columns — no migration needed.")
        conn.close()
        return 0

    print(f"Detected {current_cols} columns — migrating to 24-col schema...")

    # Get existing data
    old_rows = conn.execute("SELECT * FROM plan_entities").fetchall()
    row_count = len(old_rows)
    print(f"Found {row_count} rows to migrate.")

    # Get old column names
    old_cols = [c[1] for c in conn.execute("PRAGMA table_info(plan_entities)").fetchall()]

    # New columns to add
    new_columns = [
        ("ueid", "TEXT"),
        ("entity_type", "TEXT"),
        ("slug", "TEXT"),
        ("parent_ueid", "TEXT"),
        ("related_ueids", "TEXT DEFAULT '[]'"),
        ("title", "TEXT"),
        ("description", "TEXT"),
        ("status", "TEXT DEFAULT 'ACTIVE'"),
        ("updated_at", "TEXT"),
        ("last_reviewed_at", "TEXT"),
        ("archived_at", "TEXT"),
        ("ikigai_vectors", "TEXT DEFAULT '{}'"),
        ("vector_weights_snapshot", "TEXT DEFAULT '{}'"),
        ("phase_at_creation", "TEXT"),
        ("regime_at_creation", "TEXT"),
        ("horizon_days", "INTEGER"),
        ("primary_score", "TEXT"),
        ("is_placeholder", "INTEGER DEFAULT 0"),
        ("placeholder_owner", "TEXT"),
        ("claimed_by", "TEXT"),
        ("source", "TEXT DEFAULT 'ikigai'"),
        ("source_md_path", "TEXT"),
        ("custom", "TEXT DEFAULT '{}'"),
        ("tags", "TEXT DEFAULT '[]'"),
    ]

    # Add new columns
    for col_name, col_def in new_columns:
        try:
            conn.execute(f"ALTER TABLE plan_entities ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Recreate table with new schema and migrate data
    conn.execute("DROP TABLE IF EXISTS plan_entities_new")

    # Build new table schema (canonical 24-col + mtime)
    conn.execute("""
        CREATE TABLE plan_entities_new (
            ueid TEXT PRIMARY KEY NOT NULL,
            entity_type TEXT NOT NULL,
            slug TEXT NOT NULL,
            parent_ueid TEXT,
            related_ueids TEXT NOT NULL DEFAULT '[]',
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_reviewed_at TEXT,
            archived_at TEXT,
            ikigai_vectors TEXT NOT NULL DEFAULT '[]',
            vector_weights_snapshot TEXT NOT NULL DEFAULT '{}',
            phase_at_creation TEXT,
            regime_at_creation TEXT,
            horizon_days INTEGER,
            primary_score TEXT,
            is_placeholder INTEGER NOT NULL DEFAULT 0,
            placeholder_owner TEXT,
            claimed_by TEXT,
            source TEXT NOT NULL DEFAULT 'user',
            source_md_path TEXT,
            custom TEXT NOT NULL DEFAULT '{}',
            tags TEXT NOT NULL DEFAULT '[]',
            mtime TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            UNIQUE(ueid)
        )
    """)

    # Migrate old data to new schema
    for row in old_rows:
        if len(old_cols) >= 11:
            # Old 11-col schema: cycle_id, regime, q_he, passion, skill, market, revenue, course, meta_vector, corrections, created_at
            cycle_id = row[0]
            created_at = row[10] if len(row) > 10 else ""

            # Map to new schema
            conn.execute("""
                INSERT INTO plan_entities_new (
                    ueid, entity_type, slug, title, status,
                    created_at, updated_at, ikigai_vectors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"cycle:{cycle_id}",
                "cycle",
                cycle_id,
                f"Cycle {cycle_id}",
                "ACTIVE",
                created_at,
                created_at,
                "{}",
            ))

    # Replace old table with new
    conn.execute("DROP TABLE plan_entities")
    conn.execute("ALTER TABLE plan_entities_new RENAME TO plan_entities")

    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_entities_type ON plan_entities(entity_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_entities_status ON plan_entities(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_entities_parent ON plan_entities(parent_ueid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_entities_slug ON plan_entities(entity_type, slug)")

    # Create history table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plan_entities_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT NOT NULL,
            change_kind TEXT NOT NULL,
            snapshot TEXT NOT NULL,
            changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_ueid ON plan_entities_history(ueid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_changed ON plan_entities_history(changed_at)")

    conn.commit()
    conn.close()

    print(f"Migration complete: {row_count} rows migrated to 24-col schema.")
    return row_count


def main() -> int:
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Migrate plan_entities.db to canonical 24-col schema")
    parser.add_argument("--db-path", type=Path, help="Path to plan_entities.db (default: ~/.ikigai/plan_entities.db)")
    args = parser.parse_args()

    db_path = args.db_path or get_db_path()

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    print(f"Checking {db_path}...")
    migrate(db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
