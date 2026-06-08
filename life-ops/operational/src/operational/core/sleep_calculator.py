"""Sleep calculation and quality classification (PAV §7).

This module implements the **canonical sleep model** of the
``operational`` package. The two PAV §7 functions
(:func:`calcular_horas_sono` and :func:`validar_sono_ideal`) are exposed
both as class-level static methods (for namespace grouping) and as
module-level functions (for ergonomics).

Source spec:
    * PAV ``vibe-ops/base/Produtividade Algorítmica Visual.md`` §7
      (lines 263-289) — sleep duration calculation, quality buckets,
      and the 5x4 decision matrix.

Design rules:

* **Pure functions** — no I/O, no state mutation, no logging side effects.
* **mypy --strict** compatible — every parameter and return type annotated.
* **ruff ALL** compliant — line-length 100, Google docstrings, no emojis
  in code (the only emoji characters present are the
  ``"✅"``/``"⚠️"``/``"❌"`` glyphs embedded in :data:`_STATUS_*`
  constants — these *are* the data, not decorative).
* No imports from :mod:`operational.entities`, :mod:`operational.core.*`
  (sibling), or :mod:`operational.parsers` to avoid circular dependencies.
* The canonical import paths are :mod:`operational.constants`,
  :mod:`operational.enums`, and (only the public surface of) the
  stdlib :mod:`dataclasses`.

Public surface
--------------
* :class:`SleepQuality` — namespace class wrapping the two PAV §7
  functions plus the optimal-window predicate.
* :func:`calcular_horas_sono` / :func:`validar_sono_ideal` —
  module-level aliases for the two PAV §7 functions.
* :func:`is_within_optimal_window` — convenience wrapper.
* :class:`SleepDecision` — frozen dataclass describing one cell of
  the 5x4 sleep decision matrix.
* :func:`get_sleep_matrix` — generator returning the full 5x4
  decision matrix from PAV §7 as a list of :class:`SleepDecision`
  records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from operational.constants import DEFAULT
from operational.enums import QualityLabel

__all__ = [
    "STATUS_CRITICO",
    "STATUS_HARDCORE",
    "STATUS_OK",
    "SleepDecision",
    "SleepQuality",
    "calcular_horas_sono",
    "get_sleep_matrix",
    "is_within_optimal_window",
    "validar_sono_ideal",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Decision-matrix grid (PAV §7)
_MATRIX_DORMIR: Final[tuple[int, ...]] = (18, 19, 20, 21, 23)
"""Bedtime rows of the 5x4 decision matrix (PAV §7 table)."""

# Each (wake_hour, target_hours) pair represents a column of the matrix.
# The "3am HARDCORE" column reuses the 3am wake hour but with a 4h target.
_MATRIX_ACORDAR: Final[tuple[tuple[int, int], ...]] = (
    (3, 9),
    (4, 8),
    (5, 7),
    (3, 4),  # 3am HARDCORE
)
"""Wake-up columns of the 5x4 decision matrix (PAV §7 table)."""

# Status glyphs (PAV §7 — these ARE the data, not decoration)
STATUS_OK: Final[str] = "\u2705"  # green check — exact match
"""Status glyph for ``actual == 9h`` (the 9h ideal) or the 4h HARDCORE escape hatch."""

STATUS_HARDCORE: Final[str] = "\u26a0\ufe0f"  # warning sign — in range, off target
"""Status glyph for in-range cells that are off-target (recoverable)."""

STATUS_CRITICO: Final[str] = "\u274c"  # red cross — out of range
"""Status glyph for cells that are out of PAV range or violate the HARDCORE commitment."""

# Decision-rule thresholds (PAV §1 SONO_OPCOES + ±0.5 tolerance)
_OPTIMAL_MIN_HOURS: Final[float] = 7.0
_OPTIMAL_MAX_HOURS: Final[float] = 9.0
"""Optimal sleep-duration window (PAV §1: 7-9h is the "ACEITAVEL" to "EXCELENTE" band)."""

# Hour boundaries (PAV §1)
_HOUR_MIN: Final[int] = 0
_HOUR_MAX: Final[int] = 23
"""Valid 24h clock range. Reused in input validation."""

# PAV sleep quality thresholds (PAV §7)
_SONO_EXCELENTE: Final[float] = 9.0
_SONO_BOM: Final[float] = 8.0
_SONO_ACEITAVEL: Final[float] = 7.0
_SONO_HARDCORE: Final[float] = 4.0
"""The 4 PAV §7 sleep-quality bucket thresholds."""

# PAV §7 matrix classification bounds
_RANGE_LO: Final[float] = 4.0
_RANGE_HI: Final[float] = 12.0
"""In-range actual-sleep window: 4h < actual < 12h."""

# HARDCORE magic values
_HARDCORE_BEDTIME: Final[int] = 23
_HARDCORE_WAKE_HOUR: Final[int] = 3
_HARDCORE_TARGET: Final[int] = 4
_IDEAL_SLEEP_HOURS: Final[int] = 9
"""The 9h "ideal sleep" duration used by the diagonal-✅ rule."""


# ---------------------------------------------------------------------------
# Decision matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class SleepDecision:
    """One cell of the PAV §7 5x4 sleep decision matrix.

    Each cell answers the question: *"if I commit to ``target_horas`` of
    sleep by waking at ``acordar``, what actually happens when I go to
    bed at ``dormir``?"*

    Attributes:
        dormir: Bedtime hour (0-23). PAV §7 grid rows: 18, 19, 20, 21, 23.
        acordar: Wake-up hour (0-23). PAV §7 grid columns: 3, 4, 5, 3.
        target_horas: Committed sleep duration for this column
            (PAV §1 ``SONO_OPCOES_HORAS`` = (9, 8, 7, 4)).
        actual_horas: Real sleep duration given ``dormir`` and ``acordar``,
            as computed by :func:`calcular_horas_sono`.
        status: Decision glyph — :data:`STATUS_OK`, :data:`STATUS_HARDCORE`,
            or :data:`STATUS_CRITICO`. **The glyphs are PAV §7 data.**
        is_optimal: ``True`` iff ``status == STATUS_OK``.
    """

    dormir: int
    acordar: int
    target_horas: int
    actual_horas: float
    status: str
    is_optimal: bool

    def __post_init__(self) -> None:
        """Validate invariant: status must be one of the three glyphs.

        Raises:
            ValueError: If ``status`` is not a recognised glyph. Caught at
                construction time, not at every read — this is a
                programming error, not a runtime data error.
        """
        if self.status not in {STATUS_OK, STATUS_HARDCORE, STATUS_CRITICO}:
            msg = f"status must be one of the 3 PAV glyphs, got {self.status!r}"
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Quality namespace
# ---------------------------------------------------------------------------


class SleepQuality:
    """Namespace for the two PAV §7 sleep functions + the optimal predicate.

    All methods are ``@staticmethod`` so the class is purely a grouping
    device — it has no instance state, no ``__init__``, and can be used
    interchangeably with the module-level function aliases.

    The class form is the **canonical** API; the module-level functions
    (:func:`calcular_horas_sono`, :func:`validar_sono_ideal`) are
    ergonomic shortcuts that delegate here.
    """

    @staticmethod
    def calcular_horas_sono(hora_dormir: int, hora_acordar: int) -> float:
        """Calculate sleep duration in hours (PAV §7).

        Handles the two cases from the spec:

        * **Crossed midnight** (most common): ``hora_acordar < hora_dormir``.
          Result is ``(24 - hora_dormir) + hora_acordar``.
        * **Same day** (rare, e.g. nap): ``hora_acordar >= hora_dormir``.
          Result is ``hora_acordar - hora_dormir``.

        Args:
            hora_dormir: Bedtime hour in 24h format (0-23). E.g. ``22`` for 10pm.
            hora_acordar: Wake-up hour in 24h format (0-23). E.g. ``6`` for 6am.

        Returns:
            Sleep duration in hours. Always ``>= 0``. Can exceed 12 if the
            schedule is unusual (e.g. bed at 18h, wake at 11h = 17h), which
            the caller should treat as a data error.

        Raises:
            ValueError: If either hour is outside ``[0, 23]``. Booleans
                are accepted as ``int`` per PEP 285 and rejected explicitly.
        """
        if isinstance(hora_dormir, bool) or isinstance(hora_acordar, bool):
            msg = "hours must be int, not bool"
            raise TypeError(msg)
        if not isinstance(hora_dormir, int) or not isinstance(hora_acordar, int):
            msg = (
                f"hours must be int, got "
                f"hora_dormir={type(hora_dormir).__name__}, "
                f"hora_acordar={type(hora_acordar).__name__}"
            )
            raise TypeError(msg)
        if not _HOUR_MIN <= hora_dormir <= _HOUR_MAX:
            msg = f"hora_dormir must be in [0, 23], got {hora_dormir}"
            raise ValueError(msg)
        if not _HOUR_MIN <= hora_acordar <= _HOUR_MAX:
            msg = f"hora_acordar must be in [0, 23], got {hora_acordar}"
            raise ValueError(msg)
        if hora_acordar < hora_dormir:  # Cruzou meia-noite (PAV §7)
            return float((24 - hora_dormir) + hora_acordar)
        return float(hora_acordar - hora_dormir)

    @staticmethod
    def validar_sono_ideal(horas_sono: float) -> QualityLabel:
        """Classify sleep duration into a :class:`QualityLabel` (PAV §7).

        Buckets (descending order, first match wins):

        * ``>= 9`` → :attr:`QualityLabel.EXCELENTE`
        * ``>= 8`` → :attr:`QualityLabel.BOM`
        * ``>= 7`` → :attr:`QualityLabel.ACEITAVEL`
        * ``>= 4`` → :attr:`QualityLabel.HARDCORE`
        * else    → :attr:`QualityLabel.CRITICO`

        Args:
            horas_sono: Sleep duration in hours (float). Negative values
                are rejected as a programming error.

        Returns:
            The matching :class:`QualityLabel` member.

        Raises:
            ValueError: If ``horas_sono`` is negative.
        """
        if not isinstance(horas_sono, (int, float)) or isinstance(horas_sono, bool):
            msg = f"horas_sono must be numeric, got {type(horas_sono).__name__}"
            raise TypeError(msg)
        if horas_sono < _HOUR_MIN:
            msg = f"horas_sono must be non-negative, got {horas_sono}"
            raise ValueError(msg)
        if horas_sono >= _SONO_EXCELENTE:
            return QualityLabel.EXCELENTE
        if horas_sono >= _SONO_BOM:
            return QualityLabel.BOM
        if horas_sono >= _SONO_ACEITAVEL:
            return QualityLabel.ACEITAVEL
        if horas_sono >= _SONO_HARDCORE:
            return QualityLabel.HARDCORE
        return QualityLabel.CRITICO

    @staticmethod
    def is_optimal_sleep(hora_dormir: int, hora_acordar: int) -> bool:
        """Check if the sleep schedule is in the PAV §7 optimal window.

        The optimal window is the intersection of three predicates:

        1. ``DEFAULT.HORARIO_DORMIR_MIN <= hora_dormir <= DEFAULT.HORARIO_DORMIR_MAX``
        2. ``DEFAULT.HORARIO_ACORDAR_MIN <= hora_acordar <= DEFAULT.HORARIO_ACORDAR_MAX``
        3. ``7 <= calcular_horas_sono(hora_dormir, hora_acordar) <= 9``

        Args:
            hora_dormir: Bedtime hour (0-23).
            hora_acordar: Wake-up hour (0-23).

        Returns:
            ``True`` iff all three predicates hold.
        """
        horas = SleepQuality.calcular_horas_sono(hora_dormir, hora_acordar)
        optimal_dormir = (
            DEFAULT.HORARIO_DORMIR_MIN <= hora_dormir <= DEFAULT.HORARIO_DORMIR_MAX
        )
        optimal_acordar = (
            DEFAULT.HORARIO_ACORDAR_MIN <= hora_acordar <= DEFAULT.HORARIO_ACORDAR_MAX
        )
        optimal_duration = _OPTIMAL_MIN_HOURS <= horas <= _OPTIMAL_MAX_HOURS
        return optimal_dormir and optimal_acordar and optimal_duration


# ---------------------------------------------------------------------------
# Module-level aliases (ergonomic — delegate to SleepQuality)
# ---------------------------------------------------------------------------


def calcular_horas_sono(hora_dormir: int, hora_acordar: int) -> float:
    """Module-level alias for :meth:`SleepQuality.calcular_horas_sono`."""
    return SleepQuality.calcular_horas_sono(hora_dormir, hora_acordar)


def validar_sono_ideal(horas_sono: float) -> QualityLabel:
    """Module-level alias for :meth:`SleepQuality.validar_sono_ideal`."""
    return SleepQuality.validar_sono_ideal(horas_sono)


def is_within_optimal_window(hora_dormir: int, hora_acordar: int) -> bool:
    """Module-level alias for :meth:`SleepQuality.is_optimal_sleep`."""
    return SleepQuality.is_optimal_sleep(hora_dormir, hora_acordar)


# ---------------------------------------------------------------------------
# Decision matrix generator
# ---------------------------------------------------------------------------


def _classify(dormir: int, acordar: int, target_horas: int, actual_horas: float) -> str:
    """Classify a matrix cell into a PAV §7 status glyph.

    The PAV §7 decision rule has **three layers** that combine to produce
    the 5x4 table. The rule is **not** a simple "actual == target"
    match — the column headers (e.g. "3am (9h)", "4am (8h)") are
    descriptive of the column's *scenario*, but the :data:`STATUS_OK`
    glyph is awarded on a **9h ideal diagonal** plus the HARDCORE
    escape hatch.

    The three layers, in order:

    1. **HARDCORE escape hatch** — the cell ``(23h, 3am, 4h)`` is the
       only valid 23h schedule. It is :data:`STATUS_OK`.
    2. **23h strictness** — every other 23h cell is :data:`STATUS_CRITICO`
       (you signed up for HARDCORE mode by going to bed at 23h; any
       other wake-up is a violation).
    3. **4h HARDCORE column strictness** — the 4h target column from
       any non-23h bedtime is :data:`STATUS_CRITICO` (you would have
       slept 6-9h, failing the HARDCORE commitment).
    4. **9h ideal diagonal** — for the remaining cells,
       :data:`STATUS_OK` is awarded when the actual sleep is exactly
       9h (the PAV gold standard). The diagonal of 9h cells is
       ``(18, 3)``, ``(19, 4)``, ``(20, 5)``.
    5. **In-range fallback** — if ``4 < actual < 12`` and none of the
       above apply, the cell is :data:`STATUS_HARDCORE` (recoverable,
       off-target).
    6. **Out-of-range** — anything else (< 4 or > 12) is
       :data:`STATUS_CRITICO`.

    Args:
        dormir: Bedtime hour (0-23).
        acordar: Wake-up hour (0-23).
        target_horas: Committed sleep duration for this column
            (one of PAV §1 :data:`PAVConstants.SONO_OPCOES_HORAS`).
        actual_horas: Real sleep duration from :func:`calcular_horas_sono`.

    Returns:
        One of :data:`STATUS_OK`, :data:`STATUS_HARDCORE`, :data:`STATUS_CRITICO`.
    """
    # Layer 1: HARDCORE escape hatch.
    if (
        dormir == _HARDCORE_BEDTIME
        and acordar == _HARDCORE_WAKE_HOUR
        and target_horas == _HARDCORE_TARGET
    ):
        return STATUS_OK
    # Layer 2: 23h strictness — every other 23h cell is critical.
    if dormir == _HARDCORE_BEDTIME:
        return STATUS_CRITICO
    # Layer 3: 4h HARDCORE column strictness from non-23h bedtimes.
    if target_horas == _HARDCORE_TARGET and dormir != _HARDCORE_BEDTIME:
        return STATUS_CRITICO
    # Layer 4: 9h ideal diagonal.
    if actual_horas == _IDEAL_SLEEP_HOURS:
        return STATUS_OK
    # Layer 5: in-range fallback.
    if _RANGE_LO < actual_horas < _RANGE_HI:
        return STATUS_HARDCORE
    # Layer 6: out-of-range.
    return STATUS_CRITICO


def get_sleep_matrix() -> list[SleepDecision]:
    """Generate the full 5x4 sleep decision matrix from PAV §7.

    Iterates over the 5 bedtimes (18, 19, 20, 21, 23) and 4 wake-up
    scenarios (3am-9h, 4am-8h, 5am-7h, 3am-HARDCORE-4h), producing
    **20 cells** total.

    Returns:
        A list of 20 :class:`SleepDecision` records, ordered by
        ``(dormir ascending, acordar ascending)``. Use
        :func:`render_sleep_matrix` to format as an ASCII table.
    """
    decisions: list[SleepDecision] = []
    for dormir in _MATRIX_DORMIR:
        for acordar, target in _MATRIX_ACORDAR:
            actual = calcular_horas_sono(dormir, acordar)
            status = _classify(dormir, acordar, target, actual)
            decisions.append(
                SleepDecision(
                    dormir=dormir,
                    acordar=acordar,
                    target_horas=target,
                    actual_horas=actual,
                    status=status,
                    is_optimal=(status == STATUS_OK),
                )
            )
    return decisions


def render_sleep_matrix(decisions: list[SleepDecision] | None = None) -> str:
    """Format the sleep decision matrix as an ASCII table.

    Args:
        decisions: Optional pre-computed list. If ``None``, calls
            :func:`get_sleep_matrix` internally.

    Returns:
        A multi-line string with column headers (wake-up hour + target)
        and row headers (bedtime hour). Useful for CLI display and
        snapshot tests.
    """
    cells = decisions if decisions is not None else get_sleep_matrix()
    headers: list[str] = [
        "Dormir \\ Acordar",
        *(f"{a:>02d}h ({t}h)" for a, t in _MATRIX_ACORDAR),
    ]
    rows: list[list[str]] = [headers]
    for dormir in _MATRIX_DORMIR:
        row: list[str] = [f"{dormir}h"]
        for acordar, target in _MATRIX_ACORDAR:
            cell = next(
                c
                for c in cells
                if c.dormir == dormir and c.acordar == acordar and c.target_horas == target
            )
            row.append(f"{cell.status} {cell.actual_horas:>4.0f}h")
        rows.append(row)
    widths: list[int] = [max(len(r[i]) for r in rows) for i in range(len(headers))]
    lines: list[str] = []
    for i, row in enumerate(rows):
        lines.append(" | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)))
        if i == 0:
            lines.append("-+-".join("-" * w for w in widths))
    return "\n".join(lines)
