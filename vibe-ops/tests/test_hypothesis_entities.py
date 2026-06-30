"""Tests for FalsifiableHypothesis + HypothesisEvaluation entities (T6)."""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from models.hypothesis_entities import (  # noqa: E402
    FalsifiableHypothesis,
    HypothesisEvaluation,
)


def _base_kwargs(**overrides):
    base = dict(
        id="fh_test_basic",
        dream_id="dr_alpha",
        hypothesis_text="Daily 90-min focused work blocks will sustain QHE > 0.7",
        evidence_threshold="QHE drops below 0.5 over 90-day window",
    )
    base.update(overrides)
    return base


class TestFalsifiableHypothesisDefaults:
    def test_id_pattern_enforced(self):
        h = FalsifiableHypothesis(**_base_kwargs())
        assert h.id == "fh_test_basic"

    def test_invalid_id_pattern_rejected(self):
        with pytest.raises(ValidationError):
            FalsifiableHypothesis(**_base_kwargs(id="bad_id"))

    def test_status_default_active(self):
        h = FalsifiableHypothesis(**_base_kwargs())
        assert h.status == "active"

    def test_measurement_window_default_90(self):
        h = FalsifiableHypothesis(**_base_kwargs())
        assert h.measurement_window_days == 90

    def test_indicator_lists_default_empty(self):
        h = FalsifiableHypothesis(**_base_kwargs())
        assert h.leading_indicators == []
        assert h.lagging_indicators == []
        assert h.refactor_triggers == []

    def test_kill_switch_default_none(self):
        h = FalsifiableHypothesis(**_base_kwargs())
        assert h.kill_switch_date is None

    def test_created_at_default_now(self):
        h = FalsifiableHypothesis(**_base_kwargs())
        assert isinstance(h.created_at, datetime)
        assert (datetime.now(h.created_at.tzinfo) - h.created_at).total_seconds() < 5


class TestFalsifiableHypothesisValidation:
    def test_hypothesis_text_min_length(self):
        with pytest.raises(ValidationError):
            FalsifiableHypothesis(**_base_kwargs(hypothesis_text="too short"))

    def test_hypothesis_text_max_length(self):
        with pytest.raises(ValidationError):
            FalsifiableHypothesis(**_base_kwargs(hypothesis_text="x" * 1001))

    def test_evidence_threshold_required(self):
        kwargs = _base_kwargs()
        kwargs.pop("evidence_threshold")
        with pytest.raises(ValidationError):
            FalsifiableHypothesis(**kwargs)

    def test_measurement_window_min(self):
        with pytest.raises(ValidationError):
            FalsifiableHypothesis(**_base_kwargs(measurement_window_days=0))

    def test_measurement_window_max(self):
        with pytest.raises(ValidationError):
            FalsifiableHypothesis(**_base_kwargs(measurement_window_days=3651))

    def test_all_status_values_accepted(self):
        for status in ("active", "validated", "falsified", "pivoted", "abandoned"):
            h = FalsifiableHypothesis(**_base_kwargs(status=status))
            assert h.status == status

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            FalsifiableHypothesis(**_base_kwargs(status="maybe"))


class TestFalsifiableHypothesisAssignment:
    def test_indicators_assigned(self):
        h = FalsifiableHypothesis(**_base_kwargs(
            leading_indicators=["study_session_minutes >= 60", "sleep_target_met"],
            lagging_indicators=["QHE > 0.7", "weekly_xp_gain > 100"],
            refactor_triggers=["market_shift_to_ai", "team_restructure"],
        ))
        assert len(h.leading_indicators) == 2
        assert len(h.lagging_indicators) == 2
        assert len(h.refactor_triggers) == 2

    def test_kill_switch_assigned(self):
        ks = date.today() + timedelta(days=90)
        h = FalsifiableHypothesis(**_base_kwargs(kill_switch_date=ks))
        assert h.kill_switch_date == ks

    def test_last_evaluated_at_assigned(self):
        ts = datetime(2026, 6, 30, 12, 0, 0)
        h = FalsifiableHypothesis(**_base_kwargs(last_evaluated_at=ts))
        assert h.last_evaluated_at == ts

    def test_vault_path_assigned(self):
        h = FalsifiableHypothesis(
            **_base_kwargs(vault_path="/vault/hypotheses/fh_test_basic.md")
        )
        assert h.vault_path == "/vault/hypotheses/fh_test_basic.md"

    def test_extra_fields_allowed(self):
        h = FalsifiableHypothesis(
            **_base_kwargs(custom_field="vault_extra", numeric_meta=42)
        )
        assert h.custom_field == "vault_extra"
        assert h.numeric_meta == 42


class TestHypothesisEvaluation:
    def test_basic_construction(self):
        e = HypothesisEvaluation(
            hypothesis_id="fh_test_basic",
            verdict="validated",
            score=0.85,
        )
        assert e.verdict == "validated"
        assert e.score == 0.85
        assert e.notes == ""

    def test_all_verdicts_accepted(self):
        for verdict in ("validated", "falsified", "pivoted", "no_change"):
            e = HypothesisEvaluation(hypothesis_id="fh_x", verdict=verdict, score=0.5)
            assert e.verdict == verdict

    def test_score_min_boundary(self):
        with pytest.raises(ValidationError):
            HypothesisEvaluation(hypothesis_id="fh_x", verdict="validated", score=-0.01)

    def test_score_max_boundary(self):
        with pytest.raises(ValidationError):
            HypothesisEvaluation(hypothesis_id="fh_x", verdict="validated", score=1.01)

    def test_notes_default_empty(self):
        e = HypothesisEvaluation(hypothesis_id="fh_x", verdict="validated", score=0.5)
        assert e.notes == ""

    def test_indicator_counts_recorded(self):
        e = HypothesisEvaluation(
            hypothesis_id="fh_x",
            verdict="validated",
            score=0.8,
            leading_met=3,
            lagging_met=2,
            leading_total=4,
            lagging_total=3,
            notes="Strong on behaviors, partial on outcomes",
        )
        assert e.leading_met == 3
        assert e.lagging_met == 2
        assert e.leading_total == 4
        assert e.lagging_total == 3
        assert "Strong" in e.notes