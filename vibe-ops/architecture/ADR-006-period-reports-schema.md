# ADR-006: Period Reports Template Schema — Algoritmo de Escrita por Período

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Matheus + Hephaestus (planning session)
**Contexto:** [`_templates_periodos/`](../../) (5 templates em PT-BR) · [`strategics/00-ÍNDICE-PROGRESSIVO.md`](../../strategics/00-ÍNDICE-PROGRESSIVO.md) · [`specs/vault-bidirectional-sync/`](../../specs/vault-bidirectional-sync/)

---

## 1. Contexto

O Algorithmic Life OS tem uma **pirâmide de granularidade** documentada em [`strategics/00-ÍNDICE-PROGRESSIVO.md`](../../strategics/00-ÍNDICE-PROGRESSIVO.md):

```
SONHO (6-12m) → AVALIAÇÃO TRIMESTRAL (90d) → ONDA (45d úteis)
   → REVISÃO SEMANAL (7d) → RELATÓRIO DIÁRIO (1d)
```

Cada nível consome o nível abaixo e emite um **veredito algorítmico** que dirige o próximo ciclo.

### Problema

Antes desta ADR, existiam apenas 3 templates de planejamento no codebase, **não-alinhados** com a pirâmide do índice:

| Template existente | Período | Gap |
|---|---|---|
| `vibe-ops/planning/TEMPLATE-micro-ciclo.md` | 1-7 dias (micro-ciclo) | Sobrepõe com Relatório Diário |
| `vibe-ops/planning/TEMPLATE-weekly-review.md` | 7 dias | Não tem verdict algorítmico nem policy_recommendation |
| `vibe-ops/planning/TEMPLATE-epic-sprint.md` | 1-4 semanas | Conflita com Onda (45d) |

E o sistema **não conseguia**:

1. **Ingerir reports estruturados** no `vibe_ops.db` (sync layer do `vault-bidirectional-sync` não tinha contrato de schema)
2. **Visualizar trends** por período (Dataview dashboards só mostravam notas avulsas)
3. **Aplicar verdicts** algoritmicamente (veredito era narrativa subjetiva, não função)
4. **Cruzar hierarquia** sonho → trimestral → onda → semanal → diário sem FKs explícitas

---

## 2. Decisão

Adotar **5 templates oficiais** alinhados 1:1 com a pirâmide do índice, com **schema contract YAML unificado** que permite parsing determinístico pelo sync layer.

### 2.1. Os 5 Templates

| # | Arquivo | Período | Cluster | Verdict Algoritmo |
|---|---------|---------|---------|-------------------|
| 1 | `01-sonho.md` | 6-12 meses | Estratégico | 3-Axis FalsifiableHypothesis |
| 2 | `02-avaliacao-trimestral.md` | 90 dias | Estratégico | Teste de Fogo lite (5 dimensões, média ≥ 0.70) |
| 3 | `03-onda.md` | 45 dias úteis | Tático | Route Correction (≥ 0.75 / ≥ 0.50 / < 0.50) |
| 4 | `04-revisao-semanal.md` | 7 dias | Tático | Policy Adjustment (PASS→PUSH / PARTIAL→MAINTAIN / FAIL→REDUCE) |
| 5 | `05-relatorio-diario.md` | 1 dia | Operacional | Completion Rate ≥ 0.80 |

### 2.2. Schema Contract (YAML Frontmatter)

**Localização:** [`_templates_periodos/00-README.md`](../../) §3

#### Required (6 campos)

```yaml
type: period_report                  # sempre
period: daily|weekly|onda|quarterly|sonho
date_start: YYYY-MM-DD
date_end: YYYY-MM-DD
verdict: <enum por period>           # ver §2.3
verdict_score: float                 # 0.00 - 1.00
```

#### Optional (recomendados)

```yaml
template_version: 1.0
ikigai_cluster: plan
entity_type: period_report
sonho_id: <fk>
ikigai_vector: passion|skill|market|revenue
xp_gained: int
mastery_delta: string
policy_recommendation: push|maintain|reduce|recover
parent_period: <fk para nível acima>
status: draft|active|closed
tags: [period/<name>, ikigai/plan, ...]
```

### 2.3. Verdict Enums por Period

```yaml
daily:        [PASS, PARTIAL, FAIL]
weekly:       [PASS, PARTIAL, FAIL]
onda:         [CONTINUE_WAVE, CORRECT_TRAJECTORY, KILL_WAVE]
quarterly:    [PASS, PARTIAL, FAIL]
sonho:        [ACTIVE, VALIDATED, FALSIFIED, PIVOTED, ABANDONED]
```

### 2.4. Hierarquia Parent-Child

```
01-sonho (parent_period: null, sonho_id: self)
   ↑
02-avaliacao-trimestral (parent_period: sonho_id)
   ↑
03-onda (parent_period: id_trimestral_pai)
   ↑
04-revisao-semanal (parent_period: id_onda_pai)
   ↑
05-relatorio-diario (parent_period: id_semana_pai)
```

**Regra:** todo report aponta para o pai via `parent_period` no frontmatter. Isso permite walk recursivo no sync layer.

### 2.5. Algoritmo de Verdict (Padrão)

```
1. Coleta métricas do período (do nível abaixo)
2. Calcula score = média ponderada de N dimensões
3. Aplica thresholds:
   - score >= threshold_high → verdict = PASS / CONTINUE / VALIDATED
   - threshold_low <= score < threshold_high → verdict = PARTIAL / CORRECT / PIVOTED
   - score < threshold_low → verdict = FAIL / KILL / FALSIFIED / ABANDONED
4. Recomenda PolicyEngine state para o próximo período
5. Persiste via sync bidirecional
```

**Pesos padrão:**

| Dimensão | Peso | Origem |
|----------|:---:|--------|
| Completion Rate | 0.50 | Diário → Semanal |
| Sleep Hours | 0.20 | Diário |
| Q_HE | 0.20 | Diário |
| Velocity | 0.10 | Semanal → Onda |

### 2.6. Storage + Sync

- **Vault location:** `_templates_periodos/` (Obsidian)
- **Filled reports:** `_periodos/` (separado, append-only)
- **Sync to DB:** `life sync vault --folder _templates_periodos`
- **DB table:** `period_reports` (nova tabela em `vibe_ops.db`)
- **Indexes:** por `sonho_id`, `ikigai_vector`, `verdict`, `period`

### 2.7. Downstream (v1)

- **Dataview/Bases dashboard:** [`3_indice/00_Period_Reports_Dashboard.md`](../../) com 10 views (status, trends, anomalies, policy trail, IKIGAi alignment)

### 2.8. Downstream (v1.1, deferred)

- **PolicyEngine consume verdict:** `life sync code` exporta verdict + policy_recommendation de volta ao vault
- **FalsifiableHypothesis evaluator (T7 do vault-bidirectional-sync):** consome sonho verdicts
- **Mermaid cycle diagrams:** auto-gerados de completion data

---

## 3. Trade-offs

### Por que 5 e não 10 templates?

O índice define 10 níveis (incluindo Rotina Inicial/Final, Supervisão Quinzenal, Revisão Mensal, Teste de Fogo). Decidimos cobrir apenas **5 porque**:

| Decidido | Deferido (v1.1 / v2) | Razão |
|----------|----------------------|-------|
| Relatório Diário | Rotina Inicial/Final | Podem ser perguntas dentro do Diário (não precisam template próprio) |
| Revisão Semanal | Supervisão Quinzenal | Quinzenal = 2× Semanal (derivável, não precisa artifact próprio) |
| Onda | (n/a) | — |
| Avaliação Trimestral | Revisão Mensal | Mensal = Trimestral ÷ 3 (pode ser inferido, não precisa artifact próprio) |
| Sonho | Teste de Fogo | Teste de Fogo = Sonho + métricas macro (incorporado no Sonho) |

### Por que YAML frontmatter e não JSON-LD?

YAML frontmatter é **nativo do Obsidian**, parseado pela lib `python-frontmatter` (já em uso no `vibe-ops/src/pipeline/frontmatter_parser.py`), e legível por humanos sem overhead. JSON-LD seria mais semântico mas adiciona uma camada de encoding.

### Por que PT-BR e não inglês?

A pirâmide do índice é PT-BR. Templates em PT-BR mantêm coerência com `strategics/` e reduzem overhead cognitivo do operador (Matheus). Field names em inglês (snake_case) porque são processados por código Python.

### Por que `verdict` enums diferentes por period?

Cada nível tem **significado distinto** para o verdict:
- **Sonho:** VALIDATED/FALSIFIED = conclusão da hipótese
- **Onda:** CONTINUE_WAVE/CORRECT_TRAJECTORY = ação corretiva específica do nível tático
- **Diário/Semanal/Trimestral:** PASS/PARTIAL/FAIL = gradação uniforme

Unificar todos seria perder semântica. Manter enums separados preserva a linguagem do domínio.

### Por que 6 required fields?

Mínimo para o sync layer:
- `type` + `period` → roteamento
- `date_start` + `date_end` → timeline queries
- `verdict` + `verdict_score` → dashboards + trending

Tudo mais é enhancement opcional (não bloqueia ingestão).

---

## 4. Consequências

### Positivas

1. **Sync determinístico.** 5 templates × 6 required fields = contrato fechado. Sync layer pode validar uniformemente.
2. **Vereditos algoritmicos.** Não há mais ambiguidade sobre "passou ou não" — é função, não opinião.
3. **Hierarquia FK explícita.** Cross-references sonho → trimestral → onda → semanal → diário via `parent_period`.
4. **Dataview nativo.** Dashboard de 10 views funciona sem código custom — só queries.
5. **Append-only real.** Reports preenchidos vão para `_periodos/` (separado), `_templates_periodos/` mantém originais imutáveis.
6. **Reuso.** Algoritmo de verdict é o mesmo padrão (3 thresholds) — copy-paste na mentalidade.

### Negativas / Riscos

1. **Risco de inércia.** Se o operador não preencher o diário, a pirâmide quebra no nível 0. Mitigação: dashboard View 1 mostra gaps de cobertura (dias sem report).
2. **Sync duplica estado.** `vibe_ops.db` tem cópias dos reports. Mitigação: sync é one-way (vault → code) e append-only (não deleta).
3. **Thresholds arbitrários.** 0.80 / 0.65 / 0.50 para completion_rate são heurísticos. Mitigação: ADR-006 será revisada após 3 meses de dados empíricos.
4. **Templates verbosos.** Cada report tem 9-10 seções. Mitigação: section headers servem como checklist; usuário não precisa preencher tudo.
5. **Verdict FAIL não dispara ação automática.** Em v1, dashboard mostra o FAIL, mas não há auto-replan. Mitigação: v1.1 inclui `replan` CLI command.

### Trade-off Explícito

Escolhemos **algoritmo > opinião** mesmo sabendo que isso torna os templates **menos flexíveis**. Templates mais flexíveis (com verdict subjetivo) seriam mais confortáveis, mas não gerariam dados úteis para trending. Optamos por **dados > conforto** porque o objetivo é fechar o loop cibernético.

---

## 5. Implementação

### Já Feito (2026-06-26)

- [x] 5 templates PT-BR criados em `_templates_periodos/`
- [x] Schema contract documentado em `00-README.md`
- [x] Dashboard Dataview de 10 views em `3_indice/00_Period_Reports_Dashboard.md`
- [x] Hierarquia parent-child via `parent_period` FK

### Próximo (v1.1)

- [ ] Sync layer (T2 do `vault-bidirectional-sync`) ingere `entity_type: period_report` em nova tabela `period_reports`
- [ ] `Life sync vault --folder _templates_periodos` disponível
- [ ] 1 exemplo preenchido (synthetic) para validação do parser
- [ ] Property tests para o algoritmo de verdict (todas as 15 combinações)

### Próximo (v2)

- [ ] PolicyEngine consume verdict → emite setpoints
- [ ] FalsifiableHypothesis evaluator cruza com sonhos
- [ ] Mermaid cycle diagrams auto-gerados
- [ ] Replan CLI command (auto-trigger em FAIL)

---

## 6. Cross-references

### Templates

- [`_templates_periodos/00-README.md`](../../) — Schema contract master
- [`_templates_periodos/01-sonho.md`](../../) — Sonho (6-12m)
- [`_templates_periodos/02-avaliacao-trimestral.md`](../../) — Trimestral (90d)
- [`_templates_periodos/03-onda.md`](../../) — Onda (45d úteis)
- [`_templates_periodos/04-revisao-semanal.md`](../../) — Semanal (7d)
- [`_templates_periodos/05-relatorio-diario.md`](../../) — Diário (1d)

### Dashboard

- [`3_indice/00_Period_Reports_Dashboard.md`](../../) — 10 views Dataview

### Strategic Docs

- [`strategics/00-ÍNDICE-PROGRESSIVO.md`](../../strategics/00-ÍNDICE-PROGRESSIVO.md) — Pirâmide de granularidade (origem)

### Sync / Engine

- [`vibe-ops/specs/spec-cluster-plan-pipelines.md`](../../vibe-ops/specs/spec-cluster-plan-pipelines.md) — Cluster PLAN pipelines
- [`vibe-ops/specs/spec-cluster-plan-inputs.md`](../../vibe-ops/specs/spec-cluster-plan-inputs.md) — Cluster PLAN inputs
- [`vibe-ops/src/pipeline/policy_engine.py`](../../vibe-ops/src/pipeline/policy_engine.py) — PolicyEngine FSM (4-state)
- [`vibe-ops/src/middleware/sync_engine.py`](../../vibe-ops/src/middleware/sync_engine.py) — Sync middleware (one-way → bidirectional)
- [`specs/vault-bidirectional-sync/PRODUCT.md`](../../specs/vault-bidirectional-sync/PRODUCT.md) — Sync plan (T2 ingere period_reports)

### IKIGAi / Cluster PLAN

- [`vibe-ops/base/IKIGAi.md`](../../vibe-ops/base/IKIGAi.md) — IKIGAi canonical spec
- [`vibe-ops/planning/PRD-07-ikigai-vectors.md`](../../vibe-ops/planning/PRD-07-ikigai-vectors.md) — IKIGAi vectors PRD
- [`life-ops/planner/ikigai_planning/`](../../life-ops/planner/ikigai_planning/) — IKIGAi drilldowns (5 docs)

### ADRs Relacionados

- [`ADR-001-data-flow-topology.md`](./ADR-001-data-flow-topology.md) — Topologia geral
- [`ADR-002-mesh-contracts-state-machines.md`](./ADR-002-mesh-contracts-state-machines.md) — Contratos mesh
- [`ADR-003-ikigai-as-meta-brain.md`](./ADR-003-ikigai-as-meta-brain.md) — IKIGAi meta-brain

---

## 7. Revisão

Esta ADR deve ser revisada após:

- **3 meses de uso:** validar se os thresholds (0.80/0.65/0.50) fazem sentido empiricamente
- **6 meses:** revisar se a pirâmide de 5 níveis é suficiente ou se precisamos de camadas intermediárias
- **1 ano:** avaliar se o sync está performando bem (latência, idempotência, conflicts)

Se algum threshold se mostrar muito permissivo/rigoroso, esta ADR é o lugar para registrar a mudança (com diff de rationale).

---

*ADR-006 · Aceita · 2026-06-26 · Matheus + Hephaestus · Cluster PLAN · IKIGAi Sys-01 · Schema Contract v1.0*