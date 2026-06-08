# 03 — Sleep Calculator (PAV §7)

The **sleep calculator** is the canonical model for the one
variable that gates every other recovery metric: **did you sleep
enough, and was it good sleep?** The module lives in
`core/sleep_calculator.py` (the matrix + quality functions) and
`entities/metric.py` (the per-night `SleepRecord` entity with the
midnight-crossing-safe duration).

## `SleepRecord.duration_hours` — `entities/metric.py:154-174`

The **midnight-crossing-safe duration** is a computed field on the
`SleepRecord` Pydantic entity. It combines `bedtime` and `wake_time`
on `self.date`, and adds one day to the wake datetime if it
crossed midnight.

```python
@computed_field
@property
def duration_hours(self) -> float:
    bed_dt = datetime.combine(self.date, self.bedtime)
    wake_dt = datetime.combine(self.date, self.wake_time)
    if wake_dt < bed_dt:
        wake_dt = wake_dt.replace(day=wake_dt.day + 1)
    delta = wake_dt - bed_dt
    return delta.total_seconds() / 3600.0
```

| Property | Value |
|----------|-------|
| Complexity | O(1) — two `datetime.combine` calls, one conditional increment |
| Inputs | `self.date: date`, `self.bedtime: time`, `self.wake_time: time` |
| Output | `float` — sleep duration in hours |
| Side effects | none |

**Edge cases:**

* **Midnight crossing** (most common): `bedtime = 23:00`,
  `wake_time = 06:00`, `date = 2026-06-08`. The combined
  `wake_dt = 2026-06-08 06:00 < bed_dt = 2026-06-08 23:00`, so we
  roll `wake_dt` to `2026-06-09 06:00`. Duration = 7.0 h.
* **Equal times** (degenerate): `bedtime == wake_time`. The `wake_dt
  < bed_dt` test is false, so no roll. Duration = 0.0 h.
* **No midnight crossing** (rare, e.g. nap): `bedtime = 14:00`,
  `wake_time = 15:00`. Duration = 1.0 h. Possible but unusual.

## `sleep_calculator.py` — the module's main functions

The `core/sleep_calculator.py:170-309` module exposes three
operations, all static methods on the `SleepQuality` namespace
class (with module-level aliases for ergonomics).

### `classify_quality(score: int) -> QualityLabel` — `core/sleep_calculator.py:227-262`

The canonical sleep-quality classifier. Bucket thresholds are
checked descending, first match wins.

```python
def validar_sono_ideal(horas_sono: float) -> QualityLabel:
    if horas_sono >= 9.0:
        return QualityLabel.EXCELENTE
    if horas_sono >= 8.0:
        return QualityLabel.BOM
    if horas_sono >= 7.0:
        return QualityLabel.ACEITAVEL
    if horas_sono >= 4.0:
        return QualityLabel.HARDCORE
    return QualityLabel.CRITICO
```

| Property | Value |
|----------|-------|
| Complexity | O(1) — 5 comparisons |
| Inputs | `horas_sono: float` (≥ 0) |
| Output | `QualityLabel` |
| Side effects | raises `ValueError` if `horas_sono < 0`; raises `TypeError` on non-numeric input |

### `compute_debt(hours_actual, hours_target) -> float`

The module also exports the **sleep-debt** helper
(`hours_actual - hours_target`), used by the weekly aggregator to
spot multi-day deficits. Convention: positive = debt, negative =
surplus.

### `is_within_optimal_window(hora_dormir, hora_acordar) -> bool` — `core/sleep_calculator.py:264-289, 307-309`

A boolean that asks: *is the user in the PAV §7 "ideal" window?*
The optimal window is the intersection of three predicates:

```python
def is_optimal_sleep(hora_dormir: int, hora_acordar: int) -> bool:
    horas = calcular_horas_sono(hora_dormir, hora_acordar)
    optimal_dormir = (
        DEFAULT.HORARIO_DORMIR_MIN <= hora_dormir <= DEFAULT.HORARIO_DORMIR_MAX
    )
    optimal_acordar = (
        DEFAULT.HORARIO_ACORDAR_MIN <= hora_acordar <= DEFAULT.HORARIO_ACORDAR_MAX
    )
    optimal_duration = 7.0 <= horas <= 9.0
    return optimal_dormir and optimal_acordar and optimal_duration
```

| Property | Value |
|----------|-------|
| Complexity | O(1) |
| Inputs | `hora_dormir, hora_acordar: int` in `[0, 23]` |
| Output | `bool` |
| Side effects | raises `ValueError` on out-of-range hours |

## Sleep quality bands

| Band | Hours | QualityLabel | Emoji | Use case |
|------|-------|--------------|-------|----------|
| `EXCELENTE` | `>= 9.0` | 🟢 | Olympic recovery day |
| `BOM` | `>= 8.0` | 🟢 | Normal good day |
| `ACEITAVEL` | `>= 7.0` | 🟡 | Minimum acceptable |
| `HARDCORE` | `>= 4.0` | 🟠 | Survival mode (deadline) |
| `CRITICO` | `< 4.0` | 🔴 | Data error / health risk |

The buckets are also mirrored in `enums.QualityLabel.from_hours()`
(`enums.py:349-370`) which adds an extra clamp: negative values
are clamped to 0 and treated as `CRITICO`.

The **PAV §7 5×4 decision matrix** (`get_sleep_matrix()` at
`core/sleep_calculator.py:380-407`) extends these bands with a
schedule-level decision rule. There are 5 bedtime rows (18, 19,
20, 21, 23) and 4 wake-up columns (3am-9h, 4am-8h, 5am-7h,
3am-HARDCORE-4h). The matrix classifies each cell into
`STATUS_OK` / `STATUS_HARDCORE` / `STATUS_CRITICO` based on a
6-layer rule (see the module docstring at
`core/sleep_calculator.py:317-378`).

## Edge cases

* **Bedtime > wake_time (midnight crossing)** — handled by
  `duration_hours` and by `calcular_horas_sono`. Add one day to
  the wake datetime.
* **Bedtime == wake_time (degenerate)** — duration = 0 h,
  quality = `CRITICO`. Possible as a data-entry error, never a
  real value.
* **`deep_sleep_pct` missing** — the `SleepRecord` field is
  `Optional[Annotated[float, Field(ge=0.0, le=100.0)]]`. The
  duration calculation does not depend on it; deep-sleep is used
  only by the report layer for display.
* **Hours out of `[0, 23]`** — `calcular_horas_sono` raises
  `ValueError`. `is_optimal_sleep` propagates the same error.
* **Negative hours** — `validar_sono_ideal` raises `ValueError`.
* **Bool inputs** — both `calcular_horas_sono` and
  `validar_sono_ideal` explicitly reject booleans with
  `TypeError` (booleans are int subclasses per PEP 285).

## UI rendering

The sleep KPI is a single card in the daily report:

* `kpi_card(title, value, *, color="primary", footer, icon, width=28)`
  — `ui/components.py:341-361`. Returns a Rich `Panel` with a
  large number, an icon, and a footer.
* The call site is in `ui/daily_report.py` — the sleep card
  uses color `"sleep"` (`"dodger_blue2"`) and the quality icon
  derived from `QualityLabel.emoji`.

```text
+--------------------------------------+
|  💤  Sono                            |
|  7h 30min                            |
|  ACEITAVEL — dentro da janela PAV    |
+--------------------------------------+
```

The **decision matrix** can be rendered as an ASCII table via
`render_sleep_matrix()` (`core/sleep_calculator.py:410-444`),
which produces a 5×4 grid with the three status glyphs (✅ / ⚠️ /
❌) and the actual sleep duration per cell.

## Examples

### Example 1 — normal night (6 h sleep, 80 % focus)

* `bedtime = 23:00`, `wake_time = 05:00`, `date = 2026-06-08`.
* `duration_hours = 6.0`.
* `validar_sono_ideal(6.0) = QualityLabel.HARDCORE` (only ≥ 7.0 is
  `ACEITAVEL`).
* The 6 h cell of the matrix lands in the 4h-HARDCORE column
  (no match) — i.e. `STATUS_CRITICO` because the 4h target
  commitment was not made.

### Example 2 — early bird (7 h sleep)

* `bedtime = 22:00`, `wake_time = 05:00`, `date = 2026-06-09`.
* `duration_hours = 7.0`.
* `validar_sono_ideal(7.0) = QualityLabel.ACEITAVEL`.
* `is_optimal_sleep(22, 5) = True` (within the 7-9h window and
  both times inside `HORARIO_DORMIR_*` / `HORARIO_ACORDAR_*`).

### Example 3 — elite night (9 h sleep)

* `bedtime = 21:00`, `wake_time = 06:00`, `date = 2026-06-10`.
* `duration_hours = 9.0`.
* `validar_sono_ideal(9.0) = QualityLabel.EXCELENTE`.
* The 9 h cell of the matrix (bedtime 21, wake 6) is on the
  "9h ideal diagonal" → `STATUS_OK`.

### Example 4 — short survival night (3.5 h)

* `bedtime = 02:30`, `wake_time = 06:00`, `date = 2026-06-11`.
* `duration_hours = 3.5`.
* `validar_sono_ideal(3.5) = QualityLabel.CRITICO` (< 4.0).
* The matrix will return `STATUS_CRITICO` for any cell in the
  3.5 h range (out-of-range layer).
* `compute_debt(3.5, 8.0) = -4.5` (4.5 h of debt vs the
  MAINTAIN regime target).

## Tests

* `tests/unit/core/test_sleep_calculator.py` —
  `calcular_horas_sono`, `validar_sono_ideal`,
  `is_within_optimal_window`, the full 5×4 decision matrix
  (`get_sleep_matrix`), and the `render_sleep_matrix` ASCII
  formatter.
* `tests/unit/entities/test_metric.py` — `SleepRecord.duration_hours`
  (midnight crossing, equal times, deep_sleep_pct optional).
* `tests/unit/reports/test_weekly_report.py` — sleep-debt
  aggregation across a week.
