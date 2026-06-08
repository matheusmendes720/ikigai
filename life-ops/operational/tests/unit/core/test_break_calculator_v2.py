"""Unit tests for :mod:`operational.core.break_calculator` — adjusted_net_rest."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from operational.core.break_calculator import adjusted_net_rest_minutes
from operational.core.context_switch import context_switch_overhead_minutes
from operational.entities.ajuste_fino import AjusteFino
from operational.enums import Period


def _make_ajuste(period: Period, minutos: int, reason: str = "test") -> AjusteFino:
    return AjusteFino(
        id=f"aju_{period.value.lower()}_{minutos}_{abs(minutos)}".replace("-", "_"),
        date=date(2026, 6, 7),
        period=period,
        minutos=minutos,
        reason=reason,
        created_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# Basic adjusted_net_rest_minutes
# ---------------------------------------------------------------------------


class TestAdjustedNetRestMinutes:
    """Tests for adjusted_net_rest_minutes (gross break - overhead + ajustes)."""

    def test_no_ajustes_matches_net_rest(self) -> None:
        """With no ajustes, adjusted = net_rest (gross_break - overhead)."""
        # 60min gross, MANHA→TARDE overhead 30min → 30min net (no ajustes)
        result = adjusted_net_rest_minutes(60.0, Period.MANHA, Period.TARDE)
        assert result == 30.0

    def test_zero_gross_break(self) -> None:
        result = adjusted_net_rest_minutes(0.0, Period.MANHA, Period.TARDE)
        assert result == 0.0

    def test_gross_break_equals_overhead(self) -> None:
        # 30min gross, 30min overhead → 0 net
        result = adjusted_net_rest_minutes(30.0, Period.MANHA, Period.TARDE)
        assert result == 0.0

    def test_gross_break_less_than_overhead_clamps_to_zero(self) -> None:
        # 10min gross, 30min overhead → 0 (clamped)
        result = adjusted_net_rest_minutes(10.0, Period.MANHA, Period.TARDE)
        assert result == 0.0

    def test_negative_gross_break_raises(self) -> None:
        with pytest.raises(ValueError, match="gross_break_minutes"):
            adjusted_net_rest_minutes(-1.0, Period.MANHA, Period.TARDE)

    def test_within_period(self) -> None:
        # Within-period overhead 5min, 30min gross → 25min net
        result = adjusted_net_rest_minutes(30.0, Period.MANHA, Period.MANHA)
        assert result == 25.0

    def test_backward_transition(self) -> None:
        # TARDE→MANHA overhead 45min, 60min gross → 15min net
        result = adjusted_net_rest_minutes(60.0, Period.TARDE, Period.MANHA)
        assert result == 15.0


# ---------------------------------------------------------------------------
# With AjustesFinos
# ---------------------------------------------------------------------------


class TestAdjustedNetRestWithAjustes:
    """Tests with AjusteFino entries."""

    def test_positive_ajuste_adds_to_net(self) -> None:
        # 60min gross - 30min overhead + 10min ajuste = 40min
        ajuste = _make_ajuste(Period.MANHA, 10)
        result = adjusted_net_rest_minutes(
            60.0, Period.MANHA, Period.TARDE, ajustes_finos=[ajuste],
        )
        assert result == 40.0

    def test_negative_ajuste_subtracts_from_net(self) -> None:
        # 60min gross - 30min overhead + (-10)min ajuste = 20min
        ajuste = _make_ajuste(Period.MANHA, -10)
        result = adjusted_net_rest_minutes(
            60.0, Period.MANHA, Period.TARDE, ajustes_finos=[ajuste],
        )
        assert result == 20.0

    def test_multiple_ajustes_sum(self) -> None:
        # 60 - 30 + 5 - 3 + 10 = 42
        ajustes = [
            _make_ajuste(Period.MANHA, 5),
            _make_ajuste(Period.MANHA, -3),
            _make_ajuste(Period.MANHA, 10),
        ]
        result = adjusted_net_rest_minutes(
            60.0, Period.MANHA, Period.TARDE, ajustes_finos=ajustes,
        )
        assert result == 42.0

    def test_ajuste_for_wrong_period_ignored(self) -> None:
        # Only MANHA-period ajustes count for MANHA→TARDE
        ajustes = [
            _make_ajuste(Period.MANHA, 10),  # counts
            _make_ajuste(Period.TARDE, 100),  # ignored (wrong period)
            _make_ajuste(Period.NOITE, 50),  # ignored
        ]
        result = adjusted_net_rest_minutes(
            60.0, Period.MANHA, Period.TARDE, ajustes_finos=ajustes,
        )
        assert result == 40.0  # 60 - 30 + 10

    def test_net_clamps_to_zero(self) -> None:
        # Large negative ajuste + small gross = 0 (clamped)
        ajuste = _make_ajuste(Period.MANHA, -100)
        result = adjusted_net_rest_minutes(
            30.0, Period.MANHA, Period.TARDE, ajustes_finos=[ajuste],
        )
        assert result == 0.0  # 30 - 30 - 100 = -100 → 0

    def test_ajuste_for_correct_period_in_complex_scenario(self) -> None:
        # MANHA→TARDE: overhead 30min
        # User has 3 ajustes in MANHA: +10, -5, +5 (net +10)
        # 60 - 30 + 10 = 40
        ajustes = [
            _make_ajuste(Period.MANHA, 10, "extended morning break"),
            _make_ajuste(Period.MANHA, -5, "shaved morning focus"),
            _make_ajuste(Period.MANHA, 5, "extra hydration ritual"),
        ]
        result = adjusted_net_rest_minutes(
            60.0, Period.MANHA, Period.TARDE, ajustes_finos=ajustes,
        )
        assert result == 40.0

    def test_empty_ajustes_iterable_same_as_none(self) -> None:
        # Both should give the same result
        result_no_ajustes = adjusted_net_rest_minutes(
            60.0, Period.MANHA, Period.TARDE,
        )
        result_empty = adjusted_net_rest_minutes(
            60.0, Period.MANHA, Period.TARDE, ajustes_finos=[],
        )
        assert result_no_ajustes == result_empty == 30.0
