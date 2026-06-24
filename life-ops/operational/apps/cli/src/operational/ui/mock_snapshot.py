"""Build a DaySnapshot from a MockProfile for visual testing.

This bypasses the real ``core.services.get_day_snapshot()`` (which
reads from 14 JSON repos) and synthesizes a complete DaySnapshot
directly from a ``MockProfile``. The result flows through the same
rendering path as production data, so ``--mock q3`` produces the
exact same output as if the user had 7 Q3 days in production.
"""
from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from operational.cli.services import DaySnapshot, SleepSnapshot

if TYPE_CHECKING:
    from operational.ui.mock_profiles import MockProfile


def build_mock_snapshot(profile: MockProfile) -> DaySnapshot:
    """Synthesize a DaySnapshot from a mock profile.

    The result is a real ``DaySnapshot`` dataclass that the UI
    layer can render identically to production snapshots.
    """
    sleep = SleepSnapshot(
        bedtime=time(23, 0) if profile.sleep_hours > 0 else None,
        wake_time=time(7, 0) if profile.sleep_hours > 0 else None,
        duration_hours=profile.sleep_hours,
        quality=profile.sleep_quality,
        notes=f"[MOCK PROFILE: {profile.name}]",
    )
    return DaySnapshot(
        date=profile.target_date,
        tipo_dia=profile.tipo_dia,
        sleep=sleep,
        wake_hour=7 if profile.sleep_hours > 0 else None,
        sleep_hour=23 if profile.sleep_hours > 0 else None,
        workout_done=profile.energia >= 7,
        workout_minutes=30 if profile.energia >= 7 else 0,
        meditacao_done=profile.foco >= 7,
        meditacao_minutes=10 if profile.foco >= 7 else 0,
        lunch_eat_min=5,
        lunch_rest_min=30,
        lunch_pesado=profile.energia < 5,
        jantar_antes_18=profile.sleep_hours >= 7,
        luz_azul_apos_18=profile.energia >= 6,
        n_transicoes_completas=int(9 * profile.foco / 10),
        n_transicoes_total=9,
        n_blocks=3 if profile.pomodoros_done > 0 else 0,
        total_block_minutes=profile.hardwork_realizado_min,
        hardwork_orcado_min=profile.orcado_min,
        hardwork_realizado_min=profile.hardwork_realizado_min,
        pomodoros_meta=profile.pomodoros_meta,
        pomodoros_done=profile.pomodoros_done,
        n_pomodoros=profile.pomodoros_done,
        energia=profile.energia,
        foco=profile.foco,
        humor_morning=8 if profile.energia >= 7 else 4,
        humor_evening=7 if profile.energia >= 7 else 3,
        desvios=[] if profile.quadrant == "Q1" else [
            f"[MOCK] {profile.description}",
        ],
        licoes=[],
        ajustes=[],
        big_win="[MOCK] Peak focus achieved" if profile.quadrant == "Q1" else "",
        parar_de_fazer=[],
        repetir=[],
    )


__all__ = ["build_mock_snapshot"]
