# ADR-002: Contratos de Data-Mesh e Máquinas de Estado

**Status:** Aceita
**Data:** 2026-06-05
**Autores:** Matheus (Arquiteto de Produtividade) + AI Agent
**Contexto:** `life/vibe-ops/`

---

## 1. Contexto do Problema

O workspace `life/vibe-ops/` define **7 sub-grafos** (PRDs 01-07), cada um
com suas próprias entidades Pydantic, tabelas SQLite, e regras de negócio.
Esses sub-grafos precisam trocar dados de forma **tipada** e **auditável**.

**Problemas observados:**

1. **Schemas divergentes** — cada sub-grafo tinha sua própria versão de
   entidades similares (e.g., `TimeBlock` em `operational_entities.py` vs
   `daily_block` em `life-ops/life_tatics/`).
2. **Drift de tipos** — valores hardcoded em código (e.g., `study_score` vs
   `skill_score`) sem contrato central.
3. **State machines implícitas** — entidades stateful como `SoftwareProject`
   e `Sprint` tinham transições espalhadas em código, sem documentação
   canônica.
4. **Sem teste de regressão** — quebra de contrato não era detectada
   até produção.

O problema central é: **como garantir consistência entre os 7 sub-grafos
sem acoplamento rígido nem duplicação de validação?**

---

## 2. Decisão

Adotar **2 padrões complementares** que sustentam o data-mesh:

### 2.1. Padrão A: Contratos de Dados Tipados (YAML + Pydantic + SQL)

**Toda entidade stateful tem 3 representações canônicas:**

1. **YAML schema** (em `vibe-ops/src/contracts/*.yaml` ou `vibe-ops/specs/schema-*.md`)
2. **Pydantic v2 model** (em `vibe-ops/src/models/*.py` + `vibe-ops/src/schemas/pydantic_v2.py`)
3. **SQL DDL** (em `vibe-ops/src/storage/schema.sql` + migrations)

**Contratos ativos:**

| Arquivo | Tipo | Status |
|---|---|---|
| `vibe-ops/src/contracts/planning.v1.yaml` | YAML canônico (7531 bytes) | 🟢 |
| `vibe-ops/src/contracts/registry.yaml` | Schema registry | 🟢 |
| `vibe-ops/src/contracts/roadmap_sync_v1.py` | Pydantic sync | 🟢 |
| `vibe-ops/src/contracts/sync_contract_v1.py` | Pydantic sync | 🟢 |
| `vibe-ops/contracts/roadmap_v1.json` | JSON contract | 🟢 |
| `vibe-ops/contracts/study_topic_v1.json` | JSON contract | 🟢 |

**Princípio:** Schema-First (ADR-001 §2.1) — toda mudança no schema é
**primeiro** declarada no YAML, **depois** validada no Pydantic, **depois**
migrada no SQL.

### 2.2. Padrão B: Máquinas de Estado Explícitas

**Toda entidade stateful tem uma state machine documentada e testada.**

| Entidade | State Machine | Origem |
|---|---|---|
| **SoftwareProject** | BACKLOG → ACTIVE → PAUSED → COMPLETED → ARCHIVED | `vibe-ops/planning/PRD-04-project-execution.md §2` |
| **Epic** | PLANNED → IN_PROGRESS → DONE → CANCELLED | Idem |
| **Sprint** | PLANNED → ACTIVE → REVIEW → DONE | Idem |
| **Task** | TODO → IN_PROGRESS → BLOCKED → DONE / CANCELLED | Idem |
| **Habit** | active → paused → archived | `vibe-ops/planning/PRD-02-habit-tracker.md §2` |
| **StudyTopic** | backlog → active → paused → completed | `vibe-ops/planning/PRD-03-study-backlog.md §2` |
| **Regime π(s_t)** | PUSH ↔ MAINTAIN ↔ REDUCE ↔ RECOVER (histerese 2-3d) | `vibe-ops/planning/PRD-06-policy-governance.md §2` |
| **PolicyState** | 4 estados com transições + histerese | `vibe-ops/src/schemas/pydantic_v2.py` |
| **DailyRoutine** | Pending → Active → Recovery → Archived | [`../../CLUSTER_PLAN.md §2`](../CLUSTER_PLAN.md) |
| **IKIGAiVectorEntity** | active → paused → mastered | [`../../life-ops/planner/ikigai_planning/ikigai_4_vectors.md`](../life-ops/planner/ikigai_planning/ikigai_4_vectors.md) |
| **Phase** | FUNDAÇÃO → BUSCA → HACKATHON → RECUPERAÇÃO → OVERCLOCKING | [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md §2`](../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) |
| **Wave** | active → consolidation | `vibe-ops/planning/PRD-01-temporal-engine.md` |
| **Cycle** | active → renormalization → checkpoint | Idem |
| **Phase (Wave context)** | mid → final | Idem |

**Princípio:** Toda transição tem:
- **Trigger** (o que dispara)
- **Pre-condition** (o que deve ser verdade)
- **Post-condition** (o que fica verdade)
- **Audit log** (quem/quando/por quê)

---

## 3. Alternativas Consideradas

### 3.1. Alternativa A: "Tudo via flags boolean" (Rejeitada)

**Descrição:** representar estado como combinações de flags (`is_active`, `is_paused`, `is_archived`).

**Motivos da Rejeição:**
- Histórico perdido (não dá pra saber de onde veio)
- Combinações ilegais possíveis (active + archived simultaneamente)
- Refatoração cara (lógica de flags espalhada)
- Impossível validar com type system

### 3.2. Alternativa B: "Sem contratos, validar em runtime" (Rejeitada)

**Descrição:** confiar em type hints Python sem Pydantic + YAML.

**Motivos da Rejeição:**
- Late errors (só descobre em produção)
- Sem autocomplete confiável
- Impossível gerar JSON Schema para OpenAPI
- Refatoração arriscada (sem testes de contrato)

### 3.3. Alternativa C: "Event Sourcing" (Rejeitada por complexidade)

**Descrição:** armazenar todos os eventos de mudança de estado como log
imutável; estado atual = projeção dos eventos.

**Motivos da Rejeição:**
- Over-engineering para single-user
- Complexidade de queries (precisa materializar projeções)
- Storage overhead (todos os eventos)
- Single source of truth ainda precisa ser derivada

---

## 4. Consequências

### 4.1. Positivas

- **Type safety** — Pydantic valida em runtime
- **Documentação automática** — Pydantic gera JSON Schema
- **Refactor seguro** — IDE e mypy detectam quebras
- **Auditoria** — transitions explícitas + logs
- **Histerese** — protege contra oscilação (regime π(s_t))

### 4.2. Negativas / Riscos Aceitos

- **Curva de aprendizado Pydantic v2** — `model_validator` é poderoso
  mas verboso
- **Mudança em schema = migração** — exige migrations Alembic-style
- **Duplicação YAML ↔ Pydantic** — schemas definidos em 2 lugares
- **Mais código boilerplate** — `BaseSettings`, `Field(ge=0, le=100)` etc.

### 4.3. Mitigações

- Snapshots + `triagem.md` (ADR-001) para dados dessincronizados
- Migrations Alembic-style em `vibe-ops/migrations/`
- Testes de contrato (golden file tests) em `vibe-ops/tests/`
- `verify_mesh.py` (root) para sanity check de imports

---

## 5. Implementação (Sprint 1 + roadmap)

### Sprint 1 (esta semana)
- [ ] Reescrever `vibe-ops/src/models/ikigai_entities.py` (18 → 200 linhas)
- [ ] Reescrever `vibe-ops/src/pipeline/ikigai_scorer.py` (46 → 100 linhas, 5 vetores)
- [ ] Validar `vibe-ops/src/schemas/pydantic_v2.py` (Pydantic v2 canônico)

### Sprint 2-3
- [ ] Adicionar `ikigai_vectors` table em `schema.sql`
- [ ] Implementar state machines explícitas (Python `Enum` + `model_validator`)
- [ ] Adicionar testes de contrato

### Sprint 4
- [ ] Gerar JSON Schema automático para OpenAPI
- [ ] Documentar todas as 14 state machines em tabela

---

## 6. Referências

### ADRs relacionados

- [ADR-001: Data Flow Topology](ADR-001-data-flow-topology.md) — topologia
- [ADR-003: IKIGAi as Meta-Brain](ADR-003-ikigai-as-meta-brain.md) — IKIGAi
- [ADR-004: Hybrid RAG Strategy](ADR-004-hybrid-rag-strategy.md) — RAG
- [ADR-005: Data Mesh Topology](ADR-005-data-mesh-topology.md) — mesh

### Schemas & Models

- [`vibe-ops/src/schemas/pydantic_v2.py`](../src/schemas/pydantic_v2.py) — Pydantic v2 canônico
- [`vibe-ops/src/schemas/registry.py`](../src/schemas/registry.py) — Schema registry
- [`vibe-ops/src/models/`](../src/models/) — 14 entity files
- [`vibe-ops/src/storage/schema.sql`](../src/storage/schema.sql) — SQL canônico
- [`vibe-ops/specs/schema-pydantic-models-v2.md`](../specs/schema-pydantic-models-v2.md) — Spec Pydantic v2
- [`vibe-ops/specs/schema-frontmatter-contract-v2.md`](../specs/schema-frontmatter-contract-v2.md) — Spec frontmatter v2

### PRDs (origem das state machines)

- [`vibe-ops/planning/PRD-01-temporal-engine.md`](../planning/PRD-01-temporal-engine.md) — Wave/Cycle/Phase state
- [`vibe-ops/planning/PRD-02-habit-tracker.md`](../planning/PRD-02-habit-tracker.md) — Habit state
- [`vibe-ops/planning/PRD-03-study-backlog.md`](../planning/PRD-03-study-backlog.md) — StudyTopic state
- [`vibe-ops/planning/PRD-04-project-execution.md`](../planning/PRD-04-project-execution.md) — Project/Epic/Sprint/Task state
- [`vibe-ops/planning/PRD-06-policy-governance.md`](../planning/PRD-06-policy-governance.md) — Regime state
- [`vibe-ops/planning/PRD-07-ikigai-vectors.md`](../planning/PRD-07-ikigai-vectors.md) — IKIGAi vector entities

### Cluster docs

- [`../../CLUSTER_PLAN.md`](../CLUSTER_PLAN.md) — DailyRoutine state
- [`../../life-ops/planner/ikigai_planning/`](../life-ops/planner/ikigai_planning/) — IKIGAi state machines

### Implementação atual

- [`vibe-ops/src/cybernetics/daily_loop.py`](../src/cybernetics/daily_loop.py) — Cybernetic loop state
- [`vibe-ops/src/pipeline/policy_engine.py`](../src/pipeline/policy_engine.py) — 4-state machine
- [`vibe-ops/src/middleware/sync_engine.py`](../src/middleware/sync_engine.py) — Sync orchestrator

---

*ADR-002 — v1.0 — 2026-06-05 — Contratos de Data-Mesh e Máquinas de Estado*
