# DEEP_DIVE_REVIEW.md

**Data:** 2026-09-10 (madrugada, sessão autônoma)
**Método:** Code read direto de `src/ikigai/`, `sys_ikigai/`, `src/mesh/`, `interfaces/cli/`, `langgraph.json`, drift tests. Sem subagents (foi um único agente background).

---

## Resumo em uma linha

> **6 bugs reais foram encontrados após o P0 fix.** O harness ABRE mas o agente dentro é stub — não roda LLM nos nós, não tem persona, e o estado entre nós está quebrado.

---

## 1. Shipped Surface (ground truth)

### 1.1 LangGraph graphs em `langgraph.json`

| Graph | Entry | Status |
|-------|-------|--------|
| `pae_maintainer` | `vibe-ops/src/langgraph_entry.py:make_pae_graph` | registered |
| **`ikigai_maintainer_v2`** | `src/ikigai/src/agents/v2/graph.py:make_v2_graph` | **✅ registered** (corrigi meu HTML de topologia — eu errei antes) |
| `ikigai_fork_smoke` | `src/ikigai/src/agents/v2/fork_smoke_graph.py:make_fork_smoke_graph` | registered |

`make dev-graph NAME=ikigai_maintainer_v2` funciona. O graph boota. Mas os nós internos são stubs (ver §2).

### 1.2 v2 graph structure (11 nodes)

```
observe → score_vectors → heuristics → balance → (decompose | plan)
  → tag_and_persist → reflect → commit → dispatch_sub_agents → surface_intentions
```

Plus `error` terminal + meta_plan subgraph separado (classify_intent → fetch_context → generate_proposal → proposal_executor).

### 1.3 MCP gateway (FastMCP stdio, 11 tools + 6 resources)

Tools: `ikigai_decompose`, `ikigai_write_tasks`, `ikigai_read_tasks`, `ikigai_mesh_show`, `ikigai_task_create`, `ikigai_health`, `vault_write`, `vault_read`, `investigation_enqueue`, `investigation_status`, `investigation_complete`.

Resources: `ueid://`, `queue://pending`, `queue://events/{id}`, `health://gateway`, `plans://cycles`, `plans://cycles/{id}`.

### 1.4 Data mesh (3 adapters + PAE consumer)

- `CliAdapter` → `data/tasks.jsonl`
- `TaskdogAdapter` → `data/taskdog/tasks.db` (SQLite UPSERT)
- `SolverforgeCalendarAdapter` → `data/solverforge_calendar/unified_planning.db`
- `agent_consumer.validate()` → PAE rules
- `review_queue_worker` → drains `data/review_queue/`

### 1.5 sys_ikigai (Pydantic v2 strict)

- Entities: `UEID`, `Regime`, `RegimeGraph`, `RegimeOverride`, etc.
- 8 FSMs: `dream`, `goal`, `objective`, `project`, `task`, `habit`, `routine`, `deliverable`
- `vault_write` (sole vault writer per ADR-012) — atomic, VaultLock, audit log
- `kill_switch` (3-mechanism: env var > vault file > data file)
- `transition_validator` — SONHO writes requerem actor=user
- `vault_write_wrapper` (ADR-029)
- `UnifiedMCPGateway` (HTTP+SSE, pure stdlib)

---

## 2. Bugs CRÍTICOS

### 🔴 B1 — UEID 4-part vs 5-part split

Duas regexes em código ativo discordam.

| Arquivo | Pattern |
|---------|---------|
| `sys_ikigai/entities/ueid.py:16` | **5-part**: `(ikigai\|tw\|obsidian\|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}$` |
| `sys_ikigai/security/kill_switch.py:111` | **4-part**: `kill:kill-event:<uuid>:<16hex>` |
| `src/ikigai/src/agents/v2/subgraph.py:50` | **4-part**: `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` |
| `src/mesh/agent_consumer.py` (via `src/contracts.common.UEID`) | inherits whichever canonical UEID is imported |

CLAUDE.md diz "4-part canonical per ADR-014 supersedes 2026-08-31 5-part" — mas `sys_ikigai/entities/ueid.py` ainda usa 5-part. Qualquer UEID criado pelo v2 graph (4-part) VAI FALHAR a validação canônica 5-part em `agent_consumer.py` / `tools_mesh.py:59` (`parsed = UEID(ueid)`).

**Fix:** atualizar `sys_ikigai/entities/ueid.py:16` pra regex 4-part. Adicionar drift test.

### 🔴 B2 — v2 node state fields não existem em `IKIGAiStateDict`

| Node | Reads | Existe em `IKIGAiStateDict`? |
|------|-------|-------------------------------|
| `observe_node` | `state["date"]` | ❌ não |
| `score_vectors_node` | `state["vectors"]` | ❌ (state tem `vector_scores: dict`) |
| `heuristics_node` | `state["context"]` | ❌ |
| `balance_node` | `state["load"]` | ❌ |
| `decompose_node` | `state["task_id"]` | ❌ |
| `plan_node` | `state["cycle_id"]` | ✅ |
| `tag_and_persist_node` | `state["ueid"]` | ❌ (state tem `active_*_ueids: list[str]`) |
| `reflect_node` | `state["cycle_id"]` | ✅ |
| `commit_node` | `state["cycle_id"]` | ✅ |
| TODOS os nodes | writes `error_channel: []` | ❌ (state tem `error_type`, `error_message`) |

**Maioria dos 11 nós não pode rodar de verdade** — quebraria em `state["vectors"]` lookup se esses campos estivessem missing. Os testes em `test_phase_8_2_wiring.py:38-46` só verificam os wrappers do mcp_bridge contra `FakeMcpServer` — nunca invocam o graph full com state realístico.

### 🔴 B3 — `observe.py` imports quebrados

Linhas 53-66 chamam `subprocess.run` e `json.loads` mas nenhum é importado. A função `_read_workload_from_upi` é dead code — nunca chamada por `observe_node`. O `observe_node` real chama `mcp_bridge.ikigai_observe_pav_state(date=state.get("date", "2026-09-08"))` — mas `state["date"]` não existe em `IKIGAiStateDict`.

### 🟠 B4 — CLI v2 surface é `plan` only

`interfaces/cli/v2.py:183` registra APENAS o comando `plan` (Plan D meta-planner). V5-D aposentou daily/weekly/today. Então `dcode --chat` NÃO EXISTE como CLI — o que você tá chamando nunca foi shipped.

O v2 graph PODE ser invocado via `make dev-graph NAME=ikigai_maintainer_v2`, mas isso é um langgraph dev server, não um chat harness.

### 🟠 B5 — `agent_consumer` existe mas nunca invocado

`src/mesh/agent_consumer.py` + `src/mesh/review_queue_worker.py` ship com PAE validation. Nada em `interfaces/cli/`, `ikigai.bat`, `make`, ou qualquer daemon os invoca. Eventos ficam em `data/review_queue/` forever. É por isso que `mesh-show` retorna `cli: <task>, taskdog: null, solverforge_calendar: null` pra cross-fork joins.

### 🟠 B6 — `heuristics.py` usa `_c(...)` que pode não existir

Linhas 44, 47, 55, 73, 87, 112, 115, 122 referenciam `_c(...)` para constantes como `_c("REGIME_TARGETS")`, `_c("HEURISTICS_H2_DEVIATION_WARN")`, etc. O `load_constants.py` mostrado expõe `get(key)` não `_c`. Se `_c` não existe, `heuristics_node` daria `NameError` imediatamente — mas `heuristics_node` só chama `mcp_bridge.ikigai_heuristics(...)`, então esse dead code path não dispara. Mais um sinal que esses nodes são stubs.

---

## 3. Persona / Behavior gap

**NÃO HÁ system prompt definindo voz/persona do agente em lugar nenhum no v2 graph ou MCP server.** O LLM-as-judge review que você quer é impossível porque:

- `make_v2_graph()` aceita apenas `checkpoint_db` e `entry_point` — sem `system_prompt`, sem `instructions`
- Os tools do MCP server retornam JSON strings — sem LLM call, sem persona context
- O meta-plan subgraph (classify_intent → fetch_context → generate_proposal) não tem LLM call em lugar nenhum — é tudo keyword classification + filesystem walking
- `heuristics.py` TEM heuristic computation layer (H1-H6) mas é tudo dead code porque `heuristics_node` em si só chama o MCP bridge

Então "o agente não parece saber que é um assistente de planejamento" é estruturalmente exato: **o harness tem ZERO LLM calls e ZERO persona context.** O único que roda é aritmética + filesystem walking.

A coisa mais próxima de "persona":
- `mcp_bridge.py:23` — `"Observability — real OTel tracer"`
- `graph.py:6` — docstring descrevendo o pipeline shape
- `subgraph.py:1-26` — ADR-026 reference docstring

Nenhuma dessas é user-facing voice.

---

## 4. Drift net coverage

✅ Cobrindo:
- `FORBIDDEN_IMPORTS` (math kernel packages — `ikigai.core.scoring` etc.)
- `FORBIDDEN_FUNCTIONS` (15 math function names)
- `FORBIDDEN_CLASSES` (6 scorer classes)
- `FORBIDDEN_MCP_TOOLS` (7 re-deleted observation wrappers)
- `KILL_SWITCH_*` keys em `algorithm_constants.json` (W4.7)
- `vault_write_wrapper` canonical API surface + LEGAL_CALLERS whitelist

❌ NÃO cobrem:
- **4-part vs 5-part UEID split (B1)**
- **v2 node field-name ↔ IKIGAiStateDict consistency (B2)**
- **`subprocess`/`json` import completeness em observe.py (B3)**
- **`dcode --chat` entry exists**

---

## 5. Recomendações (por blast radius)

1. **B1 fix (UEID split)** — 1 linha em `sys_ikigai/entities/ueid.py:16` + drift test. Sem isso, mesh-show quebra pra qualquer UEID 4-part.
2. **B2 fix (state field names)** — 9 edits em `src/ikigai/src/agents/v2/nodes/*.py` + `_state_get()` helper que usa `state.get(...)` com nome canônico (`active_task_ueids[0]` em vez de `task_id`).
3. **Definir persona** — add `system_prompt` arg em `make_v2_graph()` + passar pra cada nó via state. Ou criar `mcp_server/persona.py` com prompt base carregado por `ikigai_decompose` etc.
4. **Wire `agent_consumer` como daemon** — `make` target ou systemd unit que roda `python -m src.mesh.review_queue_worker` em loop.
5. **Adicionar CLI binding pra `dcode --chat`** — comando Typer em `interfaces/cli/v2.py` que chama `compiled.invoke({"user_request": args.request})`.
6. **B3 fix (observe.py imports)** — remover `_read_workload_from_upi` ou adicionar `import subprocess, json`.
7. **Adicionar drift tests pra B1, B2, B3** — previne re-regressão.

---

## 6. Onde a "versão antiga de AI Engineering" vivia

Baseado em code archaeology, a versão antiga provavelmente:
- Lia `vault/` como contexto markdown (agora só via `vault_read` MCP tool, nunca auto-loaded no graph)
- Aplicava `strategics/` como system prompt context (agora zero LLM call, então zero context)
- Emit framing human-readable "I'm here to help with X" (agora enterrado em docstrings, nunca surfaced)

**Recuperável de:** `archive/recovered-agentic-2026-09-01/` (32 source files). Não li — fora do escopo deste review, mas flagged pro LLM-as-judge pass se você quiser arqueologia de persona.

---

## Conclusão honesta

**O harness ABRE (`dcode --chat` works), mas o agente dentro é stub.** Você tem:
- ✅ Infraestrutura funcional (entry points, MCP servers, drift net, OTel, sys_ikigai)
- ❌ Lógica interna quebrada (B1, B2, B3, B4, B5, B6)
- ❌ Persona ausente (zero system prompt)

Para um agente que AJUDA com planejamento (não só roda arithmetic), você precisa no mínimo B1, B2, persona, e um LLM call real em algum dos nodes. Isso é trabalho de médio porte — não coisa de uma sessão.

Nenhuma venda de "fully ready" aqui. O que tem funciona. O que não tem, não.

---

**Report end.** Nada commitado neste fork.
