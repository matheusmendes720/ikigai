# 01 — The Productivity Plane (Cartesian)

The **productivity plane** is the canonical visual feedback channel
of the system. Every day produces a single point `(X, Y)` and the
point lands in one of four quadrants (Q1, Q2, Q3, Q4). The quadrant
is what the user sees in the daily report and what drives the
"next step" recommendation.

## The plane

```text
   Y (Efficiency %)
   ▲
100┤- - - - - - - - - - - - - - - - - - -  Q1 (Excelente)   ▲
   │  (x≥50, y≥50)                          high output       │
   │  X ≥ 80, Y ≥ 80 → "Excelente"        AND high focus    │  Q2
   │  else      → "Bom"                                       │  (Otimizado
 50┤·························································· │   mas pouco
   │                                                          │   output)
   │                                                          │  x<50, y≥50
   │                          ◆ (today)                       │
   │                                                          │
   │  Q4 (Produtivo                                           │
   │  mas desotimizado)                                       │
   │  x≥50, y<50                Q3 (Crítico)                  │
   │                            x<50, y<50                    │
  0└──────────────────────────────────────────────────────▶   ▼
   0                          50                            100  X (Productivity %)
```

* **X = Productivity** = `realizado / orcado × 100` — how much of the
  planned hard work got done.
* **Y = Efficiency** = `foco / total × 100` — of the time tracked,
  how much was in deep focus.
* The four quadrants are the cybernetic "buckets" of the day.

## `productivity_pct(r, o)` — `core/budget.py:73-85`

The X-axis of the plane. Given actual and planned minutes, return a
percentage in `[0, 100]`.

```python
def productivity_pct(realizado: int, orcado: int) -> float:
    if orcado <= 0:
        return 0.0
    return min(100.0, (realizado / orcado) * 100.0)
```

| Property | Value |
|----------|-------|
| Complexity | O(1) |
| Inputs | `realizado: int` (≥ 0), `orcado: int` (≥ 0) |
| Output | `float` in `[0, 100]` |
| Side effects | none |

**Edge cases:**

* `orcado == 0` (or negative) → returns `0.0` (avoids division by
  zero). This means a CURSO day with no work scheduled collapses to
  the origin.
* `realizado > orcado` (over-achieved) → capped at `100.0` — the
  plane never goes past the right edge, even if the user worked
  twice the budget. The over-budget magnitude is captured separately
  by `classify_infracao()`.
* `realizado == 0` and `orcado > 0` → returns `0.0` (origin).

## `efficiency_pct(foco, total)` — `core/budget.py:88-100`

The Y-axis of the plane. Given focused minutes and total tracked
minutes, return a percentage in `[0, 100]`.

```python
def efficiency_pct(foco_min: int, total_min: int) -> float:
    if total_min <= 0:
        return 0.0
    return min(100.0, (foco_min / total_min) * 100.0)
```

| Property | Value |
|----------|-------|
| Complexity | O(1) |
| Inputs | `foco_min: int`, `total_min: int` |
| Output | `float` in `[0, 100]` |
| Side effects | none |

**Edge cases:**

* `total_min == 0` (or negative) → returns `0.0` (no time tracked =
  no efficiency).
* `foco_min > total_min` (impossible in normal data) → capped at
  `100.0` (you cannot be more focused than 100 % of the time).

## `classify_quadrant(x, y)` — `core/budget.py:103-123`

Map a point to a quadrant code, a Portuguese label, and an action.

```python
def classify_quadrant(x: float, y: float) -> tuple[str, str, str]:
    if x >= 50 and y >= 50:
        if x >= 80 and y >= 80:
            return "Q1", "Excelente — manter ritmo, monitorar fadiga", "Manter"
        return "Q1", "Bom — manter ritmo", "Manter"
    if x < 50 and y >= 50:
        return "Q2", "Otimizado mas pouco output", "Aumentar volume de trabalho"
    if x < 50 and y < 50:
        return "Q3", "Crítico — revisar sistema, identificar bloqueios", "Revisão urgente"
    return "Q4", "Produtivo mas precisa otimizar", "Reduzir distrações"
```

| Property | Value |
|----------|-------|
| Complexity | O(1) — 4 branch tests |
| Inputs | `x, y: float` in `[0, 100]` |
| Output | `(code, label_pt, action_pt)` |

**Five cases** (note: the function does not classify the origin
explicitly — it falls into Q3 because `x < 50` and `y < 50`):

| Case | Condition | Code | Label (pt) | Action (pt) |
|------|-----------|------|------------|-------------|
| 1a | `x ≥ 80` **and** `y ≥ 80` | `Q1` | Excelente — manter ritmo, monitorar fadiga | Manter |
| 1b | `50 ≤ x < 80` and `y ≥ 50` (Q1 sub-case) | `Q1` | Bom — manter ritmo | Manter |
| 2 | `x < 50` and `y ≥ 50` | `Q2` | Otimizado mas pouco output | Aumentar volume de trabalho |
| 3 | `x < 50` and `y < 50` | `Q3` | Crítico — revisar sistema, identificar bloqueios | Revisão urgente |
| 4 | `x ≥ 50` and `y < 50` | `Q4` | Produtivo mas precisa otimizar | Reduzir distrações |

The **1b sub-case** (`Q1` but neither `x ≥ 80` nor `y ≥ 80`) is the
"good enough" state: at least half the budget done, at least half
the time in focus, but not in the elite band.

## `classify_infracao(r, o)` — `core/budget.py:49-70`

The **deviation classifier** is the 5-bucket companion to
`productivity_pct`. It captures *how far* from the budget the user
landed, in raw minutes.

```python
def classify_infracao(realizado_min: int, orcado_min: int) -> tuple[str, int]:
    delta = realizado_min - orcado_min
    if delta > 60:
        return "MUITO_ACIMA", delta
    if delta > 20:
        return "ACIMA", delta
    if delta >= -20:
        return "DENTRO", delta
    if delta >= -60:
        return "ABAIXO", delta
    return "MUITO_ABAIXO", delta
```

| Property | Value |
|----------|-------|
| Complexity | O(1) — 5 branch tests |
| Inputs | `realizado_min, orcado_min: int` |
| Output | `(label, delta_min)` where `delta = realizado - orcado` |

**The 5 buckets** (piecewise, in `delta = realizado - orcado` order):

| Delta (min) | Label | Meaning |
|-------------|-------|---------|
| `delta > 60` | `MUITO_ACIMA` | More than 1 h over the budget |
| `20 < delta ≤ 60` | `ACIMA` | 20-60 min over |
| `-20 ≤ delta ≤ 20` | `DENTRO` | Within ±20 min of the budget |
| `-60 ≤ delta < -20` | `ABAIXO` | 20-60 min under |
| `delta < -60` | `MUITO_ABAIXO` | More than 1 h under |

**Note:** the bucket `delta == 60` lands in `ACIMA` (the `> 60`
boundary is strict). `delta == -20` lands in `DENTRO` (the
`>= -20` boundary is inclusive).

## UI rendering

The plane is rendered as a Rich `Table.grid` with fixed-width cells
(2 chars each) — no loose string concatenation.

* `cartesian_plane(x, y, *, width=18, height=7)` —
  `ui/components.py:241-327`
* The point is a coloured glyph (`◆` or `▲` or `✗`) at the integer
  column/row computed from the percentages.
* Axis labels show `0`, `50`, `100` only — no in-between tick marks.
* The 50 % quadrant lines are drawn as light dotted lines
  (`┊` / `┈`); the origin is `┼`.

```text
Y%                    X% (Produtividade)
100    ································◆·······················
       ·                            ┊  ·                     ·
 75    ·                            ┊  ·                     ·
       ·                            ┊  ·                     ·
 50    ·····························┊·························
       ·                            ┊  ·                     ·
 25    ·                            ┊  ·                     ·
       ·                            ┊  ·                     ·
  0    ┼─────────────────────────────────────────────────────
        0              50                                    100
```

The point is coloured by quadrant: `bright_green` for Q1, `cyan`
for Q2, `bold red` for Q3, `yellow` for Q4.

## Examples

### Day 1 — a "Bom" CURSO day (Q1 sub-case 1b)

* CURSO: `orcado = 240 min` (4 h).
* Realizado = 180 min focused + 60 min overhead = 240 min tracked.
* `productivity_pct(240, 240) = 100.0`.
* `efficiency_pct(180, 240) = 75.0`.
* `classify_quadrant(100, 75) = ("Q1", "Bom — manter ritmo", "Manter")`.

### Day 2 — a heavy "HARDCORE" day that under-delivered (Q3)

* HARDCORE: `orcado = 660 min` (11 h).
* Realizado = 240 min. `productivity_pct = 36.4`.
* Focused = 120 min. `efficiency_pct = 50.0`.
* `classify_quadrant(36.4, 50.0) = ("Q3", "Crítico — revisar sistema, identificar bloqueios", "Revisão urgente")`.
* `classify_infracao(240, 660) = ("MUITO_ABAIXO", -420)`.

### Day 3 — a "LIVRE" day with high focus (Q1 sub-case 1a)

* LIVRE: `orcado = 540 min`.
* Realizado = 510 min, focused = 480 min.
* `productivity_pct = 94.4`, `efficiency_pct = 94.1`.
* `classify_quadrant(94.4, 94.1) = ("Q1", "Excelente — manter ritmo, monitorar fadiga", "Manter")`.

## Tests

* `tests/unit/core/test_scenario_classifier.py` — quadrant edges
  (50 / 50 / 80 / 80), origin, Q1 sub-cases.
* `tests/core/test_services.py` — `compute_day_quadrant()`
  integration with `DaySnapshot` and the 60-min overhead offset
  applied to `efficiency_pct`.
* `tests/unit/reports/test_daily_summary.py` — end-to-end via
  `DailySummary` with budget fixtures (240 min, 480 min).
