# ADR-001: Topologia de Fluxo de Dados do Vibe-Ops Data-Mesh (Multi-Cluster)

**Status:** Aceita
**Data:** 2026-05-03 (original) | **2026-06-05 (expandido para multi-cluster)**
**Autores:** Matheus (Arquiteto de Produtividade) + AI Agent
**Contexto:** `life/vibe-ops/`

> **v1.0 → v1.1 — Expansão multi-cluster**
>
> Este ADR foi originalmente escrito em 2026-05-03 com **3 domínios**
> (PLANNING, MIDDLEWARE, EXECUTION). Após a sessão de orquestração de
> 2026-06-05 (4 swarm-tasks criando `ARCHITECTURE_INDEX.md`, 5 docs
> `ikigai_planning/`, 5 ADRs, 9 drilldowns em `planning/`/`specs/`),
> a arquitetura cresceu para **5 sub-sistemas autônomos** com **4 facetas
> documentadas**. Este ADR agora reflete essa totalidade.

---

## 1. Contexto do Problema

O workspace `produtividade` opera com **múltiplos sistemas desacoplados** que precisam trocar dados para gerar insights de produtividade:

### 1.1. Sistemas Originais (2026-05-03)

| Sistema | Tipo | Dado Principal | Formato Nativo |
|:--------|:-----|:---------------|:---------------|
| Markdown/Obsidian | Planejamento estratégico | Sonhos, Objetivos, Metas, Tarefas | YAML Frontmatter + Markdown |
| Taskwarrior | Execução operacional | Tasks, Projetos, Status, Prioridade | JSON (`.task` binary) |
| Timewarrior | Rastreamento de tempo | Intervalos de início/fim por tag | JSON/Text (`.timew`) |
| GnuCash/fin_ops | Contabilidade e ROI | Receitas, Despesas, Valoração | SQLite / CSV |
| IKIGAi Model | Framework de decisão | Vetores de alinhamento estratégico | Markdown + Equações |
| Day Logger (legado) | Input diário de hábitos | Scores binários + horas | CSV/pandas |

### 1.2. Sistemas Atuais (2026-06-05 — pós-orquestração)

Após a criação de 3 cluster docs (`CLUSTER_PLAN.md`, `CLUSTER_PROJ.md`, `CLUSTER_STUDY.md`), 5 docs IKIGAi planning, e 9 drilldowns, o workspace agora tem **5 sub-sistemas autônomos**:

| Sub-sistema | Cluster Doc | Domínio primário | Estado Atual |
|---|---|---|---|
| **1. Plan + Personal Productivity** | [`../../CLUSTER_PLAN.md`](../../CLUSTER_PLAN.md) (1861 linhas, v1.1) | Routines, blocos, rituais, IKIGAi↔PAV | 🟡 Sprint 1 |
| **2. Project PMO↔TW** | [`../../CLUSTER_PROJ.md`](../../CLUSTER_PROJ.md) (~1100 linhas) | SoftwareProject, Epic, Sprint, Task | 🟡 parcial |
| **3. Studies/PKM** | [`../../CLUSTER_STUDY.md`](../../CLUSTER_STUDY.md) (~900 linhas) | Skill, Topic, Material, Session | 🟡 parcial |
| **4. IKIGAi (Meta-Brain)** | [`../../life-ops/planner/ikigai_planning/`](../../life-ops/planner/ikigai_planning/) (5 docs) | 5 vetores canônicos + meta-vetor | 🟡 docs OK, code GAP |
| **5. Habit/Cybernetics** | [`../../CONCEPTUAL_MODEL.md §4`](../../CONCEPTUAL_MODEL.md) | Q_HE, histerese, regime | 🟢 |

O problema central é: **como conectar esses 5 sub-sistemas de forma que
o dado flua de ponta a ponta sem duplicação, sem perda de contexto, e
sem exigir input manual complexo do operador humano?**

---

## 2. Decisão

Adotar uma arquitetura **Data-Mesh Desacoplada** com **5 sub-sistemas
autônomos** + **Middleware Python centralizado** que atua como
"barramento de integração" entre todos os domínios.

### 2.1. Princípios Arquiteturais Eleitos

| Princípio | Justificativa | Origem |
|:----------|:-------------|:-------|
| **Fully Local** | Zero dependência de cloud. Todos os dados residem no filesystem local. Soberania total. | ADR-001 §2.1 |
| **Append-Only** | Documentos de planejamento nunca são sobrescritos — apenas expandidos. Garante rastreabilidade. | ADR-001 §2.1 |
| **Single Source of Truth (por domínio)** | Cada sistema "manda" no seu domínio de dados. Não há duplicação autoritativa. | ADR-001 §2.1 |
| **Schema-First** | Todo contrato de dados é definido ANTES da implementação. Pydantic valida antes de injetar. | ADR-001 §2.1 |
| **Human-in-the-Loop para Metadados** | O humano escreve Markdown. O pipeline extrai e enriquece. O humano aprova triagens. | ADR-001 §2.1 |
| **Idempotência** | Re-executar o pipeline não cria duplicatas. `upstream_id` como chave de idempotência. | ADR-001 §2.1 |
| **Determinismo (v1.1)** | Sem LLM no pipeline diário/semanal. Apenas aritmética + funções algébricas. | [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) |
| **5 Sub-Sistemas Autônomos (v1.1)** | Cada cluster evolui independentemente; cross-cluster joins via middleware. | [`../../ARCHITECTURE_INDEX.md §5`](../../ARCHITECTURE_INDEX.md) |
| **IKIGAi como Meta-Brain (v1.1)** | Propósito superior: governa regime, fase, e pesos $w_i$. Não apenas consome dados — propaga decisões. | [ADR-003](ADR-003-ikigai-as-meta-brain.md) |
| **6 Contratos Cross-Domain (v1.1)** | C1-C6 entre os 4 domínios (PLANNING/STUDY/DEV/METRICS). | [ADR-005 §2.2](ADR-005-data-mesh-topology.md) |

### 2.2. Topologia Final (v1.1 — Multi-Cluster)

```
                    ┌────────────────────────────────────────────┐
                    │       TIER 0 — INTENÇÃO ESTRATÉGICA        │
                    │  docs/, strategics/, vibe-ops/base/,      │
                    │  life-ops/planner/ikigai_planning/         │
                    │  IKIGAi como meta-brain (5 vetores)        │
                    │  North Star Metrics (22 constantes)        │
                    │  Meta-Heuristics (6 algoritmos)            │
                    └────────────────┬───────────────────────────┘
                                     │ IKIGAi vectors + regime π(s_t)
                                     ▼
                    ┌────────────────────────────────────────────┐
                    │       TIER 1 — ORQUESTRAÇÃO (CLI Hub)      │
                    │  life/centrals/ (task, finance, knowledge) │
                    │  life/handlers/ (daily.py, weekly.py)       │
                    │  life/plugins/ (lifecycle hooks)            │
                    │  life/cli/ (Typer main)                     │
                    │                                              │
                    │  3 Cluster Docs canônicos:                   │
                    │  - CLUSTER_PLAN.md (Cluster 1)              │
                    │  - CLUSTER_PROJ.md (Cluster 2)              │
                    │  - CLUSTER_STUDY.md (Cluster 3)             │
                    └────────────────┬───────────────────────────┘
                                     │ Typer sub-apps + subprocess
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │         TIER 2 — MESH CIBERNÉTICO (Middleware Python)       │
        │                                                              │
        │   ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
        │   │ 5 Sub-Sistemas  │  │  6 Cross-Domain │  │  AI Harness  │ │
        │   │  Autônomos       │  │  Contratos      │  │  (acessor.)  │ │
        │   └────────┬────────┘  └────────┬────────┘  └──────┬───────┘ │
        │            │                     │                   │       │
        │   ┌────────▼────────┐  ┌────────▼────────┐           │       │
        │   │ 1. PLAN         │  │ C1: skill_req   │           │       │
        │   │   routines      │  │ C2: regime      │           │       │
        │   │   blocks        │  │ C3: window      │           │       │
        │   │   rituals       │  │ C4: knowl_appl  │           │       │
        │   │   auto_indagacao│  │ C5: study_hours │           │       │
        │   └────────┬────────┘  │ C6: revenue     │           │       │
        │            │           └─────────────────┘           │       │
        │   ┌────────▼────────┐                                  │       │
        │   │ 2. PROJECT      │                                  │       │
        │   │   SoftwareProj  │  ┌─────────────────┐           │       │
        │   │   Epic/Sprint   │◄─┤  SyncEngine     │           │       │
        │   │   Task↔TW       │  │  (sync 3-way)   │           │       │
        │   │   RICE+IKIGAi   │  └─────────────────┘           │       │
        │   └────────┬────────┘                                  │       │
        │            │                                            │       │
        │   ┌────────▼────────┐                                  │       │
        │   │ 3. STUDIES/PKM  │  ┌─────────────────┐           │       │
        │   │   Skill/Topic   │  │  Policy Engine  │           │       │
        │   │   Material/Sess │◄─┤  (4-state FSM)  │           │       │
        │   │   Cog. Debt     │  └─────────────────┘           │       │
        │   └────────┬────────┘                                  │       │
        │            │                                            │       │
        │   ┌────────▼────────┐  ┌─────────────────┐           │       │
        │   │ 4. IKIGAi       │  │  Hybrid RAG      │           │       │
        │   │   5 vectors     │  │  (SQL+Chroma+   │           │       │
        │   │   Meta-vetor    │◄─┤   Obsidian)     │           │       │
        │   │   Regime π(s_t) │  └─────────────────┘           │       │
        │   └────────┬────────┘                                  │       │
        │            │                                            │       │
        │   ┌────────▼────────┐                                  │       │
        │   │ 5. HABIT/CYBER  │                                  │       │
        │   │   H(t), E(t)    │  ┌─────────────────┐           │       │
        │   │   Q_HE          │◄─┤  IKIGAi Scorer  │           │       │
        │   │   Streak        │  │  (5 vetores)    │           │       │
        │   │   Habit streak  │  └─────────────────┘           │       │
        │   └─────────────────┘                                  │       │
        │                                                              │
        └────────┬──────────────────┬──────────────────┬───────────┘
                 │                  │                  │
                 ▼                  ▼                  ▼
        ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
        │   TASKWARRIOR   │  │   TIMEWARRIOR   │  │   SQLITE       │
        │   (.task DB)    │  │   (.timew)      │  │   (vibe_ops.db)│
        │   SoT: Status   │  │   SoT: Tempo    │  │   Snapshots    │
        │   & Prioridade  │  │   (Time track)  │  │   Históricos   │
        │   + UDAs        │  │   Tags phase:*  │  │   + ChromaDB   │
        └────────────────┘  └────────────────┘  └───────┬────────┘
                                                        │
                                             ┌──────────▼─────────┐
                                             │   BI/DASHBOARD     │
                                             │   Streamlit / Rust │
                                             │   TUI (Read-Only)  │
                                             └────────────────────┘
```

### 2.3. Mapeamento: Cluster ↔ Middleware ↔ Output

| Cluster | Pydantic Models | Pipelines principais | Output canônico |
|---|---|---|---|
| **1. PLAN** | `vibe-ops/src/models/cluster_plan_entities.py` (Sprint 1) | `policy_engine`, `daily_consolidator`, `habit_engine` (a criar) | `daily_routine.json`, `weekly_report.md` |
| **2. PROJECT** | `vibe-ops/src/models/project_entities.py` | `tw_sync`, `roadmap_sync_ingest`, `code_review_sync` | `burndown`, `velocity`, `ROI` |
| **3. STUDIES** | `vibe-ops/src/models/study_entities.py` | `study_manager`, `rag_indexer`, `knowledge_tree` | `skill_progress`, `cog_debt_trend` |
| **4. IKIGAi** | `vibe-ops/src/models/ikigai_entities.py` (Sprint 6) | `ikigai_scorer`, `mvl_orchestrator`, `enrichment_engine` | `ikigai_score`, `regime`, `phase` |
| **5. HABIT/CYBER** | `vibe-ops/src/models/habit_entities.py` | `policy_engine`, `cognitive_debt_tracker` | `qhe_history`, `streak` |

### 2.4. Os 6 Contratos Cross-Domain (origem: ADR-005 §2.2)

| # | Contrato | Origem | Destino | Dados |
|---|---|---|---|---|
| **C1** | `skill_requirements` | PLANNING (PROJECT) | STUDY | `tech_stack` → Skill entities + StudyTopic backlog |
| **C2** | `regime + time_allocation` | PLANNING (IKIGAi) | PROJECT (DEV) | `policy_engine` → sprint velocity |
| **C3** | `window_constants` | PLANNING (IKIGAi) | METRICS | 22 constantes → validação |
| **C4** | `knowledge_applied` | STUDY | PROJECT (DEV) | `Skill.projects_using` → SoftwareProject |
| **C5** | `study_hours` | STUDY | METRICS | `Σ StudySession.duration_minutes` → DailyMetrics |
| **C6** | `revenue + velocity` | PROJECT (DEV) | METRICS | `SoftwareProject.actual_revenue` → metrics |

> **Origem completa:** [ADR-005](ADR-005-data-mesh-topology.md) (data mesh topology)

---

## 3. Alternativas Consideradas

### 3.1. Alternativa A: Taskwarrior como Hub Central (Rejeitada)

**Descrição:** Colocar toda a inteligência dentro do TW via UDAs (User Defined Attributes), hooks, e configurações avançadas.

**Motivos de Rejeição:**
- UDAs têm limites de tipo (string, numeric, date, duration) — sem suporte a arrays ou objetos aninhados
- Hooks em shell/Python executam a cada `task add/modify`, criando overhead em operações simples
- Toda a lógica de validação estaria acoplada ao TW — impossível testar isoladamente
- Migração futura para outro task manager seria catastrófica

### 3.2. Alternativa B: Obsidian Dataview como Motor de Consulta (Parcialmente Aceita)

**Descrição:** Usar o plugin Dataview do Obsidian para fazer queries diretamente no YAML Frontmatter, sem pipeline Python.

**Veredito:** Aceita como **camada de visualização leve** para o domínio Planning, mas rejeitada como motor de pipeline:
- Dataview é read-only — não pode injetar dados no TW
- Não suporta JOINs entre TW e Markdown
- Performance degrada com vaults grandes (>1000 notas)
- Útil para: dashboards locais do Obsidian, revisões semanais rápidas

### 3.3. Alternativa C: PostgreSQL como Data Warehouse (Rejeitada)

**Motivos de Rejeição:**
- Overhead de manutenção para um sistema single-user
- Requer daemon rodando permanentemente
- SQLite oferece 95% das funcionalidades sem nenhum processo servidor
- DuckDB oferece OLAP nativo para analytics sem sair do filesystem

### 3.4. Alternativa D: Monolito (1 schema, 1 Pydantic unificado) — Rejeitada em v1.1

**Descrição:** Unificar todos os 5 sub-sistemas em 1 schema SQL + 1 Pydantic model.

**Motivos da Rejeição (v1.1):**
- Acoplamento forte (mudança em 1 cluster quebra todos)
- Refatoração cara
- Impossível extrair sub-cluster (ex: STUDY virar serviço separado)
- Domain ownership fica difuso

> **Origem:** [ADR-005 §3.2](ADR-005-data-mesh-topology.md)

### 3.5. Alternativa E: LLM-decision-maker (Rejeitada em v1.1)

**Descrição:** LLM decide regime/fase baseado em prompts do estado atual.

**Motivos da Rejeição (v1.1):**
- Não-determinístico (mesmo input pode dar output diferente)
- Caro (chamadas API, latência)
- Viola princípio "Fully Local" (ADR-001)
- Difícil de auditar (caixa-preta)
- O usuário explicitamente disse: **"nao tera nada de nlp .. processar apenas usando aritmetica"**

> **Origem:** [ADR-003 §3.2](ADR-003-ikigai-as-meta-brain.md)

---

## 4. Consequências

### 4.1. Positivas (v1.1 — Multi-Cluster)

- **5 sub-sistemas evoluem independentemente** (append-only, schema-first)
- **Domain ownership claro** (PLANNING/STUDY/DEV/METRICS + IKIGAi como meta-brain)
- **6 contratos cross-domain explícitos** (não implícitos)
- **Auditabilidade** (idempotency via upstream_id, deterministic algorithms)
- **Flexibilidade** (qualquer sub-cluster pode virar serviço separado)
- **No LLM/NLP no pipeline diário** (apenas aritmética + funções algébricas)
- **AI-Native documentation** (drilldowns em `ikigai_planning/`, `planning/`, `specs/`)
- **Standalone Memory Machines** (cada cluster doc é auto-contido)

### 4.2. Negativas / Riscos Aceitos

- **Complexidade inicial** — 5 sub-sistemas + 6 contratos = muito para entender
- **Cross-domain joins são middleware-only** (não-SQL)
- **Manutenção do parser** — mudanças no formato do Frontmatter exigem update no Pydantic
- **Single point of failure** — se o pipeline Python quebrar, dados dessincronizam
- **Curva de aprendizado** — operador precisa entender a topologia completa
- **6 contratos = 6 places para drift** (mitigado por testes)
- **Single-user não testa 100%** (concorrência, particionamento)
- **Vector store (ChromaDB) é opcional** (sqlite-vec fallback)

### 4.3. Mitigações

- **Cada cluster tem Standalone Memory Machine** (auto-contido) → ver `CLUSTER_PLAN.md §0-12`
- **Pydantic gera documentação automática** dos schemas
- **Pipeline é idempotente** — re-execução corrige dessincronias
- **`triagem.md`** captura o que o pipeline não consegue processar
- **5 IKIGAi planning docs** (drilldowns AI-native) — qualquer coding agent implementa
- **5 ADRs** (topologia, contratos, IKIGAi, RAG, mesh) — decisões documentadas
- **Testes de contrato** em `vibe-ops/tests/` (Sprint 1+)
- **`verify_mesh.py`** (root) para sanity check de imports

---

## 5. Implementação (v1.1)

### 5.1. Estado Atual por Sub-sistema

| Sub-sistema | Spec | Code | Data | Docs |
|---|:---:|:---:|:---:|:---:|
| **1. PLAN** | 🟡 (PRD-01,02,05,06) | 🟡 (vibe-ops/src/pipeline/policy_engine) | 🟡 (temporal_*, habits, metrics) | 🟢 (CLUSTER_PLAN.md 1861L) |
| **2. PROJECT** | 🟢 (PRD-04) | 🟡 (tw_sync, roadmap_sync_ingest) | 🟢 (dev_*, roadmap_sync) | 🟢 (CLUSTER_PROJ.md ~1100L) |
| **3. STUDIES** | 🟢 (PRD-03) | 🟡 (study_manager, rag_indexer) | 🟢 (study_*) | 🟢 (CLUSTER_STUDY.md ~900L) |
| **4. IKIGAi** | 🟢 (PRD-07) | 🔴 (ikigai_scorer.py diverge) | 🔴 (sem ikigai_vectors table) | 🟢 (ikigai_planning/ 5 docs) |
| **5. HABIT/CYBER** | 🟢 (PRD-02) | 🟢 (policy_engine, daily_loop) | 🟢 (habits, habit_states, policy_decisions) | 🟢 (CONCEPTUAL_MODEL §4) |

### 5.2. Roadmap (v1.1)

- **Sprint 1** (esta semana): Implementar Cluster PLAN inputs (CLI `plan journal log`)
- **Sprint 2-4**: Wave/Cycle/Phase reviews
- **Sprint 5**: Refinamento + polish
- **Sprint 6**: Reescrever `ikigai_scorer.py` (corrigir GAP de 5 vetores)
- **Sprint 7-8**: Meta-heuristics (UCB, phase pivot)
- **Sprint 9-10**: Sync com TW (Cluster PROJ)
- **Sprint 11-12**: Sync com Study (Cluster STUDY) + Q3 final

> **Origem completa:** [`vibe-ops/planning/CLUSTER_PLAN_ROADMAP.md`](vibe-ops/planning/CLUSTER_PLAN_ROADMAP.md)

---

## 6. Referências

### ADRs relacionados (v1.1)

- [ADR-002: Contratos de Data-Mesh e Máquinas de Estado](ADR-002-mesh-contracts-state-machines.md) — 14 state machines explícitas
- [ADR-003: IKIGAi como Meta-Brain (Propositivo-Superior)](ADR-003-ikigai-as-meta-brain.md) — IKIGAi meta-brain
- [ADR-004: Estratégia de RAG Híbrido (SQLite + ChromaDB + Obsidian)](ADR-004-hybrid-rag-strategy.md) — 3-layer RAG
- [ADR-005: Topologia do Data-Mesh (4 Domínios Autônomos)](ADR-005-data-mesh-topology.md) — 4 domínios + 6 contratos

### Architecture README

- [`README.md`](README.md) — Visão geral + índice de ADRs

### Cluster docs (Standalone Memory Machines)

- [`../../CLUSTER_PLAN.md`](../../CLUSTER_PLAN.md) (1861 linhas, v1.1) — Cluster 1
- [`../../CLUSTER_PROJ.md`](../../CLUSTER_PROJ.md) (~1100 linhas) — Cluster 2
- [`../../CLUSTER_STUDY.md`](../../CLUSTER_STUDY.md) (~900 linhas) — Cluster 3
- [`../../CONCEPTUAL_MODEL.md`](../../CONCEPTUAL_MODEL.md) — T→B→S framework
- [`../../SYSTEMS_TOPOLOGY.md`](../../SYSTEMS_TOPOLOGY.md) — Mapa técnico de middlewares

### IKIGAi Planning (cérebro do sistema)

- [`../../life-ops/planner/ikigai_planning/README.md`](../../life-ops/planner/ikigai_planning/README.md) — Overview
- [`../../life-ops/planner/ikigai_planning/ikigai_4_vectors.md`](../../life-ops/planner/ikigai_planning/ikigai_4_vectors.md) — 4 vetores + 5º contextual
- [`../../life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md`](../../life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md) — 22 constantes
- [`../../life-ops/planner/ikigai_planning/ikigai_propagation.md`](../../life-ops/planner/ikigai_planning/ikigai_propagation.md) — Data flow
- [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) — 6 algoritmos determinísticos

### Architecture Index (master)

- [`../../ARCHITECTURE_INDEX.md`](../../ARCHITECTURE_INDEX.md) — Master index do workspace

### Documentos autoritativos originais

- [`../doc/01-data-mesh-strategy.md`](../doc/01-data-mesh-strategy.md) — Estratégia (v1)
- [`../doc/01.5-data-contracts-and-pipelines.md`](../doc/01.5-data-contracts-and-pipelines.md) — Contratos + pipelines (master, 29K)
- [`../doc/03-data-mesh-enrichment.md`](../doc/03-data-mesh-enrichment.md) — Enrichment (27K)
- [`../doc/02-tw-factory-reset.md`](../doc/02-tw-factory-reset.md) — TW factory reset
- [`../doc/solucoes_extensoes_tw.md`](../doc/solucoes_extensoes_tw.md) — Soluções + extensões TW
- [`../doc/tw-vanilla_limits_analysis.md`](../doc/tw-vanilla_limits_analysis.md) — Limites TW vanilla

### PRDs (origem dos 7 sub-grafos)

- [`../planning/PRD-01-temporal-engine.md`](../planning/PRD-01-temporal-engine.md) — Wave/Cycle/Phase
- [`../planning/PRD-02-habit-tracker.md`](../planning/PRD-02-habit-tracker.md) — H(t), E(t), Q_HE
- [`../planning/PRD-03-study-backlog.md`](../planning/PRD-03-study-backlog.md) — Skill/Topic/Material/Session
- [`../planning/PRD-04-project-execution.md`](../planning/PRD-04-project-execution.md) — Project/Epic/Sprint/Task
- [`../planning/PRD-05-metrics-health.md`](../planning/PRD-05-metrics-health.md) — SleepRecord/EnergyReading
- [`../planning/PRD-06-policy-governance.md`](../planning/PRD-06-policy-governance.md) — PolicyEngine (4-state)
- [`../planning/PRD-07-ikigai-vectors.md`](../planning/PRD-07-ikigai-vectors.md) — IKIGAi entities

### Specs (engineering)

- [`../specs/SPEC-05-cybernetic-epistemic-mesh.md`](../specs/SPEC-05-cybernetic-epistemic-mesh.md) — Cybernetic mesh
- [`../specs/schema-frontmatter-contract-v2.md`](../specs/schema-frontmatter-contract-v2.md) — Frontmatter v2
- [`../specs/schema-pydantic-models-v2.md`](../specs/schema-pydantic-models-v2.md) — Pydantic v2
- [`../specs/schema-planner-extension.md`](../specs/schema-planner-extension.md) — Planner extension
- [`../specs/spec-cluster-plan-inputs.md`](../specs/spec-cluster-plan-inputs.md) — Cluster PLAN inputs (Sprint 1)
- [`../specs/spec-cluster-plan-pipelines.md`](../specs/spec-cluster-plan-pipelines.md) — Cluster PLAN pipelines
- [`../specs/spec-cluster-plan-reports.md`](../specs/spec-cluster-plan-reports.md) — Cluster PLAN reports

### Cluster PLAN Drilldowns (Sprint 1, 2026-Q3)

- [`../planning/CLUSTER_PLAN_BRD.md`](../planning/CLUSTER_PLAN_BRD.md) — Business Requirements
- [`../planning/CLUSTER_PLAN_DATA_MODEL.md`](../planning/CLUSTER_PLAN_DATA_MODEL.md) — Schema + Pydantic
- [`../planning/CLUSTER_PLAN_USER_STORIES.md`](../planning/CLUSTER_PLAN_USER_STORIES.md) — 10 user stories
- [`../planning/CLUSTER_PLAN_CLI_SPEC.md`](../planning/CLUSTER_PLAN_CLI_SPEC.md) — 13 CLI commands
- [`../planning/CLUSTER_PLAN_ROADMAP.md`](../planning/CLUSTER_PLAN_ROADMAP.md) — 12 sprints Q3 2026

### Base docs (conceito)

- [`../base/IKIGAi.md`](../base/IKIGAi.md) — IKIGAi conceitual (90K)
- [`../base/Planning_notes.md`](../base/Planning_notes.md) — Frameworks priorização
- [`../base/Produtividade Algorítmica Visual.md`](../base/Produtividade%20Algor%C3%ADtmica%20Visual.md) — PAV (815K)

---

*ADR-001 — v1.1 — 2026-06-05 — Topologia de Fluxo de Dados Multi-Cluster (5 sub-sistemas, 4 facetas, 6 contratos)*
