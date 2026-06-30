"""Tests for HypothesisEvaluator (T7).

Covers the score formula, evaluation rules, refactor-trigger detection,
and persistence. Pure in-memory SQLite, no fixtures required.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from models.hypothesis_entities import (  # noqa: E402
    FalsifiableHypothesis,
)
from pipeline.hypothesis_evaluator import HypothesisEvaluator  # noqa: E402


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


def _hypothesis(**overrides) -> FalsifiableHypothesis:
    base = dict(
        id="fh_eval_test",
        dream_id="dr_alpha",
        hypothesis_text="Daily 90-min focused blocks sustain QHE > 0.7",
        evidence_threshold="QHE < 0.5 over 90 days",
    )
    base.update(overrides)
    return FalsifiableHypothesis(**base)


class TestComputeFalsificationScore:
    def test_spec_formula(self):
        # (2/3)*0.5 + (1 - 1/4)*0.5 = 0.333 + 0.375 = 0.708
        score = HypothesisEvaluator.compute_falsification_score(2, 1, 3, 4)
        assert score == pytest.approx(0.7083, abs=0.01)

    def test_all_leading_zero_lagging(self):
        # (0/3)*0.5 + (1 - 0/2)*0.5 = 0 + 0.5 = 0.5
        score = HypothesisEvaluator.compute_falsification_score(0, 0, 3, 2)
        assert score == pytest.approx(0.5)

    def test_all_leading_met_zero_lagging(self):
        # (3/3)*0.5 + (1 - 0/2)*0.5 = 0.5 + 0.5 = 1.0
        score = HypothesisEvaluator.compute_falsification_score(3, 0, 3, 2)
        assert score == pytest.approx(1.0)

    def test_all_leading_met_all_lagging_met(self):
        # (3/3)*0.5 + (1 - 2/2)*0.5 = 0.5 + 0 = 0.5
        score = HypothesisEvaluator.compute_falsification_score(3, 2, 3, 2)
        assert score == pytest.approx(0.5)

    def test_empty_indicators_treated_as_satisfied(self):
        # Both empty -> 1.0*0.5 + (1-1.0)*0.5 = 0.5
        score = HypothesisEvaluator.compute_falsification_score(0, 0, 0, 0)
        assert score == pytest.approx(0.5)

    def test_only_leading_indicators(self):
        # (2/2)*0.5 + (1 - 1)*0.5 = 0.5
        score = HypothesisEvaluator.compute_falsification_score(2, 0, 2, 0)
        assert score == pytest.approx(0.5)

    def test_score_clamped_to_unit_interval(self):
        # Hypothetical inputs shouldn't push past 0-1 even with edge data.
        score = HypothesisEvaluator.compute_falsification_score(0, 100, 1, 100)
        assert 0.0 <= score <= 1.0


class TestSchemaBootstrap:
    def test_tables_created_on_init(self, conn):
        HypothesisEvaluator(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('falsifiable_hypotheses', 'hypothesis_evaluations')"
        ).fetchall()
        names = {r[0] for r in rows}
        assert names == {"falsifiable_hypotheses", "hypothesis_evaluations"}


class TestUpsertHypothesis:
    def test_insert_then_read(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            leading_indicators=["study_min >= 60"],
            lagging_indicators=["QHE > 0.7"],
            refactor_triggers=["market_collapse"],
            kill_switch_date=date.today() + timedelta(days=10),
        )
        ev.upsert_hypothesis(h)
        row = conn.execute(
            "SELECT id, hypothesis_text FROM falsifiable_hypotheses WHERE id = ?",
            (h.id,),
        ).fetchone()
        assert row is not None
        assert row[1] == h.hypothesis_text

    def test_update_on_conflict(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis()
        ev.upsert_hypothesis(h)
        h_updated = _hypothesis(hypothesis_text="Updated hypothesis text " * 5)
        ev.upsert_hypothesis(h_updated)
        row = conn.execute(
            "SELECT hypothesis_text FROM falsifiable_hypotheses WHERE id = ?",
            (h.id,),
        ).fetchone()
        assert row[0].startswith("Updated")


class TestEvaluateOne:
    def test_validated_when_leading_met_no_lagging(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            leading_indicators=["a", "b", "c"],
            lagging_indicators=["x", "y"],
        )
        ev.upsert_hypothesis(h)
        # Override _count_leading_met to return all-met for this test.
        ev._count_leading_met = lambda _h: (3, 3)
        ev._count_lagging_met = lambda _h: (0, 2)
        ev._detect_refactor_trigger = lambda _h: None
        result = ev.evaluate_all()
        assert len(result) == 1
        assert result[0].verdict == "validated"
        assert result[0].score >= 0.7

    def test_falsified_when_lagging_above_threshold(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            leading_indicators=["a", "b"],
            lagging_indicators=["x", "y"],
        )
        ev.upsert_hypothesis(h)
        ev._count_leading_met = lambda _h: (2, 2)
        ev._count_lagging_met = lambda _h: (2, 2)
        ev._detect_refactor_trigger = lambda _h: None
        result = ev.evaluate_all()
        assert result[0].verdict == "falsified"
        assert result[0].score <= 0.5

    def test_pivoted_when_refactor_triggered(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            leading_indicators=["a"],
            lagging_indicators=["x"],
            refactor_triggers=["market_collapse"],
        )
        ev.upsert_hypothesis(h)
        ev._count_leading_met = lambda _h: (1, 1)
        ev._count_lagging_met = lambda _h: (0, 1)
        ev._detect_refactor_trigger = lambda _h: "market_collapse"
        result = ev.evaluate_all()
        assert result[0].verdict == "pivoted"
        assert "market_collapse" in result[0].notes

    def test_no_change_when_leading_partial(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            leading_indicators=["a", "b", "c"],
            lagging_indicators=["x"],
        )
        ev.upsert_hypothesis(h)
        ev._count_leading_met = lambda _h: (1, 3)
        ev._count_lagging_met = lambda _h: (0, 1)
        ev._detect_refactor_trigger = lambda _h: None
        result = ev.evaluate_all()
        assert result[0].verdict == "no_change"


class TestRefactorTriggerDetection:
    def test_journal_keyword_match(self, conn, tmp_path):
        vault = tmp_path
        (vault / "0_daily").mkdir(parents=True)
        (vault / "0_daily" / "journal.md").write_text(
            "Today the market_collapse arrived and everything went sideways.",
            encoding="utf-8",
        )
        ev = HypothesisEvaluator(conn, vault_path=vault)
        h = _hypothesis(refactor_triggers=["market_collapse"])
        hit = ev._detect_refactor_trigger(h)
        assert hit == "market_collapse"

    def test_no_journal_returns_none(self, conn, tmp_path):
        ev = HypothesisEvaluator(conn, vault_path=tmp_path)
        h = _hypothesis(refactor_triggers=["market_collapse"])
        assert ev._detect_refactor_trigger(h) is None

    def test_no_trigger_in_journal_returns_none(self, conn, tmp_path):
        vault = tmp_path
        (vault / "0_daily").mkdir(parents=True)
        (vault / "0_daily" / "journal.md").write_text(
            "Calm day, no surprises.", encoding="utf-8"
        )
        ev = HypothesisEvaluator(conn, vault_path=vault)
        h = _hypothesis(refactor_triggers=["market_collapse"])
        assert ev._detect_refactor_trigger(h) is None


class TestPersistence:
    def test_evaluation_persisted(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            leading_indicators=["a"],
            lagging_indicators=["x"],
            kill_switch_date=date.today(),  # forces "due"
        )
        ev.upsert_hypothesis(h)
        ev._count_leading_met = lambda _h: (1, 1)
        ev._count_lagging_met = lambda _h: (0, 1)
        ev._detect_refactor_trigger = lambda _h: None
        ev.evaluate_all()
        row = conn.execute(
            "SELECT verdict, score FROM hypothesis_evaluations "
            "WHERE hypothesis_id = ?",
            (h.id,),
        ).fetchone()
        assert row is not None
        assert row[0] == "validated"

    def test_hypothesis_status_updated(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            leading_indicators=["a"],
            lagging_indicators=["x"],
            kill_switch_date=date.today(),
        )
        ev.upsert_hypothesis(h)
        ev._count_leading_met = lambda _h: (1, 1)
        ev._count_lagging_met = lambda _h: (0, 1)
        ev._detect_refactor_trigger = lambda _h: None
        ev.evaluate_all()
        row = conn.execute(
            "SELECT status FROM falsifiable_hypotheses WHERE id = ?",
            (h.id,),
        ).fetchone()
        assert row[0] == "validated"


class TestDueFiltering:
    def test_kill_switch_due(self, conn):
        ev = HypothesisEvaluator(conn)
        past = date.today() - timedelta(days=1)
        h = _hypothesis(kill_switch_date=past)
        ev.upsert_hypothesis(h)
        ev._count_leading_met = lambda _h: (0, 0)
        ev._count_lagging_met = lambda _h: (0, 0)
        ev._detect_refactor_trigger = lambda _h: None
        result = ev.evaluate_all()
        assert len(result) == 1

    def test_fresh_evaluation_skipped(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(last_evaluated_at=datetime.now(timezone.utc).isoformat())
        ev.upsert_hypothesis(h)
        result = ev.evaluate_all()
        assert result == []

    def test_already_validated_skipped(self, conn):
        ev = HypothesisEvaluator(conn)
        h = _hypothesis(
            status="validated",
            kill_switch_date=date.today() - timedelta(days=1),
        )
        ev.upsert_hypothesis(h)
        result = ev.evaluate_all()
        assert result == []