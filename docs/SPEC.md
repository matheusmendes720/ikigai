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

---

## Cross-references ao novo design-system (2026-08-28)

Este doc faz parte do escopo legacy PAV-era preservado como histórico
(append-only invariant). A canonical reference post-pivot vive em
[`docs/design-system/`](design-system/00-INDEX.md) — 40 docs em 9 camadas
que cobrem UI tokens, padrões arquiteturais, forks-prontas, user journeys,
validação (Nielsen + checklist + risks), e análise crítica de segunda ordem.
Os PRDs, ADRs e BRDs linkados nas tabelas acima continuam sendo o source-of-truth
para os artefatos legacy; nada aqui foi deletado nem refatorado.

**Índice & narrativa canônica (Layer 0–1):**
- [`docs/design-system/00-INDEX.md`](design-system/00-INDEX.md) — índice navegável das 9 camadas
- [`docs/design-system/01-master-branch-carro-chefe-2026-08-28.md`](design-system/01-master-branch-carro-chefe-2026-08-28.md) — narrativa canônica deep-agent ↔ forks-prontas ↔ vault
- [`docs/design-system/02-interfaces-dual-layer-architecture.md`](design-system/02-interfaces-dual-layer-architecture.md) — arquitetura dual-layer (forks = user views; cli/tui nativos = operator control plane)

**Patterns (Layer 3) — substituem a noção de "spec" nesta era:**
- [`docs/design-system/10-pattern-ueid-tri-key.md`](design-system/10-pattern-ueid-tri-key.md) — UEID tri-key (join canônico cross-fork)
- [`docs/design-system/11-pattern-frozen-pydantic-strict.md`](design-system/11-pattern-frozen-pydantic-strict.md) — Pydantic v2 strict (frozen=True, extra="forbid")
- [`docs/design-system/13-pattern-fork-adapter-protocol.md`](design-system/13-pattern-fork-adapter-protocol.md) — ForkAdapter Protocol (`@runtime_checkable`)
- [`docs/design-system/14-pattern-idempotency-upstream-id.md`](design-system/14-pattern-idempotency-upstream-id.md) — idempotência via `upstream_id`
- [`docs/design-system/15-pattern-hysteresis-fsm.md`](design-system/15-pattern-hysteresis-fsm.md) — FSM com histerese (substitui PolicyEngine 4-state)

**Validação (Layer 7):**
- [`docs/design-system/50-nielsen-heuristics-coverage.md`](design-system/50-nielsen-heuristics-coverage.md) — cobertura das 10 heurísticas de Nielsen
- [`docs/design-system/51-usability-checklist.md`](design-system/51-usability-checklist.md) — checklist de usabilidade
- [`docs/design-system/52-known-risks-mitigations.md`](design-system/52-known-risks-mitigations.md) — riscos conhecidos + mitigações
- [`docs/design-system/53-adr-007-data-first-gate.md`](design-system/53-adr-007-data-first-gate.md) — ADR-007 data-first gate (gating novos algoritmos)

**Análise crítica (Layer 8):**
- [`docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md`](design-system/09-analise-critica-segunda-ordem-arquitetura.md) — 46 issues de segunda ordem
- [`docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md`](design-system/10-modelo-unificado-auto-feedback-estocastico.md) — modelo unificado auto-feedback estocástico

**Tokens (Layer 5):**
- [`docs/design-system/30-tokens-deep-agent-era.md`](design-system/30-tokens-deep-agent-era.md) — tokens canônicos da era deep-agent
- [`docs/design-system/34-superseded-pav-era-tokens.md`](design-system/34-superseded-pav-era-tokens.md) — mapa de migração PAV → deep-agent

*Para a estrutura completa das 9 camadas e entry points por persona, ver `docs/design-system/00-INDEX.md`.*

