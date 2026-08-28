# 05 — `interfaces/tui` Reverse-Engineering

**Date:** 2026-08-28
**Source:** `C:/Users/mathe/code_space/life-oss/life/interfaces/tui/` (44-line README only)
**Mode:** Gap analysis. No code exists. No tests. No CI matrix entry.
**Sibling context:** `interfaces/cli/` exists with `pyproject.toml` + `read_tasks.py` (broken entry-point per critic-gap #8); `apps/kanban/tuiboard`, `apps/dev-tools/taskdog`, `apps/calendar/solverforge-calendar` were deleted 2026-08-28 (orphan Windows-locked dirs cleared).

---

## README summary

The 44-line `README.md` is a **specification, not implementation**. It declares:

- **Position in pipeline:** Pure consumer of `data/tasks.jsonl`. Writes feedback to `data/feedback.jsonl`. **Never writes `vault/`** (Deep Agent owns vault).
- **Flow diagram:** `vault → Deep Agent → tasks.jsonl → TUI apps → feedback.jsonl → Deep Agent`. TUIs sit at the human-in-the-loop edge.
- **3 planned apps, all Textual:**
  | App | Focus |
  |-----|-------|
  | `daily-view` | Today's tasks + regime + Q_HE |
  | `kanban` | Gantt / board view by horizon |
  | `calendar` | Wave/sprint calendar |
- **Contracts:** Import `Task`, `Period`, `Priority` from `src/contracts/` (Pydantic v2, frozen=True, extra="forbid").
- **Feedback protocol:** Append-only `{"id", "action", "date", "source"}` lines; Deep Agent reads back.

**Read more:** nothing else exists in the directory. No `pyproject.toml`, no `__init__.py`, no `app.py`, no `screens/`, no `widgets/`, no entry points.

---

## Gap inventory

| # | Gap | Severity | Evidence |
|---|-----|----------|----------|
| 1 | **Zero source code** | P0 | `ls interfaces/tui/` returns only `README.md` (1209 B) |
| 2 | **No `pyproject.toml`** | P0 | No deps declared; cannot `uv sync` or `pip install -e .` |
| 3 | **No entry points / `__main__.py`** | P0 | Nothing to invoke. Sister `interfaces/cli/pyproject.toml:9` has broken `life-tasks` script (critic-gap #8) — pattern at risk |
| 4 | **No `tests/tui/` directory** | P1 | Path referenced in Phase 1 audit (B-08) as empty/orphan dir needing deletion; never existed as scaffolded `tests/tui/` |
| 5 | **No CI matrix entry** | P1 | `.github/workflows/ci.yml:56-65` matrix covers `src/operational`, `src/ikigai`, `src/contracts`; nothing for `interfaces/tui` (per Step 8 in `04-sequencing.md` this is one of the additions needed) |
| 6 | **Consumer data missing** | P0 | `data/tasks.jsonl` does NOT exist (B-04). Producer `vibe-ops/src/pipeline/daily_consolidator.py` exists (327-408 lines, `--dry-run` supported) but never invoked. TUIs would render zero rows on first launch |
| 7 | **No contracts import path resolution** | P1 | README says `from contracts import Task, Period, Priority` but `src/contracts/` is a sibling package not on default PYTHONPATH. Sister `interfaces/cli/read_tasks.py` pattern TBD |
| 8 | **No feedback writer stub** | P1 | Append-only `data/feedback.jsonl` writer not scaffolded; Deep Agent's read-back loop has no input channel |
| 9 | **Architecture lie about CLI** | P1 | Per critic-gap #4, root `python -m life.cli daily run` does NOT call cybernetic engine; TUIs will inherit same documentation lie if "subprocess → vibe-ops" framing is copied |
| 10 | **Dual-layer architecture unresolved** | P1 | Memory `[[interfaces-architecture-2026-08-27]]` says forks (tuiboard/taskdog/solverforge-calendar) deleted → "user views" must be built elsewhere. Native TUIs here = backend control plane ONLY, not user views |

**Net:** 10 gaps total (4 P0, 5 P1, 1 P1-equivalent). The directory is a **stub-of-a-stub**: README declares the *interface contract*, no implementation.

---

## Build requirements per planned TUI

### Common (all 3 apps)

- `textual>=0.85` (TUI framework; CSS-like styling, async event loop, screens)
- `textual-dev` (live reload during dev) — dev-only
- `rich>=13.7` (RichLog, Markdown render; already used by sister `interfaces/cli`)
- `pydantic>=2.6` (Task / Subtask / ChecklistItem from `src/contracts/`)
- `httpx` or `watchfiles` for `tasks.jsonl` polling (no inotify in stdlib)
- Entry pattern: `python -m interfaces.tui.daily_view` (sibling to `interfaces/cli/read_tasks.py`)
- Each app MUST add `data/feedback.jsonl` write helper (shared module: `interfaces/tui/_feedback.py`)

### `daily-view` (1-day, lowest complexity)

- **Layout:** `Header` + `DataTable` (today's tasks) + side `Static` (regime + Q_HE score) + `Footer` (keybindings)
- **Widgets:** `DataTable`, `Static`, `Markdown` (for goal/mission context)
- **Keys:** `d` (mark done), `p` (cycle priority), `r` (refresh), `?` (help)
- **Read:** `data/tasks.jsonl` filter `date == today AND status != done`
- **Phase 1 blocker:** depends on PR-3 sensor seeding + Step 3 task writer migration (sequencing `04-sequencing.md`)

### `kanban` (3-5 days, medium complexity)

- **Layout:** Tabbed `Tabs` with one `DataTable` per `Period` (DAY/WEEK/MONTH/QUARTER/YEAR) + horizontal Gantt strip
- **Widgets:** `Tabs`, `TabPane`, `DataTable`, `Horizontal`/`Vertical` containers, custom `GanttStrip` (Canvas-based)
- **Read:** `data/tasks.jsonl` grouped by `period` + `horizon`
- **Risk:** Pydantic `Period` enum has 5+ values → 5 tab panes. Gantt needs date math (`pendulum` or stdlib `datetime`); add `pendulum>=3.0` if needed
- **Phase 1 blocker:** depends on PR-2 contracts unification (canonical `Period` enum)

### `calendar` (3-5 days, medium complexity)

- **Layout:** `Calendar` widget (Textual ≥0.50) + `ListView` for selected-day tasks + `ModalScreen` for task detail/edit
- **Widgets:** `Calendar`, `ListView`, `ModalScreen`, `Input`, `Button`
- **Read:** `data/tasks.jsonl` indexed by `sprint_start`/`sprint_end` (Wave/Sprint from `src/contracts/planning.py`)
- **Write:** `data/feedback.jsonl` `action=snooze|date_shift`
- **Phase 1 blocker:** depends on Wave/Sprint contracts existing with date fields (verify `src/contracts/planning.py`)

### Scaffolding order

1. `pyproject.toml` with `[tool.hatch.build.targets.wheel]` packages = `["tui"]`
2. `interfaces/tui/__init__.py` + `__main__.py` (dispatches subcommand)
3. `interfaces/tui/_io.py` (JSONL read + tail-follow)
4. `interfaces/tui/_feedback.py` (append-only writer, file-locked)
5. `interfaces/tui/daily_view.py` (first app — simplest, validates pipeline)
6. `kanban.py`, `calendar.py` (after daily_view stabilizes)
7. `tests/tui/` (unit tests for `_io`, `_feedback`; smoke tests for each app via `pytest-textual-snapshot` or `pytest-asyncio` + `App.run_test()`)

---

## Trade-offs

### TUI vs CLI vs Web (already settled at architecture layer)

Per `CLAUDE.md`: "Interfaces only read vault; write goes to data/feedback" + memory `[[interfaces-architecture-2026-08-27]]`: **forks are user views, native CLI/TUI = backend control plane**. So:

- **TUI here:** operator / power-user keyboard-driven control plane (mark done, snooze, reassign priority). NOT a replacement for user-facing Obsidian/Claude-Code views.
- **CLI (`interfaces/cli/read_tasks.py`):** one-shot script-mode queries. Sister; shares `tasks.jsonl` reader.
- **Web:** out of scope. No web stack declared. `stitch-*` and `react-vite-dashboard` skills available if user later requests.
- **External consumers:** Obsidian plugin / Claude-Code MCP / Deep Agent (`ikigai` kernel) already read `data/` directly.

### Textual vs Ratatui vs custom

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Textual** (README choice) | Python = same language as Pydantic contracts; widget library; CSS-like styling; rapid iteration | Slower startup (~150ms); heavier dep; lock-in to Textual's reactive model | **Pick.** README committed. Sibling `interfaces/cli` already uses Rich — Textual extends Rich natively |
| **Ratatui (Rust)** | `vibeops-tui` already uses it (Rust); blazing fast; native terminal feel | Language boundary = no direct Pydantic import; need JSON serialization boundary; slower iteration | Reject for `interfaces/tui` (Python layer); keep for `vibe-ops/vibeops-tui` (Rust service) |
| **Urwid / prompt_toolkit** | Lighter deps; long history | Smaller widget sets; worse async story; older ecosystem | Reject. Textual is the modern choice and committed in README |
| **Custom (curses/raw ANSI)** | Zero deps; minimal binary | Reinventing widget layout, event loop, focus mgmt | Reject. Cost > value for 3 apps |

### Native Python vs fork consumption

- README assumes **native Python apps in `interfaces/tui/`**.
- Three relevant forks (`apps/kanban/tuiboard`, `apps/dev-tools/taskdog`, `apps/calendar/solverforge-calendar`) were deleted 2026-08-28 as orphan Windows-locked dirs (per memory `[[windows-orphan-dir-delete]]`).
- Per `[[interfaces-architecture-2026-08-27]]`, native CLI/TUI here = **operator control plane only**. The "user views" for kanban/calendar would now need NEW fork projects under `apps/` or be replaced by Obsidian plugin / Claude-Code skill.
- **Implication:** If README's "kanban" + "calendar" mean *user-facing* apps, they're architecturally misplaced in `interfaces/tui/`. Re-scope to "operator dashboards" or move to `apps/`.

---

## Cross-references

- **Phase 1 audit:**
  - `01-verified.md` B-04 (`tasks.jsonl` missing — producer never invoked) → TUIs will render empty
  - `01-verified.md` B-08 (empty `tests/{tui,ui,property}/` directories) → `tests/tui/` was never scaffolded
  - `02-critic-gaps.md` #8 (sister `interfaces/cli` broken entry-point) → pattern risk for `interfaces/tui`
  - `02-critic-gaps.md` #4 (root CLI architectural lie) → TUIs must not copy "subprocess → vibe-ops" framing
  - `03-priority-matrix.md` PR-2 (contracts unification) → blocks all 3 TUIs
  - `03-priority-matrix.md` PR-3 (seed sensor) → unblocks real data flow
  - `04-sequencing.md` Step 8 → CI matrix addition for `interfaces/tui`
  - `05-open-questions.md` OQ-1, OQ-2, OQ-3 → storage topology, contracts naming, `tasks.jsonl` role all undecided
- **Memory:**
  - `[[interfaces-architecture-2026-08-27]]` — dual-layer: native = operator, forks = user views
  - `[[ag3-gateway-orphan-2026-08-27]]` — fork path collision risk
  - `[[windows-orphan-dir-delete]]` — 3 fork dirs deleted; TUIs must NOT assume they exist
  - `[[data-first-methodology]]` — "no new code until 5+ manual logs" (SONHO 1/5); writing TUIs may violate data-first
- **Sister dirs:** `interfaces/cli/` (43-line `read_tasks.py` + broken `pyproject.toml`), `apps/` (orphans deleted)
- **Contracts:** `src/contracts/{common,task,planning,metrics}.py` (canonical, Phase 3 PR-2 winner pending)
- **Data sources:** `data/tasks.jsonl` (MISSING), `data/feedback.jsonl` (MISSING), `data/vibe_ops.db` (19 tables, 0 rows per B-05)
- **Plan ordering:** `04-sequencing.md` — TUI build belongs AFTER Step 6 (sensor seeded) + Step 8 (CI matrix extended)
