# 05 — Pomodoro Machine (PAV §9)

The **Pomodoro machine** is the focus-timer state machine. It
counts the day in 50 min work blocks, separated by 10 min short
breaks, with a 30 min long break every N cycles. A typical day
runs **3 sessions × 3-4 pomodoros = 9-12 rounds**.

## The 7 states

From `enums.PomodoroState` (`enums.py:373-462`):

| State | Meaning | `is_terminal` | `is_active` | `is_paused` |
|-------|---------|---------------|-------------|-------------|
| `IDLE` | Ready, not running | ✓ | | |
| `WORK` | 50 min focus block | | ✓ | |
| `BREAK` | 10 min short break | | ✓ | |
| `LONG_BREAK` | 30 min long break (every Nth) | | ✓ | |
| `PAUSED` | Timer paused mid-state | | | ✓ |
| `SKIPPED` | Round abandoned | ✓ | | |
| `COMPLETE` | Session finished | ✓ | | |

The state diagram in the enum docstring
(`enums.py:373-383`):

```text
IDLE ──▶ WORK ──▶ BREAK ──▶ WORK ──▶ BREAK ──▶ ...
              └──── (after N cycles) ──▶ LONG_BREAK
        any state ──▶ PAUSED ──▶ previous state
        WORK ──▶ SKIPPED ──▶ IDLE
        LONG_BREAK ──▶ COMPLETE ──▶ IDLE
```

## State transition graph

From `core/pomodoro_machine.py:51-59` — the canonical transition
table. Every edge is a `frozenset` of allowed targets.

```text
   ┌──────┐  start   ┌──────┐  tick   ┌──────┐  tick   ┌──────┐
   │ IDLE │────────▶ │ WORK │───────▶ │BREAK │───────▶ │ WORK │
   └──┬───┘          └──┬───┘         └──┬───┘         └──┬───┘
      │                 │                │                │
      │ pause           │ pause          │ long           │ pause
      ▼                 ▼                ▼                ▼
   ┌──────┐         ┌────────┐        ┌──────────┐    ┌────────┐
   │PAUSED│         │ PAUSED │        │LONG_BREAK│    │ PAUSED │
   └──┬───┘         └────────┘        └────┬─────┘    └────────┘
      │ resume                              │ tick
      ▼                                     ▼
   (back to IDLE or WORK)               ┌──────────┐
                                        │ COMPLETE │ (terminal)
                                        └──────────┘

   skip path:  WORK ──▶ SKIPPED ──▶ IDLE
   abort path: any non-terminal ──▶ PAUSED ──▶ IDLE
```

Note: the `pomodoro_machine.py` transition table at line 51 is
**slightly different** from the `PomodoroState.can_transition_to`
table at `enums.py:438-462`. The two coexist:

* The **enum table** is the canonical FSM (used by validation).
* The **machine table** is the orchestrator's allowed set
  (includes `IDLE → COMPLETE` for the explicit "stop session"
  action).

## `PomodoroConfig` — `entities/pomodoro.py:48-176`

The Pydantic entity that defines a pomodoro session recipe:

| Field | Type | Constraint | Default |
|-------|------|------------|---------|
| `id` | `UEID` | — | — |
| `name` | `str` | 1-100 chars | — |
| `work_minutes` | `int` | `[10, 120]` | 50 |
| `break_minutes` | `int` | `[1, 30]` | 10 |
| `long_break_minutes` | `int` | `[10, 60]` | 30 |
| `rounds_min` | `int` | `[1, 10]` | 3 |
| `rounds_max` | `int` | `[1, 10]` | 4 |
| `routine_id` | `UEID \| None` | — | — |
| `created_at` | `datetime` | — | — |

**Cross-field invariants** enforced at construction:

* `rounds_max >= rounds_min`.
* `break_minutes < work_minutes` (strict; the config rejects
  configurations where the break is longer than the work block).

**Computed field:**

* `session_duration_minutes` =
  `rounds_max * work_minutes + (rounds_max - 1) * break_minutes + long_break_minutes`
  — the total expected session duration assuming the long break
  replaces the last short break.

## `PomodoroConfig.from_pav_defaults(name, **overrides)` — `entities/pomodoro.py:137-176`

The factory that reads the canonical numbers from
`operational.constants.DEFAULT`:

```python
@classmethod
def from_pav_defaults(cls, name: str, **overrides: Any) -> PomodoroConfig:
    base = {
        "id": f"pmo_{uuid4().hex[:12]}",
        "name": name,
        "work_minutes": DEFAULT.POMODORO_WORK_MIN,
        "break_minutes": DEFAULT.POMODORO_BREAK_MIN,
        "long_break_minutes": DEFAULT.POMODORO_LONG_BREAK_MIN,
        "rounds_min": DEFAULT.POMODORO_ROUNDS_MIN,
        "rounds_max": DEFAULT.POMODORO_ROUNDS_MAX,
        "created_at": datetime.now(tz=UTC),
    }
    base.update(overrides)
    return cls(**base)
```

The factory is the only sanctioned way to construct a config in
production code — it guarantees the cross-field invariants hold
because all defaults already satisfy them.

## `PomodoroRound`

A single round of the state machine. From `entities/pomodoro.py:184-...`:

| Field | Type | Constraint |
|-------|------|------------|
| `id` | `UEID` | — |
| `round_number` | `int` | `[1, 20]` |
| `state` | `PomodoroState` | — |
| `started_at` | `datetime \| None` | wall-clock start |
| `completed_at` | `datetime \| None` | wall-clock end |
| `paused_seconds` | `int` | ≥ 0 |
| `work_minutes` | `int` | `[10, 120]` |
| `focus_score` | `int` | `[1, 10]` (self-reported) |

A computed field `actual_duration_minutes` subtracts the
paused seconds from the wall-clock delta.

## Constants

From `constants.py:101-115`:

| Constant | Value | Source |
|----------|-------|--------|
| `POMODORO_WORK_MIN` | `50` | PAV §1 |
| `POMODORO_BREAK_MIN` | `10` | PAV §1 |
| `POMODORO_LONG_BREAK_MIN` | `30` | PAV §9 (line 2291) |
| `POMODORO_ROUNDS_MIN` | `3` | PAV §1 |
| `POMODORO_ROUNDS_MAX` | `4` | PAV §1 |

The invariants enforced in `constants.py:193-204` (called from
`__post_init__`):

* `POMODORO_BREAK_MIN < POMODORO_WORK_MIN` (10 < 50 ✓).
* `POMODORO_ROUNDS_MIN <= POMODORO_ROUNDS_MAX` (3 ≤ 4 ✓).

## Pomodoro machine module — `core/pomodoro_machine.py`

The orchestrator side: it owns the state, emits events, and
delegates to a `PomodoroPlugin` (default: in-memory).

| Symbol | Lines | Role |
|--------|-------|------|
| `PomodoroState` (enum) | `enums.py:373-462` | The 7 states + transition table |
| `DEFAULT_TRANSITIONS` | `core/pomodoro_machine.py:51-59` | The orchestrator's allowed transitions |
| `PomodoroPlugin` (Protocol) | `core/pomodoro_machine.py:67-115` | Pluggable sub-block time tracking (Timewarrior, in-memory, …) |
| `PomodoroEvent` | `core/pomodoro_machine.py:116-133` | One transition event |
| `PomodoroSessionEvent` | `core/pomodoro_machine.py:134-148` | One session-lifecycle event |
| `PomodoroSession` | `core/pomodoro_machine.py:149-168` | Aggregate session record |
| `InMemoryPomodoroPlugin` | `core/pomodoro_machine.py:170-227` | Default in-memory plugin |
| `PomodoroTracker` | `core/pomodoro_machine.py:229-389` | Stateful tracker with `start()`, `tick()`, `pause()`, `skip()`, `finish()` |
| `get_default_plugin()` / `set_default_plugin()` | `core/pomodoro_machine.py:391-415` | Singleton plugin registry |
| `default_transition_table()` | `core/pomodoro_machine.py:417-419` | Returns a copy of the transition table |

## `distribute_pomodoros_across_sessions(n)` — `core/services.py:365-371`

Splits a daily total of pomodoros into the 3 sessions (morning,
afternoon, evening), capped at 4 per session. Greedy fill: S1 first,
S2 second, S3 last.

```python
def distribute_pomodoros_across_sessions(total: int) -> tuple[int, int, int]:
    s1 = min(4, total)
    remaining = total - s1
    s2 = min(4, remaining)
    s3 = max(0, min(4, remaining - s2))
    return s1, s2, s3
```

| Property | Value |
|----------|-------|
| Complexity | O(1) — three `min` calls |
| Inputs | `total: int` (≥ 0) |
| Output | `(s1, s2, s3)` — each capped at 4 |
| Side effects | none |

**Edge cases:**

* `total = 0` → `(0, 0, 0)`.
* `total <= 4` → `(total, 0, 0)`.
* `total = 9` → `(4, 4, 1)`.
* `total = 12` → `(4, 4, 4)`.
* `total > 12` → `(4, 4, 4)` (the surplus is **dropped** by the
  cap; callers should clamp `total` upstream to the
  `max_pomodoros_per_day` from the active policy).

The distribution is **pro-rata** in the sense that it preserves
the order — the first 4 go to S1, the next 4 to S2, the rest to
S3. It is not a true pro-rata of an underlying time budget.

## UI rendering

* `pomodoros_grid(s1, s2, s3, *, max_per_session=4)` —
  `ui/components.py:222-238`. Returns a Rich `Table.grid` with
  three rows, one per session, showing `n / max_per_session` as
  filled (`▣`) / empty (`▢`) cells.

```text
   S1 manhã    ▣ ▣ ▣ ▢   3/4
   S2 tarde    ▣ ▣ ▢ ▢   2/4
   S3 noite    ▢ ▢ ▢ ▢   0/4
```

The grid is mounted in the daily report via
`build_pomodoros_grid_section()` (`ui/daily_report.py:319-...`).

## Examples

### Example 1 — PUSH day, 10 pomodoros

* Policy setpoints: `PUSH` → `max_pomodoros_per_day = 10`.
* `distribute_pomodoros_across_sessions(10) = (4, 4, 2)`.
* Total: 4 × 50 min + 3 × 10 min breaks + 30 min long break =
  260 min per session, ≈ 6.5 h of focus time across the day.

### Example 2 — RECOVER day, 2 pomodoros

* Policy setpoints: `RECOVER` → `max_pomodoros_per_day = 2`.
* `distribute_pomodoros_across_sessions(2) = (2, 0, 0)`.
* Total: 100 min of focus time, all in S1. The rest of the day
  is recovery / shutdown.

### Example 3 — MAINTAIN day, 8 pomodoros

* Policy setpoints: `MAINTAIN` → `max_pomodoros_per_day = 8`.
* `distribute_pomodoros_across_sessions(8) = (4, 4, 0)`.
* The third session is skipped entirely (S3 is reserved for
  evening shutdown in the PAV §1 schedule).

## Tests

* `tests/unit/entities/test_pomodoro.py` — `PomodoroConfig`
  validation (cross-field invariants, computed
  `session_duration_minutes`), `PomodoroRound`, `PomodoroSession`,
  the `from_pav_defaults` factory, and
  `PomodoroState.can_transition_to` for every edge of the graph.
* `tests/unit/core/test_pomodoro_plugin.py` — `PomodoroTracker`
  state transitions, the in-memory plugin, and the singleton
  registry.
* `tests/unit/core/test_routine_logger.py` and
  `tests/integration/*` — end-to-end session lifecycle.
