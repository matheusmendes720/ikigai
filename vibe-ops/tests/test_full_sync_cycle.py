"""End-to-end integration test for the full bidirectional sync cycle (T12).

Walks through:
  1. Empty DB + fixture vault
  2. sync_vault_to_code() ingests all valid notes
  3. Sync_policy_decision() injects a PolicyDecision into DB
  4. sync_code_to_vault() writes 12 computed frontmatter keys
  5. HypothesisEvaluator evaluates dream hypothesis
  6. Re-run is idempotent (only timestamps change)
  7. Vault files remain valid YAML + parseable

Runs in <10 seconds against an in-memory temp dir.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import frontmatter
import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
VIBE_OPS_ROOT = Path(__file__).resolve().parents[1]
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from middleware.bidirectional_sync import BidirectionalSync  # noqa: E402
from pipeline.hypothesis_evaluator import HypothesisEvaluator  # noqa: E402


FIXTURE_VAULT = VIBE_OPS_ROOT / "tests" / "fixtures" / "vault"


def _make_db(db_path: Path) -> None:
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


def _insert_policy_decision(
    db_path: Path,
    *,
    policy: str = "MAINTAIN",
    qhe: float = 0.65,
    computed_at: str | None = None,
) -> None:
    if computed_at is None:
        computed_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS policy_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        conn.execute(
            "INSERT INTO policy_decisions "
            "(date, policy, qhe, hardwork_budget_hours, "
            "pause_duration_minutes, sleep_target_hours, "
            "recomendacoes, alertas, computed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "2026-06-30", policy, qhe, 4.0, 15, 8.0,
                json.dumps(["maintain study cadence"]),
                json.dumps([]),
                computed_at,
            ),
        )
        conn.commit()


@pytest.mark.e2e
class TestFullSyncCycle:
    """End-to-end bidirectional sync through the full pipeline."""

    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Iterator[tuple[Path, Path, BidirectionalSync]]:
        vault = tmp_path / "vault"
        db = tmp_path / "vibe_ops.db"
        shutil.copytree(FIXTURE_VAULT, vault)
        _make_db(db)
        sync = BidirectionalSync(vault, db)
        yield vault, db, sync
        sync._conn().close()

    def test_step1_initial_state(self, workspace):
        vault, db, sync = workspace
        with sqlite3.connect(str(db)) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM planning_entities"
            ).fetchone()[0]
        assert total == 0

    def test_step2_vault_ingests_six_notes(self, workspace):
        vault, db, sync = workspace
        result = sync.sync_vault_to_code()
        assert result["ingested"] == 6
        assert result["errors"] == 1
        assert result["skipped"] == 0

        with sqlite3.connect(str(db)) as conn:
            rows = conn.execute(
                "SELECT entity_type, COUNT(*) FROM planning_entities "
                "GROUP BY entity_type"
            ).fetchall()
        by_type = {r[0]: r[1] for r in rows}
        assert by_type.get("project", 0) == 2  # p1 + p2 (broken.md errors out)
        assert by_type.get("dream", 0) == 1
        assert by_type.get("atomic", 0) == 1
        assert by_type.get("moc", 0) == 1
        assert by_type.get("literature_note", 0) == 1
        assert sum(by_type.values()) == 6

    def test_step3_idempotent_reingestion(self, workspace):
        vault, db, sync = workspace
        sync.sync_vault_to_code()
        result2 = sync.sync_vault_to_code()
        assert result2["ingested"] == 0
        assert result2["skipped"] == 6

    def test_step4_code_export_with_policy(self, workspace):
        vault, db, sync = workspace
        sync.sync_vault_to_code()
        _insert_policy_decision(db, policy="PUSH", qhe=0.85)
        sync2 = BidirectionalSync(vault, db)
        result = sync2.sync_code_to_vault()
        assert result["exported"] >= 2

        post = frontmatter.load(str(vault / "2_projeto" / "p1.md"))
        assert post.metadata["regime"] == "PUSH"
        assert post.metadata["qhe_target"] == 0.85
        assert post.metadata["hardwork_budget_hours"] == 4.0

        assert post.metadata["xp_points"] == 1500
        assert post.metadata["mastery_level"] == "advanced"
        assert post.metadata["tech_stack"] == ["Python", "FastAPI", "SQLite"]

    def test_step5_hypothesis_evaluation(self, workspace):
        vault, db, sync = workspace
        from models.hypothesis_entities import FalsifiableHypothesis
        from datetime import date, timedelta
        sync.sync_vault_to_code()
        # Insert a falsifiable hypothesis with kill_switch in the past.
        conn = sqlite3.connect(str(db))
        try:
            fh = FalsifiableHypothesis(
                id="fh_e2e",
                dream_id="dr_dream1",
                hypothesis_text="Testable claim with enough text to pass min length",
                evidence_threshold="QHE < 0.5",
                kill_switch_date=date.today() - timedelta(days=1),
                leading_indicators=["a", "b"],
                lagging_indicators=["x"],
            )
            evaluator = HypothesisEvaluator(conn, vault_path=vault)
            evaluator.upsert_hypothesis(fh)
            evals = evaluator.evaluate_all()
        finally:
            conn.close()
        assert len(evals) == 1
        assert evals[0].hypothesis_id == "fh_e2e"

    def test_step6_idempotent_code_export(self, workspace):
        """Re-running sync_code_to_vault with no policy change preserves file content."""
        vault, db, sync = workspace
        sync.sync_vault_to_code()
        _insert_policy_decision(db, policy="MAINTAIN", qhe=0.65)
        sync2 = BidirectionalSync(vault, db)
        sync2.sync_code_to_vault()

        post_first = frontmatter.load(str(vault / "2_projeto" / "p1.md"))
        first_content = post_first.content
        first_keys = set(post_first.metadata.keys())

        sync2.sync_code_to_vault()
        post_second = frontmatter.load(str(vault / "2_projeto" / "p1.md"))
        second_content = post_second.content
        second_keys = set(post_second.metadata.keys())

        assert first_content == second_content
        assert first_keys == second_keys

    def test_step7_vault_files_still_valid_yaml(self, workspace):
        vault, db, sync = workspace
        sync.sync_vault_to_code()
        _insert_policy_decision(db, policy="MAINTAIN", qhe=0.65)
        sync2 = BidirectionalSync(vault, db)
        sync2.sync_code_to_vault()
        for md_file in vault.rglob("*.md"):
            if md_file.name == "broken.md":
                continue
            post = frontmatter.load(str(md_file))
            assert isinstance(post.metadata, dict)
            assert post.content is not None

    def test_full_cycle_runs_under_10_seconds(self, workspace):
        vault, db, sync = workspace
        start = time.monotonic()
        sync.sync_vault_to_code()
        _insert_policy_decision(db, policy="MAINTAIN", qhe=0.65)
        sync2 = BidirectionalSync(vault, db)
        sync2.sync_code_to_vault()
        sync2.sync_vault_to_code()  # re-ingest
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"cycle took {elapsed:.2f}s"

    def test_no_data_loss_after_roundtrip(self, workspace):
        """Original vault keys must survive vault->code->vault round trip."""
        vault, db, sync = workspace
        original = frontmatter.load(str(vault / "2_projeto" / "p1.md"))
        original_keys = set(original.metadata.keys())

        sync.sync_vault_to_code()
        _insert_policy_decision(db, policy="MAINTAIN", qhe=0.65)
        sync2 = BidirectionalSync(vault, db)
        sync2.sync_code_to_vault()

        roundtripped = frontmatter.load(str(vault / "2_projeto" / "p1.md"))
        roundtripped_keys = set(roundtripped.metadata.keys())
        # All original keys preserved.
        assert original_keys.issubset(roundtripped_keys)
        # Plus new computed keys.
        new_keys = roundtripped_keys - original_keys
        assert "regime" in new_keys
        assert "qhe_target" in new_keys
        assert "hardwork_budget_hours" in new_keys
        assert "policy_decision_at" in new_keys