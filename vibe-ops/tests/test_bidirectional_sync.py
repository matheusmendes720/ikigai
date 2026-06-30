"""Tests for BidirectionalSync.sync_vault_to_code() — T2.

Verifies ingestion, idempotency, error tolerance, and upstream_id stability.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from middleware.bidirectional_sync import BidirectionalSync  # noqa: E402


def _write_md(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _make_db_with_planning_table(db_path: Path) -> None:
    """Create a minimal planning_entities table matching the live schema."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS planning_entities (
                id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                upstream_id TEXT NOT NULL,
                synced_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL,
                PRIMARY KEY (id, entity_type)
            )
            """
        )
        conn.commit()


@pytest.fixture
def workdir() -> Iterator[Path]:
    tmp = Path(tempfile.mkdtemp(prefix="vault_sync_test_"))
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sync_pair(workdir: Path) -> tuple[BidirectionalSync, Path, Path]:
    vault = workdir / "vault"
    db = workdir / "vibe_ops.db"
    vault.mkdir(parents=True, exist_ok=True)
    _make_db_with_planning_table(db)
    sync = BidirectionalSync(vault, db)
    return sync, vault, db


class TestSyncVaultToCodeHappyPath:
    """Ingestion works on a clean fixture vault."""

    def test_ingests_five_notes(self, sync_pair):
        sync, vault, _db = sync_pair
        for i in range(5):
            _write_md(
                vault / "2_projeto" / f"proj_t_{i}.md",
                (
                    "---\n"
                    f"entity_type: project\n"
                    f"id: proj_t_{i}\n"
                    f"title: Project {i}\n"
                    "status: active\n"
                    "revenue_impact: HIGH\n"
                    "---\n\n"
                    f"Body {i}\n"
                ),
            )
        result = sync.sync_vault_to_code()
        assert result == {"ingested": 5, "skipped": 0, "errors": 0, "conflicts": 0}

    def test_idempotent_second_call(self, sync_pair):
        sync, vault, _db = sync_pair
        for i in range(5):
            _write_md(
                vault / "2_projeto" / f"proj_i_{i}.md",
                (
                    "---\n"
                    f"entity_type: project\n"
                    f"id: proj_i_{i}\n"
                    f"title: Idem {i}\n"
                    "status: active\n"
                    "revenue_impact: HIGH\n"
                    "---\n"
                ),
            )
        first = sync.sync_vault_to_code()
        second = sync.sync_vault_to_code()
        assert first["ingested"] == 5
        assert second == {"ingested": 0, "skipped": 5, "errors": 0, "conflicts": 0}

    def test_planning_entities_has_five_rows(self, sync_pair):
        sync, vault, db = sync_pair
        for i in range(5):
            _write_md(
                vault / "2_projeto" / f"proj_r_{i}.md",
                (
                    "---\n"
                    f"entity_type: project\n"
                    f"id: proj_r_{i}\n"
                    f"title: Row {i}\n"
                    "status: active\n"
                    "revenue_impact: HIGH\n"
                    "---\n"
                ),
            )
        sync.sync_vault_to_code()
        with sqlite3.connect(str(db)) as conn:
            rows = conn.execute(
                "SELECT id, entity_type, upstream_id FROM planning_entities"
            ).fetchall()
        assert len(rows) == 5
        # All rows have a 12-char upstream_id hash.
        for _id, _etype, upstream_id in rows:
            assert isinstance(upstream_id, str)
            assert len(upstream_id) == 12

    def test_payload_json_round_trips(self, sync_pair):
        sync, vault, db = sync_pair
        _write_md(
            vault / "2_projeto" / "proj_pj.md",
            (
                "---\n"
                "entity_type: project\n"
                "id: proj_pj\n"
                "title: Payload Round Trip\n"
                "status: active\n"
                "revenue_impact: HIGH\n"
                "xp_points: 150\n"
                "mastery_level: advanced\n"
                "tech_stack:\n  - Python\n  - FastAPI\n"
                "---\n"
            ),
        )
        sync.sync_vault_to_code()
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT payload_json FROM planning_entities WHERE id = ?",
                ("proj_pj",),
            ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        assert payload["xp_points"] == 150
        assert payload["mastery_level"] == "advanced"
        assert payload["tech_stack"] == ["Python", "FastAPI"]


class TestSyncVaultToCodeErrorTolerance:
    """Bad files do not abort the whole run."""

    def test_invalid_yaml_does_not_abort(self, sync_pair):
        sync, vault, _db = sync_pair
        # Write 4 good notes + 1 bad.
        for i in range(4):
            _write_md(
                vault / "2_projeto" / f"proj_g_{i}.md",
                (
                    "---\n"
                    f"entity_type: project\n"
                    f"id: proj_g_{i}\n"
                    f"title: Good {i}\n"
                    "status: active\n"
                    "revenue_impact: HIGH\n"
                    "---\n"
                ),
            )
        # Bad YAML: unclosed bracket.
        _write_md(
            vault / "2_projeto" / "proj_bad.md",
            "---\nentity_type: project\nid: proj_bad\ntitle: Bad\n: [unclosed\n---\n",
        )
        result = sync.sync_vault_to_code()
        assert result["ingested"] == 4
        assert result["errors"] == 1
        assert result["skipped"] == 0

    def test_missing_entity_type_is_skipped(self, sync_pair):
        sync, vault, _db = sync_pair
        _write_md(
            vault / "2_projeto" / "proj_no_et.md",
            "---\ntitle: No entity_type\nid: proj_no_et\n---\n",
        )
        _write_md(
            vault / "2_projeto" / "proj_with_et.md",
            (
                "---\n"
                "entity_type: project\n"
                "id: proj_with_et\n"
                "title: With ET\n"
                "status: active\n"
                "revenue_impact: HIGH\n"
                "---\n"
            ),
        )
        result = sync.sync_vault_to_code()
        assert result["ingested"] == 1
        assert result["skipped"] == 1

    def test_missing_folder_is_warned_not_failed(self, sync_pair):
        sync, _vault, _db = sync_pair
        # Only write into one folder; ask for two.
        result = sync.sync_vault_to_code(folders=["does_not_exist"])
        assert result == {"ingested": 0, "skipped": 0, "errors": 0, "conflicts": 0}


class TestSyncVaultToCodeUpdates:
    """Re-ingestion after vault edit updates the row."""

    def test_modified_content_updates_upstream_id(self, sync_pair):
        sync, vault, db = sync_pair
        _write_md(
            vault / "2_projeto" / "proj_mod.md",
            (
                "---\n"
                "entity_type: project\n"
                "id: proj_mod\n"
                "title: Original\n"
                "status: active\n"
                "revenue_impact: HIGH\n"
                "---\n"
            ),
        )
        first = sync.sync_vault_to_code()
        with sqlite3.connect(str(db)) as conn:
            upstream_first = conn.execute(
                "SELECT upstream_id FROM planning_entities WHERE id = ?",
                ("proj_mod",),
            ).fetchone()[0]

        # Edit the file.
        _write_md(
            vault / "2_projeto" / "proj_mod.md",
            (
                "---\n"
                "entity_type: project\n"
                "id: proj_mod\n"
                "title: Updated Title\n"
                "status: active\n"
                "revenue_impact: HIGH\n"
                "---\n"
            ),
        )
        second = sync.sync_vault_to_code()
        with sqlite3.connect(str(db)) as conn:
            upstream_second = conn.execute(
                "SELECT upstream_id FROM planning_entities WHERE id = ?",
                ("proj_mod",),
            ).fetchone()[0]

        assert first["ingested"] == 1
        assert second["ingested"] == 1
        assert upstream_first != upstream_second


class TestVaultSyncState:
    """Hash cache survives across calls."""

    def test_state_table_populated(self, sync_pair):
        sync, vault, db = sync_pair
        _write_md(
            vault / "2_projeto" / "proj_state.md",
            (
                "---\n"
                "entity_type: project\n"
                "id: proj_state\n"
                "title: State Test\n"
                "status: active\n"
                "revenue_impact: HIGH\n"
                "---\n"
            ),
        )
        sync.sync_vault_to_code()
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT vault_path, entity_type, entity_id, last_hash "
                "FROM vault_sync_state"
            ).fetchone()
        assert row is not None
        assert row[0] == "2_projeto/proj_state.md"
        assert row[1] == "project"
        assert row[2] == "proj_state"
        assert len(row[3]) == 12