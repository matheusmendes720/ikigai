# Architectural Reframing — 2026-06-07

> **Status:** 🟢 Applied — pomodoro no longer an active engine in the time-blocks layer.

## Context

The user clarified on 2026-06-07 that the time-blocks layer must capture
**only gross entry/exit times**. Pomodoros (fine-grained sub-block
task tracking) are a **future plug-in** for Timewarrior integration,
not a current feature. The journal serves as **reflection checkpoints
outside the entry/exit routines**, not as input to the time-blocks
pipeline.

## Changes Applied

### 1. `pomodoro_machine.py` — reframed as a plug-in contract

**Before (Sprint 3B):**
- `PomodoroMachine` was the central state machine, used as the
  reference implementation for fine-grained round tracking.
- Implied to be wired into the time-blocks pipeline.

**After (Sprint 3B-r2):**
- Introduced a `PomodoroPlugin` `Protocol` — the pluggable boundary
  for future Timewarrior integration.
- `InMemoryPomodoroPlugin` is the **default in-memory reference
  implementation** (used for tests).
- `PomodoroTracker` (formerly `PomodoroMachine`) is now explicitly a
  **reference state machine**, not an active engine.
- Added `PomodoroSession` and `PomodoroSessionEvent` data records
  (plugin-agnostic shapes).
- Added `get_default_plugin()` / `set_default_plugin()` registry for
  swapping implementations at startup.
- Module docstring now explicitly states: **"The time-blocks layer is
  not coupled to this registry; it is consulted only by callers that
  opt into sub-block time tracking."**

### 2. `break_calculator.py` — new core module

**Purpose:** Compute **break minutes** between consecutive
`TimeBlock`s (gross entry/exit rest).

**Public API:**
- `compute_break_minutes(prev, next_) -> float`
- `compute_breaks(blocks) -> list[BreakInfo]`
- `compute_break_statistics(blocks) -> BreakStatistics`
- `total_break_minutes(blocks)`, `total_block_minutes(blocks)`

**Coverage:** 100% lines / 100% branches.

### 3. `context_switch.py` — new core module

**Purpose:** Estimate **PAV-based context-switch overhead** between
periods (MANHÃ → TARDE = 30min, etc.). Subtract from gross break to
get **net rest**.

**Public API:**
- `context_switch_overhead_minutes(from_period, to_period, custom_overrides=None) -> int`
- `estimate_context_switch(from_period, to_period, ...) -> ContextSwitchEstimate`
- `net_rest_minutes(gross_break, from_period, to_period, ...) -> float`

**Coverage:** 89.6% lines.

### 4. `journal_segmenter.py` — new core module

**Purpose:** Segment a `JournalEntry` by period and render a
**natural-language markdown report** per period (PT-BR).

**Public API:**
- `segment_journal_by_period(journal) -> JournalReport`
- `render_period_summary(segment) -> str`
- `render_natural_language_report(report) -> str`

**Coverage:** 97.1% lines.

### 5. Public API update

`__init__.py` now exports **101 symbols** (was 81):
- 10 new core exports (BreakInfo, BreakStatistics, compute_break_*,
  ContextSwitchEstimate, ContextSwitchSeverity, context_switch_*,
  net_rest_minutes, JournalReport, JournalSegment,
  render_*, segment_*, total_*)
- 10 new pomodoro plugin exports (PomodoroPlugin, PomodoroSession,
  PomodoroSessionEvent, InMemoryPomodoroPlugin, PomodoroTracker,
  PomodoroEvent, DEFAULT_TRANSITIONS, default_transition_table,
  get_default_plugin, set_default_plugin)
- **Removed:** `PomodoroMachine` (replaced by `PomodoroTracker`)

### 6. Test files

- Added `tests/unit/core/test_break_calculator.py` (33 tests)
- Added `tests/unit/core/test_context_switch.py` (27 tests)
- Added `tests/unit/core/test_journal_segmenter.py` (17 tests)
- Added `tests/unit/core/test_pomodoro_plugin.py` (43 tests)
- **Removed** `tests/unit/core/test_pomodoro_machine.py` (covered
  by `test_pomodoro_plugin.py` for the state machine)

## Architecture Layers (Updated)

```
┌────────────────────────────────────────────────────────────┐
│  LAYER 0 — Strategic Intent                                │
│  PAV, IKIGAi, North Star Metrics, M1-M8 Middlewares        │
└────────────────┬───────────────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────────────┐
│  LAYER 1 — Orchestration (CLI)                             │
│  centrals, handlers, plugins (Sprint 7)                    │
└────────────────┬───────────────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────────────┐
│  LAYER 2 — Core Logic (pure, no I/O)                        │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Time-blocks (gross entry/exit only)                    │ │
│  │   - TimeBlock entity (start, end, label, period)       │ │
│  │   - break_calculator (gross rest between blocks)       │ │
│  │   - context_switch (PAV overhead per period)           │ │
│  │   - net_rest = gross_break - context_switch_overhead  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Pomodoro (FUTURE PLUGIN, not active)                  │ │
│  │   - PomodoroPlugin (Protocol)                          │ │
│  │   - InMemoryPomodoroPlugin (default for tests)         │ │
│  │   - PomodoroTracker (reference state machine)          │ │
│  │   - Future: TimewarriorPomodoroPlugin                 │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Journal (reflection checkpoints)                       │ │
│  │   - JournalEntry (free-form text + global fields)     │ │
│  │   - journal_segmenter (per-period NL reports)          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Habit / Policy / Sleep / Scenario (Sprints 3+4)       │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────┬───────────────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────────────┐
│  LAYER 3 — Entities (Pydantic v2 strict)                    │
│  TimeBlock, JournalEntry, Habit, QHEMetrics, DailyLog, etc.│
└────────────────┬───────────────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────────────┐
│  LAYER 4 — Persistence (Sprint 5)                          │
│  InMemoryRepository, SqliteRepository, migrations           │
└────────────────────────────────────────────────────────────┘
```

## Key Principles (Restated)

1. **No pomodoro in the time-blocks layer.** The time-blocks layer
   captures only gross entry/exit. Pomodoros are a separate
   plug-in concern for future sub-block, task-card-level time
   tracking.
2. **No pomodoro in functional requirements for now.** Pomodoros
   exist as data structures (`PomodoroConfig`, `PomodoroRound`,
   `PomodoroSession`) and as a reference state machine, but they
   are **not** wired into the time-blocks pipeline.
3. **Break minutes = numerical focus.** The primary numerical
   signal from the time-blocks layer is the **gross rest** between
   blocks, which is then reduced by the **PAV context-switch
   overhead** to compute **net rest**.
4. **Journal = reflection checkpoints.** The journal is for
   reflection, not for routine tracking. The journal segmenter
   produces per-period natural-language summaries for daily/weekly
   reports.
5. **Day total = gross entry/exit.** Daily metrics come from
   summing all block durations and break durations, with no
   sub-block breakdown.

## What Did NOT Change

- The `PomodoroConfig`, `PomodoroRound`, `PomodoroSession` entities
  (Sprint 2A) are kept as-is — they are data structures for the
  future plugin.
- The 7 states, 11 transitions of the PAV §9 state machine are
  preserved (reframed as a **reference** state machine).
- The `TimeBlock` entity is unchanged — it was always a simple
  entry/exit primitive.
- The `JournalEntry` entity is unchanged — it was always a
  free-form text entity.

## Test Counts

```
Sprint 0: 1 (smoke)
Sprint 1: 551
Sprint 2: 820
Sprint 3: 444 (Sprint 3B-pomodoro: 134 → reframed to 43 in test_pomodoro_plugin.py)
Sprint 4: 226 + 206 (habit_engine + weekly_aggregator) + 33 (break_calc) + 27 (context_switch) + 17 (journal_seg) = 509
TOTAL:    2219 passed in 1.62s
```

## Files Touched

| Action | File | Notes |
|:-------|:-----|:------|
| Modified | `src/operational/core/pomodoro_machine.py` | Reframed as plugin contract |
| Created | `src/operational/core/break_calculator.py` | New core module |
| Created | `src/operational/core/context_switch.py` | New core module |
| Created | `src/operational/core/journal_segmenter.py` | New core module |
| Modified | `src/operational/__init__.py` | New exports |
| Created | `tests/unit/core/test_break_calculator.py` | 33 tests |
| Created | `tests/unit/core/test_context_switch.py` | 27 tests |
| Created | `tests/unit/core/test_journal_segmenter.py` | 17 tests |
| Created | `tests/unit/core/test_pomodoro_plugin.py` | 43 tests |
| Deleted | `tests/unit/core/test_pomodoro_machine.py` | Replaced by test_pomodoro_plugin.py |

---

*Architectural Reframing — operational v0.1.0 — 2026-06-07*
*Time-blocks: gross entry/exit only · Pomodoro: future plug-in · Journal: reflection checkpoints*
