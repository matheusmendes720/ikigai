# ADR-003: IKIGAi como Meta-Brain (Propositivo-Superior)

**Status:** Proposta
**Data:** 2026-06-05
**Autores:** Matheus + AI Agent
**Contexto:** [`life-ops/planner/ikigai_planning/`](../../life-ops/planner/ikigai_planning/) (5 docs drilldown)

---

## 1. Contexto

O sistema tem 5 vetores IKIGAi (passion/skill/market/revenue + course
contextual) que definem a **direção estratégica** do operador. Atualmente,
esses vetores existem em 4 localizações desconexas:

| Local | Arquivo | Conteúdo | Status |
|---|---|---|---|
| Conceito | [`vibe-ops/base/IKIGAi.md`](../base/IKIGAi.md) | 90K, 4 vetores + Hypervisor | 🟢 maduro |
| Vetores operacionais | [`vibe-ops/vectors/`](../vectors/) | 4 docs ricos (passion/skill/market/revenue) | 🟢 |
| Spec | [`vibe-ops/planning/PRD-07-ikigai-vectors.md`](../planning/PRD-07-ikigai-vectors.md) | 311 linhas, Pydantic entities + score algorithms | 🟢 |
| Implementação | [`vibe-ops/src/pipeline/ikigai_scorer.py`](../src/pipeline/ikigai_scorer.py) | 46 linhas, **DIVERGE** do conceitual | 🔴 GAP |

### Problema

O IKIGAi hoje é **reativo** (computa scores após eventos), não
**propositivo-superior** (não dirige as decisões). Falta a camada de
meta-cérebro que:

1. Define **North Star Metrics** (constantes que regem todos os outros sub-sistemas)
2. Propaga **decisões** (não apenas consome dados)
3. Emite **regras de regime** (PUSH/MAINTAIN/REDUCE/RECOVER)
4. Recalibra **pesos** $w_i$ dos vetores por fase

Concretamente, o gap é:
- `ikigai_scorer.py` retorna `{study, dev, health, global}` — **NÃO** é o IKIGAi canônico
- `ikigai_entities.py` tem só 18 linhas (apenas 4 campos)
- Não há 5º vetor (Course) implementado
- Não há propagação explícita de decisões para outros sub-sistemas

---

## 2. Decisão

Adotar a **abstração de Meta-Brain** com 4 propriedades canônicas:

### 2.1. North Star Metrics (22 constantes)

Definidas em [`../../life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md`](../../life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md):

- **Janelas temporais:** 3-5h acordar, 18-21h dormir, 50+10 pomodoro
- **Constantes matemáticas:** λ=0.093, ρ=0.7333, WAVE=15D, CYCLE=45D, PHASE=180D
- **Q_HE thresholds:** PUSH≥0.85, REDUCE≤0.65, RECOVER<0.60
- **IKIGAi weights** $w_1..w_5$ por fase
- **Q_HE components** (passion, meditation, workout, lunch, streak)

### 2.2. Propagation Contract (5 produtos)

Definidos em [`../../life-ops/planner/ikigai_planning/ikigai_propagation.md`](../../life-ops/planner/ikigai_planning/ikigai_propagation.md):

1. **Vector scores** (4+1 floats) → `policy_engine`, `temporal_engine`
2. **Vector weights** ($w_1..w_5$) → `temporal_engine`, `project_engine`
3. **Regime** $\pi(s_t)$ → `temporal_engine`, `cluster_plan`, `cluster_proj`
4. **Phase** (5 phases) → IKIGAi weight recalibration
5. **Alignment score** $\|\vec{I}\|$ → AI Harness, `triagem`

### 2.3. Meta-Heuristics (6 algoritmos determinísticos)

Definidos em [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md):

1. **Regime decision** (PUSH/MAINTAIN/REDUCE/RECOVER) com histerese 2-3d
2. **Phase pivot** (FUNDAÇÃO/BUSCA/HACKATHON/RECOVER/OVERCLOCK) baseado em momentum
3. **Vector weight recalibration** (UCB algorithm)
4. **Opportunity scoring** (fit_score para market signal)
5. **Skill velocity decision** (level promotion)
6. **Cross-cluster priority** (RICE + IKIGAi weights)

### 2.4. Single Source of Truth (4 locais)

| Função | Local canônico |
|---|---|
| Conceito | [`vibe-ops/base/IKIGAi.md`](../base/IKIGAi.md) |
| Vetores operacionais | [`vibe-ops/vectors/`](../vectors/) |
| Spec/entities | [`vibe-ops/planning/PRD-07-ikigai-vectors.md`](../planning/PRD-07-ikigai-vectors.md) |
| Expansão AI-native | [`life-ops/planner/ikigai_planning/`](../../life-ops/planner/ikigai_planning/) |
| Implementação | [`vibe-ops/src/models/ikigai_entities.py`](../src/models/ikigai_entities.py) + [`vibe-ops/src/pipeline/ikigai_scorer.py`](../src/pipeline/ikigai_scorer.py) |

---

## 3. Alternativas Consideradas

### 3.1. Alternativa A: IKIGAi como simples "calculator" (status quo)

**Descrição:** Calcula scores, mas não propaga decisões.

**Motivos da Rejeição:**
- Perde o papel de "cabeça" do sistema
- Não há diferenciação entre "valor passivo" e "valor ativo"
- Cálculos dispersos em 5+ lugares diferentes

### 3.2. Alternativa B: IKIGAi como LLM-decision-maker (Rejeitada)

**Descrição:** LLM decide regime/fase baseado em prompts do estado atual.

**Motivos da Rejeição:**
- Não-determinístico (mesmo input pode dar output diferente)
- Caro (chamadas API, latência)
- Viola princípio "Fully Local" (ADR-001)
- Difícil de auditar (caixa-preta)
- O usuário explicitamente disse: **"nao tera nada de nlp .. processar apenas usando aritmetica"**

### 3.3. Alternativa C: IKIGAi como dashboard read-only (Rejeitada)

**Descrição:** Apenas visualização de scores, sem propagação.

**Motivos da Rejeição:**
- Subutiliza o potencial de meta-cérebro
- Não atende ao "propositivo-superior"
- Não há decisão automatizada (humano tem que decidir manualmente)

### 3.4. Alternativa D: IKIGAi como LLM-assistant (Híbrido)

**Descrição:** Algoritmos determinísticos para 95% das decisões; LLM
apenas como "AI Harness" para sugestões (não-decisões).

**Status:** **Parcialmente aceita** — `vibe-ops/src/pipeline/harness_epistemic.py` e `harness_metrics.py` já implementam este pattern. Mas isso é **acessório**, não substitui o meta-brain determinístico.

---

## 4. Consequências

### 4.1. Positivas

- **Decisões rastreáveis** — todo regime/phase tem `rationale` documentado
- **Single source of truth** — 4 locais com roles distintos (conceito, vetor, spec, expansão)
- **Algoritmos determinísticos** — sem LLM, sem random, auditáveis
- **Histerese** — protege contra oscilação
- **Composabilidade** — algoritmos são funções puras

### 4.2. Negativas / Riscos Aceitos

- **Acoplamento conceitual** — IKIGAi vira ponto único de falha lógico
- **Constantes podem ficar stale** — exige revisão trimestral
- **Mais código a manter** — 5 docs novos + 4+ ADRs
- **Risco de drift** entre conceitual (90K IKIGAi.md) e implementação (gap)

### 4.3. Mitigações

- **Constantes versionadas** em `ikigai_north_star_metrics.md` (git-controlled)
- **Review trimestral** do meta-brain (PHASE_END)
- **Testes de regressão** em `vibe-ops/tests/`
- **`triagem.md`** (ADR-001) para inconsistências
- **5 docs AI-native** em `life-ops/planner/ikigai_planning/` (drilldowns que qualquer coding agent pode seguir)

---

## 5. Implementação (Roadmap)

### Sprint 1 (esta semana) — CRÍTICO

- [ ] Reescrever `vibe-ops/src/models/ikigai_entities.py` (18 → 200 linhas)
  - 5 `IKIGAiVectorEntity` (passion/skill/market/revenue/course)
  - `IKIGAiProfile` com 5 scores + zones + alignment_label
  - `SkillNode`, `OpportunitySignal`
- [ ] Reescrever `vibe-ops/src/pipeline/ikigai_scorer.py` (46 → 100 linhas)
  - 5 vetores canônicos
  - Meta-vetor $\|\vec{I}\|$
  - `alignment_label`
- [ ] Adicionar Course vector (5º contextual) em `PRD-07` e `vectors/`
- [ ] Validar com testes em `vibe-ops/tests/`

### Sprint 2-3

- [ ] Adicionar `ikigai_vectors` table em `schema.sql` (migration `004_ikigai_v1.sql`)
- [ ] Implementar funções puras de `ikigai_meta_heuristics.md` em `pipeline/`
- [ ] Integrar com `policy_engine` (consumir regime)

### Sprint 4+

- [ ] Gerar JSON Schema automático
- [ ] Documentar todas as 14 state machines
- [ ] Refinar meta-heuristics com dados reais

---

## 6. Referências

### Conceito (origem)

- [`vibe-ops/base/IKIGAi.md`](../base/IKIGAi.md) — IKIGAi conceitual (90K)
- [`vibe-ops/vectors/README.md`](../vectors/README.md) — Index dos 4 vetores
- [`vibe-ops/vectors/vector-passion.md`](../vectors/vector-passion.md)
- [`vibe-ops/vectors/vector-skill.md`](../vectors/vector-skill.md)
- [`vibe-ops/vectors/vector-market.md`](../vectors/vector-market.md)
- [`vibe-ops/vectors/vector-revenue.md`](../vectors/vector-revenue.md)

### Spec (entidades)

- [`vibe-ops/planning/PRD-07-ikigai-vectors.md`](../planning/PRD-07-ikigai-vectors.md) — Spec entities
- [`vibe-ops/specs/prd-ikigai-vectors.md`](../specs/prd-ikigai-vectors.md) — Spec mirror

### Expansão AI-native (drilldowns)

- [`../../life-ops/planner/ikigai_planning/README.md`](../../life-ops/planner/ikigai_planning/README.md) — Overview
- [`../../life-ops/planner/ikigai_planning/ikigai_4_vectors.md`](../../life-ops/planner/ikigai_planning/ikigai_4_vectors.md) — 4 vetores + 5º contextual
- [`../../life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md`](../../life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md) — 22 constantes
- [`../../life-ops/planner/ikigai_planning/ikigai_propagation.md`](../../life-ops/planner/ikigai_planning/ikigai_propagation.md) — Data flow
- [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) — 6 algoritmos

### Implementação atual (com gaps)

- [`vibe-ops/src/models/ikigai_entities.py`](../src/models/ikigai_entities.py) — 18 linhas (GAP)
- [`vibe-ops/src/pipeline/ikigai_scorer.py`](../src/pipeline/ikigai_scorer.py) — 46 linhas (GAP, diverge)
- [`vibe-ops/src/schemas/pydantic_v2.py`](../src/schemas/pydantic_v2.py) — PolicyState

### Cluster docs (consumidores)

- [`../../CONCEPTUAL_MODEL.md §3`](../CONCEPTUAL_MODEL.md) — Meta-vetor
- [`../../CLUSTER_PLAN.md §4.5`](../CLUSTER_PLAN.md) — IKIGAi↔PAV
- [`../../CLUSTER_PROJ.md §3`](../CLUSTER_PROJ.md) — RICE+IKIGAi
- [`../../CLUSTER_STUDY.md §3`](../CLUSTER_STUDY.md) — Skill vector

### Math foundations

- [`../../life-ops/planner/Points_of_premisses-task-habits.md §3-4`](../../life-ops/planner/Points_of_premisses-task-habits.md) — Q_HE + histerese

### ADRs relacionados

- [ADR-001: Data Flow Topology](ADR-001-data-flow-topology.md) — topologia
- [ADR-002: Mesh Contracts & State Machines](ADR-002-mesh-contracts-state-machines.md) — contratos
- [ADR-005: Data Mesh Topology](ADR-005-data-mesh-topology.md) — mesh

---

*ADR-003 — v1.0 — 2026-06-05 — IKIGAi como Meta-Brain (propositivo-superior)*
