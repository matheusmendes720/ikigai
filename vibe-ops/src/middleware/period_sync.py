"""PeriodReports-specific sync layer.

Source: .omo/plans/period-reports-sync.md T3
Linked: vault-bidirectional-sync plan (T2 will call this from BidirectionalSync.sync_vault_to_code)

Differences from generic SyncEngine (sync_engine.py):
- Natural key: (sonho_id, period, date_start) — NOT upstream_id sha256
- Conflict policy: vault-wins for ALL fields (no computed fields in period_reports)
- Hierarchy validation: parent_period FK must resolve
- Idempotency: vault_hash (sha256 canonical JSON, 16 chars)
- Multi-pass orphan recovery built into sync_vault_to_db
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from models.period_report import PeriodReport, PeriodReportParser, PeriodSyncStats

__all__ = ["PeriodReportSync"]


# Migration 004 SQL inline (loaded from migrations dir at runtime)
_MIGRATION_PATH = Path(__file__).resolve().parents[2] / "migrations" / "004_period_reports.sql"


class PeriodReportSync:
    """Sync period_reports from vault to vibe_ops.db.
    
    Multi-pass orphan recovery: first run ingests roots (sonho), 
    subsequent runs resolve children whose parent_period now exists.
    """
    
    def __init__(
        self,
        vault_path: Path,
        db_path: Path,
        template_folder: str = "_templates_periodos",
    ):
        self.vault_path = Path(vault_path)
        self.db_path = Path(db_path)
        self.template_folder = template_folder
        self._ensure_migration()
    
    def _ensure_migration(self) -> None:
        """Apply migration 004 idempotently (CREATE TABLE IF NOT EXISTS)."""
        if not _MIGRATION_PATH.exists():
            # Fallback: inline minimal DDL (allows sync to work even without migration file)
            ddl = """
            CREATE TABLE IF NOT EXISTS period_reports (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL DEFAULT 'period_report',
                period TEXT NOT NULL CHECK (period IN ('daily','weekly','onda','quarterly','sonho')),
                date_start DATE NOT NULL,
                date_end DATE NOT NULL,
                verdict TEXT NOT NULL,
                verdict_score REAL NOT NULL CHECK (verdict_score >= 0.0 AND verdict_score <= 1.0),
                template_version TEXT DEFAULT '1.0',
                ikigai_cluster TEXT DEFAULT 'plan',
                sonho_id TEXT,
                ikigai_vector TEXT CHECK (ikigai_vector IS NULL OR ikigai_vector IN ('passion','skill','market','revenue')),
                xp_gained INTEGER,
                mastery_delta TEXT,
                policy_recommendation TEXT CHECK (policy_recommendation IS NULL OR policy_recommendation IN ('push','maintain','reduce','recover')),
                parent_period TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','closed')),
                tags TEXT,
                vault_path TEXT NOT NULL,
                vault_hash TEXT NOT NULL,
                last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (date_end >= date_start)
            );
            """
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(ddl)
                conn.commit()
            return
        
        sql = _MIGRATION_PATH.read_text(encoding="utf-8")
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(sql)
            conn.commit()
    
    def sync_vault_to_db(self) -> PeriodSyncStats:
        """Scan vault/_templates_periodos/*.md, upsert into period_reports table.
        
        Multi-pass: orphans (parent_period FK unresolved) are skipped with stats.orphans++.
        Re-run until orphans=0.
        
        Returns PeriodSyncStats with counts.
        """
        # PeriodSyncStats is frozen=True, so accumulate in locals and construct once at end.
        ingested = 0
        skipped = 0
        updated = 0
        errors = 0
        orphans = 0
        file_errors: list[dict[str, str]] = []

        folder = self.vault_path / self.template_folder
        if not folder.is_dir():
            errors += 1
            file_errors.append({
                "path": str(folder),
                "error": f"folder not found: {folder}",
            })
            return PeriodSyncStats(
                ingested=ingested, skipped=skipped, updated=updated,
                errors=errors, orphans=orphans, file_errors=file_errors,
            )
        
        for md_file in sorted(folder.glob("*.md")):
            try:
                report = PeriodReportParser.parse_file(str(md_file))
                if report is None:
                    continue  # Not a period_report (e.g., README.md)
                
                # Idempotency check via vault_hash OR id
                if self._fetch_existing(report.vault_hash, report.id):
                    skipped += 1
                    continue
                
                # Hierarchy validation: parent_period must resolve
                if report.parent_period and not self._exists(report.parent_period):
                    orphans += 1
                    file_errors.append({
                        "path": str(md_file),
                        "error": f"parent_period {report.parent_period!r} not found in DB",
                    })
                    continue
                
                # Upsert
                is_new = not self._exists(report.id)
                self._upsert(report)
                if is_new:
                    ingested += 1
                else:
                    updated += 1
            except Exception as exc:
                errors += 1
                file_errors.append({
                    "path": str(md_file),
                    "error": str(exc),
                })
        
        return PeriodSyncStats(
            ingested=ingested, skipped=skipped, updated=updated,
            errors=errors, orphans=orphans, file_errors=file_errors,
        )
    
    def _fetch_existing(self, vault_hash: str, report_id: str) -> bool:
        """Returns True if a period_report with the same vault_hash OR id exists."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM period_reports WHERE id = ? OR vault_hash = ? LIMIT 1",
                (report_id, vault_hash),
            ).fetchone()
            return row is not None
    
    def _exists(self, report_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM period_reports WHERE id = ? LIMIT 1",
                (report_id,),
            ).fetchone()
            return row is not None
    
    def _upsert(self, report: PeriodReport) -> None:
        """Upsert into period_reports table."""
        tags_json = json.dumps(report.tags)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO period_reports (
                    id, entity_type, period, date_start, date_end,
                    verdict, verdict_score, template_version, ikigai_cluster,
                    sonho_id, ikigai_vector, xp_gained, mastery_delta,
                    policy_recommendation, parent_period, status, tags,
                    vault_path, vault_hash, last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    period = excluded.period,
                    date_start = excluded.date_start,
                    date_end = excluded.date_end,
                    verdict = excluded.verdict,
                    verdict_score = excluded.verdict_score,
                    ikigai_vector = excluded.ikigai_vector,
                    policy_recommendation = excluded.policy_recommendation,
                    xp_gained = excluded.xp_gained,
                    mastery_delta = excluded.mastery_delta,
                    status = excluded.status,
                    tags = excluded.tags,
                    vault_path = excluded.vault_path,
                    vault_hash = excluded.vault_hash,
                    last_synced_at = CURRENT_TIMESTAMP
                """,
                (
                    report.id, report.entity_type, report.period,
                    report.date_start.isoformat(), report.date_end.isoformat(),
                    report.verdict, report.verdict_score,
                    report.template_version, report.ikigai_cluster,
                    report.sonho_id, report.ikigai_vector,
                    report.xp_gained, report.mastery_delta,
                    report.policy_recommendation, report.parent_period,
                    report.status, tags_json,
                    report.vault_path, report.vault_hash,
                ),
            )
            conn.commit()
    
    def get_period_hierarchy(self, sonho_id: str) -> dict[str, Any]:
        """Return nested tree of all reports under a sonho."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, period, date_start, date_end, parent_period,
                       sonho_id, verdict, verdict_score, policy_recommendation,
                       vault_path
                FROM period_reports
                WHERE sonho_id = ? OR id = ?
                ORDER BY date_start ASC
                """,
                (sonho_id, sonho_id),
            ).fetchall()
        
        nodes = {row["id"]: dict(row) for row in rows}
        tree = []
        for node in nodes.values():
            if node["parent_period"] is None:
                tree.append(self._build_subtree(node, nodes))
        return {"sonho_id": sonho_id, "tree": tree, "count": len(nodes)}
    
    def _build_subtree(self, node: dict[str, Any], nodes: dict[str, Any]) -> dict[str, Any]:
        """Recursively build child tree."""
        children = [
            self._build_subtree(n, nodes)
            for n in nodes.values()
            if n["parent_period"] == node["id"]
        ]
        return {**node, "children": children}
    
    def sync_db_to_vault(self) -> PeriodSyncStats:
        """Reverse direction (code → vault) — no-op for period_reports in v1.1.
        
        Period reports are user-authored; no computed fields to export.
        If PolicyEngine later emits period_reports, this method would handle that.
        """
        return PeriodSyncStats()  # all zeros
