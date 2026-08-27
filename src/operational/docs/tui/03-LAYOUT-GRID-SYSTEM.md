# 03 — Layout & Grid System

> The dashboard is composed entirely with `rich.table.Table.grid`. There is **no** f-string alignment, no manual column-width calculation, no `str.ljust(n)` tricks. The reason is simple: terminals are 60 to 200 columns wide depending on the host, and string alignment is **brittle** across that range. `Table.grid` lets Rich compute column widths from the cell content while respecting `min_width` and `no_wrap` constraints, producing a layout that survives a 200-column window, a 60-column SSH session, and a captured `StringIO` buffer identically.

## Why no string concatenation

Consider a 3-KPI row that you want to lay out side by side. The "obvious" approach is:

```python
kpi_a, kpi_b, kpi_c = kpi_card(...), kpi_card(...), kpi_card(...)
# "align" them by padding
print(f"{kpi_a}   {kpi_b}   {kpi_c}")
```

This breaks immediately when:

- One panel wraps to two lines (the others stay on one).
- The terminal is narrower than 3 × panel-width (panels clip on the right).
- A panel's title contains a wide character (emoji, CJK).
- The output is captured (Rich loses its sense of width).

The `Table.grid` approach:

```python
grid = Table.grid(expand=False, padding=(0, 2))
grid.add_column(no_wrap=True)  # column 0
grid.add_column(no_wrap=True)  # column 1
grid.add_column(no_wrap=True)  # column 2
grid.add_row(kpi_a, kpi_b, kpi_c)
console.print(grid)
```

Rich computes each cell's intrinsic width, picks the widest of the three as the column width, and aligns the others. The whole grid is then sized to `sum(column_widths) + padding`. If the terminal is wider than the grid, the grid does not expand (`expand=False`); if it is narrower, columns can shrink (Rich re-wraps the cell content).

## `Table.grid(expand=False, padding=(0, 2))` — the base

Every layout grid in the codebase starts with these two arguments:

- **`expand=False`** — the grid does **not** stretch to fill the terminal width. This prevents KPI cards from ballooning to 60 columns wide. The grid is always exactly as wide as its content + padding.
- **`padding=(0, 2)`** — vertical padding 0 (rows are not artificially spaced), horizontal padding 2 (one space of breathing room between columns). Override per-grid for tighter or looser layouts (e.g. `padding=(0, 1)` for the cartesian plane, `padding=(0, 0)` for the timeline).

`ui/components.py:9-11` makes the rule explicit:

```python
# If you find yourself reaching for `f"x{' ' * n}y"` to align text,
# STOP. Use ``Table.grid(expand=False)`` with ``no_wrap=True`` columns.
```

## `no_wrap=True` — prevent text from breaking in middle of words

`no_wrap=True` on a `Column` tells Rich "do not split this column across multiple lines, even if its content is wider than the column's intrinsic width". This is critical for short tokens like:

- Numeric values (`"8.5h"`, `"10/10"`, `"70%"`).
- IDs and codes (`"S1 manhã"`, `"OKR-1"`).
- Axis labels in the cartesian plane (`"Y%"`, `"X% (Produtividade)"`).

Without `no_wrap=True`, Rich can split `"Produtividade"` into `"Produt-\nividade"` if the column is squeezed. With it, the column expands to fit the token, and the grid as a whole expands.

The `cartesian_plane` renderer (`ui/components.py:241-275`) uses `no_wrap=True` on **every** column — the Y-axis labels, the 2-character grid cells, the X-axis caption — to guarantee that the plane never deforms.

## 2-column vs 3-column KPI grid

A 2-column grid (KPI + KPI) is the most common layout for small cards (default width 22 chars). A 3-column grid is used when each card is wider (28 chars). Both are shown below.

### 2-column grid

```python
grid = Table.grid(expand=False, padding=(0, 4))
grid.add_column(no_wrap=True)
grid.add_column(no_wrap=True)
grid.add_row(
    kpi_card("Energia", "8 / 10", icon="⚡", color="energy"),
    kpi_card("Foco",    "9 / 10", icon="🎯", color="focus"),
)
```

```text
╭──────────────────────────╮    ╭──────────────────────────╮
│  ⚡  Energia              │    │  🎯  Foco                 │
│  8 / 10                    │    │  9 / 10                    │
╰──────────────────────────╯    ╰──────────────────────────╯
```

### 3-column grid

```python
grid = Table.grid(expand=False, padding=(0, 2))
grid.add_column(no_wrap=True)
grid.add_column(no_wrap=True)
grid.add_column(no_wrap=True)
grid.add_row(
    kpi_card("Sono",     "7.2h", icon="😴", color="sleep",    width=28),
    kpi_card("Energia",  "8/10", icon="⚡", color="energy",   width=28),
    kpi_card("Foco",     "9/10", icon="🎯", color="focus",    width=28),
)
```

```text
╭────────────────────────╮  ╭────────────────────────╮  ╭────────────────────────╮
│  😴  Sono              │  │  ⚡  Energia            │  │  🎯  Foco               │
│  7.2h                   │  │  8/10                    │  │  9/10                    │
╰────────────────────────╯  ╰────────────────────────╯  ╰────────────────────────╯
```

## Common mistakes

### Mistake 1: `no_wrap=False` (the default)

If a column has `no_wrap=False` (the default) and contains a token longer than the column width, Rich will split the token mid-word. The `cartesian_plane` would print `Y%` as `Y\n%` if `no_wrap=False`. Always set `no_wrap=True` on:

- Axis labels
- Numeric values
- Short codes (SKU, OKR, S1/S2/S3)
- Titles inside `kpi_card` if the card width is small

### Mistake 2: `expand=True`

`expand=True` (the default for `Table`) tells Rich to stretch the table to the full terminal width. For a 3-KPI dashboard on a 200-column terminal, that means each KPI grows to ~60 columns wide and the layout is unreadable. **Always** use `expand=False` on layout grids that compose panels.

### Mistake 3: Missing `padding`

`padding=(0, 0)` is the default. It produces a grid where columns touch each other. For anything meant to be read as "three side-by-side cards", use at least `padding=(0, 1)`. The dashboards use `padding=(0, 2)` for a more spacious feel.

### Mistake 4: Mixing `Table` and `Table.grid` widths

A `Table` (non-grid) inside a `Table.grid` cell uses its own `width` attribute. If the inner table's `width` exceeds the grid column's `min_width`, the grid column will expand to fit, pushing sibling columns around. Always set the inner `Table`'s `width` to match (or be less than) the `min_width` of the grid column.

## Column widths — `min_width`, `max_width`, `justify`

```python
grid.add_column(min_width=22, max_width=40, justify="left", no_wrap=True)
```

| Argument | Effect |
|----------|--------|
| `min_width` | Column will be **at least** this wide. If content is narrower, the column expands with whitespace. |
| `max_width` | Column will be **at most** this wide. If content is wider, Rich wraps (and the cell content must tolerate that — use `no_wrap=True` if not). |
| `justify` | `"left"`, `"center"`, or `"right"`. For numeric columns, use `"right"`. |
| `no_wrap` | If `True`, the column never splits a word; it expands to fit the widest token. |

The default is `min_width=1, max_width=None (unlimited), justify="left", no_wrap=False`. Always set `no_wrap=True` for label columns, and `justify="right"` for numeric columns.

## Nested grids

A `Table.grid` can contain another `Table.grid` as a cell. This is how the cartesian plane is laid out — the outer grid defines the panel structure, the inner grid is the plane itself.

```python
outer = Table.grid(expand=False, padding=(0, 2))
outer.add_column()
outer.add_column()
outer.add_row(
    section_panel("Y axis", cartesian_plane(80, 70)),
    section_panel("Legend",  legend_grid()),
)
```

Nested grids inherit the column-width discipline. The inner grid is sized to its content; the outer grid then places it as a cell with the same rules.

## Examples — 5 layouts

### Example 1: Single-column header (most reports start with this)

```python
header = Table.grid(expand=False, padding=(0, 0))
header.add_column(no_wrap=True)
header.add_row(section_panel("Dia 2026-06-08", day_summary_table()))
```

### Example 2: 2-KPI row + chart

```python
grid = Table.grid(expand=False, padding=(0, 2))
grid.add_column(no_wrap=True)
grid.add_column(no_wrap=True)
grid.add_row(
    kpi_card("Energia", "8/10", color="energy"),
    section_panel("Distribuição do Sono", sleep_sparkline),
)
```

### Example 3: 3-KPI row

```python
grid = Table.grid(expand=False, padding=(0, 2))
for _ in range(3):
    grid.add_column(no_wrap=True)
grid.add_row(
    kpi_card("Sono",    "7.2h", color="sleep"),
    kpi_card("Energia", "8/10", color="energy"),
    kpi_card("Foco",    "9/10", color="focus"),
)
```

### Example 4: 2×2 metric grid

```python
grid = Table.grid(expand=False, padding=(0, 2))
grid.add_column(no_wrap=True)
grid.add_column(no_wrap=True)
grid.add_row(
    section_panel("EASE",    ease_table),
    section_panel("HARDWORK", hardwork_table),
)
grid.add_row(
    section_panel("Transições", transitions_table),
    section_panel("Pontualidade", punct_table),
)
```

### Example 5: Composite dashboard (header + KPI row + chart + recommendation)

```python
body = Table.grid(expand=False, padding=(0, 0))
body.add_column(no_wrap=False)  # let the column shrink
body.add_row(section_panel("Header", header_text))
body.add_row(kpi_row_3col)
body.add_row(section_panel("Cartesian", cartesian_plane(80, 70)))
body.add_row(next_step_panel("Manter ritmo. Monitorar fadiga."))
console.print(body)
```

This is the canonical structure of a daily report.
