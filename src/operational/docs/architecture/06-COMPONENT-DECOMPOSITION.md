# Component Decomposition

> **Status:** 🟢 Authoritative — synced with `packages/core/src/operational/` and `apps/` tree at time of writing.
> **Audience:** Anyone onboarding to `operational`. Read this before opening the source.
> **Related:** `01-MVC-LAYERS.md`, `02-PERSISTENCE-LAYER.md`, `03-ENTITY-LIFECYCLE.md`, `04-IMPORT-GRAPH.md`, `05-DATA-FLOW.md`.

This document enumerates every component in the system at three depths:

1. **Layer view** — what each layer (Core / Entity / Persistence / Parser / Report / Meta / CLI / TUI / UI-Components) is responsible for, and what it deliberately does **not** do.
2. **Module view** — file-by-file inventory with public symbols, dependencies, and what each module **does not** do (the negative space is what keeps the system maintainable).
3. **Dependency graph** — what imports what, and the import-discipline rules that prevent circular dependencies.

---

## 1. Layer View

```
┌──────────────────────────────────────────────────────────────────────────┐
│ apps/cli/      Typer + Rich CLI  (12 sub-typers + pav home + pav tui)   │  ← Layer 3: thin controllers
│ apps/tui/      Textual + plotext TUI (7 screens + 5 widgets + 1 chart)   │  ← Layer 3: thin controllers
│ apps/cli/ui/   Rich component factories (30+ v2 widgets + tokens)        │  ← Layer 2: visual primitives
│ apps/tui/ui/   Textual component factories (kpi_card, regime_bar, …)    │  ← Layer 2: visual primitives
├──────────────────────────────────────────────────────────────────────────┤
│ packages/core/                                                        │
│   meta/       EntityRegistry, factories, validators                    │  ← glue
│   parsers/    frontmatter + time_block parsers                          │
│   reports/    daily_summary + weekly_report                            │
│   persistence/ Repository Protocol + InMemory + SQLite + migrations    │
│   entities/   10 frozen Pydantic models                                │  ← Layer 1.5: data shapes
│   core/       19 pure-arithmetic modules                              │  ← Layer 1: pure business logic
└──────────────────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

| Layer | What it owns | What it explicitly does **not** do |
|---|---|---|
| **core/** (Layer 1) | All algorithms: state machines, classifiers, scoring, recommendation. 19 files. Pure functions in / pure arithmetic out. | Read files, write files, talk to the network, import Typer/Textual/Rich, print, log, raise via sys.exit. |
| **entities/** (Layer 1.5) | 10 frozen Pydantic v2 models. Construction-time validation. JSON (de)serialisation. `extra=forbid`. | Cross-import each other. Contain arithmetic. Talk to anything below Layer 1. |
| **persistence/** | Repository Protocol. Three backends (Memory, SQLite, JSON-flat). Migrations runner. | Decide *what* to store (the entities own that). Import from `core/`. |
| **parsers/** | Frontmatter parsing (YAML embedded in markdown). Time-block parser (CSV/JSON). | Know about the algorithms. Import `core/`. |
| **reports/** | Markdown renderers for daily_summary + weekly_report. | Compute anything not pre-computed by `core/`. Import `core/` for lookups only. |
| **meta/** | EntityRegistry (introspection), factories (build entities from raw), validators (cross-field rules). | Mutate state. Import from `core/` and `entities/`. |
| **cli/** (Layer 3) | 12 Typer sub-commands + `pav home` interactive menu + `pav tui` launcher. CSV loader. State persistence adapter. | Logic of any kind — all logic is in `core/`. The CLI just orchestrates. |
| **tui/** (Layer 3) | 7 Textual screens. App, navigation, theme, chart helpers, 5 widgets. | Same as CLI: thin. All math is in `core/`. |
| **cli/ui/** (Layer 2) | 30+ Rich v2 widgets. Design tokens (SEVERITY, STYLES, REGIME, QUADRANT, Glyph). Mock profiles. Receipt panel. | Use Typer. Know about commands. |
| **tui/ui/** (Layer 2) | 5 Textual widgets (kpi_card, regime_bar, habit_streak, sparkline_chart, time_block, pomodoro_grid). | Use Textual `App` / `Screen`. |

---

## 2. Module View

### 2.1 `core/` — 19 pure-arithmetic modules

| Module | Public symbols (representative) | Role |
|---|---|---|
| `constants.py` | `PAVConstants` (22 frozen fields) | All magic numbers; the only place constants live |
| `enums.py` | `Period`, `RoutineType`, `HabitCategory`, `PolicyState`, `PomodoroPhase`, `TimeOfDay`, `MetricKind`, … | Closed enum sets |
| `types.py` | `NewType`, `Protocol`, `TypeAlias` | Pure-type declarations |
| `exceptions.py` | 10 PAV error codes (`PAV001`…`PAV010`) | All custom exceptions |
| `habit_engine.py` | `compute_H(streak, λ)`, `compute_E(R, H)`, `Q_HE_score(...)` | Habit consistency model |
| `policy_engine.py` | `PolicyEngine`, 4-state FSM with hysteresis | PUSH → MAINTAIN → REDUCE → RECOVER |
| `pomodoro_machine.py` | `PomodoroMachine` (8-state SM), `PomodoroPlugin` (Protocol) | Per-round task tracking (currently a plug-in contract, see ADR) |
| `scenario_classifier.py` | `classify(history, …) → Scenario` | Pattern detection over history |
| `sleep_calculator.py` | `SleepCalculator`, `validate_hours(…)` | Sleep scoring |
| `time_validator.py` | `validate_interval(start, end)`, `overlaps(…)` | Interval algebra |
| `budget.py` | `classify_budget(used, capacity) → BudgetClass` | Time budget classification |
| `consolidator.py` | `consolidate_day(…)`, `consolidate_week(…)` | Roll-ups |
| `break_calculator.py` | `BreakRecommender`, `BreakType` | Break suggestions (deterministic) |
| `context_switch.py` | `switch_cost(prev, next)` | Switch-cost penalty |
| `journal_segmenter.py` | `segment_journal(text, …) → [Segment]` | Splits freeform text into typed segments |
| `next_step.py` | `recommend(state, history) → NextStep` | "What should I do now?" |
| `routine_logger.py` | `RoutineLog`, log/transition tracking | Routine start/stop events |
| `weekly_aggregator.py` | `aggregate_week(…) → WeeklySnapshot` | Per-week aggregation |
| `analytics.py` | `AnalyticsService` (pure, no I/O) | Composed views (KPIs, regime) |
| `insights.py` | `insight_for(state) → Insight` | One-liner interpretive text |

### 2.2 `entities/` — 10 frozen Pydantic v2 models

| Module | Public model | Frozen | Notes |
|---|---|:---:|---|
| `routine.py` | `Routine`, `RoutineLog` | ✅ | Composite: routine + per-day log |
| `time_block.py` | `TimeBlock` | ✅ | Gross entry/exit only (ADR 2026-06-07) |
| `journal.py` | `JournalEntry` | ✅ | Reflection checkpoint, not pipeline input |
| `habit.py` | `Habit`, `HabitEvent` | ✅ | |
| `metric.py` | `Metric`, `SleepRecord` | ✅ | |
| `pomodoro.py` | `PomodoroRound` | ✅ | Plug-in contract, optional |
| `policy.py` | `PolicyDecision`, `PolicySetpoints` | ✅ | |
| `consolidation.py` | `DayContext`, `DailyReflection`, `LunchRecord`, `TransicaoRegistrada` | ✅ | |
| `ajuste_fino.py` | `AjusteFino` | ✅ | Fine-tuning adjustments |
| `v3.py` | `V3Snapshot` | ✅ | Forward-compatible schema |

All entities share: `model_config = ConfigDict(frozen=True, extra="forbid")`, JSON-tagged via Pydantic, never import from each other.

### 2.3 `persistence/` — Repository Protocol + 3 backends

| Module | Public symbols | Role |
|---|---|---|
| `base.py` | `Repository` (Protocol) | Generic CRUD contract |
| `memory.py` | `InMemoryRepository[T]` | Tests, ephemeral runs |
| `sqlite.py` | `SQLiteRepository[T]` | Production default |
| `runner.py` | `MigrationRunner` | Forward-only schema migrations |
| `migrations/` | `0001_init.sql`, … | SQL DDL bundled with code |
| `exceptions.py` | `RepoError`, `NotFoundError` | Backend-agnostic errors |

The Protocol allows the CLI/TUI to depend on `Repository[T]`, not a concrete backend — switching from Memory → SQLite is a one-line wire-up at startup.

### 2.4 `parsers/`, `reports/`, `meta/`

| Module | Public symbols | Notes |
|---|---|---|
| `parsers/frontmatter.py` | `parse_frontmatter(md_text) → (meta, body)` | YAML subset |
| `parsers/time_block_parser.py` | `parse_blocks(text) → [TimeBlock]` | CSV / JSON / loose |
| `reports/daily_summary.py` | `render_day(ctx) → markdown` | |
| `reports/weekly_report.py` | `render_week(week) → markdown` | |
| `meta/registry.py` | `EntityRegistry` | Discovery by string name |
| `meta/factories.py` | `make_routine(spec)`, `make_metric(spec)` | Build entities from raw dicts |
| `meta/validators.py` | cross-field rules | Pure-function |

### 2.5 `apps/cli/` — Typer + Rich (Layer 3)

| File | Subcommand group | Notes |
|---|---|---|
| `app.py` | root | 12 sub-typers registered here |
| `home_v2.py` | `pav home` | Interactive 10-item menu |
| `state.py` | (none) | 14 `_PersistentRepo` instances over JSON-flat files |
| `csv_loader.py` | (none) | Bulk import |
| `services.py` | (none) | Pure data services (`get_day_snapshot`) |
| `dataset_selector.py` | `pav demo` | `golden` + `synthetic` |
| `console.py` | (none) | Rich Console singleton |
| `seed.py` | `pav demo seed` | Populate 7 days mock |
| `_compat.py` | (none) | Typer/Rich version shims |
| `formatters/*.py` | (none) | Output adapters (json/table/md) |
| `commands/*.py` | 12 groups | One file per subcommand group |
| `ui/` (Layer 2) | (none) | 30+ Rich v2 widgets + tokens |

### 2.6 `apps/tui/` — Textual + plotext (Layer 3)

| File | Role |
|---|---|
| `app.py` | `PAVApp` — top-level App with `BINDINGS` and `SCREENS` dict |
| `navigation.py` | Screen-to-screen routing |
| `theme.py` | `get_tui_theme()` — colour palette |
| `charts.py` | `plotext` chart builders |
| `screens/dashboard_screen.py` | SCR-001 |
| `screens/daily_flow_screen.py` | SCR-002 |
| `screens/habits_screen.py` | SCR-003 |
| `screens/journal_screen.py` | SCR-004 |
| `screens/metrics_screen.py` | SCR-005 |
| `screens/pomodoro_timer_screen.py` | SCR-006 |
| `screens/policy_screen.py` | SCR-007 |
| `screens/help_screen.py` | modal help |
| `widgets/kpi_card.py` | KPI tile |
| `widgets/regime_bar.py` | PUSH/MAINTAIN/REDUCE/RECOVER strip |
| `widgets/habit_streak.py` | Streak counter with sparkline |
| `widgets/sparkline_chart.py` | Inline mini-chart |
| `widgets/time_block.py` | Day timeline |
| `widgets/pomodoro_grid.py` | Round grid |

---

## 3. Dependency Graph

```
                ┌────────────────────────────────────────┐
                │   apps/cli   apps/tui   (Layer 3)      │
                │     │           │                      │
                │     ▼           ▼                      │
                │   apps/cli/ui   apps/tui/widgets  (L2) │
                │     │           │                      │
                │     ▼           ▼                      │
                │   packages/core/                        │
                │     ├── meta/  parsers/  reports/      │
                │     │   │       │          │            │
                │     │   └───────┴──────────┘            │
                │     ▼                                   │
                │   persistence/                          │
                │     │                                   │
                │     ▼                                   │
                │   entities/                             │
                │     ▲                                   │
                │     │                                   │
                │     └── core/                           │
                └────────────────────────────────────────┘
```

### Import-discipline rules

1. **`core/` imports nothing in this repo.** It uses only `math`, `datetime`, `enum`, `dataclasses`, `typing`.
2. **`entities/` imports nothing in this repo.** Pydantic only.
3. **`persistence/`, `parsers/`, `reports/`, `meta/` may import `core/` and `entities/`.** Never the reverse.
4. **`apps/cli/` and `apps/tui/` may import `core/`, `entities/`, `persistence/`, `parsers/`, `reports/`, `meta/`.** They never import each other (the CLI and TUI are siblings; cross-cutting goes through `core/services` or a shared facade).
5. **`apps/cli/ui/` and `apps/tui/widgets/` may import Rich / Textual respectively.** They never import the CLI/TUI controllers.
6. **`apps/cli/commands/` never imports `apps/tui/` and vice versa.** Cross-cutting presentation lives in `core/services` or a JSON fixture.

### Negative-space summary

The rule "what a layer does **not** do" is more important than what it does. If you find yourself reaching down (e.g. `core/` wanting to `print()` or `apps/tui/` wanting to compute a habit score), stop — promote the dependency upward or extract the helper into the layer that owns it.
