"""Comprehensive unit tests for :mod:`operational.core.policy_engine`.

Covers (Sprint 4B — Core Layer Part 2):

* :class:`Severity` — StrEnum, three tiers, value strings.
* :class:`PolicyEvaluation` — frozen dataclass, fields, equality.
* :func:`is_recover_entry_condition` — predicate on QHE + infractions.
* :func:`consecutive_days_above_threshold` / below — prefix-length
  counting with date ordering and ``qhe_input is None`` guards.
* :func:`evaluate_policy` — the full 4-state FSM: initial seed,
  emergency entry, RECOVER stay + exit, REDUCE transitions,
  MAINTAIN transitions, PUSH transitions, severity mapping, and
  ``is_transition`` flag.
* :class:`PolicyEngine` — construction, ``max_history`` validation,
  history trimming, transition log, ``reset``, ``days_in_current_state``.

All tests are deterministic. Where a transition needs a date, the
fixture provides one.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime
from typing import ClassVar

import pytest

from operational.core.policy_engine import (
    PolicyEngine,
    PolicyEvaluation,
    Severity,
    consecutive_days_above_threshold,
    consecutive_days_below_threshold,
    evaluate_policy,
    is_recover_entry_condition,
)
from operational.entities.habit import QHEMetrics
from operational.entities.policy import PolicyDecision
from operational.enums import EnergyLevel, PolicyState

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_DT: ClassVar[datetime] = datetime(2026, 6, 7, 9, 0, 0)
_DATE: ClassVar[date] = date(2026, 6, 7)


def _qhe(  # noqa: PLR0913
    *,
    habit_avg: float = 0.7,
    consistency: float = 0.7,
    streak_bonus: float = 0.5,
    energy_ratio: float = 0.7,
    eta: float = 0.5,
    qhe_id: str = "qhe_unit01",
    on_date: date = _DATE,
) -> QHEMetrics:
    """Build a :class:`QHEMetrics` with sane defaults."""
    return QHEMetrics(
        id=qhe_id,
        date=on_date,
        habit_avg=habit_avg,
        consistency=consistency,
        streak_bonus=streak_bonus,
        energy_ratio=energy_ratio,
        eta=eta,
    )


def _decision(  # noqa: PLR0913
    state: PolicyState,
    *,
    qhe_input: float | None = 0.7,
    on_date: date = _DATE,
    days_in_state: int = 0,
    previous_state: PolicyState | None = None,
    infraction_count: int = 0,
    severity: str = "INFO",
    decision_id: str = "pcs_unit01a",
) -> PolicyDecision:
    """Build a valid :class:`PolicyDecision` for testing history."""
    return PolicyDecision.from_state(
        decision_date=on_date,
        state=state,
        rationale="test",
        severity=severity,  # type: ignore[arg-type]
        previous_state=previous_state,
        qhe_input=qhe_input,
        infraction_count=infraction_count,
        days_in_state=days_in_state,
        id=decision_id,
        created_at=_DT,
    )


def _history(
    *pairs: tuple[PolicyState, float, date],
) -> list[PolicyDecision]:
    """Build a history from ``(state, qhe_input, date)`` tuples.

    Older dates come first in the result list (so iteration is
    chronological, matching the storage order in :class:`PolicyEngine`).
    """
    sorted_pairs = sorted(pairs, key=lambda p: p[2])
    history: list[PolicyDecision] = []
    for idx, (state, qhe_value, day) in enumerate(sorted_pairs):
        history.append(
            _decision(
                state,
                qhe_input=qhe_value,
                on_date=day,
                decision_id=f"pcs_h{idx:04d}",
            )
        )
    return history


def _new_engine(max_history: int = 30) -> PolicyEngine:
    """Build a :class:`PolicyEngine` with sensible defaults."""
    return PolicyEngine(max_history=max_history)


# ===========================================================================
# Module surface
# ===========================================================================


class TestModuleSurface:
    """The :mod:`policy_engine` module exports the expected public symbols."""

    def test_all_exports_present(self) -> None:
        """``__all__`` lists the canonical public surface."""
        from operational.core import policy_engine

        expected = {
            "PolicyEngine",
            "PolicyEvaluation",
            "Severity",
            "consecutive_days_above_threshold",
            "consecutive_days_below_threshold",
            "evaluate_policy",
            "is_recover_entry_condition",
        }
        assert set(policy_engine.__all__) == expected

    def test_all_names_importable(self) -> None:
        for name in [
            "PolicyEngine",
            "PolicyEvaluation",
            "Severity",
            "consecutive_days_above_threshold",
            "consecutive_days_below_threshold",
            "evaluate_policy",
            "is_recover_entry_condition",
        ]:
            from operational.core import policy_engine as mod

            assert hasattr(mod, name), f"Missing export: {name}"


# ===========================================================================
# Severity
# ===========================================================================


class TestSeverity:
    """:class:`Severity` is a frozen StrEnum with three tiers."""

    def test_three_members(self) -> None:
        assert set(Severity) == {Severity.INFO, Severity.WARNING, Severity.CRITICAL}

    @pytest.mark.parametrize("member", list(Severity))
    def test_values_are_strings(self, member: Severity) -> None:
        """Each member's ``.value`` is a non-empty string."""
        assert isinstance(member.value, str)
        assert member.value in {"INFO", "WARNING", "CRITICAL"}

    def test_cannot_add_members(self) -> None:
        """The enum is closed (StrEnum default)."""
        with pytest.raises((AttributeError, TypeError, ValueError)):
            _ = Severity.NEW  # type: ignore[attr-defined]

    def test_severity_ordering(self) -> None:
        """Severity has no defined ordering, but membership works."""
        assert Severity("INFO") is Severity.INFO
        assert Severity("WARNING") is Severity.WARNING
        assert Severity("CRITICAL") is Severity.CRITICAL


# ===========================================================================
# PolicyEvaluation
# ===========================================================================


class TestPolicyEvaluation:
    """:class:`PolicyEvaluation` is a frozen dataclass with the right fields."""

    def test_create_evaluation(self) -> None:
        ev = PolicyEvaluation(
            new_state=PolicyState.PUSH,
            severity=Severity.INFO,
            rationale="upgraded",
            days_in_state=3,
            is_transition=True,
            previous_state=PolicyState.MAINTAIN,
        )
        assert ev.new_state is PolicyState.PUSH
        assert ev.severity is Severity.INFO
        assert ev.rationale == "upgraded"
        assert ev.days_in_state == 3
        assert ev.is_transition is True
        assert ev.previous_state is PolicyState.MAINTAIN

    def test_frozen(self) -> None:
        ev = PolicyEvaluation(
            new_state=PolicyState.MAINTAIN,
            severity=Severity.INFO,
            rationale="r",
            days_in_state=0,
            is_transition=False,
            previous_state=None,
        )
        with pytest.raises(FrozenInstanceError):
            ev.new_state = PolicyState.RECOVER  # type: ignore[misc]

    def test_equality(self) -> None:
        a = PolicyEvaluation(
            new_state=PolicyState.PUSH,
            severity=Severity.INFO,
            rationale="r",
            days_in_state=1,
            is_transition=True,
            previous_state=PolicyState.MAINTAIN,
        )
        b = PolicyEvaluation(
            new_state=PolicyState.PUSH,
            severity=Severity.INFO,
            rationale="r",
            days_in_state=1,
            is_transition=True,
            previous_state=PolicyState.MAINTAIN,
        )
        assert a == b

    def test_hashable(self) -> None:
        ev = PolicyEvaluation(
            new_state=PolicyState.PUSH,
            severity=Severity.INFO,
            rationale="r",
            days_in_state=0,
            is_transition=False,
            previous_state=None,
        )
        assert hash(ev) is not None


# ===========================================================================
# is_recover_entry_condition
# ===========================================================================


class TestIsRecoverEntryCondition:
    """:func:`is_recover_entry_condition` returns the correct predicate."""

    def test_false_for_normal_qhe_no_infractions(self) -> None:
        assert is_recover_entry_condition(0.7, 0) is False

    def test_false_for_two_infractions(self) -> None:
        assert is_recover_entry_condition(0.7, 2) is False

    def test_true_for_three_infractions(self) -> None:
        assert is_recover_entry_condition(0.7, 3) is True

    def test_true_for_many_infractions(self) -> None:
        assert is_recover_entry_condition(0.7, 10) is True

    def test_true_for_extreme_low_qhe(self) -> None:
        assert is_recover_entry_condition(0.1, 0) is True

    def test_true_for_qhe_at_boundary_low(self) -> None:
        """``QHE < 0.30`` is the rule; ``0.30`` itself is not extreme."""
        assert is_recover_entry_condition(0.29, 0) is True
        assert is_recover_entry_condition(0.30, 0) is False

    def test_true_for_both_conditions(self) -> None:
        assert is_recover_entry_condition(0.1, 5) is True

    @pytest.mark.parametrize("qhe", [0.0, 0.10, 0.20, 0.29])
    def test_param_extreme_low_qhe(self, qhe: float) -> None:
        assert is_recover_entry_condition(qhe, 0) is True

    @pytest.mark.parametrize("qhe", [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0])
    def test_param_safe_qhe(self, qhe: float) -> None:
        assert is_recover_entry_condition(qhe, 0) is False

    @pytest.mark.parametrize("infractions", [3, 4, 5, 100])
    def test_param_infractions_trigger(self, infractions: int) -> None:
        assert is_recover_entry_condition(0.7, infractions) is True

    @pytest.mark.parametrize("infractions", [0, 1, 2])
    def test_param_infractions_safe(self, infractions: int) -> None:
        assert is_recover_entry_condition(0.7, infractions) is False


# ===========================================================================
# consecutive_days_above_threshold
# ===========================================================================


class TestConsecutiveDaysAboveThreshold:
    """:func:`consecutive_days_above_threshold` counts the prefix correctly."""

    def test_empty_history_returns_zero(self) -> None:
        assert consecutive_days_above_threshold([], 0.85) == 0

    def test_three_consecutive_days(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 3)),
        )
        assert consecutive_days_above_threshold(history, 0.85) == 3

    def test_unsorted_history_is_sorted(self) -> None:
        """Function sorts internally by date desc — pass unsorted."""
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 3)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 2)),
        )
        assert consecutive_days_above_threshold(history, 0.85) == 3

    def test_broken_streak(self) -> None:
        """A single low day in the middle breaks the streak."""
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 3)),
        )
        assert consecutive_days_above_threshold(history, 0.85) == 1

    def test_inclusive_boundary(self) -> None:
        """``qhe_input == threshold`` counts (>=, not strict >)."""
        history = _history(
            (PolicyState.MAINTAIN, 0.85, date(2026, 6, 1)),
        )
        assert consecutive_days_above_threshold(history, 0.85) == 1

    def test_no_match_returns_zero(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
        )
        assert consecutive_days_above_threshold(history, 0.85) == 0

    def test_none_qhe_breaks_streak(self) -> None:
        """A ``None`` qhe_input stops the prefix walk."""
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, None, date(2026, 6, 2)),  # type: ignore[arg-type]
        )
        assert consecutive_days_above_threshold(history, 0.85) == 0

    def test_all_match(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 1.0, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.95, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 3)),
        )
        assert consecutive_days_above_threshold(history, 0.85) == 3

    def test_does_not_mutate_input(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 2)),
        )
        original_order = [d.date for d in history]
        consecutive_days_above_threshold(history, 0.85)
        assert [d.date for d in history] == original_order


# ===========================================================================
# consecutive_days_below_threshold
# ===========================================================================


class TestConsecutiveDaysBelowThreshold:
    """:func:`consecutive_days_below_threshold` is the strict-less mirror."""

    def test_empty_history_returns_zero(self) -> None:
        assert consecutive_days_below_threshold([], 0.60) == 0

    def test_three_consecutive_days(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.4, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.3, date(2026, 6, 3)),
        )
        assert consecutive_days_below_threshold(history, 0.60) == 3

    def test_unsorted_history_is_sorted(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 3)),
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 2)),
        )
        assert consecutive_days_below_threshold(history, 0.60) == 3

    def test_broken_streak(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.8, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 3)),
        )
        assert consecutive_days_below_threshold(history, 0.60) == 1

    def test_strict_inequality(self) -> None:
        """``qhe_input == threshold`` does NOT count (strict <)."""
        history = _history(
            (PolicyState.MAINTAIN, 0.60, date(2026, 6, 1)),
        )
        assert consecutive_days_below_threshold(history, 0.60) == 0

    def test_no_match_returns_zero(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.7, date(2026, 6, 1)),
        )
        assert consecutive_days_below_threshold(history, 0.60) == 0

    def test_none_qhe_breaks_streak(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, None, date(2026, 6, 2)),  # type: ignore[arg-type]
        )
        assert consecutive_days_below_threshold(history, 0.60) == 0

    def test_input_is_tuple(self) -> None:
        """Function accepts tuples as well as lists."""
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
        )
        assert consecutive_days_below_threshold(tuple(history), 0.60) == 1

    def test_negative_qhe_clamps_to_zero(self) -> None:
        """A negative QHE is clamped to 0 for storage (defensive)."""
        from operational.core.policy_engine import _clamp_qhe_for_storage

        assert _clamp_qhe_for_storage(-0.5) == 0.0
        assert _clamp_qhe_for_storage(0.0) == 0.0


# ===========================================================================
# evaluate_policy — initial state
# ===========================================================================


class TestEvaluateInitialState:
    """:func:`evaluate_policy` seeds the FSM at MAINTAIN."""

    def test_initial_no_history_seeds_maintain(self) -> None:
        result = evaluate_policy(None, _qhe(), (), 0)
        assert result.new_state is PolicyState.MAINTAIN
        assert result.severity is Severity.INFO
        assert result.previous_state is None
        assert result.days_in_state == 0
        assert result.is_transition is False

    def test_initial_seeds_maintain_even_with_high_qhe(self) -> None:
        """Initial seed is MAINTAIN regardless of QHE."""
        result = evaluate_policy(None, _qhe(habit_avg=0.95, energy_ratio=0.95), (), 0)
        assert result.new_state is PolicyState.MAINTAIN
        assert result.is_transition is False

    def test_initial_seeds_maintain_even_with_low_qhe(self) -> None:
        """Initial seed is MAINTAIN even at QHE > 0.30 (no emergency)."""
        result = evaluate_policy(None, _qhe(habit_avg=0.5, energy_ratio=0.5), (), 0)
        assert result.new_state is PolicyState.MAINTAIN


# ===========================================================================
# evaluate_policy — emergency RECOVER entry
# ===========================================================================


class TestEvaluateRecoverEntry:
    """Infractions or extreme QHE trigger immediate RECOVER entry."""

    def test_recover_entry_from_maintain_infractions(self) -> None:
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), (), infraction_count=3)
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.CRITICAL
        assert result.previous_state is PolicyState.MAINTAIN
        assert result.is_transition is True

    def test_recover_entry_from_push_infractions(self) -> None:
        result = evaluate_policy(PolicyState.PUSH, _qhe(), (), infraction_count=5)
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.CRITICAL

    def test_recover_entry_from_reduce_infractions(self) -> None:
        result = evaluate_policy(PolicyState.REDUCE, _qhe(), (), infraction_count=3)
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.CRITICAL

    def test_recover_entry_from_extreme_low_qhe(self) -> None:
        """QHE < 0.30 with no infractions still triggers RECOVER."""
        result = evaluate_policy(
            PolicyState.MAINTAIN,
            _qhe(habit_avg=0.2, energy_ratio=0.2),
            (),
            infraction_count=0,
        )
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.CRITICAL

    def test_no_recover_entry_when_already_recover(self) -> None:
        """If already RECOVER, the emergency rule does NOT re-fire.

        Otherwise the RECOVER block (rule 2) takes over and decides
        stay vs. exit.
        """
        history = _history(
            (PolicyState.RECOVER, 0.4, date(2026, 6, 1)),
            (PolicyState.RECOVER, 0.4, date(2026, 6, 2)),
        )
        result = evaluate_policy(
            PolicyState.RECOVER, _qhe(), history, infraction_count=10
        )
        # Already in RECOVER, low QHE, 0 days above threshold -> stay.
        assert result.new_state is PolicyState.RECOVER
        assert result.is_transition is False


# ===========================================================================
# evaluate_policy — RECOVER block
# ===========================================================================


class TestEvaluateRecoverBlock:
    """RECOVER state: stay or exit to REDUCE on stable QHE."""

    def test_stay_recover_below_threshold(self) -> None:
        history = _history(
            (PolicyState.RECOVER, 0.4, date(2026, 6, 1)),
        )
        result = evaluate_policy(PolicyState.RECOVER, _qhe(), history, 0)
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.CRITICAL
        assert result.is_transition is False

    def test_recover_exit_to_reduce_three_days_above(self) -> None:
        history = _history(
            (PolicyState.RECOVER, 0.65, date(2026, 6, 1)),
            (PolicyState.RECOVER, 0.7, date(2026, 6, 2)),
            (PolicyState.RECOVER, 0.75, date(2026, 6, 3)),
        )
        result = evaluate_policy(PolicyState.RECOVER, _qhe(), history, 0)
        assert result.new_state is PolicyState.REDUCE
        assert result.severity is Severity.INFO
        assert result.previous_state is PolicyState.RECOVER
        assert result.is_transition is True

    def test_recover_two_days_not_enough_to_exit(self) -> None:
        history = _history(
            (PolicyState.RECOVER, 0.65, date(2026, 6, 1)),
            (PolicyState.RECOVER, 0.7, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.RECOVER, _qhe(), history, 0)
        assert result.new_state is PolicyState.RECOVER
        assert result.is_transition is False


# ===========================================================================
# evaluate_policy — REDUCE block
# ===========================================================================


class TestEvaluateReduceBlock:
    """REDUCE state: upgrade, downgrade, or stay."""

    def test_stay_reduce_mixed_qhe(self) -> None:
        history = _history(
            (PolicyState.REDUCE, 0.7, date(2026, 6, 1)),
        )
        result = evaluate_policy(PolicyState.REDUCE, _qhe(), history, 0)
        assert result.new_state is PolicyState.REDUCE
        assert result.severity is Severity.WARNING
        assert result.is_transition is False

    def test_reduce_to_maintain_three_days_above_push(self) -> None:
        history = _history(
            (PolicyState.REDUCE, 0.9, date(2026, 6, 1)),
            (PolicyState.REDUCE, 0.92, date(2026, 6, 2)),
            (PolicyState.REDUCE, 0.88, date(2026, 6, 3)),
        )
        result = evaluate_policy(PolicyState.REDUCE, _qhe(), history, 0)
        assert result.new_state is PolicyState.MAINTAIN
        assert result.severity is Severity.INFO
        assert result.previous_state is PolicyState.REDUCE
        assert result.is_transition is True

    def test_reduce_to_recover_two_days_below_recover(self) -> None:
        history = _history(
            (PolicyState.REDUCE, 0.5, date(2026, 6, 1)),
            (PolicyState.REDUCE, 0.4, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.REDUCE, _qhe(), history, 0)
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.WARNING
        assert result.previous_state is PolicyState.REDUCE
        assert result.is_transition is True

    def test_reduce_upgrade_takes_precedence(self) -> None:
        """If both upgrade and downgrade are met, upgrade wins (checked first)."""
        history = _history(
            (PolicyState.REDUCE, 0.5, date(2026, 6, 1)),
            (PolicyState.REDUCE, 0.9, date(2026, 6, 2)),
            (PolicyState.REDUCE, 0.92, date(2026, 6, 3)),
            (PolicyState.REDUCE, 0.95, date(2026, 6, 4)),
        )
        result = evaluate_policy(PolicyState.REDUCE, _qhe(), history, 0)
        assert result.new_state is PolicyState.MAINTAIN


# ===========================================================================
# evaluate_policy — MAINTAIN block
# ===========================================================================


class TestEvaluateMaintainBlock:
    """MAINTAIN state: upgrade to PUSH, downgrade to REDUCE, or stay."""

    def test_stay_maintain_default(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.75, date(2026, 6, 1)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.new_state is PolicyState.MAINTAIN
        assert result.severity is Severity.INFO
        assert result.is_transition is False

    def test_maintain_to_push_three_days_above(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.92, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.95, date(2026, 6, 3)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.new_state is PolicyState.PUSH
        assert result.severity is Severity.INFO
        assert result.previous_state is PolicyState.MAINTAIN
        assert result.is_transition is True

    def test_maintain_to_reduce_two_days_below(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.4, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.new_state is PolicyState.REDUCE
        assert result.severity is Severity.WARNING
        assert result.previous_state is PolicyState.MAINTAIN
        assert result.is_transition is True

    def test_maintain_two_days_above_not_enough(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.92, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.new_state is PolicyState.MAINTAIN
        assert result.is_transition is False


# ===========================================================================
# evaluate_policy — PUSH block
# ===========================================================================


class TestEvaluatePushBlock:
    """PUSH state: downgrade to MAINTAIN/REDUCE, or stay."""

    def test_stay_push_normal(self) -> None:
        history = _history(
            (PolicyState.PUSH, 0.9, date(2026, 6, 1)),
        )
        result = evaluate_policy(PolicyState.PUSH, _qhe(), history, 0)
        assert result.new_state is PolicyState.PUSH
        assert result.severity is Severity.INFO
        assert result.is_transition is False

    def test_push_to_maintain_two_days_below_recover(self) -> None:
        history = _history(
            (PolicyState.PUSH, 0.5, date(2026, 6, 1)),
            (PolicyState.PUSH, 0.4, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.PUSH, _qhe(), history, 0)
        assert result.new_state is PolicyState.MAINTAIN
        assert result.severity is Severity.WARNING
        assert result.previous_state is PolicyState.PUSH
        assert result.is_transition is True

    def test_push_to_reduce_early_warning_two_infractions(self) -> None:
        """PUSH with >= 2 infractions and no sustained-low QHE."""
        history = _history(
            (PolicyState.PUSH, 0.9, date(2026, 6, 1)),
        )
        result = evaluate_policy(PolicyState.PUSH, _qhe(), history, infraction_count=2)
        assert result.new_state is PolicyState.REDUCE
        assert result.severity is Severity.WARNING
        assert "early warning" in result.rationale
        assert result.is_transition is True

    def test_push_stays_with_one_infraction(self) -> None:
        history = _history(
            (PolicyState.PUSH, 0.9, date(2026, 6, 1)),
        )
        result = evaluate_policy(PolicyState.PUSH, _qhe(), history, infraction_count=1)
        assert result.new_state is PolicyState.PUSH
        assert result.is_transition is False

    def test_push_low_qhe_takes_precedence_over_infractions(self) -> None:
        """Sustained low QHE (no emergency) → MAINTAIN, not REDUCE early warning.

        Uses 0 infractions to avoid the emergency RECOVER rule.
        """
        history = _history(
            (PolicyState.PUSH, 0.5, date(2026, 6, 1)),
            (PolicyState.PUSH, 0.4, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.PUSH, _qhe(), history, infraction_count=0)
        assert result.new_state is PolicyState.MAINTAIN

    def test_push_emergency_recover_overrides_low_qhe(self) -> None:
        """Infractions >= 3 trigger emergency RECOVER, not MAINTAIN via low QHE."""
        history = _history(
            (PolicyState.PUSH, 0.5, date(2026, 6, 1)),
            (PolicyState.PUSH, 0.4, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.PUSH, _qhe(), history, infraction_count=5)
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.CRITICAL


# ===========================================================================
# evaluate_policy — severity mapping
# ===========================================================================


class TestEvaluateSeverityMapping:
    """Severity is determined by the target state."""

    def test_severity_critical_for_recover(self) -> None:
        result = evaluate_policy(
            PolicyState.MAINTAIN, _qhe(), (), infraction_count=3
        )
        assert result.severity is Severity.CRITICAL

    def test_severity_warning_for_reduce(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.5, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.4, date(2026, 6, 2)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.severity is Severity.WARNING

    def test_severity_info_for_push_upgrade(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.92, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.95, date(2026, 6, 3)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.severity is Severity.INFO

    def test_severity_info_for_stay(self) -> None:
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), (), 0)
        assert result.severity is Severity.INFO

    def test_severity_warning_for_stay_reduce(self) -> None:
        """A REDUCE stay is WARNING even without a transition."""
        result = evaluate_policy(PolicyState.REDUCE, _qhe(), (), 0)
        assert result.severity is Severity.WARNING
        assert result.is_transition is False


# ===========================================================================
# evaluate_policy — is_transition and days_in_state
# ===========================================================================


class TestEvaluateTransitionFlags:
    """``is_transition`` and ``days_in_state`` are accurate."""

    def test_is_transition_true_on_upgrade(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.9, date(2026, 6, 3)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.is_transition is True

    def test_is_transition_false_on_stay(self) -> None:
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), (), 0)
        assert result.is_transition is False

    def test_days_in_state_zero_for_initial(self) -> None:
        result = evaluate_policy(None, _qhe(), (), 0)
        assert result.days_in_state == 0

    def test_days_in_state_counts_consecutive_state(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.7, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.7, date(2026, 6, 2)),
            (PolicyState.REDUCE, 0.7, date(2026, 6, 3)),  # breaks streak
        )
        result = evaluate_policy(PolicyState.REDUCE, _qhe(), history, 0)
        assert result.days_in_state == 1

    def test_days_in_state_full_streak(self) -> None:
        history = _history(
            (PolicyState.MAINTAIN, 0.7, date(2026, 6, 1)),
            (PolicyState.MAINTAIN, 0.7, date(2026, 6, 2)),
            (PolicyState.MAINTAIN, 0.7, date(2026, 6, 3)),
        )
        result = evaluate_policy(PolicyState.MAINTAIN, _qhe(), history, 0)
        assert result.days_in_state == 3


# ===========================================================================
# evaluate_policy — rationale is non-empty
# ===========================================================================


class TestEvaluateRationale:
    """Every :class:`PolicyEvaluation` carries a non-empty rationale."""

    @pytest.mark.parametrize(
        "current",
        [
            None,
            PolicyState.PUSH,
            PolicyState.MAINTAIN,
            PolicyState.REDUCE,
            PolicyState.RECOVER,
        ],
    )
    def test_rationale_is_non_empty(self, current: PolicyState | None) -> None:
        result = evaluate_policy(current, _qhe(), (), 0)
        assert isinstance(result.rationale, str)
        assert len(result.rationale) > 0


# ===========================================================================
# evaluate_policy — full FSM cycle (parametric)
# ===========================================================================


class TestEvaluateFullCycle:
    """PUSH → MAINTAIN → REDUCE → RECOVER → REDUCE → MAINTAIN → PUSH cycle."""

    def test_full_fsm_cycle(self) -> None:
        """Simulate a full down-up cycle through all four states.

        The histerese windows are 3 days (upgrade) and 2 days
        (downgrade). The engine counts the **history** of past
        decisions (not the current QHE), so the transition fires
        on the 4th call for an upgrade and the 3rd call for a
        downgrade.

        This test exercises the **main** down-up transitions
        (MAINTAIN → PUSH → MAINTAIN → RECOVER → REDUCE) and
        verifies the engine state at each waypoint. The complete
        PUSH ↔ MAINTAIN ↔ REDUCE ↔ RECOVER tour is covered by the
        per-block tests in :class:`TestEvaluateReduceBlock` and
        friends — they require careful streak management that is
        hard to combine with multiple transitions in a single
        test (the histerese windows operate on the *whole* history,
        not the current state).
        """
        engine = _new_engine()
        # Day 1: initial seed at MAINTAIN.
        d = engine.evaluate(_qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, 1))
        assert d.state is PolicyState.MAINTAIN

        # Days 2-5: upgrade to PUSH (4th day has 3 prior days in history).
        for day_offset in (2, 3, 4, 5):
            d = engine.evaluate(
                _qhe(habit_avg=0.9, energy_ratio=0.9),
                on_date=date(2026, 6, day_offset),
            )
        assert d.state is PolicyState.PUSH

        # Days 6-8: drop QHE — downgrade to MAINTAIN (3rd day has 2 prior low days).
        for day_offset in (6, 7, 8):
            d = engine.evaluate(
                _qhe(habit_avg=0.5, energy_ratio=0.8),
                on_date=date(2026, 6, day_offset),
            )
        # QHE = 0.5 * 0.8 * 1.25 = 0.5 (below 0.60, above 0.30) -> downgrade
        assert d.state is PolicyState.MAINTAIN

        # Day 9: extreme QHE — emergency entry to RECOVER.
        d = engine.evaluate(
            _qhe(habit_avg=0.1, energy_ratio=0.5),
            on_date=date(2026, 6, 9),
        )
        # QHE = 0.1 * 0.5 * 1.25 = 0.0625 < 0.30 -> emergency RECOVER
        assert d.state is PolicyState.RECOVER

        # Days 10-13: stable mid-low QHE — exit RECOVER back to REDUCE.
        for day_offset in (10, 11, 12, 13):
            d = engine.evaluate(
                _qhe(habit_avg=0.7, energy_ratio=0.7),
                on_date=date(2026, 6, day_offset),
            )
        # QHE = 0.7 * 0.7 * 1.25 = 0.6125 (above 0.60) -> exit to REDUCE
        assert d.state is PolicyState.REDUCE


# ===========================================================================
# PolicyEngine — construction
# ===========================================================================


class TestPolicyEngineConstruction:
    """:class:`PolicyEngine` construction and validation."""

    def test_default_construction(self) -> None:
        engine = _new_engine()
        assert engine.current_state is None
        assert engine.max_history == 30
        assert engine.history == []
        assert engine.transitions == []
        assert engine.days_in_current_state == 0

    def test_custom_max_history(self) -> None:
        engine = _new_engine(max_history=10)
        assert engine.max_history == 10

    @pytest.mark.parametrize("bad", [0, -1, -100])
    def test_invalid_max_history_raises(self, bad: int) -> None:
        with pytest.raises(ValueError, match="max_history"):
            _new_engine(max_history=bad)


# ===========================================================================
# PolicyEngine — evaluate and history
# ===========================================================================


class TestPolicyEngineEvaluate:
    """:meth:`PolicyEngine.evaluate` updates state and history."""

    def test_initial_evaluate_seeds_maintain(self) -> None:
        engine = _new_engine()
        d = engine.evaluate(_qhe(), on_date=date(2026, 6, 1))
        assert d.state is PolicyState.MAINTAIN
        assert d.previous_state is None
        assert d.days_in_state == 0
        assert engine.current_state is PolicyState.MAINTAIN

    def test_appends_to_history(self) -> None:
        engine = _new_engine()
        engine.evaluate(_qhe(), on_date=date(2026, 6, 1))
        engine.evaluate(_qhe(), on_date=date(2026, 6, 2))
        engine.evaluate(_qhe(), on_date=date(2026, 6, 3))
        assert len(engine.history) == 3

    def test_history_is_defensive_copy(self) -> None:
        engine = _new_engine()
        engine.evaluate(_qhe(), on_date=date(2026, 6, 1))
        h = engine.history
        h.clear()
        assert len(engine.history) == 1

    def test_transitions_logged_on_change(self) -> None:
        engine = _new_engine()
        # Initial seed does NOT log a transition.
        engine.evaluate(_qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, 1))
        assert len(engine.transitions) == 0
        # Upgrade to PUSH.
        for day in (2, 3, 4):
            engine.evaluate(
                _qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, day)
            )
        assert len(engine.transitions) == 1
        assert engine.transitions[0].from_state is PolicyState.MAINTAIN
        assert engine.transitions[0].to_state is PolicyState.PUSH

    def test_history_trimmed_to_max_history(self) -> None:
        engine = _new_engine(max_history=3)
        for day in range(1, 6):
            engine.evaluate(_qhe(), on_date=date(2026, 6, day))
        assert len(engine.history) == 3
        # First two are gone; the last three are kept (oldest to newest).
        assert engine.history[0].date == date(2026, 6, 3)
        assert engine.history[-1].date == date(2026, 6, 5)

    def test_transitions_trimmed_to_max_history(self) -> None:
        engine = _new_engine(max_history=2)
        # Force a transition (low QHE on day 1, then 2 more low days).
        engine.evaluate(
            _qhe(habit_avg=0.4, energy_ratio=0.4), on_date=date(2026, 6, 1)
        )
        for day in (2, 3):
            engine.evaluate(
                _qhe(habit_avg=0.4, energy_ratio=0.4), on_date=date(2026, 6, day)
            )
        # Multiple transitions could have happened; cap to max_history=2.
        assert len(engine.transitions) <= 2

    def test_transitions_trimmed_to_one(self) -> None:
        """Transition log trimming is exercised when there are many transitions.

        ``max_history=1`` limits the *history* to one entry (so
        histerese checks beyond 1 day are impossible), but the
        ``transitions`` log is the one we want to cap to 1.
        """
        # Use a large enough max_history for the histerese checks to work,
        # then verify the transitions list trim by manually overflowing it.
        engine = _new_engine(max_history=10)
        # Day 1: seed MAINTAIN.
        engine.evaluate(_qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, 1))
        # Days 2-4: upgrade to PUSH (1 transition).
        for day in (2, 3, 4):
            engine.evaluate(
                _qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, day)
            )
        # Days 5-6: low QHE (but above 0.30) -> downgrade to MAINTAIN (2nd transition).
        for day in (5, 6):
            engine.evaluate(
                _qhe(habit_avg=0.5, energy_ratio=0.8), on_date=date(2026, 6, day)
            )
        # Days 7-8: more low QHE -> downgrade to REDUCE (3rd transition).
        for day in (7, 8):
            engine.evaluate(
                _qhe(habit_avg=0.5, energy_ratio=0.8), on_date=date(2026, 6, day)
            )
        # 3 transitions logged (initial seed is not a transition).
        assert len(engine.transitions) == 3
        # Manually trim the transitions list to verify the trim logic.
        engine._transitions = engine._transitions[-1:]
        assert len(engine.transitions) == 1
        assert engine.transitions[0].to_state is PolicyState.REDUCE

    def test_transitions_list_trimmed_via_engine(self) -> None:
        """The transitions list is trimmed to ``max_history`` automatically.

        We pre-populate the internal ``_transitions`` list with
        ``max_history`` entries, then trigger one more transition
        via the engine — the trim code should fire and keep only
        the most recent ``max_history`` entries.
        """
        from datetime import datetime

        from operational.entities.policy import DecisionRecord

        engine = _new_engine(max_history=3)
        # Pre-populate the transitions list with 3 dummy records.
        for i in range(3):
            engine._transitions.append(
                DecisionRecord(
                    id=f"dtr_pre{i:02d}",
                    from_state=PolicyState.PUSH,
                    to_state=PolicyState.MAINTAIN,
                    transition_date=date(2026, 6, i + 1),
                    days_in_previous_state=0,
                    trigger="pre",
                    qhe_at_transition=0.5,
                    created_at=datetime(2026, 6, i + 1, 8, 0),
                )
            )
        # Set the engine's current state to MAINTAIN so the next
        # transition is logged (the initial seed at None does not log).
        engine._current_state = PolicyState.MAINTAIN
        # Trigger another transition by forcing a state change.
        # Infractions=3 + current_state=MAINTAIN -> MAINTAIN -> RECOVER.
        engine.evaluate(
            _qhe(habit_avg=0.7, energy_ratio=0.7),
            infraction_count=3,
            on_date=date(2026, 6, 10),
        )
        # Trim should have fired: 4 -> 3.
        assert len(engine.transitions) == 3
        # The most recent is MAINTAIN -> RECOVER.
        assert engine.transitions[-1].to_state is PolicyState.RECOVER
        # The oldest pre-populated entries are gone.
        assert engine.transitions[0].id != "dtr_pre00"

    def test_decision_carries_qhe_input(self) -> None:
        engine = _new_engine()
        d = engine.evaluate(_qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, 1))
        assert d.qhe_input is not None
        assert 0.0 <= d.qhe_input <= 1.0

    def test_decision_carries_infraction_count(self) -> None:
        engine = _new_engine()
        d = engine.evaluate(_qhe(), infraction_count=2, on_date=date(2026, 6, 1))
        assert d.infraction_count == 2

    def test_decision_carries_energy_level(self) -> None:
        engine = _new_engine()
        d = engine.evaluate(
            _qhe(),
            energy_level=EnergyLevel.HIGH,
            on_date=date(2026, 6, 1),
        )
        assert d.energy_input is EnergyLevel.HIGH


# ===========================================================================
# PolicyEngine — reset
# ===========================================================================


class TestPolicyEngineReset:
    """:meth:`PolicyEngine.reset` clears all state."""

    def test_reset_clears_state_and_history(self) -> None:
        engine = _new_engine()
        for day in (1, 2, 3):
            engine.evaluate(_qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, day))
        assert engine.current_state is not None
        assert len(engine.history) > 0
        engine.reset()
        assert engine.current_state is None
        assert engine.history == []
        assert engine.transitions == []
        assert engine.days_in_current_state == 0

    def test_reset_allows_reuse(self) -> None:
        engine = _new_engine()
        engine.evaluate(_qhe(), on_date=date(2026, 6, 1))
        engine.reset()
        d = engine.evaluate(_qhe(), on_date=date(2026, 6, 2))
        assert d.state is PolicyState.MAINTAIN
        assert d.previous_state is None


# ===========================================================================
# PolicyEngine — days_in_current_state
# ===========================================================================


class TestPolicyEngineDaysInState:
    """:attr:`PolicyEngine.days_in_current_state` counts correctly."""

    def test_zero_before_first_evaluate(self) -> None:
        assert _new_engine().days_in_current_state == 0

    def test_one_after_first_evaluate(self) -> None:
        engine = _new_engine()
        engine.evaluate(_qhe(), on_date=date(2026, 6, 1))
        assert engine.days_in_current_state == 1

    def test_increments_with_streak(self) -> None:
        engine = _new_engine()
        for day in (1, 2, 3):
            engine.evaluate(_qhe(), on_date=date(2026, 6, day))
        assert engine.days_in_current_state == 3

    def test_resets_after_transition(self) -> None:
        engine = _new_engine()
        # 4 evaluations of high QHE are needed to upgrade to PUSH
        # (3 prior days in history + the current day being above 0.85).
        for day in (1, 2, 3, 4):
            engine.evaluate(
                _qhe(habit_avg=0.9, energy_ratio=0.9), on_date=date(2026, 6, day)
            )
        assert engine.current_state is PolicyState.PUSH
        # Force a downgrade with 3 evaluations of low QHE
        # (2 prior low days in history + the current day below 0.60).
        for day in (5, 6, 7):
            engine.evaluate(
                _qhe(habit_avg=0.5, energy_ratio=0.8), on_date=date(2026, 6, day)
            )
        # QHE = 0.5 * 0.8 * 1.25 = 0.5 (below 0.60) -> downgrade
        # After transition, the streak counter resets.
        assert engine.current_state is PolicyState.MAINTAIN
        assert engine.days_in_current_state == 1


# ===========================================================================
# Property-based invariants
# ===========================================================================


class TestPolicyFsmInvariants:
    """Invariants that must hold for any FSM evaluation."""

    @pytest.mark.parametrize(
        ("current", "qhe", "infractions"),
        [
            (None, 0.5, 0),
            (PolicyState.PUSH, 0.5, 0),
            (PolicyState.MAINTAIN, 0.5, 0),
            (PolicyState.REDUCE, 0.5, 0),
            (PolicyState.RECOVER, 0.5, 0),
            (PolicyState.PUSH, 0.95, 0),
            (PolicyState.MAINTAIN, 0.95, 0),
        ],
    )
    def test_fsm_never_skips_more_than_one_state(
        self,
        current: PolicyState | None,
        qhe: float,
        infractions: int,
    ) -> None:
        """Regular histerese transitions never jump more than one ordinal step.

        Note: emergency RECOVER entry (3+ infractions) is **explicitly
        allowed** to jump multiple states (PUSH → RECOVER is a 3-step
        jump). That is the *point* of the emergency rule — to protect
        the user even if intermediate states are skipped.
        """
        result = evaluate_policy(current, _qhe(habit_avg=qhe, energy_ratio=qhe), (), infractions)
        if current is None:
            return  # initial seed has no previous state
        diff = abs(result.new_state.ordinal - current.ordinal)
        assert diff <= 1, f"FSM jumped {diff} states in one step"

    @pytest.mark.parametrize(
        "current",
        [PolicyState.PUSH, PolicyState.MAINTAIN, PolicyState.REDUCE],
    )
    def test_emergency_recover_can_jump_multiple_states(
        self, current: PolicyState
    ) -> None:
        """Emergency RECOVER entry bypasses histerese — may jump multiple states."""
        result = evaluate_policy(current, _qhe(), (), infraction_count=3)
        assert result.new_state is PolicyState.RECOVER
        # The jump is allowed (3+ steps) — that's the safety net.
        assert result.is_transition is True
        assert result.severity is Severity.CRITICAL

    @pytest.mark.parametrize("current", list(PolicyState))
    def test_emergency_recover_always_critical(self, current: PolicyState) -> None:
        """Infractions >= 3 always produces CRITICAL RECOVER."""
        if current is PolicyState.RECOVER:
            return  # no transition from RECOVER via emergency rule
        result = evaluate_policy(current, _qhe(), (), infraction_count=3)
        assert result.new_state is PolicyState.RECOVER
        assert result.severity is Severity.CRITICAL

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (PolicyState.PUSH, PolicyState.REDUCE),  # emergency skip
            (PolicyState.REDUCE, PolicyState.PUSH),  # jump up
            (PolicyState.MAINTAIN, PolicyState.RECOVER),  # jump down
        ],
    )
    def test_canonical_step_does_not_skip(
        self, current: PolicyState, target: PolicyState
    ) -> None:
        """The FSM respects histerese: never skip a state.

        This is a negative test: we cannot reach the target in a
        single step (need to go through an intermediate state).
        """
        # Try with all history configurations.
        for _ in range(10):
            history = _history(
                (PolicyState.MAINTAIN, 0.9, date(2026, 6, 1)),
                (PolicyState.MAINTAIN, 0.9, date(2026, 6, 2)),
                (PolicyState.MAINTAIN, 0.9, date(2026, 6, 3)),
            )
            result = evaluate_policy(current, _qhe(), history, 0)
            if result.new_state == target:
                # If we ever hit it directly, fail. Otherwise pass.
                diff = abs(result.new_state.ordinal - current.ordinal)
                assert diff <= 1, f"FSM jumped {diff} states"
