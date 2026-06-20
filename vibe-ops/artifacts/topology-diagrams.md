# Topologia do Sistema — Algorithmic Life OS

> Gerado em: 2026-05-18  
> Série completa de diagramas arquiteturais em 6 camadas.

---

## Diagrama 1 — Visão Geral do Monorepo

```mermaid
graph TD
    subgraph REPO["life-oss Monorepo"]
        subgraph CLI_LAYER["CLI Layer — life CLI Typer App"]
            CLI["life CLI"]
            CFG["LifeConfig"]
            LOG["Logger"]
        end
        subgraph CENTRALS["Domain Centrals"]
            TASK["task\nTaskwarrior"]
            FIN["finance\nfin_ops"]
            KNOW["knowledge\nnotes vault"]
            RES["research\ncrawl search"]
        end
        subgraph HANDLERS["Handlers"]
            DAILY["daily.py"]
            WEEKLY["weekly.py"]
        end
        subgraph PLUGINS["Plugin System"]
            LOADER["Plugin Loader"]
            HC["health_check"]
        end
        subgraph LIFE_OPS["life-ops — life-tatics CLI"]
            LT["Poetry project\nStandalone"]
        end
        subgraph VIBE_OPS["vibe-ops — Cybernetic Orchestrator"]
            VIBE_CLI["main.py CLI"]
            VIBE_SRC["src pipeline models storage"]
            VIBE_TUI["vibeops-tui Rust ratatui"]
            VIBE_DB[("vibe_ops.db")]
        end
        subgraph EXT["External Tools — Local air-gapped"]
            TW["Taskwarrior"]
            OBS["Obsidian Vault"]
            CHROMA[("ChromaDB")]
        end
    end

    CLI --> CENTRALS
    CLI --> DAILY
    CLI --> WEEKLY
    CFG --> CLI
    LOADER --> HC
    TASK --> TW
    KNOW --> OBS
    RES --> OBS
    DAILY --> TASK
    DAILY --> FIN
    WEEKLY --> TASK
    WEEKLY --> FIN
    VIBE_CLI --> VIBE_SRC
    VIBE_SRC --> VIBE_DB
    VIBE_SRC --> TW
    VIBE_SRC --> OBS
    VIBE_SRC --> CHROMA
    VIBE_TUI --> VIBE_DB
    LT -. "decoupled" .-> CLI
```

---

## Diagrama 2 — CLI Layer (Typer App)

```mermaid
graph LR
    subgraph CLI["life CLI — Typer App — python -m life.cli"]
        direction TB
        APP["Typer App\ncli/cli.py"]
        CFG["LifeConfig\ncli/config.py\nlife.yaml"]
        LOG2["Logger\ncli/log.py"]
        TR["Test Runner\ncli/test_runner.py"]
    end

    subgraph CENTRALS["Domain Centrals — BaseCentral.run_cli subprocess"]
        direction TB
        TC["task central\ntask today · review · metrics"]
        FC["finance central\nfin_ops · report"]
        KC["knowledge central\nleitura · mindmaps · notes"]
        RC["research central\nmap · crawl · search"]
    end

    subgraph HANDLERS["Handlers — orchestrate centrals"]
        direction TB
        DH["daily handler\ntask today + finance report"]
        WH["weekly handler\nreview + finance + metrics"]
    end

    subgraph PLUGINS["Plugin System"]
        direction TB
        PP["PluginProtocol\nregister + before/after_daily"]
        PL["Plugin Loader\nplugin_dirs in life.yaml"]
        HCP["builtin health_check\nregisters life health cmd"]
    end

    subgraph CMDS["Top-level commands"]
        CV["config-show"]
        LG["log"]
        TS["test"]
        SM["submodules"]
        FT["features"]
        PLC["plugins"]
        VR["version"]
    end

    CFG --> APP
    LOG2 --> APP
    APP --> TC
    APP --> FC
    APP --> KC
    APP --> RC
    APP --> DH
    APP --> WH
    APP --> CMDS
    PL --> HCP
    PL --> PP
    PP --> APP
    DH --> TC
    DH --> FC
    WH --> TC
    WH --> FC
    WH --> KC
    TR --> TS
```

---

## Diagrama 3 — vibe-ops Arquitetura Interna

```mermaid
graph TD
    subgraph VIBE["vibe-ops — Cybernetic Orchestrator"]

        subgraph ENTRY["Entry Points"]
            CLI_E["main.py argparse CLI"]
            TUI["vibeops-tui Rust ratatui"]
        end

        subgraph CYBER["Cybernetics Layer"]
            LOOP["CyberneticDailyLoop\ncybernetics/daily_loop.py"]
            ENGINE["BinaryKnowledgeTree\nGapSearchEngine\ncybernetics/engine.py"]
        end

        subgraph PIPELINE["Pipeline Layer — 31 modules"]
            POLICY["PolicyEngine\nPUSH-MAINTAIN-REDUCE-RECOVER"]
            IKIGAI["IkigaiScorer\nMulti-vector health"]
            RAG["HybridRAGIndexer\nMultimodal search"]
            INGEST["IngestionEngine\nFrontmatter parsing"]
            ENRICH["EnrichmentEngine\nMetadata enrichment"]
            MVL["MVLOrchestrator\nData mesh orchestration"]
            GAP["GapEngine\nExecution debt analysis"]
            ROUTER["UnifiedRouter\nSQL-Vector routing"]
        end

        subgraph MIDDLEWARE["Middleware Layer"]
            SYNC["SyncEngine\nObsidian-SQLite-TW sync"]
        end

        subgraph MODELS["Pydantic v2 Models — 14 entity files"]
            STUDY["study_entities"]
            HABIT["habit_entities"]
            POLICY_M["policy_entities"]
            TEMPORAL["temporal_entities"]
            PROJECT["project_entities"]
            RAG_M["rag_entities"]
            IKIGAI_M["ikigai_entities"]
        end

        subgraph STORAGE["Storage Layer"]
            ORM["SQLAlchemy 2.0 ORM"]
            SQLITE_A["SQLiteAdapter"]
            CHROMA_A["ChromaAdapter"]
            VEC["sqlite-vec + NumPy fallback"]
            MESH["DataMeshAdapter"]
            UEID["UEID Manager"]
        end

        subgraph DB["Persistence"]
            SQLITE_DB[("vibe_ops.db SQLite")]
            CHROMA_DB[("ChromaDB vectors")]
        end

        subgraph EMBED["Embeddings"]
            EMB["EmbeddingProvider\nLocal or OpenAI"]
        end
    end

    CLI_E --> LOOP
    TUI --> SQLITE_DB
    LOOP --> POLICY
    LOOP --> IKIGAI
    LOOP --> SYNC
    LOOP --> RAG
    LOOP --> ENGINE
    POLICY --> IKIGAI
    RAG --> EMB
    RAG --> CHROMA_A
    RAG --> VEC
    INGEST --> ENRICH
    ENRICH --> MESH
    MVL --> MESH
    MESH --> ORM
    MESH --> UEID
    SYNC --> SQLITE_A
    SYNC --> ORM
    SQLITE_A --> SQLITE_DB
    CHROMA_A --> CHROMA_DB
    ORM --> SQLITE_DB
    VEC --> SQLITE_DB
    PIPELINE --> MODELS
```

---

## Diagrama 4 — Loop Cibernético Target-Sensor-Adjuster (Sequência)

```mermaid
sequenceDiagram
    participant CLI as main.py CLI
    participant LOOP as CyberneticDailyLoop
    participant IKI as IkigaiScorer
    participant SENSOR as SQLite Sensor
    participant POL as PolicyEngine
    participant SYNC as SyncEngine
    participant RAG as HybridRAGIndexer
    participant TW as Taskwarrior
    participant OBS as Obsidian Vault
    participant DB as vibe_ops.db
    participant CHROMA as ChromaDB

    CLI->>LOOP: execute_daily_cycle(date)

    Note over LOOP,IKI: 1. TARGET — Setpoint computation
    LOOP->>IKI: compute_score()
    IKI->>DB: query study/habit/health metrics
    DB-->>IKI: raw vectors
    IKI-->>LOOP: {global, study, dev, health} scores

    Note over LOOP,SENSOR: 2. SENSOR — Real execution capture
    LOOP->>SENSOR: _read_sensor_data(date)
    SENSOR->>DB: SELECT study_sessions WHERE date=?
    SENSOR->>DB: SELECT habit_states WHERE date=?
    DB-->>SENSOR: actual_hours, consistency, infractions
    SENSOR-->>LOOP: metrics dict

    Note over LOOP,POL: 3. ADJUSTER — Cybernetic correction
    LOOP->>DB: _get_previous_decision()
    DB-->>LOOP: prev PolicyDecision
    LOOP->>POL: evaluate(metrics, prev_decision, date)
    POL-->>POL: state machine PUSH-MAINTAIN-REDUCE-RECOVER
    POL-->>LOOP: PolicyDecision {policy, budget, alerts}

    Note over LOOP,DB: 4. PERSIST
    LOOP->>DB: INSERT policy_decisions

    Note over LOOP,TW: 5. SYNC — Distribution
    LOOP->>SYNC: sync_sqlite_to_taskwarrior(policy.value)
    SYNC->>DB: SELECT planning_entities JOIN roadmap_sync
    DB-->>SYNC: pending study plans
    SYNC->>TW: tasks.add / tasks.filter (upsert)
    TW-->>SYNC: uuid
    SYNC->>DB: UPDATE roadmap_sync SET tw_uuid

    Note over LOOP,CHROMA: 6. SEMANTIC INDEXING
    LOOP->>RAG: index_vault(vault_path)
    RAG->>OBS: rglob *.md
    OBS-->>RAG: markdown files
    RAG->>CHROMA: embed + upsert vectors
    RAG->>DB: store RAG metadata

    LOOP-->>CLI: PolicyDecision (final)
```

---

## Diagrama 5 — Data Flow (Obsidian → SQLite → Taskwarrior ↔ ChromaDB)

```mermaid
graph LR
    subgraph SOURCES["Data Sources — External Tools"]
        OBS["Obsidian Vault\nMarkdown + Frontmatter"]
        TW_SRC["Taskwarrior\ntask binary + tasklib"]
        MANUAL["Manual Input\nstudy_sessions / habit_states"]
    end

    subgraph INGEST["Ingestion — Obsidian to SQLite"]
        FM["FrontmatterParser"]
        IE["IngestionEngine"]
        EE["EnrichmentEngine"]
        UEID["UEID Manager\nSHA-256 idempotent IDs"]
    end

    subgraph STORE["Central Store — vibe_ops.db SQLite"]
        PE["planning_entities"]
        RS["roadmap_sync"]
        SS["study_sessions"]
        HS["habit_states"]
        PD["policy_decisions"]
    end

    subgraph VEC["Vector Store"]
        CHROMA["ChromaDB vectors"]
        SVEC["sqlite-vec / NumPy fallback"]
    end

    subgraph PIPELINE2["Processing Pipeline"]
        RAG2["HybridRAGIndexer"]
        MESH2["DataMeshAdapter"]
        ROUTER2["UnifiedRouter"]
        MVL2["MVLOrchestrator"]
    end

    subgraph OUTPUT["Output — Distribution"]
        TW_OUT["Taskwarrior Injection\nthrottled by PolicyState"]
        STATUS["status command"]
        GAPS_OUT["gaps command"]
        TUI2["Rust TUI Dashboard"]
    end

    OBS -->|"rglob *.md"| FM
    FM --> IE
    IE --> EE
    EE --> UEID
    UEID -->|"idempotent upsert"| PE
    MANUAL --> SS
    MANUAL --> HS
    PE --> RS
    RS -->|"status=pending"| TW_OUT
    TW_SRC -->|"completed tasks feedback"| RS
    PE --> MESH2
    MESH2 --> ROUTER2
    ROUTER2 --> CHROMA
    ROUTER2 --> SVEC
    RAG2 -->|"embed vault"| CHROMA
    RAG2 --> SVEC
    MVL2 --> MESH2
    SS --> PD
    HS --> PD
    PD -->|"policy throttle"| TW_OUT
    PD --> STATUS
    PE --> GAPS_OUT
    SS --> GAPS_OUT
    PD --> TUI2
    SS --> TUI2
    HS --> TUI2
```

---

## Diagrama 6 — Policy Engine State Machine

```mermaid
stateDiagram-v2
    [*] --> PUSH : Sistema inicializa

    PUSH : PUSH
    PUSH : Budget 4-6h/dia — Máxima expansão

    MAINTAIN : MAINTAIN
    MAINTAIN : Budget 2-3h/dia — Operação nominal

    REDUCE : REDUCE
    REDUCE : Budget 1-2h/dia — Redução controlada

    RECOVER : RECOVER
    RECOVER : Budget até 1h/dia — Bloqueia tasks > 60min

    PUSH --> MAINTAIN : qhe OK + c_comp OK
    PUSH --> REDUCE : infrações > 2 ou horas < 50% target
    PUSH --> RECOVER : infrações > 5 ou colapso de consistência

    MAINTAIN --> PUSH : qhe > 0.9 + c_comp > 0.95 por 3+ dias
    MAINTAIN --> REDUCE : infrações 2-4 ou c_comp < 0.5
    MAINTAIN --> RECOVER : infrações > 5 ou burnout detectado

    REDUCE --> MAINTAIN : c_comp > 0.7 e sem infrações por 2 dias
    REDUCE --> RECOVER : c_comp < 0.3 ou infrações > 3

    RECOVER --> REDUCE : c_comp > 0.5 após período mínimo
    RECOVER --> MAINTAIN : recuperação completa c_comp > 0.8 + 0 infrações
```
