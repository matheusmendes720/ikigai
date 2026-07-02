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
| `ADR-007-data-first-methodology.md` | Accepted (2026-07-02) | Data-first methodology: schema → storage → adapters |
| `OPERATIONAL.md` | index | Pointer to PAV kernel ADR set (see § 7c) |
| `VIBE-OPS.md` | index | Pointer to cybernetic engine ADR set (see § 7a) |

Base path: `C:\Users\mathe\code_space\life-oss\life\code-docs\adr\`

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

1. **`code-docs/adr/README.md` does not exist** (other three — `prd/`, `brd/`,
   `ard/` — each have a README). Created date: 2026-07-02.
2. **IKIGAi vector count mismatch** — root `README.md` and `CLAUDE.md`
   advertise **5 vectors** (Passion, Skill, Market, Revenue, **Course**);
   `vibe-ops/planning/PRD-07` documents **4 vectors** (Passion, Skill,
   Market, Revenue). Reconcile by promoting PRD-07 to 5 vectors or by
   rolling root docs back to 4.
3. **ADRs not in one canonical place** — three surfaces:
   `vibe-ops/architecture/` (6 cybernetic), `life-ops/operational/docs/adr/`
   (13+ PAV), `code-docs/adr/` (3 local index files). Consider a single
   cross-link table.
4. **`vibe-ops/specs/` carries deprecated v1 schemas alongside canonical v2**
   — readers must check the in-folder README to know which is current.
5. **Operational docs count is approximate** — `docs/ux/06-padroes/`,
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
