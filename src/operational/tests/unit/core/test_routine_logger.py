"""Unit tests for :mod:`operational.core.routine_logger`."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from operational.core.routine_logger import (
    RoutineLogger,
    build_ajuste_fino,
    build_routine_log,
    filter_ajustes_finos_by_date,
    filter_ajustes_finos_by_period,
    filter_routine_logs_by_date,
    filter_routine_logs_by_period,
    total_ajuste_minutos,
)
from operational.entities.ajuste_fino import AjusteFino
from operational.entities.routine import RoutineLog
from operational.enums import Period, RoutineType


# ---------------------------------------------------------------------------
# build_routine_log
# ---------------------------------------------------------------------------


class TestBuildRoutineLog:
    """Tests for the build_routine_log factory."""

    def test_minimal_build(self) -> None:
        log = build_routine_log(
            routine_log_id="rlog_b1",
            routine_id="rou_acordar",
            date_=date(2026, 6, 7),
            period=Period.MANHA,
            routine_type=RoutineType.ENTRY,
            text="Acordei bem",
        )
        assert isinstance(log, RoutineLog)
        assert log.id == "rlog_b1"
        assert log.routine_id == "rou_acordar"
        assert log.text == "Acordei bem"
        assert log.created_at is not None

    def test_build_with_all_fields(self) -> None:
        log = build_routine_log(
            routine_log_id="rlog_b2",
            routine_id="rou_preparar",
            date_=date(2026, 6, 7),
            period=Period.NOITE,
            routine_type=RoutineType.EXIT,
            text="2 marmitas prontas",
            block_id="tbl_noite_wind_down",
            energia_nivel=5,
            foco_nivel=4,
            humor=3,
        )
        assert log.energia_nivel == 5
        assert log.foco_nivel == 4
        assert log.humor == 3
        assert log.block_id == "tbl_noite_wind_down"

    def test_build_strips_whitespace(self) -> None:
        log = build_routine_log(
            routine_log_id="rlog_b3",
            routine_id="rou_x",
            date_=date(2026, 6, 7),
            period=Period.MANHA,
            routine_type=RoutineType.ENTRY,
            text="  Spacious  text  ",
        )
        assert log.text == "Spacious  text"  # strip removes edges only

    def test_build_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="text cannot be empty"):
            build_routine_log(
                routine_log_id="rlog_b4",
                routine_id="rou_x",
                date_=date(2026, 6, 7),
                period=Period.MANHA,
                routine_type=RoutineType.ENTRY,
                text="",
            )

    def test_build_whitespace_only_text_raises(self) -> None:
        with pytest.raises(ValueError, match="text cannot be empty"):
            build_routine_log(
                routine_log_id="rlog_b5",
                routine_id="rou_x",
                date_=date(2026, 6, 7),
                period=Period.MANHA,
                routine_type=RoutineType.ENTRY,
                text="   \t\n  ",
            )


# ---------------------------------------------------------------------------
# build_ajuste_fino
# ---------------------------------------------------------------------------


class TestBuildAjusteFino:
    """Tests for the build_ajuste_fino factory."""

    def test_minimal_build(self) -> None:
        ajuste = build_ajuste_fino(
            ajuste_fino_id="aju_b1",
            date_=date(2026, 6, 7),
            period=Period.MANHA,
            minutos=5,
            reason="Extended break",
        )
        assert isinstance(ajuste, AjusteFino)
        assert ajuste.minutos == 5
        assert ajuste.reason == "Extended break"

    def test_build_with_block_refs(self) -> None:
        ajuste = build_ajuste_fino(
            ajuste_fino_id="aju_b2",
            date_=date(2026, 6, 7),
            period=Period.TARDE,
            minutos=-30,
            reason="Reduced S3 to 2 rounds",
            block_id_before="tbl_focus_s2",
            block_id_after="tbl_focus_s3",
        )
        assert ajuste.minutos == -30
        assert ajuste.block_id_before == "tbl_focus_s2"

    def test_build_strips_reason(self) -> None:
        ajuste = build_ajuste_fino(
            ajuste_fino_id="aju_b3",
            date_=date(2026, 6, 7),
            period=Period.MANHA,
            minutos=5,
            reason="  Spacious reason  ",
        )
        assert ajuste.reason == "Spacious reason"

    def test_build_empty_reason_raises(self) -> None:
        with pytest.raises(ValueError, match="reason cannot be empty"):
            build_ajuste_fino(
                ajuste_fino_id="aju_b4",
                date_=date(2026, 6, 7),
                period=Period.MANHA,
                minutos=5,
                reason="",
            )


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def _make_log(date_: date, period: Period, routine_type: RoutineType = RoutineType.ENTRY) -> RoutineLog:
    return RoutineLog(
        id=f"rlog_{date_.strftime('%Y%m%d')}_{period.value.lower()}",
        routine_id="rou_x",
        date=date_,
        period=period,
        routine_type=routine_type,
        text="x",
        created_at=datetime(2026, 6, 7, 4, 0),
    )


def _make_ajuste(date_: date, period: Period, minutos: int = 5) -> AjusteFino:
    return AjusteFino(
        id=f"aju_{date_.strftime('%Y%m%d')}_{period.value.lower()}",
        date=date_,
        period=period,
        minutos=minutos,
        reason="x",
        created_at=datetime(2026, 6, 7, 4, 0),
    )


class TestFilters:
    """Tests for filter functions."""

    def test_filter_routine_logs_by_date(self) -> None:
        logs = [
            _make_log(date(2026, 6, 7), Period.MANHA),
            _make_log(date(2026, 6, 7), Period.TARDE),
            _make_log(date(2026, 6, 8), Period.MANHA),
        ]
        result = filter_routine_logs_by_date(logs, date(2026, 6, 7))
        assert len(result) == 2
        assert all(log.date == date(2026, 6, 7) for log in result)

    def test_filter_routine_logs_by_date_sorted(self) -> None:
        logs = [
            _make_log(date(2026, 6, 7), Period.NOITE),
            _make_log(date(2026, 6, 7), Period.MANHA),
            _make_log(date(2026, 6, 7), Period.TARDE),
        ]
        result = filter_routine_logs_by_date(logs, date(2026, 6, 7))
        # Sorted by period start hour: MANHA(3) < TARDE(8) < NOITE(18)
        assert [log.period for log in result] == [Period.MANHA, Period.TARDE, Period.NOITE]

    def test_filter_routine_logs_by_period(self) -> None:
        logs = [
            _make_log(date(2026, 6, 7), Period.MANHA),
            _make_log(date(2026, 6, 7), Period.TARDE),
            _make_log(date(2026, 6, 8), Period.MANHA),
        ]
        result = filter_routine_logs_by_period(logs, Period.MANHA)
        assert len(result) == 2
        assert all(log.period == Period.MANHA for log in result)

    def test_filter_ajustes_finos_by_date(self) -> None:
        ajustes = [
            _make_ajuste(date(2026, 6, 7), Period.MANHA),
            _make_ajuste(date(2026, 6, 7), Period.TARDE),
            _make_ajuste(date(2026, 6, 8), Period.MANHA),
        ]
        result = filter_ajustes_finos_by_date(ajustes, date(2026, 6, 7))
        assert len(result) == 2

    def test_filter_ajustes_finos_by_period(self) -> None:
        ajustes = [
            _make_ajuste(date(2026, 6, 7), Period.MANHA),
            _make_ajuste(date(2026, 6, 7), Period.TARDE),
            _make_ajuste(date(2026, 6, 8), Period.MANHA),
        ]
        result = filter_ajustes_finos_by_period(ajustes, Period.MANHA)
        assert len(result) == 2

    def test_total_ajuste_minutos_mixed(self) -> None:
        ajustes = [
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=10),
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=-5),
            _make_ajuste(date(2026, 6, 7), Period.TARDE, minutos=15),
        ]
        assert total_ajuste_minutos(ajustes) == 20

    def test_total_ajuste_minutos_empty(self) -> None:
        assert total_ajuste_minutos([]) == 0


# ---------------------------------------------------------------------------
# RoutineLogger facade
# ---------------------------------------------------------------------------


class TestRoutineLoggerFacade:
    """Tests for the RoutineLogger dataclass facade."""

    def test_logs_on(self) -> None:
        logs = [
            _make_log(date(2026, 6, 7), Period.MANHA),
            _make_log(date(2026, 6, 8), Period.TARDE),
        ]
        rl = RoutineLogger(routine_logs=logs, ajustes_finos=[])
        result = rl.logs_on(date(2026, 6, 7))
        assert len(result) == 1
        assert result[0].date == date(2026, 6, 7)

    def test_logs_in(self) -> None:
        logs = [
            _make_log(date(2026, 6, 7), Period.MANHA),
            _make_log(date(2026, 6, 7), Period.TARDE),
            _make_log(date(2026, 6, 8), Period.MANHA),
        ]
        rl = RoutineLogger(routine_logs=logs, ajustes_finos=[])
        result = rl.logs_in(Period.MANHA)
        assert len(result) == 2
        assert all(log.period == Period.MANHA for log in result)

    def test_ajustes_on(self) -> None:
        ajustes = [
            _make_ajuste(date(2026, 6, 7), Period.MANHA),
            _make_ajuste(date(2026, 6, 8), Period.TARDE),
        ]
        rl = RoutineLogger(routine_logs=[], ajustes_finos=ajustes)
        result = rl.ajustes_on(date(2026, 6, 7))
        assert len(result) == 1

    def test_ajustes_in(self) -> None:
        ajustes = [
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=5),
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=-3),
            _make_ajuste(date(2026, 6, 7), Period.TARDE, minutos=10),
        ]
        rl = RoutineLogger(routine_logs=[], ajustes_finos=ajustes)
        result = rl.ajustes_in(Period.MANHA)
        assert len(result) == 2

    def test_net_adjustment_for_period_positive(self) -> None:
        ajustes = [
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=10),
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=5),
        ]
        rl = RoutineLogger(routine_logs=[], ajustes_finos=ajustes)
        assert rl.net_adjustment_for_period(Period.MANHA) == 15

    def test_net_adjustment_for_period_negative(self) -> None:
        ajustes = [
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=10),
            _make_ajuste(date(2026, 6, 7), Period.MANHA, minutos=-25),
        ]
        rl = RoutineLogger(routine_logs=[], ajustes_finos=ajustes)
        assert rl.net_adjustment_for_period(Period.MANHA) == -15

    def test_net_adjustment_for_period_empty(self) -> None:
        rl = RoutineLogger(routine_logs=[], ajustes_finos=[])
        assert rl.net_adjustment_for_period(Period.MANHA) == 0
