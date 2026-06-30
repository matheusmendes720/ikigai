"""Bidirectional sync between Obsidian vault and vibe-ops algorithmic engine.

Source: .omo/plans/vault-bidirectional-sync.md (T2/T3)
ADR-006 (period_reports schema) is referenced but this layer is
schema-agnostic — it pushes everything into planning_entities with
frontmatter entity_type as the discriminator.

Append-only safe: never deletes. Conflicts go to .sync-conflicts.md
per D3 (vault-wins for manual, code-wins for computed).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import frontmatter
import yaml

logger = logging.getLogger(__name__)


# Folders the engine scans by default. Override via sync_vault_to_code(folders=...).
DEFAULT_VAULT_FOLDERS: List[str] = [
    "2_projeto",
    "5_atomicas",
    "3_indice",
    "4_leitura",
]

# Frontmatter keys considered "manual" (vault is authoritative).
MANUAL_FIELD_PREFIXES: Set[str] = {
    "xp_", "mastery_", "subject", "learning_phase", "tech_stack",
    "milestone", "deliverable", "commercial_goal",
}

# Frontmatter keys considered "computed" (code is authoritative).
COMPUTED_FIELD_NAMES: Set[str] = {
    "policy_state", "rice_score", "priority_rank",
    "falsifiability_score", "hypothesis_verdict",
}


class BidirectionalSync:
    """Bridge between Obsidian vault (manual fields) and vibe-ops SQLite (computed fields).

    The vault holds human-curated data (xp, mastery, subjects). The SQLite
    store holds computed data (PolicyDecision, RICE, FalsifiableHypothesis).
    This class moves both directions, idempotently, with conflict detection.
    """

    def __init__(self, vault_path: Path, db_path: Path) -> None:
        self.vault_path = Path(vault_path)
        self.db_path = Path(db_path)
        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault not found: {self.vault_path}")
        if not self.db_path.exists():
            raise FileNotFoundError(f"DB not found: {self.db_path}")

        # Ensure vault_sync_state table exists.
        self._ensure_schema()
        # Enable WAL mode for concurrent read safety.
        with self._conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

    # ---------- public API ----------

    def sync_vault_to_code(
        self,
        folders: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """Ingest frontmatter from vault .md files into planning_entities.

        Returns:
            {"ingested": N, "skipped": N, "errors": N, "conflicts": N}

        Idempotent: re-running with no vault changes returns
        {"ingested": 0, "skipped": N, "errors": 0}.
        """
        folders = folders or DEFAULT_VAULT_FOLDERS
        stats = {"ingested": 0, "skipped": 0, "errors": 0, "conflicts": 0}

        for folder in folders:
            folder_path = self.vault_path / folder
            if not folder_path.exists():
                logger.warning("Vault folder missing: %s", folder_path)
                continue
            for md_file in sorted(folder_path.rglob("*.md")):
                self._ingest_one(md_file, stats)

        return stats

    def sync_code_to_vault(
        self,
        entity_types: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """Export computed fields from SQLite back to vault .md frontmatter.

        Only writes fields whose key is in COMPUTED_FIELD_NAMES (D3: code-wins
        for computed). Manual fields are never overwritten.

        Returns:
            {"exported": N, "skipped": N, "errors": N, "conflicts": N}
        """
        entity_types = entity_types or ["project", "study_project"]
        stats = {"exported": 0, "skipped": 0, "errors": 0, "conflicts": 0}

        with self._conn() as conn:
            placeholders = ",".join("?" for _ in entity_types)
            rows = conn.execute(
                f"SELECT id, entity_type, payload_json, upstream_id FROM "
                f"planning_entities WHERE entity_type IN ({placeholders})",
                entity_types,
            ).fetchall()

        for row in rows:
            entity_id, entity_type, payload_json, _upstream_id = row
            try:
                payload = json.loads(payload_json)
            except (TypeError, json.JSONDecodeError) as exc:
                logger.error("Bad payload_json for %s: %s", entity_id, exc)
                stats["errors"] += 1
                continue

            computed_fields = {
                k: v for k, v in payload.items()
                if k in COMPUTED_FIELD_NAMES
            }
            if not computed_fields:
                stats["skipped"] += 1
                continue

            # Find vault file by vault_path hint, fall back to id-based heuristic.
            vault_file = self._resolve_vault_file(entity_type, entity_id, payload)
            if vault_file is None:
                stats["skipped"] += 1
                continue

            exported = self._merge_into_frontmatter(vault_file, computed_fields)
            if exported:
                stats["exported"] += 1
            else:
                stats["skipped"] += 1

        return stats

    def resolve_conflicts(self) -> Dict[str, Any]:
        """Read .sync-conflicts.md and apply documented resolution rules.

        D3 policy:
          - vault wins for manual fields (xp, mastery, subject...)
          - code wins for computed fields (policy_state, rice_score...)
          - ambiguous field: log to conflicts file
        """
        conflicts_file = self.vault_path / ".sync-conflicts.md"
        if not conflicts_file.exists():
            return {"found": 0, "resolved": 0, "pending": 0}

        text = conflicts_file.read_text(encoding="utf-8")
        rows = self._parse_conflict_table(text)
        resolved = 0
        for row in rows:
            if row["side"] == "vault" and row["field"] in MANUAL_FIELD_PREFIXES:
                resolved += 1
            elif row["side"] == "code" and row["field"] in COMPUTED_FIELD_NAMES:
                resolved += 1
        return {"found": len(rows), "resolved": resolved, "pending": len(rows) - resolved}

    def status(self) -> Dict[str, Any]:
        """Return counts and last sync timestamps."""
        with self._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM planning_entities"
            ).fetchone()[0]
            by_type_rows = conn.execute(
                "SELECT entity_type, COUNT(*) FROM planning_entities "
                "GROUP BY entity_type"
            ).fetchall()
            last_sync = conn.execute(
                "SELECT MAX(synced_at) FROM planning_entities"
            ).fetchone()[0]
            state_rows = conn.execute(
                "SELECT vault_path, last_hash, last_synced_at "
                "FROM vault_sync_state"
            ).fetchall()

        return {
            "total_entities": total,
            "by_type": {row[0]: row[1] for row in by_type_rows},
            "last_sync_at": last_sync,
            "tracked_files": [
                {
                    "vault_path": r[0],
                    "last_hash": r[1],
                    "last_synced_at": r[2],
                }
                for r in state_rows
            ],
        }

    # ---------- internals ----------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Create vault_sync_state table if missing. planning_entities assumed pre-existing."""
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vault_sync_state (
                    vault_path TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    last_hash TEXT NOT NULL,
                    last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _ingest_one(self, md_file: Path, stats: Dict[str, int]) -> None:
        """Ingest a single vault .md file. Continues past parse errors."""
        try:
            post = frontmatter.load(str(md_file))
            metadata = dict(post.metadata or {})
        except (yaml.YAMLError, OSError) as exc:
            logger.error("Frontmatter parse failed for %s: %s", md_file, exc)
            stats["errors"] += 1
            return

        entity_type = metadata.get("entity_type")
        entity_id = metadata.get("id")
        if not entity_type or not entity_id:
            # Files without entity_type are skipped (notes, indexes).
            stats["skipped"] += 1
            return

        # Idempotency hash — same content -> same hash -> skip.
        canonical = json.dumps(metadata, sort_keys=True, default=str)
        import hashlib
        new_hash = hashlib.sha256(canonical.encode()).hexdigest()[:12]
        upstream_id = new_hash

        vault_rel = str(md_file.relative_to(self.vault_path)).replace("\\", "/")
        prev_hash = self._get_prev_hash(vault_rel)

        if prev_hash == new_hash:
            stats["skipped"] += 1
            return

        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO planning_entities
                        (id, entity_type, payload_json, upstream_id, synced_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id, entity_type) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        upstream_id = excluded.upstream_id,
                        synced_at = excluded.synced_at
                    WHERE excluded.upstream_id != planning_entities.upstream_id
                    """,
                    (
                        entity_id,
                        entity_type,
                        json.dumps(metadata, default=str),
                        upstream_id,
                        datetime.now(timezone.utc).isoformat(),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO vault_sync_state
                        (vault_path, entity_type, entity_id, last_hash, last_synced_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(vault_path) DO UPDATE SET
                        entity_type = excluded.entity_type,
                        entity_id = excluded.entity_id,
                        last_hash = excluded.last_hash,
                        last_synced_at = excluded.last_synced_at
                    """,
                    (vault_rel, entity_type, entity_id, new_hash, datetime.now(timezone.utc).isoformat()),
                )
            stats["ingested"] += 1
        except sqlite3.Error as exc:
            logger.error("DB error ingesting %s: %s", md_file, exc)
            stats["errors"] += 1

    def _get_prev_hash(self, vault_rel: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT last_hash FROM vault_sync_state WHERE vault_path = ?",
                (vault_rel,),
            ).fetchone()
        return row[0] if row else None

    def _resolve_vault_file(
        self, entity_type: str, entity_id: str, payload: Dict[str, Any]
    ) -> Optional[Path]:
        """Find the .md file that owns this entity."""
        hint = payload.get("vault_path")
        if hint:
            candidate = self.vault_path / hint
            if candidate.exists():
                return candidate
        # Fallback: rglob for a file whose frontmatter id matches.
        for md_file in self.vault_path.rglob("*.md"):
            try:
                post = frontmatter.load(str(md_file))
            except (yaml.YAMLError, OSError):
                continue
            md_id = (post.metadata or {}).get("id")
            if md_id == entity_id:
                return md_file
        return None

    def _merge_into_frontmatter(
        self, md_file: Path, computed_fields: Dict[str, Any]
    ) -> bool:
        """Merge computed fields into existing frontmatter. Returns True if written."""
        try:
            post = frontmatter.load(str(md_file))
        except (yaml.YAMLError, OSError) as exc:
            logger.error("Could not load %s: %s", md_file, exc)
            return False
        existing = dict(post.metadata or {})
        # Conflict guard: if a vault field already carries one of these keys
        # but the existing value differs AND the key is in MANUAL_FIELD_PREFIXES,
        # we skip and record a conflict.
        conflict = False
        for key, val in computed_fields.items():
            prev = existing.get(key)
            if prev is not None and prev != val and key in MANUAL_FIELD_PREFIXES:
                self._record_conflict(md_file, key, prev, val)
                conflict = True
            else:
                existing[key] = val
        if conflict:
            return False

        new_content = frontmatter.dumps(frontmatter.Post(existing, post.content))
        # Atomic write: write to tmp, rename.
        tmp_path = md_file.with_suffix(md_file.suffix + ".tmp")
        tmp_path.write_text(new_content, encoding="utf-8")
        tmp_path.replace(md_file)
        return True

    def _record_conflict(
        self,
        md_file: Path,
        field: str,
        vault_value: Any,
        code_value: Any,
    ) -> None:
        """Append a row to .sync-conflicts.md (append-only invariant)."""
        conflicts_file = self.vault_path / ".sync-conflicts.md"
        if not conflicts_file.exists():
            conflicts_file.write_text(
                "| timestamp | file | field | vault | code | resolved | resolution |\n"
                "|---|---|---|---|---|---|---|\n",
                encoding="utf-8",
            )
        ts = datetime.now(timezone.utc).isoformat()
        row = (
            f"| {ts} | {md_file.name} | {field} | "
            f"{vault_value!r} | {code_value!r} | false | pending |\n"
        )
        with conflicts_file.open("a", encoding="utf-8") as f:
            f.write(row)

    def _parse_conflict_table(self, text: str) -> List[Dict[str, str]]:
        """Parse the markdown conflict log into structured rows."""
        rows: List[Dict[str, str]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 5 or parts[0] == "timestamp":
                continue
            rows.append(
                {
                    "timestamp": parts[0],
                    "file": parts[1],
                    "field": parts[2],
                    "vault": parts[3],
                    "code": parts[4],
                    "side": "vault" if "vault" in parts[3].lower() else "code",
                }
            )
        return rows