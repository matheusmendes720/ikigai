# Agent 3 — PAV operational kernel

**Source:** `Agent` tool dispatched 2026-08-27
**Scope:** Map PAV core (entities, core algorithms, persistence, reports, tests)
**Status:** COMPLETE

---

## 1. Layout — `src/operational/`

**Packages (`packages/`):** only `packages/core/` exists. `packages/cli/` and `packages/tui/` are **NOT present** (verified by glob — per memory: "PAV TUI/CLI deprecated for deletion").

### Subdirectory tree

```
constants.py                 310 lines — PAVConstants (22 frozen fields), DEFAULT sentinel
enums.py                     914 lines — Period, PolicyState, PomodoroState, etc.
exceptions.py                359 lines — ProductivitySystemError + 5-tier Severity
input_validation.py          — system-boundary validation
types.py                     269 lines — UEID, Repository Protocol, T_Entity generic
__init__.py                  419 lines — public API surface
__main__.py                    9 lines — entry point (`from operational.cli.app import app` — references MISSING module)

analytics/
  circadian.py               550 lines — circadian-aware helpers
  engine.py                 1155 lines — analytics aggregation engine
  __init__.py

core/
  analytics.py              1091 lines
  break_calculator.py        280 lines — break minutes between TimeBlocks
  budget.py                  166 lines — time-budget classification, compute_day_quadrant
  consolidator.py            666 lines — daily/weekly rollups
  context_switch.py          233 lines — PAV context-switch overhead
  exceptions.py              — core-specific exceptions
  habit_engine.py            665 lines — H(t), E, Q_HE formulas (PRD-02 §3, PAV §6)
  insights.py                558 lines
  journal_segmenter.py       339 lines — natural-language reports by period
  next_step.py               176 lines
  policy_engine.py           827 lines — 4-state FSM with hysteresis (PRD-06)
  pomodoro_machine.py        434 lines — 7 states, 11 transitions
  routine_logger.py          239 lines
  scenario_classifier.py     433 lines — PAV §8 day scenario classifier
  sleep_calculator.py        441 lines — sleep hours validation
  time_validator.py          271 lines — wake-hour validation
  weekly_aggregator.py       368 lines — 7-day rollup

entities/                    (29 BaseModel classes across 12 files)
  ajuste_fino.py              91 lines — AjusteFino
  consolidation.py           401 lines — MetricAlert, DailyConsolidation, WeeklyAggregate
  habit.py                   546 lines — Habit, HabitState, QHEMetrics
  journal.py                 354 lines — JournalEntry, AutoIndagacao
  metric.py                  452 lines — SleepRecord, EnergyReading, DailyLog
  period_report.py            92 lines — PeriodReport
  policy.py                  563 lines — PolicySetpoints, PolicyDecision, DecisionRecord
  pomodoro.py                433 lines — PomodoroConfig, PomodoroRound, PomodoroSession
  portfolio.py               173 lines — PortfolioArtifact
  routine.py                 425 lines — Routine, Ritual, Transition, RoutineLog
  time_block.py              144 lines — TimeBlock
  v3.py                      249 lines — DayContext, DailyReflection, LunchRecord, TransicaoRegistrada

meta/                        — entity registry, validators, factories
parsers/                     — frontmatter.py (201L), time_block_parser.py
persistence/
  base.py                    192 lines — RepositoryBase[T_Entity] ABC
  memory.py                  100 lines — InMemoryRepository
  sqlite.py                  264 lines — SqliteRepository + get_connection()
  runner.py                  192 lines — MigrationRunner
  migrations/
    001_initial.sql          — single `entities` table (JSON blob)
    002_period_reports.sql   — 3 indexes
    003_vault_sync.sql       — vault_sync_state table
reports/                     — daily_summary.py (313L), weekly_report.py (230L) — pure functions
```

---

## 2. Entities — 29 BaseModels, all `extra="forbid"`

**CLAUDE.md mismatch:** CLAUDE.md lists 15 entities, **actual count is 29**.

| Entity | File:Line | Fields | Mutable? |
|--------|-----------|--------|----------|
| Routine | `entities/routine.py:81` | 11 | no |
| Ritual | `entities/routine.py:217` | 6 | no |
| Transition | `entities/routine.py:277` | 7 | no |
| RoutineLog | `entities/routine.py:346` | 11 | no |
| TimeBlock | `entities/time_block.py:42` | 10 | no |
| Habit | `entities/habit.py:89` | 11 | no |
| HabitState | `entities/habit.py:233` | 7 | no |
| QHEMetrics | `entities/habit.py:406` | 7 | no |
| SleepRecord | `entities/metric.py:102` | 11 | no |
| EnergyReading | `entities/metric.py:184` | 10 | no |
| DailyLog | `entities/metric.py:233` | 21 | **YES** |
| JournalEntry | `entities/journal.py:91` | 16 | **YES** |
| AutoIndagacao | `entities/journal.py:249` | 7 | no |
| MetricAlert | `entities/consolidation.py:116` | 9 | **YES** |
| DailyConsolidation | `entities/consolidation.py:206` | 12 | no |
| WeeklyAggregate | `entities/consolidation.py:298` | 15 | no |
| PomodoroConfig | `entities/pomodoro.py:49` | 9 | no |
| PomodoroRound | `entities/pomodoro.py:182` | 6 | no |
| PomodoroSession | `entities/pomodoro.py:288` | 6 | no |
| PolicySetpoints | `entities/policy.py:96` | 10 | no |
| PolicyDecision | `entities/policy.py:269` | 14 | **YES** |
| DecisionRecord | `entities/policy.py:449` | 8 | no |
| AjusteFino | `entities/ajuste_fino.py:37` | 8 | no |
| PeriodReport | `entities/period_report.py:48` | 20 | **YES** |
| PortfolioArtifact | `entities/portfolio.py:56` | 22 | no |
| DayContext | `entities/v3.py:42` | 11 | no |
| DailyReflection | `entities/v3.py:101` | 12 | no |
| LunchRecord | `entities/v3.py:161` | 7 | no |
| TransicaoRegistrada | `entities/v3.py:217` | 8 | no |

**5 mutable entities** (frozen=False + validate_assignment=True): MetricAlert, JournalEntry, DailyLog, PolicyDecision, PeriodReport.

**Undocumented in CLAUDE.md** (9 entities): RoutineLog, AutoIndagacao, DecisionRecord, PeriodReport, PortfolioArtifact, DayContext, DailyReflection, LunchRecord, TransicaoRegistrada.

---

## 3. Core Algorithms

### `core/habit_engine.py` (665 lines)

Formulas (verbatim from docstrings):
- `H(t) = 1 - e^(-λ·s)` — habit consolidation level (`compute_habit_level`, line 199)
- `E_req = R·(1 - H(t))` — energy required (`compute_energy_required`, line 238)
- `eff = H(t) / (1 + E_req)` — efficiency ratio (`compute_efficiency_ratio`, line 274)
- `H_avg = Σ w_i·H_i / Σ w_i` — weighted average (`compute_habit_avg`, line 315)
- `C = completed / total` — consistency (`compute_consistency`, line 365)
- `S_bonus = min(s_cur / s_max, 1.0)` — streak bonus (`compute_streak_bonus`, line 389)
- `Q_HE = H_avg · (E/E_max) · (1 + η·S_bonus)` — Quality-Habit-Effectiveness (`compute_qhe`, line 430)

Constants: `STREAK_MAX_DEFAULT=90`, `ETA_DEFAULT=0.5`, `LAMBDA_LEARNING_DEFAULT=0.093`.

Regime bands: PUSH≥0.85, RECOVER<0.60 (REDUCE is never produced by QHE alone — requires multi-signal logic).

`HabitEngine` class (line 541) is stateless OO wrapper around pure functions.

### `core/policy_engine.py` (827 lines)

4-state FSM: **PUSH / MAINTAIN / REDUCE / RECOVER**.

Transitions (docstring lines 4-16):
- PUSH→MAINTAIN (downgrade)
- MAINTAIN→PUSH (upgrade)
- MAINTAIN→REDUCE (downgrade)
- REDUCE→MAINTAIN (upgrade)
- REDUCE→RECOVER (downgrade)
- RECOVER→REDUCE (exit)
- `*any`→RECOVER (emergency entry: `infraction_count≥3` OR `QHE<0.30`)

`evaluate_policy` pure function at line 399. `PolicyEngine` class at line 639 (stateful wrapper, `max_history=30`).

### `core/pomodoro_machine.py` (434 lines)

**NOT 8 states as CLAUDE.md claims — it is 7 states.** Docstring at line 16 says "(7 states, 11 transitions)".

States: `IDLE, WORK, BREAK, LONG_BREAK, PAUSED, SKIPPED, COMPLETE`. Transition table at line 52 (`DEFAULT_TRANSITIONS`). COMPLETE is terminal.

Plugin contract `PomodoroPlugin` (Protocol, line 71), default `InMemoryPomodoroPlugin` (line 176), reference `PomodoroTracker` stateful SM (line 237).

---

## 4. Persistence

| File | Lines | Role |
|------|-------|------|
| `base.py` | 192 | `RepositoryBase[T_Entity]` ABC |
| `memory.py` | 100 | `InMemoryRepository[T_Entity]` (dict-backed) |
| `sqlite.py` | 264 | `SqliteRepository[T_Entity]` + `get_connection()` — JSON-blob single-table |
| `runner.py` | 192 | `MigrationRunner` (SHA-256 hashing, schema_migrations meta) |

**Migration story:** 3 SQL files, single-table JSON-blob layout, filtered indexes, `vault_sync_state` table.

---

## 5. Reports — Pure Functions

| File | Lines | Public API |
|------|-------|------------|
| `daily_summary.py` | 313 | `generate_daily_summary(*, ...)` → markdown string + `calculate_efficiency`, `render_cartesian_ascii` |
| `weekly_report.py` | 230 | `generate_weekly_report(*, ...)` → markdown string |

Reports do NOT read from persistence/repositories directly; callers pass pre-aggregated scalars.

---

## 6. CLI/TUI Packages

**Neither exists.** `packages/` contains only `core/` (verified by `find packages -type d`).

**References to missing modules** (orphans):
- `packages/core/src/operational/__main__.py:9` — `from operational.cli.app import app` ❌ BROKEN
- `packages/core/src/operational/__init__.py:358` — `"cli_app"` listed in `__all__` (no import statement)
- `verify_sprint.py:224-233` — spawns `python -m operational.cli.app --help` as subprocess
- Multiple docs reference `operational.cli.*`

---

## 7. Tests

### Counts

| Directory | .py test files | Total LOC |
|-----------|----------------|-----------|
| `tests/unit/core/` | 15 | 13,798 |
| `tests/unit/entities/` | 11 | 7,170 |
| `tests/unit/persistence/` | 4 | 902 |
| `tests/unit/reports/` | 2 | 162 |
| `tests/unit/parsers/` | 2 | 296 |
| `tests/unit/meta/` | 3 | 251 |
| `tests/unit/` (top-level) | 6 | 2,613 |
| `tests/integration/` | 3 + conftest | 681 |
| `tests/e2e/` | 4 | ~250 |
| `tests/property/` | 0 (empty) | 0 |
| `tests/core/` (orphan) | 2 | 1,531 |
| **Total** | **52 test files** | **~27,500 lines** |

### Orphan tests

1. **`tests/core/test_services.py`** (1137 lines) — **ORPHAN**:
   - `from operational.cli import services as services_mod` (line 28)
   - `from operational.cli.services import DaySnapshot, SleepSnapshot, ...` (lines 29-37)
   - `from operational.cli import state` (line 101)
   - None of `operational.cli.services`, `operational.cli.state`, `operational.cli.app` exist
   - **Big orphan — 1137 lines**

2. **`tests/e2e/test_cli_workflow.py`** (66 lines) — **ORPHAN**:
   - `from operational.cli import app` (line 6)

3. **`tests/core/test_exceptions.py`** (394 lines) — OK, imports from `operational.core.exceptions`

### Empty/orphan directories

- `tests/tui/` — only `__pycache__/` (empty)
- `tests/ui/` — only `__pycache__/` (empty)
- `tests/property/` — only `__init__.py` (0 bytes)
- `tests/unit/cli/` — only `__pycache__/` (wrong location, cli package doesn't exist)

---

## 8. CLAUDE.md vs Reality

| Item | CLAUDE.md | Reality |
|------|-----------|---------|
| Entity count | 15 | **29** |
| Pomodoro states | 8 | **7** |
| Pomodoro between time blocks | "NO pomodoro engine" | Plugin contract implemented |
| PAV TUI/CLI | (implied existent) | DELETED per 2026-08-26 migration |

---

## 9. Retrospective Claims Verification

| Claim | Status |
|-------|--------|
| B6 QHE formulas | ✅ DONE — canonical in `operational/core/habit_engine.py` |
| B7 UEID formats | ⏸ DECIDED — keep separate |
| PAV cli/tui deprecated | ✅ Confirmed — deleted, but import refs not cleaned |
