"""BYD + Salvador outreach tracker init script — D4 (sqlite3 stdlib only).

Usage:
    python byd-tracker-init.py

Output: byd-tracker.db (relative to current dir)

Anti-bot note: this is local DB, no network calls. Anti-bot is enforced
at the application layer (LinkedIn/email), not here.

YAGNI: no ORM, no migration framework — plain sqlite3 + manual SQL.
Schema in byd-tracker-schema.sql.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent / "byd-tracker-schema.sql"
DB_FILE = Path(__file__).parent / "byd-tracker.db"


def init_db(db_path: Path = DB_FILE, schema_path: Path = SCHEMA_FILE) -> None:
    """Create DB and apply schema (idempotent)."""
    schema_sql = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print(f"DB initialized: {db_path}")
        # Verify tables exist
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        print(f"Tables created: {tables}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()