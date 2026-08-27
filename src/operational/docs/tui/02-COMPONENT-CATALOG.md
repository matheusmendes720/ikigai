# 02 — Component Catalog

> Every visual element in the dashboard is built by a small factory function. Each function takes plain Python data (no Rich objects) and returns a Rich renderable. The factories are pure: no I/O, no `console.print()`, no side effects. The split is **`ui/components.py` (atomic + composite panels)** and **`cli/renderers.py` (extended renderers, including `metric_table` and `timeline_h`)**. Both modules are view-only; the controller layer (`cli/commands/*.py`) is the only place that calls `console.print()`.

The catalog below lists the 12 components in the order they appear in code, with a 1-paragraph description, signature, return type, and an ASCII mockup of typical output.

---

## 1. `kpi_card` — single KPI tile

A bordered `Panel` (box `SIMPLE_HEAD`) that holds a small title, a large value, and an optional footer. Used in 2- or 3-column rows to surface headline metrics (energy, focus, sleep hours, etc.).

**Defined in:** `ui/components.py:341-361` (canonical, no `footer` arg) and `cli/renderers.py:135-159` (alt factory with `width=22`).

```python
def kpi_card(
    title: str,
    value: str,
    *,
    color: str = "primary",
    footer: str = "",
    icon: str = "",
    width: int = 28,
) -> Panel
```

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `title` | `str` | — | Short label, e.g. `"Energia"` |
| `value` | `str` | — | The big number/text, e.g. `"8 / 10"` |
| `color` | `str` | `"primary"` | Key from `COLORS` |
| `footer` | `str` | `""` | Italic dim sub-text, e.g. `"+1 vs ontem"` |
| `icon` | `str` | `""` | Leading emoji, e.g. `"⚡"` |
| `width` | `int` | `28` | Fixed panel width |

**Returns:** `rich.panel.Panel`

**Example output:**

```text
╭──────────────────────────╮
│  ⚡  Energia              │
│                            │
│  8 / 10                    │
│                            │
│  +1 vs ontem               │
╰──────────────────────────╯
```

---

## 2. `section_panel` — bordered section

A bordered `Panel` with a colored title in the header bar. The body is whatever renderable the caller passes in (a `Table`, a `Text`, a `Group` of components).

**Defined in:** `ui/components.py:364-378`.

```python
def section_panel(
    title: str,
    body: RenderableType,
    *,
    color: str = "primary",
) -> Panel
```

**Example output:**

```text
╭─  🟢 EASE  ─────────────────────────────╮
│  │ rotina 1  ENTRY   MANHA   done        │
│  │ rotina 2  CORE    TARDE   pending     │
╰──────────────────────────────────────────╯
```

---

## 3. `next_step_panel` — recommendation block

A short call-to-action panel. Used at the end of reports ("Apply this plan: …") and after state inspections. Sister to `next_step` in `cli/renderers.py:468-478` which has a near-identical signature with `color=` instead of `severity=`.

**Defined in:** `ui/components.py:381-387`.

```python
def next_step_panel(
    text: str,
    *,
    severity: str = "ok",
    icon: str = "→",
) -> Panel
```

**Example output:**

```text
╭──────────────────────────────────────╮
│  →  Manter ritmo. Monitorar fadiga.  │
╰──────────────────────────────────────╯
```

---

## 4. `error_panel` — error renderer

Standardized error surface used by every controller when a command fails. The full Python traceback is logged via `log_error`; the user sees this clean panel with the message, optional context, and an optional hint.

**Defined in:** `ui/components.py:390-426`.

```python
def error_panel(
    mensagem: str,
    *,
    contexto: str | None = None,
    severity: str = "crit",
    hint: str | None = None,
) -> Panel
```

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `mensagem` | `str` | — | The error message itself, in plain text |
| `contexto` | `str \| None` | `None` | Surrounding state, e.g. `routine='Morning' period=MANHA` |
| `severity` | `str` | `"crit"` | One of `crit`, `warn`, `ok` |
| `hint` | `str \| None` | `None` | One-line debugging tip |

**Example output:**

```text
╭────  SISTEMA FALHOU  ─────────────────────────╮
│  ❌ Erro de Execução                           │
│                                                 │
│  ValidationError: 1 validation error for Habit │
│  category                                                               │
│    Input should be 'physiological', 'cognitive' …
│                                                 │
│  [Contexto]  routine='Morning'                 │
│  [💡 Dica]  Verifique o enum HabitCategory.    │
╰─────────────────────────────────────────────────╯
```

---

## 5. `pomodoros_grid` — 3×4 pomodoro cells

A compact 3-row grid showing the number of completed pomodoros in each session (S1 manhã, S2 tarde, S3 noite). The canonical version is a `Table.grid` (`ui/components.py:222-238`); the alternative in `cli/renderers.py:204-230` returns a `Text` (line-by-line). The `Table.grid` version is the preferred one because it aligns columns at any width.

**Defined in:** `ui/components.py:222-238`.

```python
def pomodoros_grid(
    s1: int,
    s2: int,
    s3: int,
    *,
    max_per_session: int = 4,
) -> Table
```

**Example output (s1=3, s2=4, s3=1):**

```text
  S1 manhã   ▣ ▣ ▣ ▢   3/4
  S2 tarde   ▣ ▣ ▣ ▣   4/4
  S3 noite   ▣ ▢ ▢ ▢   1/4
```

---

## 6. `cartesian_plane` — 2D scatter with 0/50/100 axes

A 2D Cartesian plane rendered as a `Table.grid` with explicit `width=2` columns. Used by the daily report to plot the day's X (produtividade) vs Y (qualidade). The point glyph and color are chosen by quadrant.

**Defined in:** `ui/components.py:241-327` (canonical, returns `Table.grid`) and `cli/renderers.py:268-349` (alt, returns `Text`). The Table.grid version is preferred for layout stability.

```python
def cartesian_plane(
    x: float,
    y: float,
    *,
    width: int = 18,
    height: int = 7,
) -> Table
```

**Example output (x=80, y=70 → Q1):**

```text
Y%        X% (Produtividade)
100                                                    ◆
                                                      
 50  ┊                                                
                                                      
   0 ┼───────────────────────────────────────
       0                50               100
```

The point is plotted as `◆` in `bright_green` for Q1, `◆` in `cyan` for Q2, `✗` in `bold red` for Q3, and `▲` in `yellow` for Q4. The 50% quadrants are drawn with `┊` / `┈` in `grey30`.

---

## 7. `progress_bar` — horizontal bar

A horizontal progress bar built from full-block `█` and light-shade `░` characters. The percentage is appended in bold severity color. An optional `label` is appended in muted grey.

**Defined in:** `ui/components.py:192-202` (canonical, `severity=` arg) and `cli/renderers.py:185-196` (alt, `color=` arg). Both return a `Text`.

```python
def progress_bar(
    value: float,
    total: float,
    *,
    width: int = 18,
    severity: str = "ok",
    label: str = "",
) -> Text
```

**Example output (value=14, total=20):**

```text
██████████████░░░░  70%  (14/20h estudo)
```

---

## 8. `sparkline` — Unicode block sparkline

A single-line trend using the 8-step block ramp `▁▂▃▄▅▆▇█`. Designed for 7-day inline trends (e.g. "sono this week"). Empty input returns a muted `(sem dados)` placeholder.

**Defined in:** `ui/components.py:205-219` (canonical) and `cli/renderers.py:360-384` (alt with optional resampling).

```python
def sparkline(
    values: Sequence[float],
    *,
    color: str = "primary",
    label: str = "",
) -> Text
```

**Example output (7 ascending values):**

```text
  ▁▂▃▄▅▆▇█  sono 7d
```

---

## 9. `metric_table` — colored key-value table

A `rich.table.Table` with two columns: `Métrica` (bold white, no-wrap) and `Valor` (severity-colored via inline markup). Used to render a *group* of related KPIs (e.g. the 7-day sleep distribution or the activity summary of the day).

**Defined in:** `cli/renderers.py:406-433`. **Note:** this is **not** in `ui/components.py`; it lives in `cli/renderers.py` because it was added during the report-renderer workstream. Both files are imported by controllers.

```python
def metric_table(
    title: str,
    rows: Sequence[tuple[str, str, str | None]],
    *,
    title_color: str = "primary",
    show_header: bool = True,
) -> Table
```

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `title` | `str` | — | Bold colored title shown above the table |
| `rows` | `Sequence[(label, value, severity)]` | — | `severity` may be `None` for uncolored rows |
| `title_color` | `str` | `"primary"` | Key from `COLORS` |
| `show_header` | `bool` | `True` | Set `False` for label-only tables |

**Example output:**

```text
  😴 Distribuição do Sono (7 dias)
╭──────────────────────┬────────────╮
│ Métrica              │ Valor      │
├──────────────────────┼────────────┤
│ Média                │ 7.2h       │
│ Mínimo               │ 5.8h       │  (yellow)
│ Máximo               │ 8.5h       │  (bright_green)
│ Noites < 6h          │ 1          │  (bold red)
╰──────────────────────┴────────────╯
```

---

## 10. `severity_text` — colored text helper

A thin wrapper that applies a severity color to a string and returns a `Text`. The companion to `SEVERITY_COLOR` (`ui/components.py:87-94`). Use this when you need a colored value but do not want to construct a `Text` by hand.

**Defined in:** `ui/components.py:330-333`.

```python
def severity_text(value: str, severity: str | None) -> Text
```

**Example:**

```python
severity_text("8.5h", "ok")   # Text("8.5h", style="bright_green")
severity_text("5.8h", "warn") # Text("5.8h", style="yellow")
severity_text("—",   None)    # Text("—",   style="white")
```

---

## 11. `timeline_h` — horizontal timeline

A horizontal timeline of time blocks. Each block is a `█`-run of fixed length followed by a `HHh label` annotation. Used to show "what I did between 04:00 and 22:00 today" in the state dashboard.

**Defined in:** `cli/renderers.py:238-260`.

```python
def timeline_h(
    blocks: Sequence[tuple[int, int, str]],
    *,
    width: int = 60,
    color: str = "hardwork",
) -> Text
```

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `blocks` | `Sequence[(start_h, end_h, label)]` | — | Hours in 24h format |
| `width` | `int` | `60` | Total bar width in characters |
| `color` | `str` | `"hardwork"` | Key from `COLORS` |

**Example output:**

```text
  ████ 04h Sleep
  ████████████ 06h Workout
  ████████ 10h Deep Work
  █████████ 14h Lunch + Rest
  ██████████ 16h Admin
  █████ 20h Shutdown
```

---

## 12. `next_step` — single recommendation block

The `cli/renderers.py` sister of `next_step_panel`. Same visual contract; the only difference is the parameter name (`color` vs `severity`) and that it lives in the renderer module for use by the v3 reports.

**Defined in:** `cli/renderers.py:468-478`.

```python
def next_step(
    text: str,
    *,
    color: str = "ok",
    icon: str = "→",
) -> Panel
```

**Example output:**

```text
╭─────────────────────────────────────────╮
│  ✓  Dia dentro do padrão ouro. Manter.  │
╰─────────────────────────────────────────╯
```

Use `next_step_panel` for new controllers, `next_step` for report-renderer code. They render identically.

---

## Where the rest lives

`ui/components.py` also exports the **severity helpers** (`sev_for_wake_hour`, `sev_for_sleep_hours`, `sev_for_lunch`, etc.) and the **lookup dicts** (`COLORS`, `TIPO_DIA_COLOR`, `PERIOD_ICON`, `QUADRANT_EMOJI/COLOR/LABEL/ACTION`, `SEVERITY_COLOR`). These are not "components" — they are pure data + small classification functions. They are documented in `04-COLOR-PALETTE.md`.
