# operational — Sprint 3 Completion Report

**Sprint:** 3 — Core Layer Part 1 (Sleep, Validation, Pomodoro, Scenarios)
**Date:** 2026-06-07
**Status:** 🟢 **COMPLETED — 110% DoD**

---

## 1. Sub-Agents Deployed (2 PARALLEL)

| Sub-Agent | Modules | Status |
|:----------|:--------|:------:|
| 3A | sleep_calculator, time_validator | ✅ |
| 3B | pomodoro_machine, scenario_classifier | ✅ |

## 2. Deliverables

| # | File | Lines | Coverage | Quality Gates |
|--:|:-----|------:|---------:|:--------------|
| 1 | `src/operational/core/sleep_calculator.py` | 444 | 98.9% | mypy ✅, ruff ✅, pytest ✅ |
| 2 | `src/operational/core/time_validator.py` | 272 | 100% | mypy ✅, ruff ✅, pytest ✅ |
| 3 | `src/operational/core/pomodoro_machine.py` | 601 | 100% | mypy ✅, ruff ✅, pytest ✅ |
| 4 | `src/operational/core/scenario_classifier.py` | 433 | 100% | mypy ✅, ruff ✅, pytest ✅ |
| 5 | `src/operational/__init__.py` (updated) | 200+ | n/a | 81 public exports |
| 6 | `tests/unit/core/test_sleep_calculator.py` | 595 | 100% | 134 tests |
| 7 | `tests/unit/core/test_time_validator.py` | 480 | 100% | 111 tests |
| 8 | `tests/unit/core/test_pomodoro_machine.py` | 903 | 100% | 134 tests |
| 9 | `tests/unit/core/test_scenario_classifier.py` | 526 | 100% | 65 tests |
| 10 | `docs/adr/PRD-CORE-SLEEP-VALIDATION.md` | 621 | n/a | Mermaid ✅ |
| 11 | `docs/adr/PRD-CORE-POMODORO-SCENARIO.md` | 582 | n/a | Mermaid ✅ |
| **Total** | **11 files** | **5,455** | **99.5%** | **all green** |

## 3. Test Results

```
========================= 1815 passed in 1.33s =========================
```

| Sprint | Tests | Modules | Coverage |
|:-------|------:|--------:|---------:|
| Sprint 1 (Foundation) | 551 | 4 | 100% |
| Sprint 2 (Entities) | 820 | 8 | 99.6% |
| Sprint 3 (Core P1) | 444 | 4 | 99.5% |
| **TOTAL** | **1,815** | **16** | **99.5%** |

## 4. Public API (81 exports)

```python
import operational

# Core - Sleep Calculator (9)
from operational import (
    SleepQuality, SleepDecision,
    STATUS_OK, STATUS_HARDCORE, STATUS_CRITICO,
    calcular_horas_sono, validar_sono_ideal,
    is_within_optimal_window, get_sleep_matrix,
)

# Core - Time Validator (4)
from operational import (
    WakeUpStatus, WakeUpValidation,
    validar_horario_acordar, is_optimal_wake_hour,
)

# Core - Pomodoro Machine (4)
from operational import (
    PomodoroMachine, PomodoroEvent,
    DEFAULT_TRANSITIONS, default_transition_table,
)

# Core - Scenario Classifier (5)
from operational import (
    Scenario, ScenarioClassification,
    HARDCORE_MAX_PER_MONTH, classificar_dia, is_hardcore_alert,
)
```

## 5. Critical Design Decisions (consolidated)

### 3A: Sleep + Validation
1. **Matrix rule deconstruction (6 layers)** — The PAV §7 5x4 matrix is not a simple `actual == target` match. The ✅ glyph is awarded on the **9h ideal diagonal** `(18→3, 19→4, 20→5)` plus the **HARDCORE escape hatch** `(23→3, 4h)`. The 4h HARDCORE column from any non-23h bedtime is strict ❌; the 23h row is HARDCORE-only ❌ except for the 3am escape hatch.
2. **Module-level function aliases** — Both `calcular_horas_sono`/`validar_sono_ideal` and `is_optimal_sleep` are exposed as both `SleepQuality` class methods AND module-level functions, matching the spec's ergonomic requirement.
3. **`WakeUpValidation` as stdlib `@dataclass(frozen, slots, kw_only)`** — Following the `PAVErrorSpec` precedent from Sprint 1A, not a Pydantic `BaseModel`. Faster, lighter, no extra dependency at the validation-result tier.
4. **All PLR2004 magic values extracted** — 9 module-level `Final` constants in `sleep_calculator.py` and 9 in `time_validator.py`.
5. **Pre-validation: `bool` rejected explicitly** — Per PEP 285, `True`/`False` are `int` in Python but semantically wrong for hour inputs.
6. **`PAVErrorCode` propagated via `raise_pav_error`** — `validar_horario_acordar` calls `raise_pav_error(PAVErrorCode.TIME_001, msg)` for hours 0-2 and `PAVErrorCode.TIME_002` for hours 12+.

### 3B: Pomodoro + Scenario
1. **`PomodoroMachine` is a regular class** (not a dataclass) because it has mutable behaviour. `PomodoroEvent` is a **frozen dataclass** for hashable, immutable event records.
2. **All semantic helpers funnel through `transition()`** — single source of truth for state mutation and event emission.
3. **`skip_break()` increments the round counter** so the emitted events carry the new round number.
4. **`events` property returns a defensive copy** — callers cannot mutate the internal buffer.
5. **`is_hardcore_alert()` enforces the 2x/month cap** — sibling helper, not part of `classificar_dia`.
6. **Optional self-reports only boost DESVIADO** (not HARDCORE/PERFEITO). Boost is capped at 95.0 to match the PERFEITO ceiling.
7. **`default_transition_table()` returns a fresh top-level dict** (inner `frozenset` values are immutable and may be shared).
8. **All numeric thresholds are named `Final` constants** — no magic numbers.
9. **The state machine uses the spec's stricter 11-transition table**; the existing `PomodoroState.can_transition_to` in `enums.py` is a separate, more permissive entity-level guard.

## 6. Definition of Done (Sprint 3)

| Criterion | Status |
|:----------|:------:|
| All 4 core modules created with pure business logic | ✅ |
| `mypy --strict` compatible | ✅ |
| `ruff` ALL rules pass | ✅ |
| All 1815 tests pass | ✅ |
| Coverage ≥95% per module (3 of 4 at 100%, sleep at 98.9%) | ✅ |
| Google-style docstrings | ✅ |
| PAV §6 error codes propagated via `raise_pav_error` | ✅ |
| Public API updated in `__init__.py` (81 exports) | ✅ |
| 2 PRDs with Mermaid diagrams | ✅ |
| NO I/O, NO persistence, NO logging side effects | ✅ |

## 7. Next: Sprint 4 — Core Layer Part 2

2 parallel sub-agents will generate:
- `core/habit_engine.py` — `HabitEngine` (H(t), E_req, Q_HE formula) — 100% deterministic
- `core/policy_engine.py` — `PolicyEngine` (4-state FSM with histerese 3d upgrade / 2d downgrade)
- `core/weekly_aggregator.py` — `aggregate_week` → `WeeklyAggregate`
- `core/consolidator.py` — `daily_consolidate` (energy/productivity/health/overall scores)

These are the **arithmetic engines** that consume entity data and produce derived metrics.

---

*Sprint 3 — 100% complete — operational v0.1.0 — 2026-06-07*
