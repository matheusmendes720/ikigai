# 06 — Canvas: Agents Architecture (Deep Agent + IKIGAi Maintainer + LangGraph)

> **Categoria:** INDEX (Layer 2 — Architecture Canvas)
> **Anchor canônico:** `src/ikigai/src/agents/` + `src/ikigai/src/mcp_server/`
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Resumo

A camada de agentes tem **3 peças load-bearing**:
1. **Deep Agent** (carro-chefe) — LangGraph + `deepagents` lib + `FilesystemBackend` + `SqliteSaver`
2. **IKIGAi Maintainer** — LangGraph com 8 nodes, 1 dos 6 graphs registrados
3. **MCP Gateway** — 10 tools (não 8 como documentado em `MCP_GATEWAY.md`)

HITL embutido: `interrupt_on={"write_file": True}` pausa antes de mudanças em vault.

## §2 — Inventário

| Arquivo | Função | LOC | Notas |
|:--------|:-------|:---:|:------|
| `src/ikigai/src/agents/deepagents_harness.py` | Deep Agent factory (carro-chefe) | ~280 | create_deep_agent + 18 tools |
| `src/ikigai/src/agents/tools.py` | 18 LangChain @tool-wrapped tools | ~600 | 8 IKIGAi + 3 solverforge + 4 tuiboard + 3 taskdog |
| `src/ikigai/src/agents/reliability.py` | @retry_with_backoff, @circuit_breaker, invalidate_session_cache | ~200 | Padrão #17 (decorator stack) |
| `src/ikigai/src/agents/ikigai_maintainer/__init__.py` | Re-exports state + graph factory | ~10 | — |
| `src/ikigai/src/agents/ikigai_maintainer/state.py` | IKIGAiStateDict (TypedDict), PlanTier, PlanVerdict, BalancerVerdict, CorrectionSignal, compute_meta_vector | ~350 | 60% geo + 40% harmonic |
| `src/ikigai/src/agents/ikigai_maintainer/graph.py` | make_ikigai_graph (StateGraph) | ~200 | 8 nodes, SqliteSaver |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/observe.py` | Lê sensors (Q_HE, workload, UPI) | ~120 | Invoca solverforge subprocess |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/score_vectors.py` | 5 vectors + meta-vector | ~150 | H4/H5 weights modulados por regime |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/heuristics.py` | H1-H6 deterministic corrections | ~180 | — |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/balance.py` | Hysteresis-aware workload/capacity balancer | ~140 | Padrão #15 |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/decompose.py` | UEID hierarchy traversal (Dream→Task) | ~100 | Solverforge subprocess |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/plan.py` | Prospective channel (regime-specific drafting) | ~120 | — |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/reflect.py` | Retrospective channel (counts done/blocked) | ~100 | — |
| `src/ikigai/src/agents/ikigai_maintainer/nodes/commit.py` | Persist to SQLite + markdown vault (kill-switch guarded) | ~140 | — |
| `src/ikigai/src/mcp_server/server.py` | 10 MCP tools (stdin/stdout JSON-RPC) | ~250 | asyncio |
| `langgraph.json` | 6 graphs registrados | ~40 | — |
| `vibe-ops/src/langgraph_entry.py` | Entry factory para 6 graphs | ~150 | thin-adapter pattern |

## §3 — Deep Agent (carro-chefe)

`deepagents_harness.py` configura:

```python
agent = create_deep_agent(
    model=ChatAnthropic(...),
    tools=IKIGAI_TOOLS,  # 18 tools
    backend=FilesystemBackend(root_dir=Path.home(), virtual_mode=False),
    checkpointer=SqliteSaver(db_path="~/.ikigai/ikigai_checkpoints.db"),
    interrupt_on={"write_file": True},  # HITL
)
```

**18 tools expostos:**

| Categoria | Tools | Count |
|:----------|:------|:------|
| IKIGAi | `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections`, `ikigai_decompose`, `ikigai_plan_cycle`, `ikigai_sync_vault`, `ikigai_checkpoint` | 8 |
| solverforge-calendar | `solverforge_*` (3) | 3 |
| tuiboard | `board_*` (4) | 4 |
| taskdog | `taskdog_*` (3) | 3 |

**HITL:** `interrupt_on={"write_file": True}` pausa o agent antes de qualquer write em vault. Usuário humano aprova/rejeita.

## §4 — IKIGAi Maintainer (8 nodes)

`make_ikigai_graph()` cria um `StateGraph(IKIGAiStateDict)` com 8 nodes conectados por edges condicionais:

```
observe → score_vectors → heuristics → balance → decompose → plan → reflect → commit
                ↑                                                            ↓
                └────────────────────────────────────────────────────────────┘
```

**Cada node:**
- `observe`: lê sensors (Q_HE, workload, UPI) — invoca solverforge subprocess
- `score_vectors`: calcula 5 vectors + meta-vector; **H4/H5 weights modulados por regime**
- `heuristics`: H1-H6 deterministic corrections
- `balance`: hysteresis-aware workload/capacity balancer
- `decompose`: UEID hierarchy traversal (Dream→Task) via solverforge subprocess
- `plan`: prospective channel (regime-specific drafting)
- `reflect`: retrospective channel (counts done/blocked from UPI history)
- `commit`: persiste em SQLite + markdown vault (**kill-switch guarded**)

**Compute meta-vector:** `meta = 0.6·geo + 0.4·harmonic` (ADR-003 §3.4).

## §5 — MCP Gateway (10 tools, não 8)

`MCP_GATEWAY.md` documenta 8 tools; o server real registra 10. Correção:

| # | Tool | Schema | Description |
|:-:|:-----|:-------|:------------|
| 1 | `ikigai_score` | `{}` | 5-vector + meta + Q_HE |
| 2 | `ikigai_regime` | `{}` | regime + Q_HE + dias |
| 3 | `ikigai_phase` | `{}` | phase + iteration + weights |
| 4 | `ikigai_corrections` | `{limit=20}` | H1-H6 signals |
| 5 | `ikigai_decompose` | `{dream_ueid}` | Decompose Dream UEID |
| 6 | `ikigai_plan_cycle` | `{active_dream_ueid, cycle_start, cycle_end}` | Run full cycle |
| 7 | `ikigai_checkpoint` | `{action: get\|set\|list, thread_id, state_snapshot}` | Checkpoint DB |
| 8 | `ikigai_sync_vault` | `{cycle_id}` | Sync cycle to markdown |
| 9 | `ikigai_write_tasks` | `{tasks: [...]}` | Write to `data/tasks.jsonl` |
| 10 | `ikigai_read_tasks` | `{horizon, done, project_id, limit=50}` | Read from `data/tasks.jsonl` |

**MCP transport:** stdio JSON-RPC, protocol `2024-11-05`. Entry: `ikigai.bat mcp` ou `python run_mcp_server.py`.

**Config:** `src/ikigai/mcp_config.json` registra `ikigai`, `tuiboard`, `taskdog` MCP servers.

## §6 — 6 LangGraph graphs (`langgraph.json`)

| Graph | Entry factory | Nodes |
|:------|:--------------|:------|
| `pae_maintainer` | `make_pae_graph` | observe → plan_reflect → balance → commit |
| `quarterly_replan` | `make_replan_graph` | loads `quarterly-replan.yml` |
| `test_de_fogo_rollup` | `make_rollup_graph` | loads `test-de-fogo-rollup.yml` |
| `correction_protocol` | `make_correction_graph` | loads `correction-protocol.yml` |
| `dream_falsification` | `make_falsification_graph` | loads `dream-falsification.yml` |
| `ikigai_maintainer` | `make_ikigai_graph` | observe → score_vectors → heuristics → balance → decompose → plan → reflect → commit |

**YAML workflows:** carregados de `.claude/skills/quarterly-planner/workflows/*.yml`.

**Thin-adapter pattern:** `vibe-ops/src/langgraph_entry.py` wrap de custom Python graphs como langgraph SDK wrappers.

## §7 — Reliability layer (`reliability.py`)

Decoradores críticos:

```python
@retry_with_backoff(
    name="...",
    retryable_exceptions=(...),
    config=RetryConfig(max_attempts=3, initial_backoff_s=0.5, max_backoff_s=8.0)
)
@circuit_breaker(
    name="...",
    config=CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=30.0)
)
def my_tool(...): ...
```

**Invariante load-bearing:** ordem dos decorators importa — CB **outer**, retry **inner**. Mover retry para fora causaria storms de retry quando o circuit está aberto.

**Default config:** `max_attempts=3`, `initial_backoff_s=0.5`, `max_backoff_s=8.0`, `failure_threshold=5`, `reset_timeout_s=30.0`.

**OTA span:** cada retry emite span (OTel propagation).

## §8 — Cross-references

### Code
- `src/ikigai/src/agents/deepagents_harness.py`
- `src/ikigai/src/agents/tools.py`
- `src/ikigai/src/agents/reliability.py`
- `src/ikigai/src/agents/ikigai_maintainer/graph.py`
- `src/ikigai/src/mcp_server/server.py`
- `langgraph.json`

### Docs
- `src/ikigai/MCP_GATEWAY.md` — especificação original (8 tools, desatualizada)
- `vibe-ops/architecture/ADR-002-mesh-contracts-state-machines.md` — state machines
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` — IKIGAi meta-brain
- `docs/auto-performance-os/25-integration-deep-agent-sync.md` — sync flow
- `docs/auto-performance-os/22-meta-ikigai-meta-vector.md` — meta-vector math

### Memory
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical narrative
- `[[ikigai-chat-harness-decisions]]` — 8 ADRs aceitos
- `[[graph-orchestration-checkpoint-2026-08-27]]` — 2 graphs reais

## §9 — Fontes

- `src/ikigai/src/agents/deepagents_harness.py` — Deep Agent factory
- `src/ikigai/src/agents/tools.py` — 18 tools
- `src/ikigai/src/agents/reliability.py` — decorators
- `src/ikigai/src/agents/ikigai_maintainer/graph.py` — make_ikigai_graph
- `src/ikigai/src/agents/ikigai_maintainer/state.py` — IKIGAiStateDict, compute_meta_vector
- `src/ikigai/src/mcp_server/server.py` — 10 MCP tools
- `langgraph.json` — 6 graphs registrados
- `vibe-ops/src/langgraph_entry.py` — entry factory
- `src/ikigai/MCP_GATEWAY.md` — spec original (desatualizada)
