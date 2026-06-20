# CLUSTER PLAN — Roadmap de Implementação

> Roadmap de **Q3 2026** para o Cluster PLAN, em sprints semanais.

---

## 1. Visão Geral

| Sprint | Data | Foco | Deliverables | Story Points |
|---|---|---|---|---|
| **Sprint 1** | 08-14 Jun | Inputs manuais + persistência | 3 user stories (US-001/002/003) + report semanal básico | 21 |
| **Sprint 2** | 15-21 Jun | Wave reviews | US-005 (Mid-Wave) + US-006 (Wave-End) | 13 |
| **Sprint 3** | 22-28 Jun | Cycle review | US-007 (Cycle-End) | 8 |
| **Sprint 4** | 29 Jun-05 Jul | Phase review + recovery | US-008 + US-009 + US-010 | 13 |
| **Sprint 5** | 06-12 Jul | Refinamento | Polish + tests + docs | 8 |
| **Sprint 6** | 13-19 Jul | IKIGAi integration | Reescrever `ikigai_scorer.py` + entities | 13 |
| **Sprint 7** | 20-26 Jul | Vector weights UCB | Implementar `weight_recalibrate_ucb()` | 8 |
| **Sprint 8** | 27 Jul-02 Ago | Phase pivot | Implementar `compute_phase()` | 8 |
| **Sprint 9** | 03-09 Ago | Polish Q3 | Testes, docs, refactor | 8 |
| **Sprint 10** | 10-16 Ago | TW sync (cluster PROJ) | Sincronizar auto_indagacao ↔ TW | 13 |
| **Sprint 11** | 17-23 Ago | Study sync (cluster STUDY) | Sincronizar auto_indagacao ↔ StudySession | 13 |
| **Sprint 12** | 24-30 Ago | Q3 final | Documentation, retrospective | 8 |

**Total Q3 2026:** ~134 story points (≈ 12 sprints × 1 dev)

---

## 2. Sprint 1 — Detalhamento

### Goals

- Operador pode registrar 1 semana de journaling
- Relatório semanal básico funciona (orçado × realizado)

### User Stories

- US-001: Cold-Start Matinal
- US-002: Re-Entry Tarde
- US-003: Shutdown Noturno
- US-004: Report Semanal (básico)

### Tasks

#### Setup (Dia 1)

- [ ] Criar migration `004_cluster_plan_v1.sql` (6 tables)
- [ ] Criar `vibe-ops/src/models/cluster_plan_entities.py` (Pydantic v2)
- [ ] Setup test fixtures (in-memory SQLite)

#### CLI (Dias 2-3)

- [ ] Implementar `plan journal log --morning|--afternoon|--evening` (Typer)
- [ ] Wizard interativo (1 pergunta por vez, não dump all-at-once)
- [ ] Validação: idempotência (UNIQUE), Q_HE calc, regime predição

#### Report (Dia 4)

- [ ] Implementar `plan report weekly` (queries SQLite + aritmética)
- [ ] Output markdown + JSON
- [ ] Testes: scenarios com 0/3/7 dias registrados

#### Tests (Dia 5)

- [ ] `vibe-ops/tests/test_journal.py` (in-memory SQLite)
- [ ] `vibe-ops/tests/test_regime.py` (histerese)
- [ ] `vibe-ops/tests/test_cli_plan.py` (CLI integration)

#### Docs (Dia 6)

- [ ] Update [`../../CLUSTER_PLAN.md §7`](../../CLUSTER_PLAN.md) com CLI real
- [ ] Update `life-ops/life_tatics/README.md` com link para PLAN
- [ ] Update [`../../ARCHITECTURE_INDEX.md`](../../ARCHITECTURE_INDEX.md) §3 (Cluster 1 = OK)

#### Polish (Dia 7)

- [ ] Buffer para imprevistos
- [ ] Demo para 1 dia completo (morning → afternoon → evening → next morning)

### Definition of Done (Sprint 1)

- [ ] Operador pode rodar `plan journal log` 3x/dia por 7 dias consecutivos
- [ ] `plan report weekly` retorna em ≤ 2 segundos
- [ ] Zero chamadas LLM/embeddings (verificável via logs)
- [ ] Testes passam (≥ 80% coverage)
- [ ] Documentação atualizada
- [ ] PR review aprovado

---

## 3. Sprint 2 — Wave Reviews

### Goals

- Operador pode revisar WAVE no meio (d7) e fim (d15)

### User Stories

- US-005: Mid-Wave Review
- US-006: Wave-End Review

### Tasks

- [ ] Adicionar tabela `wave_reviews`
- [ ] CLI: `plan wave review --mid|--end`
- [ ] Algoritmo $H_{wave}$: query `auto_indagacao.date` por wave_id
- [ ] Decisão de continuidade (manter/pivotar/pausar hábito)

---

## 4. Sprint 3 — Cycle Review

### Goals

- Operador pode consolidar CYCLE (45d)

### User Stories

- US-007: Cycle-End Review

### Tasks

- [ ] CLI: `plan cycle review --end`
- [ ] Algoritmo: 3 WAVE reviews consolidadas
- [ ] HALF_QUARTER check (45D ≡ 45D)
- [ ] Skill velocity + ROI vector

---

## 5. Sprint 4 — Phase + Recovery + Chaos

### Goals

- Operador pode consolidar PHASE (180d)
- Operador pode ativar RECOVER ou TRAVERSE CHAOS

### User Stories

- US-008: Phase-End Review
- US-009: Recovery Day
- US-010: Traverse Chaos

### Tasks

- [ ] CLI: `plan phase review --end`
- [ ] CLI: `plan regime --recover|--traverse`
- [ ] Teste de Fogo (5 dimensões)
- [ ] Histerese completa (3d up, 2d down, 4d traverse)

---

## 6. Sprint 5 — Refinamento Q3

### Goals

- Polish + testes + docs
- Retrospectiva Q3

### Tasks

- [ ] Test coverage ≥ 90%
- [ ] Performance: todos os reports ≤ 2s
- [ ] UX: mensagens de erro claras
- [ ] Docs: tutorial end-to-end

---

## 7. Sprint 6 — IKIGAi Integration

### Goals

- Reescrever `ikigai_scorer.py` para usar 5 vetores canônicos

### Tasks

- [ ] Reescrever `vibe-ops/src/models/ikigai_entities.py` (200 linhas)
- [ ] Reescrever `vibe-ops/src/pipeline/ikigai_scorer.py` (100 linhas)
- [ ] Adicionar 5º vetor (Course) em `PRD-07`
- [ ] Testes: regressão (4 vetores antigos devem continuar funcionando)

---

## 8. Sprint 7-8 — Meta-Heuristics

### Goals

- Implementar UCB weight recalibration
- Implementar phase pivot

### Tasks

- [ ] Função `weight_recalibrate_ucb()` em `vibe-ops/src/pipeline/`
- [ ] Função `compute_phase()` em `vibe-ops/src/pipeline/`
- [ ] Trimestral cron (PHASE_END)
- [ ] Logging auditável

---

## 9. Sprint 9-10 — Sync com TW (Cluster PROJ)

### Goals

- Sincronizar `auto_indagacao` com Taskwarrior
- Tasks PROJ recebem tags IKIGAi automaticamente

### Tasks

- [ ] Schema: `tw_uda_ikigai` mapping table
- [ ] CLI: `plan tw sync` (sync bidirecional)
- [ ] Triagem de tasks órfãs

---

## 10. Sprint 11 — Sync com Study (Cluster STUDY)

### Goals

- Sincronizar `auto_indagacao` com `StudySession`
- Streak days cruzam com cluster STUDY

---

## 11. Sprint 12 — Q3 Final

### Goals

- Documentação final
- Retrospectiva Q3

### Tasks

- [ ] CHANGELOG.md atualizado
- [ ] Sprint retrospective
- [ ] Roadmap Q4 2026

---

## 12. Q4 2026 (preliminar)

- Sincronização TW/STUDY completa
- AI Harness (sugestões, não-decisões)
- Streamlit dashboard (read-only)
- Neo4j opcional para grafo de dependencies
- Hybrid RAG (ADR-004) Sprint 2+

---

## 13. Cross-refs

- [`CLUSTER_PLAN_BRD.md`](CLUSTER_PLAN_BRD.md) — Business Requirements
- [`CLUSTER_PLAN_USER_STORIES.md`](CLUSTER_PLAN_USER_STORIES.md) — User stories
- [`CLUSTER_PLAN_CLI_SPEC.md`](CLUSTER_PLAN_CLI_SPEC.md) — CLI spec
- [`CLUSTER_PLAN_DATA_MODEL.md`](CLUSTER_PLAN_DATA_MODEL.md) — Schema + Pydantic
- [`../../CLUSTER_PLAN.md §10-§12`](../../CLUSTER_PLAN.md) — Cross-refs + revisão
- [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) — Algoritmos
- [`../../ARCHITECTURE_INDEX.md`](../../ARCHITECTURE_INDEX.md) — Master index

---

*CLUSTER_PLAN_ROADMAP.md — v1.0 — 2026-06-05 — Roadmap de implementação Q3 2026*
