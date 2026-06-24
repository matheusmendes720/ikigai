# PAV-OS Terminal Design Audit — `life-ops/operational/`

> **Author:** deep analysis pass on 2026-06-22
> **Scope:** CLI (Typer + Rich) + TUI (Textual) + plotext visualization
> **Audience:** author of the project (Matheus) + future contributors
> **Length:** long. Each section is self-contained — you can skip to a topic.

---

## Table of Contents

1. [TL;DR — the 5 things to fix first](#1-tldr--the-5-things-to-fix-first)
2. [The conceptual model: how terminal apps actually work](#2-the-conceptual-model-how-terminal-apps-actually-work)
3. [What you have today — mapped](#3-what-you-have-today--mapped)
4. [Design pattern library](#4-design-pattern-library)
5. [Data stream architecture for I/O processing](#5-data-stream-architecture-for-io-processing)
6. [Screen-by-screen UX critique](#6-screen-by-screen-ux-critique)
7. [Command-by-command CLI critique](#7-command-by-command-cli-critique)
8. [Concrete refactor plan + code samples](#8-concrete-refactor-plan--code-samples)
9. [Implementation roadmap](#9-implementation-roadmap)
10. [Appendix A — what to update in docs/](#appendix-a--what-to-update-in-docs)

---

## 1. TL;DR — the 5 things to fix first

| # | Severity | Issue | File | Fix in |
|---|----------|-------|------|--------|
| 1 | **🔴 P0 — crashes on every interactive choice** | `home_v2.py:187` references `str(ROOT)` but `ROOT` is never imported. Every interactive subcommand (reflect, journal, routine, block, metric) will crash with `NameError` the moment you pick option 1–4 or 5–10. The non-interactive path (`_run_cmd` with `redirect_stdout`) doesn't hit this code, so it can stay latent. | `apps/cli/src/operational/cli/home_v2.py:187` | 15 min |
| 2 | **🔴 P0 — TUI memory leak** | `PAVApp.action_switch_*` calls `push_screen()` for keys 1–7. After 30 minutes of use, the screen stack has 100+ screens. `pop_screen()` only happens on `Esc`. Use `switch_screen()` (which pops + pushes). | `apps/tui/src/operational/tui/app.py:83-102` | 10 min |
| 3 | **🟠 P1 — TUI screens don't show real data** | `DashboardScreen.on_mount()` sets the same hardcoded `value="8.0h"` that was passed to `compose()`. The whole TUI is a "design system demo", not a data app. It never reads from `get_day_snapshot()`. | `apps/tui/src/operational/tui/screens/dashboard_screen.py:65-74` (+ all 6 other screens) | 2 days |
| 4 | **🟠 P1 — duplicate color literals** | `widgets/kpi_card.py` defines `_CORAL = "#ff6b6b"`, `_TEAL = "#4ecdc4"`, etc. — but `theme.py` already has them in `TUI_COLORS`. Two sources of truth = design drift. | `apps/tui/src/operational/tui/widgets/kpi_card.py:7-12` (+ similar in 4 other widgets) | 1 hour |
| 5 | **🟡 P2 — spec drift** | `docs/ux/05-telas/SCR-*.md` describes 15 screens with modal/tab flow specs, but the TUI implements only 7 (no "Lunch", "Reflect", "Block create", "Routine create" etc. as screens). The TUI is a *dashboard*, not a CRUD app. Decide if TUI is read-only dashboards, or implement the missing 8. | `docs/ux/05-telas/` vs `apps/tui/src/operational/tui/screens/` | design decision |

**Bonus 6 (P2, found while reading):** `apps/tui/src/operational/tui/navigation.py` defines a `TUIState` global with `get_state()` / `set_state()` / `navigate_to()` helpers, but `PAVApp` and the screens don't use any of them. Dead code from a half-finished refactor. Either wire it up or delete it.

---

## 2. The conceptual model: how terminal apps actually work

> If you're new to terminal interfaces, read this section first — it gives you the vocabulary for the rest of the document.

A terminal app lives in a 80×24 (or wider) grid of cells. Each cell holds one character with one foreground color and one background color. That's it. No pixels, no z-index, no animation primitives. Everything you see is a sequence of "print this glyph at this position with this color".

That constraint is the source of all terminal UX patterns. Once you internalize it, every design choice becomes obvious.

### 2.1 The four primitive operations

| Op | What it does | Python tool | When to use |
|---|---|---|---|
| **Print** | write a string to the screen | `print()`, `Console.print()`, `typer.echo()` | one-shot output (reports, tables) |
| **Prompt** | read a line of input from the user | `typer.prompt()`, `rich.prompt.Prompt.ask()`, `input()` | small CLI forms |
| **Live** | repeatedly rewrite a region of the screen | `rich.live.Live`, `textual` widgets | progress bars, spinners, ticking timers |
| **Full-screen** | take over the terminal, run an event loop | `textual.app.App`, `curses` | TUIs (multiple screens, key bindings) |

Your app uses all four. The most common mistake beginners make is conflating "prompt" with "live" — they try to do interactive forms with `print` + `input()`, which leaves the screen full of stale text.

### 2.2 Three layers, never crossed

A well-designed terminal app has three layers, and **data flows only downward**:

```
┌──────────────────────────────────────────────┐
│  L3: PRESENTATION                            │  ← Rich, Textual, plotext
│  - Receives plain dataclasses / dicts        │
│  - Renders, prompts, animates                │
│  - No business logic, no validation          │
├──────────────────────────────────────────────┤
│  L2: ORCHESTRATION                           │  ← Typer commands, TUI actions
│  - Calls L1 functions                        │
│  - Translates between domain exceptions      │
│    and user-facing error panels              │
│  - No I/O directly on raw files              │
├──────────────────────────────────────────────┤
│  L1: DOMAIN                                   │  ← core/ + entities/ + persistence/
│  - Pure Python functions (no Rich, no Typer) │
│  - Pydantic models                           │
│  - Repository pattern (InMemory + JSON dump) │
└──────────────────────────────────────────────┘
```

**Why this matters:** the moment you import `rich` from `core/`, you can't unit-test the domain without a terminal emulator. The moment you `json.dumps()` from a Typer command, you can't reuse the same logic from the TUI. You already do this well — `apps/cli/src/operational/cli/services.py` is exactly L2 (orchestration that combines L1 repos + L1 services) and `apps/cli/src/operational/cli/formatters/` is exactly L3 (presentation). The TUI breaks this slightly (see §6).

### 2.3 The design-token principle

A *design token* is a named semantic value that components reference instead of literal hex codes. Example: instead of `color: "#1E90FF"` you write `color: "$primary"`. Then if you want a dark/light theme, you change the token mapping, not every component.

Your `apps/tui/src/operational/tui/theme.py` does this correctly with a `Theme(variables={...})`. Your `apps/cli/src/operational/ui/tokens.py` (referenced in `home_v2.py`) has `SEVERITY` and `STYLES` dicts. But several widgets duplicate the literals (see issue #4). The fix is to make all widget colors reference the theme tokens.

### 2.4 The data-stream / event-loop split

This is the part most beginners miss. A terminal interface has **two fundamentally different modes**:

| Mode | Data direction | Examples |
|------|---------------|----------|
| **Streaming (record-at-a-time)** | Repo → filters → renderer, one item at a time | CSV import, log tail, pomodoro ticks |
| **Snapshot (full state)** | Repo → aggregator → renderer, all at once | daily report, dashboard, home menu |

A good app uses the right one for each screen. Your `state show` command is a snapshot (whole day). Your `demo import_csv` is streaming (one entity at a time, progress bar). The TUI dashboard is *currently* a snapshot but should be **streaming** (a `set_interval(1.0, refresh_from_repo)` so the KPIs auto-update as you log pomodoros in another tab — Textual's `set_interval` is purpose-built for this).

### 2.5 Navigation patterns

Terminal apps have three navigation patterns:

1. **Numbered menu** (your `home_v2.py`) — pick `1-10` or `q` to exit. Best for ≤15 options.
2. **Command palette** (`:` in vim, `Ctrl+P` in VS Code) — fuzzy search, scales to 100+ actions. You spec it in `help_screen.py:59` (`[:]  Command mode`) but it's not implemented.
3. **Screen switcher** (`1-7` in your TUI) — fixed number of views, key-bound. Best for 2–9 top-level screens.

You use all three patterns. They don't conflict — they live at different layers (home menu → command palette → screen).

---

## 3. What you have today — mapped

I read all 7 TUI screens, 12 CLI sub-typers, 16 widgets, the design system spec, and your latest usability report. Here's the inventory:

### 3.1 Strengths (don't break these)

1. **Three-layer MVC is real** — `core/` has zero `import rich` (let me re-verify), `cli/commands/` is thin, `ui/` owns Rich.
2. **Design system spec is mature** — `docs/design-system/DESIGN-SYSTEM.md` is 676 lines of design tokens, component wireframes, and an acceptance checklist. This is rare and good.
3. **UX spec is rich** — 15 screen specs (`SCR-001` to `SCR-015`), 10 flow specs (`FLOW-001` to `FLOW-010`), 12 component specs, 3 risk docs. Whoever wrote these knows what they're doing.
4. **All commands support `--json`** — enables scripting and testing.
5. **`get_day_snapshot()` is the single source of truth for the UI** — the L2 layer that aggregates 14 repos into one normalized dataclass. This is the right pattern.
6. **Repository pattern with JSON dump** — `_PersistentRepo` writes the full state to `~/.time-tasker/*.json` after every mutation. Predictable, debuggable, version-controllable.
7. **Plotext wrapper class** (`PlotextChart`) — abstracts `px.clf()` and adds 6 chart types (sparkline, bar, scatter, line, dual_axis, subplot). Reusable.
8. **Modal help screen** — `Ctrl+H` from anywhere pops a `ModalScreen` with sectioned keybinding reference. Standard pattern, well executed.
9. **Manual test report** — `test_results/usability_report_20260622_162040.md` shows 29/29 manual tests pass. You're testing the CLI directly, not just unit tests.
10. **Multi-level keybinding hierarchy** — `L0` (universal), `L1` (navigation), `L2` (screen actions), `L3` (power). Surfaced in the help screen. This is a real pattern (used by `k9s`, `lazygit`, `btop`).

### 3.2 Gaps & issues (the audit)

I categorized 23 issues. Top 5 in TL;DR (§1). Full list in §6 and §7 below. Summary by category:

| Category | Count | Severity |
|----------|-------|----------|
| Crashes / undefined names | 1 | 🔴 P0 |
| Memory leaks / wrong API usage | 1 | 🔴 P0 |
| TUI doesn't bind to real data | 7 | 🟠 P1 |
| Code duplication / dead code | 5 | 🟠 P1 |
| Spec drift (docs say X, code does Y) | 4 | 🟡 P2 |
| UX micro-issues | 5 | 🟡 P3 |

---

## 4. Design pattern library

This is the meta-skill you asked for — a catalog of patterns you can apply to new screens, commands, or flows. Each pattern has: name, when to use, your project's current adoption, code template.

### 4.1 CLI patterns

#### 4.1.1 Numbered categorized menu (your `home_v2.py`)

**When:** top-level entry point, ≤15 options, mixed audience (new + power users).

**Your adoption:** ✅ implemented. 3 groups, 10 items, submenu for reports.

**Code template (already in `home_v2.py`):**
```python
MENU_GROUPS: list[dict] = [
    {"key": "FLUXO", "title": "...", "icon": "🚀", "severity": "primary", "items": [...]},
    {"key": "DASHBOARD", ...},
    {"key": "DADOS", ...},
]
```

**Recommended enhancement:** add `["?", "📖 Ajuda", "Este menu"]` as item 11 and bind it to `_print_help()`. New users always want to know what the keys mean.

#### 4.1.2 Subcommand with `--json` (your every command)

**When:** every command should be both human-friendly and scriptable.

**Your adoption:** ✅ universal. Every command in `cli/commands/*.py` has `--json`.

**Code template (from `demo_cmd.py`):**
```python
@app.command()
def seed(json: bool = typer.Option(False, "--json", help="JSON output")) -> None:
    if json:
        typer.echo(format_as_json({"status": "seeded", "summary": summary}))
    else:
        with console.status("[cyan]Seeding...", spinner="dots"):
            summary = seed_demo_data()
        console.print(summary)
```

**Recommended enhancement:** always include the command name in JSON output: `{"command": "demo seed", "ok": true, "data": ...}`. Makes logs and pipelines readable.

#### 4.1.3 Subprocess dispatch for interactive subcommands

**When:** the menu itself is non-interactive (numbered choices) but a subcommand needs a TTY for `Prompt.ask`.

**Your adoption:** ✅ implemented (`_is_interactive()` + `subprocess.run([...])`).

**Code template (from `home_v2.py:172-194`):**
```python
if _is_interactive(args):
    subprocess.run(["uv", "run", "--directory", str(ROOT), "pav", *args], check=False)
```

**The bug:** `ROOT` is not defined in this file. It needs to be `Path(__file__).parent.parent.parent` or imported from a config module. See §8.1 for the fix.

#### 4.1.4 Status spinner for sub-second ops

**When:** work that takes 100ms–2s (seeding, clearing, snapshot aggregation).

**Your adoption:** ✅ used in `demo_cmd.py` seed/clear/export. Use `console.status(spinner="dots")`.

**Why it matters:** without a spinner, a 500ms operation looks like a frozen terminal. Rich's `console.status` shows an animated glyph and a message.

#### 4.1.5 Progress bar for multi-second ops

**When:** work that takes 2s+ and processes N items (CSV import, batch ops).

**Your adoption:** ✅ used in `demo_cmd.py import_csv` with `rich.progress.Progress(console=console, transient=True)`.

**Pattern:** one `add_task` per item type, `progress.update(task, advance=1)` per item. Use `transient=True` to auto-clear the bar on completion.

#### 4.1.6 Async I/O for genuinely long ops

**When:** work that takes >10s and is CPU-bound (e.g. CSV parsing 100MB).

**Your adoption:** ❌ nowhere. All `seed_demo_data` and `import_csv` are synchronous. Rich's spinner lies (it animates while the work is running synchronously, which is fine for ≤2s, but blocks the event loop for longer).

**Pattern (proposed):**
```python
async def seed_async(progress_cb: Callable[[int, int], None]) -> SeedSummary:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, seed_demo_data, progress_cb)
```

#### 4.1.7 Layered JSON output (machine + human)

**When:** you want a single command to be both `--json` and `--pretty`.

**Pattern:**
```python
def _output(payload: dict, json: bool, pretty_panel: Callable[[dict], Renderable]) -> None:
    if json:
        typer.echo(JSON(payload, indent=2))  # rich.json.JSON for syntax highlight
    else:
        console.print(pretty_panel(payload))
```

### 4.2 TUI patterns

#### 4.2.1 Screen = `Screen` subclass, registered in `SCREENS` dict

**When:** every top-level TUI view.

**Your adoption:** ✅ universal. All 7 screens extend `Screen` (or `ModalScreen` for overlays), and `PAVApp.SCREENS` maps strings to classes.

**Pattern:**
```python
class DashboardScreen(Screen):
    BINDINGS = [...]  # screen-level key bindings
    CSS = "..."       # screen-level CSS

    def compose(self) -> ComposeResult:
        yield Header()  # built-in
        yield MyWidget(...)
        yield Footer()  # built-in

    def on_mount(self) -> None:
        self.query_one("#kpi-sono", KPICard).value = "8.0h"
```

#### 4.2.2 Modal overlay for help / dialogs

**When:** secondary view that should block the underlying screen.

**Your adoption:** ✅ used in `HelpScreen` (extends `ModalScreen`).

**Pattern:**
```python
class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Close", show=False)]

    def action_dismiss(self) -> None:
        self.dismiss()
```

#### 4.2.3 `push_screen` vs `switch_screen` vs `pop_screen`

**When:** navigating between screens.

| Method | Stack effect | Use case |
|--------|--------------|----------|
| `push_screen("foo")` | push on stack | drill into a sub-screen, return via `Esc` |
| `switch_screen("foo")` | pop to root, then push | replace current top-level screen (your `1-7` keys) |
| `pop_screen()` | pop top | back navigation (your `Esc`) |

**Your adoption:** ❌ wrong. You use `push_screen` for global `1-7` keys, which causes a stack leak. Fix: change `action_switch_*` to use `switch_screen`. See §8.2.

#### 4.2.4 Widget = `Static` subclass with `render()`

**When:** any reusable visual element (KPI card, regime bar, sparkline).

**Your adoption:** ✅ used. `KPICard`, `RegimeBar`, `PomodoroGrid`, `HabitStreakDisplay` all extend `Static` and override `render()`.

**Pattern (from `kpi_card.py`):**
```python
class KPICard(Static):
    DEFAULT_CSS = """KPICard { ... }"""

    def __init__(self, label, value, delta="", icon="", severity="primary", **kwargs):
        super().__init__(**kwargs)
        self.label, self.value, self.delta, self.icon, self.severity = (
            label, value, delta, icon, severity,
        )

    def render(self) -> str:
        return f"[{_TEAL}]{self.icon}[/{_TEAL}] [{_TEXT}]{self.label}[/{_TEXT}] {self.value}"
```

**Issue:** the colors are hardcoded. Should reference the theme via `$primary` CSS variables.

#### 4.2.5 Data refresh via `set_interval`

**When:** a screen should auto-update from the data source every N seconds.

**Your adoption:** ❌ not used. All TUI screens are static.

**Pattern:**
```python
class DashboardScreen(Screen):
    def on_mount(self) -> None:
        self._refresh_data()
        self.set_interval(2.0, self._refresh_data)  # every 2s

    def _refresh_data(self) -> None:
        snap = get_day_snapshot(date.today())
        self.query_one("#kpi-sono", KPICard).value = f"{snap.sleep.duration_hours:.1f}h"
```

#### 4.2.6 Command palette (the missing `:` key)

**When:** app has 10+ actions, no room for key bindings.

**Your adoption:** ❌ spec'd in help but not implemented.

**Pattern (proposed):**
```python
class CommandPaletteScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Cancel", show=False)]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Type a command...", id="cmd-input")
        yield ListView(id="cmd-list")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value
        self.dismiss(cmd)

# In PAVApp:
def action_command_palette(self) -> None:
    def on_selected(cmd: str | None) -> None:
        if cmd:
            self.run_action(cmd)  # or exec the command
    self.push_screen(CommandPaletteScreen(), on_selected)
```

### 4.3 Data-stream / I/O patterns

#### 4.3.1 Snapshot pattern (read full state, render once)

**When:** a screen needs all the data to compute its display (dashboard, report).

**Your adoption:** ✅ `services.get_day_snapshot(date)`.

**Pattern:**
```python
@dataclass(frozen=True)
class DaySnapshot:
    date: date
    sleep: SleepSnapshot
    pomodoros_meta: int
    # ... 30+ fields

def get_day_snapshot(d: date) -> DaySnapshot:
    # Pull from all relevant repos, return one normalized object
    ...
```

**Tip:** if the function is slow (>100ms), make it async. If it's called frequently, cache the result keyed by `(date, version_counter)` where `version_counter` is incremented on every repo write.

#### 4.3.2 Stream pattern (read N items, render one at a time)

**When:** progress bar, log tail, ticking timer.

**Your adoption:** ✅ `demo import_csv` with `rich.progress.Progress`.

**Pattern:**
```python
with Progress(console=console, transient=True) as progress:
    for etype, entities in groups.items():
        task = progress.add_task(f"  {etype}", total=len(entities))
        for ent in entities:
            repo.upsert(ent)
            progress.update(task, advance=1)
```

#### 4.3.3 Reactive pattern (data store, observers)

**When:** multiple screens need to react to data changes.

**Your adoption:** ❌ not used. Each screen reads repos directly.

**Pattern (proposed with Textual):**
```python
class ReactiveRepo(Repository[T]):
    def __init__(self):
        super().__init__()
        self._observers: list[Callable[[str, T], None]] = []

    def subscribe(self, cb: Callable[[str, T], None]) -> None:
        self._observers.append(cb)

    def upsert(self, entity: T) -> None:
        super().upsert(entity)
        for cb in self._observers:
            cb("upsert", entity)
```

Then the TUI's `DashboardScreen.on_mount` subscribes, and a CLI write triggers a refresh.

#### 4.3.4 Mock profile switch (your `pav state show` with `TIME_TASKER_DATASET`)

**When:** visual regression testing, design demos, screenshot generation.

**Your adoption:** ✅ via `TIME_TASKER_DATASET` env var (set in `state.py:_auto_load_dataset`).

**Pattern (more powerful — see DESIGN-SYSTEM.md §7.2):**
```bash
pav report today --mock q1     # Force Q1 quadrant
pav report today --mock burnout
pav report today --mock empty
```

The current `TIME_TASKER_DATASET` mechanism only switches between CSVs. Adding `--mock` per-command gives finer control.

---

## 5. Data stream architecture for I/O processing

> The user asked: "help me to build complete app interface design patterns and data streams architectures.. for IO processing"

Here's the unified picture, in three diagrams.

### 5.1 CLI I/O flow

```
User input
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Typer parser (cli/app.py + cli/commands/*.py)            │
│  - parses argv                                            │
│  - dispatches to command function                         │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────┐
│ Orchestrator (cli/services.py + cli/state.py)            │
│  - pulls from _PersistentRepo (in-memory + JSON)         │
│  - calls core/ algorithms (get_day_snapshot, etc.)        │
│  - handles domain exceptions                              │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────┐
│ Formatter (cli/formatters/ + ui/components_v2.py)        │
│  - takes a plain dataclass / dict                         │
│  - emits Rich renderable (Table, Panel, Live)            │
│  - or JSON if --json flag                                 │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
Console (stdout, Rich Console, utf8)
```

**The "interactive" exception:** when the command needs `Prompt.ask` (e.g. `pav reflect entrada`), the flow forks:

```
Menu dispatcher (home_v2.py:_run_cmd)
  │
  ├── read-only: capture stdout via redirect_stdout, render in-process
  │
  └── interactive: subprocess.run(["pav", ...])  ← fresh TTY
                       │
                       ▼
                 Typer parser → command → Prompt.ask (real TTY) → exit
```

The "fresh TTY" trick is the only way to get `rich.prompt.Prompt.ask` to work after a `redirect_stdout` has captured the parent's stdin/stdout. This is fragile and a known papercut. See §8.1 for a fix that avoids subprocess.

### 5.2 TUI I/O flow

```
Textual event loop
  │
  ├── on_key(event)           ← intercepts q, Ctrl+H
  ├── on_button_pressed       ← button clicks
  ├── on_input_submitted      ← text input
  ├── on_tabs_tab_changed     ← tab clicks
  ├── set_interval(2.0, ...)  ← timer ticks (your screens don't use this yet)
  │
  ▼
Screen.action_*(self)         ← dispatched from BINDINGS
  │
  ▼
Service call                  ← cli/services.get_day_snapshot
  │
  ▼
Repo read                     ← _PersistentRepo.list()
  │
  ▼
Widget.update() / .render()   ← refreshes affected widgets
  │
  ▼
Textual repaints              ← dirty-region diff
```

**The gap:** the arrow from "Service call" to "Widget update" doesn't exist in your code. Your `DashboardScreen._refresh_data` would call `get_day_snapshot()`, mutate the `KPICard.value` attribute, and then... nothing happens. The widget only re-renders when `refresh()` is called explicitly. Your `HabitsScreen.on_mount` does this (line 73: `widget.refresh()`) but `DashboardScreen.on_mount` doesn't. The pattern is:

```python
def _refresh_data(self) -> None:
    snap = get_day_snapshot(today)
    card = self.query_one("#kpi-sono", KPICard)
    card.value = f"{snap.sleep.duration_hours:.1f}h"
    card.refresh()  # ← mandatory
```

**Or**, the more idiomatic Textual way: use `reactive` attributes on your widget, and Textual auto-refreshes.

```python
class KPICard(Static):
    value = reactive("")  # Textual watches this

    def watch_value(self, old: str, new: str) -> None:
        self.refresh()  # called automatically when value changes
```

### 5.3 Data store architecture

```
┌──────────────────────────────────────────────────────────┐
│ 14 entity types (Pydantic v2 frozen models)              │
│                                                          │
│ Routine  TimeBlock  JournalEntry  Habit                  │
│ RoutineLog  SleepRecord  PomodoroRound  PolicyDecision   │
│ PolicySetpoints  AjusteFino  DayContext  DailyReflection │
│ LunchRecord  TransicaoRegistrada                         │
└────────────┬─────────────────────────────────────────────┘
             │ one repo per type
             ▼
┌──────────────────────────────────────────────────────────┐
│ _PersistentRepo (InMemoryRepository + JSON dump)         │
│  - in-memory dict (fast reads)                           │
│  - write to ~/.time-tasker/<type>.json on every mutation│
│  - reads from JSON on first import                       │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────┐
│ Aggregation layer (cli/services.py)                      │
│  - get_day_snapshot(date) → DaySnapshot                  │
│  - compute_day_quadrant(snap) → (Q, x, y)                │
│  - distribute_pomodoros_across_sessions(n) → (s1,s2,s3)  │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────┐
│ Presentation (ui/components_v2.py + tui/widgets/*)       │
│  - takes a DaySnapshot or domain object                  │
│  - emits Rich/Textual renderable                         │
└──────────────────────────────────────────────────────────┘
```

This is the right shape. The P1 fix is wiring the bottom two layers together (see §6.1).

---

## 6. Screen-by-screen UX critique

For each of the 7 TUI screens, I give: what it should do, what it does today, the gap, and a fix.

### 6.1 DashboardScreen

**Should do:** show 4 KPIs (sleep, pomodoros, energy, focus) from the current `DaySnapshot`, the current regime with history, the pomodoro grid for today, and the next step computed from the data.

**Today does:** renders hardcoded values. `compose()` passes `value="8.0h"` to each `KPICard`. `on_mount()` then re-sets them with the same hardcoded values.

**Gap:** the data is never read. The "next step" is a literal string. There's no date selector.

**Fix:**
```python
def on_mount(self) -> None:
    self._refresh_data()
    self.set_interval(2.0, self._refresh_data)  # auto-refresh every 2s

def _refresh_data(self) -> None:
    from datetime import date
    from operational.cli.services import get_day_snapshot

    snap = get_day_snapshot(date.today())
    self.query_one("#kpi-sono", KPICard).update_value(f"{snap.sleep.duration_hours or 0:.1f}h")
    self.query_one("#kpi-pomo", KPICard).update_value(f"{snap.n_pomodoros}/{snap.pomodoros_meta or 0}")
    self.query_one("#kpi-energia", KPICard).update_value(f"{snap.energia or 0}/10")
    self.query_one("#kpi-foco", KPICard).update_value(f"{snap.foco or 0}/10")

    regime = get_current_regime()  # from services or core/policy_engine
    self.query_one("#regime-bar", RegimeBar).current = regime

    # Compute next step
    next_step = compute_next_step(snap)  # pure function in core/
    self.query_one("#next-step", Static).update(next_step)
```

Also, the `KPICard` widget should expose a `update_value()` method (instead of setting `.value` and hoping for refresh):

```python
class KPICard(Static):
    def update_value(self, value: str) -> None:
        self.value = value
        self.refresh()  # explicit
```

### 6.2 DailyFlowScreen

**Should do:** show the routines/time-blocks for the selected period (MANHA/TARDE/NOITE) for the selected date, with status indicators.

**Today does:** tabs work, but the time blocks are hardcoded in `_show_period()`. The `TimeBlockDisplay` widget receives a `label`/`start`/`end`/`status` directly. There is no date selector.

**Gap:** completely decoupled from `time_blocks` repo. Tabs and arrow keys work, but the content is fake.

**Fix:**
```python
def _show_period(self, period: str) -> None:
    from datetime import date
    from operational.cli.state import time_blocks

    today = date.today()
    blocks_for_period = [
        b for b in time_blocks.list()
        if b.start.date() == today and b.period.value == period
    ]
    # remove old TimeBlockDisplay widgets, add new ones with real data
    self.query(TimeBlockDisplay).remove()
    container = self.query_one("#period-content")
    for b in blocks_for_period:
        container.mount(TimeBlockDisplay(
            label=b.label, start=b.start.strftime("%H:%M"),
            end=b.end.strftime("%H:%M"),
            status=classify_status(b),  # OK/WARN/PEND
            period=period,
        ))
```

### 6.3 PomodoroTimerScreen

**Should do:** run a live pomodoro timer using the `core/pomodoro_machine.PomodoroMachine` FSM. Show current state, time remaining, next state.

**Today does:** a 102-line toy that hardcodes `_state = "IDLE"` and re-implements a 4-state FSM (`IDLE → WORK → BREAK → IDLE`) that has nothing to do with the real 8-state machine in `core/pomodoro_machine.py`. The "Skip Break" button sets `_state = "WORK"` (skips to work, not to long_break as a real Pomodoro would). The "Pause" button sets `_state = "BREAK"` (calls pause "break" — confusing).

**Gap:** doesn't use the real pomodoro machine, doesn't persist rounds, doesn't tick the timer (it just sits at 25:00 until you click).

**Fix:** wire to `core.pomodoro_machine.PomodoroMachine`:

```python
from operational.core.pomodoro_machine import PomodoroMachine, PomodoroEvent

class PomodoroTimerScreen(Screen):
    def on_mount(self) -> None:
        self._machine = PomodoroMachine.start_session(n_rounds=4, work_min=25, break_min=5)
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self._machine.advance(60)  # 1 second = 1s of game time
        self.query_one("#pomo-timer", Digits).update(
            f"{self._machine.minutes_remaining:02d}:{self._machine.seconds_remaining:02d}"
        )
        self.query_one("#state-label", Static).update(f"State: {self._machine.state.name}")
        # ... auto-persist round when machine.state transitions to COMPLETE
```

### 6.4 HabitsScreen

**Should do:** list all habits from `habits` repo, with current streak, best streak, Q_HE. Filter by category (`[f]`), sort by Q_HE.

**Today does:** hardcodes 4 habits. The `[a]`/`[e]`/`[d]`/`[f]` keybindings are declared but their `action_*` methods are missing — they would do nothing. The `on_mount` re-sets the same hardcoded values, calling `widget.refresh()` on each.

**Gap:** the action methods are unimplemented. The data is hardcoded.

**Fix:**
```python
def _refresh_data(self) -> None:
    from operational.cli.state import habits
    self.query(HabitStreakDisplay).remove()
    for h in habits.list():
        streak = compute_streak(h)  # in core/habit_engine
        self.mount(HabitStreakDisplay(
            name=h.name,
            current_streak=streak.current,
            best_streak=streak.best,
            q_he=compute_q_he(h, streak),  # in core/habit_engine
        ))

# Add the missing action methods:
def action_add_habit(self) -> None:
    self.push_screen("habit_create")  # new screen

def action_filter_habits(self) -> None:
    self.push_screen(FilterHabitsModal())
```

### 6.5 MetricsScreen

**Should do:** historical sparklines (sleep, energy, focus) for last 7d / 30d, selectable.

**Today does:** this is the best screen — uses `PlotextChart` correctly with `sparkline`, `bar_chart`, `dual_axis`. Period toggle works. **But** data is hardcoded module-level (`SLEEP_DATA_7D = [7.5, 8.0, ...]`).

**Gap:** data is not from the repo. The plotext wrapper is well-designed, but the screen is the only one that actually uses it.

**Fix:**
```python
def _refresh_data(self, period: str) -> None:
    from datetime import date, timedelta
    from operational.cli.state import sleep_records, journals

    days = 7 if period == "7d" else 30
    today = date.today()
    sleep_vals = [get_sleep_hours(today - timedelta(days=i)) for i in range(days)]
    energy_vals = [get_energy_level(today - timedelta(days=i)) for i in range(days)]
    focus_vals = [get_focus_level(today - timedelta(days=i)) for i in range(days)]

    self.query_one("#sleep-chart", PlotextChart).sparkline(
        sleep_vals, color=ChartColors.SLEEP["primary"], fill=True, ...
    )
    # ... etc
```

### 6.6 PolicyScreen

**Should do:** show current regime, last N decisions, hysteresis thresholds.

**Today does:** renders hardcoded regime, 3 fake decisions, and a hysteresis constant.

**Gap:** same — decoupled from data.

**Fix:** read from `policy_decisions` and `policy_setpoints` repos.

### 6.7 JournalScreen

**Should do:** searchable list of journal entries, with date/period filters.

**Today does:** 5 hardcoded entries, an `Input` for search (not wired to anything), 2 filter rows.

**Gap:** the search/filter is cosmetic. No action methods for `n` (new), `f` (filter).

**Fix:** implement `action_focus_search` (focus the input), `on_input_changed` (filter entries by substring), `action_new_entry` (push a new-entry modal).

### 6.8 HelpScreen (the one that works)

This is the best screen. `ModalScreen` overlay, sectioned keybinding reference, `Esc` to dismiss, button to close. **No changes needed.** Maybe add a `[?] Show this help` reference in every other screen's footer.

---

## 7. Command-by-command CLI critique

### 7.1 `pav home` (your entry point)

| Aspect | Status | Note |
|--------|--------|------|
| Visual layout | ✅ excellent | 3 grouped panels, header, footer |
| Dispatch logic | 🔴 broken | `ROOT` undefined, crashes on interactive choices |
| Back navigation | ⚠️ awkward | "Press [Enter] to voltar" after every command — extra keystroke |
| Submenus | ✅ works | Reports submenu `[D/S/E/V]` |
| Help | ❌ missing | No `?` to show what each option does |

**Recommended fixes:**

1. Fix the `ROOT` bug (see §8.1)
2. Replace the post-command `[Enter] to voltar` with an automatic back-after-2-seconds OR keep it but make it skippable with `q` (quit) or `m` (main menu)
3. Add an `?` option that shows expanded help
4. Show a context line above the menu: "Last command: `pav state show` succeeded (5 entities)"

### 7.2 `pav tui` (the TUI launcher)

| Aspect | Status | Note |
|--------|--------|------|
| Argument parsing | ✅ clean | `--screen`, `--data-file`, `--golden`, `--debug` |
| Async launch | ⚠️ uses `asyncio.run` | `PAVApp.run_async()` is the right API but `asyncio.run` blocks until exit — should be the standard pattern. OK. |
| Default screen | ✅ | "dashboard" |

**Recommended fixes:**
1. Add `--no-help` flag (skip help binding) for screenshot automation
2. Add `--mock q1`/`--mock burnout` (per DESIGN-SYSTEM.md §7.2)
3. Auto-load a sample dataset if state is empty (after `pav demo seed`)

### 7.3 `pav doctor`

| Aspect | Status | Note |
|--------|--------|------|
| Health check | ✅ works | 29/29 manual tests pass |
| JSON output | ✅ works | `--json` produces structured output |
| `python --version` etc. | ✅ | Reports interpreter, path, env |

**Recommended fixes:**
1. Add a "fix" mode: `pav doctor --fix` that auto-resolves common issues (missing dir, corrupt JSON, stale data)
2. Group checks by category: state integrity, environment, performance

### 7.4 `pav demo` (the demo data manager)

| Aspect | Status | Note |
|--------|--------|------|
| Subcommands | ✅ seed, clear, show, week, export_csv, import_csv, dataset | |
| Progress bar on import | ✅ | Uses `rich.progress.Progress` |
| `dataset` listing | ✅ | Shows OK/MISSING for each |

**Recommended fixes:**
1. Add `pav demo golden` (load golden dataset) and `pav demo synth` (load synthetic) as shortcuts
2. Add `pav demo random` (generate a single randomized day for visual testing)

### 7.5 Other commands

`routine`, `block`, `journal`, `habit`, `metric`, `policy`, `reflect`, `lunch`, `state`, `report` — all are thin Typer wrappers that delegate to `services.py` + repos. They follow the same pattern: `--json` flag, Rich spinner on long ops, plain text otherwise. The usability report shows 29/29 pass.

**Common improvement:** every command should print "✓ <command> done in 230ms" on success (Rich `console.print` with a green check). Currently the output stops at the data, with no success indicator. Helps new users confirm the command worked.

---

## 8. Concrete refactor plan + code samples

### 8.1 Fix the `ROOT` bug in `home_v2.py`

**Before (`apps/cli/src/operational/cli/home_v2.py:172-194`):**
```python
def _run_cmd(args: list[str]) -> None:
    deduped: list[str] = []
    for a in args:
        if not (deduped and deduped[-1] == a):
            deduped.append(a)
    args = deduped

    if _is_interactive(args):
        try:
            subprocess.run(
                ["uv", "run", "--directory", str(ROOT), "pav", *args],  # ← ROOT undefined
                check=False,
            )
        except Exception as e:
            console.print(f"[red]Error running {args[0]} {args[1] if len(args) > 1 else ''}: {e}[/red]")
        return
    ...
```

**After (3 options, pick one):**

**Option A — add a `ROOT` constant near the top:**
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
# __file__ = .../cli/home_v2.py
# parent x4 = .../apps/cli/src/operational/cli  → up to apps/cli
# adjust as needed

def _run_cmd(args: list[str]) -> None:
    if _is_interactive(args):
        subprocess.run(
            ["uv", "run", "--directory", str(ROOT), "pav", *args],
            check=False,
        )
        return
```

**Option B — skip the subprocess entirely (best option, removes the TTY problem):**

The reason for the subprocess was that `redirect_stdout` blocks `Prompt.ask`. But you can avoid the redirect for interactive commands by simply calling the command function directly and letting Typer raise. But Typer catches the function and rebuilds the parser... so this needs more work.

A simpler fix: detect interactive commands and call them via `os.system` (which preserves the TTY):

```python
import os
import sys

def _run_cmd(args: list[str]) -> None:
    deduped = [a for i, a in enumerate(args) if i == 0 or a != args[i-1]]
    if _is_interactive(deduped):
        # os.system preserves TTY; sys.executable is the current Python
        cmd = f'"{sys.executable}" -m operational.cli {" ".join(deduped)}'
        os.system(cmd)
        return
    # ... rest unchanged
```

**Option C — change `Prompt.ask` to `click.echo` + `input()` (loses Rich formatting):**
Not recommended. Stick with Option A or B.

**My recommendation:** Option A (minimal change, keeps the subprocess, but you need to verify the `ROOT` path resolves correctly when the app is installed vs run from source).

### 8.2 Fix the TUI screen stack leak

**Before (`apps/tui/src/operational/tui/app.py:83-102`):**
```python
def action_switch_dashboard(self) -> None:
    self.push_screen("dashboard")

def action_switch_daily_flow(self) -> None:
    self.push_screen("daily_flow")
# ... etc
```

**After:**
```python
def action_switch_dashboard(self) -> None:
    self.switch_screen("dashboard")  # pop + push, replaces top

def action_switch_daily_flow(self) -> None:
    self.switch_screen("daily_flow")
# ... etc
```

`switch_screen` was added in Textual 0.30 and is the standard API for "I want this screen to be the active one, replacing whatever is on top."

### 8.3 Wire TUI screens to real data (the P1 fix)

**Before (`apps/tui/src/operational/tui/screens/dashboard_screen.py:54-74`):**
```python
def compose(self) -> ComposeResult:
    yield Header()
    yield KPICard(label="Sono", value="8.0h", delta="+0.5h 7d", icon="😴", id="kpi-sono")
    yield KPICard(label="Pomodoros", value="12", delta="+3 today", icon="🍅", id="kpi-pomo")
    # ...
    yield Static("Próximo: Deep Work Session (14:00-16:00)", id="next-step")
    yield Footer()

def on_mount(self) -> None:
    self.query_one("#kpi-sono", KPICard).value = "8.0h"  # duplicate
    self.query_one("#kpi-sono", KPICard).delta = "+0.5h 7d"  # duplicate
    # ...
```

**After:**
```python
from datetime import date
from operational.cli.services import get_day_snapshot
from operational.core.policy_engine import get_current_regime
from operational.core.next_step import compute_next_step

def compose(self) -> ComposeResult:
    yield Header()
    yield KPICard(id="kpi-sono", label="Sono", icon="😴")
    yield KPICard(id="kpi-pomo", label="Pomodoros", icon="🍅")
    yield KPICard(id="kpi-energia", label="Energia", icon="⚡")
    yield KPICard(id="kpi-foco", label="Foco", icon="🎯")
    yield RegimeBar(id="regime-bar")
    yield PomodoroGrid(id="pomo-grid")
    yield Static(id="next-step")
    yield Footer()

def on_mount(self) -> None:
    self._refresh()
    self.set_interval(2.0, self._refresh)  # auto-update

def _refresh(self) -> None:
    snap = get_day_snapshot(date.today())
    self.query_one("#kpi-sono", KPICard).update(
        value=f"{snap.sleep.duration_hours or 0:.1f}h",
        delta=_compute_sleep_delta(snap),
    )
    self.query_one("#kpi-pomo", KPICard).update(
        value=f"{snap.n_pomodoros}/{snap.pomodoros_meta or 0}",
        delta="",
    )
    self.query_one("#kpi-energia", KPICard).update(
        value=f"{snap.energia or 0}/10",
        delta=_compute_energy_delta(snap),
    )
    self.query_one("#kpi-foco", KPICard).update(
        value=f"{snap.foco or 0}/10",
        delta="",
    )
    self.query_one("#regime-bar", RegimeBar).current = get_current_regime()
    self.query_one("#next-step", Static).update(compute_next_step(snap))
```

You also need to add `update()` methods to `KPICard` and `RegimeBar` that set multiple attributes and call `refresh()` atomically.

### 8.4 De-duplicate color literals

**Before (`apps/tui/src/operational/tui/widgets/kpi_card.py:7-12`):**
```python
_CORAL = "#ff6b6b"
_TEAL = "#4ecdc4"
_TEXT = "#E0E0E0"
_TEXT_MUTED = "#A9A9A9"
```

**After:** import from `theme.py`:
```python
from operational.tui.theme import TUI_COLORS
# TUI_COLORS already defines: primary, success, warning, danger, info, muted, accent, inverse

# Use them in render():
def render(self) -> str:
    icon_markup = f"[{TUI_COLORS['info']}]{self.icon}[/{TUI_COLORS['info']}] " if self.icon else ""
    label_markup = f"[white]{self.label:<12}[/white]"
    value_markup = f"[bold white]{self.value}[/bold white]"
    delta_markup = f"[{TUI_COLORS['muted']}]{self.delta}[/{TUI_COLORS['muted']}]" if self.delta else ""
    return f"{icon_markup}{label_markup} {value_markup} {delta_markup}"
```

Or, even better, use Textual CSS variables (defined in `theme.py`):
```css
/* in kpi_card.py DEFAULT_CSS */
KPICard {
    color: $text;
    background: $surface;
    border: solid $border;
}
```

```python
# in render(), use Textual markup that references the theme
def render(self) -> str:
    return f"{self.icon} {self.label:<12} [bold]{self.value}[/bold] [dim]{self.delta}[/dim]"
```

### 8.5 Add a command palette to the TUI

**New file: `apps/tui/src/operational/tui/screens/command_palette.py`**
```python
"""Command palette — `:` key. Fuzzy-search and run any TUI action."""
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

COMMANDS: list[tuple[str, str, str]] = [
    # (key, label, action_name)
    ("g dashboard", "Go to Dashboard", "switch_dashboard"),
    ("g daily",     "Go to Daily Flow", "switch_daily_flow"),
    ("g pomo",      "Go to Pomodoro",   "switch_pomodoro_timer"),
    ("g habits",    "Go to Habits",     "switch_habits"),
    ("g metrics",   "Go to Metrics",    "switch_metrics"),
    ("g policy",    "Go to Policy",     "switch_policy"),
    ("g journal",   "Go to Journal",    "switch_journal"),
    ("?",           "Show Help",        "show_help"),
    ("q",           "Quit",             "quit"),
]

class CommandPaletteScreen(ModalScreen[str | None]):
    BINDINGS: ClassVar = [Binding("escape", "dismiss(None)", "Cancel", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Input(placeholder="Type a command (e.g. 'g daily', '?', 'q')", id="palette-input")
            yield ListView(id="palette-list")

    def on_mount(self) -> None:
        self._refresh_list("")
        self.query_one("#palette-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_list(event.value)

    def _refresh_list(self, query: str) -> None:
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for key, label, _action in COMMANDS:
            if query.lower() in key or query.lower() in label.lower():
                lv.append(ListItem(Label(f"{key:20}  {label}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None:
            self.dismiss(COMMANDS[idx][2])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # exact match
        for key, _label, action in COMMANDS:
            if key == event.value:
                self.dismiss(action)
                return
        self.dismiss(None)
```

**Add to `PAVApp`:**
```python
# in BINDINGS:
Binding("colon", "command_palette", "Command", show=False),

# new method:
def action_command_palette(self) -> None:
    def on_selected(action: str | None) -> None:
        if action and action != "quit":
            self.run_action(action)
        elif action == "quit":
            self.exit()
    self.push_screen(CommandPaletteScreen(), on_selected)
```

### 8.6 Use Textual `reactive` to auto-refresh widgets

**Before (`KPICard`):**
```python
class KPICard(Static):
    def __init__(self, label, value, delta="", icon="", severity="primary", **kwargs):
        super().__init__(**kwargs)
        self.value = value  # plain attribute

    def render(self) -> str:
        return f"... {self.value} ..."
```

**After:**
```python
from textual.reactive import reactive

class KPICard(Static):
    value = reactive("")  # Textual watches this
    delta = reactive("")

    def watch_value(self, old: str, new: str) -> None:
        self.refresh()  # called automatically when value changes

    def watch_delta(self, old: str, new: str) -> None:
        self.refresh()
```

Now `card.value = "8.0h"` automatically triggers a refresh, no manual `card.refresh()` needed.

---

## 9. Implementation roadmap

I split the work into 5 sprints, ordered by impact and dependency.

### Sprint 1 — Critical bug fixes (1 day, ship immediately)

- [ ] Fix `ROOT` undefined in `home_v2.py:187` (§8.1)
- [ ] Change `action_switch_*` to use `switch_screen` (§8.2)
- [ ] Update the stale project `CLAUDE.md` to reflect uv workspace layout

**Why first:** these are crashers and the work blocks every other sprint.

### Sprint 2 — Wire TUI to real data (3 days)

- [ ] Add `update()` method to `KPICard`, `RegimeBar`, `PomodoroGrid` (§8.3)
- [ ] Add `compute_next_step(snap)` to `core/next_step.py` (pure function)
- [ ] Make `DashboardScreen.on_mount` read from `get_day_snapshot()` and call `set_interval(2.0, refresh)`
- [ ] Same for `DailyFlowScreen`, `HabitsScreen`, `MetricsScreen`, `PolicyScreen`, `JournalScreen`
- [ ] Wire `PomodoroTimerScreen` to `core.pomodoro_machine.PomodoroMachine`

**Why second:** without this, the TUI is a design demo. With it, it's a real app.

### Sprint 3 — Design system hardening (2 days)

- [ ] De-duplicate color literals in widgets (§8.4)
- [ ] Add `update_*` methods and `reactive` attributes to all widgets
- [ ] Add `light` theme variant to `get_tui_theme()` (auto-detect via `os.environ.get("PAV_THEME")`)
- [ ] Add `pav doctor --fix` mode (auto-resolve common issues)
- [ ] Add `pav demo golden` / `pav demo synth` shortcuts

### Sprint 4 — Power-user features (3 days)

- [ ] Add command palette (`: ` key) to TUI (§8.5)
- [ ] Add `--mock q1|q3|burnout|empty` flag to report commands
- [ ] Add `pav state show --watch` (live refresh every 5s) using `rich.live.Live`
- [ ] Add per-entity CRUD screens to TUI (habit_create, journal_create, etc.) — or decide TUI is read-only and document that

### Sprint 5 — Async I/O for long ops (1 day)

- [ ] Make `seed_demo_data` async (offload to `ThreadPoolExecutor`)
- [ ] Make `import_csv` async
- [ ] Replace `console.status` (sync animation over sync work) with `Progress` + `asyncio`

---

## Appendix A — what to update in docs/

After the sprints above, update:

| Doc | Section | Update |
|-----|---------|--------|
| `CLAUDE.md` (project root) | full | Reflect uv workspace (`apps/cli/`, `apps/tui/`, `packages/core/`) and the 12 CLI subcommands + 7 TUI screens |
| `docs/architecture/01-MVC-LAYERS.md` | full | Add the L3 `reactive` widget pattern |
| `docs/tui/05-HOME-MENU.md` | full | Document the `ROOT` fix and the menu dispatch table |
| `docs/tui/06-INTERACTIVITY.md` | add | Add command palette section |
| `docs/design-system/DESIGN-SYSTEM.md` | §4 (Component Refactor v2) | Mark items that are implemented vs spec-only (KPI Card v2 ✅, Regime Bar ✅, Pomodoros Grid ✅, Cartesian Plane ❌, Next Step v2 ❌) |
| `docs/ux/05-telas/SCR-001-home-menu.md` | full | The current implementation matches this spec, but doesn't mention the `ROOT` workaround |
| `docs/ux/01-inventario/01-telas-inventario.md` | full | Mark 8 missing screens (lunch, reflect, block-create, etc.) as "future / not in TUI" |

---

*End of audit. Total findings: 23. Critical (P0): 2. Important (P1): 12. Nice-to-have (P2/P3): 9.*
