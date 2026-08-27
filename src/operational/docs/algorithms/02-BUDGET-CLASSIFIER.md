# 02 — Budget Classifier (orçado × realizado)

The **day budget** is the planned hard-work minutes for a day. The
**classifier** is the function that maps a real day to a 5-bucket
deviation label. Together they are the "thermometer" of the system:
what was the plan, what actually happened, how far off was it.

## `budget_for_day_type(tipo)` — `core/budget.py:18-28`

Read the canonical budget for a day type directly from the
`TipoDia` enum.

```python
def budget_for_day_type(tipo: TipoDia) -> int:
    return tipo.orcado_min_padrao
```

| Property | Value |
|----------|-------|
| Complexity | O(1) — dict lookup |
| Inputs | `tipo: TipoDia` |
| Output | `int` — planned hardwork minutes |
| Side effects | none |

The budgets are defined on the enum itself
(`enums.py:728-741`):

| Day type | Budget (min) | Budget (h) |
|----------|--------------|------------|
| `CURSO` (school day) | 240 | 4 h |
| `LIVRE` (weekend / off) | 540 | 9 h |
| `HARDCORE` (deadline) | 660 | 11 h |
| `DESCANSO` (recovery) | 120 | 2 h |

## `budget_for_date(d, tipo=None)` — `core/budget.py:31-46`

Compute the budget for a specific date. If `tipo` is given, use it
directly; otherwise fall back to a simple weekday heuristic.

```python
def budget_for_date(d: date, tipo: TipoDia | None = None) -> int:
    if tipo is None:
        weekday = d.weekday()  # 0=mon, 6=sun
        tipo = TipoDia.CURSO if weekday < 5 else TipoDia.LIVRE
    return budget_for_day_type(tipo)
```

| Property | Value |
|----------|-------|
| Complexity | O(1) |
| Inputs | `d: date`, optional `tipo: TipoDia` |
| Output | `int` — planned hardwork minutes |

**The heuristic** (when `tipo is None`):

* `weekday() < 5` (Mon-Fri) → `CURSO` (240 min)
* `weekday() >= 5` (Sat-Sun) → `LIVRE` (540 min)

`DESCANSO` and `HARDCORE` are **never** inferred from the weekday
alone — they must be set explicitly via the `tipo` parameter or via
`infer_tipo_dia()`.

## `infer_tipo_dia(d, has_school_workout=False)` — `core/budget.py:126-138`

A slightly more contextual version of the heuristic. Adds an override
for SENAI / school-workout days.

```python
def infer_tipo_dia(d: date, has_school_workout: bool = False) -> TipoDia:
    if has_school_workout:
        return TipoDia.CURSO
    weekday = d.weekday()
    return TipoDia.CURSO if weekday < 5 else TipoDia.LIVRE
```

| Property | Value |
|----------|-------|
| Complexity | O(1) |
| Inputs | `d: date`, `has_school_workout: bool = False` |
| Output | `TipoDia` |

**Override:** if `has_school_workout=True`, the day is treated as
`CURSO` regardless of weekday. This handles the case of a weekend
training day (e.g. Saturday at SENAI).

## Day types

From `enums.py:709-750`:

| Type | Value | Budget | `is_work_intensive` | Description |
|------|-------|--------|---------------------|-------------|
| `CURSO` | `"curso"` | 240 min (4 h) | False | Weekday with SENAI 6-12h — hardwork reduced |
| `LIVRE` | `"livre"` | 540 min (9 h) | True | Weekend or day off — hardwork maximised |
| `HARDCORE` | `"hardcore"` | 660 min (11 h) | True | Deadline / emergency mode |
| `DESCANSO` | `"descanso"` | 120 min (2 h) | False | Mandatory recovery after HARDCORE |

The `is_work_intensive` property is the canonical flag the daily
handler reads to decide whether the day should be loaded with
pomodoros or kept light.

## The deviation model

The companion to the budget is **`classify_infracao()`** —
`core/budget.py:49-70`. It takes the deviation in minutes and
returns a 5-bucket label.

| Delta (min) | Label |
|-------------|-------|
| `> 60` | `MUITO_ACIMA` |
| `(20, 60]` | `ACIMA` |
| `[-20, 20]` | `DENTRO` |
| `[-60, -20)` | `ABAIXO` |
| `< -60` | `MUITO_ABAIXO` |

> See [01-PRODUCTIVITY-PLANE.md](01-PRODUCTIVITY-PLANE.md) for the
> full reference, the `delta == 60` boundary note, and worked
> examples.

The deviation and the productivity percentage are **two views of
the same information**:

* `productivity_pct` = the **normalised** view (0-100 %), used by
  the cartesian plane.
* `classify_infracao` = the **absolute** view (raw minutes, bucket
  label), used by the daily report header.

## Examples

### Example 1 — Mon, CURSO day, 200 min worked

```python
from datetime import date
from operational.core.budget import budget_for_date, classify_infracao

d = date(2026, 6, 8)             # Monday
orcado = budget_for_date(d)      # 240
print(orcado)                    # 240

label, delta = classify_infracao(200, orcado)
# ("ABAIXO", -40)
```

The user worked 40 min under the budget. `productivity_pct = 83.3`,
quadrant is Q1 sub-case 1b ("Bom — manter ritmo").

### Example 2 — Sun, LIVRE day, 700 min worked

```python
d = date(2026, 6, 14)            # Sunday
orcado = budget_for_date(d)      # 540
print(orcado)                    # 540

label, delta = classify_infracao(700, orcado)
# ("MUITO_ACIMA", 160)
```

Over-achieved by 2 h 40 min. `productivity_pct` caps at 100, so
the cartesian plane cannot distinguish "a little over" from "way
over" — the infraction label captures that.

### Example 3 — Sat + SENAI override, 300 min worked

```python
from operational.core.budget import infer_tipo_dia, budget_for_date, classify_infracao

d = date(2026, 6, 13)            # Saturday
tipo = infer_tipo_dia(d, has_school_workout=True)
# TipoDia.CURSO

orcado = budget_for_date(d, tipo=tipo)   # 240
label, delta = classify_infracao(300, orcado)
# ("ACIMA", 60)
```

The override correctly forces a 240 min budget for the Saturday
training day. Without the override, `infer_tipo_dia(d)` would have
returned `LIVRE` and the budget would have been 540 — a 260 min
gap that would be misread as a massive under-delivery.

### Example 4 — Wed, HARDCORE day, 660 min worked

```python
from operational.enums import TipoDia
d = date(2026, 6, 10)
orcado = budget_for_date(d, tipo=TipoDia.HARDCORE)   # 660
label, delta = classify_infracao(660, orcado)
# ("DENTRO", 0)
```

Hit the deadline-day budget exactly. `productivity_pct = 100.0`.

## Tests

* `tests/core/test_services.py` —
  `test_default_budget_for_curso` and `test_default_budget_for_livre`
  (verify the heuristic).
* `tests/unit/core/test_scenario_classifier.py` — round-trips
  between `classify_infracao` and the cartesian plane.
* `tests/unit/reports/test_daily_summary.py` — budget fixtures of
  240 min (CURSO) and 480 min (custom) and the `exceeds_budget`,
  `zero_budget`, `half_of_budget` cases.
