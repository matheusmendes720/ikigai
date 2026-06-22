# Algorithmic Life OS

> **Personal productivity orchestration system** — a CLI hub, a PAV productivity kernel,
> a cybernetic data-mesh, and a strategic planning layer. 100% local, single-user,
> append-only. Zero LLM in the daily pipeline. Pure arithmetic only.

---

## GitHub Infrastructure

| Resource | URL |
|----------|-----|
| **Repository** | https://github.com/matheusmendes720/ikigai |
| **Project Board** (Kanban + Roadmap) | https://github.com/users/matheusmendes720/projects/5 |
| **Issues** (backlog, planning) | https://github.com/matheusmendes720/ikigai/issues |
| **Wiki** | https://github.com/matheusmendes720/ikigai/wiki |
| **CI/CD** | `.github/workflows/ci.yml` — ruff, mypy --strict, pytest, pre-commit |

**Project fields:** Priority (P0–P3), Pipeline (Backlog → Ready → In Progress → In Review → Done), Domain, Size (story points), Sprint (1-week iterations)

---

## TL;DR — Three Subsystems, One Goal

```
┌──────────────────────────────────────────────────────────────┐
│                        life/ (root)                          │
│   CLI hub + daily/weekly orchestrator + 5 domain centrals    │
│   centrals: task · finance · knowledge · research            │
└────────────────────────────┬─────────────────────────────────┘
                             │ calls via subprocess
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ life-ops/       │  │ life-ops/       │  │ vibe-ops/       │
│ operational/    │  │ life_tatics/     │  │                 │
│ (ACTIVE DEV)   │  │ (standalone     │  │ Cybernetic      │
│ PAV kernel     │  │  time tactics)  │  │ data-mesh       │
│ 2518 tests     │  │                 │  │ Obs↔SQLite↔TW   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

| Subsystem | Language | Role | Status |
|-----------|----------|------|--------|
| `life/` (root) | Python | CLI hub — Typer orchestrator | 🟡 Stable |
| `life-ops/operational/` | Python | **PAV productivity kernel** (CLI + TUI, uv workspace) | 🟢 **Active** |
| `life-ops/life_tatics/` | Python | Standalone time-block planner | 🟡 Stable |
| `vibe-ops/` | Python + Rust | Cybernetic loop · Target-Sensor-Adjuster · 3-cluster data | 🟡 Stable |
| `strategics/` | PT-BR prose | Strategic frameworks (pyramid, dual-frame, 4 regimes) | 🟢 Read-only |
| `taskwarrior/` | Bash + Python | Taskwarrior binary + scripts + config | 🟢 Stable |

**Primary development:** `life-ops/operational/` (the PAV kernel).

---

## Quick Start

### PAV Kernel — Active Development (run this first)

```bash
cd life-ops/operational
uv sync

pav --help
pav home                    # interactive menu
pav screen dashboard        # TUI dashboard

# Quality gates
uv run pytest              # 2518 tests
uv run ruff check packages/core/src/
uv run mypy packages/core/src/
```

### Root CLI Hub

```bash
cd life-ops/life          # or from repo root with PYTHONPATH
python -m life.cli daily run
python -m life.cli weekly run
python -m life.cli task today --json
```

### Vibe-ops (Cybernetic Data-Mesh)

```bash
cd vibe-ops
python src/main.py run-daily [--date YYYY-MM-DD]
python src/main.py status
python src/vibe_cli.py hybrid_search "query"
```

### Life-tatics (Standalone Time Planner)

```bash
cd life-ops
poetry install
poetry run life-tatics --help
```

---

## Architecture — Three-Layer CLI Model

```
life/ (root)
│
├── cli/cli.py          — Typer app root; mounts centrals, handlers, plugins
├── cli/config.py       — LifeConfig dataclass; YAML + env loading
├── cli/log.py         — Structured logger
│
├── handlers/           — Daily + weekly orchestrators (call centrals via subprocess)
│   ├── daily.py
│   └── weekly.py
│
├── centrals/           — Thin domain wrappers (delegate to external submodules)
│   ├── base.py         BaseCentral.run_cli() — subprocess helper
│   ├── task.py         → Taskwarrior binary
│   ├── finance.py     → fin_ops submodule
│   ├── knowledge.py    → leitura, mindmaps, notes
│   └── research.py     → research submodule
│
└── plugins/            — Plugin discovery + lifecycle hooks
    ├── protocol.py     PluginProtocol (register + before/after hooks)
    ├── loader.py       Filesystem discovery from cfg.plugin_dirs
    └── builtin/        health_check command
```

---

## life-ops/operational/ — PAV Productivity Kernel (Active Dev)

uv workspace with 3 packages: `packages/core`, `apps/cli`, `apps/tui`.

```
operational/
├── packages/core/src/operational/
│   ├── constants.py      PAVConstants (22 frozen fields)
│   ├── enums.py          Period, RoutineType, HabitCategory, PolicyState …
│   ├── types.py          NewType, Protocol, TypeAlias
│   ├── exceptions.py     10 PAV error codes
│   ├── entities/         11 Pydantic v2 models (frozen, extra=forbid)
│   ├── core/             Pure arithmetic — no I/O, no Rich, no Typer
│   │   ├── habit_engine.py   H(t)=1−e^(−λ·streak), E=R·(1−H(t)), Q_HE
│   │   ├── policy_engine.py   4-state FSM: PUSH→MAINTAIN→REDUCE→RECOVER
│   │   ├── pomodoro_machine.py  8-state SM + scenario classifier
│   │   ├── sleep_calculator.py  sleep window validation
│   │   └── consolidator.py  daily/weekly rollups
│   ├── persistence/      Repository Protocol + InMemory + SQLite
│   ├── parsers/         YAML frontmatter → Pydantic
│   └── reports/          Markdown daily/weekly narrative generators
│
├── apps/cli/src/operational/cli/
│   ├── app.py           12 sub-typers (routine, block, journal, habit…)
│   ├── home_v2.py      interactive 10-item menu
│   ├── state.py         14 _PersistentRepo (JSON flat files)
│   ├── csv_loader.py
│   └── commands/        one file per subcommand group
│
├── apps/tui/src/operational/tui/
│   ├── app.py           PAVApp — 7 screens + BINDINGS
│   ├── theme.py         get_tui_theme()
│   ├── charts.py        plotext chart renderers
│   └── screens/         dashboard · daily_flow · habits · journal · metrics · pomodoro · policy
│
└── tests/               2518 pytest tests (unit/integration/property/e2e)
```

**Core algorithms (pure arithmetic, zero LLM):**

| Algorithm | Formula | File |
|-----------|---------|------|
| Habit consistency | `H(t) = 1 − e^(−λ·streak)` | `habit_engine.py` |
| Energy required | `E = R·(1 − H(t))` | `habit_engine.py` |
| Q_HE composite | weighted composite of H, E, streak | `habit_engine.py` |
| PolicyEngine FSM | 4 states + hysteresis | `policy_engine.py` |
| Pomodoro SM | 8 states + scenario classifier | `pomodoro_machine.py` |

**CLI entry points** (all equivalent): `pav`, `pav-os`, `operational`

**TUI screens**: `pav screen <dashboard|daily_flow|habits|journal|metrics|pomodoro|policy>`

---

## vibe-ops/ — Cybernetic Data-Mesh

Target-Sensor-Adjuster loop: `TARGET → SENSOR → ADJUSTER → PERSIST → SYNC → INDEX`

```
src/
├── main.py              argparse CLI: run-daily, status, gaps, sync
├── vibe_cli.py         Typer+Rich CLI: sync_file, hybrid_search, gaps
├── cybernetics/         daily_loop.py (Target-Sensor-Adjuster loop)
├── middleware/          sync_engine.py (Obsidian ↔ SQLite ↔ Taskwarrior)
├── pipeline/            ~30 modules: policy_engine, ikigai_scorer, rag_indexer…
├── models/              14 Pydantic entity modules
├── storage/             SQLite + ChromaDB + sqlite-vec + UEID manager
├── contracts/           YAML + Pydantic sync contracts
├── embeddings/          OpenAI / local / hash provider abstraction
└── vibeops-tui/         Rust TUI (ratatui) — polls vibe_ops.db
```

**PolicyEngine states:**

| State | hardwork_budget | pause_min | sleep_target | Q_HE target |
|-------|----------------|-----------|--------------|-------------|
| PUSH | 4.0 h | 10 min | 7.5 h | 0.85 |
| MAINTAIN | 2.5 h | 15 min | 8.0 h | 0.65 |
| REDUCE | 1.5 h | 20 min | 8.5 h | 0.45 |
| RECOVER | 0.5 h | 30 min | 9.0 h | 0.25 |

---

## 3 Operational Clusters

Each cluster is a **Standalone Memory Machine** (self-contained, cross-referenced):

| Cluster | Canonical Doc | Focus |
|---------|--------------|-------|
| **PLAN** | `CLUSTER_PLAN.md` | Routines, habits, Q_HE, daily/weekly rhythm |
| **PROJECT** | `CLUSTER_PROJ.md` | PMO ↔ Taskwarrior, roadmap, changelog |
| **STUDIES** | `CLUSTER_STUDY.md` | PKM, prerequisites graph, cognitive debt |

Meta-brain: **IKIGAi** — 5 vectors (Passion, Skill, Market, Revenue, Course),
governs all 3 clusters. Implemented across `vibe-ops/base/IKIGAi.md` (conceptual)
and `life-ops/planner/ikigai_planning/` (AI-native drilldown).

---

## Directory Tree

```
life/                              # Root — CLI hub orchestrator
├── README.md                      # You are here
├── CLAUDE.md                      # Claude Code guidance
├── AGENTS.md                      # AI agent rules
├── ARCHITECTURE_INDEX.md          # Master architecture index (50+ cross-refs)
├── CONCEPTUAL_MODEL.md            # T→B→S framework, 5 tensions, 4 regimes
├── SYSTEMS_TOPOLOGY.md             # Middleware map M1-M8, cybernetic loop
├── CLUSTER_PLAN.md                 # Cluster 1 — Standalone Memory Machine
├── CLUSTER_PROJ.md                # Cluster 2 — Standalone Memory Machine
├── CLUSTER_STUDY.md               # Cluster 3 — Standalone Memory Machine
│
├── life-ops/                      # Python planning subsystem
│   ├── operational/               # ★ ACTIVE DEV — PAV productivity kernel (uv workspace)
│   │   ├── packages/core/         # Pure domain logic, zero I/O
│   │   ├── apps/cli/              # Typer CLI (pav, pav-os, operational)
│   │   └── apps/tui/              # Textual TUI (7 screens)
│   ├── life_tatics/               # Standalone time-block planner (Poetry)
│   ├── planner/                   # IKIGAi drilldown + mathematical specs
│   │   └── ikigai_planning/       # 5 docs on IKIGAi vectors, propagation, heuristics
│   └── pyproject.toml             # Poetry workspace
│
├── vibe-ops/                      # Cybernetic data-mesh subsystem
│   ├── src/                       # Python: pipeline, models, storage, middleware
│   ├── vibeops-tui/               # Rust TUI (ratatui) — polls SQLite
│   ├── planning/                  # 7 PRDs + 5 CLUSTER_PLAN drilldowns
│   ├── specs/                     # Engineering schemas (Pydantic v2)
│   ├── architecture/              # 5 ADRs (decisions registered)
│   ├── base/                      # IKIGAi.md (90K), PAV visual (815K)
│   └── vectors/                   # 4 IKIGAi vector docs
│
├── strategics/                    # PT-BR strategic prose (9 frameworks)
├── docs/                          # Master reading index + SPEC + DEPLOY
├── diagrams/                      # 6 Mermaid PNGs + source .mmd files
├── taskwarrior/                   # TW binary + scripts + config + 7 docs
├── handlers/                      # daily.py, weekly.py (orchestrators)
├── centrals/                      # task · finance · knowledge · research
├── plugins/                      # Plugin discovery + builtin/health_check
├── cli/                           # LifeConfig, structured logging, test runner
└── logs/                          # Runtime stdout/stderr
```

---

## Global Conventions

| Rule | Description |
|------|-------------|
| **Append-only** | Never delete files in `vibe-ops/`, `strategics/`. Re-organize only if every pre-existing string survives intact. |
| **Standalone decoupled** | `life-ops/operational/` imports nothing from `life/` or `vibe-ops/`. |
| **Zero LLM in pipeline** | Daily/weekly pipelines are purely arithmetic — no NLP, no LLM calls. |
| **--json on all CLIs** | Every new CLI command must support `--json` for machine-readable output. |
| **Pydantic v2** | All data schemas: `frozen=True`, `extra="forbid"`, strict mode. |
| **Idempotency** | All pipelines are re-executable without duplicating data (keys: `upstream_id`, `ueid`). |
| **Fully local** | Zero cloud dependencies. SQLite + filesystem only. |
| **PT-BR ↔ EN split** | Strategic prose in Portuguese; code, file names, and AI-native specs in English. |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Tests (`operational/`) | **2518** pytest (unit/integration/property/e2e) |
| Pydantic entities | 11 in `operational/`, 14 in `vibe-ops/` |
| State machines | 4 (PolicyEngine FSM) + 8 (Pomodoro) + 14 (total) |
| ADRs | 5 (architecture decisions) |
| PRDs | 7 (product requirements) |
| Cluster docs | 3 (PLAN, PROJ, STUDY) |
| Mermaid diagrams | 6 rendered PNGs |

---

## Entry Points by Persona

| Persona | Start Here |
|---------|-----------|
| Human wanting to understand the system | `ARCHITECTURE_INDEX.md` → cluster doc of interest |
| Human wanting to use the CLI | `life-ops/operational/README.md` → `pav --help` |
| AI agent implementing a feature | `AGENTS.md` → relevant `CLUSTER_*.md` → PRD → code |
| AI agent auditing gaps | `ARCHITECTURE_INDEX.md §7` (IKIGAi gap analysis) |

---

*Algorithmic Life OS — Root README — 2026-06-22*
