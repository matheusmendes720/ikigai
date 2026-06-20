"""operational — Standalone operational/cybernetic program.

A 100% local, single-user CLI for tracking routines, time blocks, habits, journal
entries, and metrics. Implements the PAV (Produtividade Algorítmica Visual) spec
with pure arithmetic algorithms (no LLM, no NLP).

Public API
----------
- :data:`__version__` — package version (SemVer)
- Constants: :class:`operational.constants.PAVConstants`, :data:`operational.constants.DEFAULT`
- Exceptions: :class:`operational.exceptions.ProductivitySystemError` and subclasses
- Enums: :class:`operational.enums.Period`, :class:`operational.enums.PolicyState`, etc.
- Types: :class:`operational.types.Repository`, :class:`operational.types.Clock`, etc.
- Entities: :class:`operational.entities.Routine`, :class:`operational.entities.Habit`, etc.
- Meta: :class:`operational.meta.EntityRegistry`, factories, validators
- CLI: :class:`operational.cli.app` (Typer application with 7 command groups)

Usage
-----
>>> import operational
>>> operational.__version__
'0.1.0'
>>> from operational.constants import PAVConstants, DEFAULT
>>> DEFAULT.HORARIO_ACORDAR_MIN
3
>>> from operational.enums import Period, PolicyState
>>> Period.MANHA == "MANHA"
True
>>> from operational.entities import Habit, HabitState, QHEMetrics
"""
from __future__ import annotations

from operational.constants import DEFAULT, PAVConstants
from operational.core.break_calculator import (
    BreakInfo,
    BreakStatistics,
    adjusted_net_rest_minutes,
    compute_break_minutes,
    compute_break_statistics,
    compute_breaks,
    total_block_minutes,
    total_break_minutes,
)
from operational.core.context_switch import (
    ContextSwitchEstimate,
    ContextSwitchSeverity,
    context_switch_overhead_minutes,
    estimate_context_switch,
    net_rest_minutes,
)
from operational.core.journal_segmenter import (
    JournalReport,
    JournalSegment,
    render_full_day_report,
    render_natural_language_report,
    render_period_summary,
    segment_journal_by_period,
)
from operational.core.pomodoro_machine import (
    DEFAULT_TRANSITIONS,
    InMemoryPomodoroPlugin,
    PomodoroEvent,
    PomodoroPlugin,
    PomodoroSession,
    PomodoroSessionEvent,
    PomodoroTracker,
    default_transition_table,
    get_default_plugin,
    set_default_plugin,
)
from operational.core.routine_logger import (
    RoutineLogger,
    build_ajuste_fino,
    build_routine_log,
    filter_ajustes_finos_by_date,
    filter_ajustes_finos_by_period,
    filter_routine_logs_by_date,
    filter_routine_logs_by_period,
    total_ajuste_minutos,
)
from operational.core.scenario_classifier import (
    HARDCORE_MAX_PER_MONTH,
    Scenario,
    ScenarioClassification,
    classificar_dia,
    is_hardcore_alert,
)
from operational.core.sleep_calculator import (
    STATUS_CRITICO,
    STATUS_HARDCORE,
    STATUS_OK,
    SleepDecision,
    SleepQuality,
    calcular_horas_sono,
    get_sleep_matrix,
    is_within_optimal_window,
    validar_sono_ideal,
)
from operational.core.time_validator import (
    WakeUpStatus,
    WakeUpValidation,
    is_optimal_wake_hour,
    validar_horario_acordar,
)
from operational.entities.ajuste_fino import AjusteFino
from operational.entities.consolidation import (
    DailyConsolidation,
    MetricAlert,
    WeeklyAggregate,
)
from operational.entities.habit import Habit, HabitState, QHEMetrics
from operational.entities.journal import AutoIndagacao, JournalEntry
from operational.entities.metric import DailyLog, EnergyReading, SleepRecord
from operational.entities.policy import (
    DecisionRecord,
    PolicyDecision,
    PolicySetpoints,
)
from operational.entities.pomodoro import PomodoroConfig, PomodoroRound
from operational.entities.routine import (
    VALID_WEEKDAYS,
    Ritual,
    Routine,
    Transition,
    Weekday,
)
from operational.entities.time_block import TimeBlock
from operational.enums import (
    AlertLevel,
    EnergyLevel,
    HabitCategory,
    Period,
    PolicyState,
    PomodoroState,
    QualityLabel,
    RitualType,
    RoutineType,
    WeekLabel,
)
from operational.exceptions import (
    PAV_ERROR_REGISTRY,
    PAVErrorCode,
    PAVErrorLookupError,
    PAVErrorSpec,
    PomodoroSessionError,
    ProductivitySystemError,
    RoutineCompletionError,
    Severity,
    SleepTrackingError,
    TimeValidationError,
    get_pav_error_spec,
    raise_pav_error,
)
from operational.meta import (
    EntityRegistry,
    entity_registry,
    get_entity_class,
    make_habit,
    make_journal_entry,
    make_routine,
    make_sleep_record,
    make_time_block,
    registered_entity_types,
    validate_datetime_ordered,
    validate_period_bounds,
    validate_ueid_format,
)
from operational.parsers import (
    parse_journal_frontmatter,
    parse_time_block_dict,
    parse_time_block_line,
    serialize_journal_to_markdown,
    serialize_time_block_line,
)
from operational.persistence import (
    DuplicateEntityError,
    EntityNotFoundError,
    InMemoryRepository,
    MigrationError,
    MigrationRunner,
    PersistenceError,
    RepositoryBase,
    SqliteRepository,
    StorageBackendError,
    get_applied_migrations,
    get_connection,
)
from operational.reports import (
    calculate_efficiency,
    generate_daily_summary,
    generate_weekly_report,
    render_cartesian_ascii,
)
from operational.types import (
    UEID,
    Clock,
    Hour,
    Logger,
    Minute,
    Repository,
    Score,
    StreakInt,
    T,
    T_Entity,
    T_Enum,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Constants (2)
    "PAVConstants",
    "DEFAULT",
    # Enums (10)
    "Period",
    "RoutineType",
    "RitualType",
    "HabitCategory",
    "EnergyLevel",
    "QualityLabel",
    "PomodoroState",
    "PolicyState",
    "WeekLabel",
    "AlertLevel",
    # Exceptions (12)
    "ProductivitySystemError",
    "TimeValidationError",
    "SleepTrackingError",
    "PomodoroSessionError",
    "RoutineCompletionError",
    "Severity",
    "PAVErrorCode",
    "PAVErrorSpec",
    "PAVErrorLookupError",
    "PAV_ERROR_REGISTRY",
    "get_pav_error_spec",
    "raise_pav_error",
    # Types (11)
    "Hour",
    "Minute",
    "UEID",
    "StreakInt",
    "Score",
    "Repository",
    "Clock",
    "Logger",
    "T",
    "T_Entity",
    "T_Enum",
    # Entities - Routine domain (5)
    "Routine",
    "Ritual",
    "Transition",
    "Weekday",
    "VALID_WEEKDAYS",
    # Entities - Time tracking (1)
    "TimeBlock",
    # Entities - Pomodoro (2)
    "PomodoroConfig",
    "PomodoroRound",
    # Entities - Journal (2)
    "JournalEntry",
    "AutoIndagacao",
    # Entities - Habit (3)
    "Habit",
    "HabitState",
    "QHEMetrics",
    # Entities - Metric (3)
    "SleepRecord",
    "EnergyReading",
    "DailyLog",
    # Entities - Consolidation (3)
    "DailyConsolidation",
    "MetricAlert",
    "WeeklyAggregate",
    # Entities - Policy (3)
    "PolicySetpoints",
    "PolicyDecision",
    "DecisionRecord",
    # Core - Sleep (8)
    "SleepQuality",
    "SleepDecision",
    "STATUS_OK",
    "STATUS_HARDCORE",
    "STATUS_CRITICO",
    "calcular_horas_sono",
    "validar_sono_ideal",
    "is_within_optimal_window",
    "get_sleep_matrix",
    # Core - Time Validator (4)
    "WakeUpStatus",
    "WakeUpValidation",
    "validar_horario_acordar",
    "is_optimal_wake_hour",
    # Core - Pomodoro Plugin Contract (4) — Timewarrior integration point
    "PomodoroPlugin",
    "PomodoroSession",
    "PomodoroSessionEvent",
    "InMemoryPomodoroPlugin",
    "PomodoroTracker",
    "PomodoroEvent",
    "DEFAULT_TRANSITIONS",
    "default_transition_table",
    "get_default_plugin",
    "set_default_plugin",
    # Core - Break Calculator (6) — gross entry/exit rest + AjusteFino
    "BreakInfo",
    "BreakStatistics",
    "compute_break_minutes",
    "compute_break_statistics",
    "compute_breaks",
    "total_break_minutes",
    "total_block_minutes",
    "adjusted_net_rest_minutes",
    # Core - Context Switch (5) — PAV-based overhead between periods
    "ContextSwitchEstimate",
    "ContextSwitchSeverity",
    "context_switch_overhead_minutes",
    "estimate_context_switch",
    "net_rest_minutes",
    # Core - Journal Segmenter (6) — natural language reports by period
    "JournalSegment",
    "JournalReport",
    "segment_journal_by_period",
    "render_period_summary",
    "render_natural_language_report",
    "render_full_day_report",
    # Core - Routine Logger (8) — NL boundary loggers (RoutineLog + AjusteFino)
    "RoutineLogger",
    "build_routine_log",
    "build_ajuste_fino",
    "filter_routine_logs_by_date",
    "filter_routine_logs_by_period",
    "filter_ajustes_finos_by_date",
    "filter_ajustes_finos_by_period",
    "total_ajuste_minutos",
    # Core - Scenario Classifier (5)
    "Scenario",
    "ScenarioClassification",
    "HARDCORE_MAX_PER_MONTH",
    "classificar_dia",
    "is_hardcore_alert",
    # Persistence (11)
    "RepositoryBase",
    "InMemoryRepository",
    "SqliteRepository",
    "MigrationRunner",
    "PersistenceError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "MigrationError",
    "StorageBackendError",
    "get_connection",
    "get_applied_migrations",
    # Parsers (5)
    "parse_journal_frontmatter",
    "parse_time_block_dict",
    "parse_time_block_line",
    "serialize_journal_to_markdown",
    "serialize_time_block_line",
    # Reports (4)
    "calculate_efficiency",
    "generate_daily_summary",
    "generate_weekly_report",
    "render_cartesian_ascii",
    # Meta — Registry (4)
    "EntityRegistry",
    "entity_registry",
    "get_entity_class",
    "registered_entity_types",
    # Meta — Validators (3)
    "validate_ueid_format",
    "validate_datetime_ordered",
    "validate_period_bounds",
    # Meta — Factories (5)
    "make_routine",
    "make_time_block",
    "make_habit",
    "make_journal_entry",
    "make_sleep_record",
    # CLI (1)
    "cli_app",
]
