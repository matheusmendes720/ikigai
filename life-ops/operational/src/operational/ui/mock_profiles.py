"""Mock data profiles for visual debug + visual regression testing.

Use ``--mock <profile>`` on any output command to force a specific
data state without touching the real JSON store. The mock data is
fed into ``core.services.get_day_snapshot()`` which returns a real
``DaySnapshot`` — so the rendering path is identical to production.

Profiles:
- q1: green quadrant, PUSH regime, peak energy
- q2: top-left, MAINTAIN
- q3: red quadrant, RECOVER (alert!)
- q4: bottom-right, REDUCE
- empty: no data, all zeros
- burnout: low everything
- peak: high everything
- golden: from docs/golden.csv
- synth: from docs/synthetic.csv
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from typing import Final

from operational.enums import EstadoPsicomatico, PolicyState, TipoDia
from operational.core.budget import (
    budget_for_date, classify_quadrant, productivity_pct, efficiency_pct,
)


@dataclass(frozen=True)
class MockProfile:
    """One deterministic data state for visual testing."""
    name: str
    description: str
    target_date: date
    tipo_dia: TipoDia
    sleep_hours: float
    sleep_quality: int
    energia: int
    foco: int
    hardwork_realizado_min: int
    pomodoros_done: int
    pomodoros_meta: int
    regime: PolicyState

    @property
    def orcado_min(self) -> int:
        return budget_for_date(self.target_date, self.tipo_dia)

    @property
    def x_pct(self) -> float:
        return productivity_pct(self.hardwork_realizado_min, self.orcado_min)

    @property
    def y_pct(self) -> float:
        # Efficiency: lower of energia and foco, scaled 0-100
        # This is what makes Q4 (high output, low focus) and Q3 (low both) work.
        return min(self.energia, self.foco) * 10.0

    @property
    def quadrant(self) -> str:
        return classify_quadrant(self.x_pct, self.y_pct)[0]


# ---------------------------------------------------------------------------
# Canonical profiles
# ---------------------------------------------------------------------------

_TODAY: Final[date] = date.today()


PROFILES: Final[dict[str, MockProfile]] = {
    "q1": MockProfile(
        name="q1",
        description="Green quadrant, PUSH regime, peak everything",
        target_date=_TODAY,
        tipo_dia=TipoDia.CURSO,
        sleep_hours=8.0,
        sleep_quality=9,
        energia=10,
        foco=10,
        hardwork_realizado_min=540,
        pomodoros_done=12,
        pomodoros_meta=12,
        regime=PolicyState.PUSH,
    ),
    "q2": MockProfile(
        name="q2",
        description="Top-left: optimized but low output, MAINTAIN",
        target_date=_TODAY,
        tipo_dia=TipoDia.CURSO,
        sleep_hours=8.0,
        sleep_quality=8,
        energia=9,
        foco=9,
        hardwork_realizado_min=100,  # <50% of orcado (240)
        pomodoros_done=2,
        pomodoros_meta=12,
        regime=PolicyState.MAINTAIN,
    ),
    "q3": MockProfile(
        name="q3",
        description="Red quadrant, RECOVER, alert state",
        target_date=_TODAY,
        tipo_dia=TipoDia.LIVRE,
        sleep_hours=4.0,  # bad
        sleep_quality=3,
        energia=3,
        foco=2,
        hardwork_realizado_min=60,
        pomodoros_done=1,
        pomodoros_meta=12,
        regime=PolicyState.RECOVER,
    ),
    "q4": MockProfile(
        name="q4",
        description="Bottom-right: productive but dispersed, REDUCE",
        target_date=_TODAY,
        tipo_dia=TipoDia.CURSO,
        sleep_hours=7.0,
        sleep_quality=7,
        energia=8,
        foco=3,  # low focus
        hardwork_realizado_min=480,  # high output
        pomodoros_done=10,
        pomodoros_meta=12,
        regime=PolicyState.REDUCE,
    ),
    "empty": MockProfile(
        name="empty",
        description="No data, all zeros, baseline empty state",
        target_date=_TODAY,
        tipo_dia=TipoDia.CURSO,
        sleep_hours=0.0,
        sleep_quality=0,
        energia=0,
        foco=0,
        hardwork_realizado_min=0,
        pomodoros_done=0,
        pomodoros_meta=0,  # no target either
        regime=PolicyState.MAINTAIN,
    ),
    "burnout": MockProfile(
        name="burnout",
        description="Burnout: low sleep, low energy, Q3, RECOVER",
        target_date=_TODAY,
        tipo_dia=TipoDia.LIVRE,
        sleep_hours=3.5,
        sleep_quality=2,
        energia=2,
        foco=1,
        hardwork_realizado_min=30,
        pomodoros_done=0,
        pomodoros_meta=12,
        regime=PolicyState.RECOVER,
    ),
    "peak": MockProfile(
        name="peak",
        description="Peak performance: high everything, deep Q1",
        target_date=_TODAY,
        tipo_dia=TipoDia.CURSO,
        sleep_hours=9.0,
        sleep_quality=10,
        energia=10,
        foco=10,
        hardwork_realizado_min=600,  # over-achievement
        pomodoros_done=12,
        pomodoros_meta=12,
        regime=PolicyState.PUSH,
    ),
}


def get_profile(name: str) -> MockProfile:
    """Get a mock profile by name. Raises ValueError if unknown."""
    if name not in PROFILES:
        raise ValueError(
            f"Unknown mock profile {name!r}. "
            f"Available: {sorted(PROFILES.keys())}"
        )
    return PROFILES[name]


def list_profiles() -> list[str]:
    """Return sorted list of profile names."""
    return sorted(PROFILES.keys())


__all__ = ["MockProfile", "PROFILES", "get_profile", "list_profiles"]
