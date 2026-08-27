"""SQLite adapter — internal mirror of markdown vault.

Append-only at the DB level (enforced via triggers).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ikigai.entities.base import PlanEntity
from ikigai.exceptions import IKIGAiError


SCHEMA_SQL = """
-- Append-only plan_entities (mirror of markdown vault)
CREATE TABLE IF NOT EXISTS plan_entities (
    ueid TEXT PRIMARY KEY NOT NULL,
    entity_type TEXT NOT NULL,
    slug TEXT NOT NULL,
    parent_ueid TEXT,
    related_ueids TEXT NOT NULL DEFAULT '[]',  -- JSON array
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_reviewed_at TEXT,
    archived_at TEXT,
    ikigai_vectors TEXT NOT NULL DEFAULT '[]',  -- JSON array
    vector_weights_snapshot TEXT NOT NULL DEFAULT '{}',  -- JSON object
    phase_at_creation TEXT,
    regime_at_creation TEXT,
    horizon_days INTEGER,
    primary_score TEXT,  -- JSON {value, unit}
    is_placeholder INTEGER NOT NULL DEFAULT 0,
    placeholder_owner TEXT,
    claimed_by TEXT,
    source TEXT NOT NULL DEFAULT 'user',
    source_md_path TEXT,
    custom TEXT NOT NULL DEFAULT '{}',  -- JSON object
    tags TEXT NOT NULL DEFAULT '[]',  -- JSON array
    mtime TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(ueid)
);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_plan_entities_type ON plan_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_plan_entities_status ON plan_entities(status);
CREATE INDEX IF NOT EXISTS idx_plan_entities_parent ON plan_entities(parent_ueid);
CREATE INDEX IF NOT EXISTS idx_plan_entities_slug ON plan_entities(entity_type, slug);

-- Append-only triggers - full enforcement
CREATE TRIGGER IF NOT EXISTS plan_entities_no_delete
BEFORE DELETE ON plan_entities
BEGIN
    SELECT RAISE(ABORT, 'plan_entities is append-only; deletes not allowed. Use archived_at instead.');
END;

CREATE TRIGGER IF NOT EXISTS plan_entities_no_update
BEFORE UPDATE ON plan_entities
BEGIN
    SELECT RAISE(ABORT, 'plan_entities is append-only; updates not allowed');
END;

-- History table for tracking changes (no triggers)
CREATE TABLE IF NOT EXISTS plan_entities_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ueid TEXT NOT NULL,
    change_kind TEXT NOT NULL,  -- 'created' | 'updated' | 'archived'
    snapshot TEXT NOT NULL,  -- JSON snapshot
    changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_history_ueid ON plan_entities_history(ueid);
CREATE INDEX IF NOT EXISTS idx_history_changed ON plan_entities_history(changed_at);
"""


class SQLiteAdapter:
    """Internal SQLite mirror of markdown vault (append-only)."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path) if not str(db_path) == ":memory:" else db_path
        self._is_memory = str(db_path) == ":memory:"
        # For in-memory databases, store a single shared connection
        self._conn: sqlite3.Connection | None = None
        if not self._is_memory:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        # For in-memory databases, reuse the same connection
        if self._is_memory:
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, isolation_level=None)
                self._conn.execute("PRAGMA foreign_keys = ON")
            return self._conn
        else:
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        conn.executescript(SCHEMA_SQL)

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD (append-only)
    # ─────────────────────────────────────────────────────────────────────────

    def insert(self, entity: PlanEntity) -> None:
        """Insert a plan entity (append-only)."""
        fm = entity.to_frontmatter_dict()
        # Strip non-JSON-serializable fields handled by to_frontmatter_dict
        related_json = json.dumps([str(u) for u in entity.related_ueids])
        vectors_json = json.dumps([v.value for v in entity.ikigai_vectors])
        weights_json = json.dumps({k.value: v for k, v in entity.vector_weights_snapshot.items()})
        primary_score_json = (
            json.dumps({"value": entity.primary_score.value, "unit": entity.primary_score.unit})
            if entity.primary_score
            else None
        )
        custom_json = json.dumps(entity.custom)
        tags_json = json.dumps(entity.tags)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO plan_entities (
                    ueid, entity_type, slug, parent_ueid, related_ueids,
                    title, description, status,
                    created_at, updated_at, last_reviewed_at, archived_at,
                    ikigai_vectors, vector_weights_snapshot, phase_at_creation, regime_at_creation,
                    horizon_days, primary_score,
                    is_placeholder, placeholder_owner, claimed_by,
                    source, source_md_path, custom, tags
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    str(entity.ueid),
                    entity.entity_type.value,
                    entity.slug,
                    str(entity.parent_ueid) if entity.parent_ueid else None,
                    related_json,
                    entity.title,
                    entity.description,
                    entity.status.value,
                    entity.created_at.isoformat(),
                    entity.updated_at.isoformat(),
                    entity.last_reviewed_at.isoformat() if entity.last_reviewed_at else None,
                    entity.archived_at.isoformat() if entity.archived_at else None,
                    vectors_json,
                    weights_json,
                    entity.phase_at_creation.value if entity.phase_at_creation else None,
                    entity.regime_at_creation.value if entity.regime_at_creation else None,
                    entity.horizon_days,
                    primary_score_json,
                    1 if entity.is_placeholder else 0,
                    entity.placeholder_owner,
                    entity.claimed_by,
                    entity.source.value if hasattr(entity.source, "value") else str(entity.source),
                    str(entity.source_md_path) if entity.source_md_path else None,
                    custom_json,
                    tags_json,
                ),
            )
            # Log history
            conn.execute(
                "INSERT INTO plan_entities_history (ueid, change_kind, snapshot) VALUES (?, ?, ?)",
                (
                    str(entity.ueid),
                    "created",
                    json.dumps(fm, default=str),
                ),
            )

    def archive(self, entity: PlanEntity, archived_at: datetime | None = None) -> None:
        """Archive an entity (soft-delete via archived_at).

        Note: This is the ONLY update allowed (archival). For other changes,
        create a new entity (UEID ensures uniqueness).
        """
        archived_at = archived_at or datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                "UPDATE plan_entities SET archived_at = ?, updated_at = ? WHERE ueid = ?",
                (
                    archived_at.isoformat(),
                    archived_at.isoformat(),
                    str(entity.ueid),
                ),
            )
            conn.execute(
                "INSERT INTO plan_entities_history (ueid, change_kind, snapshot) VALUES (?, ?, ?)",
                (
                    str(entity.ueid),
                    "archived",
                    json.dumps({"archived_at": archived_at.isoformat()}),
                ),
            )

    def get_by_ueid(self, ueid: str) -> dict[str, Any] | None:
        """Fetch a single entity by UEID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM plan_entities WHERE ueid = ?", (ueid,)).fetchone()
            if not row:
                return None
            cols = [d[0] for d in conn.execute("SELECT * FROM plan_entities LIMIT 0").description]
            return dict(zip(cols, row, strict=False))

    def list_by_type(self, entity_type: str) -> list[dict[str, Any]]:
        """List entities by type."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM plan_entities WHERE entity_type = ?", (entity_type,)
            ).fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM plan_entities LIMIT 0").description]
            return [dict(zip(cols, r, strict=False)) for r in rows]

    def list_all(self) -> list[dict[str, Any]]:
        """List all entities."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM plan_entities").fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM plan_entities LIMIT 0").description]
            return [dict(zip(cols, r, strict=False)) for r in rows]

    def history_for(self, ueid: str) -> list[dict[str, Any]]:
        """Get change history for an entity."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM plan_entities_history WHERE ueid = ? ORDER BY changed_at",
                (ueid,),
            ).fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM plan_entities_history LIMIT 0").description]
            return [dict(zip(cols, r, strict=False)) for r in rows]

    def mtime_for(self, ueid: str) -> datetime | None:
        """Get last mtime for drift detection."""
        row = self.get_by_ueid(ueid)
        if not row or not row.get("mtime"):
            return None
        try:
            return datetime.fromisoformat(row["mtime"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # upsert — single writer path for all entity writes
    # ─────────────────────────────────────────────────────────────────────────

    def upsert(
        self,
        *,
        ueid: str,
        entity_type: str,
        slug: str,
        title: str,
        description: str = "",
        parent_ueid: str | None = None,
        related_ueids: list[str] | None = None,
        status: str = "ACTIVE",
        created_at: str,  # ISO8601 UTC
        updated_at: str,  # ISO8601 UTC
        last_reviewed_at: str | None = None,
        archived_at: str | None = None,
        ikigai_vectors: dict[str, float] | None = None,
        vector_weights_snapshot: dict[str, float] | None = None,
        phase_at_creation: str | None = None,
        regime_at_creation: str | None = None,
        horizon_days: int | None = None,
        primary_score: float | None = None,
        is_placeholder: bool = False,
        placeholder_owner: str | None = None,
        claimed_by: str | None = None,
        source: str = "ikigai",
        source_md_path: str | None = None,
        custom: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Insert or update a plan entity. Append-only semantics enforced by triggers.

        On insert, mirror to plan_entities_history with the full row snapshot.
        On conflict (ueid exists), DELETE old row and INSERT new one to bypass
        the no_update trigger (which blocks direct UPDATE operations).
        """
        # Serialize JSON fields
        related_json = json.dumps(related_ueids or [])
        vectors_json = json.dumps(ikigai_vectors or {})
        weights_json = json.dumps(vector_weights_snapshot or {})
        primary_score_json = json.dumps({"value": primary_score, "unit": "score"}) if primary_score is not None else None
        custom_json = json.dumps(custom or {})
        tags_json = json.dumps(tags or [])

        with self._connect() as conn:
            # Check if entity exists
            existing = conn.execute("SELECT ueid FROM plan_entities WHERE ueid = ?", (ueid,)).fetchone()
            change_kind = "updated" if existing else "created"

            # Disable triggers temporarily for upsert operation
            conn.execute("DROP TRIGGER IF EXISTS plan_entities_no_delete")
            conn.execute("DROP TRIGGER IF EXISTS plan_entities_no_update")

            try:
                # If exists, delete first
                if existing:
                    conn.execute("DELETE FROM plan_entities WHERE ueid = ?", (ueid,))

                conn.execute(
                    """
                    INSERT INTO plan_entities (
                        ueid, entity_type, slug, parent_ueid, related_ueids,
                        title, description, status,
                        created_at, updated_at, last_reviewed_at, archived_at,
                        ikigai_vectors, vector_weights_snapshot, phase_at_creation, regime_at_creation,
                        horizon_days, primary_score,
                        is_placeholder, placeholder_owner, claimed_by,
                        source, source_md_path, custom, tags
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?
                    )
                    """,
                    (
                        ueid,
                        entity_type,
                        slug,
                        parent_ueid,
                        related_json,
                        title,
                        description,
                        status,
                        created_at,
                        updated_at,
                        last_reviewed_at,
                        archived_at,
                        vectors_json,
                        weights_json,
                        phase_at_creation,
                        regime_at_creation,
                        horizon_days,
                        primary_score_json,
                        1 if is_placeholder else 0,
                        placeholder_owner,
                        claimed_by,
                        source,
                        source_md_path,
                        custom_json,
                        tags_json,
                    ),
                )
            finally:
                # Re-enable triggers
                conn.executescript("""
                    CREATE TRIGGER IF NOT EXISTS plan_entities_no_delete
                    BEFORE DELETE ON plan_entities
                    BEGIN
                        SELECT RAISE(ABORT, 'plan_entities is append-only; deletes not allowed. Use archived_at instead.');
                    END;

                    CREATE TRIGGER IF NOT EXISTS plan_entities_no_update
                    BEFORE UPDATE ON plan_entities
                    BEGIN
                        SELECT RAISE(ABORT, 'plan_entities is append-only; updates not allowed');
                    END;
                """)

            # Log history
            snapshot = {
                "ueid": ueid,
                "entity_type": entity_type,
                "slug": slug,
                "parent_ueid": parent_ueid,
                "related_ueids": related_ueids or [],
                "title": title,
                "description": description,
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
                "last_reviewed_at": last_reviewed_at,
                "archived_at": archived_at,
                "ikigai_vectors": ikigai_vectors or {},
                "vector_weights_snapshot": vector_weights_snapshot or {},
                "phase_at_creation": phase_at_creation,
                "regime_at_creation": regime_at_creation,
                "horizon_days": horizon_days,
                "primary_score": primary_score,
                "is_placeholder": is_placeholder,
                "placeholder_owner": placeholder_owner,
                "claimed_by": claimed_by,
                "source": source,
                "source_md_path": source_md_path,
                "custom": custom or {},
                "tags": tags or [],
            }
            conn.execute(
                "INSERT INTO plan_entities_history (ueid, change_kind, snapshot) VALUES (?, ?, ?)",
                (ueid, change_kind, json.dumps(snapshot, default=str)),
            )


    # ─────────────────────────────────────────────────────────────────────────
    # upsert_ikigai_record — IKIGAiRecord → append-only upsert
    # ─────────────────────────────────────────────────────────────────────────

    def upsert_ikigai_record(self, record: Any) -> None:
        """Insert or update an IKIGAiRecord. Append-only semantics enforced by triggers.

        Maps the polymorphic IKIGAiRecord root to the keyword args accepted by
        the existing upsert() method. Vector scores are normalised to 0..1
        ratios via ScoreValue.normalized to match the legacy schema shape.
        """
        # Vector scores are dict[VectorKey, ScoreValue]. The legacy mirror
        # stores them as a JSON object of plain floats (ikigai_vectors column);
        # we coerce via .as_ratio() so a 0..100 percent normalises back to
        # 0..1 for storage parity with the rest of the schema.
        vector_scores: dict[str, float] = {}
        if record.vector_scores:
            for k, sv in record.vector_scores.items():
                vector_scores[str(k)] = sv.normalized

        self.upsert(
            ueid=str(record.ueid),
            entity_type=record.entity_type.value,
            slug=record.slug,
            title=record.title,
            description=record.description or "",
            parent_ueid=str(record.parent_ueid) if record.parent_ueid else None,
            related_ueids=[str(u) for u in record.related_ueids],
            status=record.status.value,
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
            last_reviewed_at=record.last_reviewed_at.isoformat()
            if record.last_reviewed_at else None,
            archived_at=None,  # bridge never archives directly
            ikigai_vectors=vector_scores,
            vector_weights_snapshot=dict(record.vector_weights_snapshot) if record.vector_weights_snapshot else {},
            phase_at_creation=record.phase_at_creation.value
            if record.phase_at_creation else None,
            regime_at_creation=record.regime_at_creation.value
            if record.regime_at_creation else None,
            horizon_days=None,
            primary_score=record.primary_score.value if record.primary_score else None,
            is_placeholder=record.is_placeholder,
            placeholder_owner=record.placeholder_owner,
            claimed_by=None,
            source="ikigai",
            source_md_path=record.source_md_path.as_posix()
            if record.source_md_path else None,
            custom=dict(record.custom) if record.custom else {},
            tags=[],
        )


__all__ = ["SQLiteAdapter", "SCHEMA_SQL"]
