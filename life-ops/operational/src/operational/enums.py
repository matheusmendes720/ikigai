"""Enumerations for the operational domain.

This module defines the canonical set of string-based enumerations used across
the ``operational`` package. All enums inherit from :class:`enum.StrEnum`
(Python 3.11+ stdlib) so that values are strings and serialize naturally to
JSON, YAML, and SQLite TEXT columns.

Source-of-truth references:

* **PAV** ``vibe-ops/base/Produtividade Algorítmica Visual.md`` — routines,
  rituals, sleep/quality, pomodoro state machine.
* **PRD-02** ``vibe-ops/planning/PRD-02-habit-tracker.md`` — habit categories
  and effectiveness scoring.
* **PRD-05** ``vibe-ops/planning/PRD-05-metrics-health.md`` — energy levels,
  weekly aggregation labels, and alert severities.
* **PRD-06** — four-state operational policy (PUSH / MAINTAIN / REDUCE /
  RECOVER) with hysteresis.

Conventions:

* Every enum is **frozen** (StrEnum default) — no mutation allowed.
* Every enum has an explicit ``__all__`` entry and a class-level docstring.
* Helper methods are pure functions that do not raise for normal inputs.
* Roundtrip ``Enum(value) -> Enum`` and ``Enum.value -> str`` are guaranteed.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AlertLevel",
    "CausaDesvio",
    "EnergyLevel",
    "EstadoPsicomatico",
    "HabitCategory",
    "NivelInfracao",
    "Period",
    "PolicyState",
    "PomodoroState",
    "QualityLabel",
    "RitualType",
    "RoutineType",
    "TipoDia",
    "WeekLabel",
    "WorkoutTipo",
]


# ---------------------------------------------------------------------------
# Domain constants (PAV §3 / §7, PRD-05 / PRD-06)
# ---------------------------------------------------------------------------

# Period hours (PAV §3)
_PERIOD_START_HOURS: dict[str, int] = {"MANHA": 3, "TARDE": 8, "NOITE": 18}
_PERIOD_END_HOURS: dict[str, int] = {"MANHA": 5, "TARDE": 17, "NOITE": 21}

# Energy level ordinals (PRD-05)
_ENERGY_NUMERIC: dict[str, int] = {"H": 2, "M": 1, "L": 0}
_ENERGY_LABEL: dict[str, str] = {"H": "High", "M": "Medium", "L": "Low"}

# QualityLabel thresholds (PAV §7) — in hours
_QL_EXCELENTE_MIN = 9.0
_QL_BOM_MIN = 8.0
_QL_ACEITAVEL_MIN = 7.0
_QL_HARDCORE_MIN = 4.0
_QUALITY_MIN_HOURS: dict[str, float] = {
    "excelente": _QL_EXCELENTE_MIN,
    "bom": _QL_BOM_MIN,
    "aceitavel": _QL_ACEITAVEL_MIN,
    "hardcore": _QL_HARDCORE_MIN,
    "critico": 0.0,
}

# PolicyState ordinals (PRD-06)
_POLICY_ORDINAL: dict[str, int] = {"PUSH": 0, "MAINTAIN": 1, "REDUCE": 2, "RECOVER": 3}

# WeekLabel thresholds (PRD-05)
_WL_EXCELENTE_MIN = 0.9
_WL_BOM_MIN = 0.75
_WL_MEDIO_MIN = 0.6
_WL_RUIM_MIN = 0.4
_WEEK_MIN_SCORE: dict[str, float] = {
    "excellent": _WL_EXCELENTE_MIN,
    "good": _WL_BOM_MIN,
    "average": _WL_MEDIO_MIN,
    "poor": _WL_RUIM_MIN,
    "recovery": 0.0,
}

# AlertLevel severities (PRD-05)
_ALERT_SEVERITY: dict[str, int] = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}


class Period(StrEnum):
    """The three daily periods defined in PAV §3.

    Used to bucket routines, time blocks, and journal entries by time of day.

    Time windows (PAV §3):
        * ``MANHA`` — 03:00 to 05:00 (early start, pre-work)
        * ``TARDE`` — 08:00 to 17:00 (core work day)
        * ``NOITE`` — 18:00 to 21:00 (shutdown, review, wind-down)
    """

    MANHA = "MANHA"
    TARDE = "TARDE"
    NOITE = "NOITE"

    @property
    def default_start_hour(self) -> int:
        """Return the default start hour (0-23) for this period.

        Returns:
            int: Hour of day in 24h format. ``3`` for MANHA, ``8`` for
            TARDE, ``18`` for NOITE.
        """
        return _PERIOD_START_HOURS[self.value]

    @property
    def default_end_hour(self) -> int:
        """Return the default end hour (0-23) for this period.

        Returns:
            int: Hour of day in 24h format. ``5`` for MANHA, ``17`` for
            TARDE, ``21`` for NOITE.
        """
        return _PERIOD_END_HOURS[self.value]

    @property
    def is_work_period(self) -> bool:
        """Return ``True`` if this period is reserved for core work.

        Returns:
            bool: ``True`` only for ``TARDE``. MANHA and NOITE are
            ritual/transition periods.
        """
        return self is Period.TARDE


class RoutineType(StrEnum):
    """Routine categories from PAV §3.

    Each routine in a day is tagged with one of these types to drive
    scheduling, validation, and reporting.
    """

    ENTRY = "ENTRY"
    CORE = "CORE"
    TRANSITION = "TRANSITION"
    EXIT = "EXIT"

    @property
    def is_ritual(self) -> bool:
        """Return ``True`` if this routine is a ritual (entry/exit/transition).

        Returns:
            bool: ``True`` for ENTRY, TRANSITION, EXIT. ``False`` for CORE.
        """
        return self in {RoutineType.ENTRY, RoutineType.TRANSITION, RoutineType.EXIT}

    @property
    def is_boundary(self) -> bool:
        """Return ``True`` if this routine happens at a day boundary.

        Returns:
            bool: ``True`` for ENTRY (start of day) and EXIT (end of day).
        """
        return self in {RoutineType.ENTRY, RoutineType.EXIT}


class RitualType(StrEnum):
    """Discrete ritual types that appear inside routines (PAV §3)."""

    HYDRATION = "HYDRATION"
    MEDITATION = "MEDITATION"
    SHUTDOWN = "SHUTDOWN"
    REVIEW = "REVIEW"
    MORNING = "MORNING"
    EVENING = "EVENING"

    @property
    def default_period(self) -> Period | None:
        """Return the period this ritual naturally belongs to.

        Returns:
            Period | None: The associated :class:`Period`, or ``None`` if
            the ritual can occur in any period.
        """
        mapping: dict[str, Period | None] = {
            "HYDRATION": None,
            "MEDITATION": Period.MANHA,
            "SHUTDOWN": Period.NOITE,
            "REVIEW": Period.NOITE,
            "MORNING": Period.MANHA,
            "EVENING": Period.NOITE,
        }
        return mapping[self.value]

    @property
    def is_evening(self) -> bool:
        """Return ``True`` if this ritual belongs to the evening/night block.

        Returns:
            bool: ``True`` for SHUTDOWN, REVIEW, EVENING.
        """
        return self in {RitualType.SHUTDOWN, RitualType.REVIEW, RitualType.EVENING}


class HabitCategory(StrEnum):
    """Habit taxonomy from PRD-02 §2.

    Every :class:`operational.entities.Habit` must be tagged with one of
    these categories. Categories are used for streak aggregation, balance
    analysis, and Q_HE normalization.
    """

    PHYSIOLOGICAL = "physiological"
    COGNITIVE = "cognitive"
    SOCIAL = "social"
    CREATIVE = "creative"
    RITUAL = "ritual"

    @property
    def is_body(self) -> bool:
        """Return ``True`` if the category targets the body.

        Returns:
            bool: ``True`` only for ``PHYSIOLOGICAL``.
        """
        return self is HabitCategory.PHYSIOLOGICAL

    @property
    def is_mind(self) -> bool:
        """Return ``True`` if the category targets the mind.

        Returns:
            bool: ``True`` for ``COGNITIVE`` and ``CREATIVE``.
        """
        return self in {HabitCategory.COGNITIVE, HabitCategory.CREATIVE}


class EnergyLevel(StrEnum):
    """Self-reported energy level for a time block (PRD-05)."""

    HIGH = "H"
    MEDIUM = "M"
    LOW = "L"

    @property
    def numeric(self) -> int:
        """Return an ordinal numeric value for math (H=2, M=1, L=0).

        Returns:
            int: ``2`` for HIGH, ``1`` for MEDIUM, ``0`` for LOW.
        """
        return _ENERGY_NUMERIC[self.value]

    @property
    def label(self) -> str:
        """Return a human-readable label.

        Returns:
            str: ``"High"``, ``"Medium"`` or ``"Low"``.
        """
        return _ENERGY_LABEL[self.value]

    def __lt__(self, other: object) -> bool:
        """Order by numeric value: LOW < MEDIUM < HIGH.

        Args:
            other: Object to compare against. Must be an EnergyLevel.

        Returns:
            bool: ``True`` when self is strictly less energetic than other.

        Raises:
            TypeError: If ``other`` is not an :class:`EnergyLevel`.
        """
        if not isinstance(other, EnergyLevel):
            return NotImplemented
        return self.numeric < other.numeric

    def __le__(self, other: object) -> bool:
        """Order by numeric value (less-or-equal).

        Args:
            other: Object to compare against. Must be an EnergyLevel.

        Returns:
            bool: ``True`` when self is not more energetic than other.
        """
        if not isinstance(other, EnergyLevel):
            return NotImplemented
        return self.numeric <= other.numeric

    def __gt__(self, other: object) -> bool:
        """Order by numeric value (greater-than).

        Args:
            other: Object to compare against. Must be an EnergyLevel.

        Returns:
            bool: ``True`` when self is strictly more energetic than other.
        """
        if not isinstance(other, EnergyLevel):
            return NotImplemented
        return self.numeric > other.numeric

    def __ge__(self, other: object) -> bool:
        """Order by numeric value (greater-or-equal).

        Args:
            other: Object to compare against. Must be an EnergyLevel.

        Returns:
            bool: ``True`` when self is not less energetic than other.
        """
        if not isinstance(other, EnergyLevel):
            return NotImplemented
        return self.numeric >= other.numeric


class QualityLabel(StrEnum):
    """Sleep/energy quality label (PAV §7).

    Buckets sleep duration into human-readable labels used for daily
    reporting and weekly aggregation.
    """

    EXCELENTE = "excelente"
    BOM = "bom"
    ACEITAVEL = "aceitavel"
    HARDCORE = "hardcore"
    CRITICO = "critico"

    @property
    def min_hours(self) -> float:
        """Return the minimum number of sleep hours for this label.

        Returns:
            float: Lower bound of the bucket. ``9`` for EXCELENTE,
            ``8`` for BOM, ``7`` for ACEITAVEL, ``4`` for HARDCORE,
            ``0`` for CRITICO.
        """
        return _QUALITY_MIN_HOURS[self.value]

    @classmethod
    def from_hours(cls, hours: float) -> QualityLabel:
        """Classify a sleep duration into a quality label.

        Args:
            hours: Sleep duration in hours. Negative values are clamped
                to ``0`` and treated as CRITICO.

        Returns:
            QualityLabel: The matching bucket. Order is checked
            descending: ``EXCELENTE`` → ``BOM`` → ``ACEITAVEL`` →
            ``HARDCORE`` → ``CRITICO``.
        """
        safe = max(0.0, float(hours))
        if safe >= _QL_EXCELENTE_MIN:
            return cls.EXCELENTE
        if safe >= _QL_BOM_MIN:
            return cls.BOM
        if safe >= _QL_ACEITAVEL_MIN:
            return cls.ACEITAVEL
        if safe >= _QL_HARDCORE_MIN:
            return cls.HARDCORE
        return cls.CRITICO


class PomodoroState(StrEnum):
    """Pomodoro state machine (PAV §9).

    Lifecycle::

        IDLE ──▶ WORK ──▶ BREAK ──▶ WORK ──▶ BREAK ──▶ ...
                       └──── (after N cycles) ──▶ LONG_BREAK
        any state ──▶ PAUSED ──▶ previous state
        WORK ──▶ SKIPPED ──▶ IDLE
        LONG_BREAK ──▶ COMPLETE ──▶ IDLE
    """

    IDLE = "IDLE"
    WORK = "WORK"
    BREAK = "BREAK"
    LONG_BREAK = "LONG_BREAK"
    PAUSED = "PAUSED"
    SKIPPED = "SKIPPED"
    COMPLETE = "COMPLETE"

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` if no further automatic transitions are possible.

        Returns:
            bool: ``True`` for IDLE, SKIPPED, COMPLETE.
        """
        return self in {PomodoroState.IDLE, PomodoroState.SKIPPED, PomodoroState.COMPLETE}

    @property
    def is_active(self) -> bool:
        """Return ``True`` if a timer is currently running.

        Returns:
            bool: ``True`` for WORK, BREAK, LONG_BREAK.
        """
        return self in {PomodoroState.WORK, PomodoroState.BREAK, PomodoroState.LONG_BREAK}

    @property
    def is_paused(self) -> bool:
        """Return ``True`` if the timer is currently paused.

        Returns:
            bool: ``True`` only for ``PAUSED``.
        """
        return self is PomodoroState.PAUSED

    def can_transition_to(self, other: PomodoroState) -> bool:
        """Check whether ``self`` may transition to ``other``.

        Allowed transitions:

        * ``IDLE`` → ``WORK``
        * ``WORK`` → ``BREAK`` or ``SKIPPED``
        * ``BREAK`` → ``WORK`` or ``LONG_BREAK`` (every Nth cycle)
        * ``LONG_BREAK`` → ``COMPLETE``
        * any non-terminal → ``PAUSED``
        * ``PAUSED`` → ``IDLE`` (resume goes through the orchestrator)

        Args:
            other: Target :class:`PomodoroState`.

        Returns:
            bool: ``True`` if the transition is allowed.
        """
        allowed: dict[PomodoroState, frozenset[PomodoroState]] = {
            PomodoroState.IDLE: frozenset({PomodoroState.WORK, PomodoroState.PAUSED}),
            PomodoroState.WORK: frozenset(
                {PomodoroState.BREAK, PomodoroState.SKIPPED, PomodoroState.PAUSED}
            ),
            PomodoroState.BREAK: frozenset(
                {
                    PomodoroState.WORK,
                    PomodoroState.LONG_BREAK,
                    PomodoroState.PAUSED,
                }
            ),
            PomodoroState.LONG_BREAK: frozenset({PomodoroState.COMPLETE, PomodoroState.PAUSED}),
            PomodoroState.PAUSED: frozenset(
                {
                    PomodoroState.IDLE,
                    PomodoroState.WORK,
                    PomodoroState.BREAK,
                    PomodoroState.LONG_BREAK,
                }
            ),
            PomodoroState.SKIPPED: frozenset({PomodoroState.IDLE}),
            PomodoroState.COMPLETE: frozenset({PomodoroState.IDLE}),
        }
        return other in allowed[self]


class PolicyState(StrEnum):
    """Four-state operational regime with hysteresis (PRD-06).

    Order represents **load**, not time: PUSH is the most productive,
    RECOVER is the most protective. The state machine uses hysteresis
    bands to avoid flapping between adjacent states.
    """

    PUSH = "PUSH"
    MAINTAIN = "MAINTAIN"
    REDUCE = "REDUCE"
    RECOVER = "RECOVER"

    @property
    def ordinal(self) -> int:
        """Return the ordinal position (0-based).

        Returns:
            int: ``0`` for PUSH, ``1`` for MAINTAIN, ``2`` for REDUCE,
            ``3`` for RECOVER.
        """
        return _POLICY_ORDINAL[self.value]

    @property
    def is_protective(self) -> bool:
        """Return ``True`` if this state is protective (load reduction).

        Returns:
            bool: ``True`` for REDUCE and RECOVER.
        """
        return self in {PolicyState.REDUCE, PolicyState.RECOVER}

    @property
    def is_productive(self) -> bool:
        """Return ``True`` if this state allows full productivity.

        Returns:
            bool: ``True`` for PUSH and MAINTAIN.
        """
        return self in {PolicyState.PUSH, PolicyState.MAINTAIN}

    @property
    def is_critical(self) -> bool:
        """Return ``True`` if this state mandates hard stop.

        Returns:
            bool: ``True`` only for RECOVER.
        """
        return self is PolicyState.RECOVER

    def __lt__(self, other: object) -> bool:
        """Order by ordinal (PUSH < MAINTAIN < REDUCE < RECOVER).

        Args:
            other: Object to compare. Must be a :class:`PolicyState`.

        Returns:
            bool: ``True`` if self is less loaded than other.
        """
        if not isinstance(other, PolicyState):
            return NotImplemented
        return self.ordinal < other.ordinal

    def __le__(self, other: object) -> bool:
        """Order by ordinal (less-or-equal).

        Args:
            other: Object to compare. Must be a :class:`PolicyState`.

        Returns:
            bool: ``True`` if self is not more loaded than other.
        """
        if not isinstance(other, PolicyState):
            return NotImplemented
        return self.ordinal <= other.ordinal

    def __gt__(self, other: object) -> bool:
        """Order by ordinal (greater-than).

        Args:
            other: Object to compare. Must be a :class:`PolicyState`.

        Returns:
            bool: ``True`` if self is more loaded than other.
        """
        if not isinstance(other, PolicyState):
            return NotImplemented
        return self.ordinal > other.ordinal

    def __ge__(self, other: object) -> bool:
        """Order by ordinal (greater-or-equal).

        Args:
            other: Object to compare. Must be a :class:`PolicyState`.

        Returns:
            bool: ``True`` if self is not less loaded than other.
        """
        if not isinstance(other, PolicyState):
            return NotImplemented
        return self.ordinal >= other.ordinal

    def can_step_to(self, target: PolicyState) -> bool:
        """Check whether a one-step transition is allowed by hysteresis.

        A direct transition is allowed when the ordinal difference is
        exactly ``±1``. Jumps of size ``2`` (e.g. PUSH → RECOVER) must
        traverse an intermediate state.

        Args:
            target: Desired next :class:`PolicyState`.

        Returns:
            bool: ``True`` if a single step is permitted.
        """
        return abs(self.ordinal - target.ordinal) == 1


class WeekLabel(StrEnum):
    """Weekly aggregation label (PRD-05)."""

    EXCELENTE = "excellent"
    BOM = "good"
    MEDIO = "average"
    RUIM = "poor"
    RECUPERACAO = "recovery"

    @property
    def min_score(self) -> float:
        """Return the minimum Q_HE-like score for this label.

        Returns:
            float: Lower bound of the bucket. ``0.9`` for EXCELENTE,
            ``0.75`` for BOM, ``0.6`` for MEDIO, ``0.4`` for RUIM,
            ``0.0`` for RECUPERACAO.
        """
        return _WEEK_MIN_SCORE[self.value]

    @classmethod
    def from_score(cls, score: float) -> WeekLabel:
        """Classify a normalized weekly score into a label.

        Args:
            score: Normalized score in ``[0.0, 1.0]``. Out-of-range
                values are clamped.

        Returns:
            WeekLabel: The matching bucket.
        """
        safe = max(0.0, min(1.0, float(score)))
        if safe >= _WL_EXCELENTE_MIN:
            return cls.EXCELENTE
        if safe >= _WL_BOM_MIN:
            return cls.BOM
        if safe >= _WL_MEDIO_MIN:
            return cls.MEDIO
        if safe >= _WL_RUIM_MIN:
            return cls.RUIM
        return cls.RECUPERACAO


class AlertLevel(StrEnum):
    """Severity tier for metric alerts (PRD-05)."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    @property
    def severity(self) -> int:
        """Return an ordinal severity (0, 1, 2).

        Returns:
            int: ``0`` for INFO, ``1`` for WARNING, ``2`` for CRITICAL.
        """
        return _ALERT_SEVERITY[self.value]

    @property
    def requires_action(self) -> bool:
        """Return ``True`` if this alert must be acted upon.

        Returns:
            bool: ``True`` for WARNING and CRITICAL.
        """
        return self is not AlertLevel.INFO

    def __lt__(self, other: object) -> bool:
        """Order by severity.

        Args:
            other: Object to compare. Must be an :class:`AlertLevel`.

        Returns:
            bool: ``True`` if self is less severe than other.
        """
        if not isinstance(other, AlertLevel):
            return NotImplemented
        return self.severity < other.severity

    def __le__(self, other: object) -> bool:
        """Order by severity (less-or-equal).

        Args:
            other: Object to compare. Must be an :class:`AlertLevel`.

        Returns:
            bool: ``True`` if self is not more severe than other.
        """
        if not isinstance(other, AlertLevel):
            return NotImplemented
        return self.severity <= other.severity

    def __gt__(self, other: object) -> bool:
        """Order by severity (greater-than).

        Args:
            other: Object to compare. Must be an :class:`AlertLevel`.

        Returns:
            bool: ``True`` if self is more severe than other.
        """
        if not isinstance(other, AlertLevel):
            return NotImplemented
        return self.severity > other.severity

    def __ge__(self, other: object) -> bool:
        """Order by severity (greater-or-equal).

        Args:
            other: Object to compare. Must be an :class:`AlertLevel`.

        Returns:
            bool: ``True`` if self is not less severe than :attr:`other`.
        """
        if not isinstance(other, AlertLevel):
            return NotImplemented
        return self.severity >= other.severity


# ===========================================================================
# V3 additions — spec PAV §3 (Camada 1: Enums categóricos)
# ===========================================================================


class TipoDia(StrEnum):
    """Tipo de dia (PAV §3 V3).

    Categoriza o dia conforme o contexto operacional:

    * ``CURSO`` — dia útil com SENAI 6-12h (hardwork reduzido)
    * ``LIVRE`` — fim de semana ou folga (hardwork maximizado)
    * ``HARDCORE`` — deadline emergencial (modo emergência)
    * ``DESCANSO`` — recuperação obrigatória após hardcore

    Cada tipo implica um orçado de hardwork diferente. Veja a função
    :func:`operational.reports.budget.budget_for_day_type`.
    """

    CURSO = "curso"
    LIVRE = "livre"
    HARDCORE = "hardcore"
    DESCANSO = "descanso"

    @property
    def orcado_min_padrao(self) -> int:
        """Retorna o orçamento padrão de hardwork para este tipo de dia.

        Returns:
            int: Minutos de hardwork orçados.
        """
        mapping: dict[str, int] = {
            "curso": 240,      # 4h
            "livre": 540,      # 9h
            "hardcore": 660,   # 11h
            "descanso": 120,   # 2h
        }
        return mapping[self.value]

    @property
    def is_work_intensive(self) -> bool:
        """True se o dia exige alta carga de hardwork.

        Returns:
            bool: ``True`` para ``LIVRE`` e ``HARDCORE``.
        """
        return self in {TipoDia.LIVRE, TipoDia.HARDCORE}


class NivelInfracao(StrEnum):
    """Nível de infração (PAV §3 V3).

    Classifica um desvio da rotina padrão em função do tempo de variação.

    * ``LEVE``       — < 30 min de desvio
    * ``MEDIA``      — 30-60 min
    * ``GRAVE``      — 60-120 min
    * ``GRAVISSIMA`` — > 120 min ou violação grave (acordou > 6h)
    """

    LEVE = "leve"
    MEDIA = "media"
    GRAVE = "grave"
    GRAVISSIMA = "gravissima"

    @classmethod
    def from_minutes(cls, minutes: int) -> "NivelInfracao":
        """Classifica o nível de infração pelo desvio em minutos.

        Args:
            minutes: Desvio absoluto em minutos (sempre >= 0).

        Returns:
            NivelInfracao: O nível apropriado.
        """
        if minutes < 30:
            return cls.LEVE
        if minutes < 60:
            return cls.MEDIA
        if minutes < 120:
            return cls.GRAVE
        return cls.GRAVISSIMA

    @property
    def color_emoji(self) -> str:
        """Emoji semafórico para o nível.

        Returns:
            str: Emoji correspondente.
        """
        mapping: dict[str, str] = {
            "leve": "🟡",
            "media": "🟠",
            "grave": "🔴",
            "gravissima": "🚨",
        }
        return mapping[self.value]


class EstadoPsicomatico(StrEnum):
    """Estado psicomático (PAV §3 V3 — combinação de energia + foco 1-10).

    Mapeia uma pontuação 1-10 (energia ou foco) para um estado semântico.
    Útil para classificar self-reportings de energia e foco em texto.
    """

    EXCELENTE = "excelente"  # 9-10
    BOM = "bom"              # 7-8
    REGULAR = "regular"      # 5-6
    RUIM = "ruim"            # 3-4
    CRITICO = "critico"      # 1-2

    @classmethod
    def from_score(cls, score: int) -> "EstadoPsicomatico":
        """Converte pontuação 1-10 em estado.

        Args:
            score: Pontuação inteira 1-10.

        Returns:
            EstadoPsicomatico: O estado correspondente.
        """
        if score >= 9:
            return cls.EXCELENTE
        if score >= 7:
            return cls.BOM
        if score >= 5:
            return cls.REGULAR
        if score >= 3:
            return cls.RUIM
        return cls.CRITICO

    @property
    def emoji(self) -> str:
        """Emoji representativo do estado.

        Returns:
            str: Emoji (🟢 / 🟡 / 🟠 / 🔴 / ⛔).
        """
        mapping: dict[str, str] = {
            "excelente": "🟢",
            "bom": "🟢",
            "regular": "🟡",
            "ruim": "🟠",
            "critico": "🔴",
        }
        return mapping[self.value]


class CausaDesvio(StrEnum):
    """Causa categórica de desvio (PAV §3 V3 — diagnóstico a posteriori)."""

    SONO = "sono"
    CURSO = "curso"
    INTERNET = "internet"
    VISITA = "visita"
    DOENCA = "doenca"
    ALIMENTACAO = "alimentacao"
    LUZ_AZUL = "luz_azul"
    PROCRRASTINACAO = "procrastinacao"
    OUTRO = "outro"

    @property
    def label_pt(self) -> str:
        """Label em português para exibição.

        Returns:
            str: Rótulo legível.
        """
        mapping: dict[str, str] = {
            "sono": "😴 Sono",
            "curso": "📚 Curso",
            "internet": "🌐 Internet",
            "visita": "👥 Visita",
            "doenca": "🤒 Doença",
            "alimentacao": "🍽️ Alimentação",
            "luz_azul": "📱 Luz azul",
            "procrastinacao": "🌀 Procrastinação",
            "outro": "❓ Outro",
        }
        return mapping[self.value]


class WorkoutTipo(StrEnum):
    """Tipo de workout (PAV §3 V3)."""

    CALISTENIA = "calistenia"
    CORRIDA = "corrida"
    HIIT = "hiit"
    ALONGAMENTO = "alongamento"
    NATAÇÃO = "natacao"
    MUSCULACAO = "musculacao"
    OUTRO = "outro"

    @property
    def label_pt(self) -> str:
        """Label em português.

        Returns:
            str: Rótulo legível.
        """
        mapping: dict[str, str] = {
            "calistenia": "💪 Calistenia",
            "corrida": "🏃 Corrida",
            "hiit": "⚡ HIIT",
            "alongamento": "🧘 Alongamento",
            "natacao": "🏊 Natação",
            "musculacao": "🏋️ Musculação",
            "outro": "❓ Outro",
        }
        return mapping[self.value]

