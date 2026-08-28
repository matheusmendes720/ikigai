# 01 — Master Branch Carro-Chefe 2026-08-28 (Canonical Narrative)

> **Categoria:** NEW (gap-fill #1)
> **Público:** Eu mesmo + agentes futuros
> **Localização:** `docs/design-system/01-master-branch-carro-chefe-2026-08-28.md`
> **Origem:** narrativa canônica citada em 39+ trailers mas arquivo inexistente até este commit

---

## §1 — Intuição em linguagem simples

Desde 2026-08-28, a **master branch** do `life/` monorepo tem um **carro-chefe** claro: o **Deep Agent** que sincroniza bidirecionalmente as **forks-prontas** (tuiboard, taskdog, solverforge-calendar — todas externas ao repo, em `life-oss/interfaces/`) ↔ **vault local `.db.markdown`**. Isso substitui o modelo anterior onde PAV TUI/CLI era o carro-chefe primário.

Esta mudança é **arquitetural**, não apenas técnica: marca o fim do "construir tudo internamente" e o início do "consumir contratos MCP de forks-prontas + vault como source-of-truth". PAV continua existindo no repo (em `src/operational/`) mas está **desativado como kernel primário** — agora é **reference implementation** para a matemática auto-performance, não o sistema canônico.

## §2 — Enunciado formal

**Canonical flow (master branch 2026-08-28+):**

```
VAULT (markdown source-of-truth)
   │
   │ 1. Deep Agent reads via read_vault(path)
   ▼
DEEP AGENT (carro-chefe)
   │
   │ 2. Aplica PAE + strategics + 5-vector scoring
   ▼
TASKS ESTRUTURADAS (Pydantic contracts)
   │
   │ 3. write_planning(cycle_id, tasks) → MCP Gateway
   ▼
MCP GATEWAY (8-10 tools)
   │
   ├──▶ tuiboard (Kanban TUI)
   ├──▶ taskdog (Python uv workspace)
   └──▶ solverforge-calendar (Rust ratatui)
   │
   │ 4. Manual input via interfaces → data/feedback/
   ▼
DEEP AGENT (observação)
   │
   │ 5. read_feedback() → atualiza planejamento
   ▼
VAULT (ciclo contínuo)
```

**Stack tecnológica canônica:**

| Camada         | Tecnologia                            | Localização |
|:--------------:|:--------------------------------------|:------------|
| Reasoning      | `ChatAnthropic` (Claude)              | API externa |
| Agent harness  | `deepagents` lib + `FilesystemBackend`| `src/ikigai/src/agents/deepagents_harness.py` |
| Persistence    | `SqliteSaver` (LangGraph checkpoints) | `~/.ikigai/ikigai_checkpoints.db` |
| Tools          | 8 IKIGAi + 3 solverforge + 4 tuiboard + 3 taskdog = 18 tools | `src/ikigai/src/agents/tools.py` |
| HITL           | `interrupt_on={"write_file": True}`   | Deep Agent config |
| Sync           | `SyncEngine` (Obsidian ↔ SQLite ↔ Taskwarrior) | `vibe-ops/src/middleware/sync_engine.py` |
| Cybernetic loop| Target → Sensor → Adjuster → Persist → Sync → Index | `vibe-ops/src/cybernetics/daily_loop.py` |

## §3 — Justificativa não-técnica

**Timeline do pivot:**

| Data        | Marco                                                              |
|:------------|:-------------------------------------------------------------------|
| 2026-07-02  | Data-first methodology aceita (ADR-007) — 5+ logs antes de novas entidades |
| 2026-07-09  | IKIGAi chat harness decisions (8 ADRs)                             |
| 2026-08-26  | AI-native strategic model migration — PAV TUI/CLI deprecated       |
| 2026-08-27  | Reorg P0 bugs fixed (B1-B8)                                        |
| 2026-08-28  | **Master branch carro-chefe canônico** (Deep Agent) — este doc     |

**Por que mudar de PAV-built-from-scratch para Deep Agent + forks-prontas:**

1. **Anti-over-engineering** — o PAV tinha 14+ repos, 2518 testes, 9 telas, FSM de 4 estados — investimento que não gerou uso diário observado. ADR-007 inverte: dados primeiro, código depois.

2. **Reuso de forks-prontas** — tuiboard/taskdog/solverforge-calendar são projetos open-source MIT/Apache maduros. Construir paralelo era duplicação. Agora são **consumidos via MCP contracts**.

3. **Vault como source-of-truth** — markdown sempre foi a verdade canônica para planejamento. Deep Agent lê/escreve markdown nativamente; PAV exigia transformação para SQLite.

4. **HITL embutido** — `interrupt_on={"write_file": True}` garante que mudanças em vault passem por aprovação humana antes de persistir.

## §4 — Referências cruzadas

### Code
- `src/ikigai/src/agents/deepagents_harness.py` — Deep Agent factory (carro-chefe)
- `src/ikigai/src/agents/tools.py` — 18 tools disponíveis
- `src/ikigai/src/agents/ikigai_maintainer/graph.py` — 8-node graph
- `src/ikigai/src/mcp_server/server.py` — MCP gateway (10 tools)
- `vibe-ops/src/cybernetics/daily_loop.py` — Target→Sensor→Adjuster
- `vibe-ops/src/middleware/sync_engine.py` — Obsidian ↔ SQLite ↔ TW

### Docs
- `docs/diagnostics/2026-08-28-phase3-decisions.md` — decisões D1-D6 do pivot
- `code-docs/adr/ADR-007-data-first-methodology.md` — constraint 5+ logs
- `docs/README.md:23-56` — orientação master branch
- `src/operational/CLAUDE.md:1-30` — declaração "No UI lives here"
- `vault/ikigai/meta/agents.md` — meta-learning IKIGAI

### Memory
- `[[master-branch-carro-chefe-2026-08-28]]` — pode agora ser link direto para este doc
- `[[ai-native-strategic-model-migration]]` — pivot 2026-08-26
- `[[legacy-pav-ui-era-2026-08-28]]` — era PAV deprecated
- `[[reorg-bugs-p0-fixed-2026-08-27]]` — bug fixes do reorg
- `[[graph-orchestration-checkpoint-2026-08-27]]` — 2 graphs reais + 4 stubs removidos

## §5 — Fontes

- `src/ikigai/src/agents/deepagents_harness.py` — create_deep_agent factory, 18 tools
- `src/ikigai/src/agents/ikigai_maintainer/graph.py` — make_ikigai_graph (8 nodes)
- `src/ikigai/src/agents/ikigai_maintainer/state.py` — IKIGAiStateDict, compute_meta_vector
- `src/ikigai/MCP_GATEWAY.md` — especificação original MCP gateway
- `vibe-ops/src/cybernetics/daily_loop.py` — CyberneticDailyLoop
- `vault/ikigai/meta/agents.md` — meta-learning IKIGAI (9 screens audit)
- `docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md` — 95 docs classificados (34 STALE, 17 AMBIG, 18 CURRENT, 26 INFRA)
- `docs/diagnostics/2026-08-28-structure-audit/00-INDEX.md` — 40 achados estruturais
