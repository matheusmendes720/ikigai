# IKIGAi — Master Navigation Index

> **One file, all roads in.** The Algorithmic Life OS is a personal productivity
> orchestration system — 100% local, single-user, append-only, zero LLM in the
> hot path, pure arithmetic only. This index points at every planning artifact
> (PRDs, BRDs, ARDs, ADRs, Specs, Templates, Drafts, Plans, Evidence) without
> duplicating their content. All paths are absolute Windows paths.

---

## 1. Quick nav — the 10 most important links

| # | What | Path |
|---|------|------|
| 1 | Root README — TL;DR + subsystem map | `C:\Users\mathe\code_space\life-oss\life\README.md` |
| 2 | Claude Code guidance (load-bearing invariants) | `C:\Users\mathe\code_space\life-oss\life\CLAUDE.md` |
| 3 | Codex guidance (parallel view) | `C:\Users\mathe\code_space\life-oss\life\AGENTS.md` |
| 4 | Master architecture index (50+ cross-refs) | `C:\Users\mathe\code_space\life-oss\life\ARCHITECTURE_INDEX.md` |
| 5 | PAV kernel CLAUDE.md (active dev target) | `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\CLAUDE.md` |
| 6 | code-docs root (PRD/BRD/ARD/ADR) | `C:\Users\mathe\code_space\life-oss\life\code-docs\README.md` |
| 7 | Planning templates folder (9 period templates) | `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\_templates_periodos_v2\` |
| 8 | ADRs — vibe-ops architecture (6 ADRs) | `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\` |
| 9 | Cluster PLAN — routines, habits, Q_HE | `C:\Users\mathe\code_space\life-oss\life\CLUSTER_PLAN.md` |
| 10 | System topology — middleware M1–M8 | `C:\Users\mathe\code_space\life-oss\life\SYSTEMS_TOPOLOGY.md` |

---

## 2. By subsystem

The repo has three subsystems, one kernel. Use this section to jump to the
canonical docs for each.

| Subsystem | Canonical entry point | Status | PM |
|-----------|----------------------|--------|-----|
| **Root CLI hub** (`life/`) — Typer centrals + daily/weekly handlers + plugins | `C:\Users\mathe\code_space\life-oss\life\cli\cli.py` | 🟡 Stable | — |
| **PAV productivity kernel** (`life-ops/operational/`) | `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\CLAUDE.md` | 🟢 Active | uv workspace |
| **Cybernetic engine** (`vibe-ops/`) | `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\README.md` | 🟡 Stable | uv |
| **Standalone time planner** (`life-ops/life_tatics/`) | `C:\Users\mathe\code_space\life-oss\life\life-ops\life_tatics\` | 🟡 Stable | Poetry |
| **Strategic prose** (`strategics/`, PT-BR) | `C:\Users\mathe\code_space\life-oss\life\strategics\00-ÍNDICE-PROGRESSIVO.md` | 🟢 Read-only | — |
| **Taskwarrior integration** (`taskwarrior/`) | `C:\Users\mathe\code_space\life-oss\life\taskwarrior\` | 🟢 Stable | — |

**Key invariants** (re-read before any non-trivial edit — see `CLAUDE.md`):
- **Standalone** — `life-ops/operational/` imports nothing from `life/` or `vibe-ops/`.
- **Append-only** — never delete from `vibe-ops/`, `strategics/`, cluster docs.
- **Zero LLM** — daily/weekly pipelines are pure arithmetic.
- **`--json` everywhere** — every new CLI command must support machine-readable output.
- **Pydantic v2 strict** — `frozen=True`, `extra="forbid"`, strict mode.

---

## 3. By phase

Roadmaps organize work in four phases. This section maps each phase to the
artifacts that drive it.

| Phase | Purpose | Authoritative source | Output goes to |
|-------|---------|----------------------|----------------|
| **0. Templates** | Period scaffold (sonho → onda → weekly → daily) | `vibe-ops/planning/_templates_periodos_v2/` | New planning notes |
| **1. Drafts** | Working notes / open questions / proposals | `.omo/drafts/*.md` | Specs or Plans |
| **2. Plans** | Sequenced task breakdowns with status | `.omo/plans/*.md` | Code (PRs) |
| **3. Evidence** | Trajectory / research notes from execution | `.omo/evidence/*.md` | Specs / ADRs |
| **4. Specs** | Schemas + PRDs + cluster specs (canonical) | `vibe-ops/specs/`, `vibe-ops/planning/PRD-*` | Code |
| **5. ADRs** | Architecture decisions (immutable once Aceita) | `vibe-ops/architecture/ADR-*.md` | Architectural baseline |

---

## 4. Templates index — `vibe-ops/planning/_templates_periodos_v2/`

All 9 period templates share the same frontmatter schema (`type: period_report`,
`period`, `ikigai_cluster`, `ikigai_vector`, `verdict`, `verdict_score`).
Hierarchy: **sonho → quarterly-planning → onda → weekly → daily**.

| File | Period | Sections | Verdict field | IKIGAi vector field |
|------|--------|---------:|:-------------:|:-------------------:|
| `00-quartely-planning.md` | quarterly | 11 | ✓ | ✓ |
| `01-sonho.md` | dream (sonho) | 11 | ✓ | ✓ |
| `02-avaliacao-trimestral.md` | quarterly review | 11 | ✓ | ✓ |
| `03-onda.md` | wave (onda) | 10 | ✓ | ✓ |
| `04-revisao-semanal.md` | weekly | 11 | ✓ | ✓ |
| `05-relatorio-diario.md` | daily | 11 | ✓ | ✓ |
| `06-quartely-review.md` | quarterly | 9 | ✓ | ✓ |
| `07-sprint-kickoff.md` | sprint | 9 | ✓ | ✓ |
| `08-sprint-retrospective.md` | sprint retro | 9 | ✓ | ✓ |
| `RELEASE-NOTES.md` | release | 4 | ✓ | — |

Base path: `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\_templates_periodos_v2\`

---

## 5. Drafts index — `.omo/drafts/`

Working notes and open proposals. Closed drafts = historical record (do not edit).

| File | Lines | Bytes | Status | One-line summary |
|------|------:|------:|--------|------------------|
| `agentic-markdown-system-completion.md` | 285 | 17 039 | CLOSED 19/19 | PAV/PAE planning-with-files system — all tasks complete |
| `ikigai-as-dom-on-planning-engine.md` | 278 | 12 163 | DRAFT (open) | Proposal: IKIGAi as DOM layer over planning-with-files engine |
| `vault-bidirectional-sync-completion.md` | 115 | 6 377 | CLOSED 13/13 + 4/4 reviews | Obsidian ↔ vibe-ops sync — complete with reviews |

Base path: `C:\Users\mathe\code_space\life-oss\life\.omo\drafts\`

---

## 6. Plans index — `.omo/plans/`

Sequenced task breakdowns. Status is shown in the frontmatter / top banner of each file.

| File | Lines | Status | Focus |
|------|------:|--------|-------|
| `agentic-markdown-system.md` | 503 | CLOSED | Planning-with-files adoption (system + tools) |
| `pav-tui-textualize.md` | 1 252 | ACTIVE (in progress) | Migrate PAV kernel UI from Rich home-menu to Textual TUI |
| `period-reports-sync.md` | 753 | CLOSED 10/10 | Wire period-report templates ↔ data flow (10 tasks) |
| `vault-bidirectional-sync.md` | 924 | CLOSED 13/13 | Obsidian ↔ SQLite ↔ Taskwarrior idempotent sync |

Base path: `C:\Users\mathe\code_space\life-oss\life\.omo\plans\`

---

## 7. ADRs index

Two ADR surfaces: the **cybernetic engine** (`vibe-ops/architecture/`) and the
**PAV kernel** (`life-ops/operational/docs/adr/`, 13+ docs). Plus a small local
set in `code-docs/adr/`.

### 7a. `vibe-ops/architecture/` — cybernetic engine ADRs

| ADR | Title | Status | Date |
|-----|-------|:------:|------|
| ADR-001 | Data Flow Topology | Aceita | 2026-05-03 |
| ADR-002 | Mesh Contracts & State Machines | Aceita | 2026-06-05 |
| ADR-003 | IKIGAi as Meta-Brain | Proposta | 2026-06-05 |
| ADR-004 | Hybrid RAG Strategy | Proposta | 2026-06-05 |
| ADR-005 | Data Mesh Topology | Proposta | 2026-06-05 |
| ADR-006 | Period Reports Schema | Aceita | 2026-06-26 |

Base path: `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\`
Index: `C:\Users\mathe\code_space\life-oss\life\vibe-ops\architecture\README.md`

### 7b. `code-docs/adr/` — local ADRs

| File | Status | Purpose |
|------|:------:|---------|
| `README.md` | index | Master index for code-docs/adr/ (ADR 007-011 + 3 draft support docs + 2 surface pointers) |
| `ADR-007-data-first-methodology.md` | Accepted (2026-07-02) | Data-first methodology: schema → storage → adapters |
| `OPERATIONAL.md` | index | Pointer to PAV kernel ADR set (see § 7c) |
| `VIBE-OPS.md` | index | Pointer to cybernetic engine ADR set (see § 7a) |

Base path: `C:\Users\mathe\code_space\life-oss\life\code-docs\adr\`
Full table (incl. drafts): see `code-docs/adr/README.md`.

### 7c. `life-ops/operational/docs/adr/` — PAV kernel ADRs (13+)

13+ architecture decision records for the PAV kernel (TUI migration, data
model, persistence, design system, etc.). See the in-folder index for the
full table. Base path:
`C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\adr\`

---

## 8. Specs & PRDs index

### 8a. PRDs — `vibe-ops/planning/PRD-*.md`

| PRD | Title | Domain |
|-----|-------|--------|
| PRD-01 | (see file) | (see file) |
| PRD-02 | Habit Tracker | Habits + Q_HE scoring |
| PRD-03 | (see file) | (see file) |
| PRD-04 | (see file) | (see file) |
| PRD-05 | Metrics & Health | Sleep / energy / recovery |
| PRD-06 | (see file) | (see file) |
| PRD-07 | IKIGAi (4 vectors) | Meta-brain — Passion / Skill / Market / Revenue |

Base path: `C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\`
Each PRD has a mirror in `code-docs/prd/` (per `code-docs\prd\README.md`).

### 8b. Specs — `vibe-ops/specs/`

17 spec files: SPEC-05 cybernetic mesh, schema-frontmatter-contract v2,
schema-pydantic-models v2, schema-planner-extension, spec-cluster-plan-{01..03},
prd-{01..07} mirrors, README. Base path:
`C:\Users\mathe\code_space\life-oss\life\vibe-ops\specs\`

### 8c. BRDs — `vibe-ops/planning/CLUSTER_PLAN_*.md`

| File | Type |
|------|------|
| `CLUSTER_PLAN_BRD.md` | Business requirements |
| `CLUSTER_PLAN_USER_STORIES.md` | User stories |
| `CLUSTER_PLAN_CLI_SPEC.md` | CLI surface spec |
| `CLUSTER_PLAN_ROADMAP.md` | Roadmap |
| `CLUSTER_PLAN_DATA_MODEL.md` | Data model |
| `CLUSTER_PLAN_CHECKPOINT.md` | Status snapshot |

### 8e. Observability specs — `life-ops/ikigai/docs/observability/`

4 follow-up specs for the observability sprint (committed in `1d9479a`).

| Spec | File | Subject |
|------|------|---------|
| 01 | `01-server-side-reliability.md` | Mirror IKIGAI's client-side retry + CB pattern onto the 3 external MCP servers (tuiboard, taskdog, solverforge) |
| 02 | `02-integration-smoke-test.md` | `pav smoke observability` — boot all 4 servers with `OTEL_ENABLED=true`, verify spans in LangSmith + Langfuse |
| 03 | `03-merge-plan.md` | Dependency-ordered merge procedure for the 4 OTel feature branches back to default branches |
| 04 | `04-dissolve-worktree.md` | Cleanup steps for `life-mcp-observability-worktree` once the IKIGAI merge lands |

### 8f. Backend deep-dive report — `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md`

411-line audit of the IKIGAI meta-brain backend (committed `48abd81`, 2026-08-26).
**19 issues across 4 severities** — actionable backlog, all fixes target the
`feat/mcp-observability` branch in `life-ops/life-mcp-observability-worktree/`.

| Severity | Count | Examples |
|----------|------:|----------|
| **CRITICAL** | 5 | Missing `/tmp/ikigai-test/` Python env (`mcp_config.json:4`); `_read_entity` name collision (`server.py:207-239`); `_TASKDOG_CLI` Windows path on Linux host (`tools.py:910-912`) |
| **HIGH** | 6 | Dual LangGraph instances; B1 Blocker divergence between vault and interfaces; vault root mismatch (`tools.py:21`) |
| **MEDIUM** | 5 | tag truncation in taskdog CLI; grep-based JSON-RPC test in `start_mcp_gateway.sh:243-248`; SOLVERFORGE_ROOT WSL2 path inconsistency |
| **INFO** | 3 | LangGraph singleton module state; silent except in `server.py:367-368`; `_read_entity` fallback table |

Recommended priority order: **P0** (mkdir `~/.ikigai/`, `poetry install`, fix python path) → **P1** (platform-aware paths, vault root, name collision, B1 divergence) → **P2** (WSL2 path, error logging) → **P3** (port-aware CLI, JSON parsing, singleton graph).

Tracked as Tasks #12 (C1-C5), #13 (H1-H6), #14 (M1-M5), #15 (I1-I3) in the
session task list — queued for the observability sprint, **no code changes
this turn**.

### 8g. Master system diagnostic — `code-docs/diagnostic/`

Cross-cutting diagnostic of all 77 known issues across 5 subsystems
(IKIGAI + system architecture + PAV kernel + 3 external MCP servers + known
gaps). Aggregated 2026-08-27; **diagnostic + planning only, no code changes**.

| Severity | Count | Top blockers |
|----------|------:|--------------|
| **CRITICAL** | 10 | PAV CLI broken (`604d6af`); schema split-brain (24-col vs 11-col); dcode not connected to IKIGAI MCP |
| **HIGH** | 30 | `_MCP_SESSION_CACHE` never invalidated; no retry/CB; `interrupt_on` only gates `write_file`; OTel pending merge in 3 repos |
| **MEDIUM** | 24 | Hard-coded paths; tag truncation; grep-based JSON-RPC tests; orphan test dirs |
| **INFO** | 13 | Pydantic invariant violations; 3 integration patterns; 2 CLAUDE.md files |

Includes P0→P3 fix sequence (27 sequenced steps) and verification commands.
Pending constructions roadmap (A-J) lists 10 planned-but-not-implemented
features competing for engineering time. See `code-docs/diagnostic/README.md`
for the category index and severity legend.

**Companion docs** (all 7 produced in the 2026-08-27 diagnostic sprint):

| # | File | Purpose |
|--:|------|---------|
| 1 | `2026-08-27-master-system-diagnostic.md` | 77-issue master inventory (§0-§10) |
| 2 | `2026-08-27-issue-dependencies.md` | Sprint sequencing (27 steps, 4 sprints) |
| 3 | `2026-08-27-migration-scripts-catalog.md` | 8 migration specs (MIG-1..8) |
| 4 | `2026-08-27-risk-effort-matrix.md` | Risk × effort 4-quadrant positioning |
| 5 | `2026-08-27-error-catalog.md` | 18 declared IKIGAI error codes + tool map |
| 6 | `2026-08-27-pending-constructions-detail.md` | 10 mini-specs (A-J) with AC |
| 7 | `2026-08-27-github-issues-backlog.md` | 80 GitHub-ready issues with labels |
| 8 | `2026-08-27-test-coverage-strategy.md` | S-M4/M5/M6 test specs with code |
| 9 | `2026-08-27-pre-merge-checklist.md` | 4-repo observability merge procedure |
| 10 | `2026-08-27-architecture-diagrams.md` | 6 Mermaid diagrams (5 critical paths + bonus) |
| 11 | `2026-08-27-ikigai-bootstrap-runbook.md` | C1-C5 fix procedures + cold-start boot sequence |
| 12 | `2026-08-27-sprint1-implementation-plan.md` | 16 TDD tasks w/ failing test + minimal impl + verification |
| 13 | `2026-08-27-incident-response-runbook.md` | 13 INC-* runbooks (silent-failure modes from error catalog) |
| 14 | `2026-08-27-sprint1-diagrams.md` | 6 Mermaid diagrams (DAG, heatmap, TDD cycle, swim-lane, critical path, test pyramid) |
| 15 | `2026-08-28-test-integration-recovery.md` | 27-test integration gate analysis (RT-01..06 + PD-01..04 + SU-01..04 + OV-01..03 + FR-01..03 + SA-01..05 + PH-01 + PS-01); lands with C1-C5 merge |
| 16 | `2026-08-28-pav-kernel-fate-options.md` | 3-option analysis (recover / restart / retire); recommends Option C per AI-native spec |

### 8h. Observability dashboard design — `code-docs/observability/05-dashboard-design.md`

10 dashboards (6 LangSmith + 4 Langfuse) covering IKIGAI cycle health, tool
latency, LangGraph node distribution, external MCP server health, circuit
breaker / retry state, deep-agent conversations, tool selection, HITL
frequency, and cost per cycle. Includes SLOs, Prometheus-style alert
conditions, and an implementation plan across Sprints 17-21. Companion to
the 4 follow-up observability specs in `life-ops/ikigai/docs/observability/`.

### 8h.1 External MCP server OTel plan — `code-docs/observability/06-external-mcp-otel-plan.md`

Per-server implementation plan for wiring OpenTelemetry into the 3 external
MCP servers (tuiboard TS/Bun, taskdog Python/FastMCP, solverforge Rust/rmcp).
Covers SDK choice per language, init points, code stubs, migration sequence
(taskdog → tuiboard → solverforge), endpoint correctness audit, and
cardinality safeguards. Companion to `01-server-side-reliability.md`.
Flags taskdog typo'd LangSmith endpoint (`api.lansmith.com`) as P0 fix.

### 8i. Code-docs glossary — `code-docs/glossary.md`

50+ canonical terms (A-Z) with code references and ADR cross-links.
Cross-references 11 ADRs (ADR-001 through ADR-011) plus the AI-native
strategic model spec. Append-only.

### 8j. Pending-decision + ADR consolidation

Two companion docs that close the "Proposta ADRs awaiting user decision" gap
G3 of `00-INDEX §12.1`:

| File | Purpose |
|------|---------|
| `code-docs/adr/2026-08-27-decision-questionnaire.md` | 4 ADRs (008/009/010/011) reframed as decision questions with criteria, pre-mortem, reversibility, recommendation |
| `code-docs/adr/2026-08-27-master-adr-index.md` | Single table consolidating 11 cross-cutting ADRs + 6 cybernetic + ~13 PAV kernel across 3 surfaces, by status / surface / timeline |
| `code-docs/adr/2026-08-27-cross-cutting-triage.md` | Cross-cutting decision-dependency matrix for the 4 Proposta ADRs (008-011); recommended decision order |
| `code-docs/adr/2026-08-28-adr-008-011-decision-package.md` | Ready-for-sign-off decision package: 3 sub-options per ADR with file-change lists, tests-affected, user-workflow impact, reversibility, recommendation, pre-mortem, copy-paste sign-off template |
| `code-docs/adr/2026-08-28-adr-008-011-decision-package-appendix.md` | Deep-dive impact tables (per-ADR file changes), 10 open questions, 10 implementation gotchas, sprint sequencing, `scripts/check-pydantic-strict.py` sketch |

### 8k. Data-model unification specs — `code-docs/specs/`

Five sibling specs that define acceptance + migration for the `feat/data-model-unification`
branch (Task #42). Each spec follows the §0-§8 format with purpose, problem,
design, interface signatures, AC, migration, verification, and cross-references.
TDD methodology: failing test → minimal impl → verification.

| # | Spec | Subject |
|--:|------|---------|
| C1 | `2026-08-27-spec-C1-vault-canonical-writer.md` | `IKIGAiAgenticWriter` + `VaultLock` + `dict_to_frontmatter` — sole vault writer (replaces f-string at `tools.py:350-385`) |
| C2 | `2026-08-27-spec-C2-ikigai-record-polymorphic.md` | `IKIGAiRecord` polymorphic root + `SQLiteAdapter.upsert_ikigai_record` — single SQLite write path |
| C3 | `2026-08-27-spec-C3-state-reducer.md` | `StateReducer` — `IKIGAiStateDict → IKIGAiRecord` deterministic mapping |
| C4 | `2026-08-27-spec-C4-checkpoint-adapter.md` | `CheckpointAdapter` + `JsonPlusSerializer` envelope — eliminates raw pickle from LangGraph checkpoints |
| C5 | `2026-08-27-spec-C5-drift-detector.md` | `DriftDetector` per-UEID — `triagem-{ueid}.md` reports replace whole-vault `meta/triagem.md` |

Base path: `C:\Users\mathe\code_space\life-oss\life\code-docs\specs\`
Branch target: `feat/data-model-unification` (5 source commits: `d04fa0c`, `0dd2621`, `1de3641`, `770881e`, `eb8be96`, `912a7c0`).

### 8k. Data-model unification specs — `code-docs/specs/`

Five sibling specs that define acceptance + migration for the `feat/data-model-unification`
branch (Task #42). Each spec follows the §0-§8 format with purpose, problem,
design, interface signatures, AC, migration, verification, and cross-references.
TDD methodology: failing test → minimal impl → verification.

| # | Spec | Subject |
|--:|------|---------|
| C1 | `2026-08-27-spec-C1-vault-canonical-writer.md` | `IKIGAiAgenticWriter` + `VaultLock` + `dict_to_frontmatter` — sole vault writer (replaces f-string at `tools.py:350-385`) |
| C2 | `2026-08-27-spec-C2-ikigai-record-polymorphic.md` | `IKIGAiRecord` polymorphic root + `SQLiteAdapter.upsert_ikigai_record` — single SQLite write path |
| C3 | `2026-08-27-spec-C3-state-reducer.md` | `StateReducer` — `IKIGAiStateDict → IKIGAiRecord` deterministic mapping |
| C4 | `2026-08-27-spec-C4-checkpoint-adapter.md` | `CheckpointAdapter` + `JsonPlusSerializer` envelope — eliminates raw pickle from LangGraph checkpoints |
| C5 | `2026-08-27-spec-C5-drift-detector.md` | `DriftDetector` per-UEID — `triagem-{ueid}.md` reports replace whole-vault `meta/triagem.md` |

Base path: `C:\Users\mathe\code_space\life-oss\life\code-docs\specs\`
Branch target: `feat/data-model-unification` (5 source commits: `d04fa0c`, `0dd2621`, `1de3641`, `770881e`, `eb8be96`, `912a7c0`).

### 8d. ARDs — `code-docs/ard/`

Architecture requirements (cross-cluster, conceptual layer). See
`C:\Users\mathe\code_space\life-oss\life\code-docs\ard\README.md` (746 B).
Full content lives in cluster docs (`CONCEPTUAL_MODEL.md`,
`SYSTEMS_TOPOLOGY.md`, `ARCHITECTURAL_REFRAMING.md`, `CHECKPOINT.md`).

---

## 9. Operational docs index — `life-ops/operational/docs/`

110+ files across 9 subdirectories. This is the canonical doc set for the
**PAV kernel** (active dev target).

| Subdir | Files | Purpose |
|--------|------:|---------|
| `algorithms/` | 6 + README | The 6 core formulas (cartesian, day-budget, sleep, habit/QHE, pomodoro, policy) |
| `architecture/` | 13 + README | 3-layer MVC, persistence, import graph, data flow |
| `data/` | 4 + README | 14-entity data model, CSV schema, datasets, contracts |
| `debug/` | 3 + README | Common pitfalls, recovery recipes, log location |
| `tui/` | 8 + README | Rich-based TUI (NOT textual), layout, palette, debugging |
| `ux/0-inventario/` | — | UI inventory |
| `ux/00-visao-geral/` | — | UX high-level vision |
| `ux/02-componentes/` | 12 | Component catalog |
| `ux/04-fluxos/` | 10 | User flows |
| `ux/05-telas/` | 13+ | Screen-by-screen specs |
| `ux/08-validacao/` | 3 | UX validation |
| `design-system/` | 1 | Design system (676 lines spec) |
| `adr/` | 13+ | PAV kernel ADRs (see § 7c) |
| (root) | `INTEGRATION-BACKLOG.md`, `ROADMAP.md`, `TERMINAL_DESIGN_AUDIT.md` | Cross-cutting planning + audit |

Base path: `C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\`

---

## 10. Evidence trail — `.omo/evidence/`

97 total items in `.omo/`. Of these, **4 .md files** are evidence notes
captured during agent execution / research. File list and one-liners:

| File | Purpose |
|------|---------|
| `agentic-md-explore-current.md` | Current-state exploration of agentic-md / planning-with-files |
| `agentic-md-research-langgraph.md` | LangGraph research notes |
| `agentic-md-swarm-map.md` | Swarm topology map |
| `langgraph-dev-research.md` | LangGraph dev workflow research |

Base path: `C:\Users\mathe\code_space\life-oss\life\.omo\evidence\`

---

## 11. Strategic prose — `strategics/`

PT-BR strategic frameworks. **Read-only** (append-only rule applies).

| File | Topic |
|------|-------|
| `00-ÍNDICE-PROGRESSIVO.md` | Progressive index (start here) |
| `Análise (Tático e Operacional).md` | Tactical + operational analysis |
| `Desempenho Subjacente.md` | Underlying performance framework |
| `Hierarquia de Objetivos.md` | Goal hierarchy |
| `Integração_Tatica.md` | Tactical integration |
| `Modelagem Operacional.md` | Operational modelling (4 regimes) |
| `Planejamento (Estratégico e Tático).md` | Strategic + tactical planning |
| `design_system_and_knowledge_tracking.md` | Design system + knowledge tracking |
| `system_architecture_and_tracking_framework.md` | System architecture + tracking framework |

> **Note:** `strategics/planning-with-files/` is a vendored plugin — not
> strategic prose, ignore for navigation. Base path:
> `C:\Users\mathe\code_space\life-oss\life\strategics\`

---

## 12. Known gaps

1. **IKIGAi vector count mismatch** — root `README.md` and `CLAUDE.md`
   advertise **5 vectors** (Passion, Skill, Market, Revenue, **Course**);
   `vibe-ops/planning/PRD-07` documents **4 vectors** (Passion, Skill,
   Market, Revenue). Reconcile by promoting PRD-07 to 5 vectors or by
   rolling root docs back to 4. See decision-package ADR-008 Option 2C
   (recommended).
2. **ADRs not in one canonical place** — three surfaces:
   `vibe-ops/architecture/` (6 cybernetic), `life-ops/operational/docs/adr/`
   (13+ PAV), `code-docs/adr/` (now has master README at `code-docs/adr/README.md`).
   See master-adr-index.md for the consolidated table.
3. **`vibe-ops/specs/` carries deprecated v1 schemas alongside canonical v2**
   — readers must check the in-folder README to know which is current.
4. **Operational docs count is approximate** — `docs/ux/06-padroes/`,
   `docs/ux/07-acessibilidade/`, and a few others not enumerated here
   (the in-folder READMEs are the source of truth).

---

## 13. Maintenance rules

When adding to this index, follow the global conventions in
`C:\Users\mathe\code_space\life-oss\life\CLAUDE.md`:

- **Append-only for `vibe-ops/`, `strategics/`, cluster docs** — never
  delete, prune, or rewrite; re-organisation only if every pre-existing
  string survives byte-for-byte.
- **Standalone for `life-ops/operational/`** — must not import from `life/`
  or `vibe-ops/`. Update `life-ops/operational/SPEC.md` when domain logic
  or CLI changes.
- **Pydantic v2 strict** — every new schema: `frozen=True`,
  `extra="forbid"`, strict mode.
- **`--json` everywhere** — every new CLI command must support
  machine-readable output.
- **Zero LLM in pipeline** — daily/weekly loops are pure arithmetic.
- **Fully local** — no cloud, no API keys, no OAuth. SQLite + filesystem only.
- **PT-BR ↔ EN split** — strategic prose in Portuguese; code, file names,
  and AI specs in English.
- **Idempotency keys** — `upstream_id` (SHA-256) and `ueid` (format
  `<CLUSTER>:<ENTITY>:<ID>`) for all persisted records.
- **Error collection, not abort** — handlers collect errors and report at
  end, not short-circuit on partial failure.
- **This index is a navigation layer only** — never duplicate long
  content; link to the canonical file. Keep this file under 500 lines.

---

*Master Index — v1.0 — 2026-07-02*
*One file, all roads in. When in doubt: README → ARCHITECTURE_INDEX.md → cluster doc → code.*
