"""Unit tests for :mod:`operational.entities.routine.RoutineLog`."""
from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from operational.entities.routine import RoutineLog
from operational.enums import Period, RoutineType


def _make_log(
    *,
    log_id: str = "rlog_test_001",
    routine_id: str = "rou_acordar",
    block_id: str | None = "tbl_manha_focus",
    date_: date = date(2026, 6, 7),
    period: Period = Period.MANHA,
    routine_type: RoutineType = RoutineType.ENTRY,
    text: str = "Acordei bem, 7h de sono, energia 9/10",
    energia_nivel: int | None = 9,
    foco_nivel: int | None = 8,
    humor: int | None = 4,
) -> RoutineLog:
    return RoutineLog(
        id=log_id,
        routine_id=routine_id,
        block_id=block_id,
        date=date_,
        period=period,
        routine_type=routine_type,
        text=text,
        energia_nivel=energia_nivel,
        foco_nivel=foco_nivel,
        humor=humor,
        created_at=datetime(2026, 6, 7, 4, 5),
    )


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestRoutineLogCreation:
    """Tests for creating RoutineLog entities."""

    def test_minimal_creation(self) -> None:
        log = _make_log()
        assert log.id == "rlog_test_001"
        assert log.routine_id == "rou_acordar"
        assert log.block_id == "tbl_manha_focus"
        assert log.date == date(2026, 6, 7)
        assert log.period == Period.MANHA
        assert log.routine_type == RoutineType.ENTRY
        assert log.text == "Acordei bem, 7h de sono, energia 9/10"
        assert log.energia_nivel == 9
        assert log.foco_nivel == 8
        assert log.humor == 4

    def test_block_id_optional(self) -> None:
        log = _make_log(block_id=None)
        assert log.block_id is None

    def test_all_metrics_optional(self) -> None:
        log = _make_log(energia_nivel=None, foco_nivel=None, humor=None)
        assert log.energia_nivel is None
        assert log.foco_nivel is None
        assert log.humor is None


# ---------------------------------------------------------------------------
# Computed Properties
# ---------------------------------------------------------------------------


class TestRoutineLogProperties:
    """Tests for computed properties."""

    def test_is_entry_routine_true(self) -> None:
        log = _make_log(routine_type=RoutineType.ENTRY)
        assert log.is_entry_routine is True
        assert log.is_exit_routine is False

    def test_is_exit_routine_true(self) -> None:
        log = _make_log(routine_type=RoutineType.EXIT)
        assert log.is_exit_routine is True
        assert log.is_entry_routine is False

    def test_core_routine_neither(self) -> None:
        log = _make_log(routine_type=RoutineType.CORE)
        assert log.is_entry_routine is False
        assert log.is_exit_routine is False

    def test_transition_routine_neither(self) -> None:
        log = _make_log(routine_type=RoutineType.TRANSITION)
        assert log.is_entry_routine is False
        assert log.is_exit_routine is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestRoutineLogValidation:
    """Tests for validation rules."""

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValidationError, match="text"):
            _make_log(text="")

    def test_long_text_rejected(self) -> None:
        with pytest.raises(ValidationError, match="text"):
            _make_log(text="x" * 2001)

    def test_energia_nivel_range_low(self) -> None:
        with pytest.raises(ValidationError, match="energia_nivel"):
            _make_log(energia_nivel=0)

    def test_energia_nivel_range_high(self) -> None:
        with pytest.raises(ValidationError, match="energia_nivel"):
            _make_log(energia_nivel=11)

    def test_foco_nivel_range_low(self) -> None:
        with pytest.raises(ValidationError, match="foco_nivel"):
            _make_log(foco_nivel=0)

    def test_foco_nivel_range_high(self) -> None:
        with pytest.raises(ValidationError, match="foco_nivel"):
            _make_log(foco_nivel=11)

    def test_humor_range_low(self) -> None:
        with pytest.raises(ValidationError, match="humor"):
            _make_log(humor=0)

    def test_humor_range_high(self) -> None:
        with pytest.raises(ValidationError, match="humor"):
            _make_log(humor=6)

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            RoutineLog(
                id="rlog_x",
                routine_id="rou_x",
                date=date(2026, 6, 7),
                period=Period.MANHA,
                routine_type=RoutineType.ENTRY,
                text="x",
                created_at=datetime.now(),
                extra_field="should fail",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestRoutineLogImmutability:
    """Tests for frozen model behavior."""

    def test_cannot_mutate_text(self) -> None:
        log = _make_log()
        with pytest.raises((ValidationError, AttributeError)):
            log.text = "new text"  # type: ignore[misc]

    def test_cannot_mutate_energia(self) -> None:
        log = _make_log()
        with pytest.raises((ValidationError, AttributeError)):
            log.energia_nivel = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# JSON roundtrip
# ---------------------------------------------------------------------------


class TestRoutineLogJsonRoundtrip:
    """Tests for JSON serialization."""

    def test_json_roundtrip(self) -> None:
        original = _make_log(
            log_id="rlog_rt_001",
            text="Salada + 2 marmitas para amanhã",
            routine_type=RoutineType.EXIT,
        )
        json_str = original.model_dump_json(exclude={"is_entry_routine", "is_exit_routine"})
        restored = RoutineLog.model_validate_json(json_str)
        assert restored == original
        assert restored.text == "Salada + 2 marmitas para amanhã"
