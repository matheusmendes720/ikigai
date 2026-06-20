# Vibe-Ops Planning (Requirements)

> Este diretório serve como a **lousa de requisitos** (PRDs) do Vibe-Ops.
> Aqui vivem as especificações de cada sub-grafo do sistema: entidades,
> state machines, KPIs, anti-patterns.

## Quick Reference

| Cluster | PRD | Status | Linhas | Cluster Doc Canônico |
|---|---|---|---|---|
| 1. Plan (rotinas/blocos) | (drilldowns em CLUSTER_PLAN_*.md) | 🟡 | ~1000 | [`../../CLUSTER_PLAN.md`](../../CLUSTER_PLAN.md) |
| 2. Habit/Temporal | PRD-01 (temporal) + PRD-02 (habit) | 🟢 | 17K | [`../../CLUSTER_PLAN.md`](../../CLUSTER_PLAN.md) §5 |
| 3. Study/PKM | PRD-03 | 🟢 | 13K | [`../../CLUSTER_STUDY.md`](../../CLUSTER_STUDY.md) |
| 4. Project/PMO | PRD-04 | 🟢 | 5K | [`../../CLUSTER_PROJ.md`](../../CLUSTER_PROJ.md) |
| 5. Metrics/Health | PRD-05 | 🟢 | 7K | (métricas — sem cluster doc específico) |
| 6. Policy | PRD-06 | 🟢 | 9K | [`../../CONCEPTUAL_MODEL.md §4`](../../CONCEPTUAL_MODEL.md) |
| 7. IKIGAi Vectors | PRD-07 | 🟢 | 9K | [`../../life-ops/planner/ikigai_planning/`](../../life-ops/planner/ikigai_planning/) |

## Templates

- [`TEMPLATE-micro-ciclo.md`](TEMPLATE-micro-ciclo.md) — Cognitive Debt + MVK (Minimum Viable Knowledge)
- [`TEMPLATE-weekly-review.md`](TEMPLATE-weekly-review.md) — Cybernetic Sensor/Adjuster
- [`TEMPLATE-epic-sprint.md`](TEMPLATE-epic-sprint.md) — Épico → Sprint operável

## Drilldowns Recentes (Sprint 1, 2026-Q3)

Drilldowns focados no **Cluster PLAN** (esta semana):

- [`CLUSTER_PLAN_BRD.md`](CLUSTER_PLAN_BRD.md) — Business Requirements (AI-native)
- [`CLUSTER_PLAN_DATA_MODEL.md`](CLUSTER_PLAN_DATA_MODEL.md) — SQL schema + Pydantic models
- [`CLUSTER_PLAN_USER_STORIES.md`](CLUSTER_PLAN_USER_STORIES.md) — User stories detalhadas
- [`CLUSTER_PLAN_CLI_SPEC.md`](CLUSTER_PLAN_CLI_SPEC.md) — CLI spec completa
- [`CLUSTER_PLAN_ROADMAP.md`](CLUSTER_PLAN_ROADMAP.md) — Roadmap Sprint 1-4 + Q3/Q4

## How to Use

### Se você é um agente implementando Cluster PLAN

1. Leia [`CLUSTER_PLAN_BRD.md`](CLUSTER_PLAN_BRD.md) — Business Requirements
2. Leia [`CLUSTER_PLAN_DATA_MODEL.md`](CLUSTER_PLAN_DATA_MODEL.md) — Schema SQLite
3. Leia [`CLUSTER_PLAN_CLI_SPEC.md`](CLUSTER_PLAN_CLI_SPEC.md) — Comandos CLI
4. Implemente Sprint 1 (CLI `plan journal log` → SQLite → report)

### Se você é um agente implementando Cluster PROJ/STUDY

- Cluster PROJ: leia `PRD-04` + `vibe-ops/contracts/roadmap_v1.json`
- Cluster STUDY: leia `PRD-03` + `vibe-ops/contracts/study_topic_v1.json`

### Se você é um arquiteto

- Leia `vibe-ops/architecture/ADR-001` (topologia) + `ADR-002` (contratos) + `ADR-005` (mesh)

## Cross-refs

- [`../architecture/README.md`](../architecture/README.md) — ADRs
- [`../specs/README.md`](../specs/README.md) — Engineering specs
- [`../../ARCHITECTURE_INDEX.md`](../../ARCHITECTURE_INDEX.md) — Master index
- [`../../CLUSTER_PLAN.md`](../../CLUSTER_PLAN.md) — Standalone Memory Machine Cluster 1

---

*README.md — v1.0 — 2026-06-05 — Vibe-Ops Planning (Requirements), expanded for Cluster PLAN drilldowns*
