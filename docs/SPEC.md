# Specifications — Algorithmic Life OS

> Unified index of all engineering specifications: ADRs, PRDs, BRDs, and technical references.

All specs are **append-only** unless explicitly refactored. Do not delete or rewrite existing sessions, topics, or paragraphs.

---

## vibe-ops — Cybernetic Engine

**Location:** `vibe-ops/planning/` and `vibe-ops/architecture/`

### Architecture Decision Records (ADRs)
| File | Subject |
|------|---------|
| `vibe-ops/architecture/ADR-001-data-flow-topology.md` | Multi-cluster data flow topology |
| `vibe-ops/architecture/ADR-002-mesh-contracts-state-machines.md` | Contracts and state machine specs |
| `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` | IKIGAi as meta-brain architecture |
| `vibe-ops/architecture/ADR-004-hybrid-rag-strategy.md` | Hybrid RAG indexing strategy |
| `vibe-ops/architecture/ADR-005-data-mesh-topology.md` | Data mesh topology |

### Product Requirements Documents (PRDs)
| File | Subject |
|------|---------|
| `vibe-ops/planning/PRD-01-temporal-engine.md` | Wave/Cycle/Phase temporal engine |
| `vibe-ops/planning/PRD-02-habit-tracker.md` | Habit tracker with H(t), E(t), Q_HE |
| `vibe-ops/planning/PRD-03-study-backlog.md` | Skill/Topic/Material/Session backlog |
| `vibe-ops/planning/PRD-04-project-execution.md` | Project/Epic/Sprint/Task execution |
| `vibe-ops/planning/PRD-05-metrics-health.md` | SleepRecord/EnergyReading metrics |
| `vibe-ops/planning/PRD-06-policy-governance.md` | PolicyEngine 4-state governance |
| `vibe-ops/planning/PRD-07-ikigai-vectors.md` | IKIGAi vector entities |

### Business Requirements (BRDs)
| File | Subject |
|------|---------|
| `vibe-ops/planning/CLUSTER_PLAN_BRD.md` | Cluster 1 (Plan) business requirements |
| `vibe-ops/planning/CLUSTER_PLAN_USER_STORIES.md` | 10 user stories |
| `vibe-ops/planning/CLUSTER_PLAN_CLI_SPEC.md` | 13 CLI commands spec |
| `vibe-ops/planning/CLUSTER_PLAN_ROADMAP.md` | 12 sprints Q3 roadmap |
| `vibe-ops/planning/CLUSTER_PLAN_DATA_MODEL.md` | Data model for Cluster 1 |

---

## life-ops/operational — PAV Productivity Kernel

**Location:** `life-ops/operational/docs/adr/`

### Core ADRs
| File | Subject |
|------|---------|
| `life-ops/operational/docs/adr/PRD-CONSTANTS-EXCEPTIONS.md` | PAVConstants + 10 error codes |
| `life-ops/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` | Habit engine core logic |
| `life-ops/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` | Policy FSM + consolidator |
| `life-ops/operational/docs/adr/PRD-CORE-POMODORO-SCENARIO.md` | 8-state pomodoro SM + scenarios |
| `life-ops/operational/docs/adr/PRD-CORE-SLEEP-VALIDATION.md` | Sleep calculator + validation |
| `life-ops/operational/docs/adr/PRD-CORE-TIME-BLOCKS-AND-REFLECTION.md` | Time blocks + journal reflection |

### Entity ADRs
| File | Subject |
|------|---------|
| `life-ops/operational/docs/adr/PRD-ENTITIES-JOURNAL-HABIT.md` | JournalEntry, Habit entities |
| `life-ops/operational/docs/adr/PRD-ENTITIES-METRIC-CONSOLIDATION.md` | Metric entities + rollup |
| `life-ops/operational/docs/adr/PRD-ENTITIES-POLICY.md` | PolicySetpoints, PolicyDecision |
| `life-ops/operational/docs/adr/PRD-ENTITIES-ROUTINE-TIMEBLOCK-POMODORO.md` | Routine, TimeBlock, Pomodoro entities |
| `life-ops/operational/docs/adr/PRD-ENUMS-TYPES.md` | Enums and type definitions |
| `life-ops/operational/docs/adr/ARCHITECTURAL_REFRAMING_2026-06-07.md` | Post-Sprint 10 reframe |

### Sprint Reports
| File | Subject |
|------|---------|
| `life-ops/operational/docs/adr/SPRINT-1-REPORT.md` | Sprint 1 verification |
| `life-ops/operational/docs/adr/SPRINT-2-REPORT.md` | Sprint 2 verification |
| `life-ops/operational/docs/adr/SPRINT-3-REPORT.md` | Sprint 3 verification |

---

## Templates

| File | Use |
|------|-----|
| `vibe-ops/planning/TEMPLATE-epic-sprint.md` | Epic + sprint template |
| `vibe-ops/planning/TEMPLATE-micro-ciclo.md` | Micro-cycle review template |
| `vibe-ops/planning/TEMPLATE-weekly-review.md` | Weekly review template |
