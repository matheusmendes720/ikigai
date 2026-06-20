# Especificações Técnicas (Specs-First)

> Este diretório é destinado a abrigar os documentos de **engenharia de
> requisitos e Product Design Requirements (PDR)**.
>
> Seguindo a metodologia *Specs-First*, qualquer novo componente (parser,
> sync engine, scorer) deve ter seu **funcionamento, edge cases, e
> contratos de dados** formalizados aqui **antes** de qualquer linha de
> código ser escrita.

## Quick Reference

| Spec | Tipo | Status | Linhas | Tamanho |
|---|---|---|---|---|
| [`SPEC-05-cybernetic-epistemic-mesh.md`](SPEC-05-cybernetic-epistemic-mesh.md) | Arquitetura (Hybrid RAG) | 🟢 | 69 | 3.2K |
| [`schema-frontmatter-contract.md`](schema-frontmatter-contract.md) | YAML schema v1 | ⚪ DEPRECATED | — | 10K |
| [`schema-frontmatter-contract-v2.md`](schema-frontmatter-contract-v2.md) | YAML schema v2 (canônico) | 🟢 | — | 11K |
| [`schema-pydantic-models.md`](schema-pydantic-models.md) | Pydantic v1 | ⚪ DEPRECATED | — | 14K |
| [`schema-pydantic-models-v2.md`](schema-pydantic-models-v2.md) | Pydantic v2 (canônico) | 🟢 | — | 35K |
| [`schema-planner-extension.md`](schema-planner-extension.md) | Planner extension | 🟢 | — | 88K |
| [`prd-temporal-engine.md`](prd-temporal-engine.md) | PRD mirror | 🟢 | — | 1.5K |
| [`prd-habit-tracker.md`](prd-habit-tracker.md) | PRD mirror | 🟢 | — | 1.4K |
| [`prd-study-backlog.md`](prd-study-backlog.md) | PRD mirror | 🟢 | — | 1.5K |
| [`prd-project-execution.md`](prd-project-execution.md) | PRD mirror | 🟢 | — | 1.4K |
| [`prd-metrics-health.md`](prd-metrics-health.md) | PRD mirror | 🟢 | — | 1.3K |
| [`prd-policy-governance.md`](prd-policy-governance.md) | PRD mirror | 🟢 | — | 1.3K |
| [`prd-ikigai-vectors.md`](prd-ikigai-vectors.md) | PRD mirror | 🟢 | — | 1.5K |

## Drilldowns Recentes (Sprint 1, 2026-Q3)

Drilldowns focados no **Cluster PLAN**:

- [`spec-cluster-plan-inputs.md`](spec-cluster-plan-inputs.md) — Schemas YAML + Markdown para inputs manuais
- [`spec-cluster-plan-pipelines.md`](spec-cluster-plan-pipelines.md) — Pipelines: input → SQLite → IKIGAi → reports
- [`spec-cluster-plan-reports.md`](spec-cluster-plan-reports.md) — Formato dos reports diários/semanais/mensais

## How to Use

### Specs-First Workflow

1. **Escrever/atualizar** spec em `vibe-ops/specs/`
2. **Mirror** em `vibe-ops/planning/PRD-*.md` se for requirement
3. **Mirror** em `vibe-ops/contracts/*.yaml` se for contrato
4. **Implementar** código referenciando a spec
5. **Adicionar testes** que validam a spec

### Versioning

- `-v1` = primeira versão (deprecated)
- `-v2` = segunda versão (atual)
- Use SemVer: `-v2.1`, `-v3`, etc.

### Cross-refs

- [`../planning/README.md`](../planning/README.md) — PRDs
- [`../architecture/README.md`](../architecture/README.md) — ADRs
- [`../../ARCHITECTURE_INDEX.md`](../../ARCHITECTURE_INDEX.md) — Master index

---

*README.md — v1.0 — 2026-06-05 — Especificações Técnicas (Specs-First), expanded for Cluster PLAN drilldowns*
