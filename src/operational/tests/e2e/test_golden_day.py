"""E2E: Golden day scenario — PAV §8 ideal execution."""
from __future__ import annotations

from operational.core.scenario_classifier import classificar_dia
from operational.core.sleep_calculator import calcular_horas_sono, validar_sono_ideal
from operational.core.time_validator import validar_horario_acordar
from operational.enums import QualityLabel


def test_golden_wake_time() -> None:
    wake = validar_horario_acordar(4)
    assert wake.status == "OPTIMAL"


def test_golden_sleep() -> None:
    label = validar_sono_ideal(8.0)
    assert label is QualityLabel.BOM


def test_golden_sleep_hours() -> None:
    hours = calcular_horas_sono(22, 6)
    assert hours == 8.0


def test_golden_scenario() -> None:
    result = classificar_dia(
        horas_sono=8.0,
        pomodoros_planejados=10,
        pomodoros_completos=10,
    )
    assert result.scenario.value == "perfeito"


def test_golden_full_profile() -> None:
    wake = validar_horario_acordar(4)
    assert wake.status == "OPTIMAL"

    sleep_label = validar_sono_ideal(8.0)
    assert sleep_label is QualityLabel.BOM

    scenario = classificar_dia(8.0, 10, 10)
    assert scenario.scenario.value == "perfeito"
