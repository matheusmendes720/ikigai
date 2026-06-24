# Evolution Timeline — operational kernel

> **Reads:** `docs/adr/SPRINT-1..3-REPORT.md`, `docs/adr/ARCHITECTURAL_REFRAMING_2026-06-07.md`, `ROADMAP.md`, `INTEGRATION-BACKLOG.md`, `docs/architecture/01-MVC-LAYERS.md`.
> **Status:** 🟢 Authoritative — constructed from sprint reports + ADRs.

---

## Pre-history — before the sprints

Before sprint 0, the system did not exist. The codebase that would become `operational` was a collection of Python scripts in a personal dotfiles repo (`~/.time-tasker/`), written to automate a daily routine tracker built around `pav` (a Python TUI). The scripts had:
- No type annotations
- No tests
- No documentation
- Hardcoded constants scattered across files
- No separation between "what I want to compute" and "how I want to display it"

The decision to extract this into a structured kernel was the first architectural move: **separate the computation from the interface**.

---

## Sprint 0 — Scaffolding + tooling

**Goal:** Establish the build system, CI pipeline, and import discipline before writing any business logic.

| Deliverable | Detail |
|---|---|
| `pyproject.toml` | uv workspace with `packages/core/` + `apps/cli/` + `apps/tui/` |
| `mypy` config | Strict mode; all modules typed |
| `ruff` config | All rules enabled; pre-commit hook |
| `pytest` config | Coverage threshold 90% |
| Import discipline | Core may not import entities or persistence |

**What this sprint decided:** The three-layer rule (Core / Entity+Persistence / Interface) would be enforced by tooling, not convention. The import graph rules in `04-IMPORT-GRAPH.md` were written here and have never been violated.

---

## Sprint 1 — Foundation: constants, exceptions, enums, types

**Goal:** Establish the vocabulary before building any logic.

| Deliverable | Lines | Tests |
|---|---|---|
| `core/constants.py` — 22 magic numbers, all in one place | ~200 | 551 |
| `core/enums.py` — `Period`, `RoutineType`, `HabitCategory`, `PolicyState`, `PomodoroPhase`, `TimeOfDay`, `MetricKind`, `BudgetClass`, `Scenario`, `Verdict` | ~150 | (in sprint 2) |
| `core/types.py` — `NewType`, `Protocol`, `TypeAlias` | ~50 | (in sprint 2) |
| `core/exceptions.py` — `PAV001`…`PAV010` error codes | ~80 | (in sprint 2) |

**Key decision:** All magic numbers are declared in `constants.py` with their unit. Example: `POMODORO_WORK_MINUTES: Final[int] = 25`. The rule "no magic numbers in business logic" has been enforced since sprint 1.

**Architectural signal:** The sprint 1 report is a serial log — one module after another, no parallelism. This is the TTY phase of the project.

---

## Sprint 2 — Entities: 8 Pydantic modules

**Goal:** Freeze the data model before the algorithms.

| Deliverable | Lines | Tests |
|---|---|---|
| `routine.py`, `time_block.py`, `journal.py`, `habit.py`, `metric.py`, `pomodoro.py`, `policy.py`, `consolidation.py` | ~1,400 | 820 |

Each entity follows the same recipe:
```python
model_config = ConfigDict(frozen=True, extra="forbid")
```

**Key decision:** Entities **do not import each other**. A `RoutineLog` references a `routine_id: str`, not a `Routine` object. This decouples the entity graph from the in-memory object graph and makes persistence straightforward (foreign keys are just strings).

**Architectural signal:** The sprint 2 report introduces the first parallel sub-agent ("3A + 3B in parallel" would come in sprint 3). The ANSI stream is starting to carry its own structure.

---

## Sprint 3 — Core P1: sleep, validation, pomodoro, scenario

**Goal:** First algorithms — the ones that have no dependents yet.

| Sub-Agent | Module | Tests |
|---|---|---|
| 3A | `sleep_calculator.py` | 134 |
| 3A | `time_validator.py` | 111 |
| 3B | `pomodoro_machine.py` | 134 |
| 3B | `scenario_classifier.py` | 65 |

Total: **1,815 tests, 99.5% coverage, all green.**

**Key decisions made in this sprint:**
1. `PomodoroMachine` is an 8-state state machine — the reference implementation for fine-grained round tracking
2. `SleepCalculator` is deterministic — given the same inputs, it always returns the same score
3. `ScenarioClassifier` classifies the current day into one of 6 scenarios based on history

**Architectural signal:** The sprint 3 report introduces **parallel sub-agents** ("3A + 3B DEPLOYED (2 PARALLEL)"). This is the Job/Channel moment — the project is starting to model its own development process as a state machine.

---

## Sprint 4 — Core P2: habit engine, policy engine, consolidator

**Goal:** The BFF algorithms — the ones that everything else depends on.

| Module | What it does | Key formula |
|---|---|---|
| `habit_engine.py` | Habit consistency model | `H(t) = 1 − e^(−λ·streak)`, `E = R·(1−H)`, `Q_HE = f(E, R, S)` |
| `policy_engine.py` | 4-state FSM with hysteresis | PUSH → MAINTAIN → REDUCE → RECOVER |
| `consolidator.py` | Per-day roll-up | raw events → `DayContext` |

**Key decision (formalised later in ADR):** Pomodoro is reframed as a **plug-in contract**, not a pipeline stage. This decouples the fine-grained round tracker from the gross-entry/exit time-blocks model.

**Architectural signal:** This is the "Neovim Msgpack-RPC" moment for the project — the core algorithms are now stable enough to have plug-in contracts. The kernel can now be a server.

---

## Sprint 5 — Persistence: Repository, InMemory, SQLite, migrations

**Goal:** Make the data outlive the process.

| Module | Role |
|---|---|
| `base.py` | `Repository[T]` Protocol — generic CRUD contract |
| `memory.py` | InMemory backend — dict-backed, thread-safe |
| `sqlite.py` | SQLite backend — connection-pooled, versioned schema |
| `runner.py` | `MigrationRunner` — forward-only, backed-up before each run |
| `migrations/` | `0001_init.sql` … `0003_add_ajuste_fino.sql` |

**Key decision:** The CLI and TUI **do not know which backend is active**. They hold a `Repository[Routine]` and call `.add()`, `.get()`, `.list()`. Switching from InMemory → SQLite is a one-line change at startup.

---

## Sprint 6 — Parsers + Reports

**Goal:** Make the kernel's output machine-readable and human-readable.

| Module | Role |
|---|---|
| `frontmatter.py` | Parse YAML frontmatter from markdown journal entries |
| `time_block_parser.py` | Parse CSV / JSON / loose-format time blocks |
| `daily_summary.py` | Render today's `DayContext` as markdown |
| `weekly_report.py` | Render a 7-day `WeeklySnapshot` as markdown |

---

## Sprint 7 — Meta: registry, validators, factories + CLI (Typer)

**Goal:** Close the loop between data and code — registry discovery, cross-field validation, factory construction, and the first complete CLI.

| Deliverable | Detail |
|---|---|
| `meta/registry.py` | `EntityRegistry` — string-name → class lookup |
| `meta/factories.py` | `make_routine(spec)`, `make_metric(spec)` — construct from raw dict |
| `meta/validators.py` | Cross-field rules — e.g. `start_ts < stop_ts` |
| `apps/cli/` | 12 Typer subcommands, `pav home` interactive menu, `pav tui` launcher |

**Key decision:** `apps/cli/` is the first **remote UI** for the kernel. The CLI is a separate process from the kernel (they share the same Python interpreter in dev, but the boundary is explicit in code). This sets the pattern for the TUI.

---

## Sprint 8 — Integration: factory↔persistence + E2E

**Goal:** Verify that the factory → repository → output pipeline works end-to-end.

31 E2E scenarios run against the full stack: factory → SQLite → retrieve → validate → render. All pass.

---

## Sprint 9 — Documentation + ADRs

**Goal:** Document everything that was decided.

This sprint produced:
- The `docs/architecture/` tree (5 docs)
- The `docs/data/` tree (4 docs)
- The `docs/algorithms/` tree (6 docs)
- The `docs/adr/` tree (15 PRD/ADR documents)
- The `docs/tui/` tree (8 docs)
- The `docs/ux/` tree (18 component/screen/flow docs)

**ADR: Architectural Reframing 2026-06-07**

The most significant document produced in this sprint. It changed the identity of the project:

> "PomodoroMachine was the central state machine... Pomodoros are a **future plug-in** for Timewarrior integration, not a current feature."

This single reframe has downstream consequences that play out in sprints 10 and beyond: the policy engine becomes the primary state machine, the time-blocks pipeline is simplified to gross entry/exit, and the journal is repositioned as a reflection checkpoint outside the pipeline.

---

## Sprint 10 — Verification + sign-off

**Goal:** Clean CI, zero mypy errors, zero ruff warnings, all 2,518 tests green.

Result: 🟢 all green.

---

## Post-sprint — medic (Go toolkit)

Sprint 10 closed the Python kernel. The next chapter is `life-ops/medic/` — a Go binary that wraps the kernel and adds:
- Health gates (coverage, complexity, test count)
- Code review (`medic review`, `medic issue`, `medic pr`)
- Visual debug pipeline (`medic visual capture`, `medic visual diff`, `medic visual critic`)
- Agentic workflow engine (`medic workflow run`)
- MiniMax VL-01 vision critic (`medic vision critique`)

The Go toolkit is written in a different language **by design** — it enforces the boundary between "kernel" and "tooling around the kernel". It cannot import the Python kernel; it must interact with it the way any external tool would: running commands, reading output, asserting exit codes.

---

## Timeline summary

```
Sprint  0  Scaffolding        import discipline, tooling, CI
Sprint  1  Foundation         22 constants, 10 enums, 10 exceptions, 551 tests
Sprint  2  Entities          8 Pydantic models, frozen, 820 tests
Sprint  3  Core P1           sleep + validator + pomodoro + scenario, 1815 tests
Sprint  4  Core P2           habit_engine + policy_engine + consolidator  ← BFF
Sprint  5  Persistence       Repository Protocol + 3 backends + migrations
Sprint  6  Parsers+Reports   frontmatter + time_block + daily/weekly reports
Sprint  7  Meta+CLI          registry + factories + validators + 12 Typer cmds
Sprint  8  Integration       factory↔persistence E2E, 31 scenarios
Sprint  9  Documentation     47 docs across 6 trees + 15 ADRs
Sprint 10  Verification      2518 tests, mypy, ruff — all green 🟢

Post-sprint          medic (Go) — health gates + visual debug + vision critic
```
