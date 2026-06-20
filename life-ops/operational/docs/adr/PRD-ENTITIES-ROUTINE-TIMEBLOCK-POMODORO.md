# PRD-ENTITIES-ROUTINE-TIMEBLOCK-POMODORO — Routine, TimeBlock and Pomodoro entities

> **Status:** Accepted v1.0
> **Sprint:** 2A
> **Owners:** Operational package maintainers
> **Last updated:** 2026-06-07
> **Module scope:** `operational.entities.routine`, `operational.entities.time_block`, `operational.entities.pomodoro`

---

## 1. Objective

Sprint 2A delivers the **three core domain entity modules** of the
`operational` package — the time-bounded building blocks that compose
the daily PAV schedule:

1. **`operational.entities.routine`** — `Routine`, `Ritual`,
   `Transition` (PAV §3, §5). The "what" of the day: tasks for each
   period, transitional actions, period-to-period markers.
2. **`operational.entities.time_block`** — `TimeBlock` (PRD-01 §2).
   The "when" of the day: recorded intervals of work, breaks and
   errands, optionally linked to a planned routine.
3. **`operational.entities.pomodoro`** — `PomodoroConfig`,
   `PomodoroRound`, `PomodoroSession` (PAV §9, PRD-01). The "how" of
   focused work: the state machine of work/break rounds and the
   session-level aggregations.

All seven entities share the same **engineering contract**:

* **Pydantic v2** with `frozen=True`, `extra="forbid"`,
  `validate_assignment=True`, `str_strip_whitespace=True`.
* **Strict typing** (`from __future__ import annotations`, no `Any`
  except in `**overrides`, mypy-compatible).
* **Google-style docstrings** on every class and method, with
  explicit `__all__`.
* **No circular imports** — entities are leaves that only import from
  `operational.enums`, `operational.types` and
  `operational.constants`. Cross-entity links (e.g. `TimeBlock →
  Routine`) are expressed as `:data:`UEID`:data:` strings, not
  Pydantic model references.

---

## 2. Source Spec

The three entity modules are derived from four canonical documents in
the Algorithmic Life OS monorepo:

| Source | Path | Sections used |
|:-------|:-----|:--------------|
| PAV — *Produtividade Algorítmica Visual* | `vibe-ops/base/Produtividade Algorítmica Visual.md` | §3 (Routines, Rituals, Periods), §5 (Period transitions), §9 (Pomodoro state machine + `POMODORO_LONG_BREAK_MIN=30`) |
| PRD-01 — *Entity Contracts* | `vibe-ops/planning/PRD-01-entities.md` | §2 (`TimeBlock` shape), §3 (`Pomodoro*` shapes) |
| Points_of_premisses | `life-ops/planner/Points_of_premisses-task-habits.md` | §4 (Policy FSM — referenced by `PomodoroState` transitions) |
| `operational.constants` | `src/operational/constants.py` | `PomodoroConfig.from_pav_defaults` factory reads `POMODORO_WORK_MIN`, `POMODORO_BREAK_MIN`, `POMODORO_LONG_BREAK_MIN`, `POMODORO_ROUNDS_MIN`, `POMODORO_ROUNDS_MAX` |

Every field constraint and computed property in this document traces
back to a numbered section in one of the four sources.

---

## 3. Data Model (UML Class Diagram)

```mermaid
classDiagram
    direction LR

    %% -- Enums (referenced, not redefined) --
    class Period {
        <<enum>>
        MANHA
        TARDE
        NOITE
        +default_start_hour
        +default_end_hour
        +is_work_period
    }
    class RoutineType {
        <<enum>>
        ENTRY
        CORE
        TRANSITION
        EXIT
        +is_ritual
        +is_boundary
    }
    class RitualType {
        <<enum>>
        HYDRATION
        MEDITATION
        SHUTDOWN
        REVIEW
        MORNING
        EVENING
        +default_period
        +is_evening
    }
    class PomodoroState {
        <<enum>>
        IDLE
        WORK
        BREAK
        LONG_BREAK
        PAUSED
        SKIPPED
        COMPLETE
        +is_terminal
        +is_active
        +is_paused
        +can_transition_to()
    }

    %% -- Branded type aliases --
    class UEID {
        <<type alias>>
        pattern: ^[a-z]{3,5}_[a-z0-9_]+$
    }

    %% -- Routine module --
    class Routine {
        +UEID id
        +str name
        +Period period
        +RoutineType routine_type
        +time start_time
        +time end_time
        +str description
        +bool mandatory
        +set~int~ days_of_week
        +datetime created_at
        +bool archived
        +computed int duration_minutes
        +computed bool active_on_weekend
    }

    class Ritual {
        +UEID id
        +str name
        +RitualType ritual_type
        +int duration_minutes
        +UEID triggers_routine_id
        +datetime created_at
        +computed Period default_period
        +computed bool triggers_routine
    }

    class Transition {
        +UEID id
        +str name
        +Period from_period
        +Period to_period
        +list~UEID~ rituals
        +int duration_minutes
        +datetime created_at
        +computed bool is_ritual_heavy
    }

    %% -- TimeBlock module --
    class TimeBlock {
        +UEID id
        +str label
        +datetime start
        +datetime end
        +Period period
        +UEID routine_id
        +str notes
        +datetime created_at
        +computed int duration_minutes
        +computed bool overlaps_period
        +computed bool has_routine_link
    }

    %% -- Pomodoro module --
    class PomodoroConfig {
        +UEID id
        +str name
        +int work_minutes
        +int break_minutes
        +int long_break_minutes
        +int rounds_min
        +int rounds_max
        +UEID routine_id
        +datetime created_at
        +computed int session_duration_minutes
        +from_pav_defaults() classmethod
    }

    class PomodoroRound {
        +UEID id
        +int round_number
        +PomodoroState state
        +datetime started_at
        +datetime completed_at
        +int paused_duration_seconds
        +computed float actual_duration_minutes
        +computed bool is_focus_round
        +computed bool is_break_round
    }

    class PomodoroSession {
        +UEID id
        +UEID config_id
        +PomodoroState state
        +list~PomodoroRound~ rounds
        +datetime started_at
        +datetime completed_at
        +computed int total_focus_minutes
        +computed int total_break_minutes
        +computed int total_minutes
        +computed float completion_ratio
        +computed float focus_ratio
    }

    %% -- Cross-entity references (UEID links) --
    Routine "0..1" --o "many" TimeBlock : routine_id (UEID)
    Routine "0..1" --o "many" PomodoroConfig : routine_id (UEID)
    Ritual "0..1" --> "0..1" Routine : triggers_routine_id (UEID)
    Transition "many" --> "many" Ritual : rituals (UEID list)
    PomodoroSession "many" --> "1" PomodoroConfig : config_id (UEID)
    PomodoroSession "1" *-- "many" PomodoroRound : rounds

    %% -- Type/Enum dependencies --
    Routine ..> Period
    Routine ..> RoutineType
    Ritual ..> RitualType
    Transition ..> Period
    TimeBlock ..> Period
    PomodoroRound ..> PomodoroState
    PomodoroSession ..> PomodoroState
    PomodoroConfig ..> PomodoroState
```

**Key design decisions visible in the diagram:**

* All IDs are `UEID` strings — never Pydantic model references — to
  avoid circular imports.
* The two `routine_id` references on `TimeBlock` and `PomodoroConfig`
  are **optional** (`UEID | None`), supporting free-standing blocks
  and configs.
* `PomodoroSession` *owns* its `PomodoroRound` list (`*--`
  composition); the rounds cannot exist without the session and are
  removed with it.

---

## 4. Field Reference

### 4.1 `Routine` (PAV §3)

| Field | Type | Constraint | Default | Notes |
|:------|:-----|:-----------|:--------|:------|
| `id` | `UEID` | `^[a-z]{3,5}_[a-z0-9_]+$` | required | Convention: `rou_<slug>` |
| `name` | `str` | 1 ≤ len ≤ 100, stripped | required | |
| `period` | `Period` | MANHA / TARDE / NOITE | required | See `Period.default_*_hour` |
| `routine_type` | `RoutineType` | ENTRY / CORE / TRANSITION / EXIT | required | |
| `start_time` | `time` | — | required | Same-day only |
| `end_time` | `time` | strictly > `start_time` | required | Enforced by validator |
| `description` | `str` | 0 ≤ len ≤ 500 | `""` | |
| `mandatory` | `bool` | — | `True` | |
| `days_of_week` | `set[int]` | each ∈ {0, 1, 2, 3, 4, 5, 6} | `{0..6}` (all days) | Mon=0, Sun=6 |
| `created_at` | `datetime` | — | required | |
| `archived` | `bool` | — | `False` | Soft-delete flag |

### 4.2 `Ritual` (PAV §3 — rituais de transição)

| Field | Type | Constraint | Default | Notes |
|:------|:-----|:-----------|:--------|:------|
| `id` | `UEID` | pattern | required | Convention: `rit_<slug>` |
| `name` | `str` | 1 ≤ len ≤ 100, stripped | required | |
| `ritual_type` | `RitualType` | 6 members | required | |
| `duration_minutes` | `int` | 1 ≤ value ≤ 60 | required | Rituals are short by design |
| `triggers_routine_id` | `UEID \| None` | pattern when set | `None` | Optional link to `Routine` |
| `created_at` | `datetime` | — | required | |

### 4.3 `Transition` (PAV §5)

| Field | Type | Constraint | Default | Notes |
|:------|:-----|:-----------|:--------|:------|
| `id` | `UEID` | pattern | required | Convention: `trn_<from>_<to>` |
| `name` | `str` | 1 ≤ len ≤ 100, stripped | required | |
| `from_period` | `Period` | — | required | |
| `to_period` | `Period` | must ≠ `from_period` | required | Validated |
| `rituals` | `list[UEID]` | each UEID valid | `[]` | Optional list of `Ritual` UEIDs |
| `duration_minutes` | `int` | 0 ≤ value ≤ 120 | required | 0 allowed for instantaneous transitions |
| `created_at` | `datetime` | — | required | |

### 4.4 `TimeBlock` (PRD-01 §2)

| Field | Type | Constraint | Default | Notes |
|:------|:-----|:-----------|:--------|:------|
| `id` | `UEID` | pattern | required | Convention: `blk_<date>_<hhmm>` |
| `label` | `str` | 1 ≤ len ≤ 100, stripped | required | |
| `start` | `datetime` | — | required | |
| `end` | `datetime` | strictly > `start` | required | Overnight crossing allowed |
| `period` | `Period` | — | required | |
| `routine_id` | `UEID \| None` | pattern when set | `None` | Optional link to `Routine` |
| `notes` | `str` | 0 ≤ len ≤ 500 | `""` | |
| `created_at` | `datetime` | — | required | |

### 4.5 `PomodoroConfig` (PAV §9, PRD-01)

| Field | Type | Constraint | Default | Notes |
|:------|:-----|:-----------|:--------|:------|
| `id` | `UEID` | pattern | required | Convention: `pmo_<slug>` |
| `name` | `str` | 1 ≤ len ≤ 100, stripped | required | |
| `work_minutes` | `int` | 10 ≤ value ≤ 120 | required | PAV §1 default: 50 |
| `break_minutes` | `int` | 1 ≤ value ≤ 30, `< work_minutes` | required | PAV §1 default: 10 |
| `long_break_minutes` | `int` | 10 ≤ value ≤ 60 | required | PAV §9 default: 30 |
| `rounds_min` | `int` | 1 ≤ value ≤ 10 | required | PAV §1 default: 3 |
| `rounds_max` | `int` | 1 ≤ value ≤ 10, `≥ rounds_min` | required | PAV §1 default: 4 |
| `routine_id` | `UEID \| None` | pattern when set | `None` | Optional link to `Routine` |
| `created_at` | `datetime` | — | required | |

### 4.6 `PomodoroRound` (PAV §9)

| Field | Type | Constraint | Default | Notes |
|:------|:-----|:-----------|:--------|:------|
| `id` | `UEID` | pattern | required | Convention: `pmor_<session>_<n>` |
| `round_number` | `int` | 1 ≤ value ≤ 20 | required | 1-based |
| `state` | `PomodoroState` | 7 members | required | |
| `started_at` | `datetime \| None` | `≥ completed_at` (when both set) | `None` | |
| `completed_at` | `datetime \| None` | — | `None` | |
| `paused_duration_seconds` | `int` | `≥ 0` | `0` | Subtract from raw duration |

### 4.7 `PomodoroSession` (PAV §9, PRD-01)

| Field | Type | Constraint | Default | Notes |
|:------|:-----|:-----------|:--------|:------|
| `id` | `UEID` | pattern | required | Convention: `pms_<date>_<tag>` |
| `config_id` | `UEID` | pattern | required | Reference to `PomodoroConfig` |
| `state` | `PomodoroState` | — | required | Current machine state |
| `rounds` | `list[PomodoroRound]` | — | `[]` | Ordered history |
| `started_at` | `datetime` | — | required | |
| `completed_at` | `datetime \| None` | set only when `state.is_terminal` | `None` | Validated |

---

## 5. Computed Fields

| Entity | Computed | Formula / Logic | Used by |
|:-------|:---------|:----------------|:--------|
| `Routine` | `duration_minutes` | `end_time - start_time` (whole minutes) | Daily handler, weekly report |
| `Routine` | `active_on_weekend` | `days_of_week & {5, 6} != ∅` | Weekend-only reports |
| `Ritual` | `default_period` | delegates to `RitualType.default_period` | Morning/evening ritual classifier |
| `Ritual` | `triggers_routine` | `triggers_routine_id is not None` | Ritual-chain diagnostics |
| `Transition` | `is_ritual_heavy` | `len(rituals) > 1` | Daily handler prioritization |
| `TimeBlock` | `duration_minutes` | `(end - start).total_seconds() // 60` | Aggregators |
| `TimeBlock` | `overlaps_period` | block fits inside `Period.default_*_hour` | Anomaly detection |
| `TimeBlock` | `has_routine_link` | `routine_id is not None` | Ad-hoc vs planned classification |
| `PomodoroConfig` | `session_duration_minutes` | `rounds_max * work_minutes + (rounds_max - 1) * break_minutes + long_break_minutes` | Daily-planner estimate |
| `PomodoroRound` | `actual_duration_minutes` | `(completed_at - started_at).total_seconds() - paused` (in minutes) | Round-level metrics |
| `PomodoroRound` | `is_focus_round` | `state in {WORK, COMPLETE}` | Focus-time aggregation |
| `PomodoroRound` | `is_break_round` | `state in {BREAK, LONG_BREAK}` | Break-time aggregation |
| `PomodoroSession` | `total_focus_minutes` | Σ `actual_duration_minutes` for focus rounds | Daily report |
| `PomodoroSession` | `total_break_minutes` | Σ `actual_duration_minutes` for break rounds | Daily report |
| `PomodoroSession` | `total_minutes` | `total_focus + total_break` | Session health metric |
| `PomodoroSession` | `completion_ratio` | `completed_rounds / len(rounds)` (range `[0, 1]`) | Session-quality score |
| `PomodoroSession` | `focus_ratio` | `total_focus / total_minutes` (range `[0, 1]`) | "All breaks, no work" detector |

**Why `PomodoroSession.completion_ratio` uses `len(rounds)` and not the
config's `rounds_max`:** the spec is ambiguous, and using `len(rounds)`
keeps the session **self-contained** (no external config lookup
required). A session that was abandoned after 2 rounds shows `2/2 = 1.0`
(100% of *what was attempted*), not `2/4 = 0.5` (50% of *what was
planned*). The "what was planned" ratio is exposed separately through
the application's `PomodoroConfig` lookup.

---

## 6. Validators

| Entity | Validator | Field(s) | Invariant |
|:-------|:----------|:---------|:----------|
| `Routine` | `field_validator` | `days_of_week` | `set ⊆ {0..6}` |
| `Routine` | `model_validator(mode="after")` | `start_time`, `end_time` | `end > start` (same day) |
| `Ritual` | `Field(ge, le)` | `duration_minutes` | 1 ≤ value ≤ 60 |
| `Transition` | `model_validator(mode="after")` | `from_period`, `to_period` | `from ≠ to` |
| `Transition` | `Field(ge, le)` | `duration_minutes` | 0 ≤ value ≤ 120 |
| `TimeBlock` | `model_validator(mode="after")` | `start`, `end` | `end > start` (overnight OK) |
| `PomodoroConfig` | `model_validator(mode="after")` | `rounds_min`, `rounds_max` | `rounds_max ≥ rounds_min` |
| `PomodoroConfig` | `model_validator(mode="after")` | `work_minutes`, `break_minutes` | `break < work` |
| `PomodoroRound` | `model_validator(mode="after")` | `started_at`, `completed_at` | `completed_at ≥ started_at` (when both set) |
| `PomodoroSession` | `model_validator(mode="after")` | `state`, `completed_at` | `completed_at` set ⇒ `state.is_terminal` |
| `PomodoroSession` | `model_validator(mode="after")` | `started_at`, `completed_at` | `completed_at ≥ started_at` |

**Pydantic v2 constraint handling:**

* `Field(ge=10, le=120)` — integer range, enforced by Pydantic.
* `Field(min_length=1, max_length=100)` — string length, enforced by Pydantic.
* `UEID` pattern is enforced through the `Annotated[str, Field(pattern=...)]`
  type alias in `operational.types`.
* `extra="forbid"` rejects unknown fields (Pydantic).
* `frozen=True` raises `ValidationError` on attribute assignment.

---

## 7. Factories

### 7.1 `PomodoroConfig.from_pav_defaults`

```python
@classmethod
def from_pav_defaults(
    cls,
    name: str,
    **overrides: Any,  # noqa: ANN401
) -> PomodoroConfig:
    """Build a PomodoroConfig from PAV canonical defaults.

    Reads the constants from operational.constants.DEFAULT (the
    single source of truth) and produces a validated instance.
    Any field can be overridden through keyword arguments.

    Args:
        name: Human-readable name (1-100 characters).
        **overrides: Field overrides. Allowed keys: id, work_minutes,
            break_minutes, long_break_minutes, rounds_min, rounds_max,
            routine_id, created_at. Unknown keys raise ValueError
            (Pydantic extra="forbid").

    Returns:
        A fully-validated PomodoroConfig.
    """
```

**Defaults used** (all from `operational.constants.DEFAULT`):

| Field | Value | Source |
|:------|:------|:-------|
| `id` | `f"pmo_{uuid4().hex[:12]}"` (generated) | — |
| `name` | `name` (required arg) | — |
| `work_minutes` | `DEFAULT.POMODORO_WORK_MIN` (50) | PAV §1 |
| `break_minutes` | `DEFAULT.POMODORO_BREAK_MIN` (10) | PAV §1 |
| `long_break_minutes` | `DEFAULT.POMODORO_LONG_BREAK_MIN` (30) | PAV §9 |
| `rounds_min` | `DEFAULT.POMODORO_ROUNDS_MIN` (3) | PAV §1 |
| `rounds_max` | `DEFAULT.POMODORO_ROUNDS_MAX` (4) | PAV §1 |
| `created_at` | `datetime.now(tz=UTC)` | — |

**Why no factory on `Routine` / `Ritual` / `Transition` / `TimeBlock`:**
those entities are user-defined (one routine per real-world activity)
and have no canonical "default" form. Only `PomodoroConfig` has a
PAV-canonical recipe, hence the factory.

---

## 8. Test Strategy

### 8.1 Coverage

* **285 tests** across three test files (`test_routine.py`,
  `test_time_block.py`, `test_pomodoro.py`) plus the shared
  `_roundtrip.py` helper.
* **>95% branch coverage** per module (every model_validator branch,
  every computed-field branch, every factory path exercised).
* The test files are organised by **entity → concern** (construction /
  model_config / validators / computed fields / JSON roundtrip), with
  parametric `pytest.mark.parametrize` for value sweeps.

### 8.2 Categories of test

| Category | What it asserts | Pattern |
|:---------|:----------------|:--------|
| **Construction happy paths** | `Routine(id="rou_x", name="X", ...)` builds an instance with the same fields | Direct kwargs |
| **Frozen / extra=forbid** | `r.name = "X"` raises; `Routine(..., bogus=1)` raises | `pytest.raises(ValidationError)` |
| **Field constraints** | Out-of-range values (`duration_minutes=0`, `rounds_max=11`) raise | `pytest.raises(ValidationError)` |
| **Cross-field invariants** | `end_time <= start_time`, `from_period == to_period`, `rounds_max < rounds_min`, `break >= work` | `pytest.raises(ValidationError)` |
| **Computed fields** | `r.duration_minutes == 120`, `s.total_focus_minutes == 100`, `s.completion_ratio == 0.5` | Direct property access |
| **JSON roundtrip** | `roundtrip(entity) == entity` and computed fields re-derive | `_roundtrip` helper |
| **Parametric sweeps** | `Period` × 3, `RoutineType` × 4, `RitualType` × 6, `PomodoroState` × 7 | `@pytest.mark.parametrize` |
| **State machine** | `PomodoroState.can_transition_to` matches PAV §9 | Direct method calls |
| **Boundary windows** | `overlaps_period` accepts (3-5, 8-17, 18-21) | Parametric over start/end hours |

### 8.3 Test infrastructure

* **`tests/unit/entities/_roundtrip.py`** — A small helper that JSON
  round-trips a Pydantic v2 model, stripping **computed fields** from
  the dump so that `extra="forbid"` validation accepts the
  re-validation payload. Computed values are re-derived on the
  decoded model, so the equality check still holds.
* **Why strip computed fields?** `model_dump_json()` includes
  computed fields by default. Re-validating the same JSON would
  fail with `extra_forbidden` errors. Computed fields are derived
  state, not stored state — they should not be part of the
  serialised payload.
* **Why not disable `extra="forbid"` for the roundtrip test?**
  Because production code relies on `extra="forbid"` to catch
  typos and stale fields. Disabling it in tests would mask
  regressions in the production code path.

### 8.4 Tests excluded from coverage

* `pragma: no cover` markers are not used. The test suite covers
  every branch of every entity.
* Pre-existing entity files (`habit.py`, `journal.py`, `policy.py`,
  `metric.py`, `consolidation.py`) and their tests are **out of
  scope** for this PRD.

---

## 9. Acceptance Criteria

A reviewer can verify Sprint 2A is complete when **all** of the
following hold:

1. **Files exist** at the seven paths listed in the deliverables
   summary, with non-trivial line counts.
2. **`pytest tests/unit/entities/test_routine.py` passes** with all
   routines/rituals/transitions covered.
3. **`pytest tests/unit/entities/test_time_block.py` passes** with
   all canonical period windows covered.
4. **`pytest tests/unit/entities/test_pomodoro.py` passes** with
   full state-machine coverage.
5. **`pytest tests/ ` passes** (the full suite) — **1189 tests, 0
   failures**.
6. **`ruff check src/operational/entities/pomodoro.py
   src/operational/entities/routine.py
   src/operational/entities/time_block.py
   tests/unit/entities/test_pomodoro.py
   tests/unit/entities/test_routine.py
   tests/unit/entities/test_time_block.py
   tests/unit/entities/_roundtrip.py` returns
   `All checks passed!`**.
7. **No circular imports** — `python -c "from operational.entities
   import Routine, Ritual, Transition, TimeBlock, PomodoroConfig,
   PomodoroRound, PomodoroSession"` succeeds.
8. **Public API stable** — every entity has an explicit `__all__`
   that matches the public re-exports in
   `operational/entities/__init__.py`.
9. **Factory smoke** —
   `PomodoroConfig.from_pav_defaults("X").work_minutes == 50`.
10. **JSON roundtrip invariant** — every entity satisfies
    `roundtrip(e) == e` (Pydantic `__eq__` semantics, including
    computed fields).

---

## 10. References

* **PAV** — `vibe-ops/base/Produtividade Algorítmica Visual.md` §3, §5, §9.
* **PRD-01** — `vibe-ops/planning/PRD-01-entities.md` §2, §3.
* **PRD-02** — `vibe-ops/planning/PRD-02-habit-tracker.md` (QHE
  thresholds, referenced by `PomodoroConfig.from_pav_defaults`).
* **PRD-06** — `vibe-ops/planning/PRD-06-policy-fsm.md` (four-state
  policy FSM that the Pomodoro state machine mirrors).
* **`operational.constants`** — `src/operational/constants.py`
  (Pomodoro and QHE defaults).
* **`operational.enums`** — `src/operational/enums.py` (Period,
  RoutineType, RitualType, PomodoroState, plus 6 other enums).
* **`operational.types`** — `src/operational/types.py` (UEID, Hour,
  Minute branded type aliases).
* **Pydantic v2 docs** — https://docs.pydantic.dev/latest/
  (`computed_field`, `model_validator`, `ConfigDict`).

---

## 11. Change Log

| Version | Date | Author | Change |
|:--------|:-----|:-------|:-------|
| v1.0 | 2026-06-07 | Operational team (Sprint 2A) | Initial PRD: three entity modules, three test files, one roundtrip helper, 285 tests. |

---

## 12. Design Decisions (rationale log)

### 12.1 Why UEID strings, not Pydantic model references?

Cross-entity links (`TimeBlock.routine_id`, `PomodoroConfig.routine_id`,
`Ritual.triggers_routine_id`, `Transition.rituals`,
`PomodoroSession.config_id`) are typed as `UEID` strings, **not**
nested Pydantic models. Reasons:

* **No circular imports** — entities are leaves; only enums, types
  and constants can be imported. A nested model would either be
  defined here (forcing a circular import of itself) or
  forward-declared with `from __future__ import annotations` and
  a runtime `model_rebuild()` call.
* **Decoupled persistence** — the persistence layer can store a
  block without fetching the routine; the application layer
  resolves the link when needed.
* **Plain Pydantic forward refs are fragile** — they need
  `model_rebuild()` after class definition, which complicates the
  import order and makes tooling (e.g. JSON schema generation)
  harder.

### 12.2 Why `frozen=True` + `validate_assignment=True`?

Both are set on every entity. With `frozen=True`, any field
assignment raises `ValidationError` before reaching the validator, so
`validate_assignment=True` is **redundant in practice**. We set it
anyway to:

* Document the intent explicitly (this is a value-object, not a
  mutable record).
* Make the configuration forward-compatible: if `frozen=True` is
  ever removed (e.g. for an audit-trail subclass), the
  per-assignment validation will kick in without code changes.

### 12.3 Why no cross-entity validators?

The spec did not require a check like "a `TimeBlock` with
`period=MANHA` and `routine_id` pointing to a TARDE routine is
invalid". We considered it and rejected because:

* It would require resolving the linked entity, which crosses the
  "leaves of the import graph" boundary.
* The canonical period check is already exposed through
  `TimeBlock.overlaps_period` (a soft signal, not a hard error).

The application layer can compose stricter checks as needed.

### 12.4 Why expose `VALID_WEEKDAYS` and `Weekday`?

`Weekday` is a branded `Annotated[int, Field(ge=0, le=6)]` type
alias that the `set[Weekday]` field on `Routine` uses for
documentation. `VALID_WEEKDAYS` is a public `frozenset` of
`{0, 1, 2, 3, 4, 5, 6}` that downstream code (e.g. a daily handler
that wants to iterate weekdays) can import without redefining the
constant.

### 12.5 Why use `Period.default_start_hour` / `default_end_hour` in `TimeBlock.overlaps_period`?

The canonical hour windows for the three periods are encoded as
properties on the `Period` enum. `TimeBlock.overlaps_period` reads
them, which:

* **Single source of truth** — changing the canonical hours (e.g.
  shifting MANHA from 3-5 to 4-6) requires only a change in
  `operational.enums`, not in every entity.
* **Matches the spec's test cases** — the parametric tests assert
  on the exact hours, and the enum properties are the source.

### 12.6 Why `dict.fromkeys(..., True)` in the roundtrip helper?

Pydantic v2's `model_dump(exclude=...)` accepts a `dict[str, bool]`
where the values are flags. `dict.fromkeys(iterable, True)` is the
canonical Python idiom for "every key in `iterable` mapped to
`True`" — more concise than a dict comprehension and flagged by
ruff C420 (we fixed that).
