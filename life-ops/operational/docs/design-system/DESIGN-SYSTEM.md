# Operational Design System (ODS) v2.0

> **Status:** Spec proposta. Implementação em fase 2 deste loop.
> **Re-brand completo:** "Time-Tasker / operational" → **"PAV-OS"** (Produtividade
> Algorítmica Visual — Operating System).
> **Inspiração:** Textual/Textualize (`rich`, `textual`), o aesthetic de
> dashboards densos de informação, mas com hierarquia visual clara.

---

## 1. Princípios Fundamentais

1. **Densidade com hierarquia** — muita info, mas com clara primária/secundária/terciária
2. **Cor é sinal, não decoração** — cada cor tem significado funcional
3. **Layout = 3 zonas** — Header / Work Area / Action Footer
4. **Zero texto redundante** — se KPI diz "8h", não repete "8 horas" embaixo
5. **Glifo Unicode > ASCII** — `▣ ▢ ◆ ▲ ▁▂▃▄▅▆▇█ ┊ ┈ ┼ ─ │` são primeira-classe
6. **Estado vazio é design** — não é exceção, é estado previsto
7. **Acessibilidade não é afterthought** — alto contraste + texto alternativo

---

## 2. Identidade Verbal

### 2.1 Nome do produto

| Antes | Depois | Razão |
|---|---|---|
| time-tasker | **pav-os** | Alinhado com PAV (Produtividade Algorítmica Visual) |
| operational (CLI name) | **pav** | Curto, mnemônico |
| "Time-Tasker — Algorítmica Visual" | **"PAV-OS — Cybernetic Life OS"** | Mais aspiracional |
| `operational report daily` | `pav report today` | Linguagem natural |

### 2.2 Tagline

> "Target. Sense. Adjust. — O loop cibernético do seu dia."

### 2.3 Vocabulário de marca

| Usar | Evitar | Razão |
|---|---|---|
| Snapshot | Status | Mais "fotografia do momento" |
| Quadrant | Bucket | Mais preciso, menos jargão |
| Regime | State | Mais claro, "PUSH regime" |
| Cadence | Pattern | Mais musical, lembra ritual |
| Drift | Deviation | Curto, geek-friendly |
| Sentinel | Watcher | Místico, cyberpunk vibe |

---

## 3. Design Tokens

### 3.1 Color Palette — "Photon Dark"

Base: terminal dark (default). Auto-detect light via `os.environ.get("PAV_THEME")`.

```python
# src/operational/ui/tokens.py

class Severity:
    """The 8 core semantic colors. NEVER use raw colors in components."""
    PRIMARY   = "dodger_blue1"     # Headers, focus, OK baseline
    SUCCESS   = "bright_green"     # Inside budget, regime MAINTAIN/PUSH
    WARNING   = "yellow"           # Drift detected, 80%+ of limit
    DANGER    = "bold red"         # Out of budget, Q3 quadrant, regime RECOVER
    INFO      = "deep_sky_blue1"   # Neutral informational
    MUTED     = "grey58"           # Secondary, historical, helpers
    ACCENT    = "magenta"          # Highlighted CTAs, "next step" hints
    INVERSE   = "black on white"   # Light theme only


class Surface:
    """Background tints (subtle, used only in dark theme for cards)."""
    BASE      = "default"          # Terminal default
    RAISED    = "grey11"           # KPI card background
    SUNKEN    = "grey7"            # Pomodoros grid empty cells
    HIGHLIGHT = "grey23"           # Selected row
    DANGER_ZONE = "dark_red"       # Q3 quadrant fill
    SUCCESS_ZONE = "dark_green"    # Q1 quadrant fill


class Regime:
    """The 4 policy regimes have distinct colors AND icons."""
    PUSH      = ("bright_green",  "▲")  # "Aumentar"
    MAINTAIN  = ("dodger_blue1",  "◆")  # "Manter"
    REDUCE    = ("yellow",        "▼")  # "Reduzir"
    RECOVER   = ("bold red",      "✗")  # "Recuperar"


class Quadrant:
    """The 4 Cartesian plane quadrants."""
    Q1 = ("bright_green", "◆", "Excelente")
    Q2 = ("cyan",         "▲", "Otimizado")
    Q3 = ("bold red",     "✗", "Crítico")
    Q4 = ("yellow",       "?", "Produtivo disperso")
```

### 3.2 Typography

```python
# Rich styles
class Style:
    H1 = "bold white on dodger_blue1"   # Page title
    H2 = "bold cyan"                     # Section header
    H3 = "bold white"                    # Subsection
    BODY = "default"                     # Regular text
    BODY_MUTED = "grey70"                # Secondary text
    MONO = "dim cyan"                    # IDs, dates, technical
    EMPHASIS = "bold yellow"             # Numbers that matter
    DANGER_NUM = "bold red"              # Bad numbers
    SUCCESS_NUM = "bold bright_green"    # Good numbers
```

### 3.3 Spacing

```python
# Padding tuples (vertical, horizontal) for Rich Panel/Table
PADDING = {
    "xs":  (0, 1),   # Inline, between widgets in same row
    "sm":  (0, 2),   # Default for KPI cards
    "md":  (1, 2),   # Section panels
    "lg":  (2, 4),   # Page-level padding
    "xl":  (3, 6),   # Modal/dialog only
}

# Margins between components
GAPS = {
    "tight": 0,       # Side-by-side
    "snug":  1,       # Same group
    "normal": 2,      # Different groups
    "loose": 4,       # Different sections
}
```

### 3.4 Glyph Library

```python
# src/operational/ui/glyphs.py

class Glyph:
    """Centralized Unicode glyphs. NEVER hardcode glyphs in components."""

    # Pomodoros
    POMO_DONE   = "▣"  # Completed
    POMO_SKIP   = "▢"  # Skipped/not done
    POMO_PARTIAL = "▤"  # Partial (work started but not completed)

    # Cartesian plane
    PT_EXCEL    = "◆"  # Q1 — excellent
    PT_OPT      = "▲"  # Q2 — optimized
    PT_CRIT     = "✗"  # Q3 — critical
    PT_DISP     = "?"  # Q4 — productive but dispersed
    LINE_V      = "┊"  # Vertical quadrant line
    LINE_H      = "┈"  # Horizontal quadrant line
    AXIS_CROSS  = "┼"  # 50% mark
    AXIS_X      = "─"  # X axis
    AXIS_Y      = "│"  # Y axis
    AXIS_LABEL  = "·"  # Tick mark

    # Sparkline (8 levels)
    SPARK = "▁▂▃▄▅▆▇█"

    # Progress bars
    BAR_FULL   = "█"
    BAR_SEVEN  = "▇"
    BAR_FIVE   = "▅"
    BAR_THREE  = "▃"
    BAR_ONE    = "▁"
    BAR_EMPTY  = "░"
    BAR_CURSOR = "▏"

    # Severity markers (use in place of ✗ for accessibility)
    SEV_CRIT  = "▲"  # Triangle = warning
    SEV_WARN  = "▵"  # Empty triangle
    SEV_OK    = "●"  # Filled circle
    SEV_MUTED = "○"  # Empty circle

    # Status
    CHECK     = "✓"  # Done
    CROSS     = "✗"  # Failed
    PENDING   = "◌"  # Pending
    ACTIVE    = "●"  # Currently active
```

---

## 4. Component Refactor (v2)

### 4.1 Header (NEW)

A 3-column header used on EVERY output screen:

```python
def header(
    title: str,        # "DAILY REPORT"
    subtitle: str,     # "2026-06-08"
    context: Renderable,  # Right: regime, quadrant, dataset name
    width: int = 120,
) -> Renderable:
    """3-zone header: title | subtitle | context badge.
    No heavy box — just bottom border with color."""
```

Wireframe:
```
──────────────────────────────────────────────────────────────────────────────
 DAILY REPORT        2026-06-08 ◆ LIVRE              regime: PUSH
──────────────────────────────────────────────────────────────────────────────
```

### 4.2 KPI Card v2

Before: 4-5 line panel with label/value/sub.
After: 1-line high-density card with semantic color:

```python
def kpi_v2(
    label: str,         # "Sono"
    value: str,         # "8.0h"
    severity: str,      # "ok" | "warn" | "crit" | "muted"
    delta: str | None,  # "+0.5h vs 7d"  (NEW: show trend inline)
    icon: str,          # "😴"
    width: int = 28,    # Fixed width for grid alignment
) -> Renderable:
    """Single-line KPI: [icon] [label] [value] [delta]
    Color of value matches severity."""
```

Wireframe:
```
┌──────────────────────────┐  ┌──────────────────────────┐
│ 😴 Sono       8.0h 🟢   │  │ 🍅 Pomodoros  0/12  🔴   │
│              +0.5h 7d   │  │              meta 12     │
└──────────────────────────┘  └──────────────────────────┘
```

### 4.3 Cartesian Plane v2 (the critical widget)

Before: 18x7 grid with bare axis labels.
After: 18x7 grid with **labels INSIDE the plot**, quadrant fill, hover info (when interactive):

```python
def cartesian_v2(
    x: float,           # 0-100
    y: float,           # 0-100
    quadrant: str,      # "Q1" | "Q2" | "Q3" | "Q4"
    show_legend: bool = True,  # NEW
    show_equation: bool = True,  # NEW: "x = realizado/orçado × 100"
    historical: list[tuple[float, float]] | None = None,  # NEW: past 7 days as dots
    width: int = 18,
    height: int = 7,
) -> Renderable:
    """Cartesian plane with quadrant fill, legend, equation, history."""
```

Wireframe (Q1 with 7-day history):
```
Y%  ┌─────────────────────┐
100 ┤   ··                 │  X = realizado / orçado × 100
 84 ┤ ·                    │  Y = foco / total × 100
 68 ┤                ◆     │  Q1: ◆ Excelente
 52 ┤┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┊┈  │  Q3: ✗ Crítico
 36 ┤                      │
 20 ┤  ·                   │  Histórico 7d: ▁▂▃▄▅▆▇
  4 ┼──────────────────────│
  0  0      50       100
```

### 4.4 Pomodoros Grid v2 (NEW: focus score per session)

Before: 3x4 grid of empty/done cells.
After: 3x4 grid with focus score per session, target line, completion %:

```python
def pomodoros_v2(
    sessions: list[PomodoroSession],  # 3 sessions
    target_per_session: int = 4,
    show_focus_score: bool = True,  # NEW
    show_interruption_count: bool = True,  # NEW
) -> Renderable:
    """Per-session: progress bar, focus score, interruptions."""
```

Wireframe:
```
S1 manhã  ▣ ▣ ▣ ▢  75%   ⭐ 8/10  ⚠ 0 pausas
S2 tarde  ▣ ▣ ▢ ▢  50%   ⭐ 6/10  ⚠ 1 pausa
S3 noite  ▢ ▢ ▢ ▢   0%   ⭐ -    ⚠ -

Total: 5/12 (42%)   Foco médio: 7.0/10
```

### 4.5 Section Panel v2

Before: Box with title + content.
After: Box with title + content + **subtitle** + optional footer:

```python
def section_v2(
    title: str,            # "EASE"
    icon: str,             # "🛌"
    subtitle: str,         # "Rotinas + sono + refeições"
    content: Renderable,
    severity: str = "primary",  # Border color
    footer: Renderable | None = None,  # NEW: small summary at bottom
) -> Renderable:
```

### 4.6 Timeline (NEW)

Use `rich.columns.Columns` for horizontal layout. Used in: home menu, doctor:

```python
def timeline(
    events: list[tuple[str, str]],  # (timestamp, label)
    max_width: int = 120,
) -> Renderable:
    """Horizontal timeline with dots and connectors."""
```

Wireframe:
```
─ 06:00 ─── 07:00 ─── 09:00 ─── 12:00 ─── 14:00 ─── 18:00 ─── 22:00 ───
  ● wake     ● coffee   ● class    ● lunch     ● work     ● dinner    ● sleep
  ✓          ✓          ✓          ⚠ heavy     ✓          ✓          ◌
```

### 4.7 Regime Bar (NEW)

Visual indicator of current policy regime with arrow showing direction:

```python
def regime_bar(
    current: PolicyState,
    history: list[PolicyState] | None = None,  # last 7 days
) -> Renderable:
    """Bar showing PUSH → MAINTAIN → REDUCE → RECOVER with marker.
    Optionally shows history as dots above."""
```

Wireframe:
```
        PUSH    MAINTAIN   REDUCE   RECOVER
         ▲◆      ◇◇◇        ◇◇       ◇◇◇
        today   3 dias    2 dias   2 dias
```

### 4.8 Sparkline v2 (NEW: with min/max)

Before: 8-char sparkline.
After: 8-char sparkline + min/max labels + current value:

```python
def sparkline_v2(
    values: list[float],
    label: str,
    current_format: str = "{:.0f}",
    show_min_max: bool = True,  # NEW
) -> Renderable:
```

### 4.9 Quadrant Bar Chart v2

Before: `Q1   7  ████████████████`
After: 5 columns: Q1, Q2, Q3, Q4 + total + target line:

```
Quadrante   Q1   Q2   Q3   Q4
─────       ───  ───  ───  ───
Dias        5    1    1    0
%          71%  14%  14%   0%
                                    target: 80% Q1
                                    atual:  71% Q1 ⚠
```

### 4.10 Next Step v2 (NEW: dual-line)

Before: single line "Maintain rhythm".
After: **observation → action** (2 lines):

```
OBSERVAÇÃO: Q1 mantido por 5 dias consecutivos.
AÇÃO:       Aumentar pomodoros de 12 para 14 (gradual).
```

### 4.11 Error Panel v2

Before: red box with message.
After: red box with message + **context** + **suggested fix**:

```
┌─ ⚠ ERRO ────────────────────────────────────────────────────────────┐
│ Data inválida: 2026-13-99                                           │
│                                                                    │
│ Contexto:    comando `pav report daily --date 2026-13-99`          │
│ Esperado:    YYYY-MM-DD (ano-mês-dia, mês 01-12, dia 01-31)        │
│ Sugestão:    pav report daily --date 2026-06-08                    │
│                                                                    │
│ Pressione qualquer tecla para voltar.                              │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. Layout System

### 5.1 Page template (NEW)

Every output screen follows this template:

```python
def page(
    header_ctx: HeaderContext,    # title, subtitle, regime
    primary_zone: Renderable,     # 60% of vertical space
    secondary_zone: Renderable,   # 30%
    action_footer: Renderable,    # 10% — "next step" or error
    width: int = 120,
) -> Renderable:
    """Standard page layout: header → primary → secondary → action."""
```

### 5.2 Zone composition (NEW)

Each "zone" is built from **1+ columns** of widgets. Use `rich.columns.Columns`:

```python
from rich.columns import Columns

# KPI grid (2x2)
kpi_grid = Columns([
    kpi_v2(...), kpi_v2(...),
    kpi_v2(...), kpi_v2(...),
], equal=True, expand=True)
```

### 5.3 Z-ordering (visual hierarchy)

When multiple zones conflict for attention:
1. **DANGER** color always wins (Q3, regime RECOVER, error)
2. **Action footer** is the only place that says "do this"
3. **Primary zone** shows current state
4. **Secondary zone** shows context
5. **Header** is the smallest font size

---

## 6. Interactive Widgets (NEW — the gap)

### 6.1 Hover Tooltips (Textual-style)

For now (CLI = non-interactive), we use **footnote markers**:

```
😴 Sono       8.0h 🟢 ¹
  ¹ Qualidade 9/10, sem interrupções, acordar descansado
```

### 6.2 Progress Display

Use `rich.progress.Progress` for long operations (CSV import, dataset load):

```python
with Progress() as progress:
    task = progress.add_task("Importando golden.csv...", total=151)
    for row in rows:
        repo.upsert(row)
        progress.update(task, advance=1)
```

### 6.3 Status Spinner

Use `rich.status.Status` for sub-second operations:

```python
with console.status("[cyan]Carregando snapshot..."):
    snapshot = get_day_snapshot(date)
```

### 6.4 Live Updating (for monitor mode)

Use `rich.live.Live` for `--watch` flag on reports:

```python
with Live(generate_report(), refresh_per_second=1) as live:
    while True:
        live.update(generate_report())
        sleep(60)
```

### 6.5 Markdown Rendering

Use `rich.markdown.Markdown` for any text field that may contain markdown:

```python
Markdown("## Insights\n- *Bom ritmo esta semana*\n- **Q1 mantido**")
```

### 6.6 JSON Syntax Highlighting

Use `rich.json.JSON` for `--json` output instead of `json.dumps`:

```python
console.print(JSON(payload))
```

### 6.7 Tree View

Use `rich.tree.Tree` for hierarchical views (routines per period):

```python
Tree("Rotinas").add(
    Tree("MANHÃ").add("Acordar 06:00", "Workout 06:30")
)
```

### 6.8 Columns (NEW)

For dense horizontal layouts (KPI grid, button bar):

```python
from rich.columns import Columns
Columns([card1, card2, card3], equal=True, expand=True)
```

---

## 7. Mock Data Switch (CRITICAL for visual debug)

### 7.1 The problem

Visual regression testing requires **deterministic** data. Today the only way to test a new component is to:
1. Manually `operational demo seed`
2. Run the command
3. Eyeball the output
4. Hope you didn't introduce a regression

### 7.2 The solution

Add `--mock` flag to every output command:

```bash
pav report today --mock q1     # Forces Q1 quadrant, all green
pav report today --mock q3     # Forces Q3 quadrant, all red
pav report today --mock golden # Uses data from docs/golden.csv
pav report today --mock synth  # Uses data from docs/synthetic.csv
```

### 7.3 Mock profiles

```python
# src/operational/ui/mock_profiles.py

MOCK_PROFILES: dict[str, MockData] = {
    "q1": MockData(
        quadrant="Q1", orcado=540, realizado=540, foco_min=480, total_min=480,
        pomodoros=(12, 12), sleep_quality=9, sleep_hours=8.0,
        regime=PolicyState.PUSH, energy=9, foco=9,
    ),
    "q2": MockData(...),
    "q3": MockData(...),
    "q4": MockData(...),
    "empty": MockData(quadrant="N/A", orcado=0, realizado=0, ...),
    "burnout": MockData(quadrant="Q3", regime=RECOVER, energy=2, foco=3, sleep_hours=4),
    "peak": MockData(quadrant="Q1", regime=PUSH, energy=10, foco=10, sleep_hours=9),
}
```

### 7.4 Visual test workflow

```bash
# Test 1: Healthy day
pav report today --mock q1 > /tmp/snap_q1.txt

# Test 2: Burnout
pav report today --mock burnout > /tmp/snap_burnout.txt

# Diff: confirm error panel appears differently, colors differ
diff /tmp/snap_q1.txt /tmp/snap_burnout.txt
```

---

## 8. Re-brand — Concrete Changes

### 8.1 File rename

| Old | New |
|---|---|
| `pyproject.toml` name = "operational" | name = "pav-os" |
| `src/operational/__init__.py` | (unchanged) |
| Entry point `operational` | Entry point `pav` |
| `cli/app.py` `app = typer.Typer(name="time-tasker", ...)` | `app = typer.Typer(name="pav", ...)` |
| `src/operational/cli/console.py` console width=120 | console width=128 (wider for v2 widgets) |

### 8.2 Tagline locations

Replace every "Time-Tasker — Algorítmica Visual" with "PAV-OS — Cybernetic Life OS":

- `cli/app.py:33` (help text)
- `cli/__main__.py` (if exists)
- `pyproject.toml` description
- `README.md` first line

### 8.3 Color migration

| Old | New | When |
|---|---|---|
| `cyan` | `dodger_blue1` | Headers (more saturated) |
| `bright_green` | `bright_green` | (unchanged) |
| `bold red` | `bold red` | (unchanged) |
| `yellow` | `yellow` | (unchanged) |
| `deep_sky_blue1` | `deep_sky_blue1` | (unchanged) |
| `grey58` | `grey70` | (slightly more readable) |

### 8.4 Help text

Before:
```
⚡ TIME-TASKER — Algorítmica Visual: rotinas, blocos, hábitos, métricas, policy.
```

After:
```
◆ PAV-OS — Cybernetic Life OS — Target. Sense. Adjust.

Dashboard pessoal: sono, foco, hábitos, regime. Dados locais, sem cloud.
```

---

## 9. Migration Path (Safe)

Phase 1 (this loop): **add new widgets, don't remove old**
- Add `ui/v2/` alongside `ui/components.py`
- New commands get v2 widgets, old commands keep v1
- Both render side-by-side for visual diff

Phase 2 (next loop): **gradual swap**
- Move v2 widgets to `ui/components.py` (with v1 as fallback)
- Update commands one at a time
- `git diff` each command's output

Phase 3 (later): **deprecate v1**
- v1 widgets stay for tests
- New commands use v2 only
- Final commit removes v1

---

## 10. Acceptance Criteria

For the redesign to be considered done:

- [ ] `pav report today --mock q1` shows green Q1
- [ ] `pav report today --mock q3` shows red Q3
- [ ] `pav report today --mock burnout` shows RECOVER regime
- [ ] `pav report today --mock empty` shows clean empty state
- [ ] All 7 widget tokens used consistently
- [ ] Console width = 128
- [ ] `pav` (not `operational`) is the entry point
- [ ] All Pydantic entities still validate (no breaking changes)
- [ ] All 2755 tests still pass

---

## 11. Out of Scope (For Later)

- Textual TUI app (full interactive) — separate project
- Web UI (textual-serve) — backlog item
- 3rd-party theme marketplace — backlog item
- Real-time sync with external systems — backlog item

---

*This spec is the source of truth for the re-brand. All changes must reference
this doc and update the Acceptance Criteria section.*
