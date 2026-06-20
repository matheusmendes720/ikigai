# SYSTEMS_TOPOLOGY.md

> **Índice-of-índices + Mapa de Middlewares do Algorithmic Life OS**
>
> Este documento é o **ponto de entrada canônico** para qualquer agente que precise entender *como os sistemas se conversam*. Ele complementa `AGENTS.md` (convenções para o agente) e `CLAUDE.md` (guia do Claude) com uma **visão relacional** do workspace.
>
> **Princípio-guia:** *sistemas independentes que se tornam mais fortes juntos*, através de middlewares que compartilham **apenas os dados necessários e relevantes** (engenharia de contexto fina, nunca acoplamento cego).
>
> **Última varredura:** 2026-06-05 — cobre todos os arquivos `.md`, `.py`, `.rs`, `.yaml`, `.sql`, `.toml`, `.sh`, `.ps1` do workspace.
>
> **Documento-irmão:** `CONCEPTUAL_MODEL.md` — o *porquê* (Tensão → Comportamento → Solução). Este doc é o *como* (mapa técnico de middlewares).
>
> **Documentos de cluster (Standalone Memory Machines):** `CLUSTER_PLAN.md` (rotinas/blocos), `CLUSTER_PROJ.md` (PMO↔TW), `CLUSTER_STUDY.md` (PKM + pré-req). Cada cluster é auto-contido e referencia ~100 arquivos do workspace.

---

## 0. COMO USAR ESTE DOCUMENTO

| Se você quer… | Vá para… |
|---|---|
| Entender a topologia geral de uma vez | §1 (Visão) |
| Ver o grafo de fluxo de dados | §2 (Mermaid topology) |
| Saber "onde está o doc de X?" | §3 (Mapa de Sistemas) |
| Achar a spec certa rapidamente | §4 (Índice de Specs) |
| Implementar um sistema novo | §5 (Contratos de Dados Ativos) |
| Auditar o que está vivo vs. stub | §6 (Estado de Implementação) |
| Fechar uma lacuna do Data-Mesh | §7 (Lacunas & Middlewares Propostos) |
| Entender um acrônimo | §8 (Glossário) |
| Saber o próximo passo crítico | §9 (Roadmap de Middlewares) |

---

## 1. VISÃO GERAL: 5 TIERS, 1 DATA-MESH

O workspace se organiza em **5 tiers** interligados por **contratos de dados tipados** (Pydantic + YAML) e **middlewares** (sync engines, parsers, oracles). Os tiers não são "camadas" — são **domínios autônomos** que se conectam por meio de **contratos explícitos**.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ TIER 0 — INTENÇÃO ESTRATÉGICA                                               │
│   docs, strategics/, vibe-ops/base/, life-ops/planner/                       │
│   (definição de sonhos, objetivos, IKIGAi vectors, modelos matemáticos)     │
├──────────────────────────────────────────────────────────────────────────────┤
│ TIER 1 — ORQUESTRAÇÃO (CLI HUB: `life`)                                     │
│   cli/, centrals/, handlers/, plugins/                                       │
│   (centrais que despacham para sub-módulos; handlers diários/semanais)     │
├──────────────────────────────────────────────────────────────────────────────┤
│ TIER 2 — MESH CIBERNÉTICO (Target-Sensor-Adjuster)                          │
│   vibe-ops/src/cybernetics/ + pipeline/ + middleware/                        │
│   (loop diário, motor de políticas, RAG híbrido, score IKIGAi)              │
├──────────────────────────────────────────────────────────────────────────────┤
│ TIER 3 — ARMAZENAMENTO E CONTRATOS                                          │
│   vibe-ops/src/storage/ (SQLite + Chroma + UEID)                             │
│   vibe-ops/src/schemas/  (Pydantic v2)                                       │
│   vibe-ops/src/contracts/ (YAMLs)                                            │
│   vibe-ops/src/models/   (12 clusters Pydantic)                              │
│   vibe-ops/migrations/    (SQL DDL)                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ TIER 4 — EXECUÇÃO (Downstream Tools)                                        │
│   taskwarrior/         (binário TW + scripts + .taskrc + hooks)              │
│   life-ops/            (life-tatics: standalone, time blocks/screentime)     │
│   vibe-ops/vibeops-tui/ (Rust ratatui, polling 1Hz sobre vibe_ops.db)        │
└──────────────────────────────────────────────────────────────────────────────┘

MIDDLEWARES (atravessam todos os tiers):
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ • SyncEngine            (Obsidian ↔ SQLite ↔ Taskwarrior)              │
   │ • HybridRAGIndexer      (Markdown → embeddings → vector store)          │
   │ • PolicyEngine          (severity → 4-state machine)                   │
   │ • IkigaiScorer          (SQLite queries → vector IKIGAi)                │
   │ • GapSearchEngine       (cognitive + execution debt analysis)           │
   │ • BinaryKnowledgeTree   (study topic dependencies)                      │
   │ • SchemaRegistry        (Pydantic ↔ YAML contracts, generator)          │
   │ • UEID Manager          (cluster:entity:id → string key)                │
   │ • FrontmatterParser     (Markdown YAML → Pydantic)                      │
   │ • Timewarrior ↔ Energy  (TW tags → E(t) curve update)                   │
   │ • MVL Orchestrator      (state machine: ingest → enrich → persist)      │
   └─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. TOPOLOGIA DE FLUXO DE DADOS (Mermaid)

```mermaid
flowchart TB
    subgraph T0["TIER 0 — Intenção"]
        IKIGAI["IKIGAi Vectors<br/>(vibe-ops/base/IKIGAi.md)"]
        HYP["Hypervisor / Setpoints<br/>(base/Produtividade Algorítmica Visual)"]
        STRAT["Strategics/ docs<br/>(Modelagem, Hierarquia,<br/>Desempenho, Integração)"]
        MATH["life-ops/planner/<br/>(27 modelos matemáticos,<br/>5×3×3 fractal)"]
    end

    subgraph T1["TIER 1 — Orquestração (life CLI)"]
        CLIdaily["handlers/daily.py<br/>(subprocess aggregator)"]
        CLIweek["handlers/weekly.py"]
        CENT["centrals/<br/>task · finance · knowledge · research"]
        PLG["plugins/builtin/health_check<br/>(+ lifecycle hooks stubs)"]
    end

    subgraph T2["TIER 2 — Mesh Cibernético (vibe-ops/src/)"]
        LOOP["CyberneticDailyLoop<br/>execute_daily_cycle()"]
        POL["PolicyEngine<br/>PUSH/MAINTAIN/REDUCE/RECOVER"]
        IKS["IkigaiScorer<br/>(GAP: vetores divergentes)"]
        SYNC["SyncEngine<br/>upstream_id = SHA256[:12]"]
        RAG["HybridRAGIndexer<br/>SQLite-vec + ChromaDB"]
        GAP["GapSearchEngine<br/>(cognitive + execution debt)"]
        BKT["BinaryKnowledgeTree"]
        MVL["MVL Orchestrator<br/>(state machine)"]
    end

    subgraph T3["TIER 3 — Storage & Contratos"]
        SQL[("vibe_ops.db<br/>(SQLite schema.sql)")]
        CHR[("chroma_db/<br/>(vector store)")]
        OBS[("Obsidian Vault<br/>(Markdown + YAML)")]
        PYD["Pydantic v2 Models<br/>12 clusters"]
        YML["YAML Contracts<br/>registry + planning.v1"]
    end

    subgraph T4["TIER 4 — Execução"]
        TW["Taskwarrior<br/>(binário + .task DB)"]
        TIMEW["Timewarrior<br/>(.timew files)"]
        LIFET["life-tatics CLI<br/>(time blocks + screentime)"]
        TUI["Rust TUI<br/>(vibeops-tui/, 1Hz polling)"]
    end

    %% Fluxos de intenção
    IKIGAI -->|alvo motivacional| HYP
    MATH -->|constantes WORK_RATIO, Q_HE| HYP
    STRAT -->|diretrizes, templates| HYP
    HYP -->|setpoints diários| LOOP

    %% Orquestração → Centrals
    CLIdaily --> CENT
    CLIweek --> CENT
    CENT -.-> PLG

    %% Centrals → Taskwarrior
    CENT -->|task/scripts/*| TW
    CENT -->|fin_ops, leitura, etc.| TIMEW

    %% Obsidian → Sync (core do Data-Mesh)
    OBS -->|frontmatter YAML| SYNC
    SYNC -->|upstream_id FK| SQL
    SYNC -->|push compliant tasks| TW
    TW -->|reverse sync (status, time)| SYNC
    TIMEW -->|tags + durations| SYNC

    %% Sync → Cybernetic Loop
    SYNC -->|planning_entities| LOOP
    SQL -->|study_sessions, habit_states| LOOP

    %% Loop interno
    LOOP --> POL
    LOOP --> IKS
    LOOP --> RAG
    LOOP --> GAP
    LOOP --> MVL
    POL -->|policy_decisions row| SQL
    MVL -->|enrichment de entidades| SQL

    %% RAG
    OBS -->|chunks| RAG
    RAG --> CHR
    RAG --> SQL

    %% Read paths (consulta)
    BKT -->|prereqs resolvidos| GAP
    GAP -->|gaps report| LOOP
    TUI -->|SELECT * FROM policy_decisions| SQL
    TUI -->|read-only display| TUI
    LIFET -->|time_blocks, screentime| SQL
    IKS -->|aggregates habit+dev+study| SQL

    %% Contratos atravessando tudo
    PYD -.->|validação| SYNC
    PYD -.->|validação| MVL
    YML -.->|registry| PYD
    YML -.->|schema-first| SQL
```

---

## 3. MAPA DE SISTEMAS (Índice exaustivo de arquivos)

Cada linha = **um sistema ou subsistema autônomo** com seus arquivos reais. Use o caminho como referência direta.

### 3.1 TIER 0 — Intenção Estratégica

| Sistema | Arquivo(s) principal(is) | Propósito | Status |
|---|---|---|---|
| **IKIGAi Vectors** (função objetivo) | `vibe-ops/base/IKIGAi.md` (4-vec: passion/skill/market/revenue) | Vetores motivacionais; alvo do Hypervisor | 🟡 **GAP:** `pipeline/ikigai_scorer.py` usa 4-vec *diferente* (study/dev/health/global) |
| **Hypervisor** (orquestrador de setpoints) | `vibe-ops/base/IKIGAi.md` §Hypervisor + `vibe-ops/base/Produtividade Algorítmica Visual.md` | Calcula setpoints diários (deep_work/laborative/content_lab/data_review) | 🟢 Spec forte; ⚠️ sem implementação dedicada (PolicyEngine cobre parcialmente) |
| **Modelo PAE × Hierárquico** | `strategics/Modelagem Operacional.md` + `strategics/Planejamento (Estratégico e Tático).md` | Pirâmide 4 níveis (Sonhos→Objetivos→Metas→Tarefas) com dual-frame temporal | 🟢 Doc canônico |
| **Desempenho Subjacente (5×3×3)** | `strategics/Desempenho Subjacente.md` | Folha de pontuação proporcional: 5d exec / 3 sem análise / 3 meses estratégia | 🟢 Doc |
| **Hierarquia de Objetivos** | `strategics/Hierarquia de Objetivos.md` | Templates de revisão semanal + mensal | 🟢 Doc |
| **Integração Tática** | `strategics/Integracao_Tatica.md` | Sistema de labels e tags de documentação | 🟢 Doc |
| **Análise Tático-Operacional** | `strategics/Análise (Tático e Operacional).md` | Blocos diários, rotinas, relatórios | 🟢 Doc |
| **Design System & Knowledge Tracking** | `strategics/design_system_and_knowledge_tracking.md` | Patterns de design para o sistema de rastreamento | 🟢 Doc |
| **System Architecture & Tracking Framework** | `strategics/system_architecture_and_tracking_framework.md` | Framework macro | 🟢 Doc |
| **Índice Progressivo Raiz** | `strategics/00-ÍNDICE-PROGRESSIVO.md` + `docs/ÍNDICE PROGRESSIVO.md` | Dois índices-irmãos: navegação do workspace | 🟢 Doc |
| **PRD IKIGAi** | `vibe-ops/specs/prd-ikigai-vectors.md` | Especificação técnica dos vetores | 🟢 Spec |
| **PRD Hypervisor/Policies** | `vibe-ops/specs/prd-policy-governance.md` | Spec de governança política | 🟢 Spec |
| **Planejamento Matemático (life-ops)** | `life-ops/planner/time-lenghts_reviews.md` (1171 linhas) | Modelo fractal WAVE/CYCLE/PHASE com 27 modelos matemáticos | 🟢 **Doc denso e subutilizado** — contém WORK_RATIO, supercompensation, Q_HE |
| **SCALAR DECOMPOSITION BACKLOG** | `life-ops/planner/SCALAR_DECOMPOSITION_BACKLOG.md` (2101 linhas) | Backlog vivo: 27 modelos, 16 entity types, 35 itens, integration matrix | 🟢 **Doc denso e subutilizado** — mapa módulo/arquivo |
| **Crítica de Rigor Matemático** | `life-ops/planner/Points_of_premisses-task-habits.md` (226 linhas) | Operadores de revisão espaçada (renormalização de λ, k, vetor s) | 🟢 Doc |
| **Planning Notes (life-tatics)** | `life-ops/life_tatics/Planning_notes.md` | Notas de planejamento avulsas | 🟡 Nota solta |

### 3.2 TIER 1 — Orquestração (`life`)

| Sistema | Arquivo(s) | Propósito | Status |
|---|---|---|---|
| **CLI raiz (Typer)** | `cli/cli.py` (246 linhas) + `cli/__init__.py` (`__version__ = "0.1.0"`) | Entry point `python -m life.cli` | 🟢 |
| **Config loader** | `cli/config.py` (96 linhas) | `LifeConfig` dataclass, YAML + env; resolve submodules | 🟢 ⚠️ paths default podem não existir |
| **Logger estruturado** | `cli/log.py` | Plain ou JSON, file + stderr | 🟢 |
| **Test runner** | `cli/test_runner.py` (90 linhas) | Descobre `tests/` em submodules; roda pytest | 🟢 |
| **BaseCentral (ABC)** | `centrals/base.py` (56 linhas) | `run_cli(cwd, module, args, json_out)` para sub-módulos | 🟢 |
| **Task central** | `centrals/task.py` (137 linhas) | Dispatch para `task` binário + scripts `taskwarrior/scripts/` | 🟢 |
| **Finance central** | `centrals/finance.py` (106 linhas) | Dispatch para `fin_ops` (track/report/simulate/derivatives) | 🟡 fin_ops não existe neste repo |
| **Knowledge central** | `centrals/knowledge.py` (160 linhas) | Dispatch para `leitura`/`mindmaps`/`notes` (cada um standalone) | 🟡 sub-módulos não existem |
| **Research central** | `centrals/research.py` (90 linhas) | Dispatch para `research` CLI (map/crawl/search) | 🟡 sub-módulo não existe |
| **Daily handler** | `handlers/daily.py` (91 linhas) | Roda centrals via subprocess `python -m life.cli ...`; agrega erros | 🟢 |
| **Weekly handler** | `handlers/weekly.py` (similar) | Semelhante ao daily para cadência semanal | 🟢 |
| **Plugin Protocol** | `plugins/protocol.py` (39 linhas) | `register(app)`, `before_daily/after_daily/...` (declarados) | 🟡 **GAP:** hooks não chamados |
| **Plugin Loader** | `plugins/loader.py` (105 linhas) | Descobre de `cfg.plugin_dirs` via `PLUGIN`/`plugin`/`Plugin` attr | 🟢 |
| **Health check (built-in)** | `plugins/builtin/health_check.py` (52 linhas) | Verifica existência de submodules + `task_scripts` | 🟢 |

### 3.3 TIER 2 — Mesh Cibernético (vibe-ops/src/)

| Sistema | Arquivo(s) | Propósito | Status |
|---|---|---|---|
| **CLI argparse (legado)** | `src/main.py` (197 linhas) | `run-daily`, `status`, `gaps`, `sync` | 🟢 |
| **CLI Typer+Rich (avançado)** | `src/vibe_cli.py` | `sync_file`, `hybrid_search`, `gaps`, `debt_dashboard` | 🟢 |
| **Daily Cybernetic Loop** | `src/cybernetics/daily_loop.py` (122 linhas) | `CyberneticDailyLoop.execute_daily_cycle()` orquestra Target→Sensor→Adjuster→Persist→Sync→Index | 🟢 |
| **PolicyEngine (Adjuster)** | `src/pipeline/policy_engine.py` (118 linhas) | Máquina 4-estados PUSH/MAINTAIN/REDUCE/RECOVER; severidade | 🟢 |
| **BinaryKnowledgeTree + GapSearchEngine** | `src/cybernetics/engine.py` (111 linhas) | Detecta gaps cognitivos e execution debt (72h) | 🟢 |
| **SyncEngine (middleware master)** | `src/middleware/sync_engine.py` (138 linhas) | `sync_obsidian_to_sqlite`, `sync_sqlite_to_taskwarrior`, `sync_taskwarrior_to_sqlite`; `upstream_id` 12-char SHA-256 | 🟢 |
| **HybridRAGIndexer** | `src/pipeline/rag_indexer.py` | Indexa vault Obsidian em SQLite-vec + ChromaDB (fallback NumPy) | 🟢 |
| **IkigaiScorer** | `src/pipeline/ikigai_scorer.py` (46 linhas) | Score multi-dimensional; **GAP:** vetores errados | 🟡 |
| **Reverse Sync** | `src/pipeline/reverse_sync.py` | TW → SQLite (status, time logs) | 🟡 Parcial |
| **MVL Orchestrator** | `src/pipeline/mvl_orchestrator.py` | State machine: ingest → enrich → persist | 🟢 |
| **Enrichment Engine** | `src/pipeline/enrichment.py` + `enrichment_engine.py` | Adiciona metadados via cross-refs | 🟡 |
| **FK Resolver** | `src/pipeline/fk_resolver.py` | Resolve integridade referencial | 🟡 |
| **Ingestion Engine** | `src/pipeline/ingestion_engine.py` | Lê vault e parseia | 🟢 |
| **Frontmatter Parser** | `src/pipeline/frontmatter_parser.py` | Markdown → YAML | 🟢 |
| **Cognitive Debt Tracker** | `src/pipeline/cognitive_debt_tracker.py` | Mede débito cognitivo de tópicos | 🟡 |
| **Knowledge Telemetry** | `src/pipeline/knowledge_telemetry.py` | Métricas de aquisição | 🟡 |
| **Daily Consolidator** | `src/pipeline/daily_consolidator.py` | Consolida métricas do dia | 🟡 |
| **Analytics Emitter** | `src/pipeline/analytics_emitter.py` | Emite snapshots para BI | 🟡 |
| **Router (SQL/Vector)** | `src/pipeline/router.py` + `unified_router.py` | Decide onde armazenar/consultar | 🟡 |
| **Schema Registry** | `src/pipeline/schema_registry.py` | Gera contratos YAML a partir de Pydantic | 🟢 |
| **Sync Orchestrator** | `src/pipeline/sync_orchestrator.py` | Coordena 3 vias (Obs→SQL, SQL→TW, TW→SQL) | 🟡 |
| **TW Sync Adapter** | `src/pipeline/tw_sync.py` + `tw_sync_adapter.py` | Wrappers de TW (TaskWarrior via tasklib) | 🟢 |
| **Roadmap Sync Ingest** | `src/pipeline/roadmap_sync_ingest.py` | Ingere roadmap → TW | 🟡 |
| **Gap Engine** | `src/pipeline/gap_engine.py` | Detecta gaps de execução | 🟡 |
| **Study Manager** | `src/pipeline/study_manager.py` | Coordena sessões de estudo | 🟡 |
| **Code Review Sync** | `src/pipeline/code_review_sync.py` | Conecta commits a tasks (Git Dash do SPEC-05) | 🟡 |
| **Roadmap Sync contract** | `src/contracts/roadmap_sync_v1.py` | Schema Python do sync roadmap | 🟢 |
| **Sync Contract v1** | `src/contracts/sync_contract_v1.py` | Schema Python do contrato de sync | 🟢 |
| **AI Harnesses** | `src/pipeline/harness_epistemic.py` + `harness_metrics.py` | Prompts para priorização epistêmica + extração de métricas | 🟡 |
| **Obsidian Parser (integration)** | `src/integration/obsidian_parser.py` | Parser alternativo Obsidian | 🟡 |
| **Semantic Engine (integration)** | `src/integration/semantic_engine.py` | Engine semântico auxiliar | 🟡 |
| **Embeddings Provider** | `src/embeddings/provider.py` + `config.py` | Pluggable: OpenAI / local sentence-transformers / hash-mock | 🟢 |
| **Chats de design (referência histórica)** | `vibe-ops/base/chat-Sistema Prático de Aprendizado Cibernético.txt` + `chat-Produtividade Algorítmica Visual.txt` | Chats de design que originaram os modelos | 🟢 Histórico |

### 3.4 TIER 3 — Armazenamento, Schemas, Contratos, Modelos

| Sistema | Arquivo(s) | Propósito | Status |
|---|---|---|---|
| **Schema SQLite (DDL)** | `src/storage/schema.sql` (243 linhas) | Tabelas: temporal_waves/cycles/phases, study_plans/topics/materials/sessions, dev_projects/roadmaps/backlogs/changelogs, habits/habit_states, policy_decisions, planning_entities, roadmap_sync | 🟢 |
| **SQLite Adapter** | `src/storage/sqlite_adapter.py` + `sqlite_store.py` | Camada de acesso SQLite | 🟢 |
| **ChromaDB Adapter** | `src/storage/chroma_adapter.py` | Vector store com fallback mock | 🟢 |
| **sqlite-vec Integration** | `src/storage/sqlite_vec_integration.py` | Vetores em SQLite (com fallback NumPy) | 🟢 |
| **Vector Store** | `src/storage/vector_store.py` | Wrapper de vector store | 🟡 |
| **UEID Manager** | `src/storage/ueid.py` (18 linhas) | `<cluster>:<entity>:<id>` (ex. `study:topic:st_python_01`) | 🟢 |
| **SQLAlchemy ORM 2.0** | `src/storage/orm.py` + `metadata_orm.py` | ORM declarativo | 🟢 |
| **Data Mesh Adapter** | `src/storage/data_mesh_adapter.py` | Adaptador genérico mesh | 🟡 |
| **Schema Registry YAML** | `src/contracts/registry.yaml` (136 linhas) | 5 domínios × products × versions; planning v1 ativo, demais `draft` | 🟡 |
| **Planning Contract v1** | `src/contracts/planning.v1.yaml` (258 linhas) | 11 entity_types (wave/cycle/phase/project/habit/study_*/backlog_task/review_event/policy_decision) + cross-entity FK rules | 🟢 |
| **Migrations SQL** | `vibe-ops/migrations/001_create_dev_cluster_tables.sql` + `002_roadmap_sync_v1.sql` + `003_epistemic_priority_view.sql` + `versions/` | DDL versionado | 🟢 |
| **Pydantic v2 Schemas** | `src/schemas/pydantic_v2.py` (PolicyState/PolicyDecision/QHEMetrics/TaskPayload/StudyPlanEntity) + `registry.py` | Modelos core | 🟢 |
| **Models: temporal** | `src/models/temporal_entities.py` | Wave/Cycle/Phase | 🟢 |
| **Models: study** | `src/models/study_entities.py` | StudyProject/Topic/Material/Session | 🟢 |
| **Models: project (dev)** | `src/models/project_entities.py` | DevProject/Roadmap/Backlog/Changelog | 🟢 |
| **Models: habit** | `src/models/habit_entities.py` | Habit/HabitState com `H(t)=1−e^(−λt)` | 🟡 entidades ok; sem engine |
| **Models: policy** | `src/models/policy_entities.py` | PolicyDecision/Record | 🟢 |
| **Models: RAG** | `src/models/rag_entities.py` | IndexEntity, ChunkEntity | 🟢 |
| **Models: ikigai** | `src/models/ikigai_entities.py` | IKIGAiVector/Profile/Skill/Opportunity | 🟢 |
| **Models: knowledge** | `src/models/knowledge_entities.py` | Knowledge tree nodes | 🟢 |
| **Models: feedback** | `src/models/feedback_entities.py` | Review events | 🟢 |
| **Models: contracts (engine)** | `src/models/contracts.py` | Engine de contratos | 🟢 |
| **Models: contracts (pipeline)** | `src/contracts.py` | Contratos entre módulos pipeline | 🟢 |
| **Models: doc** | `src/models/doc_entities.py` | Documentos/registro | 🟡 |
| **Models: metric** | `src/models/metric_entities.py` | Métricas | 🟡 |
| **Models: health** | `src/models/health_entities.py` | Saúde/fadiga | 🟡 |
| **Models: operational** | `src/models/operational_entities.py` | Operação | 🟡 |
| **Parsers (markdown/frontmatter)** | `src/parsers/` (presume existir) | Markdown frontmatter | 🟡 |
| **Migrations versions** | `vibe-ops/migrations/versions/` | Versionamento Alembic-like | 🟡 |
| **Verify Mesh (sanity check)** | `verify_mesh.py` + `verify_mesh_v2.py` (root) | Import sanity check de ORM models | 🟢 |

### 3.5 TIER 4 — Execução (Downstream Tools)

| Sistema | Arquivo(s) | Propósito | Status |
|---|---|---|---|
| **Taskwarrior config** | `taskwarrior/config/taskrc.template` + `taskwarrior/config/hooks/on-exit` | `.taskrc` para TW | 🟢 |
| **Taskwarrior scripts** | `taskwarrior/scripts/task_aliases.sh` + `daily-review.sh` + `weekly-review.sh` + `calculate-metrics.py` + `working-days.py` + `backup-and-recur.sh` + `generate-working-recur.sh` + `on-add.sh` | Scripts consumidos pelo `centrals/task.py` | 🟢 |
| **Taskwarrior help** | `taskwarrior/help/` (00–12) + `main-help.ps1` + `main-help.sh` + `format-markdown.*` + `CROSS_PLATFORM_HELP_GUIDE.md` | Sistema de help custom | 🟢 |
| **Taskwarrior docs** | `taskwarrior/docs/TASKWARRIOR_*.md` + `VANILLA_USAGE_GUIDE.md` | Setup, howto, cheatsheet, workflows, pitfalls | 🟢 |
| **Taskwarrior PowerShell** | `taskwarrior/pwsh/task-aliases.ps1` | Aliases para Windows | 🟢 |
| **Taskwarrior SPEC** | `taskwarrior/SPEC.md` | Documento de propósito e escopo | 🟢 |
| **life-tatics CLI (standalone)** | `life-ops/life_tatics/cli.py` (54 linhas) | `life-tatics block start|stop`, `screentime dev|rest` | 🟢 |
| **life-tatics domain** | `life-ops/life_tatics/domain/time_blocks.py` (14 linhas) + `domain/screentime.py` | Lógica de time blocks + screentime | 🟢 (mas stub: retorna dict literal) |
| **life-tatics SPEC** | `life-ops/SPEC.md` | Documento de contrato do submodule | 🟢 |
| **life-tatics README** | `life-ops/README.md` | Quickstart | 🟢 |
| **life-tatics planner docs** | `life-ops/planner/{Points_of_premisses, SCALAR_DECOMPOSITION, time-lenghts_reviews}.md` | Modelos matemáticos | 🟢 |
| **Rust TUI (ratatui)** | `vibe-ops/vibeops-tui/Cargo.toml` + `src/main.rs` + `src/persistence.rs` | Dashboard live de policy/ikigai | 🟢 |
| **PowerShell launcher** | `vibe-ops/run_loop.ps1` (referenciado) | Launcher Windows para daily loop | 🟢 |

### 3.6 Specs & PRDs (consolidados em `vibe-ops/specs/`)

| Spec | Arquivo | Cobre |
|---|---|---|
| **PRD Temporal Engine** | `specs/prd-temporal-engine.md` | WAVE/CYCLE/PHASE |
| **PRD Habit Tracker** | `specs/prd-habit-tracker.md` | H(t) curves, streaks, infractions |
| **PRD Study Backlog** | `specs/prd-study-backlog.md` | StudyProject/Topic/Material/Session |
| **PRD Project Execution** | `specs/prd-project-execution.md` | DevRoadmap/Backlog/Changelog |
| **PRD Metrics & Health** | `specs/prd-metrics-health.md` | QHE, C_comp, métricas |
| **PRD Policy & Governance** | `specs/prd-policy-governance.md` | PolicyState, 4-state machine |
| **PRD IKIGAi Vectors** | `specs/prd-ikigai-vectors.md` | 4-vec passion/skill/market/revenue |
| **Schema Frontmatter v1** | `specs/schema-frontmatter-contract.md` | Markdown frontmatter schema |
| **Schema Frontmatter v2** | `specs/schema-frontmatter-contract-v2.md` | Evolução do schema v1 |
| **Schema Pydantic v1** | `specs/schema-pydantic-models.md` | Pydantic models v1 |
| **Schema Pydantic v2** | `specs/schema-pydantic-models-v2.md` | Pydantic v2 com type adapters |
| **Schema Planner Extension** | `specs/schema-planner-extension.md` | Extensões para o planner |
| **SPEC-05 Cybernetic Epistemic Mesh** | `specs/SPEC-05-cybernetic-epistemic-mesh.md` | Hybrid RAG topology, feedback loop, UEID |
| **Conceptual Arch Diagram** | `specs/concept_sys-archy.drawio` (e `.bkp`) | Diagrama editável de arquitetura | 🟡 DrawIO (binário) |
| **SPECs Index (legacy)** | `specs/README.md` | Sumário das specs | 🟢 |

### 3.7 Docs Estratégicos (Data-Mesh Vision)

| Doc | Arquivo | Cobre |
|---|---|---|
| **Data-Mesh Strategy** | `vibe-ops/doc/01-data-mesh-strategy.md` | Visão macro: Upstream (planning) vs Downstream (TW) |
| **Data Contracts & Pipelines** | `vibe-ops/doc/01.5-data-contracts-and-pipelines.md` (328 linhas) | Compilador de backlog, API Push, "Vetor em Fractais" |
| **Taskwarrior Factory Reset** | `vibe-ops/doc/02-tw-factory-reset.md` | Rollback metodológico ao vanilla TW |
| **Data-Mesh Enrichment** | `vibe-ops/doc/03-data-mesh-enrichment.md` (486 linhas) | Upstream/Downstream, frontmatter contracts, IKIGAi × mesh |
| **TW Vanilla Limits** | `doc/tw-vanilla_limits_analysis.md` | Análise de limitações do TW vanilla | 🟢 |
| **Soluções Extensões TW** | `doc/solucoes_extensoes_tw.md` | Workarounds para limites | 🟢 |
| **Doc Images** | `doc/image/` (refs em 01.5) | Screenshots de burndown, calendar, timew chart | 🟢 |

### 3.8 Testes (oficiais + scratch)

| Teste | Arquivo | Cobertura |
|---|---|---|
| **MVL Orchestrator test** | `vibe-ops/tests/test_mvl_orchestrator.py` (71 linhas) | State machine ingest-enrich-persist com SQLite in-memory + Chroma mock |
| **Knowledge Telemetry test** | `vibe-ops/tests/test_knowledge_telemetry.py` | Knowledge tree + debt |
| **Scratch tests** | `vibe-ops/scratch/test_*.py` | Exploratórios (NÃO oficiais) | 🟡 |

### 3.9 Raiz & Misc

| Arquivo | Propósito |
|---|---|
| `verify_mesh.py` + `verify_mesh_v2.py` | Sanity check dos models ORM |
| `vibe_ops.db` (binário, repo) | DB SQLite local pré-populada |
| `time-tasker/` | DUPLICATE snapshot — **não canônico** (ver `AGENTS.md` §2) |
| `logs/` | Runtime logs |

---

## 4. ÍNDICE DE SPECS POR FACETA

Para cada pergunta operacional, esta seção aponta o arquivo exato que responde.

### 4.1 "Onde está a definição do que é um Sonho/Objetivo/Meta/Tarefa?"

- `strategics/Modelagem Operacional.md` (pirâmide de 4 níveis, dual-frame)
- `strategics/Hierarquia de Objetivos.md` (templates de revisão)
- `strategics/Integracao_Tatica.md` (organização em níveis)
- `vibe-ops/doc/03-data-mesh-enrichment.md` §2.1 (Frontmatter por nível)
- `vibe-ops/contracts/planning.v1.yaml` (entity_types formais)

### 4.2 "Como funciona o loop Target-Sensor-Adjuster?"

- `vibe-ops/base/IKIGAi.md` §Hypervisor
- `vibe-ops/src/cybernetics/daily_loop.py` (orquestrador)
- `vibe-ops/src/pipeline/policy_engine.py` (Adjuster)
- `vibe-ops/src/cybernetics/engine.py` (GapSearchEngine, BinaryKnowledgeTree)
- `vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md` §3 (Target/Sensor/Actuator)

### 4.3 "Como Taskwarrior se conecta ao Planning?"

- `vibe-ops/doc/01-data-mesh-strategy.md` (Upstream vs Downstream)
- `vibe-ops/doc/01.5-data-contracts-and-pipelines.md` (API Push, UDA enxuta)
- `vibe-ops/doc/03-data-mesh-enrichment.md` §1.2 (Reverse Sync)
- `vibe-ops/src/middleware/sync_engine.py` (código)
- `vibe-ops/src/pipeline/roadmap_sync_ingest.py` (ingest de roadmap)
- `vibe-ops/src/contracts/roadmap_sync_v1.py` (contrato)
- `vibe-ops/migrations/002_roadmap_sync_v1.sql` (DDL)

### 4.4 "Como o RAG híbrido (SQL + Vector + Graph) funciona?"

- `vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md` §2 (3-index strategy)
- `vibe-ops/src/pipeline/rag_indexer.py` (código)
- `vibe-ops/src/storage/{sqlite_vec_integration, chroma_adapter, vector_store}.py` (storages)
- `vibe-ops/src/models/rag_entities.py` (modelos)

### 4.5 "O que é o UEID e por que existe?"

- `vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md` §4
- `vibe-ops/src/storage/ueid.py` (código, 18 linhas)
- Formato: `<CLUSTER>:<ENTITY>:<ID>` — ex. `study:topic:st_python_01`, `dev:proj:proj_vibe_01`, `task:tw:81d33ec8`

### 4.6 "Como os modelos matemáticos do Hypervisor se definem?"

- `vibe-ops/base/IKIGAi.md` §Hypervisor (PID Controller, η, vetor Ikigai)
- `vibe-ops/base/Produtividade Algorítmica Visual.md` (constantes, switch-cases, error handling)
- `vibe-ops/src/pipeline/policy_engine.py` (PolicyMap, severidade, histerese)
- `life-ops/planner/time-lenghts_reviews.md` (constantes: WORK_RATIO=0.7333, WAVE=15d, CYCLE=45d, PHASE=180d)
- `life-ops/planner/SCALAR_DECOMPOSITION_BACKLOG.md` (27 modelos, ex. MODEL-001 a MODEL-027)
- `life-ops/planner/Points_of_premisses-task-habits.md` (operadores de revisão R_n)

### 4.7 "Como o sistema detecta gaps cognitivos e de execução?"

- `vibe-ops/src/cybernetics/engine.py` (BinaryKnowledgeTree, GapSearchEngine)
- `vibe-ops/src/pipeline/gap_engine.py` (engine alternativa)
- `vibe-ops/src/main.py` comando `gaps`
- `vibe-ops/src/vibe_cli.py` comando `gaps` (versão avançada)

### 4.8 "Como o Habit Tracker funciona matematicamente?"

- `vibe-ops/specs/prd-habit-tracker.md` (PRD)
- `vibe-ops/src/models/habit_entities.py` (modelos)
- `life-ops/planner/Points_of_premisses-task-habits.md` §2-3 (Q_HE, H(t)=1−e^(−λt))
- `vibe-ops/src/storage/schema.sql` (tabela habit_states)
- **GAP:** `src/pipeline/habit_engine.py` (referenciado no SCALAR_DECOMPOSITION §1 mas não existe)

### 4.9 "Como funciona o TUI Rust?"

- `vibe-ops/vibeops-tui/Cargo.toml` (deps: ratatui, crossterm, rusqlite)
- `vibe-ops/vibeops-tui/src/main.rs` (loop + UI)
- `vibe-ops/vibeops-tui/src/persistence.rs` (SQLite read)
- Lê `../vibe_ops.db` (sibling do executável)

### 4.10 "Como o life CLI delega para sub-módulos?"

- `cli/cli.py` (registra centrals, handlers, plugins)
- `centrals/base.py` (`BaseCentral.run_cli(cwd, module, args, json_out)`)
- `cli/test_runner.py` (descobre `tests/` em submodules)
- `cli/config.py` (resolução de paths de submodules)

### 4.11 "Como o plugin system funciona?"

- `plugins/protocol.py` (interface)
- `plugins/loader.py` (descoberta)
- `plugins/builtin/health_check.py` (exemplo)
- `cli/cli.py` (registro automático via `register_plugins(app)`)
- **GAP:** hooks de lifecycle (`before_daily`, `after_daily`, etc.) não são chamados

### 4.12 "Como o time-block / screentime do life-tatics se conecta ao resto?"

- `life-ops/life_tatics/cli.py` (entry point)
- `life-ops/life_tatics/domain/time_blocks.py` (lógica)
- `life-ops/life_tatics/domain/screentime.py` (lógica)
- `life-ops/SPEC.md` (contrato)
- **GAP:** nenhuma ponte explícita com TW ou `vibe_ops.db` ainda

### 4.13 "Como a triagem de tarefas órfãs funciona?"

- `vibe-ops/doc/03-data-mesh-enrichment.md` §6 (Pipeline de Triagem)
- `vibe-ops/src/middleware/sync_engine.py` (stat counter `triaged`)
- **GAP:** geração efetiva de `triagem.md` não verificada no código atual

### 4.14 "Como o sistema de revisão IKIGAi fecha o loop com feedback?"

- `vibe-ops/doc/03-data-mesh-enrichment.md` §3 (cálculo ROI IKIGAi multi-dimensional)
- `vibe-ops/doc/03-data-mesh-enrichment.md` §4 (Hypervisor como consumidor do mesh)
- `vibe-ops/src/pipeline/ikigai_scorer.py` (código, **GAP:** vetores errados)
- `vibe-ops/src/models/ikigai_entities.py` (entidades formais)
- `vibe-ops/src/contracts/registry.yaml` (domínio `ikigai` ainda em `draft`)

---

## 5. CONTRATOS DE DADOS ATIVOS

Esta seção lista **o que é compartilhado entre sistemas** (essência do Data-Mesh) e onde está definido.

### 5.1 Contratos core (vivo, validado)

| Contrato | Arquivo | Tipos/Entidades | Status |
|---|---|---|---|
| **Planning Entities v1** | `vibe-ops/src/contracts/planning.v1.yaml` | wave, cycle, phase, project, habit, study_material, study_topic, study_session, backlog_task, review_event, policy_decision | 🟢 active |
| **Schema Registry v1.0.0** | `vibe-ops/src/contracts/registry.yaml` | 5 domínios (planning/execution/temporal/analytics/ikigai/study/finance) × products × versions | 🟡 (apenas `planning.entities.v1` active; demais `draft`) |
| **SyncContractV1 (Python)** | `vibe-ops/src/contracts/sync_contract_v1.py` | Payload entre SyncEngine ↔ TW | 🟢 |
| **RoadmapSyncV1 (Python)** | `vibe-ops/src/contracts/roadmap_sync_v1.py` | Schema roadmap → TW | 🟢 |
| **Planning Pydantic v2** | `vibe-ops/src/schemas/pydantic_v2.py` | PolicyState, PolicyDecision, QHEMetrics, TaskPayload, StudyPlanEntity | 🟢 |
| **Schema Registry (engine)** | `vibe-ops/src/schemas/registry.py` + `vibe-ops/src/pipeline/schema_registry.py` | Gera YAMLs a partir de Pydantic (round-trip) | 🟢 |
| **Storage Schema (DDL)** | `vibe-ops/src/storage/schema.sql` (243 linhas) | 15+ tabelas (temporal/study/dev/habit/policy/planning/roadmap_sync) | 🟢 |
| **Migrations** | `vibe-ops/migrations/001/002/003*.sql` | DDL versionado + views (epistemic_priority, dashboard_study_dev) | 🟢 |

### 5.2 UEID — Unified Entity ID (middleware pattern)

| Aspecto | Detalhe |
|---|---|
| Formato | `<CLUSTER>:<ENTITY>:<ID>` |
| Exemplos | `study:topic:st_python_01`, `dev:proj:proj_vibe_01`, `task:tw:81d33ec8` |
| Onde | `vibe-ops/src/storage/ueid.py` (18 linhas) |
| Quem gera | `vibe-ops/src/middleware/sync_engine.py::compute_upstream_id()` (12-char SHA-256 prefix) |
| Quem usa | `SyncEngine` (upstream_id), `RAG entities` (chunk keys), todos os models Pydantic |

### 5.3 Idempotência de Push (Sync)

| Aspecto | Detalhe |
|---|---|
| Chave | `upstream_id` (12-char SHA-256) |
| Tabela | `planning_entities` (SQLite) |
| Padrão | `INSERT ... ON CONFLICT(id, entity_type) DO UPDATE WHERE excluded.upstream_id != planning_entities.upstream_id` |
| Skip se | hash inalterado (idempotente) |
| Onde | `vibe-ops/src/middleware/sync_engine.py` (linhas 26-60) |

### 5.4 Source-of-Truth Boundaries (regra do Data-Mesh)

| Camada | É source-of-truth para… | NÃO é source-of-truth para… |
|---|---|---|
| **Markdown (Obsidian)** | Metadados, nomenclatura, hierarquia de sonhos/objetivos | Status de execução, time logs |
| **Taskwarrior (.task)** | Status binário (pending/done), timestamps, duration | Nomenclatura de projetos, hierarquia semântica |
| **Timewarrior (.timew)** | Time logs (séries temporais) | Status de tasks, metadados |
| **SQLite (vibe_ops.db)** | Snapshots analíticos, joins cross-domain, métricas consolidadas | Decisões de execução em tempo real (TW é mais rápido) |
| **Policy Decisions (SQLite)** | Setpoints (PUSH/MAINTAIN/REDUCE/RECOVER), budget, alertas | Razões qualitativas (ficam no chat/obsidian) |

---

## 6. ESTADO DE IMPLEMENTAÇÃO (por sistema)

Legenda: 🟢 vivo + exercitado · 🟡 vivo mas parcial · 🔴 planejado / stub

| Categoria | Sistema | Spec? | Código? | Notas |
|---|---|---|---|---|
| **Config** | `life` CLI loader | 🟢 | 🟢 | `cli/config.py` |
| **Config** | `life` config YAML | 🔴 | 🔴 | Nenhum `config/life.yaml` no repo |
| **Orquestração** | daily/weekly handlers | 🟢 | 🟢 | `handlers/daily.py`, `weekly.py` |
| **Orquestração** | Centrals (task/finance/knowledge/research) | 🟢 | 🟡 | Wrappers prontos; sub-módulos `fin_ops/leitura/mindmaps/notes/research` não existem neste repo |
| **Orquestração** | Plugin lifecycle hooks | 🟢 | 🔴 | Declarados em `plugins/protocol.py`; nunca invocados |
| **Orquestração** | Plugin discovery | 🟢 | 🟢 | `plugins/loader.py` |
| **Orquestração** | health_check built-in | 🟢 | 🟢 | `plugins/builtin/health_check.py` |
| **Cybernetic** | PolicyEngine (Adjuster) | 🟢 | 🟢 | 4-state machine com histerese |
| **Cybernetic** | CyberneticDailyLoop | 🟢 | 🟢 | `cybernetics/daily_loop.py` orquestra tudo |
| **Cybernetic** | BinaryKnowledgeTree | 🟢 | 🟢 | `cybernetics/engine.py` |
| **Cybernetic** | GapSearchEngine | 🟢 | 🟢 | Execution debt 72h |
| **Cybernetic** | Habit Engine (H(t), Q_HE) | 🟢 | 🔴 | MODEL-001..027 existem no `SCALAR_DECOMPOSITION` mas `pipeline/habit_engine.py` não |
| **Sync (Upstream)** | Frontmatter parser | 🟢 | 🟢 | `pipeline/frontmatter_parser.py` + `integration/obsidian_parser.py` |
| **Sync (Upstream)** | Vault traversal completo | 🟢 | 🟡 | `sync_engine.py:30` hardcoded `folder="2_projeto"` |
| **Sync (Upstream)** | Ingestion idempotente | 🟢 | 🟢 | `INSERT ON CONFLICT WHERE hash != hash` |
| **Sync (Sideways)** | SQLite ↔ Taskwarrior (push) | 🟢 | 🟢 | `sync_sqlite_to_taskwarrior` em `sync_engine.py` |
| **Sync (Downstream)** | Reverse Sync TW→SQLite | 🟢 | 🟡 | `pipeline/reverse_sync.py`; `triagem` stat existe, geração de `triagem.md` parcial |
| **Sync (Downstream)** | Triagem de órfãs | 🟢 | 🟡 | `project:INBOX` detector presente, proposta automática parcial |
| **RAG** | HybridRAGIndexer | 🟢 | 🟢 | `pipeline/rag_indexer.py` + `storage/{chroma_adapter, sqlite_vec_integration}.py` |
| **RAG** | Embedding provider (pluggable) | 🟢 | 🟢 | OpenAI / local SBERT / hash-mock |
| **RAG** | Vector store com fallback | 🟢 | 🟢 | ChromaDB → sqlite-vec → NumPy |
| **RAG** | Chunking strategy | 🟢 | 🟡 | `models/rag_entities.py` ok; chunker não profundo |
| **RAG** | Graph layer (Obsidian + Neo4j) | 🟢 | 🔴 | Apenas links markdown, sem Neo4j |
| **IKIGAi** | 4-vec `passion/skill/market/revenue` (spec) | 🟢 | 🔴 | `pipeline/ikigai_scorer.py` implementa 4-vec *diferente* (study/dev/health/global) — **RECONCILIAÇÃO NECESSÁRIA** |
| **IKIGAi** | IKIGAi Profile / Skill / Opportunity | 🟢 | 🟡 | `models/ikigai_entities.py` existe; não wired no scorer |
| **IKIGAi** | ROI multi-dimensional (R$ × horas) | 🟢 | 🔴 | Pseudocódigo em `doc/03 §3.2`; sem implementação |
| **Models (Pydantic)** | temporal, study, project, policy, ikigai, knowledge, RAG, feedback, contracts | 🟢 | 🟢 | 9 clusters sólidos |
| **Models (Pydantic)** | doc, metric, health, operational, habit | 🟢 | 🟡 | Existem mas pouco exercitados |
| **Storage** | SQLite schema + migrations | 🟢 | 🟢 | `schema.sql` + 3 migrations |
| **Storage** | UEID Manager | 🟢 | 🟢 | `storage/ueid.py` |
| **Storage** | DataMesh Adapter | 🟢 | 🟡 | Existe mas sem uso documentado |
| **Storage** | Vector store (sqlite-vec) | 🟢 | 🟢 | Com fallback NumPy |
| **Contracts (YAML)** | planning.v1 | 🟢 | 🟢 | Active |
| **Contracts (YAML)** | execution.v1, temporal.v1, analytics.v1, ikigai.v1, study.v1, finance.v1 | 🟡 | 🔴 | Todos `draft`, sem YAML publicado |
| **Timewarrior** | Time-tracking | 🟢 | 🟡 | `tasklib` para TW; `timew` referenciado mas sem adapter dedicado |
| **Timewarrior** | Tags → E(t) update | 🟢 | 🔴 | Planejado; nenhuma ponte TW→E(t) implementada |
| **TW Scripts** | daily-review.sh / weekly-review.sh / calculate-metrics.py / on-add.sh | 🟢 | 🟢 | Prontos, consumidos por `centrals/task.py` |
| **TW Scripts** | working-days.py | 🟢 | 🟢 | Cálculo de WORK_RATIO (0.7333) |
| **life-tatics** | block start/stop | 🟢 | 🟢 | `cli.py` + `domain/time_blocks.py` (stub, retorna dict) |
| **life-tatics** | screentime dev/rest | 🟢 | 🟢 | `domain/screentime.py` (stub) |
| **life-tatics** | routine morning/evening | 🟢 | 🔴 | Documentado em SPEC, não codificado |
| **life-tatics** | TW integration | 🟢 | 🔴 | Planejado (tw-api) |
| **TUI** | Rust + ratatui + 1Hz polling | 🟢 | 🟢 | `vibeops-tui/src/{main.rs, persistence.rs}` |
| **TUI** | Manual sync trigger | 🟢 | 🟢 | Implementado |
| **BI / Streamlit** | Dashboards ROI | 🟢 | 🔴 | Planejado em `doc/01.5 §4.3`; nenhum `.py` Streamlit |
| **Tests** | MVL orchestrator (pytest) | 🟢 | 🟢 | `tests/test_mvl_orchestrator.py` (in-memory SQLite, Chroma mock) |
| **Tests** | Knowledge telemetry | 🟢 | 🟢 | `tests/test_knowledge_telemetry.py` |
| **Tests** | Tests oficiais em outros tiers | 🔴 | 🔴 | Nenhum `tests/` em `life/`, `taskwarrior/`, `life-ops/`, `strategics/` |
| **Tests** | Integration tests do Sync end-to-end | 🔴 | 🔴 | Nenhum |

### 6.1 ⚠️ Risco de Design: discrepância IKIGAi vectors

| Onde | Vetores | Observação |
|---|---|---|
| `vibe-ops/base/IKIGAi.md` (spec) | `passion / skill / market / revenue` | Função objetivo motivacional (4 quadrantes Ikigai clássico) |
| `vibe-ops/specs/prd-ikigai-vectors.md` | `passion / skill / market / revenue` (com `revenue_impact_score`) | Confirma spec |
| `vibe-ops/src/pipeline/ikigai_scorer.py` (código) | `study / dev / health / global` | **4-vec operacional, não motivacional** |
| `vibe-ops/src/models/ikigai_entities.py` | `IKIGAiVector / Profile / Skill / Opportunity` | Não fixa o conjunto de vetores |
| `vibe-ops/doc/03 §3.2` (pseudocódigo) | `passion / skill / market / revenue` (com pesos 0.25 cada) | Pseudocódigo do ROI |

**Decisão recomendada:** reconciliar para usar `passion/skill/market/revenue` em ambos spec e código (com `study/dev/health` como *sub-dimensões* de `skill`). Caso contrário, todo cálculo de ROI IKIGAi (`doc/03 §3.2`) produzirá números sem sentido semântico.

### 6.2 ⚠️ Risco de Design: vault traversal hardcoded

`vibe-ops/src/middleware/sync_engine.py:30` — `folder: str = "2_projeto"` é hardcoded. O sistema não atravessa o vault inteiro; ignora arquivos em `1_wave/`, `3_review/`, `4_archive/`, etc.

**Decisão recomendada:** parametrizar via `LifeConfig` ou `PlanningNotes` frontmatter, e usar `glob("**/*.md")` com allowlist de folders via YAML config.

### 6.3 ⚠️ Risco de Design: paths de sub-módulos default não existem

`cli/config.py:23-29` define `DEFAULT_SUBMODULES` apontando para `fin_ops/`, `system/raise_data/`, `system/knowledge/`, etc. — **nenhum destes diretórios existe neste repo**. `get_submodule_path()` retorna `{"ok": False, "error": "..."}` silenciosamente.

**Decisão recomendada:** (a) tornar paths opcionais (None = não instalado), (b) documentar em `README` o que precisa existir para cada central funcionar, ou (c) mover defaults para `config/life.yaml` que ainda não existe.

---

## 7. LACUNAS DO DATA-MESH & MIDDLEWARES PROPOSTOS

Esta seção é o **núcleo deste documento**: identifica o que **falta** para que os sistemas conversem entre si de forma robusta, e propõe os **middlewares** que preencham essas lacunas.

### 7.1 O que está especificado mas não implementado

| Lacuna | Onde a spec vive | Middleware necessário |
|---|---|---|
| **Plano de Aksi → Story Points → TW cards** (downstream contract) | Implícito em `doc/01.5 §6` (Checklists Tipados) + `doc/03 §2.1` (Nível 4: Tarefa) | **`StoryPointDecomposer`** — converte `BacklogTask` (Markdown checklist) em cards TW com `size` (UDA) e `priority` calculados a partir de `revenue_impact` + `est effort` |
| **Dev-Logs estruturados** (commits → task) | `specs/SPEC-05 §6` (Feedback Evidence: "Commit linked to task exists (Git)") | **`CommitTaskLinker`** — middleware que parseia `git log` (local), identifica SHA-1→UEID via Conventional Commits (`feat(study:topic:st_python_01): ...`), persiste em `changelog_entries` |
| **Histerese robusta do Hypervisor** | `doc/03 §3.1` (matriz de decisão) + `Points_of_premisses §2` (operador R_n) | **`ReviewOperator`** — implementa $\mathcal{R}_n(\mathbf{s}_t)$ com renormalização de $\lambda, k$ |
| **Q_HE calculado de verdade** | `Points_of_premisses §3` (pesos w_sono=0.35, w_med=0.20, w_workout=0.25, w_lunch=0.10) | **`HabitEfficiencyOracle`** — calcula `Q_HE` a partir de `habit_states` + `study_sessions` + streak |
| **TW ad-hoc → Planning (triagem)** | `doc/03 §6` (Pipeline de Triagem completo) | **`OrphanTriageWriter`** — emite `triagem.md` com tabela e checkboxes; idempotente |
| **BI / Streamlit MVP** | `doc/01.5 §4.3` (declarado) + `doc/03 §3.3` (Dashboard IKIGAi ASCII) | **`StreamlitBI`** — 3 páginas: Burndown, IKIGAi balance, ROAS (horas × receita) |
| **Plugin lifecycle real** | `plugins/protocol.py:25-37` (hooks declarados) | **`HookDispatcher`** — `handlers/daily.py` e `weekly.py` chamam `plugin.before_daily(context)` antes de processar centrals; `after_daily` no fim |
| **Habit engine (H(t), E(t), P(t))** | `SCALAR_DECOMPOSITION §1` (MODEL-001..004) | **`HabitEngine`** — funções puras em `pipeline/habit_engine.py` (referenciado mas não existe) |
| **Finance integration (GnuCash/fin_ops)** | Implícito em `centrals/finance.py` (dispatch para fin_ops) | **`FinanceReverseSync`** — extrai ROI de `timew` (hours × $/hr setpoint) e injeta em `policy_decisions` como nova coluna `revenue_pro_hora` |
| **Timewarrior → Energy curve** | Implícito no SPEC-05 §3.2 ("Daily Journal: Energy Matrix") | **`TimewEnergyBridge`** — extrai tags `+phase:learn/earn/train` de TW, atualiza E(t) curve, persiste em `metrics` table |

### 7.2 Proposta de 8 middlewares (ordem de prioridade)

Para cada middleware: **o que faz**, **o que consome**, **o que produz**, **em que tier opera**.

#### M1. `StoryPointDecomposer` (P1 — crítico)
- **O que faz:** quebra `BacklogTask` (Markdown) em 1..N cards TW com `size` (UDA), `priority` (H/M/L → `urgency` polynomial boost), e `depends` intra-projeto
- **Consome:** `BacklogTask` (Markdown checklist com `size: 4h`) + `Project` (revenue_impact) + `Meta` (priority P1/P2)
- **Produz:** TW task com `project:obj_q3_seguranca.proj_alfa_01` + `size:4h` + `+priority_high` + `upstream_id:hashAlpha01`
- **Tier:** 2 (pipeline) + 3 (storage `roadmap_sync`) + 4 (TW binário)
- **Ref:** `vibe-ops/doc/01.5 §6-9`; `vibe-ops/src/contracts/roadmap_sync_v1.py` (já existe, falta o consumer)

#### M2. `CommitTaskLinker` (P1 — crítico, falta de "dev-logs")
- **O que faz:** parseia `git log` local, identifica SHA-1→UEID via Conventional Commits
- **Consome:** Conventional Commits (`feat(study:topic:st_python_01): ...`) ou trailer (`Task-UEID: dev:proj:proj_vibe_01`)
- **Produz:** rows em `changelog_entries` (já existe a tabela em `schema.sql`)
- **Tier:** 2 (pipeline) + 4 (git CLI)
- **Ref:** `vibe-ops/specs/SPEC-05 §6` (Feedback Evidence #2: "Commit linked to task exists")

#### M3. `HabitEngine` (P1 — base matemática)
- **O que faz:** implementa `H(t)`, `E(t)`, `P(t)`, `Q_HE`, `supercompensation`, `lambda_renormalization`
- **Consome:** `habit_states`, `study_sessions`, `metrics`
- **Produz:** scores normalizados consumidos por `PolicyEngine` e `IkigaiScorer`
- **Tier:** 2 (pipeline) — funções puras testáveis
- **Ref:** `life-ops/planner/SCALAR_DECOMPOSITION_BACKLOG.md §1` (MODEL-001 a MODEL-027); `vibe-ops/planner/Points_of_premisses-task-habits.md §2-3`

#### M4. `ReviewOperator` (P2 — calibração)
- **O que faz:** aplica $\mathcal{R}_n(\mathbf{s}_t)$ em `t ∈ {7, 15, 30, 45}` para renormalizar `λ`, `k`, vetor de estado
- **Consome:** `metrics` history, streak counters, `policy_decisions` history
- **Produz:** update de `lambda_rate` em `habits`, `k_coef` em `metrics`, novo `review_event` em `review_events`
- **Tier:** 2 (pipeline)
- **Ref:** `Points_of_premisses §2`

#### M5. `OrphanTriageWriter` (P2 — fechamento do loop)
- **O que faz:** toda noite, lê `task export project:INBOX upstream_id.none:`, gera `triagem.md` com tabela
- **Consome:** TW `export` filtrado
- **Produz:** `triagem.md` em vault, com checkboxes `[ ] Aprovar proj:S1.O2`
- **Tier:** 2 (pipeline) + 4 (TW) + 0 (vault write-back)
- **Ref:** `vibe-ops/doc/03 §6`; já há `stats["triaged"]` em `sync_engine.py` (stat pronto, ação não)

#### M6. `HookDispatcher` (P2 — extensibilidade)
- **O que faz:** `handlers/daily.py` e `weekly.py` ganham chamadas `plugin.before_daily(context)` / `after_daily`
- **Consome:** `context: dict` (results agregados de cada central)
- **Produz:** mutação de `context` antes/depois (plugins podem enriquecer/alerts)
- **Tier:** 1 (orquestração)
- **Ref:** `plugins/protocol.py:25-37`; nenhum caller

#### M7. `TimewEnergyBridge` (P3 — time→energy)
- **O que faz:** extrai tags de TW (`+phase:learn`, `+phase:earn`, `+phase:train`), cruza com `timew export`, atualiza curva E(t)
- **Consome:** `timew export` JSON + `tags` de TW
- **Produz:** rows em `metrics` com `phase:learn/earn/train` + `duration_minutes`
- **Tier:** 2 (pipeline) + 4 (TW + Timewarrior)
- **Ref:** `vibe-ops/base/IKIGAi.md §4` (PID Controller); `doc/01.5 §2.2` (Timewarrior Reports)

#### M8. `StreamlitBI` (P3 — observabilidade)
- **O que faz:** 3 dashboards (Burndown TW, IKIGAi balance, ROAS)
- **Consome:** `vibe_ops.db` (read-only), `timew export`
- **Produz:** visualização em `localhost:8501`
- **Tier:** 3 (read-only)
- **Ref:** `vibe-ops/doc/01.5 §4.3`; `vibe-ops/doc/03 §3.3`

### 7.3 Middlewares existentes (consolidação)

Para clareza, os middlewares que **já existem** mas estão espalhados:

| Middleware | Arquivo | Estado |
|---|---|---|
| `SyncEngine` (master) | `vibe-ops/src/middleware/sync_engine.py` | 🟢 138 linhas, idempotente |
| `MVL Orchestrator` | `vibe-ops/src/pipeline/mvl_orchestrator.py` | 🟢 state machine |
| `Sync Orchestrator` | `vibe-ops/src/pipeline/sync_orchestrator.py` | 🟡 |
| `TW Sync Adapter` | `vibe-ops/src/pipeline/tw_sync*.py` | 🟢 |
| `Roadmap Sync Ingest` | `vibe-ops/src/pipeline/roadmap_sync_ingest.py` | 🟡 |
| `Enrichment Engine` | `vibe-ops/src/pipeline/enrichment*.py` | 🟡 |
| `FK Resolver` | `vibe-ops/src/pipeline/fk_resolver.py` | 🟡 |
| `Schema Registry` | `vibe-ops/src/pipeline/schema_registry.py` | 🟢 |
| `Code Review Sync` | `vibe-ops/src/pipeline/code_review_sync.py` | 🟡 (sem consumer claro) |
| `AI Harness: Epistemic` | `vibe-ops/src/pipeline/harness_epistemic.py` | 🟡 |
| `AI Harness: Metrics` | `vibe-ops/src/pipeline/harness_metrics.py` | 🟡 |

---

## 8. GLOSSÁRIO DE ACRÔNIMOS

| Sigla | Significado | Onde aparece |
|---|---|---|
| **PAE** | Plano Anual Estratégico | `strategics/Planejamento (Estratégico e Tático).md` |
| **TW** | Taskwarrior | `taskwarrior/`, `vibe-ops/doc/*`, `centrals/task.py` |
| **TW API** | tasklib (Python wrapper) | `vibe-ops/src/middleware/sync_engine.py:4` |
| **QHE** | Quociente Hábito-Eficiência | `Points_of_premisses §3`; `schemas/pydantic_v2.py` (QHE Metrics) |
| **C_comp** | Cognitive Complexity / Completion | `policy_engine.py`; `schema.sql` (`c_comp` column) |
| **CLR** | Cognitive Load Ratio | SPEC-05; referenciado em `policies` |
| **IC** | (vide schema.sql) | Provavelmente *Information Coefficient* ou *Implementation Coverage* |
| **UEID** | Unified Entity ID (`cluster:entity:id`) | `storage/ueid.py`; SPEC-05 §4 |
| **RICE** | Reach/Impact/Confidence/Effort | `vibe-ops/base/Planning_notes.md` (frameworks de priorização) |
| **ICE** | Impact/Confidence/Ease | `vibe-ops/base/Planning_notes.md` |
| **MoSCoW** | Must/Should/Could/Won't | `vibe-ops/base/Planning_notes.md` |
| **MVL** | Minimum Viable Loop | `vibe-ops/src/pipeline/mvl_orchestrator.py` |
| **RAG** | Retrieval-Augmented Generation | `vibe-ops/specs/SPEC-05 §2` |
| **MDP** | Markov Decision Process | `life-ops/planner/SCALAR_DECOMPOSITION` |
| **TSDB** | Time Series Database | `vibe-ops/doc/01.5 §4.3` (Timewarrior) |
| **ETL** | Extract/Transform/Load | `vibe-ops/doc/01.5 §4.1` |
| **ROI** | Return on Investment | `vibe-ops/doc/03 §3.2` (ROI IKIGAi) |
| **ROAS** | Return on Ad Spend (análogo: tempo investido) | Generalizado para horas investidas |
| **IDM** | IKIGAi Decision-Making | (uso informal) |
| **SENAI** | Serviço Nacional de Aprendizagem Industrial (curso ADS do Matheus) | `vibe-ops/base/IKIGAi.md` (linha 165) |
| **INBOX** | TW project órfão (placeholder) | `vibe-ops/doc/03 §6` |
| **Fractal Vector** | "Vetor em Fractais" — propagação exponencial de uma mudança local | `vibe-ops/doc/01.5 §2.3` |
| **FK** | Foreign Key | `vibe-ops/src/contracts/planning.v1.yaml` |
| **UDA** | User Defined Attribute (TW) | `vibe-ops/doc/01.5 §5` |
| **PMBOK / RICE / ICE / Eisenhower** | Frameworks de priorização | `vibe-ops/base/Planning_notes.md` |
| **WORK_RATIO** | 22/30 ≈ 0.7333 (dias úteis / dias corridos) | `life-ops/planner/time-lenghts_reviews.md §1.2` |
| **λ (lambda)** | Taxa de aprendizado (curva H(t)) | `Points_of_premisses §2` |
| **k** | Coeficiente de fadiga (curva E(t)) | `Points_of_premisses §2` |
| **$\mathcal{R}_n$** | Operador de revisão espaçada | `Points_of_premisses §2` |
| **sonho/obj/meta** | Sonho (6-12m) / Objetivo (3m) / Meta (15d) | `strategics/Modelagem Operacional.md` |
| **wave/cycle/phase** | Onda (15d) / Ciclo (45d) / Fase (180d) | `vibe-ops/storage/schema.sql` (`temporal_waves/cycles/phases`) |

---

## 9. ROADMAP DE MIDDLEWARES (próximos passos)

Ordem recomendada de implementação (impacto decrescente + dependências resolvidas).

### Sprint 1 — Fechar lacunas P1 (1-2 semanas)

- [ ] **M3. `HabitEngine`** — criar `vibe-ops/src/pipeline/habit_engine.py` com `habit_formation(t, λ)`, `energy_curve(t, k)`, `performance(t, k, λ, R)`, `supercomp_energy(...)`, `calculate_qhe(habits, energy_ratio, streak)`. Testes unitários em `tests/test_habit_engine.py`.
- [ ] **M1. `StoryPointDecomposer`** — implementar quebra de `BacklogTask` em TW com `size`/`priority`/`upstream_id`. Consome `vibe-ops/src/contracts/roadmap_sync_v1.py` (já existe).
- [ ] **M2. `CommitTaskLinker`** — middleware git→SQLite, preenche `changelog_entries` (tabela já existe em `schema.sql`).
- [ ] **§6.1 Reconciliar IKIGAi vectors** — decidir entre `passion/skill/market/revenue` (spec) e `study/dev/health/global` (código), ou criar mapeamento explícito. Atualizar `pipeline/ikigai_scorer.py` + `models/ikigai_entities.py`.

### Sprint 2 — Fechar lacunas P2 (1-2 semanas)

- [ ] **M4. `ReviewOperator`** — implementar $\mathcal{R}_n(\mathbf{s}_t)$; persistir renormalizações em `metrics`/`habit_states`.
- [ ] **M5. `OrphanTriageWriter`** — emitir `triagem.md` noturno; revisar nightly cron.
- [ ] **M6. `HookDispatcher`** — `handlers/daily.py` ganha 4 chamadas (before/after × daily/weekly).
- [ ] **§6.2 Vault traversal paramétrico** — `sync_engine.py` aceita lista de folders via config.
- [ ] **§6.3 Paths opcionais para sub-módulos** — `get_submodule_path()` retorna `None` em vez de path inexistente; centrals exibem "módulo não instalado".

### Sprint 3 — Lacunas P3 + Observabilidade (2-3 semanas)

- [ ] **M7. `TimewEnergyBridge`** — extrair tags TW + `timew`; persistir em `metrics` com `phase:*`.
- [ ] **M8. `StreamlitBI`** — MVP de 3 páginas (Burndown, IKIGAi, ROAS).
- [ ] **Tests oficiais em outros tiers** — criar `tests/` em `life-ops/`, `taskwarrior/`, `life/`.
- [ ] **Integration test do Sync end-to-end** — fixture: vault sintético → Sync → TW (com TW mock) → Reverse → assert planning_entities == input.

### Sprint 4 — Extensões de Longo Prazo

- [ ] **Neo4j graph layer** para SPEC-05 §2.3 (Topic→Prerequisite)
- [ ] **Migrations Alembic-style** completas (`vibe-ops/migrations/versions/`)
- [ ] **Contracts execution/temporal/analytics/ikigai/study/finance** movidos de `draft` para `active`
- [ ] **Plano de Segurança** — vault encryption-at-rest, Timewarrior hooks auditáveis

---

## 10. NOTAS FINAIS & APÊNDICE

### 10.1 Política Append-Only (vibe-ops/)

Conforme `AGENTS.md §6.1`, este documento respeita a regra: **nada foi deletado em `vibe-ops/`**. Todos os arquivos referenciados continuam onde estavam antes desta varredura. Este `SYSTEMS_TOPOLOGY.md` vive no **root** (não em `vibe-ops/`), então não viola a regra.

### 10.2 Como adicionar um novo sistema a este índice

1. Adicione a entrada na tabela apropriada em §3.
2. Se for um middleware novo, adicione a §7 com a tupla: O que faz / Consome / Produz / Tier / Ref.
3. Se mudar contratos, atualize §5.
4. Não remova entradas — adicione nota `(deprecated)` se aplicável.

### 10.3 Como auditar lacunas

```bash
# Specs sem implementação de código correspondente:
ls vibe-ops/specs/*.md | while read spec; do
  base=$(basename "$spec" .md)
  impl=$(find vibe-ops/src -name "${base}*.py" 2>/dev/null)
  [ -z "$impl" ] && echo "❌ SPEC WITHOUT CODE: $spec"
done
```

### 10.4 Métricas deste documento

- **Arquivos `.md` indexados:** 35+
- **Arquivos `.py` indexados:** 60+
- **Lacunas de middleware identificadas:** 10
- **Sistemas autônomos mapeados:** 50+
- **Contratos de dados ativos:** 8 (YAMLs + Pydantic + SQL)

### 10.5 Versão & changelog

- **v1.0** (2026-06-05): varredura inicial completa do workspace, identifica 10 middlewares a implementar, 3 riscos de design, 4 sprints de roadmap.

---





