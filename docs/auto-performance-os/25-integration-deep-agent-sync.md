# 25 — Integração: Deep Agent — Sync Vault ↔ SQLite

> **Categoria:** §5 Integração
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** MCP_GATEWAY.md, sync_engine.py, deepagents

---

## §1 — Intuição em linguagem simples

O **Deep Agent** (carro-chefe do IKIGAi) lê o vault markdown, aplica PAE (Pensamento Algorítmico Estratégico) + estrategicos PT-BR, escreve tasks estruturadas em `data/`, e mantém tudo sincronizado bidirecionalmente. Esta é a peça que **transforma prosa humana em tasks executáveis**.

## §2 — Enunciado formal

**Pipeline bidirectional sync:**

```
   VAULT (markdown, source of truth)          DATA (SQLite, runtime state)
              │                                        ▲
              │ 1. read_vault(path)                    │
              ▼                                        │
       DEEP AGENT                                       │
              │                                        │
              │ 2. apply PAE + strategics              │
              ▼                                        │
       TASKS ESTRUTURADAS (Pydantic contracts)         │
              │                                        │
              │ 3. write_planning(cycle_id, tasks)     │
              └────────────────────────────────────────┘
                       sync_interfaces()
                              │
                              ▼
                       INTERFACES (CLI/TUI/Kanban)
                              │
                              │ feedback manual
                              ▼
                       data/feedback/<id>.md
                              │
                              │ get_metrics()
                              ▼
                       DEEP AGENT (observação)
```

**Invariantes:**

| Regra                                              | Razão                                |
|:--------------------------------------------------:|:-------------------------------------|
| Deep Agent é o **único** writer de vault/          | interfaces só leem vault             |
| Interfaces escrevem em `data/feedback/` (não vault)| separação clara de responsabilidades |
| `data/review_queue/` append-only                   | auditoria de mudanças                |
| Pydantic v2 strict (`frozen=True, extra="forbid"`) | garante contratos estáveis           |

**Contratos canônicos consumidos pelo agent:**

| Módulo             | Modelos                                                |
|:------------------:|:-------------------------------------------------------|
| `common.py`        | UEID, Period, Priority, EntityType, RegimeState        |
| `task.py`          | Task, Subtask, ChecklistItem, Project, Milestone       |
| `task_change.py`   | TaskChange, PropagationEvent, TaskAction (Phase 3 v1)  |
| `planning.py`      | PlanningCycle, Wave, Sprint, VaultEvent                |
| `metrics.py`       | Burndown, ExecutionRate, QHEScore                      |

## §3 — Justificativa não-técnica

Por que **Deep Agent único writer de vault**: o vault é **source of truth**. Se interfaces pudessem escrever, dois sistemas poderiam conflitar (ex: CLI renomeia task e TUI deleta). Com writer único, sempre há um pipeline de mudanças auditável.

Por que **bidirecional sync explícito**: a seta `data → vault` é **observação** (agent lê feedback, atualiza planejamento); a seta `vault → data` é **execução** (agent escreve tasks). Sem distinção, o sistema vira loop infinito de read-write.

Por que **Pydantic v2 strict** (`frozen=True, extra="forbid"`): garante que o contrato **não muda silenciosamente**. Se um adapter adiciona um campo extra, o Pydantic recusa — força migração explícita. Sem isso, mudanças aditivas viram bugs difíceis de rastrear.

## §4 — Referências cruzadas (consumidores downstream)

- **24-integration-mesh-ueid-propagation** — sink do Deep Agent (tasks viram TaskChange → mesh)
- **26-integration-cybernetic-loop** — sync é parte do loop Target→Sensor→Adjuster
- **22-meta-ikigai-meta-vector** — meta-vetor calculado a partir de tasks estruturadas
- **12-postulado-consolidacao-diaria** — overall reportado via get_metrics()

## §5 — Fontes

- `src/ikigai/MCP_GATEWAY.md` — especificação dos 8 tools
- `src/middleware/sync_engine.py` — Obsidian ↔ SQLite ↔ Taskwarrior sync
- `src/contracts/` — 5 módulos canônicos
- `vibe-ops/architecture/ADR-001-data-model-unification.md` — unificação de contratos
- `vault/ikigai/meta/agent-harness-decisions.md` — 8 decisões arquiteturais aceitas 2026-07-09