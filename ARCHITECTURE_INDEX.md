# ARCHITECTURE_INDEX.md

> **Índice de Arquitetura do Algorithmic Life OS**
>
> Mapa canônico que conecta **planejamento**, **documentação**, **código**,
> e **dados** da workspace inteira.
> **AI-native** (otimizado para coding agents e swarm sub-agents) e
> **IA-legível** (humano pode ler).
>
> **Versão:** 1.0 — 2026-06-05
> **Stack:** Python 3.10+ | Typer | Pydantic v2 | SQLAlchemy 2.0 | SQLite | Taskwarrior | Obsidian
> **Regra de ouro:** sem LLM no pipeline diário (apenas aritmética + funções algébricas)
>
> **Relação com outros docs âncora:**
> - [`AGENTS.md`](AGENTS.md) — regras para o agente
> - [`CLAUDE.md`](CLAUDE.md) — guia para Claude Code
> - [`CONCEPTUAL_MODEL.md`](CONCEPTUAL_MODEL.md) — T→B→S (porquê)
> - [`SYSTEMS_TOPOLOGY.md`](SYSTEMS_TOPOLOGY.md) — mapa técnico de middlewares (como)
> - [`CLUSTER_PLAN.md`](CLUSTER_PLAN.md), [`CLUSTER_PROJ.md`](CLUSTER_PROJ.md), [`CLUSTER_STUDY.md`](CLUSTER_STUDY.md) — Standalone Memory Machines por cluster
> - [`docs/ÍNDICE PROGRESSIVO.md`](docs/%C3%8DNDICE%20PROGRESSIVO.md) — navegação estratégica

---

## §0. AS 4 FACETAS DA WORKSPACE

A workspace `life/` se divide em **4 facetas** canônicas. Cada arquivo do
workspace pertence a **exatamente 1 faceta** (com poucas exceções em
`vibe-ops/` que transitam entre especificação e código).

| Faceta | Cor | Sub-pastas Principais | Propósito | Quem cuida |
|---|---|---|---|---|
| 🟦 **PLANEJAMENTO** | strategic | `strategics/`, `life-ops/planner/`, `vibe-ops/base/`, `vibe-ops/vectors/`, raiz (AGENTS, CLAUDE, CONCEPTUAL, SYSTEMS_TOPOLOGY, CLUSTER_*, ÍNDICE PROGRESSIVO) | Sonhos, IKIGAi, 4-níveis, matemática, frameworks | Humano + Strategist |
| 🟩 **DOCUMENTAÇÃO** | specs/ADRs | `vibe-ops/{planning,specs,architecture,doc,contracts,artifacts,migrations,schema_registry}/` | PRDs, schemas, ADRs, data-mesh | AI agents + Arquiteto |
| 🟨 **CÓDIGO** | implementation | `life/{cli,centrals,handlers,plugins}/`, `vibe-ops/src/`, `life-ops/life_tatics/`, `taskwarrior/{scripts,pwsh,help,config}/`, `vibe-ops/vibeops-tui/` | Python, Rust, shell, TW | Coding agents + Dev |
| 🟥 **DADOS** | storage/contracts | `vibe-ops/src/storage/`, `vibe_ops.db`, `chroma_db/`, `taskwarrior/.task/`, `vibe-ops/{contracts,src/contracts,schema_registry}/` | SQLite, Chroma, TW, schemas | Backend agents |

### Como ler este índice

| Se você é... | Comece por... |
|---|---|
| Humano entendendo o sistema | §0 → §1 → §5 (visão geral) |
| AI agent implementando | §3 (código) → §5 (5 sub-sistemas) → §9 (regras) |
| AI agent auditando | §5 → §6 (cuidar vs ignorar) → §7 (IKIGAi gap) |
| Arquiteto decidindo | §1 (planejamento) → §2 (docs) → §8 (conflitos) |

---

## §1. FACETA: PLANEJAMENTO (🟦)

**Propósito:** estratégia, propósito, matemática, frameworks. Onde mora o "porquê".

```
life/                                # ROOT CANÔNICO
├── AGENTS.md                        # 260 linhas — regras para o agente
├── CLAUDE.md                        # 280 linhas — guia Claude Code
├── CONCEPTUAL_MODEL.md              # ~500 linhas — T→B→S, 5 tensões
├── SYSTEMS_TOPOLOGY.md              # ~800 linhas — middlewares M1-M8
├── CLUSTER_PLAN.md                  # 1861 linhas (v1.1) — Cluster 1
├── CLUSTER_PROJ.md                  # ~1100 linhas — Cluster 2
├── CLUSTER_STUDY.md                 # ~900 linhas — Cluster 3
├── docs/
│   └── ÍNDICE PROGRESSIVO.md        # 387 linhas — strategic index
│
├── strategics/                      # 9 docs (PT-BR, planning puro)
│   ├── 00-ÍNDICE-PROGRESSIVO.md
│   ├── Modelagem Operacional.md
│   ├── Planejamento (Estratégico e Tático).md
│   ├── Hierarquia de Objetivos.md
│   ├── Desempenho Subjacente.md
│   ├── Integracao_Tatica.md
│   ├── Análise (Tático e Operacional).md
│   ├── design_system_and_knowledge_tracking.md
│   └── system_architecture_and_tracking_framework.md
│
├── life-ops/
│   └── planner/                     # 3 docs matemática
│       ├── Points_of_premisses-task-habits.md
│       ├── SCALAR_DECOMPOSITION_BACKLOG.md
│       └── time-lenghts_reviews.md
│
└── vibe-ops/
    ├── base/                        # 4 docs (90K + 815K + chat exports)
    │   ├── IKIGAi.md
    │   ├── Planning_notes.md
    │   ├── Produtividade Algorítmica Visual.md
    │   └── chat exports
    └── vectors/                     # 4 vetores IKIGAi + README
        ├── README.md
        ├── vector-passion.md
        ├── vector-skill.md
        ├── vector-market.md
        └── vector-revenue.md
```

| Doc | Tipo | Audiência | Status |
|---|---|---|---|
| `AGENTS.md` | Regras do agente | AI agents | 🟢 |
| `CLAUDE.md` | Guia Claude Code | AI agents | 🟢 |
| `CONCEPTUAL_MODEL.md` | T→B→S framework | AI + humano | 🟢 v1.0 |
| `SYSTEMS_TOPOLOGY.md` | Middlewares M1-M8 | AI + arquiteto | 🟢 v1.0 |
| `CLUSTER_PLAN.md` | Standalone Memory Machine | AI + dev | 🟢 v1.1 (com drilldowns) |
| `CLUSTER_PROJ.md` | Standalone Memory Machine | AI + dev | 🟢 v1.0 |
| `CLUSTER_STUDY.md` | Standalone Memory Machine | AI + dev | 🟢 v1.0 |
| `strategics/00-ÍNDICE-PROGRESSIVO.md` | Strategic index | Humano | 🟢 |
| `strategics/Modelagem Operacional.md` | Pirâmide 4 níveis | Humano | 🟢 |
| `life-ops/planner/Points_of_premisses-task-habits.md` | Q_HE, R_n, H(t), E(t) | AI + dev | 🟢 |
| `life-ops/planner/SCALAR_DECOMPOSITION_BACKLOG.md` | 27 modelos matemáticos | AI + dev | 🟢 |
| `vibe-ops/base/IKIGAi.md` | Conceitual IKIGAi | Humano | 🟢 |
| `vibe-ops/vectors/*.md` | Vetores operacionais | AI + humano | 🟢 |

---

## §2. FACETA: DOCUMENTAÇÃO (🟩)

**Propósito:** requisitos, contratos, ADRs, decisões. Onde mora o "como" abstrato.

```
vibe-ops/
├── planning/                        # 7 PRDs + 3 templates + README
│   ├── README.md                    # 12 linhas → REESCREVER (ver SW4)
│   ├── PRD-01-temporal-engine.md
│   ├── PRD-02-habit-tracker.md
│   ├── PRD-03-study-backlog.md
│   ├── PRD-04-project-execution.md
│   ├── PRD-05-metrics-health.md
│   ├── PRD-06-policy-governance.md
│   ├── PRD-07-ikigai-vectors.md
│   ├── TEMPLATE-epic-sprint.md
│   ├── TEMPLATE-micro-ciclo.md
│   └── TEMPLATE-weekly-review.md
│
├── specs/                           # 8 prd-* + 5 schema-* + SPEC-05
│   ├── README.md                    # 4 linhas → REESCREVER
│   ├── prd-{temporal,habit,study,project,metrics,policy,ikigai}-*.md  (mirrors)
│   ├── schema-frontmatter-contract.md    # deprecado
│   ├── schema-frontmatter-contract-v2.md # canônico
│   ├── schema-planner-extension.md
│   ├── schema-pydantic-models.md         # deprecado
│   ├── schema-pydantic-models-v2.md      # canônico
│   └── SPEC-05-cybernetic-epistemic-mesh.md
│
├── architecture/                    # ADRs (ver SW3)
│   ├── README.md
│   ├── ADR-001-data-flow-topology.md    # 141 linhas, OK
│   ├── ADR-002-mesh-contracts-state-machines.md # VAZIO (0 bytes) → preencher
│   ├── ADR-003-ikigai-as-meta-brain.md  # NOVO
│   ├── ADR-004-hybrid-rag-strategy.md   # NOVO
│   └── ADR-005-data-mesh-topology.md    # NOVO
│
├── doc/                             # 6 strategy docs (4 únicos + 2 TW)
│   ├── 01-data-mesh-strategy.md
│   ├── 01.5-data-contracts-and-pipelines.md  (29K)
│   ├── 02-tw-factory-reset.md
│   ├── 03-data-mesh-enrichment.md       (27K)
│   ├── solucoes_extensoes_tw.md
│   └── tw-vanilla_limits_analysis.md
│
├── contracts/                       # 2 JSON
│   ├── roadmap_v1.json
│   └── study_topic_v1.json
│
├── artifacts/                       # 3 samples
│   ├── pm-agnostic-metadata.md
│   ├── sample_topic.md
│   └── topology-diagrams.md
│
├── migrations/                      # 3 SQL + 1 Python
│   ├── 001_create_dev_cluster_tables.sql  (10K)
│   ├── 002_roadmap_sync_v1.sql            (1.4K)
│   ├── 003_epistemic_priority_view.sql    (3.5K)
│   └── versions/001_create_dev_cluster.py
│
└── schema_registry/                 # legacy
    └── registry.yaml
```

| Doc | Tipo | Status |
|---|---|---|
| `vibe-ops/planning/PRD-*.md` (7) | Product Requirements | 🟢 |
| `vibe-ops/specs/prd-*.md` (7) | PRD mirrors (engenharia) | 🟢 |
| `vibe-ops/specs/schema-pydantic-models-v2.md` | Pydantic v2 schema canônico | 🟢 |
| `vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md` | Architecture spec | 🟢 |
| `vibe-ops/architecture/ADR-001.md` | Data flow decision | 🟢 |
| `vibe-ops/architecture/ADR-002.md` | Mesh contracts decision | 🔴 VAZIO |
| `vibe-ops/architecture/ADR-003.md` (a criar) | IKIGAi as meta-brain | 🟡 PROPOSTA |
| `vibe-ops/doc/01-data-mesh-strategy.md` | Strategy vision | 🟢 |
| `vibe-ops/doc/01.5-data-contracts-and-pipelines.md` | Contracts master | 🟢 |
| `vibe-ops/migrations/*.sql` (3) | DB migrations | 🟢 |

> **⚠️ Duplicação intencional:** `vibe-ops/planning/PRD-*.md` e `vibe-ops/specs/prd-*.md` têm **conteúdo idêntico** hoje, mas com **propósito diferente**: planning = requirements, specs = engineering. **Não mesclar** (append-only). Cross-refs devem ser explícitos.

---

## §3. FACETA: CÓDIGO (🟨)

**Propósito:** implementação executável. Onde mora o "como" concreto.

### 3.1. Root CLI (Life)

```
life/
├── cli/                             # 5 arquivos
│   ├── cli.py                       # Typer main app
│   ├── config.py                    # LifeConfig dataclass
│   ├── log.py                       # Structured logger
│   ├── test_runner.py               # Pytest discovery
│   └── __init__.py
│
├── centrals/                        # 6 arquivos
│   ├── base.py                      # BaseCentral (run_cli helper)
│   ├── task.py                      # Task central → TW
│   ├── finance.py                   # Finance central → fin_ops
│   ├── knowledge.py                 # Knowledge central → leitura/mindmaps/notes
│   ├── research.py                  # Research central → research
│   └── __init__.py
│
├── handlers/                        # 3 arquivos
│   ├── daily.py                     # run() — task today + finance
│   ├── weekly.py                    # run() — review + finance + metrics
│   └── __init__.py
│
└── plugins/                         # 4 arquivos
    ├── protocol.py                  # PluginProtocol (4 hooks)
    ├── loader.py                    # File-system discovery
    ├── builtin/health_check.py
    └── __init__.py
```

| Arquivo | Cluster | Papel | Status |
|---|---|---|---|
| `cli/cli.py` | (hub) | Main Typer app, mount centrals | 🟢 |
| `cli/config.py` | (hub) | YAML + env config loader | 🟢 |
| `handlers/daily.py` | (hub) | Orquestrador diário | 🟡 stub (não chama hooks) |
| `handlers/weekly.py` | (hub) | Orquestrador semanal | 🟡 stub |
| `centrals/base.py` | (hub) | ABC run_cli() helper | 🟢 |
| `centrals/task.py` | PROJ | Task central | 🟡 |
| `centrals/finance.py` | (hub) | Finance central | 🟡 |
| `centrals/knowledge.py` | STUDY | Knowledge central | 🟡 |
| `centrals/research.py` | (hub) | Research central | 🟡 |
| `plugins/protocol.py` | (hub) | Plugin lifecycle hooks | 🟢 (declarados, não chamados) |
| `plugins/loader.py` | (hub) | Plugin discovery | 🟢 |
| `plugins/builtin/health_check.py` | (hub) | Health check command | 🟢 |

### 3.2. vibe-ops (Cybernetic Control Center)

```
vibe-ops/
├── src/
│   ├── main.py                      # argparse CLI: run-daily, status, gaps, sync
│   ├── vibe_cli.py                  # Typer+Rich CLI: sync_file, hybrid_search
│   ├── cybernetics/                 # 2 arquivos
│   │   ├── daily_loop.py            # Target-Sensor-Adjuster
│   │   └── engine.py
│   ├── middleware/                  # 1 arquivo
│   │   └── sync_engine.py           # Obsidian ↔ SQLite ↔ TW bridge
│   ├── pipeline/                    # ~30 arquivos (largest sub-pkg)
│   │   ├── policy_engine.py         # 4-state state machine
│   │   ├── ikigai_scorer.py         # GAP: diverge de conceitual
│   │   ├── mvl_orchestrator.py
│   │   ├── rag_indexer.py
│   │   ├── tw_sync.py / tw_sync_adapter.py
│   │   ├── sync_orchestrator.py / reverse_sync.py
│   │   ├── roadmap_sync_ingest.py
│   │   ├── enrichment.py / enrichment_engine.py
│   │   ├── fk_resolver.py
│   │   ├── frontmatter_parser.py
│   │   ├── daily_consolidator.py
│   │   ├── cognitive_debt_tracker.py
│   │   ├── knowledge_tree.py / knowledge_telemetry.py
│   │   ├── learning_outcome_processor.py
│   │   ├── gap_engine.py
│   │   ├── study_manager.py
│   │   ├── ingestion_engine.py
│   │   ├── analytics_emitter.py
│   │   ├── pipeline_state_machine.py
│   │   ├── router.py / unified_router.py
│   │   ├── schema_registry.py / contracts.py / metadata_catalog.py
│   │   ├── harness_epistemic.py / harness_metrics.py
│   │   └── code_review_sync.py
│   ├── models/                      # 12 entity files
│   │   ├── temporal_entities.py
│   │   ├── habit_entities.py
│   │   ├── study_entities.py
│   │   ├── project_entities.py
│   │   ├── metric_entities.py
│   │   ├── policy_entities.py
│   │   ├── ikigai_entities.py      # ⚠️ GAP: 18 linhas
│   │   ├── rag_entities.py
│   │   ├── knowledge_entities.py
│   │   ├── health_entities.py
│   │   ├── feedback_entities.py
│   │   ├── doc_entities.py
│   │   ├── contracts.py
│   │   ├── operational_entities.py
│   │   └── __init__.py
│   ├── schemas/                     # 2 arquivos
│   │   ├── pydantic_v2.py
│   │   └── registry.py
│   ├── storage/                     # 8 arquivos
│   │   ├── schema.sql               # ⚠️ CANÔNICO
│   │   ├── sqlite_store.py / sqlite_adapter.py
│   │   ├── sqlite_vec_integration.py
│   │   ├── chroma_adapter.py / vector_store.py
│   │   ├── data_mesh_adapter.py
│   │   ├── metadata_orm.py / orm.py
│   │   └── ueid.py
│   ├── embeddings/                  # 2 arquivos
│   │   ├── provider.py
│   │   └── config.py
│   ├── integration/                 # 2 arquivos
│   │   ├── obsidian_parser.py
│   │   └── semantic_engine.py
│   ├── parsers/                     # 1 arquivo
│   │   └── code_parser.py
│   └── contracts/                   # 4 arquivos
│       ├── planning.v1.yaml
│       ├── registry.yaml
│       ├── roadmap_sync_v1.py
│       └── sync_contract_v1.py
│
├── scripts/                         # 5 ps1 + 2 py
│   ├── audit_github_execution.ps1
│   ├── setup_git_telemetry_hook.ps1
│   ├── setup_scheduler.ps1
│   ├── vibeops_loop.ps1
│   ├── search_mesh.py
│   ├── test_mvl_ingestion.py
│   └── __init__.py
│
├── tests/                           # 2 arquivos
│   ├── test_knowledge_telemetry.py
│   └── test_mvl_orchestrator.py
│
├── scratch/                         # 8 experimentais (NÃO production)
│
└── vibeops-tui/                     # Rust TUI (ratatui)
    ├── Cargo.toml / Cargo.lock
    └── src/{main.rs, persistence.rs}
```

| Arquivo-chave | Cluster | Papel | Status |
|---|---|---|---|
| `vibe-ops/src/main.py` | (hub) | argparse CLI | 🟢 |
| `vibe-ops/src/vibe_cli.py` | (hub) | Typer+Rich CLI | 🟢 |
| `vibe-ops/src/cybernetics/daily_loop.py` | PLAN | Cybernetic loop | 🟡 parcial |
| `vibe-ops/src/middleware/sync_engine.py` | PROJ | Obsidian↔SQLite↔TW | 🟡 |
| `vibe-ops/src/pipeline/policy_engine.py` | PLAN | 4-state machine | 🟡 |
| `vibe-ops/src/pipeline/ikigai_scorer.py` | PLAN (meta-brain) | ⚠️ DIVERGE de conceitual | 🟡 GAP |
| `vibe-ops/src/pipeline/mvl_orchestrator.py` | (all) | Minimum Viable Loop | 🟡 |
| `vibe-ops/src/pipeline/rag_indexer.py` | STUDY | Hybrid RAG | 🟡 |
| `vibe-ops/src/pipeline/tw_sync.py` | PROJ | TW sync | 🟡 |
| `vibe-ops/src/pipeline/roadmap_sync_ingest.py` | PROJ | Roadmap ingest | 🟡 |
| `vibe-ops/src/models/ikigai_entities.py` | PLAN | ⚠️ GAP: 18 linhas | 🔴 |
| `vibe-ops/src/models/study_entities.py` | STUDY | Study entities | 🟢 |
| `vibe-ops/src/models/project_entities.py` | PROJ | Project entities | 🟢 |
| `vibe-ops/src/storage/schema.sql` | (hub) | CANÔNICO schema | 🟢 |
| `vibe-ops/vibeops-tui/src/main.rs` | (viz) | Rust dashboard | 🟢 |

### 3.3. life-ops (Submódulo Python Standalone)

```
life-ops/
├── pyproject.toml                   # Poetry (life-tatics)
├── README.md
├── SPEC.md
└── life_tatics/                     # 3 arquivos
    ├── cli.py                       # Typer CLI (block, screentime, routine)
    ├── domain/
    │   ├── time_blocks.py
    │   └── screentime.py
    └── __init__.py
```

### 3.4. taskwarrior (Portable TW Stack)

```
taskwarrior/
├── README.md
├── SPEC.md
├── .cursor/rules/taskwarrior-setup.mdc
├── config/
│   ├── taskrc.template              # UDAs (energy, ikigai, wave)
│   └── hooks/on-exit
├── docs/                            # 7 docs (cheatsheet, howto, pitfalls, etc.)
├── help/                            # 18+ content/* + main-help.* + format-*
├── pwsh/task-aliases.ps1
└── scripts/                         # 8 scripts (.sh + .py)
    ├── daily-review.sh
    ├── weekly-review.sh
    ├── on-add.sh
    ├── calculate-metrics.py
    ├── working-days.py
    ├── generate-working-recur.sh
    ├── backup-and-recur.sh
    └── task_aliases.sh
```

---

## §4. FACETA: DADOS (🟥)

**Propósito:** persistência, contratos de dados, runtime stores.

### 4.1. SQLite Schema (canônico: `vibe-ops/src/storage/schema.sql`)

| Tabela | Cluster | Papel | Status |
|---|---|---|---|
| `temporal_waves` (regex `^W\d+_[A-Za-z]{3}_\d{4}$`) | PLAN | WAVE 15d tracking | 🟢 |
| `temporal_cycles` | PLAN | CYCLE 45d tracking | 🟢 |
| `temporal_phases` | PLAN | PHASE 180d tracking | 🟢 |
| `habits` | PLAN | Habit entities | 🟢 |
| `habit_states` | PLAN | Streak tracking (FK → habits) | 🟢 |
| `study_plans` / `study_topics` / `study_notes` | STUDY | PKM entities | 🟢 |
| `dev_projects` / `dev_roadmaps` / `dev_backlogs` / `dev_changelogs` | PROJ | Project entities | 🟢 |
| `policy_decisions` | PLAN | PolicyEngine output | 🟢 |
| `study_sessions` | STUDY | Session log | 🟢 |
| `planning_entities` | (hub) | Frontmatter mirror (idempotent) | 🟢 |
| `roadmap_sync` | PROJ | TW bridge (upstream_id UDA) | 🟢 |
| `changelog_entries` | PROJ | 🔴 GAP (schema existe, sem consumer) | 🟡 |
| `auto_indagacao` | PLAN | 🔴 GAP (proposto em CLUSTER_PLAN §6.5.B) | 🟡 |
| `metrics` | PLAN | Q_HE history | 🟢 |
| `v_epistemic_priority` (view) | STUDY | Topic priority ranking | 🟢 |
| `v_dashboard_study_dev` (view) | (viz) | Roadmap↔Study cross-join | 🟢 |

### 4.2. Runtime Stores

| Store | Path | Tamanho | Status |
|---|---|---|---|
| `vibe_ops.db` (root) | `life/vibe_ops.db` | runtime | 🟡 |
| `vibe-ops/vibe_ops.db` | `vibe-ops/vibe_ops.db` | runtime | 🟢 principal |
| `vibe-ops/test_vibe.db` | `vibe-ops/test_vibe.db` | test | 🟢 |
| `vibe-ops/vibe_mesh.db` | `vibe-ops/vibe_mesh.db` | runtime | 🟡 |
| `chroma_db/` | `vibe-ops/chroma_db/` | vector store | 🟡 |
| `taskwarrior/.task/` | `taskwarrior/.task/` | TW binary | 🟢 |

### 4.3. Contratos (YAML + JSON + Pydantic)

| Arquivo | Tipo | Status |
|---|---|---|
| `vibe-ops/src/contracts/planning.v1.yaml` | YAML schema (7531 bytes) | 🟢 canônico |
| `vibe-ops/src/contracts/registry.yaml` | Schema registry | 🟢 |
| `vibe-ops/contracts/roadmap_v1.json` | JSON contract | 🟢 |
| `vibe-ops/contracts/study_topic_v1.json` | JSON contract | 🟢 |
| `vibe-ops/src/contracts/roadmap_sync_v1.py` | Pydantic sync | 🟢 |
| `vibe-ops/src/contracts/sync_contract_v1.py` | Pydantic sync | 🟢 |
| `vibe-ops/src/schemas/pydantic_v2.py` | Pydantic v2 schemas | 🟢 |
| `vibe-ops/src/schemas/registry.py` | Schema registry | 🟢 |
| `vibe-ops/schema_registry/registry.yaml` | Legacy registry | 🟡 |

### 4.4. Migrations

| Arquivo | Cluster | Status |
|---|---|---|
| `vibe-ops/migrations/001_create_dev_cluster_tables.sql` | (bootstrap) | 🟢 |
| `vibe-ops/migrations/002_roadmap_sync_v1.sql` | PROJ | 🟢 |
| `vibe-ops/migrations/003_epistemic_priority_view.sql` | STUDY | 🟢 |
| `vibe-ops/migrations/versions/001_create_dev_cluster.py` | (bootstrap) | 🟢 |
| `vibe-ops/migrations/004_cluster_plan_v1.sql` (a criar) | PLAN | 🟡 TODO Sprint 1 |

---

## §5. OS 5 SUB-SISTEMAS MAPEADOS (visão integrada)

Cada sub-sistema é um **cluster autônomo** (Standalone Memory Machine) com
4 facetas. Esta matriz mostra o que vive em cada cluster.

| Sub-sistema | 🟦 Planejamento | 🟩 Documentação | 🟨 Código | 🟥 Dados |
|---|---|---|---|---|
| **1. Routines/Bloques (Cluster PLAN)** | `CLUSTER_PLAN.md` (1861L) | `vibe-ops/planning/PRD-{01,02,05,06}.md` | `vibe-ops/src/{pipeline/policy_engine, cybernetics/daily_loop, models/operational_entities}.py` | `temporal_*`, `habits`, `habit_states`, `metrics` |
| **2. Project PMO↔TW (Cluster PROJ)** | `CLUSTER_PROJ.md` (~1100L) | `vibe-ops/planning/PRD-04.md` + `vibe-ops/contracts/roadmap_v1.json` | `vibe-ops/src/{pipeline/{tw_sync,roadmap_sync_ingest,code_review_sync}, middleware/sync_engine, models/project_entities}.py` | `dev_*`, `roadmap_sync`, `changelog_entries` |
| **3. Studies/PKM (Cluster STUDY)** | `CLUSTER_STUDY.md` (~900L) | `vibe-ops/planning/PRD-03.md` + `vibe-ops/contracts/study_topic_v1.json` | `vibe-ops/src/{pipeline/{study_manager,rag_indexer,knowledge_tree,learning_outcome_processor,cognitive_debt_tracker,gap_engine}, models/study_entities}.py` | `study_plans`, `study_topics`, `study_notes`, `study_sessions` |
| **4. IKIGAi (Meta-Brain)** | `vibe-ops/base/IKIGAi.md` (90K) + `vibe-ops/vectors/` (4) + `life-ops/planner/ikigai_planning/` (a expandir) | `vibe-ops/planning/PRD-07.md` + `vibe-ops/architecture/ADR-003.md` (a criar) | `vibe-ops/src/{pipeline/ikigai_scorer (GAP), models/ikigai_entities (GAP 18L)}.py` | (sem tabela dedicada; alimenta policy_decisions, ikigai_vectors tables a criar) |
| **5. Habit/Cybernetics** | `life-ops/planner/Points_of_premisses-task-habits.md` | `vibe-ops/planning/PRD-02.md` (habit) + `PRD-06.md` (policy) | `vibe-ops/src/{pipeline/{policy_engine,ikigai_scorer,enrichment_engine}, models/habit_entities, cybernetics/{daily_loop,engine}}.py` | `habits`, `habit_states`, `policy_decisions`, `metrics` |

> **Nota:** Sub-sistemas 1 e 5 (PLAN + Habit) têm overlap significativo — `CLUSTER_PLAN.md` §4.5 mapeia IKIGAi↔PAV explicitamente. Sub-sistema 4 (IKIGAi) é o meta-cérebro que governa os outros 4.

---

## §6. QUAIS ARQUIVOS CUIDAR (vs QUAIS IGNORAR)

### 🟢 TOP 30 — CRÍTICOS (cuidar sempre)

1. `AGENTS.md` — regras do agente
2. `CLAUDE.md` — guia Claude Code
3. `CONCEPTUAL_MODEL.md` — T→B→S
4. `SYSTEMS_TOPOLOGY.md` — middlewares
5. `CLUSTER_PLAN.md` — Cluster 1
6. `CLUSTER_PROJ.md` — Cluster 2
7. `CLUSTER_STUDY.md` — Cluster 3
8. `docs/ÍNDICE PROGRESSIVO.md` — strategic index
9. `vibe-ops/src/storage/schema.sql` — DB schema canônico
10. `vibe-ops/src/middleware/sync_engine.py` — bridge
11. `vibe-ops/src/pipeline/policy_engine.py` — 4-state machine
12. `vibe-ops/src/pipeline/ikigai_scorer.py` — IKIGAi (com gap)
13. `vibe-ops/src/cybernetics/daily_loop.py` — loop principal
14. `vibe-ops/src/models/ikigai_entities.py` — Pydantic IKIGAi (com gap)
15. `vibe-ops/planning/PRD-07-ikigai-vectors.md` — spec IKIGAi
16. `vibe-ops/contracts/roadmap_v1.json` — contract roadmap
17. `vibe-ops/contracts/study_topic_v1.json` — contract study
18. `vibe-ops/src/contracts/planning.v1.yaml` — YAML planning
19. `vibe-ops/base/IKIGAi.md` — conceitual
20. `vibe-ops/vectors/vector-{passion,skill,market,revenue}.md` — 4 vetores
21. `life-ops/planner/Points_of_premisses-task-habits.md` — Q_HE
22. `life-ops/planner/SCALAR_DECOMPOSITION_BACKLOG.md` — 27 modelos
23. `life-ops/planner/time-lenghts_reviews.md` — WAVE/CYCLE/PHASE
24. `life-ops/life_tatics/cli.py` — CLI standalone
25. `life-ops/life_tatics/domain/{time_blocks,screentime}.py`
26. `taskwarrior/config/taskrc.template` — UDAs
27. `taskwarrior/scripts/{daily,weekly}-review.sh`
28. `handlers/{daily,weekly}.py` — handlers
29. `centrals/base.py` — BaseCentral
30. `centrals/task.py` — task central

### 🟡 TOP 30 — OPCIONAIS (cuidar quando relevante ao feature)

- 7 specs em `vibe-ops/specs/prd-*.md` (mirrors)
- 5 schemas em `vibe-ops/specs/schema-*.md`
- `vibe-ops/architecture/ADR-001` + 4 ADRs
- `vibe-ops/doc/01, 01.5, 02, 03, solucoes_extensoes_tw, tw-vanilla_limits`
- `vibe-ops/artifacts/*` (3 samples)
- 4 contratos (`vibe-ops/src/contracts/*`)
- 3 migrations + 1 Python migration
- `vibe-ops/scripts/*` (7 scripts)
- `vibe-ops/tests/*` (2 tests)
- `taskwarrior/{docs,help,pwsh,config}/*` (TW stack)
- 9 strategic docs em `strategics/`
- 8 MOCs + legados em `vibe-ops/context/`
- `vibe-ops/vibeops-tui/src/{main.rs,persistence.rs}` (Rust)

### ⚪ IGNORAR (não mexer)

- `time-tasker/` inteiro (snapshot, ver §8)
- `vibe-ops/scratch/test_*.py` (8 experimentais)
- `vibe-ops/context/Dream_Logger-algo-data_struct.md` (646K legado NLP — usuário decidiu NÃO usar)
- `vibe-ops/context/Day Logger Program Documentation.md` (legado Tkinter)
- `vibe-ops/base/Produtividade Algorítmica Visual.md` (815K — referenciar mas não editar)
- `vibe-ops/specs/.$concept_sys-archy.drawio.bkp` (backup)
- `vibe-ops/base/Semeio de Talentos.jpg` (imagem)
- `vibe-ops/base/chat-export-*.json` (chat exports, provenance only)
- `vibe-ops/context/chat-*.md` (provenance)
- `logs/*.log` (runtime, não versionar)
- `__pycache__/` (gerado)
- `chroma_db/` (gerado)
- `.task/` data (gerado)

---

## §7. ONDE MORA CADA "FACETA" DO IKIGAi

> O IKIGAi é o **sub-sistema 4** (meta-cérebro). Seus artefatos estão
> **espalhados** em 4 locais. Esta tabela é o mapa de duplicação conceitual.

| Vetor IKIGAi | Conceito (🟦) | Spec (🟩) | Código (🟨) | Dados (🟥) | Status |
|---|---|---|---|---|---|
| **Passion** | `vibe-ops/base/IKIGAi.md §1` + `vectors/vector-passion.md` | `PRD-07 §2-4` | `pipeline/ikigai_scorer.py` (não retorna passion, retorna health) | `habit_states` (FK → habits) | 🟡 GAP impl |
| **Skill** | `IKIGAi.md §1` + `vectors/vector-skill.md` | `PRD-07 §2-4` | `ikigai_scorer.py` (não retorna skill, retorna study) | `study_sessions`, `study_topics` | 🟡 GAP impl |
| **Market** | `IKIGAi.md §1` + `vectors/vector-market.md` | `PRD-07 §2-4` | `ikigai_scorer.py` (não retorna market) | (sem tabela dedicada) | 🔴 GAP total |
| **Revenue** | `IKIGAi.md §1` + `vectors/vector-revenue.md` | `PRD-07 §2-4` | `ikigai_scorer.py` (não retorna revenue, retorna dev) | `dev_projects.actual_revenue` | 🟡 GAP impl |
| **Course (5º contextual)** | `CONCEPTUAL_MODEL.md §3` | (não documentado) | (não implementado) | (sem tabela) | 🔴 GAP doc |
| **Meta-vetor $\|\vec{I}\|$** | `IKIGAi.md §Hypervisor` | `PRD-07 §4` | (não implementado) | (sem tabela) | 🔴 GAP total |
| **Vector weights $w_i$** | `CONCEPTUAL_MODEL.md §3` | `PRD-07 §2` | (parcial em `policy_engine`) | (sem tabela) | 🟡 parcial |
| **Regime PUSH/MAINTAIN/...** | `CONCEPTUAL_MODEL.md §4` | `PRD-06 §2` | `pipeline/policy_engine.py` | `policy_decisions` | 🟢 OK |
| **Q_HE formula** | `Points_of_premisses §3` | (não documentado) | (parcial em `policy_engine`) | `metrics.qhe` | 🟡 parcial |

### Gap mais crítico: `ikigai_scorer.py` (46 linhas)

```python
# Estado ATUAL (DIVERGE de conceitual):
return {"study": ..., "dev": ..., "health": ..., "global": ...}

# Estado ALVO (5 vetores canônicos):
return {
    "passion": float,
    "skill": float,
    "market": float,
    "revenue": float,
    "course": float,  # 5º contextual
    "ikigai_score": float,  # meta-vetor |\vec{I}|
    "alignment_label": "aligned|converging|misaligned|critical"
}
```

**Sprint 1 task:** Reescrever `ikigai_scorer.py` para alinhar com `PRD-07`.

---

## §8. CONFLITOS & DECISÕES (resolvidos)

| # | Conflito | Decisão Tomada | Documentação |
|---|---|---|---|
| **C1** | `time-tasker/` é cópia desatualizada do root | Manter como snapshot, marcar com `DEPRECATED-SNAPSHOT.md`, **NÃO renomear** | Este doc + `time-tasker/DEPRECATED-SNAPSHOT.md` |
| **C2** | `vibe-ops/planning/PRD-*.md` e `vibe-ops/specs/prd-*.md` têm conteúdo idêntico | Manter ambos (planning=requirements, specs=engineering). **NÃO mesclar** | `vibe-ops/specs/README.md` (a reescrever) |
| **C3** | `vibe-ops/specs/schema-frontmatter-contract.md` (v1) e `-v2.md` coexistentes | Marcar v1 como deprecado, v2 canônico | `vibe-ops/specs/README.md` |
| **C4** | `vibe-ops/specs/schema-pydantic-models.md` (v1) e `-v2.md` coexistentes | v2 canônico | Idem |
| **C5** | `vibe-ops/architecture/ADR-002-mesh-contracts-state-machines.md` está VAZIO (0 bytes) | Preencher (Sprint ADR-002 — SW3) | `vibe-ops/architecture/ADR-002` |
| **C6** | `vibe-ops/context/Data-MOC.md` está VAZIO (0 bytes) | Avaliar se é necessário (não bloquear) | — |
| **C7** | `ikigai_scorer.py` retorna 4 vetores ERRADOS (study/dev/health/global) vs conceitual (passion/skill/market/revenue) | Reescrever no Sprint 1 (Task crítica) | `vibe-ops/architecture/ADR-003` (a criar) |
| **C8** | `time-tasker/life/vibe-ops/doc/` está desatualizado (sem `03-data-mesh-enrichment.md`) | Root é canônico, snapshot é obsoleto (parte de C1) | C1 + `DEPRECATED-SNAPSHOT.md` |
| **C9** | `vibe-ops/base/Produtividade Algorítmica Visual.md` é HUGE (815K) e o usuário renomeou mentalmente para "time-tasker" | Renomeação **NÃO** aplicada ao filesystem; tratar como referenciado em `CLUSTER_PLAN §0` (PAV = Produtividade Algorítmica Visual) | `CLUSTER_PLAN.md §0` |
| **C10** | `life-ops/life_tatics/` (submódulo Python) × `time-tasker/` (snapshot) | Ambos coexistem com papéis diferentes: `life_tatics` = Python standalone; `time-tasker` = nome do projeto | `CLAUDE.md §Project Overview` |

---

## §9. COMO AGENTES DEVEM USAR ESTE ÍNDICE

### 9.1. Se você é um agente implementando Cluster PLAN

1. Leia `CLUSTER_PLAN.md §0-2` (declaração + escopo + entidades)
2. Leia `CONCEPTUAL_MODEL.md §3-4` (vetores IKIGAi + regimes)
3. Leia `vibe-ops/planning/PRD-02-habit-tracker.md` (H(t), E(t), Q_HE)
4. **Antes de implementar**, leia `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` (decisão de IKIGAi como meta-brain)
5. **Implemente Sprint 1** (CLI `plan journal log` → SQLite → report)

### 9.2. Se você é um agente implementando Cluster PROJ

1. Leia `CLUSTER_PROJ.md` (Standalone Memory Machine)
2. Leia `vibe-ops/planning/PRD-04-project-execution.md`
3. Leia `vibe-ops/contracts/roadmap_v1.json`
4. Implemente RICE+IKIGAi weighting

### 9.3. Se você é um agente implementando Cluster STUDY

1. Leia `CLUSTER_STUDY.md`
2. Leia `vibe-ops/planning/PRD-03-study-backlog.md`
3. Leia `vibe-ops/contracts/study_topic_v1.json`
4. Implemente prerequisites graph + Cognitive Debt

### 9.4. Se você é um agente auditando

1. Leia §5 (5 sub-sistemas mapeados)
2. Leia §7 (gap do IKIGAi scorer)
3. Rode: `git log --oneline -- vibe-ops/src/models/ikigai_entities.py` (ver evolução)
4. Identifique gaps preenchidos vs pendentes

### 9.5. Se você é um arquiteto decidindo nova tech

1. Leia `vibe-ops/architecture/ADR-001` (alternativas rejeitadas)
2. Leia `vibe-ops/architecture/ADR-002` (contratos)
3. Leia `vibe-ops/doc/01-data-mesh-strategy.md`
4. Documente nova decisão em ADR-XXX (template em ADR-001)

---

## §10. CONEXÕES CRUZADAS

Este índice se conecta com:

- **Documentos âncora:**
  - [`AGENTS.md`](AGENTS.md) §1-10
  - [`CLAUDE.md`](CLAUDE.md) §Project Overview + Architecture
  - [`docs/ÍNDICE PROGRESSIVO.md`](docs/%C3%8DNDICE%20PROGRESSIVO.md) (navegação estratégica)
- **Conceitual (porquê):**
  - [`CONCEPTUAL_MODEL.md`](CONCEPTUAL_MODEL.md) — T→B→S, 5 tensões
  - [`vibe-ops/base/IKIGAi.md`](vibe-ops/base/IKIGAi.md) — IKIGAi conceitual
  - [`vibe-ops/vectors/`](vibe-ops/vectors/) — 4 vetores operacionais
- **Topologia (como):**
  - [`SYSTEMS_TOPOLOGY.md`](SYSTEMS_TOPOLOGY.md) — middlewares M1-M8
  - [`vibe-ops/architecture/`](vibe-ops/architecture/) — ADRs
  - [`vibe-ops/doc/01-data-mesh-strategy.md`](vibe-ops/doc/01-data-mesh-strategy.md)
- **Clusters (o quê):**
  - [`CLUSTER_PLAN.md`](CLUSTER_PLAN.md) (1861 linhas) — Cluster 1
  - [`CLUSTER_PROJ.md`](CLUSTER_PROJ.md) (~1100 linhas) — Cluster 2
  - [`CLUSTER_STUDY.md`](CLUSTER_STUDY.md) (~900 linhas) — Cluster 3
- **Vida-ops (cérebro IKIGAi):**
  - [`life-ops/planner/Points_of_premisses-task-habits.md`](life-ops/planner/Points_of_premisses-task-habits.md) — Q_HE
  - [`life-ops/planner/SCALAR_DECOMPOSITION_BACKLOG.md`](life-ops/planner/SCALAR_DECOMPOSITION_BACKLOG.md) — 27 modelos
  - [`life-ops/planner/time-lenghts_reviews.md`](life-ops/planner/time-lenghts_reviews.md) — WAVE/CYCLE/PHASE
  - [`life-ops/life_tatics/`](life-ops/life_tatics/) — Python standalone
- **Estratégico (negócio):**
  - [`strategics/00-ÍNDICE-PROGRESSIVO.md`](strategics/00-%C3%8DNDICE-PROGRESSIVO.md)
  - [`strategics/Modelagem Operacional.md`](strategics/Modelagem%20Operacional.md)
- **Drilldowns novos (Q3 2026, em progresso):**
  - [`life-ops/planner/ikigai_planning/`](life-ops/planner/ikigai_planning/) (a criar)
  - `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` (a criar)
  - `vibe-ops/planning/CLUSTER_PLAN_BRD.md` (a criar)

---

*ARCHITECTURE_INDEX.md — v1.0 — 2026-06-05 — Índice de Arquitetura canônico do Algorithmic Life OS*
