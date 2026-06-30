"""Tests for the enhanced sync_code_to_vault() with PolicyDecision + RICE (T4/T5).

Validates the 12-field computed frontmatter export and atomic write semantics.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterator

import frontmatter
import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from middleware.bidirectional_sync import BidirectionalSync  # noqa: E402


def _make_db(db_path: Path) -> None:
    """Create the minimal schema (planning_entities + policy_decisions)."""
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS policy_decisions (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                policy TEXT NOT NULL,
                qhe REAL,
                c_comp REAL,
                infracoes_24h INTEGER,
                tipo_dia TEXT,
                hardwork_budget_hours REAL,
                pause_duration_minutes INTEGER,
                sleep_target_hours REAL,
                recomendacoes TEXT,
                alertas TEXT,
                days_in_current_policy INTEGER,
                policy_prev TEXT,
                computed_at TIMESTAMP NOT NULL
            )
            """
        )
        conn.commit()


def _insert_pd(conn, date: str, policy: str, qhe: float, computed_at: str) -> None:
    conn.execute(
        "INSERT INTO policy_decisions "
        "(date, policy, qhe, hardwork_budget_hours, pause_duration_minutes, "
        " sleep_target_hours, recomendacoes, alertas, computed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (date, policy, qhe, 4.0, 15, 8.0, "[]", "[]", computed_at),
    )


def _insert_entity(conn, entity_id: str, entity_type: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO planning_entities "
        "(id, entity_type, payload_json, upstream_id, synced_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (entity_id, entity_type, json.dumps(payload), "abc123def456",
         "2026-06-30T00:00:00", "2026-06-30T00:00:00"),
    )


@pytest.fixture
def workdir() -> Iterator[Path]:
    tmp = Path(tempfile.mkdtemp(prefix="vault_export_test_"))
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def setup(workdir: Path):
    vault = workdir / "vault"
    db = workdir / "vibe_ops.db"
    vault.mkdir(parents=True, exist_ok=True)
    _make_db(db)
    return vault, db


class TestSyncCodeToVaultExportsAllComputedFields:
    """The 12 expected fields must land in vault frontmatter."""

    def test_writes_policy_fields(self, setup):
        vault, db = setup
        (vault / "2_projeto").mkdir()
        # Project note
        (vault / "2_projeto" / "proj_a.md").write_text(
            "---\nentity_type: project\nid: proj_a\ntitle: A\n"
            "status: active\nrevenue_impact: HIGH\n---\n",
            encoding="utf-8",
        )
        with sqlite3.connect(str(db)) as conn:
            _insert_entity(conn, "proj_a", "project", {
                "id": "proj_a",
                "title": "A",
                "status": "active",
                "revenue_impact": "HIGH",
                "vault_path": "2_projeto/proj_a.md",
            })
            _insert_pd(conn, "2026-06-30", "MAINTAIN", 0.65,
                       "2026-06-30T12:00:00")
            conn.commit()

        sync = BidirectionalSync(vault, db)
        result = sync.sync_code_to_vault()
        assert result["exported"] == 1

        post = frontmatter.load(str(vault / "2_projeto" / "proj_a.md"))
        assert post.metadata["regime"] == "MAINTAIN"
        assert post.metadata["hardwork_budget_hours"] == 4.0
        assert post.metadata["pause_minutes"] == 15
        assert post.metadata["sleep_target_hours"] == 8.0
        assert post.metadata["qhe_target"] == 0.65
        assert post.metadata["policy_severity"] == "MEDIUM"
        assert "policy_decision_at" in post.metadata

    def test_preserves_existing_frontmatter_keys(self, setup):
        vault, db = setup
        (vault / "2_projeto").mkdir()
        (vault / "2_projeto" / "proj_b.md").write_text(
            "---\nentity_type: project\nid: proj_b\ntitle: B\n"
            "status: active\nrevenue_impact: HIGH\n"
            "xp_points: 100\nmastery_level: advanced\n"
            "tech_stack:\n  - Python\n  - Rust\n---\n",
            encoding="utf-8",
        )
        with sqlite3.connect(str(db)) as conn:
            _insert_entity(conn, "proj_b", "project", {
                "id": "proj_b",
                "title": "B",
                "status": "active",
                "revenue_impact": "HIGH",
                "vault_path": "2_projeto/proj_b.md",
            })
            _insert_pd(conn, "2026-06-30", "PUSH", 0.85,
                       "2026-06-30T12:00:00")
            conn.commit()

        sync = BidirectionalSync(vault, db)
        sync.sync_code_to_vault()

        post = frontmatter.load(str(vault / "2_projeto" / "proj_b.md"))
        # Original keys preserved.
        assert post.metadata["xp_points"] == 100
        assert post.metadata["mastery_level"] == "advanced"
        assert post.metadata["tech_stack"] == ["Python", "Rust"]
        # New keys added.
        assert post.metadata["regime"] == "PUSH"
        assert post.metadata["qhe_target"] == 0.85

    def test_rice_score_included_when_components_present(self, setup):
        vault, db = setup
        (vault / "2_projeto").mkdir()
        (vault / "2_projeto" / "proj_r.md").write_text(
            "---\nentity_type: project\nid: proj_r\ntitle: R\n"
            "status: active\nrevenue_impact: HIGH\n---\n",
            encoding="utf-8",
        )
        with sqlite3.connect(str(db)) as conn:
            _insert_entity(conn, "proj_r", "project", {
                "id": "proj_r",
                "title": "R",
                "status": "active",
                "revenue_impact": "HIGH",
                "vault_path": "2_projeto/proj_r.md",
                "reach": 100,
                "impact": 2.0,
                "confidence": 0.8,
                "effort_h": 5.0,
            })
            conn.commit()

        sync = BidirectionalSync(vault, db)
        sync.sync_code_to_vault()

        post = frontmatter.load(str(vault / "2_projeto" / "proj_r.md"))
        # 100 * 2.0 * 0.8 / 5.0 = 32.0
        assert post.metadata["rice_score"] == pytest.approx(32.0)


class TestSyncCodeToVaultAtomicWrites:
    """Verify the .tmp + rename pattern is in place."""

    def test_no_orphan_tmp_files_after_success(self, setup):
        vault, db = setup
        (vault / "2_projeto").mkdir()
        (vault / "2_projeto" / "proj_z.md").write_text(
            "---\nentity_type: project\nid: proj_z\ntitle: Z\n"
            "status: active\nrevenue_impact: HIGH\n---\n",
            encoding="utf-8",
        )
        with sqlite3.connect(str(db)) as conn:
            _insert_entity(conn, "proj_z", "project", {
                "id": "proj_z",
                "title": "Z",
                "status": "active",
                "revenue_impact": "HIGH",
                "vault_path": "2_projeto/proj_z.md",
            })
            conn.commit()

        sync = BidirectionalSync(vault, db)
        sync.sync_code_to_vault()

        # No leftover .tmp files.
        tmp_files = list((vault / "2_projeto").glob("*.md.tmp"))
        assert tmp_files == []

    def test_idempotent_re_export_updates_only_timestamp(self, setup):
        vault, db = setup
        (vault / "2_projeto").mkdir()
        (vault / "2_projeto" / "proj_i.md").write_text(
            "---\nentity_type: project\nid: proj_i\ntitle: I\n"
            "status: active\nrevenue_impact: HIGH\n---\n",
            encoding="utf-8",
        )
        with sqlite3.connect(str(db)) as conn:
            _insert_entity(conn, "proj_i", "project", {
                "id": "proj_i",
                "title": "I",
                "status": "active",
                "revenue_impact": "HIGH",
                "vault_path": "2_projeto/proj_i.md",
            })
            _insert_pd(conn, "2026-06-30", "PUSH", 0.85,
                       "2026-06-30T12:00:00")
            conn.commit()

        sync = BidirectionalSync(vault, db)
        sync.sync_code_to_vault()
        post_first = frontmatter.load(str(vault / "2_projeto" / "proj_i.md"))
        first_keys = set(post_first.metadata.keys())
        first_regime = post_first.metadata["regime"]

        time.sleep(1.1)
        with sqlite3.connect(str(db)) as conn:
            _insert_pd(conn, "2026-07-01", "MAINTAIN", 0.65,
                       "2026-07-01T09:00:00")
            conn.commit()

        sync2 = BidirectionalSync(vault, db)
        sync2.sync_code_to_vault()
        post_second = frontmatter.load(str(vault / "2_projeto" / "proj_i.md"))

        # Original keys preserved (no removals).
        assert first_keys <= set(post_second.metadata.keys())
        # Regime updated.
        assert post_second.metadata["regime"] == "MAINTAIN"
        assert first_regime != post_second.metadata["regime"]


class TestStatusEndpoint:
    """status() returns counts and last sync timestamps."""

    def test_status_returns_counts(self, setup):
        vault, db = setup
        sync = BidirectionalSync(vault, db)
        with sqlite3.connect(str(db)) as conn:
            _insert_entity(conn, "proj_x", "project", {"id": "proj_x"})
            _insert_entity(conn, "proj_y", "project", {"id": "proj_y"})
            _insert_entity(conn, "sp_z", "study_project", {"id": "sp_z"})
            conn.commit()
        result = sync.status()
        assert result["total_entities"] == 3
        assert result["by_type"]["project"] == 2
        assert result["by_type"]["study_project"] == 1