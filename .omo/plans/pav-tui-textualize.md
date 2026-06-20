# PAV-OS TUI — Textual + Plotext Edition

## TL;DR

> **Quick Summary**: Build a fully featured terminal TUI for the PAV productivity system using **Textual** (terminal UI framework) + **Plotext** (terminal charts), integrating with the existing operational codebase (2518 tests, mypy strict).
>
> **Library Corrections** (verified from source):
> - Textual pip package: `textual` (NOT `textualize` — package name is `textual`)
> - Install via: `pip install textual textual-dev`
> - Textual has built-in `Sparkline` widget (use for simple sparklines)
> - plotext integration: `plotext.plot()` → capture to string → display in `Static` widget
> - Textual lifecycle: `on_mount()` (not `on_ready()`), `set_interval()` for timers
>
> **Deliverables**:
> - New `pav tui` command launching a 7-screen Textualize application
> - plotext charts embedded in Metrics, Habits, and Dashboard screens
> - Reused design tokens from `ui/tokens.py` (SEVERITY, REGIME, QUADRANT, Glyph)
> - Reused entities and core logic from `src/operational/`
> - Backward compatible with existing Rich-based CLI
>
> **Estimated Effort**: Large (3-4 weeks)
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: T1 → T3 → T5 → T7 → T10 → T11 → T12 → F1-F4

---

## Context

### Original Request
User wants to build a **complete TUI** for the PAV (Produtividade Algorítmica Visual) system using **textual + plotext**, based on the existing `life-ops/operational/` codebase.

### Interview Summary
**Key Discussions**:
- Existing Rich UI in `ui/components_v2.py` (1017 lines) + `ui/v2_renderers.py` (326 lines) should be leveraged
- 2518 tests passing, mypy strict, Python 3.11+, Pydantic v2 strict mode
- **textual** and **plotext** are NOT yet installed — need to add as dependencies
- 7 TUI screens needed: Dashboard, Daily Flow, Pomodoro Timer, Habits, Metrics, Policy, Journal
- Design tokens from `ui/tokens.py` must be reused (SEVERITY, REGIME, QUADRANT, Glyph)
- Backward compatibility with existing Rich-based CLI commands

**Research Findings** (from GitHub source):
- **textual** (36.3k stars): pip package `textual`, app extends `textual.app.App`, lifecycle `on_mount()`, widgets include Digits, Sparkline, DataTable, Log, RichLog, ProgressBar, Tabs, Tree, etc., CSS styling, built-in themes, `set_interval()` for timers, DevTools via `textual-dev`
- **plotext** (2.2k stars): pip package `plotext`, plots: scatter, line, bar, histogram, datetime/candlestick, error bars, confusion matrices; no dependencies (optional for image/video); output as text string or HTML; CLI tool included
- `src/operational/ui/` — Rich components (components_v2.py, v2_renderers.py, tokens.py)
- `src/operational/cli/home_v2.py` — interactive Rich menu (312 lines)
- `src/operational/entities/` — 12 Pydantic modules (routine, ritual, transition, pomodoro, habit, journal, metric, policy, consolidation, time_block, ajuste_fino, v3)
- `src/operational/core/` — 15 business logic modules (services, sleep_calculator, pomodoro_machine, policy_engine, scenario_classifier, time_validator, habit_engine, consolidator, etc.)
- `src/operational/persistence/` — SQLite + InMemory repositories
- `src/operational/enums.py` — Period, RitualType, RoutineType, HabitCategory, PolicyState, TipoDia, etc.
- `src/operational/constants.py` — PAVConstants (22 frozen fields)

---

## Work Objectives

### Core Objective
Build a production-grade **Textual** TUI with 7 screens + plotext charts, fully integrated with the existing operational codebase, running `pav tui` alongside the existing Rich-based CLI.

### Concrete Deliverables
- `src/operational/tui/` — New TUI package with 7 screens
- `src/operational/tui/app.py` — Textualize Application (7 screens)
- `src/operational/tui/screens/` — 7 individual screen modules
- `src/operational/tui/widgets/` — Reusable TUI widgets (KPI card, regime bar, pomodoro grid, sparkline chart)
- `src/operational/tui/charts.py` — plotext chart builders
- `src/operational/tui/theme.py` — Textual theme mapping from tokens.py
- `src/operational/tui/navigation.py` — Screen routing and state
- Updated `pyproject.toml` — Add textual + plotext dependencies
- Updated `src/operational/cli/app.py` — Add `tui` subcommand

### Definition of Done
- [ ] `pav tui` launches TUI without errors
- [ ] All 7 screens navigable via keyboard
- [ ] plotext charts render in Metrics/Habits/Dashboard screens
- [ ] Existing entity data loads from SQLite repository
- [ ] 2518 original tests still pass
- [ ] mypy strict passes on new TUI code

### Must Have
- 7 functional TUI screens (Dashboard, Daily Flow, Pomodoro Timer, Habits, Metrics, Policy, Journal)
- plotext sparkline + bar charts in at least 3 screens
- Keyboard navigation (arrows + Enter + Escape)
- Mouse support toggleable
- Regime bar (PUSH/MAINTAIN/REDUCE/RECOVER) on Dashboard
- Pomodoro timer with state machine visualization
- Q_HE habits view with streak history
- Sleep + energy metrics charts
- Policy FSM history view
- Journal entry list with search

### Must NOT Have
- No cloud/network features
- No LLM/NLP integration
- No multi-user authentication
- No deletion of existing Rich UI (backward compatible)
- No changes to existing entity schemas
- No breaking changes to existing CLI commands

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: Tests-after (add TUI-specific tests after implementation)
- **Framework**: pytest (existing)
- **Agent-Executed QA**: Playwright NOT needed (TUI — use tmux/interactive_bash for verification)

### QA Policy
Every task includes agent-executed QA scenarios verified via:
- **TUI verification**: `tmux` + `script` replay for terminal interaction verification
- **Import verification**: `python -c "from operational.tui import app"` for import sanity
- **pyproject.toml check**: `toml lint` for dependency validity
- **Screen navigation**: Keybinding smoke tests via tmux send-keys

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — scaffolding + deps):
├── Task 1: Add textual + plotext to pyproject.toml [quick]
├── Task 2: Create tui/ package structure + __init__ [quick]
├── Task 3: Create theme.py (Textual theme from tokens.py) [quick]
└── Task 4: Create navigation.py (Screen routing + state) [quick]

Wave 2 (Core widgets — parallel build):
├── Task 5: Create widgets/kpi_card.py [quick]
├── Task 6: Create widgets/regime_bar.py [quick]
├── Task 7: Create widgets/pomodoro_grid.py [quick]
├── Task 8: Create widgets/sparkline_chart.py (plotext) [quick]
├── Task 9: Create widgets/time_block.py [quick]
└── Task 10: Create widgets/habit_streak.py [quick]

Wave 3 (Screens — parallel build):
├── Task 11: Create screens/dashboard_screen.py [visual-engineering]
├── Task 12: Create screens/daily_flow_screen.py [visual-engineering]
├── Task 13: Create screens/pomodoro_timer_screen.py [visual-engineering]
├── Task 14: Create screens/habits_screen.py [visual-engineering]
├── Task 15: Create screens/metrics_screen.py [visual-engineering]
├── Task 16: Create screens/policy_screen.py [visual-engineering]
└── Task 17: Create screens/journal_screen.py [visual-engineering]

Wave 4 (App integration + CLI):
├── Task 18: Create app.py (Textualize App + screen registration) [visual-engineering]
├── Task 19: Add `tui` subcommand to cli/app.py [quick]
├── Task 20: Create charts.py (plotext chart builders) [quick]
└── Task 21: Add TUI tests to tests/ [quick]

Wave FINAL (4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: T1 → T3 → T5 → T11 → T18 → T19 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 6 (Wave 2 & 3)
```

### Dependency Matrix

- **T1**: - - T2, T3, T4
- **T2**: T1 - T3, T4
- **T3**: T1 T2 - T4
- **T4**: T1 T2 T3 -
- **T5**: T4 - T6, T7, T8, T9, T10
- **T6**: T4 T5 - T7, T8, T9, T10
- **T7**: T4 T5 T6 - T8, T9, T10
- **T8**: T4 T5 T6 T7 - T9, T10
- **T9**: T4 T5 T6 T7 T8 - T10
- **T10**: T4 T5 T6 T7 T8 T9 -
- **T11**: T5 T6 T7 T8 T9 T10 - T18
- **T12**: T5 T6 T7 T8 T9 T10 T11 - T18
- **T13**: T5 T6 T7 T8 T9 T10 T11 T12 - T18
- **T14**: T5 T6 T7 T8 T9 T10 T11 T12 T13 - T18
- **T15**: T5 T6 T7 T8 T9 T10 T11 T12 T13 T14 - T18
- **T16**: T5 T6 T7 T8 T9 T10 T11 T12 T13 T14 T15 - T18
- **T17**: T5 T6 T7 T8 T9 T10 T11 T12 T13 T14 T15 T16 - T18
- **T18**: T11 T12 T13 T14 T15 T16 T17 - T19, T20, T21
- **T19**: T18 - T21
- **T20**: T18 - T21
- **T21**: T18 T19 T20 - F1, F2, F3, F4

### Agent Dispatch Summary

- **1**: **4** - T1 → `quick`, T2 → `quick`, T3 → `quick`, T4 → `quick`
- **2**: **6** - T5 → `quick`, T6 → `quick`, T7 → `quick`, T8 → `quick`, T9 → `quick`, T10 → `quick`
- **3**: **7** - T11 → `visual-engineering`, T12 → `visual-engineering`, T13 → `visual-engineering`, T14 → `visual-engineering`, T15 → `visual-engineering`, T16 → `visual-engineering`, T17 → `visual-engineering`
- **4**: **4** - T18 → `visual-engineering`, T19 → `quick`, T20 → `quick`, T21 → `quick`
- **FINAL**: **4** - F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Add textual + plotext to pyproject.toml

  **What to do**:
  - Add to `[project.dependencies]` in `pyproject.toml`:
    - `textual>=0.8,<1.0` — the TUI framework (pip package name is `textual`, NOT `textual`)
    - `textual-dev>=0.8,<1.0` — DevTools for debugging
    - `plotext>=4.2,<5.0` — terminal plotting library
  - Run `poetry lock` to update lockfile
  - Verify with `poetry show textual` and `poetry show plotext`

  **Must NOT do**:
  - Do NOT remove existing dependencies
  - Do NOT change existing version constraints
  - Do NOT use `textual` as package name (correct name is `textual`)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple dependency addition, no complex logic
  - **Skills**: []
    - No specialized skills needed for dependency addition

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 2, 3, 4 (need package available)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `life-ops/operational/pyproject.toml:28-34` — existing dependencies section to extend
  - `https://pypi.org/project/textual/` — textual package (verified: textual, NOT textual)
  - `https://pypi.org/project/plotext/` — plotext package
  - `https://github.com/Textualize/textual` — 36.3k stars, main TUI framework

  **Acceptance Criteria**:
  - [ ] `textual` and `plotext` present in `poetry.lock`
  - [ ] `poetry show textual` shows package without error
  - [ ] `poetry show plotext` shows package without error
  - [ ] `python -c "import textual; print(textual.__version__)"` works
  - [ ] `python -c "import plotext; print(plotext.__version__)"` works

  **QA Scenarios**:

  ```
  Scenario: Dependencies install correctly
    Tool: Bash
    Preconditions: Clean poetry environment
    Steps:
      1. cd life-ops/operational && poetry lock --no-update
      2. poetry install
      3. poetry show textual
      4. poetry show plotext
      5. python -c "import textual; print(textual.__version__)"
      6. python -c "import plotext; print(plotext.__version__)"
    Expected Result: Both packages install and import correctly with version info
    Failure Indicators: Package not found error, version conflict, import error
    Evidence: .omo/evidence/task-1-deps-install.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add textual + plotext dependencies`
  - Files: `pyproject.toml, poetry.lock`

- [x] 2. Create tui/ package structure + __init__

  **What to do**:
  - Create `src/operational/tui/` directory
  - Create `src/operational/tui/__init__.py` with:
    - `__version__` from parent
    - Public exports: `app`
  - Create `src/operational/tui/screens/` directory with `__init__.py`
  - Create `src/operational/tui/widgets/` directory with `__init__.py`
  - Create `src/operational/tui/charts.py` (empty, plotext chart builders)
  - Create `src/operational/tui/theme.py` (empty, Textual theme mapping)
  - Create `src/operational/tui/navigation.py` (empty, screen routing)

  **Must NOT do**:
  - Do NOT import textual yet (version not confirmed)
  - Do NOT create any screen implementations yet

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure scaffolding, file creation only
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Tasks 5-17 (all screens and widgets)
  - **Blocked By**: Task 1 (need package to exist for imports)

  **References**:
  - `src/operational/__init__.py` — parent package pattern to follow
  - `src/operational/cli/__init__.py` — CLI package pattern

  **Acceptance Criteria**:
  - [ ] `src/operational/tui/` directory exists
  - [ ] `src/operational/tui/__init__.py` exists and imports without error
  - [ ] `src/operational/tui/screens/` directory exists
  - [ ] `src/operational/tui/widgets/` directory exists
  - [ ] `python -c "from operational.tui import app"` works (may fail if app not built yet, but import should work)

  **QA Scenarios**:

  ```
  Scenario: Package structure created correctly
    Tool: Bash
    Preconditions: None
    Steps:
      1. ls -la src/operational/tui/
      2. ls -la src/operational/tui/screens/
      3. ls -la src/operational/tui/widgets/
      4. python -c "from operational.tui import app; print('import ok')"
    Expected Result: All directories exist, import succeeds
    Failure Indicators: Directory not found, import error
    Evidence: .omo/evidence/task-2-structure.log
  ```

  **Commit**: YES
  - Message: `feat(tui): scaffold tui package structure`
  - Files: `src/operational/tui/`

- [x] 3. Create theme.py (Textual theme from tokens.py)

  **What to do**:
  - Create `src/operational/tui/theme.py` with Textual Theme mapping from `ui/tokens.py`:
    - Map `SEVERITY` colors to Textualive color names
    - Map `REGIME` colors (PUSH=bright_green, MAINTAIN=dodger_blue1, REDUCE=yellow, RECOVER=bold red)
    - Map `QUADRANT` colors
    - Create `get_tui_theme()` function returning `Theme`
    - Create `TUI_COLORS` dict mapping PAV severity keys to textual CSS colors
  - Keep existing `ui/tokens.py` unchanged (source of truth)

  **Must NOT do**:
  - Do NOT modify `ui/tokens.py`
  - Do NOT introduce new color values not in tokens.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mapping file, straightforward data transformation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Tasks 5-17 (all screens use theme)
  - **Blocked By**: Task 2 (package must exist)

  **References**:
  - `src/operational/ui/tokens.py:18-27` — SEVERITY palette
  - `src/operational/ui/tokens.py:56-61` — REGIME specs
  - `src/operational/ui/tokens.py:76-81` — QUADRANT specs
  - `textual.dev/docs/reference/themes/` — Textual Theme API (librarian)

  **Acceptance Criteria**:
  - [ ] `theme.py` maps all SEVERITY keys to textual CSS color strings
  - [ ] `theme.py` maps all REGIME keys with correct colors
  - [ ] `get_tui_theme()` returns a valid `Theme` object
  - [ ] `python -c "from operational.tui.theme import get_tui_theme; t = get_tui_theme(); print('ok')"` works

  **QA Scenarios**:

  ```
  Scenario: Theme mapping from tokens works
    Tool: Bash
    Preconditions: Package structure exists
    Steps:
      1. python -c "from operational.tui.theme import get_tui_theme, TUI_COLORS; t = get_tui_theme(); print(list(TUI_COLORS.keys()))"
      2. python -c "from operational.tui.theme import get_tui_theme; t = get_tui_theme(); print(t.name)"
    Expected Result: TUI_COLORS has 8 keys (primary, success, warning, danger, info, muted, accent, inverse), theme has a name
    Failure Indicators: Import error, missing keys
    Evidence: .omo/evidence/task-3-theme.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add theme mapping from tokens.py`
  - Files: `src/operational/tui/theme.py`

- [x] 4. Create navigation.py (Screen routing + state)

  **What to do**:
  - Create `src/operational/tui/navigation.py`:
    - Define `ScreenKind` enum (DASHBOARD, DAILY_FLOW, POMODORO_TIMER, HABITS, METRICS, POLICY, JOURNAL)
    - Create `TUIState` class with reactive fields:
      - `current_screen: ScreenKind`
      - `selected_date: date`
      - `current_period: Period | None`
      - `pomodoro_state: PomodoroState | None`
      - `regime: PolicyState`
    - Create `screen_registry` dict mapping ScreenKind to screen classes
    - Create `navigate_to(screen: ScreenKind)` function
    - Create `get_state()` / `set_state()` functions

  **Must NOT do**:
  - Do NOT implement screens here (just routing)
  - Do NOT import from textual directly (use TYPE_CHECKING pattern)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: State management + routing, pure Python
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Tasks 5-17 (all screens use navigation)
  - **Blocked By**: Task 2 (package must exist)

  **References**:
  - `src/operational/enums.py` — Period, PolicyState enums to use
  - `src/operational/entities/pomodoro.py` — PomodoroState enum
  - `textual.dev/docs/reference/api/navigation/` — Textual navigation patterns (librarian)

  **Acceptance Criteria**:
  - [ ] `ScreenKind` enum has all 7 screen variants
  - [ ] `TUIState` is a proper state container
  - [ ] `screen_registry` maps all ScreenKind values
  - [ ] `python -c "from operational.tui.navigation import ScreenKind, TUIState, screen_registry; print(len(screen_registry))"` shows 7

  **QA Scenarios**:

  ```
  Scenario: Navigation state works
    Tool: Bash
    Preconditions: Package structure exists
    Steps:
      1. python -c "from operational.tui.navigation import ScreenKind, TUIState, screen_registry; s = TUIState(); print(s.current_screen)"
      2. python -c "from operational.tui.navigation import ScreenKind, TUIState; s = TUIState(); s.current_screen = ScreenKind.DASHBOARD; print(s.current_screen)"
    Expected Result: State initializes with DASHBOARD, updates correctly
    Failure Indicators: Import error, state not updating
    Evidence: .omo/evidence/task-4-nav.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add navigation state management`
  - Files: `src/operational/tui/navigation.py`

- [x] 5. Create widgets/kpi_card.py

  **What to do**:
  - Create `src/operational/tui/widgets/kpi_card.py`:
    - `KPICard` widget class extending `textual.widget.Widget`
    - Display: icon + label + value + delta (1-line format)
    - Map severity colors from `theme.TUI_COLORS`
    - Use Glyph icons from `ui.tokens.Glyph`
    - Support reactive `value`, `delta`, `severity` fields
  - Follow wireframe from `ui/components_v2.py:kpi_v2`:
    ```
    ┌──────────────────────────┐
    │ 😴 Sono       8.0h  🟢  │
    │              +0.5h 7d   │
    └──────────────────────────┘
    ```

  **Must NOT do**:
  - Do NOT use Rich components (use Textual widgets only)
  - Do NOT hardcode colors (use theme.TUI_COLORS)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple widget, straightforward Rich→Textual port
  - **Skills**: [`textual` skill if available]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 9, 10)
  - **Blocks**: Tasks 11-17 (screens use widgets)
  - **Blocked By**: Task 4 (navigation state needed)

  **References**:
  - `src/operational/ui/components_v2.py:76-107` — kpi_v2 wireframe to port
  - `src/operational/ui/tokens.py:119-151` — Glyph class
  - `src/operational/tui/theme.py` — TUI_COLORS mapping

  **Acceptance Criteria**:
  - [ ] `KPICard` widget renders with icon + label + value + delta
  - [ ] Severity coloring works (success/warning/danger)
  - [ ] Reactive updates work when value changes

  **QA Scenarios**:

  ```
  Scenario: KPICard widget renders correctly
    Tool: Bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.widgets.kpi_card import KPICard; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-5-kpi.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add KPICard widget`
  - Files: `src/operational/tui/widgets/kpi_card.py`

- [x] 6. Create widgets/regime_bar.py

  **What to do**:
  - Create `src/operational/tui/widgets/regime_bar.py`:
    - `RegimeBar` widget showing PUSH → MAINTAIN → REDUCE → RECOVER states
    - Current regime highlighted with glyph marker (▲ ◆ ▼ ✗)
    - History dots showing days in each regime
    - Map from `REGIME` dict in `ui/tokens.py`
  - Follow wireframe from `ui/components_v2.py:regime_bar`:
    ```
            PUSH    MAINTAIN   REDUCE   RECOVER
             ▲◆      ◇◇◇        ◇◇       ◇◇◇
            today   3 dias    2 dias   2 dias
    ```

  **Must NOT do**:
  - Do NOT use Rich Box/Table (use Textual layouts)
  - Do NOT hardcode regime colors

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple widget, straightforward port
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7, 8, 9, 10)
  - **Blocks**: Tasks 11-17
  - **Blocked By**: Task 4

  **References**:
  - `src/operational/ui/components_v2.py:325-354` — regime_bar wireframe
  - `src/operational/ui/tokens.py:56-61` — REGIME dict
  - `src/operational/tui/theme.py` — TUI_COLORS

  **Acceptance Criteria**:
  - [ ] 4 regime states displayed horizontally
  - [ ] Current regime highlighted with colored glyph
  - [ ] History dots shown per regime

  **QA Scenarios**:

  ```
  Scenario: RegimeBar renders correctly
    Tool: Bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.widgets.regime_bar import RegimeBar; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-6-regime.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add RegimeBar widget`
  - Files: `src/operational/tui/widgets/regime_bar.py`

- [x] 7. Create widgets/pomodoro_grid.py

  **What to do**:
  - Create `src/operational/tui/widgets/pomodoro_grid.py`:
    - `PomodoroGrid` widget showing 3 sessions × 4 rounds
    - Each round as a cell: ▣ (done), ▢ (skip), ▤ (partial)
    - Session label (S1 manha, S2 tarde, S3 noite)
    - Focus score per session (⭐ X/10)
    - Percentage complete per session
  - Follow wireframe from `ui/components_v2.py:pomodoros_v2`:
    ```
    S1 manha  ▣ ▣ ▣ ▢  75%   ⭐ 8/10
    S2 tarde  ▣ ▣ ▢ ▢  50%   ⭐ 6/10
    S3 noite  ▢ ▢ ▢ ▢   0%   ⭐ -
    ```

  **Must NOT do**:
  - Do NOT use Rich Table (use Textual Grid layout)
  - Do NOT hardcode Glyph values

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple widget, grid layout
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 8, 9, 10)
  - **Blocks**: Tasks 11-17
  - **Blocked By**: Task 4

  **References**:
  - `src/operational/ui/components_v2.py:280-318` — pomodoros_v2 wireframe
  - `src/operational/ui/tokens.py:122-124` — POMO_DONE, POMO_SKIP, POMO_PARTIAL glyphs

  **Acceptance Criteria**:
  - [ ] 3 sessions displayed with 4 rounds each
  - [ ] Glyph cells show correct state (done/skip/partial)
  - [ ] Focus score displayed per session

  **QA Scenarios**:

  ```
  Scenario: PomodoroGrid renders correctly
    Tool: Bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.widgets.pomodoro_grid import PomodoroGrid; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-7-pomo.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add PomodoroGrid widget`
  - Files: `src/operational/tui/widgets/pomodoro_grid.py`

- [x] 8. Create widgets/sparkline_chart.py (plotext + textual Static)

  **What to do**:
  - Create `src/operational/tui/widgets/sparkline_chart.py`:
    - `PlotextChart` widget — wraps plotext output in `textual.widgets.Static`
    - Integration pattern: `plotext.plot()` → `plotext.savefig()` to string buffer → `Static.update()` with text
    - `plotext.disable_terminal_colors()` for clean output in Static widget
    - For simple sparklines: prefer `textual.widgets.Sparkline` (built-in) over plotext
    - For complex charts (bar, scatter, candlestick, heatmap): use plotext → Static
  - Key plotext functions for PAV:
    - `plotext.plot(x, y, style)` — main scatter/line plot
    - `plotext.bar(category, values)` — bar charts
    - `plotext.scatter(x, y)` — scatter plots (for Q_HE correlation)
    - `plotext.sparkline(values)` — sparkline (no axes)
    - `plotext.heatmap(data)` — for regime matrix visualization
  - Map colors from `TUI_COLORS` via plotext color codes
  - Use `io.StringIO` to capture plotext output without files

  **Must NOT do**:
  - Do NOT use matplotlib (use plotext only)
  - Do NOT generate actual image files (use StringIO buffer)
  - Do NOT use `textual` as import name (correct: `textual`)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Wrapper widget, plotext API is simple
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7, 9, 10)
  - **Blocks**: Tasks 11-17
  - **Blocked By**: Task 4

  **References**:
  - `src/operational/ui/components_v2.py:361-381` — sparkline_v2 wireframe
  - `https://github.com/piccolomo/plotext` — plotext GitHub (2.2k stars, no deps)
  - `src/operational/tui/theme.py` — TUI_COLORS
  - `textual.widgets.Sparkline` — Textual built-in sparkline (for simple cases)
  - `textual.widgets.Static` — container for plotext output

  **Acceptance Criteria**:
  - [ ] `PlotextChart` widget embeds plotext output in textual Static
  - [ ] `plotext.bar()` produces bar chart output
  - [ ] `plotext.scatter()` produces scatter plot output
  - [ ] Colors mapped from TUI_COLORS
  - [ ] No file I/O (all StringIO buffer capture)

  **QA Scenarios**:

  ```
  Scenario: PlotextChart produces plotext output in textual
    Tool: Bash
    Preconditions: textual and plotext installed
    Steps:
      1. python -c "
import plotext as px
import io
px.disable_terminal_colors()
px.plot([1,2,3,4,5], [2,4,6,8,10])
buf = io.StringIO()
px.savefig(buf)
print(buf.getvalue()[:200])
"
    Expected Result: Text-based chart output (first 200 chars)
    Failure Indicators: Import error, plotext error
    Evidence: .omo/evidence/task-8-plotext.log

  Scenario: Textual Sparkline widget works for simple sparklines
    Tool: Bash
    Preconditions: textual installed
    Steps:
      1. python -c "from textual.widgets import Sparkline; print('Sparkline import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-8-sparkline-widget.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add plotext + textual chart integration widgets`
  - Files: `src/operational/tui/widgets/sparkline_chart.py`

- [x] 9. Create widgets/time_block.py

  **What to do**:
  - Create `src/operational/tui/widgets/time_block.py`:
    - `TimeBlockDisplay` widget showing a time block row
    - Display: label + start→end time range + duration
    - Status indicator (OK/WARN/CRIT/PEND/ACTIVE)
    - Color from `TUI_COLORS` based on status
  - Follow wireframe from `ui/components_v2.py:kronograma_table`:
    ```
    ┌──────────┬─────────┬──────────────────────┬──────────┐
    │ Status   │ Período │ Bloco                │ Outputs  │
    ├──────────┼─────────┼──────────────────────┼──────────┤
    │ [OK]     │ MANHA   │ Acordar              │ -        │
    └──────────┴─────────┴──────────────────────┴──────────┘
    ```

  **Must NOT do**:
  - Do NOT use Rich Table (use Textual DataTable or grid)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple display widget
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7, 8, 10)
  - **Blocks**: Tasks 11-17
  - **Blocked By**: Task 4

  **References**:
  - `src/operational/ui/components_v2.py:881-921` — kronograma_table wireframe
  - `src/operational/entities/time_block.py` — TimeBlock entity

  **Acceptance Criteria**:
  - [ ] TimeBlockDisplay shows label + time range + status
  - [ ] Status coloring works

  **QA Scenarios**:

  ```
  Scenario: TimeBlockDisplay renders correctly
    Tool: Bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.widgets.time_block import TimeBlockDisplay; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-9-block.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add TimeBlockDisplay widget`
  - Files: `src/operational/tui/widgets/time_block.py`

- [x] 10. Create widgets/habit_streak.py

  **What to do**:
  - Create `src/operational/tui/widgets/habit_streak.py`:
    - `HabitStreakDisplay` widget showing habit streak info
    - Display: habit name + current streak + best streak + Q_HE score
    - Visual streak bar (using Glyph.BAR_FULL/BAR_EMPTY)
    - Color based on Q_HE quality (success/warning/danger)
  - Follow wireframe pattern from existing UI components

  **Must NOT do**:
  - Do NOT calculate Q_HE here (delegate to existing habit_engine)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Display widget, pure rendering
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7, 8, 9)
  - **Blocks**: Tasks 11-17
  - **Blocked By**: Task 4

  **References**:
  - `src/operational/entities/habit.py` — Habit entity with streak fields
  - `src/operational/ui/tokens.py:140-145` — BAR_FULL, BAR_EMPTY, BAR_* glyphs

  **Acceptance Criteria**:
  - [ ] HabitStreakDisplay shows name + streak + Q_HE
  - [ ] Streak bar renders correctly
  - [ ] Q_HE coloring works

  **QA Scenarios**:

  ```
  Scenario: HabitStreakDisplay renders correctly
    Tool: Bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.widgets.habit_streak import HabitStreakDisplay; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-10-habit.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add HabitStreakDisplay widget`
  - Files: `src/operational/tui/widgets/habit_streak.py`

- [x] 11. Create screens/dashboard_screen.py

  **What to do**:
  - Create `src/operational/tui/screens/dashboard_screen.py`:
    - `DashboardScreen` class extending `textual.screen.Screen`
    - `compose()` yields: header row (Static/Label), 2x2 grid of KPICards, regime bar, pomodoro grid, next step panel
    - Use `textual.css.query` to find child widgets
    - Use `textual.containers` for layout (Horizontal, Vertical)
    - Use `grid` CSS layout for the 2x2 KPI grid
    - Load data from `core.services.get_day_snapshot()` in `on_mount()`
    - Cartesian quadrant: use `plotext.scatter()` → Static widget OR ASCII art
  - Follow layout from `ui/v2_renderers.py:render_daily_v2`

  **Must NOT do**:
  - Do NOT implement actual timer logic here (separate screen)
  - Do NOT hardcode data (load from repository)
  - Do NOT use `on_ready()` (use `on_mount()` for screen initialization)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex screen with multiple widget zones, layout composition
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 13, 14, 15, 16, 17)
  - **Blocks**: Task 18 (app integration)
  - **Blocked By**: Tasks 5, 6, 7, 8, 9, 10 (all widgets)

  **References**:
  - `src/operational/ui/v2_renderers.py:247-314` — render_daily_v2 layout
  - `src/operational/core/services.py` — get_day_snapshot, DaySnapshot
  - `src/operational/tui/widgets/kpi_card.py` — KPICard
  - `src/operational/tui/widgets/regime_bar.py` — RegimeBar
  - `src/operational/tui/widgets/pomodoro_grid.py` — PomodoroGrid
  - `https://textual.textual.io/guide/screens/` — Textual screen lifecycle
  - `https://textual.textual.io/guide/layout/` — Textual grid layout

  **Acceptance Criteria**:
  - [ ] Dashboard screen renders 4 KPI cards in 2x2 grid
  - [ ] Regime bar visible and colored
  - [ ] Pomodoro grid shows 3 sessions (S1/S2/S3)
  - [ ] Data loads from DaySnapshot via `on_mount()`
  - [ ] CSS grid layout for KPI cards

  **QA Scenarios**:

  ```
  Scenario: DashboardScreen loads and composes
    Tool: Bash
    Preconditions: TUI package installed
    Steps:
      1. cd life-ops/operational && python -c "
from textual.screen import Screen
from operational.tui.screens.dashboard_screen import DashboardScreen
screen = DashboardScreen()
print('DashboardScreen created:', type(screen).__name__)
print('compose method exists:', hasattr(screen, 'compose'))
"
    Expected Result: Screen class creates and has compose method
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-11-dashboard.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add DashboardScreen`
  - Files: `src/operational/tui/screens/dashboard_screen.py`

- [x] 12. Create screens/daily_flow_screen.py

  **What to do**:
  - Create `src/operational/tui/screens/daily_flow_screen.py`:
    - `DailyFlowScreen` showing morning/tarde/noite periods
    - Period tabs or vertical layout (MANHA → TARDE → NOITE)
    - Routine list per period with checkboxes
    - Ritual indicators at transitions
    - Active period highlighted
    - Load routines from `persistence` repository
  - Follow wireframe from PAV spec §3 (MATRIZ DE PERÍODOS):
    ```
    ┌──────────────────┬───────────────┬───────────────┬─────────────────────┤
    │   VARIÁVEL       │    MANHÃ      │    TARDE      │      NOITE          │
    │                  │   (3-5am)     │   (8-17h)     │    (18-21h)         │
    ├──────────────────┼───────────────┼───────────────┼─────────────────────┤
    │ horaAcordou      │      ✅       │      —        │         —           │
    ```

  **Must NOT do**:
  - Do NOT implement routine execution here (just display)
  - Do NOT modify routine data (read-only)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Tab/period navigation layout
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 13, 14, 15, 16, 17)
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 5, 6, 7, 8, 9, 10

  **References**:
  - `src/operational/entities/routine.py` — Routine, Ritual, Transition entities
  - `src/operational/persistence/sqlite.py` — routine repository
  - `src/operational/enums.py` — Period enum

  **Acceptance Criteria**:
  - [ ] 3 periods displayed (MANHA, TARDE, NOITE)
  - [ ] Routines listed per period
  - [ ] Ritual markers at transitions

  **QA Scenarios**:

  ```
  Scenario: DailyFlow screen renders
    Tool: interactive_bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.screens.daily_flow_screen import DailyFlowScreen; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-12-flow.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add DailyFlowScreen`
  - Files: `src/operational/tui/screens/daily_flow_screen.py`

- [x] 13. Create screens/pomodoro_timer_screen.py

  **What to do**:
  - Create `src/operational/tui/screens/pomodoro_timer_screen.py`:
    - `PomodoroTimerScreen` with active timer display
    - Large countdown timer (MM:SS format)
    - State machine visualization: IDLE → WORK → BREAK → WORK → ... → COMPLETE
    - Round indicator (Round 1/2/3/4 of 4)
    - Session indicator (S1 manha / S2 tarde / S3 noite)
    - Controls: Start, Pause, Skip Break, Abort
    - Integrate with `core/pomodoro_machine.py`
  - Follow state machine from PAV spec §9 (POMODORO TRACKER):
    ```
    [*] --> IDLE --> WORK --> BREAK --> WORK --> LONG_BREAK --> IDLE --> [*]
         WORK --> PAUSED --> WORK
         BREAK --> SKIPPED --> WORK
    ```

  **Must NOT do**:
  - Do NOT reimplement pomodoro logic (use existing core/pomodoro_machine.py)
  - Do NOT block the terminal (use textual async)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Timer with async updates, state machine visualization
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12, 14, 15, 16, 17)
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 5, 6, 7, 8, 9, 10

  **References**:
  - `src/operational/core/pomodoro_machine.py` — PomodoroStateMachine
  - `src/operational/entities/pomodoro.py` — Pomodoro entity
  - `src/operational/ui/components_v2.py:661-695` — Mermaid state diagram reference

  **Acceptance Criteria**:
  - [ ] Timer counts down correctly
  - [ ] State transitions work (IDLE→WORK→BREAK→...)
  - [ ] Round/session indicators update
  - [ ] Controls (Start/Pause/Skip/Abort) functional

  **QA Scenarios**:

  ```
  Scenario: Pomodoro timer state machine works
    Tool: interactive_bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.screens.pomodoro_timer_screen import PomodoroTimerScreen; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-13-timer.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add PomodoroTimerScreen`
  - Files: `src/operational/tui/screens/pomodoro_timer_screen.py`

- [x] 14. Create screens/habits_screen.py

  **What to do**:
  - Create `src/operational/tui/screens/habits_screen.py`:
    - `HabitsScreen` with list of all habits
    - Per-habit: name + current streak + Q_HE score + streak bar chart (plotext)
    - Filter by category (physiological, cognitive, creative, social)
    - Sort by Q_HE / streak / name
    - Load from `persistence` repository
  - Follow Q_HE display from PAV spec §2 (VARIÁVEIS DINÂMICAS):
    ```
    let focoNivel: number // 1-10
    let desviosRotina: string[] // registro de exceções
    ```

  **Must NOT do**:
  - Do NOT calculate Q_HE here (use existing habit_engine)
  - Do NOT modify habit data (read-only display)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: List view with sortable columns and plotext charts
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12, 13, 15, 16, 17)
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 5, 6, 7, 8, 9, 10

  **References**:
  - `src/operational/entities/habit.py` — Habit entity with Q_HE
  - `src/operational/core/habit_engine.py` — Q_HE calculation
  - `src/operational/persistence/sqlite.py` — habit repository
  - `src/operational/tui/widgets/habit_streak.py` — HabitStreakDisplay
  - `src/operational/tui/widgets/sparkline_chart.py` — plotext charts

  **Acceptance Criteria**:
  - [ ] Habits list renders with all fields
  - [ ] Plotext streak chart visible per habit
  - [ ] Filter and sort work

  **QA Scenarios**:

  ```
  Scenario: Habits screen renders with data
    Tool: interactive_bash
    Preconditions: TUI package installed, demo data seeded
    Steps:
      1. python -c "from operational.tui.screens.habits_screen import HabitsScreen; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-14-habits.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add HabitsScreen`
  - Files: `src/operational/tui/screens/habits_screen.py`

- [x] 15. Create screens/metrics_screen.py

  **What to do**:
  - Create `src/operational/tui/screens/metrics_screen.py`:
    - `MetricsScreen` with historical charts
    - Sleep duration sparkline (7d/30d)
    - Energy level bar chart (7d/30d)
    - Focus score sparkline (7d/30d)
    - Sleep debt calculation display
    - Load from `persistence` repository
  - Follow charts from PAV spec §7 (CÁLCULO DE SONO) and §10 (DASHBOARD):
    ```
    │  Acordou: ____h ____m  │  Dormiu: ____h ____m  │  Sono: ____h      │
    │  Energia:  [1][2][3][4][5][6][7][8][9][10]  ← Marque                │
    ```

  **Must NOT do**:
  - Do NOT calculate sleep hours here (use existing sleep_calculator)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Multiple plotext charts, data loading
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12, 13, 14, 16, 17)
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 5, 6, 7, 8, 9, 10

  **References**:
  - `src/operational/entities/metric.py` — SleepRecord, EnergyReading entities
  - `src/operational/core/sleep_calculator.py` — sleep calculation
  - `src/operational/persistence/sqlite.py` — metric repository
  - `src/operational/tui/widgets/sparkline_chart.py` — plotext charts

  **Acceptance Criteria**:
  - [ ] Sleep sparkline renders with plotext
  - [ ] Energy bar chart renders with plotext
  - [ ] Focus sparkline renders with plotext
  - [ ] 7d/30d toggle works

  **QA Scenarios**:

  ```
  Scenario: Metrics screen renders charts
    Tool: interactive_bash
    Preconditions: TUI package installed, demo data seeded
    Steps:
      1. python -c "from operational.tui.screens.metrics_screen import MetricsScreen; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-15-metrics.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add MetricsScreen`
  - Files: `src/operational/tui/screens/metrics_screen.py`

- [x] 16. Create screens/policy_screen.py

  **What to do**:
  - Create `src/operational/tui/screens/policy_screen.py`:
    - `PolicyScreen` showing current regime + history
    - Current setpoint display (PUSH/MAINTAIN/REDUCE/RECOVER)
    - FSM transition history timeline
    - Hysteresis visualization (threshold markers)
    - Setpoint adjustment controls (for future)
    - Load from `persistence` repository
  - Follow from PAV spec §6 (ERROR HANDLING) and `policy_engine.py`:
    ```
    ╭─ 🕹️ SETPOINT ATUAL ─────────────────────────────────╮
    │  MODO: [ MAINTAIN ] ◆               Atualizado em...  │
    ╰─────────────────────────────────────────────────────╯
    ╭─ 📝 ÚLTIMAS DECISÕES DE POLÍTICA ────────────────────╮
    │  2026-06-03 | PUSH → MAINTAIN | Fim de sprint...     │
    ╰─────────────────────────────────────────────────────╯
    ```

  **Must NOT do**:
  - Do NOT reimplement FSM logic (use existing policy_engine)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Timeline visualization, state display
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12, 13, 14, 15, 17)
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 5, 6, 7, 8, 9, 10

  **References**:
  - `src/operational/core/policy_engine.py` — PolicyEngine FSM
  - `src/operational/entities/policy.py` — PolicyState, Decision entities
  - `src/operational/persistence/sqlite.py` — policy repository
  - `src/operational/tui/widgets/regime_bar.py` — RegimeBar

  **Acceptance Criteria**:
  - [ ] Current regime displayed prominently
  - [ ] Transition history timeline renders
  - [ ] Hysteresis markers visible

  **QA Scenarios**:

  ```
  Scenario: Policy screen renders
    Tool: interactive_bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.screens.policy_screen import PolicyScreen; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-16-policy.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add PolicyScreen`
  - Files: `src/operational/tui/screens/policy_screen.py`

- [x] 17. Create screens/journal_screen.py

  **What to do**:
  - Create `src/operational/tui/screens/journal_screen.py`:
    - `JournalScreen` with journal entries list
    - Entry display: date + period + text preview
    - Search/filter by date range, period, text content
    - Full entry expansion on selection
    - Load from `persistence` repository
  - Follow from PAV spec §10 (DASHBOARD) and `entities/journal.py`:
    ```
    [17:07] [CHECK-IN] Energia: 7, Foco: 8 (chk_20260609_170706)
    [17:07] [ROUTINE]  Start: Hardwork Dev (CORE)
    ```

  **Must NOT do**:
  - Do NOT implement journal creation here (separate flow)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: List view with search and expansion
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12, 13, 14, 15, 16)
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 5, 6, 7, 8, 9, 10

  **References**:
  - `src/operational/entities/journal.py` — JournalEntry entity
  - `src/operational/persistence/sqlite.py` — journal repository
  - `src/operational/ui/components_v2.py:845-878` — timeline_log wireframe

  **Acceptance Criteria**:
  - [ ] Journal entries list renders
  - [ ] Search by date/period works
  - [ ] Entry expansion works

  **QA Scenarios**:

  ```
  Scenario: Journal screen renders
    Tool: interactive_bash
    Preconditions: TUI package installed
    Steps:
      1. python -c "from operational.tui.screens.journal_screen import JournalScreen; print('import ok')"
    Expected Result: Import succeeds
    Failure Indicators: Import error
    Evidence: .omo/evidence/task-17-journal.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add JournalScreen`
  - Files: `src/operational/tui/screens/journal_screen.py`

- [x] 18. Create app.py (Textual App + screen registration)

  **What to do**:
  - Create `src/operational/tui/app.py`:
    - `PAVApp` class extending `textual.app.App`
    - Register all 7 screens via `screen_registry`
    - `BINDINGS` for navigation: keys 1-7 for screens, arrow keys, q to quit, ctrl+p for command palette
    - `CSS` for layout (inline or separate .css file)
    - `compose()` method to yield header, body (current screen), footer
    - `on_mount()` lifecycle (NOT `on_ready()` — textual uses `on_mount`)
    - `set_interval()` for live clock/updates in header
    - Load theme from `theme.get_tui_theme()` via `app.theme`
    - Screen switching via `push_screen()` / `switch_screen()`
  - Integrate all widgets and screens
  - Follow textual patterns: `TextualApp` subclass, `CSS` class attribute, `BINDINGS` list, `compose()` generator

  **Must NOT do**:
  - Do NOT implement business logic here (delegate to core/)
  - Do NOT hardcode colors (use theme)
  - Do NOT use `on_ready()` (textual uses `on_mount()`)
  - Do NOT use `textual` as import (correct: `import textual`)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Main app class, screen orchestration, keybinding routing
  - **Skills**: [`textual` skill]

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on all screens)
  - **Parallel Group**: Wave 4 (with Tasks 19, 20, 21)
  - **Blocks**: Task 19 (CLI command)
  - **Blocked By**: Tasks 11, 12, 13, 14, 15, 16, 17

  **References**:
  - `src/operational/tui/navigation.py` — screen_registry
  - `src/operational/tui/theme.py` — get_tui_theme
  - `https://textual.textual.io/guide/app/` — Textual App guide (lifecycle: on_mount)
  - `https://textual.textual.io/guide/screens/` — Textual screen management
  - `https://textual.textual.io/guide/CSS/` — Textual CSS styling
  - `https://textual.textual.io/widgets/` — Widget gallery
  - `src/operational/cli/home_v2.py` — existing menu pattern

  **Acceptance Criteria**:
  - [ ] `PAVApp` starts without errors (`python -c "from operational.tui.app import PAVApp; app = PAVApp()"`)
  - [ ] All 7 screens registered and navigable
  - [ ] Keyboard navigation works (1-7, arrows, q)
  - [ ] Theme applied correctly
  - [ ] `set_interval()` live clock updates in header

  **QA Scenarios**:

  ```
  Scenario: PAVApp creates and binds work
    Tool: Bash
    Preconditions: All screens implemented
    Steps:
      1. cd life-ops/operational && python -c "
from operational.tui.app import PAVApp
app = PAVApp()
print('PAVApp created:', type(app).__name__)
print('BINDINGS:', len(getattr(app, 'BINDINGS', [])))
print('Screens registered:', len(app._registry) if hasattr(app, '_registry') else 'N/A')
"
    Expected Result: App creates, bindings list exists, screens registered
    Failure Indicators: Import error, AttributeError
    Evidence: .omo/evidence/task-18-app.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add PAVApp main application`
  - Files: `src/operational/tui/app.py`

- [x] 19. Add `tui` subcommand to cli/app.py

  **What to do**:
  - Update `src/operational/cli/app.py`:
    - Add `tui_app` import: `from operational.tui.app import PAVApp`
    - Add typer subcommand: `app.add_typer(tui_app, name="tui")`
    - Or add `tui` command that launches the Textual app
  - Follow pattern from existing command registration

  **Must NOT do**:
  - Do NOT remove existing commands
  - Do NOT change existing command behavior

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple CLI registration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18, 20, 21)
  - **Parallel Group**: Wave 4
  - **Blocks**: None (uses app.py)
  - **Blocked By**: Task 18 (app.py must exist)

  **References**:
  - `src/operational/cli/app.py:32-49` — existing subcommand registration pattern

  **Acceptance Criteria**:
  - [ ] `pav tui --help` shows TUI help
  - [ ] `pav tui` launches the Textual app
  - [ ] Existing commands still work

  **QA Scenarios**:

  ```
  Scenario: tui command registered
    Tool: Bash
    Preconditions: poetry install done
    Steps:
      1. cd life-ops/operational && poetry run pav tui --help
    Expected Result: Help text for TUI command
    Failure Indicators: Command not found
    Evidence: .omo/evidence/task-19-cli.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add tui CLI subcommand`
  - Files: `src/operational/cli/app.py`

- [x] 20. Create charts.py (plotext chart builders)

  **What to do**:
  - Create `src/operational/tui/charts.py`:
    - `build_sleep_sparkline(values: list[float]) -> str` — plotext sparkline for sleep hours
    - `build_energy_bar(values: list[int]) -> str` — plotext bar chart for energy 1-10
    - `build_focus_sparkline(values: list[float]) -> str` — plotext sparkline for focus scores
    - `build_quadrant_plot(x: float, y: float, quadrant: str, history: list) -> str` — ASCII quadrant
    - `build_scenario_radar(scenario: dict) -> str` — ASCII radar comparison
    - All functions return string (no file I/O)
    - Colors from `TUI_COLORS`
  - Consolidate plotext logic from widgets into reusable builders

  **Must NOT do**:
  - Do NOT use matplotlib (use plotext only)
  - Do NOT write to files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure function library, chart building
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18, 19, 21)
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks 14, 15 (used by habits and metrics screens)
  - **Blocked By**: Task 18 (app.py)

  **References**:
  - `src/operational/ui/components_v2.py:588-612` — ASCII radar comparison
  - `plotext.readthedocs.io/en/latest/index.html` — plotext API
  - `src/operational/tui/theme.py` — TUI_COLORS

  **Acceptance Criteria**:
  - [ ] All 5 chart builder functions exist
  - [ ] Each returns string output
  - [ ] No file I/O in any function

  **QA Scenarios**:

  ```
  Scenario: Chart builders produce output
    Tool: Bash
    Preconditions: plotext installed
    Steps:
      1. python -c "
from operational.tui.charts import build_sleep_sparkline, build_energy_bar
print(build_sleep_sparkline([7, 8, 6.5, 7.5, 8, 7, 6]))
print(build_energy_bar([7, 8, 6, 9, 7, 8, 6]))
"
    Expected Result: Text-based chart output
    Failure Indicators: Import error, plotext error
    Evidence: .omo/evidence/task-20-charts.log
  ```

  **Commit**: YES
  - Message: `feat(tui): add plotext chart builders`
  - Files: `src/operational/tui/charts.py`

- [x] 21. Add TUI tests to tests/

  **What to do**:
  - Create `tests/tui/` directory
  - Create `tests/tui/__init__.py`
  - Create `tests/tui/test_theme.py` — test theme mapping
  - Create `tests/tui/test_navigation.py` — test state management
  - Create `tests/tui/test_charts.py` — test plotext chart builders
  - Create `tests/tui/test_widgets.py` — test widget imports
  - Create `tests/tui/test_screens.py` — test screen imports
  - Follow existing test patterns from `tests/` directory

  **Must NOT do**:
  - Do NOT test Textual rendering (use unit tests for logic only)
  - Do NOT break existing tests

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Test file creation, follows existing patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 18, 19, 20)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Tasks 3, 4, 20 (need theme, navigation, charts)

  **References**:
  - `tests/` — existing test structure to follow
  - `pytest.ini` — test configuration

  **Acceptance Criteria**:
  - [ ] All new test files exist
  - [ ] `pytest tests/tui/` runs without errors
  - [ ] Existing 2518 tests still pass

  **QA Scenarios**:

  ```
  Scenario: TUI tests pass
    Tool: Bash
    Preconditions: poetry install
    Steps:
      1. cd life-ops/operational && poetry run pytest tests/tui/ -v
    Expected Result: All TUI tests pass
    Failure Indicators: Test collection error, assertion failure
    Evidence: .omo/evidence/task-21-tests.log
  ```

  **Commit**: YES
  - Message: `test(tui): add TUI test suite`
  - Files: `tests/tui/`

---

## Final Verification Wave (MANDATORY)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, import check). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .omo/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `mypy --strict src/operational/tui/` + `ruff check src/operational/tui/` + `python -c "from operational.tui import app"`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty state, invalid input, rapid actions. Save to `.omo/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **1**: `feat(tui): add textual + plotext dependencies` - pyproject.toml
- **2**: `feat(tui): scaffold tui package structure` - src/operational/tui/
- **3**: `feat(tui): add theme and navigation` - src/operational/tui/theme.py, navigation.py
- **4**: `feat(tui): add KPI and regime widgets` - src/operational/tui/widgets/
- **5**: `feat(tui): add pomodoro and chart widgets` - src/operational/tui/widgets/
- **6**: `feat(tui): add all 7 screens` - src/operational/tui/screens/
- **7**: `feat(tui): integrate app and CLI command` - src/operational/tui/app.py, cli/app.py
- **8**: `test(tui): add TUI tests` - tests/

---

## Success Criteria

### Verification Commands
```bash
cd life-ops/operational
poetry install
poetry run pav tui                    # TUI launches without errors
python -c "from operational.tui import app"  # Import sanity check
poetry run mypy --strict src/operational/tui/  # Type check passes
poetry run pytest tests/             # All 2518 tests still pass
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All 7 screens navigable
- [ ] plotext charts render in 3+ screens
- [ ] mypy strict passes on new code
- [ ] Original 2518 tests still pass
