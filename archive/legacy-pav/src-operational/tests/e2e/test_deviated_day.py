"""E2E: Deviated day — PAV §8 scenario with partial failures."""
from __future__ import annotations

from operational.core.scenario_classifier import classificar_dia
from operational.core.sleep_calculator import validar_sono_ideal
from operational.core.time_validator import validar_horario_acordar
from operational.enums import QualityLabel


def test_deviated_wake() -> None:
    wake = validar_horario_acordar(6)
    assert wake.status == "LEVE_DESVIO"
    assert wake.desvio_minutos == 60


def test_deviated_sleep() -> None:
    label = validar_sono_ideal(6.0)
    assert label is QualityLabel.HARDCORE


def test_deviated_scenario() -> None:
    result = classificar_dia(
        horas_sono=7.0,
        pomodoros_planejados=10,
        pomodoros_completos=4,
    )
    assert result.scenario.value == "desviado"


def test_deviated_low_pomodoro() -> None:
    result = classificar_dia(
        horas_sono=5.0,
        pomodoros_planejados=10,
        pomodoros_completos=4,
    )
    assert result.scenario.value == "desviado"
