"""Unit tests for :mod:`operational.entities.pomodoro`.

Coverage:

* :class:`PomodoroConfig` — construction, bounds, invariants, factory.
* :class:`PomodoroRound` — construction, pause accounting, computed
  duration.
* :class:`PomodoroSession` — construction, aggregate computations,
  state-machine helpers, JSON roundtrip.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from operational.entities.pomodoro import (
    PomodoroConfig,
    PomodoroRound,
    PomodoroSession,
)
from operational.enums import PomodoroState

from tests.unit.entities._roundtrip import roundtrip

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TS: datetime = datetime(2026, 6, 7, 9, 0, 0)
"""A fixed timestamp used for ``started_at``/``created_at``."""


def _make_config(**overrides: Any) -> PomodoroConfig:
    """Return a minimal but valid :class:`PomodoroConfig` with overrides."""
    base: dict[str, Any] = {
        "id": "pmo_focus_deep",
        "name": "Deep Focus",
        "work_minutes": 50,
        "break_minutes": 10,
        "long_break_minutes": 30,
        "rounds_min": 3,
        "rounds_max": 4,
        "created_at": TS,
    }
    base.update(overrides)
    return PomodoroConfig(**base)


def _make_round(**overrides: Any) -> PomodoroRound:
    """Return a minimal but valid :class:`PomodoroRound` with overrides."""
    base: dict[str, Any] = {
        "id": "pmor_session_001_round_1",
        "round_number": 1,
        "state": PomodoroState.WORK,
        "started_at": TS,
        "completed_at": TS + timedelta(minutes=50),
    }
    base.update(overrides)
    return PomodoroRound(**base)


def _make_session(**overrides: Any) -> PomodoroSession:
    """Return a minimal but valid :class:`PomodoroSession` with overrides."""
    base: dict[str, Any] = {
        "id": "pms_2026_06_07_morning",
        "config_id": "pmo_focus_deep",
        "state": PomodoroState.WORK,
        "started_at": TS,
    }
    base.update(overrides)
    return PomodoroSession(**base)


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


class TestModuleSurface:
    """The ``pomodoro`` module exposes a stable public API."""

    def test_all_is_complete(self) -> None:
        import operational.entities.pomodoro as mod

        assert {"PomodoroConfig", "PomodoroRound", "PomodoroSession"}.issubset(
            set(mod.__all__),
        )

    def test_all_names_importable(self) -> None:
        import operational.entities.pomodoro as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"


# ===========================================================================
# PomodoroConfig
# ===========================================================================


class TestPomodoroConfigConstruction:
    """Happy-path construction of :class:`PomodoroConfig`."""

    def test_create_pomodoro_config_minimal(self) -> None:
        c = _make_config()
        assert c.id == "pmo_focus_deep"
        assert c.name == "Deep Focus"
        assert c.work_minutes == 50
        assert c.break_minutes == 10
        assert c.long_break_minutes == 30
        assert c.rounds_min == 3
        assert c.rounds_max == 4
        assert c.routine_id is None
        assert c.created_at == TS

    def test_config_with_routine_link(self) -> None:
        c = _make_config(routine_id="rou_focus_block")
        assert c.routine_id == "rou_focus_block"

    def test_config_strips_whitespace_in_name(self) -> None:
        c = _make_config(name="  Deep Focus  ")
        assert c.name == "Deep Focus"

    def test_config_frozen(self) -> None:
        c = _make_config()
        with pytest.raises(ValidationError):
            c.work_minutes = 99  # type: ignore[misc]

    def test_config_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            _make_config(bogus="x")  # type: ignore[call-arg]

    @pytest.mark.parametrize("bad_id", ["ab_x", "toolong_x", "PMO_x", "pmo_"])
    def test_config_rejects_bad_ueid(self, bad_id: str) -> None:
        with pytest.raises(ValidationError):
            _make_config(id=bad_id)


class TestPomodoroConfigBounds:
    """Numeric bounds enforced by Pydantic ``Field`` constraints."""

    @pytest.mark.parametrize("value", [9, 0, -1, 121, 200])
    def test_config_rejects_work_minutes_out_of_bounds(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_config(work_minutes=value)

    @pytest.mark.parametrize("value", [20, 50, 100, 120])
    def test_config_accepts_valid_work_minutes(self, value: int) -> None:
        """``work_minutes`` accepts any value in ``[10, 120]``.

        Tested with values that keep ``break_minutes < work_minutes`` valid.
        """
        c = _make_config(work_minutes=value, break_minutes=1)
        assert c.work_minutes == value

    @pytest.mark.parametrize("value", [0, -1, 31, 100])
    def test_config_rejects_break_minutes_out_of_bounds(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_config(break_minutes=value)

    @pytest.mark.parametrize("value", [9, 0, -1, 61, 200])
    def test_config_rejects_long_break_out_of_bounds(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_config(long_break_minutes=value)

    @pytest.mark.parametrize("value", [0, -1, 11, 100])
    def test_config_rejects_rounds_min_out_of_bounds(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_config(rounds_min=value)

    @pytest.mark.parametrize("value", [0, -1, 11, 100])
    def test_config_rejects_rounds_max_out_of_bounds(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_config(rounds_max=value)

    def test_config_accepts_minimum_values(self) -> None:
        """Lowest legal values across all fields."""
        c = _make_config(
            work_minutes=10, break_minutes=1, long_break_minutes=10,
            rounds_min=1, rounds_max=1,
        )
        assert c.work_minutes == 10
        assert c.break_minutes == 1
        assert c.long_break_minutes == 10
        assert c.rounds_min == 1
        assert c.rounds_max == 1

    def test_config_accepts_maximum_values(self) -> None:
        """Highest legal values across all fields."""
        c = _make_config(
            work_minutes=120, break_minutes=30, long_break_minutes=60,
            rounds_min=10, rounds_max=10,
        )
        assert c.work_minutes == 120
        assert c.break_minutes == 30
        assert c.long_break_minutes == 60
        assert c.rounds_min == 10
        assert c.rounds_max == 10


class TestPomodoroConfigValidators:
    """Cross-field invariants in :class:`PomodoroConfig`."""

    def test_pomodoro_config_validates_rounds_order(self) -> None:
        """rounds_max < rounds_min is rejected."""
        with pytest.raises(ValidationError) as exc:
            _make_config(rounds_min=4, rounds_max=3)
        assert "rounds_max" in str(exc.value)

    def test_config_accepts_equal_rounds_min_max(self) -> None:
        """rounds_max == rounds_min is valid (fixed-count session)."""
        c = _make_config(rounds_min=3, rounds_max=3)
        assert c.rounds_min == c.rounds_max == 3

    def test_pomodoro_config_validates_break_less_than_work(self) -> None:
        """Break >= work is rejected."""
        with pytest.raises(ValidationError) as exc:
            _make_config(work_minutes=30, break_minutes=30)
        assert "break_minutes" in str(exc.value)

    def test_config_rejects_break_greater_than_work(self) -> None:
        with pytest.raises(ValidationError):
            _make_config(work_minutes=20, break_minutes=25)

    def test_config_rejects_break_equal_to_work(self) -> None:
        with pytest.raises(ValidationError):
            _make_config(work_minutes=25, break_minutes=25)


class TestPomodoroConfigFromPavDefaults:
    """``from_pav_defaults`` factory semantics."""

    def test_pomodoro_config_from_pav_defaults(self) -> None:
        c = PomodoroConfig.from_pav_defaults("Deep Focus")
        # Defaults from PAVConstants.DEFAULT
        assert c.work_minutes == 50
        assert c.break_minutes == 10
        assert c.long_break_minutes == 30
        assert c.rounds_min == 3
        assert c.rounds_max == 4
        assert c.name == "Deep Focus"
        assert c.id.startswith("pmo_")
        assert c.created_at <= datetime.now(tz=UTC)

    def test_from_pav_defaults_generates_unique_ids(self) -> None:
        """Two calls produce two distinct UEIDs."""
        a = PomodoroConfig.from_pav_defaults("A")
        b = PomodoroConfig.from_pav_defaults("B")
        assert a.id != b.id

    def test_from_pav_defaults_accepts_overrides(self) -> None:
        c = PomodoroConfig.from_pav_defaults(
            "Short Bursts", work_minutes=25, break_minutes=5,
            rounds_min=4, rounds_max=6,
        )
        assert c.work_minutes == 25
        assert c.break_minutes == 5
        assert c.rounds_min == 4
        assert c.rounds_max == 6

    def test_from_pav_defaults_rejects_bad_override(self) -> None:
        """``work_minutes=5`` violates the ``ge=10`` constraint."""
        with pytest.raises(ValidationError):
            PomodoroConfig.from_pav_defaults("Bad", work_minutes=5)

    def test_from_pav_defaults_rejects_unknown_override(self) -> None:
        with pytest.raises(ValidationError):
            PomodoroConfig.from_pav_defaults("Bad", unknown_field=1)  # type: ignore[call-arg]

    def test_from_pav_defaults_id_has_ueid_pattern(self) -> None:
        import re

        c = PomodoroConfig.from_pav_defaults("X")
        assert re.match(r"^[a-z]{3,5}_[a-z0-9_]+$", c.id)


class TestPomodoroConfigComputedFields:
    """Computed properties on :class:`PomodoroConfig`."""

    def test_session_duration_minutes(self) -> None:
        """3 work + 2 short + 1 long break at 4 rounds max."""
        c = _make_config(
            work_minutes=50, break_minutes=10, long_break_minutes=30,
            rounds_max=4,
        )
        # 4*50 + 3*10 + 30 = 260 minutes
        assert c.session_duration_minutes == 260

    def test_session_duration_minutes_one_round(self) -> None:
        c = _make_config(
            work_minutes=25, break_minutes=5, long_break_minutes=15,
            rounds_min=1, rounds_max=1,
        )
        # 1*25 + 0*5 + 15 = 40
        assert c.session_duration_minutes == 40

    def test_session_duration_appears_in_model_dump(self) -> None:
        c = _make_config()
        data = c.model_dump()
        assert "session_duration_minutes" in data
        assert data["session_duration_minutes"] == 260


# ===========================================================================
# PomodoroRound
# ===========================================================================


class TestPomodoroRoundConstruction:
    """Happy-path construction of :class:`PomodoroRound`."""

    def test_create_pomodoro_round(self) -> None:
        r = _make_round()
        assert r.id == "pmor_session_001_round_1"
        assert r.round_number == 1
        assert r.state is PomodoroState.WORK
        assert r.started_at == TS
        assert r.completed_at == TS + timedelta(minutes=50)
        assert r.paused_duration_seconds == 0

    def test_round_defaults(self) -> None:
        """started_at/completed_at default to None for new rounds."""
        r = PomodoroRound(
            id="pmor_x",
            round_number=1,
            state=PomodoroState.IDLE,
        )
        assert r.started_at is None
        assert r.completed_at is None
        assert r.paused_duration_seconds == 0

    def test_round_frozen(self) -> None:
        r = _make_round()
        with pytest.raises(ValidationError):
            r.state = PomodoroState.BREAK  # type: ignore[misc]

    def test_round_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            _make_round(bogus="x")  # type: ignore[call-arg]

    @pytest.mark.parametrize("value", [0, -1, 21, 100])
    def test_round_rejects_bad_round_number(self, value: int) -> None:
        with pytest.raises(ValidationError):
            _make_round(round_number=value)

    @pytest.mark.parametrize("state", list(PomodoroState))
    def test_round_accepts_all_states(self, state: PomodoroState) -> None:
        r = _make_round(state=state)
        assert r.state is state


class TestPomodoroRoundComputedFields:
    """Computed properties on :class:`PomodoroRound`."""

    def test_pomodoro_round_actual_duration_minutes(self) -> None:
        r = _make_round(
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 50),
        )
        assert r.actual_duration_minutes == 50.0

    def test_round_actual_duration_with_pause(self) -> None:
        r = _make_round(
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 55),
            paused_duration_seconds=300,  # 5 min paused
        )
        assert r.actual_duration_minutes == 50.0

    def test_round_actual_duration_partial(self) -> None:
        r = _make_round(
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 25),
        )
        assert r.actual_duration_minutes == 25.0

    def test_round_actual_duration_no_timestamps(self) -> None:
        r = PomodoroRound(
            id="pmor_x",
            round_number=1,
            state=PomodoroState.IDLE,
        )
        assert r.actual_duration_minutes == 0.0

    def test_round_actual_duration_only_started(self) -> None:
        r = PomodoroRound(
            id="pmor_x",
            round_number=1,
            state=PomodoroState.WORK,
            started_at=TS,
        )
        assert r.actual_duration_minutes == 0.0

    def test_round_paused_duration_validation(self) -> None:
        with pytest.raises(ValidationError):
            _make_round(paused_duration_seconds=-1)

    def test_round_paused_duration_zero(self) -> None:
        r = _make_round(paused_duration_seconds=0)
        assert r.paused_duration_seconds == 0

    def test_round_is_focus_when_work(self) -> None:
        r = _make_round(state=PomodoroState.WORK)
        assert r.is_focus_round is True
        assert r.is_break_round is False

    def test_round_is_focus_when_complete(self) -> None:
        r = _make_round(state=PomodoroState.COMPLETE)
        assert r.is_focus_round is True
        assert r.is_break_round is False

    def test_round_is_break_short(self) -> None:
        r = _make_round(state=PomodoroState.BREAK)
        assert r.is_focus_round is False
        assert r.is_break_round is True

    def test_round_is_break_long(self) -> None:
        r = _make_round(state=PomodoroState.LONG_BREAK)
        assert r.is_focus_round is False
        assert r.is_break_round is True

    def test_round_is_neither_when_paused(self) -> None:
        r = _make_round(state=PomodoroState.PAUSED)
        assert r.is_focus_round is False
        assert r.is_break_round is False

    def test_round_is_neither_when_idle(self) -> None:
        r = _make_round(state=PomodoroState.IDLE)
        assert r.is_focus_round is False
        assert r.is_break_round is False

    def test_round_is_neither_when_skipped(self) -> None:
        r = _make_round(state=PomodoroState.SKIPPED)
        assert r.is_focus_round is False
        assert r.is_break_round is False

    def test_completed_before_started_raises(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _make_round(
                started_at=datetime(2026, 6, 7, 10, 0),
                completed_at=datetime(2026, 6, 7, 9, 0),
            )
        assert "completed_at" in str(exc.value)


# ===========================================================================
# PomodoroSession
# ===========================================================================


class TestPomodoroSessionConstruction:
    """Happy-path construction of :class:`PomodoroSession`."""

    def test_create_pomodoro_session_empty(self) -> None:
        s = _make_session()
        assert s.id == "pms_2026_06_07_morning"
        assert s.config_id == "pmo_focus_deep"
        assert s.state is PomodoroState.WORK
        assert s.rounds == []
        assert s.started_at == TS
        assert s.completed_at is None

    def test_session_with_rounds(self) -> None:
        r1 = _make_round()
        s = _make_session(rounds=[r1])
        assert len(s.rounds) == 1
        assert s.rounds[0].id == r1.id

    def test_session_frozen(self) -> None:
        s = _make_session()
        with pytest.raises(ValidationError):
            s.state = PomodoroState.PAUSED  # type: ignore[misc]

    def test_session_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            _make_session(bogus="x")  # type: ignore[call-arg]

    def test_session_rejects_non_terminal_with_completed_at(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _make_session(
                state=PomodoroState.WORK,
                completed_at=TS + timedelta(hours=1),
            )
        assert "terminal" in str(exc.value)

    def test_session_accepts_terminal_state_with_completed_at(self) -> None:
        s = _make_session(
            state=PomodoroState.COMPLETE,
            completed_at=TS + timedelta(hours=4),
        )
        assert s.completed_at is not None

    def test_session_completed_at_before_started_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_session(
                state=PomodoroState.COMPLETE,
                completed_at=TS - timedelta(hours=1),
            )


class TestPomodoroSessionFocusAndBreak:
    """``total_focus_minutes`` and ``total_break_minutes`` aggregations."""

    def test_pomodoro_session_total_focus_minutes(self) -> None:
        r1 = _make_round(
            state=PomodoroState.COMPLETE,
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 50),
        )
        r2 = _make_round(
            round_number=2, id="pmor_2",
            state=PomodoroState.COMPLETE,
            started_at=datetime(2026, 6, 7, 10, 0),
            completed_at=datetime(2026, 6, 7, 10, 50),
        )
        s = _make_session(rounds=[r1, r2])
        assert s.total_focus_minutes == 100

    def test_pomodoro_session_total_break_minutes(self) -> None:
        r1 = _make_round(
            state=PomodoroState.BREAK,
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 10),
        )
        r2 = _make_round(
            round_number=2, id="pmor_2",
            state=PomodoroState.LONG_BREAK,
            started_at=datetime(2026, 6, 7, 9, 10),
            completed_at=datetime(2026, 6, 7, 9, 40),
        )
        s = _make_session(rounds=[r1, r2])
        assert s.total_break_minutes == 40

    def test_session_total_focus_includes_work_state(self) -> None:
        """In-progress WORK round is also counted as focus."""
        r = _make_round(state=PomodoroState.WORK)
        s = _make_session(rounds=[r])
        assert s.total_focus_minutes == 50

    def test_session_total_focus_excludes_break_state(self) -> None:
        r = _make_round(state=PomodoroState.BREAK)
        s = _make_session(rounds=[r])
        assert s.total_focus_minutes == 0

    def test_session_total_break_excludes_work_state(self) -> None:
        r = _make_round(state=PomodoroState.WORK)
        s = _make_session(rounds=[r])
        assert s.total_break_minutes == 0

    def test_session_total_minutes(self) -> None:
        """total_minutes = total_focus + total_break."""
        work_round = _make_round(
            state=PomodoroState.WORK,
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 50),
        )
        break_round = _make_round(
            round_number=2, id="pmor_break",
            state=PomodoroState.BREAK,
            started_at=datetime(2026, 6, 7, 9, 50),
            completed_at=datetime(2026, 6, 7, 10, 0),
        )
        s = _make_session(rounds=[work_round, break_round])
        assert s.total_focus_minutes == 50
        assert s.total_break_minutes == 10
        assert s.total_minutes == 60

    def test_session_empty_rounds_totals(self) -> None:
        s = _make_session()
        assert s.total_focus_minutes == 0
        assert s.total_break_minutes == 0
        assert s.total_minutes == 0


class TestPomodoroSessionCompletionRatio:
    """``completion_ratio`` is the fraction of rounds in COMPLETE state."""

    def test_session_completion_ratio_empty(self) -> None:
        s = _make_session()
        assert s.completion_ratio == 0.0

    def test_session_completion_ratio_all_complete(self) -> None:
        rounds = [
            _make_round(
                round_number=i, id=f"pmor_{i}",
                state=PomodoroState.COMPLETE,
            )
            for i in range(1, 4)
        ]
        s = _make_session(rounds=rounds)
        assert s.completion_ratio == 1.0

    def test_session_completion_ratio_half_complete(self) -> None:
        rounds = [
            _make_round(
                round_number=1, id="pmor_1", state=PomodoroState.COMPLETE,
            ),
            _make_round(
                round_number=2, id="pmor_2", state=PomodoroState.WORK,
            ),
        ]
        s = _make_session(rounds=rounds)
        assert s.completion_ratio == 0.5

    def test_session_completion_ratio_none_complete(self) -> None:
        rounds = [
            _make_round(
                round_number=1, id="pmor_1", state=PomodoroState.WORK,
            ),
            _make_round(
                round_number=2, id="pmor_2", state=PomodoroState.SKIPPED,
            ),
        ]
        s = _make_session(rounds=rounds)
        assert s.completion_ratio == 0.0


class TestPomodoroSessionFocusRatio:
    """``focus_ratio`` is the share of focus minutes within total minutes."""

    def test_focus_ratio_pure_focus(self) -> None:
        r = _make_round(
            state=PomodoroState.WORK,
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 50),
        )
        s = _make_session(rounds=[r])
        assert s.focus_ratio == 1.0

    def test_focus_ratio_half(self) -> None:
        work_round = _make_round(
            state=PomodoroState.WORK,
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 25),
        )
        break_round = _make_round(
            round_number=2, id="pmor_break",
            state=PomodoroState.BREAK,
            started_at=datetime(2026, 6, 7, 9, 25),
            completed_at=datetime(2026, 6, 7, 9, 50),
        )
        s = _make_session(rounds=[work_round, break_round])
        assert s.focus_ratio == 0.5

    def test_focus_ratio_empty_session(self) -> None:
        s = _make_session()
        assert s.focus_ratio == 0.0


class TestPomodoroSessionStateMachine:
    """``PomodoroState.can_transition_to`` is exercised via session state."""

    def test_idle_can_transition_to_work(self) -> None:
        assert PomodoroState.IDLE.can_transition_to(PomodoroState.WORK) is True

    def test_work_can_transition_to_break(self) -> None:
        assert PomodoroState.WORK.can_transition_to(PomodoroState.BREAK) is True

    def test_work_can_transition_to_skipped(self) -> None:
        assert PomodoroState.WORK.can_transition_to(PomodoroState.SKIPPED) is True

    def test_work_cannot_jump_to_complete(self) -> None:
        """WORK -> COMPLETE is not a valid single transition."""
        assert PomodoroState.WORK.can_transition_to(PomodoroState.COMPLETE) is False

    def test_long_break_can_transition_to_complete(self) -> None:
        assert (
            PomodoroState.LONG_BREAK.can_transition_to(PomodoroState.COMPLETE)
            is True
        )

    def test_complete_can_transition_to_idle(self) -> None:
        assert (
            PomodoroState.COMPLETE.can_transition_to(PomodoroState.IDLE) is True
        )

    def test_terminal_states(self) -> None:
        """IDLE, SKIPPED, COMPLETE are terminal."""
        for s in (PomodoroState.IDLE, PomodoroState.SKIPPED, PomodoroState.COMPLETE):
            assert s.is_terminal is True

    def test_active_states(self) -> None:
        """WORK, BREAK, LONG_BREAK are active."""
        for s in (
            PomodoroState.WORK, PomodoroState.BREAK, PomodoroState.LONG_BREAK,
        ):
            assert s.is_active is True

    def test_paused_state(self) -> None:
        assert PomodoroState.PAUSED.is_paused is True
        assert PomodoroState.WORK.is_paused is False

    def test_session_state_transitions_through_lifecycle(self) -> None:
        """End-to-end: IDLE -> WORK -> BREAK -> ... -> LONG_BREAK -> COMPLETE.

        Note: ``WORK -> LONG_BREAK`` is **forbidden** by the state machine;
        a long break is only reached from ``BREAK`` (every Nth cycle).
        """
        chain = [
            (PomodoroState.IDLE, PomodoroState.WORK),
            (PomodoroState.WORK, PomodoroState.BREAK),
            (PomodoroState.BREAK, PomodoroState.WORK),
            (PomodoroState.WORK, PomodoroState.BREAK),
            (PomodoroState.BREAK, PomodoroState.LONG_BREAK),
            (PomodoroState.LONG_BREAK, PomodoroState.COMPLETE),
            (PomodoroState.COMPLETE, PomodoroState.IDLE),
        ]
        for src, dst in chain:
            assert src.can_transition_to(dst) is True, (
                f"{src.value} should be able to transition to {dst.value}"
            )


class TestPomodoroSessionJsonRoundtrip:
    """JSON encode/decode preserves the entity and its computed values."""

    def test_json_roundtrip_config(self) -> None:
        c = _make_config(routine_id="rou_focus_block")
        decoded: PomodoroConfig = roundtrip(c)
        assert decoded == c
        assert decoded.session_duration_minutes == c.session_duration_minutes

    def test_json_roundtrip_round(self) -> None:
        r = _make_round(
            state=PomodoroState.COMPLETE,
            started_at=datetime(2026, 6, 7, 9, 0),
            completed_at=datetime(2026, 6, 7, 9, 50),
        )
        decoded: PomodoroRound = roundtrip(r)
        assert decoded == r
        assert decoded.actual_duration_minutes == r.actual_duration_minutes

    def test_json_roundtrip_session(self) -> None:
        rounds = [
            _make_round(
                round_number=i, id=f"pmor_{i}",
                state=PomodoroState.COMPLETE,
                started_at=datetime(2026, 6, 7, 9, 0) + timedelta(hours=i - 1),
                completed_at=datetime(2026, 6, 7, 9, 50) + timedelta(hours=i - 1),
            )
            for i in range(1, 4)
        ]
        s = _make_session(
            rounds=rounds,
            state=PomodoroState.COMPLETE,
            completed_at=datetime(2026, 6, 7, 12, 0),
        )
        decoded: PomodoroSession = roundtrip(s)
        assert decoded == s
        assert decoded.total_focus_minutes == s.total_focus_minutes
        assert decoded.total_break_minutes == s.total_break_minutes
        assert decoded.completion_ratio == s.completion_ratio
        assert decoded.focus_ratio == s.focus_ratio

    def test_json_payload_state_as_string(self) -> None:
        s = _make_session()
        payload = json.loads(s.model_dump_json())
        assert payload["state"] == "WORK"
        assert payload["config_id"] == "pmo_focus_deep"

    def test_json_computed_fields_included(self) -> None:
        c = _make_config()
        payload = json.loads(c.model_dump_json())
        assert "session_duration_minutes" in payload


# ---------------------------------------------------------------------------
# Deep copy
# ---------------------------------------------------------------------------


class TestEntityDeepCopy:
    """Pydantic models survive deepcopy."""

    def test_config_deepcopy(self) -> None:
        c = _make_config()
        assert deepcopy(c) == c

    def test_round_deepcopy(self) -> None:
        r = _make_round()
        assert deepcopy(r) == r

    def test_session_deepcopy(self) -> None:
        s = _make_session(rounds=[_make_round()])
        clone = deepcopy(s)
        assert clone == s
        assert len(clone.rounds) == 1
