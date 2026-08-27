# Architecture Narrative — operational as a living system

> **Status:** 🟢 Authoritative narrative.
> **Reads:** `docs/architecture/01-MVC-LAYERS.md` through `11-VISUAL-DEBUG-PIPELINE.md`.
> **Related:** `docs/adr/ARCHITECTURAL_REFRAMING_2026-06-07.md`, `ROADMAP.md`, `INTEGRATION-BACKLOG.md`.

---

## The shape of this system

`operational` is a productivity kernel — a set of pure-arithmetic modules that model a human's daily routine, habits, sleep, and policy state. It is not an app. It is the engine beneath an app.

The system has three distinct surfaces that consume the same core:

```
packages/core/           ← pure arithmetic; 19 modules, zero I/O
    │
    ├── apps/cli/        ← Typer + Rich; thin controllers over the core
    ├── apps/tui/        ← Textual + plotext; screen-based interface
    └── life-ops/medic/  ← Go toolkit; health gates, code review, visual debug

packages/core/  is  the headless core
apps/*  are  the remote UIs
life-ops/medic/  is  the devops / health UI for the kernel itself
```

This is intentional. The kernel owns no I/O. The interfaces own no business logic. The boundary is enforced by import-discipline rules (documented in `04-IMPORT-GRAPH.md`).

---

## The five layers and their contracts

### Layer 1 — Core algorithms

`packages/core/` contains 19 modules. Every module is:
- **Pure function or dataclass** — no side effects, no I/O, no imports from `entities/` or `persistence/`
- **Tested to 98–100% coverage** — per sprint reports
- **Typed with mypy** — `python -m mypy packages/core/` clean
- **Linted with ruff** — `ruff check packages/core/` zero warnings

The core modules are the **BFF** (Backend-for-Frontend) in the sense that all presentation logic is derived from their outputs. No interface renders anything that hasn't first been computed here.

Key algorithms:
- `habit_engine.py`: `H(t) = 1 − e^(−λ·streak)`, `E = R·(1−H)`, `Q_HE = f(E, R, S)` — the habit consistency model
- `policy_engine.py`: 4-state FSM with hysteresis — PUSH → MAINTAIN → REDUCE → RECOVER
- `consolidator.py`: per-day roll-up from raw events → `DayContext`
- `next_step.py`: "what should I do now?" — the recommendation engine

### Layer 1.5 — Entities

`packages/core/entities/` contains 10 frozen Pydantic v2 models. All are constructed exclusively through `meta/factories.py`. They represent the **canonical wire format** — the same JSON shape whether it comes from SQLite, JSON-flat, or the CLI.

### Layer 2 — Persistence

`packages/core/persistence/` implements the **Repository Protocol** (`Repository[T]`). Three backends:
- **InMemory** — tests, ephemeral runs
- **SQLite** — production default
- **JSON-Flat** — CLI state inspection (`pav state show`)

The Protocol means switching backends is a one-line change at startup. No interface knows which backend is active.

### Layer 3 — Interfaces (CLI + TUI)

`apps/cli/` (Typer + Rich) and `apps/tui/` (Textual + plotext) are **siblings**. They share no code. Cross-cutting logic lives in `core/services.py` or the `Repository` Protocol — never in the interface layer.

The TUI runs as a **separate process** from the CLI (via `pav tui`). The CLI can launch, pause, and resume the TUI. This is the first step toward the RPC-decoupled architecture described in the Rust integration doc.

### Layer 4 — Medic (Go toolkit)

`life-ops/medic/` is a **Go binary** that wraps the Python kernel. It is the "headless devops UI" for operational:
- `medic review` — runs the full test suite, linter, type-checker
- `medic health` — runs health gates (coverage, complexity, test count)
- `medic visual` — captures TTY frames, renders SVG, diffs against golden
- `medic vision` — MiniMax VL-01 critic on SVG frames
- `medic workflow` — YAML workflow engine with 13 registered actions

Medic is intentionally written in a different language. It **cannot** import the Python kernel — it must interact with it the same way any external tool would: by running commands, reading output, and asserting exit codes. This enforces the boundary.

---

## The RPC evolution — how the system is thinking about its future

The most important architectural shift was the ADR of **2026-06-07** (`ARCHITECTURAL_REFRAMING_2026-06-07.md`). It reframed `PomodoroMachine` from "central state machine" to "plugg-in contract". This is a small change in code terms but a large change in architectural identity:

**Before:** Pomodoro was the primary mechanism for time-block decomposition. It was wired into the time-blocks pipeline.

**After:** Pomodoro is an **optional plugin** for future Timewarrior integration. The time-blocks pipeline captures gross entry/exit only. Journal entries are reflection checkpoints *outside* the pipeline. The two streams are independent.

This is exactly the architectural move that Neovim made when it decoupled its UI from its core: the protocol between them is now explicit and stable, so either side can evolve independently.

The system is now positioned for three RPC evolutions:

```
Phase 1 (now):              Phase 2 (+3mo):            Phase 3 (+6mo):
apps/tui/ (Textual)    →    apps/tui-rs/ (ratatui)  →  opcore serve (Go headless)
                               │                           │
                               │ Unix socket              │ Unix socket
                               ▼                          ▼
                          Go opcore              apps/tui-rs/ + apps/cli-rs/
                          (unchanged)            (Rust UIs, Go core)
```

Each arrow represents a capability unlocked:
- **Arrow 1:** Rust TUI can be developed independently of the Go core
- **Arrow 2:** The Go core becomes a network service; multiple UIs can connect simultaneously

---

## The visual debug loop

The most concrete new capability enabled by the RPC evolution is the **visual debug pipeline**. In the current system (Phase 1), the TUI is a single process — a bug in the layout engine shows up as visual corruption, but the developer has no way to inspect the frame at pixel level.

With the Rust TUI over Unix socket, the capture surface is the socket itself. Every frame rendered by ratatui is also written to a shared ring buffer (`/tmp/opchart.dat`). The Go `medic` tool reads the ring buffer, renders it as SVG, and feeds it to the MiniMax VL-01 critic.

This closes the loop:

```
Rust TUI renders frame → ring buffer → medic reads → SVG → MiniMax → findings
                                                              ↓
                                     human reviews findings ←┘
```

The visual debug pipeline is documented in full in `11-VISUAL-DEBUG-PIPELINE.md`.
