# SPEC: Agentic Markdown Strategic Planning System

> **Feature ID:** `agentic-markdown-system`
> **Status:** Implemented (T1-T14 done; awaiting F1-F4)
> **Plan:** `.omo/plans/agentic-markdown-system.md`
> **ADR-006:** [`vibe-ops/architecture/ADR-006-period-reports-schema.md`](../../vibe-ops/architecture/ADR-006-period-reports-schema.md)
> **Codebase commit:** a70c39d1c1ace31282b0e8472acf31b8720d38a2

---

## 1. Context

The Algorithmic Life OS lacked an always-on planning agent to maintain the PAE (Planejamento, Avaliacao, Execucao) hierarchy continuously. Period reports existed (5 templates in `vibe-ops/planning/_templates_periodos/`) but had no agent to draft forward + aggregate backward + trigger specialist swarms on correction signals.

This spec delivers an always-on dual-channel planning agent (PROSPECTIVE + RETROSPECTIVE) with 5 templates, 3 Bases, a Python LangGraph-style PAE-Maintainer agent, 4 swarm workflows, and 4 wired agent specs.

### 1.1 Problem
- Period reports in vault are not aggregated forward (no quarterly planning wizard)
- Histeresis/5x3x3 calculations exist in operational code but not exposed in vault
- No swarm triggers on correction signals (kill switch, test de fogo drift, recover)
- No quarterly-planning template (only 5 period levels: sonho, trimestral, onda, semanal, diario)

### 1.2 Solution
9 templates + 3 Bases + 1 PAE-Maintainer agent + 4 swarm workflows + 4 agent specs wired.

### 1.3 Relevant Files (pinned to commit)
- `vibe-ops/planning/_templates_periodos_v2/` (T1-T5) -- 9 templates (PT-BR body, EN keys)
- `notas_estudo/_bases/` (T6-T8) -- 3 Bases for vault dashboard
- `vibe-ops/src/agents/pae_maintainer/` (T9-T11) -- LangGraph-style agent (state + nodes + graph + CLI)
- `vibe-ops/tests/` (T12) -- 143 tests, 96% coverage
- `.claude/skills/quarterly-planner/` (T13-T14) -- skill + 4 workflows
- `specs/agentic-markdown-system/SPEC.md` (T15, this file)

---

## 2. Proposed Changes

### 2.1 Templates (T1-T5)
9 markdown templates in `vibe-ops/planning/_templates_periodos_v2/`:
- `00-quartely-planning.md` (T1) -- 8-phase quarterly structure
- `01-sonho.md` (T5, copied) -- 3-Axis FalsifiableHypothesis
- `02-avaliacao-trimestral.md` (T5, copied)
- `03-onda.md` (T5, copied)
- `04-revisao-semanal.md` (T5, copied)
- `05-relatorio-diario.md` (T5, copied)
- `06-quartely-review.md` (T2) -- Teste de Fogo matrix + IKIGAi delta
- `07-sprint-kickoff.md` (T3) -- capacity planning + cognitive debt
- `08-sprint-retrospective.md` (T4) -- Start/Stop/Continue + KAIZEN
- `RELEASE-NOTES.md` (T5) -- version map v1.0 to v2.0

### 2.2 Bases (T6-T8) -- Dataview Bases (Obsidian)
- `Quarterly-Plans.base` (T6) -- 3 views: All Quarters, Active Quarter, 5x3x3 Proportionality Heatmap
- `Active-Ondas.base` (T7) -- 4 views: All Ondas, Active Only, Hierarchy, Days Remaining Heatmap
- `Cycle-Tracker.base` (T8) -- 4 views: All Cycles, Per-Period Status, Teste de Fogo Heatmap, By IKIGAi Vector

### 2.3 PAE-Maintainer Agent (T9-T12) -- Custom Python Graph
- `state.py` -- Pydantic models: `PlanTier`, `PlanVerdict`, `BalancerVerdict`, `PlanNode`, `ProspectiveNode`, `RetrospectiveNode`, `BalancerState`, `PAEState`
- `nodes.py` -- 5 pure functions: `observe_node`, `plan_node`, `reflect_node`, `balance_node`, `commit_node`
- `channels.py` -- `ProspectiveChannel`, `RetrospectiveChannel` (share `BalancerState`)
- `graph.py` -- LangGraph-style orchestration: `run_pae_cycle`, `checkpoint_state`, `restore_from_checkpoint`, `execute_pae_maintainer_once`
- `main.py` -- CLI entry (`run`, `daemon`, `status`, `balance`)
- `__main__.py` -- `python -m pae_maintainer`
- `AGENT_WIRING.md` -- spec to workflow mapping

### 2.4 CLI Bridge (T11)
- `pav plan` Typer subcommand (NEW -- `life-ops/operational/apps/cli/src/operational/cli/commands/plan_cmd.py`)
- 3 sub-subcommands: `pav plan run`, `pav plan status`, `pav plan balance`
- Invokes `pae_maintainer` via subprocess

### 2.5 Swarm Workflows (T13-T14) -- `.claude/skills/quarterly-planner/`
- `SKILL.md` -- skill definition
- `workflows/quarterly-replan.yml` (T13) -- Friday 6pm, on verdict!=PASS
- `workflows/test-de-fogo-rollup.yml` (T13) -- on-demand 5-dim rollup
- `workflows/correction-protocol.yml` (T13+T14) -- on kill switch, uses mesh-coordinator
- `workflows/dream-falsification.yml` (T13+T14) -- daily 9am on imminent Sonho, uses quorum-manager
- 4 agent specs wired: `mesh-coordinator`, `hierarchical-coordinator`, `adaptive-coordinator`, `quorum-manager`

### 2.6 Persistence
- New `pae_state` table in `vibe_ops.db` (created in T10 via `checkpoint_state`)
- `INSERT OR REPLACE ON CONFLICT(cycle_id) DO UPDATE` pattern (idempotent)
- State survives process restart

### 2.7 Constants Imported (NO duplication)
- `life-ops/operational/packages/core/src/operational/constants.py` (PAVConstants, Period, PolicyState)
- Single source of truth for Q_HE + 5x3x3 + histerese

---

## 3. Testing and Validation

### 3.1 Unit Tests (T12)
- `vibe-ops/tests/test_pae_state.py` -- 32 tests
- `vibe-ops/tests/test_pae_nodes.py` -- 28 tests
- Coverage: state, nodes, validators, defaults, transitions

### 3.2 Integration Tests (T12)
- `vibe-ops/tests/integration/test_pae_graph.py` -- 20 tests (full graph + checkpoint)
- `vibe-ops/tests/integration/test_pae_channels.py` -- 26 tests (channel isolation)

### 3.3 Property Tests (T12)
- `vibe-ops/tests/property/test_pae_balancer.py` -- 11 tests, 700+ examples (5x3x3 invariants, histeresis)

### 3.4 E2E Test (T12)
- `vibe-ops/tests/e2e/test_pae_q1_2026.py` -- 11 tests (synthetic Q1 2026 fixture: 1 sonho + 3 ondas + 12 weeks + 21 days = 37 nodes)

### 3.5 Verification
- pytest: 143 passed
- Coverage: 96% on `vibe-ops/src/agents/pae_maintainer/`
- mypy --strict: clean
- ruff: clean

---

## 4. Parallelization

### 4.1 Wave-Based
```
Wave 1 (Templates -- sequential, 1 agent):
├── T1: Quarterly Planning template
├── T2: Quarterly Review template
├── T3: Sprint Kickoff template
├── T4: Sprint Retrospective template
└── T5: Backup existing 5 templates

Wave 2 (Bases -- parallel, 1-2 agents):
├── T6: Quarterly-Plans.base
├── T7: Active-Ondas.base
└── T8: Cycle-Tracker.base

Wave 3 (Agent -- sequential, 1-2 agents):
├── T9: PAE state + nodes + channels
├── T10: PAE graph orchestration
├── T11: PAE entry point + CLI
└── T12: PAE tests (143 tests, 96% coverage)

Wave 4 (Swarm -- parallel, 1-2 agents):
├── T13: Skill + 4 workflows
└── T14: Wire 4 agent specs
├── T15: SPEC.md (this file)

Wave FINAL (4 parallel reviews -- F1-F4):
├── F1: Plan compliance audit
├── F2: Code quality review
├── F3: Real manual QA
└── F4: Scope fidelity check
```

### 4.2 Dependencies
- T1-T5: Sequential (templates share schema)
- T6-T8: Can parallelize after T5
- T9 depends on T1-T8 (agent needs templates + Bases as context)
- T10 depends on T9
- T11 depends on T10
- T12 depends on T11
- T13-T15: Parallel (independent)
- F1-F4 depend on all

---

## 5. Behavior Invariants

| ID | Invariant | Test |
|----|-----------|------|
| B1 | PAE state persists across restart | T12 test_pae_graph.test_persist_and_load |
| B2 | Q_HE histeresis: 3+ days in OK triggers ACTIVE | T12 test_pae_balancer.test_histeresis_active_after_3_days |
| B3 | OVERLOAD skips commit, triggers kill_switch | T12 test_pae_nodes.test_commit_skips_on_overload |
| B4 | 5x3x3 thresholds imported from operational.constants | T12 test_pae_state.test_baler_* |
| B5 | Dual channels isolated (no shared mutable state) | T12 test_pae_channels.* |
| B6 | vault_hash idempotency (re-sync = no-op) | inherited from period-reports-sync plan |

---

## 6. Out of Scope (v1)

- Real-time daemon (defer to v2 -- v1 uses `pav plan daemon` with interval polling)
- LLM-generated narrative summaries (always-no per repo convention)
- Auto-discovery of agent specs (T14 wires 4 manually; v2 adds auto-discovery)
- Wire remaining 14 of 18 agent specs (deferred to v2)
- Migration of existing 234+ vault notes (separate plan)
- LangGraph SDK adoption (custom Python chosen to match `qa_swarm.yaml` pattern)

---

## 7. Follow-ups (v1.1 + v2)

### v1.1
- `life sync migrate` for existing 234+ notes
- `life sync watch` one-shot watcher
- LLM explanation layer (off by default, opt-in)

### v2
- Real-time bidirectional daemon
- Multi-vault support
- Auto-discovery of agent specs
- Wire remaining 14 agent specs
- LangGraph SDK adoption (evaluate trade-offs)
- Consensus protocol stubs (quorum/gossip/raft)

---

*SPEC.md for agentic-markdown-system v1 -- 2026-06-26 -- Cluster PLAN -- IKIGAi Sys-01*
