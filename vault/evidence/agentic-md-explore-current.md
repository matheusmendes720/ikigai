# Agentic Markdown System — Current State Inventory
Generated: 2026-06-30
Source scan: codebase + vault + .omo/plans + .omo/drafts

---

## 1. Current PAE Artifacts (Quarterly/Trimestral)

### 1a. Quarterly Planning Files (codebase)
| Path | Size | Description |
|------|------|-------------|
| C:\Users\mathe\code_space\life-oss\life\CLUSTER_PLAN.md | — | Cluster 1 master plan doc |
| C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_BRD.md | — | BRD for cluster plan |
| C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_ROADMAP.md | — | Roadmap for cluster plan |
| C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_CLI_SPEC.md | — | CLI spec for cluster plan |
| C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_USER_STORIES.md | — | User stories for cluster plan |
| C:\Users\mathe\code_space\life-oss\life\vibe-ops\planning\CLUSTER_PLAN_DATA_MODEL.md | — | Data model for cluster plan |
| C:\Users\mathe\code_space\life-oss\life\life-ops\planner\SCALAR_DECOMPOSITION_BACKLOG.md | — | Scalar decomposition |
| C:\Users\mathe\code_space\life-oss\life\life-ops\planner\ikigai_planning\README.md | — | IKIGAi planning index |
| C:\Users\mathe\code_space\life-oss\life\life-ops\planner\ikigai_planning\ikigai_propagation.md | — | IKIGAi propagation |
| C:\Users\mathe\code_space\life-oss\life\life-ops\planner\ikigai_planning\ikigai_north_star_metrics.md | — | North star metrics |
| C:\Users\mathe\code_space\life-oss\life\life-ops\planner\ikigai_planning\ikigai_meta_heuristics.md | — | Meta heuristics |
| C:\Users\mathe\code_space\life-oss\life\strategics\Planejamento (Estratégico e Tático).md | — | Strategic/tactical planning |
| C:\Users\mathe\code_space\life-oss\life\strategics\Hierarquia de Objetivos.md | — | Goals hierarchy |
| C:\Users\mathe\code_space\life-oss\life\docs\ÍNDICE PROGRESSIVO.md | — | Progressive index |
| C:\Users\mathe\code_space\life-oss\life\docs\chat-Framework de Planejamento Estratégico.md | — | Strategic planning framework chat |
| C:\Users\mathe\code_space\life-oss\life\test_full\_templates_periodos\02-Q1.md | — | Q1 template (test fixture) |

### 1b. Period Templates (vault)
| Path | Period | Verdict Algorithm |
|------|--------|-------------------|
| 	est_full/_templates_periodos/01-sonho.md | Sonho (6-12m) | 3-Axis FalsifiableHypothesis |
| 	est_full/_templates_periodos/02-Q1.md | Trimestral (90d) | Teste de Fogo lite |
| 	est_full/_templates_periodos/03-w01.md | Onda (45d úteis) | Route Correction |
| 	est_full/_templates_periodos/04-w02.md | Semanal (7d) | Policy Adjustment |

---

## 2. Hierarchy State (Sonho/Trimestral/Onda/Semanal/Diário)

### 2a. Hierarchy Structure (from 5-level pyramid)
`
SONHO (6-12 months) → TRIMESTRAL (90 days) → ONDA (45 days úteis) → SEMANAL (7 days) → DIÁRIO (1 day)
`

### 2b. Period Templates Contract (ADR-006)
| Template | Period | Verdict Enum | Score Range | Algorithm |
|----------|--------|-------------|-------------|-----------|
| 01-sonho.md | sonho | VALIDATED/FALSIFIED/PIVOTED/ABANDONED | [0,1] | FalsifiableHypothesis |
| 02-trimestral.md | trimestral | PASS/PARTIAL/FAIL | [0,1] | Teste de Fogo (5 dims) |
| 03-onda.md | onda | CONTINUE/CORRECT/KILL | [0,1] | Route Correction |
| 04-revisao-semanal.md | weekly | PASS→PUSH/PARTIAL→MAINTAIN/FAIL→REDUCE | [0,1] | Policy Adjustment |
| 05-relatorio-diario.md | daily | PASS/FAIL | [0,1] | Completion Rate ≥0.80 |

### 2c. Hierarchy FK Contract
- Each level has: parent_period FK, sonho_id FK, erdict enum, erdict_score [0,1]
- Sonho: no parent, 6-12 month horizon
- Trimestral: parent=sonho, 90-day window
- Onda: parent=trimestral, 45 working days
- Semanal: parent=onda, 7 days
- Diário: parent=semanal, 1 day

---

## 3. LangGraph / Always-On Agentic Loop References

### 3a. LangGraph-style YAML Workflows
| Path | Description |
|------|-------------|
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\workflows\qa_swarm.yaml | 6-node QA swarm (ux_io_analyst, tdd_agent, flow_analyzer, reqs_validator, style_analyzer, system_optimizer) with edges and state_schema |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\workflows\pav_qa_pipeline.yaml | Sequential PAV QA pipeline with Slack notifications |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\workflows\daily_pipeline.yaml | Daily pipeline workflow |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\medic\examples\workflow\visual-critic.yaml | Visual critic workflow example |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\medic\examples\workflow\pr-review.yaml | PR review workflow |

### 3b. Agent Harness Infrastructure
| Path | Description |
|------|-------------|
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\__init__.py | Agent harness init |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\workflow_schema.py | Workflow schema definitions |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\task_queue.py | Task queue implementation |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\node_registry.py | Node registry |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\message_bus.py | Message bus |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\file_harness.py | File harness |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\engines\tdd_agent.py | TDD agent engine |
| C:\Users\mathe\code_space\life-oss\life\life-ops\operational\agents\harness\engines\reqs_agent.py | Reqs agent engine |

### 3c. Draft Design for Always-On Loop
From .omo/drafts/agentic-markdown-system.md §10 (LOCKED 2026-06-26):
- **Dual LangGraph pattern**: PROSPECTIVE CHANNEL + RETROSPECTIVE CHANNEL
- **Core LangGraph nodes**: observe, plan, reflect, balance, commit
- **Swarm expansion triggers**:
  - Kill switch date approaching
  - Test de Fogo PASS/FAIL delta > 0.15
  - Q_HE sustained < 0.45 for >30 days
  - Sub-sonho PIVOTED status detected
  - LangGraph cycles stuck > N iterations

---

## 4. Swarm Orchestration YAML/JSON Configs

### 4a. YAML Workflows
| Path | Nodes | Edges | Parallel Groups |
|------|-------|-------|----------------|
| life-ops/operational/agents/workflows/qa_swarm.yaml | 6 (ux_io, tdd, flow, reqs, style, optimizer) | 7 (on_complete) | 2 (phase1, phase2) |
| life-ops/operational/workflows/pav_qa_pipeline.yaml | 6 sequential tasks | 5 depends_on | N/A (sequential) |
| life-ops/operational/workflows/daily_pipeline.yaml | TBD | TBD | TBD |
| life-ops/operational/medic/examples/workflow/visual-critic.yaml | TBD | TBD | TBD |
| life-ops/operational/medic/examples/workflow/pr-review.yaml | TBD | TBD | TBD |

### 4b. GitHub Workflows / Config
| Path | Description |
|------|-------------|
| C:\Users\mathe\code_space\life-oss\life\.github\workflows\ci.yml | CI workflow |
| C:\Users\mathe\code_space\life-oss\life\.github\labels.yml | GitHub labels |
| C:\Users\mathe\code_space\life-oss\life\.pre-commit-config.yaml | Pre-commit hooks |
| life-ops/operational/.pre-commit-config.yaml | Operational pre-commit |
| life-ops/operational/medic/examples/github-action/action.yml | GitHub action example |

### 4c. Contract Registries
| Path | Description |
|------|-------------|
| ibe-ops/src/contracts/registry.yaml | Contract registry |
| ibe-ops/src/contracts/planning.v1.yaml | Planning v1 contracts |
| ibe-ops/schema_registry/registry.yaml | Schema registry |
| ibe-ops/contracts/study_topic_v1.json | Study topic contract |
| ibe-ops/contracts/roadmap_v1.json | Roadmap contract |

---

## 5. Balance / Progressive Overload Mechanisms

### 5a. PolicyEngine FSM States (from constants.py + policy_engine.py)
| State | Ordinal | hardwork_budget_h | max_pomodoros | sleep_target | qhe_target | break_min | allowed_phases |
|-------|---------|-------------------|---------------|--------------|------------|-----------|----------------|
| PUSH | 0 | 8.0 | 10 | 7.0 | 0.85 | 10 | DEEP_WORK, SHALLOW_WORK |
| MAINTAIN | 1 | 6.0 | 8 | 8.0 | 0.75 | 10 | DEEP_WORK, SHALLOW_WORK |
| REDUCE | 2 | 4.0 | 5 | 8.0 | 0.65 | 15 | SHALLOW_WORK, RECOVERY |
| RECOVER | 3 | 2.0 | 2 | 9.0 | 0.50 | 20 | RECOVERY |

### 5b. Hysteresis Values (from constants.py)
| Constant | Value | Description |
|----------|-------|-------------|
| POLICY_UPGRADE_DAYS | 3 | Consecutive days to upgrade (QHE ≥ push threshold) |
| POLICY_DOWNGRADE_DAYS | 2 | Consecutive days to downgrade (QHE < recover threshold) |
| POLICY_RECOVER_ENTRY_DAYS | 1 | Emergency RECOVER entry (QHE < 0.30 OR infractions ≥ 3) |
| QHE_PUSH_THRESHOLD | 0.85 | Upgrade to PUSH threshold |
| QHE_RECOVER_THRESHOLD | 0.60 | Downgrade to RECOVER threshold |
| _RECOVER_QHE_CRITICAL | 0.30 | Single-day emergency cutoff |
| _RECOVER_INFRACTION_THRESHOLD | 3 | Emergency RECOVER entry |

### 5c. Q_HE Formula Constants (from constants.py)
| Constant | Value | Description |
|----------|-------|-------------|
| QHE_ALPHA | 0.45 | Weight of H_avg in QHE formula |
| QHE_BETA | 0.35 | Weight of Consistency in QHE formula |
| QHE_GAMMA | 0.20 | Weight of StreakBonus in QHE formula |
| LAMBDA_LEARNING_DEFAULT | 0.093 | Default learning rate for habit automation |

### 5d. Q_HE Core Formula
`
H(t) = 1 − e^(−λ·streak)     # Habit consistency
E = R·(1 − H(t))              # Energy required
Q_HE = α·H_avg + β·Consistency + γ·StreakBonus
`

### 5e. Asymmetric Hysteresis Rules
- **Upgrade** (toward PUSH): requires QHE ≥ push_threshold for **3 consecutive days**
- **Downgrade** (toward RECOVER): requires QHE < recover threshold for **2 consecutive days**
- **Emergency RECOVER entry**: fires **immediately** when:
  - infraction_count ≥ 3, OR
  - QHE < 0.30
- **One-step rule**: direct PUSH → RECOVER jump NOT allowed; must traverse MAINTAIN/REDUCE

---

## 6. Existing .omo Plans Summary

| Plan | Status | Size | Focus |
|------|--------|------|-------|
| .omo/plans/agentic-markdown-system.md | DRAFT (locked decisions) | ~23KB | Unified PAE + swarm orchestration |
| .omo/plans/period-reports-sync.md | DRAFT (approved, T1-T10) | ~41KB | Period reports sync layer |
| .omo/plans/vault-bidirectional-sync.md | DRAFT | ~53KB | Vault ↔ DB bidirectional sync |
| .omo/plans/pav-tui-textualize.md | DRAFT | ~59KB | PAV TUI textualization |

---

## 7. Key Source Files for PAE System

### 7a. Core Policy/Habit Engine
| Path | Key Content |
|------|-------------|
| life-ops/operational/packages/core/src/operational/constants.py | 24 PAV constants including hysteresis + Q_HE weights |
| life-ops/operational/packages/core/src/operational/enums.py | PolicyState enum, Period enum, HabitCategory, RoutineType |
| life-ops/operational/packages/core/src/operational/core/policy_engine.py | 4-state FSM, evaluate_policy, hysteresis logic |
| life-ops/operational/packages/core/src/operational/core/habit_engine.py | H(t), E, Q_HE composite score |
| life-ops/operational/docs/algorithms/06-POLICY-ENGINE.md | Full policy engine documentation |
| life-ops/operational/docs/algorithms/04-HABIT-ENGINE.md | Full habit engine documentation |

### 7b. Period Report Entities
| Path | Key Content |
|------|-------------|
| ibe-ops/src/models/period_report.py | PeriodReport Pydantic entity (lenient) |
| ibe-ops/src/middleware/period_sync.py | PeriodReportSync class |
| ibe-ops/migrations/004_period_reports.sql | Migration 004: period_reports table + indexes + views |
| ibe-ops/src/models/temporal_entities.py | Temporal entity models |

### 7c. Vibe-ops Cybernetic Loop
| Path | Key Content |
|------|-------------|
| ibe-ops/src/cybernetics/daily_loop.py | Target-Sensor-Adjuster loop |
| ibe-ops/src/cybernetics/engine.py | Cybernetic engine |
| ibe-ops/src/pipeline/policy_engine.py | Vibe-ops policy engine (separate from operational) |
| ibe-ops/src/middleware/sync_engine.py | Obsidian ↔ SQLite ↔ Taskwarrior sync |

---

*Inventory generated 2026-06-30 — agentic-markdown-system exploration*
