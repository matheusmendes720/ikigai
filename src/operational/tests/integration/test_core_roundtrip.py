"""Integration: core modules work together end-to-end."""
from __future__ import annotations

from datetime import date

from operational.core.policy_engine import PolicyEngine
from operational.core.routine_logger import (
    build_ajuste_fino,
    build_routine_log,
    filter_routine_logs_by_date,
)
from operational.core.scenario_classifier import classificar_dia
from operational.core.sleep_calculator import calcular_horas_sono, validar_sono_ideal
from operational.core.time_validator import validar_horario_acordar
from operational.entities.ajuste_fino import AjusteFino
from operational.enums import Period, QualityLabel, RoutineType


def test_routine_logger_with_ajuste() -> None:
    log = build_routine_log(
        routine_log_id="rlog_test_001",
        routine_id="rou_morning",
        date_=date.today(),
        period=Period.MANHA,
        routine_type=RoutineType.ENTRY,
        text="Fiz meditação por 10 minutos.",
    )
    ajuste = build_ajuste_fino(
        ajuste_fino_id="aju_test_001",
        date_=date.today(),
        period=Period.TARDE,
        minutos=-5,
        reason="Pausa extra",
    )
    logs = filter_routine_logs_by_date([log], date.today())
    assert len(logs) >= 1
    assert isinstance(ajuste, AjusteFino)
    assert ajuste.minutos == -5


def test_sleep_and_wake_validation_integration() -> None:
    wake = validar_horario_acordar(4)
    assert wake.status == "OPTIMAL"

    hours = calcular_horas_sono(22, 6)
    assert hours == 8.0

    label = validar_sono_ideal(8.0)
    assert label is QualityLabel.BOM


def test_policy_engine_instantiation() -> None:
    engine = PolicyEngine(max_history=10)
    assert engine.current_state is None


def test_scenario_classifier() -> None:
    result = classificar_dia(
        horas_sono=8.0,
        pomodoros_planejados=10,
        pomodoros_completos=10,
    )
    assert result.scenario.value == "perfeito"
