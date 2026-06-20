# Algorithmic Life OS

> **Workspace pessoal de produtividade orquestrada** — um sistema operacional para a vida algorítmica, com CLI hub, 5 sub-sistemas autônomos, 1 meta-cérebro (IKIGAi) e ~5.000 linhas de documentação.

> **TL;DR:** Este workspace é a fusão de um CLI Python (orquestrador de centrals) + um data-mesh cybernético (vibe-ops) + um planejador standalone (life-ops/life_tatics). É **100% local, single-user, append-only, sem LLM no pipeline diário**. Tudo o que você vê aqui existe para servir 3 clusters operacionais: **Plan**, **Project**, **Studies**, supervisionados por um meta-cérebro **IKIGAi**.

---

## 1. Como o Workspace se Organiza (Visão em 7 Camadas)

O workspace é dividido em **7 camadas funcionais** que se sobrepõem em uma pilha de abstração:

```
┌─────────────────────────────────────────────────────────────────────┐
│  CAMADA 7 — VISUALIZAÇÃO                  (diagrams/ — 6 PNGs)     │
│  CAMADA 6 — LOGS                          (logs/ — runtime stdout)   │
├─────────────────────────────────────────────────────────────────────┤
│  CAMADA 5 — AI-NATIVE PLANNING            (PT-BR, IKIGAi drilling)  │
│  └─ life-ops/planner/ikigai_planning/                               │
├─────────────────────────────────────────────────────────────────────┤
│  CAMADA 4 — CLUSTER DOCS CANÔNICOS        (PT-BR, multi-cluster)    │
│  └─ CLUSTER_PLAN.md · CLUSTER_PROJ.md · CLUSTER_STUDY.md            │
│     CONCEPTUAL_MODEL.md · SYSTEMS_TOPOLOGY.md · ARCHITECTURE_INDEX  │
├─────────────────────────────────────────────────────────────────────┤
│  CAMADA 3 — ENGENHARIA DE CÓDIGO          (EN, AI-native for agents)│
│  └─ vibe-ops/architecture/  (5 ADRs)                                │
│     vibe-ops/planning/      (7 PRDs + 5 CLUSTER_PLAN_* + 3 TEMPL)   │
│     vibe-ops/specs/         (3 SPECs + 7 schemas + 3 spec-cluster)  │
│     vibe-ops/migrations/    (3 SQL + 1 Python Alembic-style)        │
├─────────────────────────────────────────────────────────────────────┤
│  CAMADA 2 — DOCS ESTRATÉGICOS             (PT-BR, conceitual)       │
│  └─ strategics/               (9 docs, frameworks e modelos)       │
│     vibe-ops/base/            (IKIGAi.md 90K, PAV 815K, Planning)  │
│     vibe-ops/doc/             (data-mesh strategy + enrichment)    │
│     docs/                     (índice progressivo)                 │
├─────────────────────────────────────────────────────────────────────┤
│  CAMADA 1 — CÓDIGO APLICACIONAL           (Python 3.10+, Typer)     │
│  ├─ centrals/ · cli/ · handlers/ · plugins/    (root CLI)          │
│  ├─ vibe-ops/src/                             (data-mesh)          │
│  │   ├─ contracts/ · cybernetics/ · embeddings/ · integration/     │
│  │   ├─ middleware/ · models/ · parsers/ · pipeline/               │
│  │   ├─ schemas/ · storage/                                       │
│  │   └─ main.py · vibe_cli.py                                     │
│  └─ life-ops/life_tatics/                       (standalone Poetry)│
│     └─ cli.py · domain/{time_blocks,screentime}.py                 │
└─────────────────────────────────────────────────────────────────────┘
```

> **Princípio de separação:** Cada camada é escrita em um **idioma e propósito** distinto. Quanto mais alto na pilha, mais conceitual/português. Quanto mais baixo, mais técnico/inglês/código. Agentes AI devem ler de baixo para cima (código → specs → estratégia); humanos podem ler de cima para baixo (estratégia → cluster docs → specs → código).

---

## 2. Top-Level — Tabela de Pastas

| Pasta | Camada | Tipo | Propósito | Quem lê |
|:------|:------:|:-----|:----------|:--------|
| `centrals/` | 1 | 🐍 Código | Hubs de domínio: `task`, `finance`, `knowledge`, `research`. Cada central = 1 Typer sub-app. | Agentes implementando CLI |
| `cli/` | 1 | 🐍 Código | Entry point (`cli.py`), config (`config.py`), logging (`log.py`), test runner. | Agentes implementando CLI |
| `handlers/` | 1 | 🐍 Código | `daily.py`, `weekly.py` — orquestram centrals via subprocess. | Agentes implementando rotinas |
| `plugins/` | 1 | 🐍 Código | Plugin protocol + loader + 1 builtin (`health_check`). | Agentes adicionando plugins |
| `vibe-ops/` | 1+2+3+4+5 | 🌐 **Subsistema** | **Data-mesh cybernético completo**: código (`src/`), estratégia (`base/`, `doc/`), engenharia (`architecture/`, `planning/`, `specs/`, `migrations/`), Rust TUI (`vibeops-tui/`), tests (`tests/`, `scratch/`). | Tudo (subsistema central) |
| `life-ops/` | 1+5 | 🌐 **Subsistema** | **Planejador standalone** (Poetry): `life_tatics/` é 100% desacoplado do root; `planner/ikigai_planning/` é a base do meta-cérebro. | Tudo (subsistema central) |
| `taskwarrior/` | 1 | 🐍+SHELL | Binário TW + scripts bash + conteúdo (.task) + 7 docs de configuração. | Agentes integrando TW |
| `strategics/` | 2 | 📚 Doc | 9 documentos estratégicos (PT-BR): índice progressivo, hierarquia de objetivos, modelagem operacional, integração tática, etc. | Humano pensante |
| `docs/` | 2 | 📚 Doc | Apenas 1 arquivo: `ÍNDICE PROGRESSIVO.md` (índice mestre de leitura). | Humano (entrada) |
| `diagrams/` | 7 | 🎨 Visual | 6 PNGs renderizados (dark mode) + 6 fontes `.mmd` + `puppeteer-config.json` + README. | Humano + agente (referência) |
| `logs/` | 6 | 📝 Runtime | Logs gerados em runtime (stdout/stderr redirecionado). | Debugging |
| `time-tasker/` | — | 🗄️ **DEPRECATED** | Snapshot do estado em data anterior. **Não editar.** Contém `life/`, `strategics/`, `taskwarrior/` espelhados. | Histórico apenas |
| `*.md` (raiz) | 4 | 📚 Doc | **Cluster docs canônicos** + master index. 6 arquivos `.md` na raiz. | Tudo (entrada) |
| `*.db` (raiz) | — | 💾 Dados | `vibe_ops.db` (140K), `test_vibe.db` (140K), `vibe_mesh.db` (0B). SQLite databases. | Código em runtime |
| `verify_mesh.py` / `verify_mesh_v2.py` | 1 | 🐍 Script | Sanity check de imports do vibe-ops models. | CI / debugging |
| `AGENTS.md` | 4 | 📚 Meta | **Guia do agente AI** — convenções, regras, quick reference. | Agentes AI |
| `CLAUDE.md` | 4 | 📚 Meta | Guia para Claude Code (humano contribuidor). | Claude Code |

---

## 3. Camada 1 — Arquitetura de Código (Python)

### 3.1. Root CLI — `centrals/` + `cli/` + `handlers/` + `plugins/`

É o **orquestrador hub**. O usuário executa `python -m life.cli <central> <cmd>` e a central delega para sub-módulos externos (configurados em `cli/config.py`).

```
cli/cli.py              ── Typer app raiz; registra centrals, handlers, plugins
cli/config.py           ── LifeConfig (dataclass); YAML + env loading
cli/log.py              ── Structured logging (plain ou JSON)
cli/test_runner.py      ── Pytest discovery & runner

centrals/base.py        ── BaseCentral.run_cli() — subprocess helper
centrals/task.py        ── Task central → delega para `task` (binário TW)
centrals/finance.py     ── Finance central → delega para `fin_ops/` (submódulo)
centrals/knowledge.py   ── Knowledge central → delega para `leitura/`, `mindmaps/`, `notes/`
centrals/research.py    ── Research central → delega para `research/` (submódulo)

handlers/daily.py       ── Orquestra centrals via subprocess (daily run)
handlers/weekly.py      ── Orquestra centrals via subprocess (weekly run)

plugins/protocol.py     ── PluginProtocol (register + lifecycle hooks)
plugins/loader.py       ── File-system plugin discovery
plugins/builtin/health_check.py  ── Built-in: registra comando `health`
```

**Fluxo:** `python -m life.cli daily run` → `handlers/daily.py` → loop sobre centrals → `BaseCentral.run_cli(["task", "today", "--json"])` → JSON aggregated.

### 3.2. Vibe-Ops Data-Mesh — `vibe-ops/src/`

É o **coração cybernético**. Implementa o loop **Target-Sensor-Adjuster** (Ikigai→SQLite→PolicyEngine→Sync).

```
src/main.py             ── argparse CLI: run-daily, status, gaps, sync
src/vibe_cli.py         ── Typer+Rich CLI: sync_file, hybrid_search, gaps, debt_dashboard
src/contracts/          ── planning.v1.yaml (7531B) + registry.yaml + sync + roadmap_sync
src/cybernetics/        ── daily_loop.py (Target-Sensor-Adjuster) + engine.py
src/embeddings/         ── provider.py (OpenAI/local abstraction) + config.py (stub)
src/integration/        ── obsidian_parser.py (stub) + semantic_engine.py
src/middleware/         ── sync_engine.py (Obsidian ↔ SQLite ↔ Taskwarrior)
src/models/             ── 13 Pydantic entity modules (project, study, ikigai, habit...)
src/parsers/            ── code_parser.py (stub)
src/pipeline/           ── 21 módulos: orchestrator, policy, rag, sync, ingestion, scoring
src/schemas/            ── pydantic_v2.py + registry.py
src/storage/            ── SQLite + ChromaDB + vector_store + UEID + ORM + sqlite-vec
```

**Status dos módulos:** ~30% são stubs (0 bytes), ~40% implementados, ~30% com lógica parcial. Veja `verify_mesh.py` para sanity check.

### 3.3. Life-Tatics Standalone — `life-ops/life_tatics/`

É o **planejador tático desacoplado**. Não importa nada do root `life/`. Vive em projeto Poetry separado.

```
life-ops/life_tatics/cli.py               ── Typer CLI entry
life-ops/life_tatics/domain/time_blocks.py  ── Time-block entity
life-ops/life_tatics/domain/screentime.py   ── Screen-time entity
life-ops/life_tatics/SPEC.md              ── Especificação standalone
life-ops/life_tatics/Planning_notes.md    ── Notas táticas (PT-BR)
life-ops/life_tatics/time-lenghts_reviews.md  ── Constantes de janela temporal
```

**Regra:** *deve* permanecer desacoplado. Qualquer nova feature atualiza `SPEC.md`.

### 3.4. Taskwarrior — `taskwarrior/`

```
taskwarrior/scripts/    ── 8 bash scripts (auto-recurrence, focus mode, etc.)
taskwarrior/content/    ── 18 arquivos (templates de tasks, hooks)
taskwarrior/doc/        ── 7 docs de configuração TW
taskwarrior/config/     ── 2 configs (UDAs definitions)
```

---

## 4. Camada 2 — Documentação Estratégica (PT-BR)

### 4.1. `strategics/` — Frameworks e Modelos

| Arquivo | Tamanho | Propósito |
|:--------|--------:|:----------|
| `00-ÍNDICE-PROGRESSIVO.md` | 23K | **Índice mestre** de leitura estratégica |
| `Planejamento (Estratégico e Tático).md` | 24K | Framework de planejamento (Wave/Cycle/Phase) |
| `Modelagem Operacional.md` | 13K | Modelos de operação (4 regimes, histerese) |
| `Hierarquia de Objetivos.md` | 4.5K | Decomposição Sonho → Meta → Task |
| `Integracao_Tatica.md` | 6.4K | Integração tática com TW |
| `Desempenho Subjacente.md` | 5.8K | Métricas de desempenho |
| `Análise (Tático e Operacional).md` | 4.3K | Análise de trade-offs |
| `design_system_and_knowledge_tracking.md` | 3.4K | Design system + tracking |
| `system_architecture_and_tracking_framework.md` | 3.7K | Framework de tracking |

### 4.2. `vibe-ops/base/` — Conceitos Fundamentais

| Arquivo | Tamanho | Propósito |
|:--------|--------:|:----------|
| `IKIGAi.md` | **90K** | IKIGAi conceitual completo (5 vetores, equações, exemplos) |
| `Planejamento_notes.md` | 27K | Frameworks de priorização (RICE, IKIGAi-weighted) |
| `Produtividade Algorítmica Visual.md` | **815K** | PAV — referência visual principal |

### 4.3. `vibe-ops/doc/` — Data-Mesh Conceitual

| Arquivo | Tamanho | Propósito |
|:--------|--------:|:----------|
| `01-data-mesh-strategy.md` | ~12K | Estratégia de data-mesh (v1) |
| `01.5-data-contracts-and-pipelines.md` | **29K** | **Master de contratos + pipelines** |
| `02-tw-factory-reset.md` | ~6K | Reset do TW para setup limpo |
| `03-data-mesh-enrichment.md` | **27K** | Enrichment pipeline conceitual |
| `solucoes_extensoes_tw.md` | ~5K | Soluções + extensões TW |
| `tw-vanilla_limits_analysis.md` | ~4K | Análise de limites TW vanilla |

### 4.4. `docs/` — Entrada Única

Apenas `ÍNDICE PROGRESSIVO.md` (18K) — sequência de leitura canônica para humanos.

---

## 5. Camada 3 — Engenharia de Código (AI-Native, EN)

Esta é a camada **AI-native**: cada documento é otimizado para que coding agents + swarm sub-agents consigam implementar features sem ambiguidade.

### 5.1. `vibe-ops/architecture/` — Decisões (ADRs)

| Arquivo | Tamanho | Status |
|:--------|--------:|:-------|
| `README.md` | 6.8K | 🟢 reescrito |
| `ADR-001-data-flow-topology.md` | **26K** | 🟢 expandido v1.1 (multi-cluster) |
| `ADR-002-mesh-contracts-state-machines.md` | 9.3K | 🟢 preenchido (era 0B) |
| `ADR-003-ikigai-as-meta-brain.md` | 10K | 🟢 novo (criado) |
| `ADR-004-hybrid-rag-strategy.md` | 7.8K | 🟢 novo (criado) |
| `ADR-005-data-mesh-topology.md` | 9.7K | 🟢 novo (criado) |

**Total:** 5 ADRs + 1 README. Cobre topologia, contratos, IKIGAi meta-brain, RAG híbrido, data-mesh.

### 5.2. `vibe-ops/planning/` — Requisitos (PRDs) + Drilldowns (Sprint 1)

| Arquivo | Tamanho | Status |
|:--------|--------:|:-------|
| `README.md` | 3.1K | 🟢 reescrito |
| `PRD-01-temporal-engine.md` | 7.1K | 🟢 (Wave/Cycle/Phase) |
| `PRD-02-habit-tracker.md` | 10K | 🟢 (H(t), E(t), Q_HE) |
| `PRD-03-study-backlog.md` | 14K | 🟢 (Skill/Topic/Material/Session) |
| `PRD-04-project-execution.md` | 5.6K | 🟢 (Project/Epic/Sprint/Task) |
| `PRD-05-metrics-health.md` | 7.9K | 🟢 (SleepRecord/EnergyReading) |
| `PRD-06-policy-governance.md` | 9.8K | 🟢 (PolicyEngine 4-state) |
| `PRD-07-ikigai-vectors.md` | 9.8K | 🟢 (IKIGAi entities) |
| `CLUSTER_PLAN_BRD.md` | 9.3K | 🟢 novo (Business Reqs) |
| `CLUSTER_PLAN_DATA_MODEL.md` | 14K | 🟢 novo (Schema + Pydantic) |
| `CLUSTER_PLAN_USER_STORIES.md` | 8.2K | 🟢 novo (10 user stories) |
| `CLUSTER_PLAN_CLI_SPEC.md` | 7.9K | 🟢 novo (13 CLI commands) |
| `CLUSTER_PLAN_ROADMAP.md` | 6.9K | 🟢 novo (12 sprints Q3) |
| `TEMPLATE-epic-sprint.md` | 2.4K | 🟢 |
| `TEMPLATE-micro-ciclo.md` | 2.5K | 🟢 |
| `TEMPLATE-weekly-review.md` | 2.2K | 🟢 |

**Total:** 7 PRDs + 5 CLUSTER_PLAN drilldowns + 3 templates + README.

### 5.3. `vibe-ops/specs/` — Engenharia (Schemas + Specs)

| Arquivo | Tamanho | Status |
|:--------|--------:|:-------|
| `README.md` | 3.0K | 🟢 reescrito |
| `schema-frontmatter-contract-v2.md` | 12K | 🟢 |
| `schema-pydantic-models-v2.md` | **36K** | 🟢 (canonical Pydantic) |
| `schema-planner-extension.md` | **89K** | 🟢 (canonical extension) |
| `schema-frontmatter-contract.md` | 10K | 🟢 (legacy) |
| `schema-pydantic-models.md` | 15K | 🟢 (legacy) |
| `SPEC-05-cybernetic-epistemic-mesh.md` | 3.3K | 🟢 |
| `spec-cluster-plan-inputs.md` | 7.8K | 🟢 novo (Sprint 1) |
| `spec-cluster-plan-pipelines.md` | 11K | 🟢 novo (Sprint 1) |
| `spec-cluster-plan-reports.md` | 11K | 🟢 novo (Sprint 1) |
| `prd-*.md` (7 arquivos) | ~1.5K cada | 🟢 (mirror dos PRDs com prefixo `prd-`) |
| `concept_sys-archy.drawio` | 46K | 🟢 (diagrama DrawIO) |
| `.$concept_sys-archy.drawio.bkp` | 11K | 🟢 (backup) |

**Convenção intencional:** Há duplicação `PRD-*.md` (em `planning/`) × `prd-*.md` (em `specs/`). É por design: **`planning/` = requisitos (o quê), `specs/` = engenharia (o como)**. Não consolidar.

### 5.4. `vibe-ops/migrations/` — Schema SQL + Python

```
migrations/001_initial_schema.sql       ── Schema inicial (SQLite)
migrations/002_seed_data.sql            ── Seed data
migrations/003_add_indices.sql          ── Índices
migrations/versions/001_init.py         ── Migration Python (Alembic-style)
```

---

## 6. Camada 4 — Cluster Docs Canônicos (PT-BR)

Estes 6 documentos `.md` na **raiz** são a entrada principal para entender o workspace como um sistema. São **Standalone Memory Machines** (auto-contidos).

| Arquivo | Tamanho | Linhas | Propósito |
|:--------|--------:|-------:|:----------|
| **`ARCHITECTURE_INDEX.md`** | 35K | ~700 | **Master index do workspace** — 10 seções, 50+ cross-refs, conflitos §8 |
| **`CLUSTER_PLAN.md`** | **88K** | **1861** | Cluster 1: Plan + Personal Productivity (v1.1) |
| **`CLUSTER_PROJ.md`** | 59K | ~1100 | Cluster 2: Project Execution (PMO ↔ Taskwarrior) |
| **`CLUSTER_STUDY.md`** | 46K | ~900 | Cluster 3: Studies & Lifelong Learning (PKM) |
| **`CONCEPTUAL_MODEL.md`** | 25K | ~500 | Tensão → Comportamento → Solução (5 tensões, 4 regimes) |
| **`SYSTEMS_TOPOLOGY.md`** | 58K | ~800 | Índice-of-índices + mapa de middlewares |

> **Regra:** Sempre ler `ARCHITECTURE_INDEX.md` primeiro. Ele é o **mapa-mestre**.

---

## 7. Camada 5 — AI-Native Planning (PT-BR, IKIGAi Drilling)

`life-ops/planner/ikigai_planning/` — **o cérebro do sistema**. Drilling do meta-cérebro IKIGAi.

| Arquivo | Tamanho | Propósito |
|:--------|--------:|:----------|
| `README.md` | 3.4K | Overview do IKIGAi como meta-brain |
| `ikigai_4_vectors.md` | 12K | 4 vetores canônicos + 5º contextual (Course) |
| `ikigai_north_star_metrics.md` | 8.1K | 22 constantes de janela temporal |
| `ikigai_propagation.md` | 9.0K | Como dados propagam IKIGAi → middlewares → outputs |
| `ikigai_meta_heuristics.md` | 13K | 6 algoritmos determinísticos (UCB, fase pivot) |

---

## 8. Camada 6 — Logs & Camada 7 — Diagramas

### 8.1. `logs/`
Logs runtime (stdout/stderr). Usado para debugging.

### 8.2. `diagrams/`
6 PNGs renderizados (dark mode via Mermaid CLI + Chrome) + 6 fontes `.mmd`:

| PNG | Fonte `.mmd` | Renderiza |
|:----|:-------------|:----------|
| `topologia.png` (231K) | `topologia.mmd` (3.2K) | Topologia multi-cluster |
| `conceitual.png` (46K) | `conceitual.mmd` (1.2K) | Modelo conceitual T→B→S |
| `cluster_plan.png` (43K) | `cluster_plan.mmd` (920B) | Cluster PLAN v1 |
| `cluster_plan_drill.png` (85K) | `cluster_plan_drill.mmd` (1.3K) | Cluster PLAN drilldown |
| `cluster_proj.png` (41K) | `cluster_proj.mmd` (1.1K) | Cluster PROJ |
| `cluster_study.png` (68K) | `cluster_study.mmd` (1.1K) | Cluster STUDY |

---

## 9. Como Navegar (Por Persona e Tarefa)

### 9.1. Se você é **humano** querendo entender o sistema

```
1. README.md (este arquivo)                          ← você está aqui
2. ARCHITECTURE_INDEX.md                             ← master index
3. CONCEPTUAL_MODEL.md                               ← o "porquê"
4. SYSTEMS_TOPOLOGY.md                               ← o "como"
5. CLUSTER_PLAN.md (se você quer implementar Plan)   ← cluster de interesse
6. strategies/00-ÍNDICE-PROGRESSIVO.md               ← leitura estratégica
7. vibe-ops/base/IKIGAi.md                           ← meta-cérebro
```

### 9.2. Se você é **agente AI** implementando uma feature

```
1. AGENTS.md                                         ← convenções + regras
2. ARCHITECTURE_INDEX.md §3-§5                       ← topologia + contratos
3. ADR-001 §2.2 (topologia) + §2.4 (contratos)       ← decisões registradas
4. vibe-ops/architecture/ADR-*.md (relevante)        ← ADRs adicionais
5. CLUSTER_PLAN.md §X.5 (drilldown relevante)        ← standalone memory
6. vibe-ops/planning/PRD-XX (relevante)              ← requisitos
7. vibe-ops/specs/schema-pydantic-models-v2.md       ← schemas canônicos
8. vibe-ops/src/ (código existente)                  ← implementar
```

### 9.3. Se você quer **adicionar uma rotina semanal/diária**

```
1. handlers/daily.py (se daily) ou handlers/weekly.py (se weekly)
2. centrals/{task,finance,knowledge,research}.py (escolher domain)
3. cli/cli.py (registrar)
4. plugins/ (se for plugin)
```

### 9.4. Se você quer **adicionar um sub-cluster IKIGAi**

```
1. life-ops/planner/ikigai_planning/ (drill AI-native)
2. vibe-ops/base/IKIGAi.md (conceito)
3. vibe-ops/src/models/ikigai_entities.py (Pydantic)
4. vibe-ops/src/pipeline/ikigai_scorer.py (scoring)
5. ADR-003 (decisão arquitetural)
```

### 9.5. Se você quer **mexer no data-mesh**

```
1. vibe-ops/architecture/ADR-001 (topologia) e ADR-002 (contratos)
2. vibe-ops/specs/schema-pydantic-models-v2.md (schemas)
3. vibe-ops/src/middleware/sync_engine.py (sync 3-way)
4. vibe-ops/migrations/ (SQL)
```

---

## 10. Quick Start (Desenvolvimento)

```bash
# Root CLI (orquestrador hub)
python -m life.cli --help
python -m life.cli daily run
python -m life.cli weekly run
python -m life.cli task today --json
python -m life.cli finance report --period week --json
python -m life.cli submodules
python -m life.cli health
python -m life.cli test                   # descobre e roda tests

# Vibe-ops CLI (data-mesh)
cd vibe-ops
python src/main.py run-daily [--date YYYY-MM-DD]
python src/main.py status
python src/main.py gaps
python src/main.py sync --vault-path <path>
python src/vibe_cli.py sync_file
python src/vibe_cli.py hybrid_search "query"
python src/vibe_cli.py debt_dashboard

# Life-tatics (standalone)
cd life-ops
poetry install
poetry run life-tatics --help

# Vibe-ops Rust TUI
cd vibe-ops/vibeops-tui
cargo run

# Sanity check
python verify_mesh.py
```

---

## 11. Convenções Globais

| Convenção | Regra |
|:----------|:------|
| **Idioma** | PT-BR para prosa estratégica (cluster docs, strategics, base). EN para código, file names, AI-native docs (PRDs, specs, ADRs). |
| **Append-Only** | `vibe-ops/` é **append-only** — nunca deletar arquivos, apenas expandir. Refactor estrutural exige aprovação do humano. |
| **`time-tasker/`** | É **snapshot deprecated**. Não editar. Root é canônico. |
| **Pydantic v2** | Todo schema de dados é Pydantic v2 com type hints + validators. |
| **Sub-cluster Standalone** | Cada cluster doc é **Standalone Memory Machine** (auto-contido, sem necessidade de ler outros docs). |
| **AI-Native Docs** | PRDs e specs são otimizados para coding agents (contexto suficiente para implementar sem ambiguidade). |
| **Determinismo** | Pipeline diário/semanal é **determinístico** (sem LLM, sem NLP, apenas aritmética). |
| **Single-User** | Sem autenticação, sem multi-tenancy. Concorrência mínima. |
| **Fully Local** | Zero cloud, zero API key obrigatória. SQLite + filesystem. |
| **Idempotência** | Todo pipeline é re-executável sem duplicar dados (chaves: `upstream_id`, `ueid`). |

---

## 12. Estado Atual (Junho 2026)

### 12.1. Sub-sistemas (5)

| # | Sub-sistema | Spec | Code | Data | Docs |
|--:|:------------|:----:|:----:|:----:|:----:|
| 1 | **PLAN** | 🟡 | 🟡 | 🟡 | 🟢 |
| 2 | **PROJECT** | 🟢 | 🟡 | 🟢 | 🟢 |
| 3 | **STUDIES** | 🟢 | 🟡 | 🟢 | 🟢 |
| 4 | **IKIGAi** | 🟢 | 🔴 (GAP) | 🔴 | 🟢 |
| 5 | **HABIT/CYBER** | 🟢 | 🟢 | 🟢 | 🟢 |

### 12.2. Roadmap Q3 2026

- **Sprint 1** (esta semana): Cluster PLAN inputs (CLI `plan journal log`)
- **Sprint 2-4**: Wave/Cycle/Phase reviews
- **Sprint 5**: Polish + refinamento
- **Sprint 6**: Reescrever `ikigai_scorer.py` (corrigir GAP de 5 vetores)
- **Sprint 7-8**: Meta-heuristics (UCB, phase pivot)
- **Sprint 9-10**: Sync com TW (Cluster PROJ)
- **Sprint 11-12**: Sync com Study (Cluster STUDY) + Q3 final

### 12.3. Conflitos Conhecidos (Resolvidos ou Em Aberto)

Veja `ARCHITECTURE_INDEX.md §8` para os 10+ conflitos documentados e suas resoluções.

---

## 13. Métricas do Workspace

| Métrica | Valor |
|:--------|------:|
| Arquivos Markdown (raiz + 1 nível) | ~120 |
| Linhas de documentação (PT-BR + EN) | ~25.000 |
| Linhas de código Python (root + vibe-ops) | ~5.000 |
| ADRs | 5 |
| PRDs | 7 |
| Cluster docs canônicos | 3 |
| Cluster PLAN drilldowns | 5 |
| Cluster PLAN specs | 3 |
| IKIGAi planning docs | 5 |
| Diagramas renderizados (PNG) | 6 |
| Sub-sistemas autônomos | 5 |
| Contratos cross-domain (C1-C6) | 6 |
| Constantes de janela temporal | 22 |
| Algoritmos meta-heurísticos | 6 |
| State machines | 14 |
| Testes automatizados (vibe-ops) | ~5 (parcial) |

---

## 14. Próximos Passos Recomendados

1. **Ler `AGENTS.md`** (se você é agente) ou **`CLAUDE.md`** (se você é humano com Claude Code).
2. **Ler `ARCHITECTURE_INDEX.md`** para visão sistêmica.
3. **Implementar Sprint 1** (Cluster PLAN inputs) — comece por `vibe-ops/specs/spec-cluster-plan-inputs.md` + `vibe-ops/planning/CLUSTER_PLAN_CLI_SPEC.md`.
4. **Renderizar diagrama do ADR-001 v1.1** (seção 2.2 ASCII ainda não tem PNG correspondente).

---

*Algorithmic Life OS — README Global — 2026-06-07*
*Single-user · Fully Local · Append-Only · AI-Native · 5 Sub-Sistemas Autônomos · 1 Meta-Cérebro IKIGAi*
