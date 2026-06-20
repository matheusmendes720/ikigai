"""Canonical operational constants (PAV §1, Points_of_premisses §4, PRD-02).

This module is the **single source of truth** for all numeric and string
constants used throughout the ``operational`` package. Values are immutable
post-construction (frozen dataclass with ``__slots__``) and trace back to the
PAV canonical spec or its derivative documents.

Source documents (in priority order):

* PAV §1 — ``CONSTANTES DO SISTEMA`` (12 base constants, lines 48-58 of
  ``vibe-ops/base/Produtividade Algorítmica Visual.md``)
* PAV §9 — Pomodoro state-machine (line 2291: ``POMODORO_LONG_BREAK = 30``)
* ``life-ops/planner/Points_of_premisses-task-habits.md`` §4 — Policy
  histerese days + QHE thresholds
* ``vibe-ops/planning/PRD-02-habit-tracker.md`` — QHE weights
  (alpha/beta/gamma) + lambda_learning default
* ``vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md`` — lambda = 0.093

Design decisions:

* **24 fields** (not 22): we kept the 12 PAV §1 fields intact, split the
  ``HORARIO_ULTIMA_REFEICAO`` range into ``_MIN``/``_MAX`` (2 fields), added
  the canonical ``POMODORO_LONG_BREAK_MIN`` (PAV §9), and bundled the 8
  policy/QHE/lambda constants that govern the cybernetic layer. All sources
  are referenced in the per-field docstrings.
* **Immutable** post-construction (frozen, slots).
* **Type-checked**: ``mypy --strict`` compatible.
* **Validated** at construction time via ``__post_init__`` — invalid
  combinations raise ``ValueError`` (programming error, not runtime data).
* Single ``DEFAULT`` instance is the production configuration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final

__all__ = ["DEFAULT", "PAVConstants"]

# --- Module-level validation constants (ruff PLR2004) -----------------------
# Magic values used in __post_init__ and domain helpers. Defining them at
# module scope makes the intent explicit and silences PLR2004 without losing
# the literal value in the call site.
_PERIODOS_DIA_EXPECTED_LEN: Final[int] = 3
_SONO_OPCOES_EXPECTED_LEN: Final[int] = 4
_QHE_WEIGHT_SUM_TOLERANCE: Final[float] = 0.001
_SLEEP_DURATION_TOLERANCE: Final[float] = 0.5
_LAMBDA_LEARNING_LOWER_BOUND: Final[float] = 0.0
_LAMBDA_LEARNING_UPPER_BOUND: Final[float] = 1.0


@dataclass(frozen=True, slots=True, kw_only=True, repr=True)
class PAVConstants:
    """Canonical operational constants. Immutable post-construction.

    The 24 fields fall into **5 categories**:

    1. **Time boundaries** (7 fields): wake / sleep / last-meal windows.
    2. **Periods** (1 field): the 3-period day cycle.
    3. **Pomodoro** (5 fields): work-block, breaks, round counts.
    4. **Health** (2 fields): sleep options, water target.
    5. **Policy & QHE** (9 fields): histerese days, QHE weights, QHE
       thresholds, learning rate.

    All values are non-negative ``int`` or ``float`` in ``[0, 1]``, except
    ``PERIODOS_DIA`` and ``SONO_OPCOES_HORAS`` which are immutable tuples.

    The class uses ``frozen=True`` + ``slots=True`` + ``kw_only=True``:

    * ``frozen`` — assignments after construction raise ``FrozenInstanceError``.
    * ``slots`` — memory-efficient, prevents ``__dict__`` creation.
    * ``kw_only`` — all parameters are keyword-only, so order independence
      and no-arg construction (``PAVConstants()``) both work.
    """

    # --- 1. Periods ---------------------------------------------------------
    PERIODOS_DIA: tuple[str, ...] = ("MANHA", "TARDE", "NOITE")
    """3 periods of the day cycle. **PAV §1**: ``["MANHA", "TARDE", "NOITE"]``."""

    # --- 2. Time boundaries (7) -------------------------------------------
    HORARIO_ACORDAR_MIN: int = 3
    """Earliest acceptable wake hour (3 am). **PAV §1** — padrão ouro."""

    HORARIO_ACORDAR_MAX: int = 5
    """Latest acceptable wake hour (5 am). **PAV §1** — padrão ouro."""

    HORARIO_DORMIR_MIN: int = 18
    """Earliest acceptable sleep hour (18 h). **PAV §1**."""

    HORARIO_DORMIR_MAX: int = 21
    """Latest acceptable sleep hour (21 h). **PAV §1**."""

    HORARIO_ULTIMA_REFEICAO_MIN: int = 15
    """Earliest final-meal hour (15 h). **PAV §1** — split from range 15-18."""

    HORARIO_ULTIMA_REFEICAO_MAX: int = 18
    """Latest final-meal hour (18 h). **PAV §1** — paired with ``LUZ_AZUL_CORTE``."""

    LUZ_AZUL_CORTE: int = 18
    """Blue-light cutoff hour (18 h). **PAV §1** — no screens after this hour."""

    # --- 3. Pomodoro (5) ---------------------------------------------------
    POMODORO_WORK_MIN: int = 50
    """Pomodoro work-block length in minutes (50 min). **PAV §1**."""

    POMODORO_BREAK_MIN: int = 10
    """Pomodoro short-break length in minutes (10 min). **PAV §1**."""

    POMODORO_LONG_BREAK_MIN: int = 30
    """Pomodoro long-break length in minutes (30 min). **PAV §9** line 2291."""

    POMODORO_ROUNDS_MIN: int = 3
    """Minimum rounds per session. **PAV §1** — required for full coverage."""

    POMODORO_ROUNDS_MAX: int = 4
    """Maximum rounds per session. **PAV §1** — upper bound for normal days."""

    # --- 4. Health (3) -----------------------------------------------------
    SONO_OPCOES_HORAS: tuple[int, ...] = (9, 8, 7, 4)
    """Approved sleep duration options in hours. **PAV §1**: ``(9, 8, 7, 4)``."""

    AGUA_GLASSES_DIA: int = 8
    """Daily water glasses target. Health baseline (250 ml x 8 = 2 L/day)."""

    # --- 5. Policy & QHE (8) -----------------------------------------------
    POLICY_UPGRADE_DAYS: int = 3
    """Days of sustained QHE ≥ push threshold before upgrading policy.
    **Points_of_premisses §4** — histerese anti-bouncing."""

    POLICY_DOWNGRADE_DAYS: int = 2
    """Days of sustained QHE ≤ recover threshold before downgrading policy.
    **Points_of_premisses §4** — asymmetric histerese (faster decay)."""

    POLICY_RECOVER_ENTRY_DAYS: int = 1
    """Days at QHE < recover threshold to enter ``RECOVER`` state.
    **Points_of_premisses §4** — emergency entry."""

    QHE_ALPHA: float = 0.45
    """Weight of ``H_avg`` in the QHE formula. **PRD-02 §Fórmula QHE**."""

    QHE_BETA: float = 0.35
    """Weight of ``Consistency`` in the QHE formula. **PRD-02 §Fórmula QHE**."""

    QHE_GAMMA: float = 0.20
    """Weight of ``StreakBonus`` in the QHE formula. **PRD-02 §Fórmula QHE**."""

    QHE_PUSH_THRESHOLD: float = 0.85
    """QHE value at or above which policy is ``PUSH``. **Points_of_premisses §4**."""

    QHE_RECOVER_THRESHOLD: float = 0.60
    """QHE value below which policy is ``RECOVER``. **Points_of_premisses §4**."""

    LAMBDA_LEARNING_DEFAULT: float = 0.093
    """Default learning rate for habit automation. **ADR-003 / time-lenghts §9.2**."""

    # --- Class metadata (not dataclass fields) ----------------------------
    FIELD_COUNT: ClassVar[int] = 24
    """Number of declared dataclass fields. Exposed for invariant tests."""

    def __post_init__(self) -> None:  # noqa: C901
        """Validate invariants on construction.

        Raises:
            ValueError: If any invariant is violated (sum of weights, ordering,
                tuple length, etc.). These are **programming errors** caught
                at module load, not runtime data errors — so they raise plain
                ``ValueError`` rather than a PAV exception.
        """
        if len(self.PERIODOS_DIA) != _PERIODOS_DIA_EXPECTED_LEN:
            msg = (
                f"PERIODOS_DIA must have exactly {_PERIODOS_DIA_EXPECTED_LEN} "
                f"elements, got {len(self.PERIODOS_DIA)}"
            )
            raise ValueError(msg)
        if self.HORARIO_ACORDAR_MIN >= self.HORARIO_ACORDAR_MAX:
            msg = (
                f"HORARIO_ACORDAR_MIN ({self.HORARIO_ACORDAR_MIN}) must be < "
                f"HORARIO_ACORDAR_MAX ({self.HORARIO_ACORDAR_MAX})"
            )
            raise ValueError(msg)
        if self.HORARIO_DORMIR_MIN >= self.HORARIO_DORMIR_MAX:
            msg = (
                f"HORARIO_DORMIR_MIN ({self.HORARIO_DORMIR_MIN}) must be < "
                f"HORARIO_DORMIR_MAX ({self.HORARIO_DORMIR_MAX})"
            )
            raise ValueError(msg)
        if self.HORARIO_ULTIMA_REFEICAO_MIN >= self.HORARIO_ULTIMA_REFEICAO_MAX:
            msg = (
                f"HORARIO_ULTIMA_REFEICAO_MIN ({self.HORARIO_ULTIMA_REFEICAO_MIN}) "
                f"must be < HORARIO_ULTIMA_REFEICAO_MAX "
                f"({self.HORARIO_ULTIMA_REFEICAO_MAX})"
            )
            raise ValueError(msg)
        if self.POMODORO_BREAK_MIN >= self.POMODORO_WORK_MIN:
            msg = (
                f"POMODORO_BREAK_MIN ({self.POMODORO_BREAK_MIN}) must be < "
                f"POMODORO_WORK_MIN ({self.POMODORO_WORK_MIN})"
            )
            raise ValueError(msg)
        if self.POMODORO_ROUNDS_MIN > self.POMODORO_ROUNDS_MAX:
            msg = (
                f"POMODORO_ROUNDS_MIN ({self.POMODORO_ROUNDS_MIN}) must be <= "
                f"POMODORO_ROUNDS_MAX ({self.POMODORO_ROUNDS_MAX})"
            )
            raise ValueError(msg)
        if len(self.SONO_OPCOES_HORAS) != _SONO_OPCOES_EXPECTED_LEN:
            msg = (
                f"SONO_OPCOES_HORAS must have {_SONO_OPCOES_EXPECTED_LEN} "
                f"options, got {len(self.SONO_OPCOES_HORAS)}"
            )
            raise ValueError(msg)
        weight_sum = self.QHE_ALPHA + self.QHE_BETA + self.QHE_GAMMA
        lower_bound = 1.0 - _QHE_WEIGHT_SUM_TOLERANCE
        upper_bound = 1.0 + _QHE_WEIGHT_SUM_TOLERANCE
        if not (lower_bound <= weight_sum <= upper_bound):
            msg = (
                f"QHE weights must sum to 1.0 (±{_QHE_WEIGHT_SUM_TOLERANCE}), "
                f"got {weight_sum}"
            )
            raise ValueError(msg)
        if self.QHE_PUSH_THRESHOLD <= self.QHE_RECOVER_THRESHOLD:
            msg = (
                f"QHE_PUSH_THRESHOLD ({self.QHE_PUSH_THRESHOLD}) must be > "
                f"QHE_RECOVER_THRESHOLD ({self.QHE_RECOVER_THRESHOLD})"
            )
            raise ValueError(msg)
        non_negative_int: tuple[str, ...] = (
            "HORARIO_ACORDAR_MIN",
            "HORARIO_ACORDAR_MAX",
            "HORARIO_DORMIR_MIN",
            "HORARIO_DORMIR_MAX",
            "HORARIO_ULTIMA_REFEICAO_MIN",
            "HORARIO_ULTIMA_REFEICAO_MAX",
            "POMODORO_WORK_MIN",
            "POMODORO_BREAK_MIN",
            "POMODORO_LONG_BREAK_MIN",
            "POMODORO_ROUNDS_MIN",
            "POMODORO_ROUNDS_MAX",
            "LUZ_AZUL_CORTE",
            "AGUA_GLASSES_DIA",
            "POLICY_UPGRADE_DAYS",
            "POLICY_DOWNGRADE_DAYS",
            "POLICY_RECOVER_ENTRY_DAYS",
        )
        for name in non_negative_int:
            value: int = getattr(self, name)
            if value < 0:
                msg = f"{name} must be non-negative, got {value}"
                raise ValueError(msg)
        if not (
            _LAMBDA_LEARNING_LOWER_BOUND
            < self.LAMBDA_LEARNING_DEFAULT
            <= _LAMBDA_LEARNING_UPPER_BOUND
        ):
            msg = (
                f"LAMBDA_LEARNING_DEFAULT must be in "
                f"({_LAMBDA_LEARNING_LOWER_BOUND}, {_LAMBDA_LEARNING_UPPER_BOUND}], "
                f"got {self.LAMBDA_LEARNING_DEFAULT}"
            )
            raise ValueError(msg)

    # --- Domain helpers (pure, no I/O) -------------------------------------
    def is_valid_wake_hour(self, hour: int) -> bool:
        """Check whether ``hour`` falls within the acceptable wake window.

        Args:
            hour: Hour of the day in 24h format (0-23).

        Returns:
            ``True`` if ``HORARIO_ACORDAR_MIN <= hour <= HORARIO_ACORDAR_MAX``.
        """
        return self.HORARIO_ACORDAR_MIN <= hour <= self.HORARIO_ACORDAR_MAX

    def is_valid_sleep_hour(self, hour: int) -> bool:
        """Check whether ``hour`` falls within the acceptable sleep window.

        Args:
            hour: Hour of the day in 24h format (0-23).

        Returns:
            ``True`` if ``HORARIO_DORMIR_MIN <= hour <= HORARIO_DORMIR_MAX``.
        """
        return self.HORARIO_DORMIR_MIN <= hour <= self.HORARIO_DORMIR_MAX

    def is_valid_sleep_duration(self, hours: float) -> bool:
        """Check whether ``hours`` is an approved sleep duration.

        Args:
            hours: Sleep duration in hours (float).

        Returns:
            ``True`` if ``hours`` matches any entry in ``SONO_OPCOES_HORAS``
            within a 0.5h tolerance (inclusive boundary).
        """
        return any(
            abs(hours - option) <= _SLEEP_DURATION_TOLERANCE
            for option in self.SONO_OPCOES_HORAS
        )

    def qhe_push_active(self, qhe: float) -> bool:
        """Return ``True`` if QHE meets the PUSH threshold.

        Args:
            qhe: Computed QHE value in [0, 1].

        Returns:
            ``True`` if ``qhe >= QHE_PUSH_THRESHOLD``.
        """
        return qhe >= self.QHE_PUSH_THRESHOLD

    def qhe_recover_required(self, qhe: float) -> bool:
        """Return ``True`` if QHE is below the RECOVER threshold.

        Args:
            qhe: Computed QHE value in [0, 1].

        Returns:
            ``True`` if ``qhe < QHE_RECOVER_THRESHOLD``.
        """
        return qhe < self.QHE_RECOVER_THRESHOLD


DEFAULT: Final[PAVConstants] = PAVConstants()
"""Sprint 1A default PAV constants. Use this in production code.

This is the canonical production configuration. Custom variants can be
constructed by passing keyword overrides::

    custom = PAVConstants(HORARIO_ACORDAR_MIN=4, AGUA_GLASSES_DIA=10)
"""
