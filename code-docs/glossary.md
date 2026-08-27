# Glossary — Algorithmic Life OS

> **Canonical terms** used across the Algorithmic Life OS. Each entry has a
> short definition, a code reference, and links to deeper docs. Append-only —
> terms are added, never removed.
>
> **Status:** 🟡 Draft — 2026-08-27

---

## A

### Adjuster
The third stage of the cybernetic Target→Sensor→Adjuster→Persist→Sync→Index
loop. Takes the sensor reading and computes an action (usually a policy
state transition). See `vibe-ops/src/cybernetics/daily_loop.py`.

### AI-native Strategic Model
The 2026-08-26 architecture migration: PAV TUI/CLI deprecated, IKIGAI becomes
a strategic template with MCP contracts consumed by external apps (Claude
Code, Obsidian, etc.). See
`docs/superpowers/specs/2026-08-26-ai-native-strategic-model.md`.

### Append-only Rule
Global convention: `vibe-ops/`, `strategics/`, and cluster docs may never be
deleted. Reorganization allowed only if every pre-existing string survives
byte-for-byte. See `life/CLAUDE.md §Global Conventions`.

### Architecture Decision Record (ADR)
Immutable record of a decision: Status, Date, Context, Decision,
Consequences, Alternatives, Implementation Rules. Lives in
`vibe-ops/architecture/` (cybernetic), `life-ops/operational/docs/adr/`
(PAV kernel), or `code-docs/adr/` (cross-cutting).

---

## B

### B1 Blocker
A vault-level flag marking a planning/decision gap. Currently divergent
between vault (says RESOLVED), taskdog #10 (PENDING), and tuiboard B1
(PENDING). See master diagnostic H4.

### Branch Strategy
`gitbutler/workspace` is the active integration branch. `master` is the
default for PRs. Worktrees live in `life-ops/*-worktree/`. See
`life/CLAUDE.md §Claude Code-Specific Operations`.

### Build/Test Gate
Per-package CI matrix: `ruff check`, `ruff format --check`, `mypy src/`,
`pytest -m "not e2e"`. See `.github/workflows/ci.yml`.

---

## C

### Canonical Source of Truth (SoT)
The Markdown vault at `data/matheus/` is canonical for IKIGAI entities. The
SQLite mirror is derived; it must reconcile to the vault via
`SQLiteAdapter.upsert()`. See
`life-ops/ikigai/src/ikigai/propagation/markdown_db.py`.

### Circuit Breaker (CB)
Reliability pattern: outer @circuit_breaker + inner @retry_with_backoff.
CB counts logical calls, not attempts. See `src/agents/tools.py:87f6ef9`.

### Cluster
Top-level planning domain. Three canonical clusters: PLAN (routines, habits,
Q_HE), PROJECT (PMO, roadmap), STUDIES (PKM, prerequisites). See
`CLUSTER_PLAN.md`, `CLUSTER_PROJ.md`, `CLUSTER_STUDY.md`.

### CorrectionSignal
Heuristic flag emitted by the heuristics node in the IKIGAI maintainer
LangGraph. Six signal types: H1-H6 (energy/sleep/pomodoro/policy/etc.
heuristic violations). See `src/agents/ikigai_maintainer/graph.py`.

### Cross-Cluster Dependency
Two clusters share a UEID lineage (e.g., a Project UEID in PROJECT cluster
links to a Goal UEID in PLAN cluster). See UEID format below.

---

## D

### Data-First Methodology
ADR-007: pivot to manual templates first, code emerges from 5+ observed
manual logs. No new entity types until workflow proven. See
`code-docs/adr/ADR-007-data-first-methodology.md`.

### Drift
Mismatch between two data layers (e.g., markdown vault vs SQLite mirror).
`Triagem` detects drift via mtime comparison. See
`life-ops/ikigai/src/ikigai/propagation/triagem.py`.

---

## E

### Entity
A Pydantic v2 model in `life-ops/ikigai/src/ikigai/entities/`. Should be
`frozen=True, extra="forbid", strict=True` per CLAUDE.md invariant (see
ADR-009 — currently violated across most entities).

### External MCP Server
3 third-party MCP servers: tuiboard (TS/Bun), taskdog (Python FastMCP),
solverforge-calendar (Rust rmcp). All 3 currently have observability
branches pending merge. See master diagnostic §4.

---

## F

### Fractal Regime
A regime (PUSH/MAINTAIN/REDUCE/RECOVER) that recurs at every level of the
hierarchy (global → cluster → vector → sub-vector) with hysteresis. See
`vibe-ops/specs/SPEC-05-cybernetic-mesh.md`.

### Frontmatter Contract
YAML frontmatter on every markdown entity. Required fields: `ueid`,
`entity_type`, `slug`, `title`, `status`, `created_at`, `updated_at`,
`source`, `ikigai_vectors`, `vector_weights_snapshot`, `tags`, `mtime`.
See `vibe-ops/specs/schema-frontmatter-contract-v2.md`.

---

## G

### Geofencing (none in this repo)
Not implemented. Out of scope per CLAUDE.md §Fully local.

### GitButler
Tool managing virtual branches on top of `gitbutler/workspace`. The
integration branch is `gitbutler/workspace`; `master` is the default for
PRs.

### Goal Hierarchy
dream → goal → objective → project → task → deliverable. Each level has
its own status enum, horizon (days), and Pydantic entity. See
`life-ops/ikigai/src/ikigai/entities/plan/`.

---

## H

### Hysteresis
A regime state transition requires sustained performance to promote upward.
Prevents oscillation. See `vibe-ops/src/pipeline/policy_engine.py`.

### Habit Consistency
`H(t) = 1 − e^(−λ·streak)` — exponential approach to 1.0 as streak grows.
See `life-ops/operational/packages/core/src/operational/core/habit_engine.py`.

### Horizon (days)
Maximum expected duration for an entity at its level. Dreams: 547-3650d.
Goals: 365-1095d. Objectives: 90-365d. Projects: 30-180d. Tasks: 1-7d.
Deliverables: 1-30d. See entity definitions in
`life-ops/ikigai/src/ikigai/entities/plan/`.

---

## I

### Idempotency Key
`upstream_id` (SHA-256) for sync payloads, `ueid` (UEID format) for
entities. All writers must use these keys to ensure re-execution doesn't
duplicate. See master diagnostic §1 S-M2 for migration runner.

### IKIGAI
The meta-brain. 5 vectors: Passion, Skill, Market, Revenue, Course
(contested — see ADR-008). 4 regimes: PUSH/MAINTAIN/REDUCE/RECOVER. 5
phases: FUNDAÇÃO/BUSCA/HACKATHON/RECUPERACAO/OVERCLOCK.

### IKIGAI Maintainer
The LangGraph chain (8 nodes: observe → score_vectors → heuristics →
balance → decompose → plan → reflect → commit). Writes to
`~/.ikigai/plan_entities.db` and `~/.ikigai/vault/cycle-*.md`. See
`src/agents/ikigai_maintainer/graph.py`.

### Interruption
HITL gate in deep agents. Currently only `write_file` is gated; ADR
proposes expanding to 6+ mutation tools. See master diagnostic S-H4.

---

## J

### JSON-RPC 2.0
Protocol used by all MCP servers. tuiboard hand-rolls; taskdog uses
FastMCP; solverforge uses rmcp. IKIGAI uses raw `mcp.server.Server` (no
SDK). See `src/mcp_server/server.py`.

---

## K

### Kill Switch
Boolean state in `IKIGAiStateDict` (`kill_switch_triggered`, `terminated`)
that short-circuits the maintainer graph. See
`src/agents/ikigai_maintainer/state.py:107-168`.

---

## L

### LangGraph
Framework for stateful multi-actor apps. Used by `ikigai_maintainer`
(8-node chain), `pae_maintainer` (vibe-ops), and 4 other graphs
registered in `langgraph.json`.

### Local-First
CLAUDE.md invariant: no cloud deps, no API keys, no OAuth. SQLite +
filesystem only. See `life/CLAUDE.md §Global Conventions`.

---

## M

### Markdown Vault
Canonical SoT at `data/matheus/` (subdirs: `dreams/`, `objectives/`,
`projects/`, `deliverables/`, `ikigai_state/`). Each file is a markdown
note with YAML frontmatter.

### MCP Server
Model Context Protocol server. Exposes tools to clients via stdio (or
HTTP+SSE — see ADR-011). IKIGAI exposes 8 tools.

### Meta-Vector Score
Composite of the 5 IKIGAI vector scores via weighted geometric mean +
harmonic mean. See `vibe-ops/src/pipeline/ikigai_scorer.py`.

### Migrate (entity level)
A `RegimeOverride` action that promotes a regime state without hysteresis
compliance. Audit-tracked. See
`life-ops/ikigai/src/ikigai/entities/regime.py`.

### Migration (data level)
Schema migration from one version to another. Currently no migrations
runner exists; only `CREATE TABLE IF NOT EXISTS`. See master diagnostic
S-M2.

---

## N

### Node
A function in a LangGraph graph. Receives state, returns state delta. The
ikigai_maintainer has 8 nodes (see IKIGAI Maintainer above).

---

## O

### Observability
OpenTelemetry wiring: LangSmith OTLP/HTTP + Langfuse OTLP/HTTP (single
SDK, two exporters). Auto-instrumentation for langchain, requests, sqlite3,
logging. Manual spans: `ikigai.make_agent`, `ikigai.run_chat.error`,
`ikigai.graph.compile`. See `src/observability/otel_init.py`.

### Onda (Wave)
A planning period between trimestral and semanal. ~3-4 weeks. Has its own
template (`vibe-ops/planning/_templates_periodos_v2/03-onda.md`).

### OpenTelemetry (OTel)
Industry-standard tracing spec. IKIGAI uses OTLP/HTTP for both exporters.
See observability sprint status (`docs/.sdd-progress.md`).

### Override
A `RegimeOverride` event that changes the current regime without
hysteresis. Logged for audit. See ADR for override policy.

---

## P

### PAV Kernel
`life-ops/operational/` — the productivity kernel (uv workspace).
Currently RESTORING (CLI broken post-`604d6af`). See master diagnostic §3.

### Phase
IKIGAI 5-phase cycle: FUNDAÇÃO (foundation) → BUSCA (search) →
HACKATHON (build) → RECUPERACAO (recovery) → OVERCLOCK (sprint). Has
its own FSM with convergence.

### PlanEntity
The base polymorphic entity for all plan hierarchy levels (Dream through
Deliverable). Defines the common fields. See
`life-ops/ikigai/src/ikigai/entities/base.py`.

### PolicyEngine FSM
4-state finite state machine: PUSH → MAINTAIN → REDUCE → RECOVER. Each
state has a hardwork_budget, pause_min, sleep_target, Q_HE target. See
`vibe-ops/src/pipeline/policy_engine.py`.

### Prospectives Buffer
Channel in `IKIGAiStateDict` that accumulates planned actions during a
cycle. Emptied at commit.

---

## Q

### Q_HE
Composite score combining habit consistency, energy required, and streak
weight. Target values per regime: PUSH 0.85, MAINTAIN 0.65, REDUCE 0.45,
RECOVER 0.25.

---

## R

### RAG (Retrieval-Augmented Generation)
Hybrid: SQLite (lexical) + ChromaDB (semantic) + sqlite-vec (vector).
3 providers: OpenAI / local / hash-moq. See ADR-004 (Hybrid RAG
Strategy).

### Regime
One of 4: PUSH, MAINTAIN, REDUCE, RECOVER. Has hysteresis (no upward
promotion without sustained performance).

### Resilience
Reliability pattern: retry + backoff + circuit breaker. See IKIGAI
`src/agents/tools.py` and observability sprint Spec 01.

### Retrospective Log
Channel in `IKIGAiStateDict` that accumulates past cycle outcomes. Used
by reflect node.

### Root CLAUDE.md
The monorepo-level CLAUDE.md at `C:\Users\mathe\code_space\life-oss\CLAUDE.md`.
See ADR-010 (dual CLAUDE.md scope strategy).

---

## S

### Schema Split-Brain
The canonical 24-col `plan_entities` table is never written to; the
runtime 11-col table is written by every commit. Drift is permanent.
See master diagnostic S-C1 and migration MIG-1.

### ScoreValue
`{value: float, unit: Literal[percent|ratio|raw|index|currency_brl|hours]}`.
Every score has a unit. See `life-ops/ikigai/src/ikigai/types.py`.

### Singleton Graph
The `make_ikigai_graph()` function returns a module-level singleton
(once compiled). Two callers currently create their own: `server.py:317`
+ `tools.py:269` — see master diagnostic H5.

### SQLite Adapter
The class that reconciles the markdown vault to the canonical 24-col
SQLite table. Currently never called by writers. See
`life-ops/ikigai/src/ikigai/propagation/sqlite_adapter.py`.

### Standalone Memory Machine
A cluster is "self-contained, cross-referenced" — all knowledge of one
domain lives in one cluster doc + its subdocs.

### Sync Engine
The chokepoint bridging Obsidian ↔ SQLite ↔ Taskwarrior. UEID-based
keys, idempotent. See
`vibe-ops/src/middleware/sync_engine.py`.

---

## T

### Taskdog
External MCP server (Python FastMCP). `apps/dev-tools/taskdog/`. IKIGAI
currently uses CLI subprocess instead of MCP (see master diagnostic S-C3).
Has `feat/otel-tracing` branch pending merge.

### Template (period)
One of 9 markdown templates at
`vibe-ops/planning/_templates_periodos_v2/`: sonho, trimestral, onda,
semanal, diário, quarterly planning, quarterly review, sprint kickoff,
sprint retrospective. See master diagnostic `00-INDEX.md §4`.

### Triagem
The drift detector. Compares mtime between markdown and SQLite, writes
`meta/triagem.md` with 4 categories. See
`life-ops/ikigai/src/ikigai/propagation/triagem.py`.

### TUI
Textual-based UI in `life-ops/operational/apps/tui/`. Currently
read-only (mutation delegated to CLI). Per the AI-native migration
(2026-08-26), TUI is deprecated for deletion; future surface is MCP
contracts only.

### tuiboard
External MCP server (TypeScript/Bun). `apps/kanban/tuiboard/`. Has
`feat/otel-tracing` branch pending merge.

---

## U

### UEID
Universal Entity Identifier. Format: `<CLUSTER>:<ENTITY>:<ID>` (5-part
validator — see master diagnostic §1.1 C4 collision). E.g.,
`study:topic:st_python_01`. Implemented in
`life-ops/ikigai/src/ikigai/types.py` with regex validation.

### Uptime Target
Implicit 100% (single-user, local-first). Down = no work happens.

### User Discipline
Per ADR-007: the user manually logs in templates. No tooling gently
reminds. Attention is the engine.

---

## V

### Vector (IKIGAI)
One of 5 (or 4 — see ADR-008): passion, skill, market, revenue, course.
Each has a 0.0-1.0 score, weight in meta-vector, and snapshot history.

### Vibe-ops
The cybernetic engine at `vibe-ops/`. Target-Sensor-Adjuster loop. 17
Pydantic entity modules. See `life/CLAUDE.md §vibe-ops`.

---

## W

### Worktree
Git worktree under `life-ops/*-worktree/` (e.g.,
`life-mcp-observability-worktree/`) or under `apps/*/` for external
repos. Isolated working copy on a separate branch. See
`life/CLAUDE.md §Claude Code-Specific Operations`.

---

## X

(no entries yet)

---

## Y

(no entries yet)

---

## Z

(no entries yet)

---

## Cross-Reference Index

| Term | Canonical source | ADR / spec |
|------|------------------|------------|
| Data-First Methodology | ADR-007 | ADR-007 |
| IKIGAI Vector Count | ADR-008 | ADR-008 |
| Pydantic Strict Mode | ADR-009 | ADR-009 |
| Dual CLAUDE.md Scope | ADR-010 | ADR-010 |
| HTTP+SSE Transport | ADR-011 | ADR-011 |
| AI-native Strategic Model | spec 2026-08-26 | spec |
| Data Flow Topology | ADR-001 | ADR-001 |
| Mesh Contracts | ADR-002 | ADR-002 |
| IKIGAI as Meta-Brain | ADR-003 | ADR-003 |
| Hybrid RAG | ADR-004 | ADR-004 |
| Data Mesh Topology | ADR-005 | ADR-005 |
| Period Reports Schema | ADR-006 | ADR-006 |

---

*Glossary — v1.0 — 2026-08-27 — append-only*
