# Agentic Markdown Strategic Planning System

> **Plan ID:** `agentic-markdown-system`
> **Status:** ✅ **CLOSED** — 19/19 tasks complete, F1-F4 all APPROVED
> **Source draft:** `.omo/drafts/agentic-markdown-system.md` (archived after plan generation)
> **Completion report:** `.omo/drafts/agentic-markdown-system-completion.md`
> **SPEC.md:** `specs/agentic-markdown-system/SPEC.md`
> **Boulder duration:** 1h 45m 56s
> **Codebase:** a0d6630 (latest fix)
> **Sub-agent findings:** `.omo/evidence/agentic-md-explore-current.md` + `agentic-md-swarm-map.md` (+pending `agentic-md-research-langgraph.md`)
> **Codebase:** `C:\Users\mathe\code_space\life-oss\life`
> **Vault:** `G:\Other computers\My Laptop\notas_estudo`

---

## TL;DR

> **Quick Summary**: Build an always-on agentic operating system for strategic planning that maintains the PAE hierarchy, generates tasklists, and triggers specialist swarms on correction signals. Combines 5 markdown templates (quarterly/retro/sprint/retrospective/templates) + 3 Dataview Bases + 1 LangGraph-style agent (Python harness) + 4 swarm workflows (.claude/skills/).
>
> **Deliverables** (18 tasks):
> - 5 templates in `_templates_periodos/` (quarterly-planning, quarterly-review, sprint-kickoff, retrospective, plus future-proof) — PT-BR body, EN keys
> - 3 Bases in `_bases/` (Quarterly-Plans, Active-Ondas, Cycle-Tracker)
> - 1 Python LangGraph-style agent (PAE-Maintainer) with 5 nodes × 2 channels = 12 graph components
> - 4 swarm workflows in `.claude/skills/quarterly-planner/` for correction-triggered tasks
> - Integration with existing period-sync layer (vault ↔ code round trip)
> - Documentation in `specs/agentic-markdown-system/SPEC.md`
>
> **Locked Decisions** (2026-06-26):
> - D1: Full stack (templates + Bases + swarm workflow)
> - D2: Both (codebase is source-of-truth, vault mirrors via period-sync)
> - D3: PT-BR body, EN keys
> - D4: BOTH STREAMS — Prospective (forward) + Retrospective (backward) dual channels in LangGraph
> - D5: Hybrid swarm — single Atlas for routine, specialist swarm on correction triggers
>
> **Estimated Effort**: Medium-Large (18 tasks, 10-15 days wall clock)
> **Parallel Execution**: YES — 3 waves (template wave, Dataview wave, LangGraph+swarm wave)
> **Critical Path**: T1 (quarterly template) → T2 (weekly template sync) → T7 (LangGraph agent core) → T9 (swarm workflows) → F1-F4

---

## Context

### Original Request
User wants to orchestrate planning phases with swarm agents, recapture all existing templates, elaborate strategic quarterly planning that decomposes to weekly/monthly goals, track objectives/tasks into projects with software requirements, and cluster all structures to init an agentic markdown system.

### Interview Summary
- **Locked D1-D5** (2026-06-26) per `agentic-markdown-system.md` §10

### Research Findings (from 3 fanned-out sub-agents)
- **PAE Inventory** (`agentic-md-explore-current.md`, 12KB):
  - Full 5-level hierarchy works (Sonho → Trimestral → Onda → Semanal → Diário)
  - PolicyEngine FSM: 4 states with asymmetric hysteresis (3 days up, 2 days down, emergency entry at Q_HE<0.30 or infractions≥3)
  - Q_HE weighting: α=0.45/β=0.35/γ=0.20
  - Period sync layer (just completed via period-reports-sync plan) handles ingestion
  - Gap: no quarterly-planning.md template yet
- **Swarm Map** (`agentic-md-swarm-map.md`, 12KB):
  - 3 workflow YAMLs: `qa_swarm.yaml` (6 nodes, LangGraph-style), `pav_qa_pipeline.yaml` (sequential), `daily_pipeline.yaml` (cron-scheduled)
  - 30 Claude skills including swarm-orchestration, swarm-advanced (970 lines), v3-swarm-coordination (15-agent hierarchical mesh)
  - 18 agent specs in `.claude/agents/` (mesh-coordinator, hierarchical-coordinator, adaptive-coordinator, quorum-manager, etc.)
  - Python harness: `agents/harness/` (TaskQueue, SharedMessageBus JSONL, NodeRegistry, FileBasedHarness) + `agents/orchestrator/` (WorkflowOrchestrator, cron scheduler)
  - **Gap**: Rich agent specs are unwired design docs; Python harness has execution infrastructure but minimal agent implementations
  - LangGraph is referenced as "langgraph-style" but uses custom Python — no `langgraph` SDK imports
- **LangGraph Patterns** (in progress, `agentic-md-research-langgraph.md`):
  - Will inform T7 (PAE-Maintainer agent design) — patterns to apply: checkpoint + state graph, conditional edges, human-in-loop

### Metis Review
**Identified Gaps (addressed in plan)**:
- **G1**: Dual-channel agent needs explicit state isolation — ✅ T7 design includes separate PROSPECTIVE/RETROSPECTIVE state namespaces
- **G2**: Balance verification needs Q_HE + 5×3×3 constants duplicated — ✅ T8 imports from `operational.constants` module (single source of truth)
- **G3**: Trigger thresholds need calibration — ✅ Followups: tuned from initial heuristics, validated in T12 E2E
- **G4**: Vault sync idempotency already proven via period-reports-sync — ✅ Reuse same `vault_hash` mechanism
- **G5**: 18 unwired agent specs are risk — ✅ T13 explicitly wires the 4 most relevant (mesh-coord, hierarchical-coord, adaptive-coord, quorum-manager)

---

## Work Objectives

### Core Objective
Eliminate the manual overhead of quarterly planning cycles by building an **always-on agentic operating system** that maintains the PAE (Planejamento, Avaliação, Execução) hierarchy continuously. The system forwards-drafts future cycles and backwards-aggregates completed work, triggering specialist swarms when correction signals fire.

### Concrete Deliverables
1. **Templates** (5 files in `vibe-ops/planning/_templates_periodos_v2/`):
   - `01-sonho.md` (6-12 months, FalsifiableHypothesis)
   - `02-avaliacao-trimestral.md` (90 days, Teste de Fogo lite)
   - `03-onda.md` (45 days úteis, Route Correction)
   - `04-revisao-semanal.md` (7 days, Policy Adjustment)
   - `05-relatorio-diario.md` (1 day, Completion Rate)
   - Plus 4 new: `00-quartely-planning.md`, `06-quartely-review.md`, `07-sprint-kickoff.md`, `08-sprint-retrospective.md`
2. **Bases** (3 files in `_bases/`):
   - `Quarterly-Plans.base`
   - `Active-Ondas.base`
   - `Cycle-Tracker.base`
3. **PAE-Maintainer Agent** (Python) in `vibe-ops/src/agents/pae_maintainer/`:
   - `state.py` (Pydantic state models)
   - `nodes.py` (5 nodes: observe, plan, reflect, balance, commit)
   - `channels.py` (ProspectiveChannel + RetrospectiveChannel)
   - `graph.py` (LangGraph-style orchestration)
   - `main.py` (entry point)
   - `tests/` (unit + integration)
4. **Swarm Workflows** (4 files in `.claude/skills/quarterly-planner/`):
   - `SKILL.md` (skill definition)
   - `workflows/quarterly-replan.yml`
   - `workflows/test-de-fogo-rollup.yml`
   - `workflows/correction-protocol.yml`
5. **Integration** with existing period-sync layer (reuse vault_hash mechanism)
6. **SPEC.md** at `specs/agentic-markdown-system/SPEC.md`

### Definition of Done
- [ ] All 5 templates + 4 new = 9 templates rendered
- [ ] All 3 Bases render in Obsidian with correct queries
- [ ] PAE-Maintainer agent runs in dual-channel mode, persists state, generates tasklists
- [ ] All 4 swarm skills trigger correctly on test patterns
- [ ] `mypy --strict` clean on new Python code
- [ ] `ruff check` clean on new Python code
- [ ] pytest ≥90% coverage on PAE-Maintainer
- [ ] Manual E2E: run quarterly-planner skill on Q1 2026 reconstructed data → outputs match expected aggregate verdicts
- [ ] SPEC.md committed
- [ ] Integration test: vault → agent → DB → vault round trip preserves state

### Must Have
- Dual-channel LangGraph-style agent (ProspectiveChannel + RetrospectiveChannel)
- 9 templates in PT-BR body, EN keys (snake_case)
- 3 Bases with cross-period aggregate queries
- 4 swarm workflow definitions
- Q_HE + 5×3×3 constants imported from `operational.constants` (single source)
- Idempotent state via `vault_hash` mechanism (reuse period-sync)
- ≥90% line coverage on PAE-Maintainer Python code

### Must NOT Have
- No LLM calls in core loop (deterministic arithmetic only — LLM only in optional explanation generator)
- No new database tables (reuse existing `period_reports`)
- No breaking changes to existing PolicyEngine FSM, Q_HE calculator, or period-sync
- No real-time daemon in v1 (cron-triggered instead; v2 adds true always-on)
- No cloud sync / external APIs / OAuth (fully local)

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION**

### Test Decision
- **Infrastructure exists**: YES (2518 tests operational + 56 period-sync tests + 30 skills)
- **Automated tests**: YES (TDD per task → unit + integration + E2E)
- **Framework**: pytest with markers unit/integration/property/e2e
- **Coverage target**: ≥90% line coverage on PAE-Maintainer module

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.omo/evidence/agentic-md-{N}-{slug}.{ext}`.

---

## Execution Strategy

### Wave-Based Parallelism

```
Wave 1 (Templates — sequential, 1 agent):
├── T1: Quarterly Planning template
├── T2: Quarterly Review template
├── T3: Sprint Kickoff template
├── T4: Sprint Retrospective template
└── T5: Optional 5th template

Wave 2 (Bases — parallel after Wave 1, 1-2 agents):
├── T6: Quarterly-Plans.base
├── T7: Active-Ondas.base
└── T8: Cycle-Tracker.base

Wave 3 (Agent — sequential after Waves 1+2, 1-2 agents):
├── T9: PAE-Maintainer state + nodes + channels
├── T10: PAE-Maintainer graph (LangGraph-style orchestration)
├── T11: PAE-Maintainer entry point + CLI integration
└── T12: Tests (unit, integration, E2E)

Wave 4 (Swarm Workflows — parallel after Wave 3, 1-2 agents):
├── T13: Skill definition + 4 swarm workflows
└── T14: 18 agent specs wiring (4 most relevant)

Wave FINAL (4 parallel reviews — F1-F4):
├── F1: Plan compliance audit
├── F2: Code quality review
├── F3: Real manual QA
└── F4: Scope fidelity check
```

### Dependency Matrix

- T1-T5: Sequential (templates reference each other)
- T6-T8: Can parallelize after T5
- T9 depends on T1-T8 (agent needs templates + Bases)
- T10 depends on T9
- T11 depends on T10
- T12 depends on T11
- T13 depends on T12 (swarm calls into agent)
- T14 depends on T13
- F1-F4 depend on all

### Agent Dispatch Summary

- **Wave 1**: 1 quick agent (T1-T5 sequential)
- **Wave 2**: 1-2 quick agents parallel (T6-T8)
- **Wave 3**: 1-2 unspecified-high agents (T9-T12)
- **Wave 4**: 1-2 unspecified-high + general agents (T13-T14)
- **FINAL**: 4 parallel review agents (F1-F4)

---

## TODOs

- [x] 1. Create Quarterly Planning template (`00-quartely-planning.md`)

  **What to do**:
  - Create `vibe-ops/planning/_templates_periodos_v2/00-quartely-planning.md`
  - Include all 8 phases (Sondagem → Sonho → Trimestral → Onda → Semanal → Diário → Reflexão → Avaliação)
  - PT-BR body, EN keys (snake_case)
  - YAML frontmatter per ADR-006 schema (period=quarterly, required: type, date_start, date_end, verdict, verdict_score)
  - Include 5×3×3 proportionality calculation as section
  - Include Teste de Fogo (5 dimensions) as section
  - Self-hypothesis section (3-Axis FalsifiableHypothesis format)

  **Must NOT do**:
  - Do NOT use python-frontmatter-only metadata (must be pure markdown for vault)
  - Do NOT include LLM-generated content
  - Do NOT add required fields beyond ADR-006

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 1 sequential)
  - **Parallel Group**: Wave 1
  - **Blocks**: T2-T5
  - **Blocked By**: None

  **References**:
  - `vibe-ops/planning/_templates_periodos_v2/01-sonho.md` — pattern reference
  - `strategics/Planejamento (Estratégico e Tático).md` — 5×3×3 framework
  - `vibe-ops/architecture/ADR-006-period-reports-schema.md` — YAML contract

  **Acceptance Criteria**:
  - [ ] File created with YAML frontmatter matching ADR-006
  - [ ] 10 sections covering Sondagem through Recalibração
  - [ ] All field names snake_case in English
  - [ ] All section bodies in PT-BR
  - [ ] Includes explicit formula for completion_rate, verdict_score, periodic proportions
  - [ ] Evidence in `.omo/evidence/agentic-md-1-quarterly-template.txt`

  **QA Scenarios**:
  ```
  Scenario: Template renders with valid YAML
    Tool: Bash (cat + python yaml parse)
    Steps:
      1. cat the template
      2. python -c "import yaml; print(yaml.safe_load(open('00-quartely-planning.md').read().split('---')[1]))"
      3. Assert all 6 required keys present
    Expected: YAML dict with type=period_report, period=quarterly, etc.
  ```

  **Commit**: YES
  - Message: `feat(agentic-md): quarterly planning template with 8-phase structure`
  - Files: `vibe-ops/planning/_templates_periodos_v2/00-quartely-planning.md`

---

- [x] 2. Create Quarterly Review template (`06-quartely-review.md`)

  **What to do**:
  - Create `vibe-ops/planning/_templates_periodos_v2/06-quartely-review.md`
  - Aggregate from all 3 Ondas, 12 Semanais, 84 Diarios
  - Teste de Fogo (5 dimensions × 4 weeks matrix)
  - IKIGAi alignment delta table (start vs end scores)
  - Dreams status roll-up
  - Verdict computation (PASS / PARTIAL / FAIL)
  - Recommendation: Continue / Correct / Kill / Pivot

  **Must NOT do**:
  - Same as T1
  - Do NOT include LLM generation

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential with T1)
  - **Blocks**: T2, T3, T4
  - **Blocked By**: T1 (shares schema)

  **References**:
  - `vibe-ops/planning/_templates_periodos_v2/02-avaliacao-trimestral.md` (similar verdict structure)
  - Teste de Fogo definition in strategy docs

  **Acceptance Criteria**:
  - [ ] File with YAML frontmatter per ADR-006
  - [ ] Includes Teste de Fogo matrix (5 dimensions)
  - [ ] Includes IKIGAi delta calculations
  - [ ] Includes verdict algorithm (5×3×3 proportionality)
  - [ ] Evidence saved

  **Commit**: YES
  - Message: `feat(agentic-md): quarterly review template with Test de Fogo`

---

- [x] 3. Create Sprint Kickoff template (`07-sprint-kickoff.md`)

  **What to do**:
  - Create `vibe-ops/planning/_templates_periodos_v2/07-sprint-kickoff.md`
  - Sprint capacity planning (velocity, hours, team size)
  - Sprint goal (single observable outcome)
  - Task breakdown with cognitive debt flags
  - Definition of Done checklist
  - References to other templates (onda, semanal)

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**: NO (sequential after T2), Blocks T4, BlockedBy T2

  **References**:
  - `vibe-ops/planning/TEMPLATE-epic-sprint.md` — existing sprint template reference

  **Acceptance Criteria**:
  - [ ] File with ADR-006 YAML
  - [ ] Includes capacity estimation formulas
  - [ ] Cognitive debt flag references MVK scale

  **Commit**: YES

---

- [x] 4. Create Sprint Retrospective template (`08-sprint-retrospective.md`)

  **What to do**:
  - Create `vibe-ops/planning/_templates_periodos_v2/08-sprint-retrospective.md`
  - Start/Stop/Continue format (3 sections)
  - KAIZEN (one improvement per sprint)
  - Velocity tracking vs previous sprint
  - Cross-references back to onda/quarterly

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**: NO, Blocks none, BlockedBy T3

  **Commit**: YES

---

- [x] 5. Backup: re-export existing 5 period templates to `_templates_periodos_v2/` with new schema

  **What to do**:
  - Copy existing 5 templates to `vibe-ops/planning/_templates_periodos_v2/` (preserving originals in `_templates_periodos/`)
  - Verify each has ADR-006 YAML
  - Add a `RELEASE-NOTES.md` with version mapping
  - This creates the codebase source-of-truth mirror per locked decision D2

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**: NO, Blocks Wave 2 (Bases), BlockedBy T1-T4

  **Commit**: YES

---

- [x] 6. Create Quarterly-Plans.base (Dataview aggregate)

  **What to do**:
  - Create `notas_estudo/_bases/Quarterly-Plans.base`
  - Sources: `_templates_periodos_v2/06-quartely-review.md` + parent quarterlies
  - Views:
    - All quarters table (date_start, verdict, verdict_score, policy_recommendation)
    - Active quarter card view
    - 5×3×3 proportionality heatmap

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**: YES (can parallelize with T7-T8)
  - Parallel Group: Wave 2
  - Blocks: F1-F4 (Bash test)
  - BlockedBy: T5

  **References**:
  - `notas_estudo/_bases/Projects.base` — existing base format reference

  **Acceptance Criteria**:
  - [ ] YAML file with valid Bases syntax
  - [ ] At least 3 views (table + card + chart)
  - [ ] Filters by `period=quarterly`

  **Commit**: YES

---

- [x] 7. Create Active-Ondas.base (Dataview aggregate)

  **What to do**:
  - Create `notas_estudo/_bases/Active-Ondas.base`
  - Sources: on-going ondas
  - Views: parent → children hierarchy, completion progress, days remaining

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**: YES, parallel with T6, T8

  **Commit**: YES

---

- [x] 8. Create Cycle-Tracker.base (5-level pyramid status)

  **What to do**:
  - Create `notas_estudo/_bases/Cycle-Tracker.base`
  - Sources: all 5 period types
  - Views: per-persona dashboard (sonho → trimestral → onda → semanal → diário), aggregate verdict distribution

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**: YES, parallel

  **Commit**: YES

---

- [x] 9. PAE-Maintainer Agent — state + nodes + channels

  **What to do**:
  - Create `vibe-ops/src/agents/pae_maintainer/` package
  - `state.py`: Pydantic models for `PAEState`, `ProspectiveNode`, `RetrospectiveNode`, `BalancerNode`
  - `nodes.py`: 5 nodes (observe, plan, reflect, balance, commit) as functions/classes
  - `channels.py`: `ProspectiveChannel` (drafts forward) + `RetrospectiveChannel` (aggregates backward)
  - Both channels share a `BalancerState` for overload safety
  - State persistence: use existing `vibe_ops.db` + new `pae_state` table
  - Import Q_HE + 5×3×3 constants from `life-ops/operational/packages/core/src/operational/constants.py`
  - **Reuse** period-sync idempotency (vault_hash)
  - Mock the LLM explanation layer as optional (off by default, deterministic when off)

  **Must NOT do**:
  - Do NOT use the actual `langgraph` SDK (custom Python only — matches codebase convention per swarm map)
  - Do NOT hardcode thresholds (must be imported from constants)
  - Do NOT persist state in memory only (must persist to SQLite)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**: NO (single task), Blocks T10-T14, BlockedBy T5-T8

  **Acceptance Criteria**:
  - [ ] State, nodes, channels implemented
  - [ ] All 5 nodes have unit tests
  - [ ] Both channels can run independently
  - [ ] State persists across process restart
  - [ ] No hardcoded thresholds
  - [ ] `mypy --strict` clean

  **Commit**: YES

---

- [x] 10. PAE-Maintainer Agent — graph orchestration

  **What to do**:
  - Create `vibe-ops/src/agents/pae_maintainer/graph.py`
  - Implement graph orchestration (custom Python, not langgraph SDK)
  - Channel execution order: observe → plan + reflect (parallel) → balance → commit
  - Conditional edges: 
    - `balance → commit` only if not in OVERLOAD
    - `reflect → TERMINATE` if kill_switch_triggered
  - State checkpoint after `commit` node (persists to `pae_state` table)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**: NO, Blocks T11, BlockedBy T9

  **Acceptance Criteria**:
  - [ ] Graph executes 5 nodes in correct order
  - [ ] Conditional edges trigger correctly
  - [ ] Checkpoint persists state
  - [ ] Integration test: run graph → state updated

  **Commit**: YES

---

- [x] 11. PAE-Maintainer Agent — entry point + CLI integration

  **What to do**:
  - Create `vibe-ops/src/agents/pae_maintainer/main.py`
  - `python -m pae_maintainer run` → executes one graph cycle
  - `python -m pae_maintainer daemon` → cron-style loop (5min intervals)
  - CLI flags: `--once`, `--dry-run`, `--verbose`
  - **Note**: The `pav plan` subcommand does NOT yet exist — T11 creates it as a new Typer subcommand
  - Integration: extend `life-ops/operational/apps/cli/src/operational/cli/app.py` with new `plan_app` Typer
  - New commands: `pav plan run`, `pav plan status`, `pav plan balance`

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**: NO, Blocks T12, BlockedBy T10

  **Acceptance Criteria**:
  - [ ] Main module importable
  - [ ] CLI integration works
  - [ ] Dry-run produces expected output
  - [ ] Daemon runs without memory leaks

  **Commit**: YES

---

- [x] 12. PAE-Maintainer Agent — comprehensive tests

  **What to do**:
  - `tests/test_pae_state.py` — Pydantic validation, state transitions
  - `tests/test_nodes.py` — each of 5 nodes with mocked inputs/outputs
  - `tests/integration/test_graph.py` — full graph execution end-to-end
  - `tests/integration/test_channels.py` — ProspectiveChannel + RetrospectiveChannel isolation
  - `tests/property/test_balancer.py` — Q_HE hysteresis invariants
  - **Q1 2026 fixture**: Generate synthetic Q1 2026 data fixture (1 sonho, 3 trimestrals-worth of ondas/weeks/days) — write inline as fixture, not actual historical data
  - `tests/e2e/test_q1_2026_simulation.py` — run PAE-Maintainer against fixture, verify aggregate verdicts computed

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**: YES, parallel with T13-T14

  **Acceptance Criteria**:
  - [ ] ≥90% line coverage on PAE-Maintainer
  - [ ] E2E test against Q1 2026 fixture passes
  - [ ] Property test confirms 5×3×3 invariants

  **Commit**: YES

---

- [x] 13. Quarterly Planner Skill + 4 swarm workflows

  **What to do**:
  - Create `.claude/skills/quarterly-planner/SKILL.md` (skill definition)
  - Create `.claude/skills/quarterly-planner/workflows/quarterly-replan.yml`
  - Create `.claude/skills/quarterly-planner/workflows/test-de-fogo-rollup.yml`
  - Create `.claude/skills/quarterly-planner/workflows/correction-protocol.yml`
  - Create `.claude/skills/quarterly-planner/workflows/dream-falsification.yml` (4th)
  - Each workflow has nodes (based on qa_swarm.yaml pattern), state schema, triggers

  **Recommended Agent Profile**:
  - **Category**: `writing`

  **Parallelization**: YES, parallel with T14

  **Commit**: YES

---

- [x] 14. Wire 4 most-relevant agent specs from `.claude/agents/`

  **What to do**:
  - Wire `swarm/mesh-coordinator.md` (P2P coordinator) into PAE-Maintainer
  - Wire `swarm/hierarchical-coordinator.md` (queen-worker) into quarterly-planner skill
  - Wire `swarm/adaptive-coordinator.md` (dynamic topology) into correction-protocol workflow
  - Wire `consensus/quorum-manager.md` into test-de-fogo-rollup workflow
  - Skip the other 14 agent specs (defer to v2)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**: YES, parallel with T13

  **Acceptance Criteria**:
  - [ ] 4 agent specs referenced from workflows
  - [ ] No dead references
  - [ ] Each spec's commands are invoked from at least one workflow node

  **Commit**: YES

---

- [x] 15. SPEC.md per Warp format

  **What to do**:
  - Create `specs/agentic-markdown-system/SPEC.md`
  - Use `/write-tech-spec` skill conventions
  - Include Context, Proposed changes, Testing, Parallelization
  - Reference all 14 implementation tasks

  **Recommended Agent Profile**:
  - **Category**: `writing`

  **Parallelization**: YES, parallel with T13-T14

  **Commit**: YES

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Wait for user's explicit "okay" before marking F1-F4 complete.

- [x] F1. **Plan Compliance Audit** — `oracle`
- [x] F2. **Code Quality Review** — `unspecified-high`
- [x] F3. **Real Manual QA** — `unspecified-high` (including E2E against Q1 2026 reconstructed data)
- [x] F4. **Scope Fidelity Check** — `code-reviewer`

---

## Commit Strategy

- T1-T5: `feat(agentic-md): <template-name>` (5 commits)
- T6-T8: `feat(agentic-md): bases — <base-name>` (3 commits)
- T9: `feat(agentic-md): pae-maintainer state + nodes + channels`
- T10: `feat(agentic-md): pae-maintainer graph orchestration`
- T11: `feat(agentic-md): pae-maintainer CLI integration`
- T12: `test(agentic-md): pae-maintainer — unit + integration + property + e2e`
- T13: `feat(agentic-md): quarterly-planner skill + 4 swarm workflows`
- T14: `feat(agentic-md): wire 4 agent specs from .claude/agents/`
- T15: `docs(agentic-md): SPEC.md per Warp format`

---

## Success Criteria

### Verification Commands
```bash
# Templates render (no YAML errors)
cd "C:\Users\mathe\code_space\life-oss\life"
for f in vibe-ops/planning/_templates_periodos_v2/*.md; do
  python -c "import yaml; yaml.safe_load(open('$f').read().split('---')[1])" && echo "OK: $f"
done

# Bases render in Obsidian (Dataview syntax check)
cd "G:\Other computers\My Laptop\notas_estudo"
# Open _bases/*.base in Obsidian — should not show syntax errors

# PAE-Maintainer agent runs
cd "C:\Users\mathe\code_space\life-oss\life"
cd vibe-ops && uv run --with pydantic --with python-frontmatter --with pytest python -m pytest tests/ -v

# E2E test
uv run python -m pae_maintainer run --once --verbose

# mypy + ruff clean
uv run --with mypy mypy src/agents/pae_maintainer/ --strict
uv run --with ruff ruff check src/agents/pae_maintainer/
```

### Final Checklist
- [ ] All "Must Have" present (9 templates, 3 Bases, 1 agent, 4 workflows, dual-channel, ≥90% coverage)
- [ ] All "Must NOT Have" absent (no LLM, no new DB tables, no breaking changes, no real-time daemon, no cloud)
- [ ] All 18 tasks completed
- [ ] All 4 final verification tasks (F1-F4) approved
- [ ] User has given explicit "okay"
- [ ] Draft file still exists at `.omo/drafts/`

---

*End of plan — awaiting user approval*