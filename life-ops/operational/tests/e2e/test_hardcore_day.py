"""E2E: Hardcore day — PAV §8 extreme scenario."""
from __future__ import annotations

import pytest

from operational.core.scenario_classifier import (
    HARDCORE_MAX_PER_MONTH,
    classificar_dia,
    is_hardcore_alert,
)
from operational.core.sleep_calculator import validar_sono_ideal
from operational.core.time_validator import validar_horario_acordar
from operational.enums import QualityLabel
from operational.exceptions import TimeValidationError


def test_hardcore_wake_out_of_bounds() -> None:
    with pytest.raises(TimeValidationError, match="impossível"):
        validar_horario_acordar(2)


def test_hardcore_sleep() -> None:
    label = validar_sono_ideal(3.5)
    assert label is QualityLabel.CRITICO


def test_hardcore_scenario() -> None:
    result = classificar_dia(
        horas_sono=3.5,
        pomodoros_planejados=12,
        pomodoros_completos=12,
    )
    assert result.scenario.value == "hardcore"


def test_hardcore_alert_threshold() -> None:
    assert HARDCORE_MAX_PER_MONTH == 2


def test_hardcore_alert_true() -> None:
    assert is_hardcore_alert(2)


def test_hardcore_alert_false() -> None:
    assert not is_hardcore_alert(1)
