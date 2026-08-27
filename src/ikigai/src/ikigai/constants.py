"""North Star Metrics (NSM) — 22 canonical constants.

Frozen here. Any change requires updating SPEC.md §11.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PAV_NS:
    """PAV North Star Metrics (22 constants, frozen)."""

    # Janelas temporais canônicas (1-9)
    HORARIO_ACORDAR_MIN: int = 3  # 3 AM
    HORARIO_ACORDAR_MAX: int = 5  # 5 AM
    HORARIO_DORMIR_MIN: int = 18  # 18h
    HORARIO_DORMIR_MAX: int = 21  # 21h
    HORARIO_ULTIMA_REFEICAO_MIN: int = 15  # 15h
    HORARIO_ULTIMA_REFEICAO_MAX: int = 18  # 18h
    SONO_OPCOES_HORAS: tuple = (9, 8, 7, 4)
    LUZ_AZUL_CORTE: int = 18  # 18h
    TRANSITION_RITUAL_MAX_MIN: int = 5

    # Pomodoro canônico (10-11)
    POMODORO_WORK_MIN: int = 50
    POMODORO_BREAK_MIN: int = 10

    # Constantes matemáticas (12-15)
    LAMBDA: float = 0.093  # habit learning rate (D⁻¹)
    RHO: float = 0.7333  # calendar W→D conversion
    WORK_RATIO: float = 0.7333  # 22/30
    BUFFER_CYCLE_DAYS: int = 3  # ~6.7% margin

    # Fractal temporal (16-21)
    WAVE_DAYS: int = 15
    CYCLE_DAYS: int = 45
    PHASE_DAYS: int = 180

    # Q_HE thresholds (22)
    Q_HE_PUSH: float = 0.85
    Q_HE_REDUCE: float = 0.65
    Q_HE_RECOVER: float = 0.60

    # Meta-vetor hybrid weights (23-24)
    META_VETOR_W_GEO: float = 0.6
    META_VETOR_W_HARM: float = 0.4

    # Hysteresis windows (25-26)
    HYSTERESIS_UPGRADE_DAYS: int = 3
    HYSTERESIS_DOWNGRADE_DAYS: int = 2

    # Phase convergence (27)
    PHASE_MAX_ITERS: int = 5
    PHASE_CONVERGENCE_THRESHOLD: float = 0.01


# Singleton instance
NSM = PAV_NS()


__all__ = ["PAV_NS", "NSM"]
