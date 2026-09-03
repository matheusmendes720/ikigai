# 24 — Taskdog Paths Architecture (3 paths to the same fork)

> **Categoria:** PATTERN (cross-cutting, position #24 — fills gap #4 from 2026-08-30 fork-connection diagnostic)
> **Anchor canônico:** `src/ikigai/src/agents/tools.py` (Path 1) + `src/mesh/adapters/taskdog.py` (Path 2) + `src/ikigai/src/ikigai/gateway/clients/taskdog.py` (Path 3)
> **Origem:** 2026-08-31 verification after subagent fabrication of "7 taskdog MCP tools live" claim (REFUTED by main-session `mcp_inspect.py`: 15 tools, ZERO `taskdog_*`)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (MCP, stdio, subprocess, JSON-RPC, Content-Length, fork, adapter, propagate, UEID, UPSERT, deepagent, IKIGAI_TOOLS, reliability, circuit breaker, retry, harness)
> **Status:** CANONICAL — replaces ad-hoc reasoning about "is taskdog connected?" with explicit path designation

---

## §1 — Resumo

Este doc **fecha o gap #4** identificado no diagnóstico de 2026-08-30: existem **3 paths distintos para alcançar o fork taskdog** no sistema, mas apenas **Path 1 está ativo** hoje e **Path 3 está broken por design** (módulo `taskdog_mcp.server` jamais foi instalado). A confusão surgiu porque um subagente alegou "taskdog conectado via MCP gateway com 7 tools live" — claim REFUTADO por verificação main-session (`mcp_inspect.py` mostra 15 tools, ZERO `taskdog_*`; `python -m taskdog_mcp.server` retorna `ModuleNotFoundError`). A designação canônica é:

| Path | Direção | Status hoje | Quem usa |
|:-----|:--------|:------------|:---------|
| **Path 1 — Harness subprocess** | agent → `taskdog.exe` | ✅ **CANONICAL** (4 @tool wrappers, 12/12 IKIGAI_TOOLS bound) | Deep agent planning (LLM tool_choice) |
| **Path 2 — Mesh SQLite adapter** | mesh queue → `data/taskdog/tasks.db` | ✅ **ALTERNATIVE** (UPSERT on ueid) | Cross-fork propagation events only |
| **Path 3 — MCP gateway factory** | gateway → `taskdog_mcp.server` | ❌ **DEFERRED** (module missing) | Resurrected only on explicit demand |

**Não trocar Path 1 por Path 3 sem motivo** — Path 1 funciona, é testado (7/7 E2E PASS em `tests/test_taskdog_harness_e2e.py`), e Path 3 exigiria rebuild do módulo `taskdog_mcp.server` que foi removido/nunca-buildado (ver §6 receita para quando for demandado).

---

## §2 — Path 1: Harness subprocess (CANONICAL)

### §2.1 Anatomia

```
LLM tool_choice("taskdog_create_task", {"name": "..."})
  → IKIGAI_TOOLS[idx]                 # 12 tools bound em deepagents_harness._make_agent()
    → @circuit_breaker                # src/agents/reliability.py:91-130
      → @retry_with_backoff           # 3 attempts, exp backoff
        → subprocess.run([TASKDOG_CLI, ...], timeout=30)
          → taskdog.exe v0.23.0       # C:/Users/mathe/.local/bin/taskdog.exe
            → taskwarrior store       # ~/.taskrc + .task/data.db
```

### §2.2 Componentes

| Componente | Path | Responsabilidade |
|:-----------|:-----|:----------------|
| `_TASKDOG_CLI` | `src/agents/tools.py` | `os.environ.get("TASKDOG_CLI", "taskdog.exe")` |
| `taskdog_create_task` | `src/agents/tools.py` | `@tool` → `subprocess.run([_TASKDOG_CLI, "add", name])` |
| `taskdog_list_tasks` | `src/agents/tools.py` | `@tool` → `subprocess.run([_TASKDOG_CLI, "list"])` |
| `taskdog_get_task` | `src/agents/tools.py` | `@tool` → `subprocess.run([_TASKDOG_CLI, "show", str(task_id)])` |
| `taskdog_complete_task` | `src/agents/tools.py` | `@tool` → `subprocess.run([_TASKDOG_CLI, "done", str(task_id)])` |
| `IKIGAI_TOOLS` | `src/agents/tools.py` | List of 12 tools (4 taskdog + 2 vault + 2 solverforge + 4 tuiboard) — drift detector enforced |
| `_make_agent()` | `src/ikigai/src/agents/deepagents_harness.py` | `create_deep_agent(model, tools=IKIGAI_TOOLS, ...)` |

### §2.3 Lifecycle crítico (taskdog v0.23.0)

taskdog v0.23.0 enforces a **state machine** que o harness agent precisa respeitar:

```
pending  --taskdog start-->  active  --taskdog done-->  completed
   |                            |
   +---taskdog cancel----------+
```

**Consequência:** chamar `taskdog_complete_task` em uma task `pending` **falha** com `✗ Error: Cannot complete task N: task is PENDING`. Workaround atual (ver E2E test): o agent workflow precisa incluir `taskdog start` antes de `done`. Isso é um **gap de design** — o `taskdog_complete_task` @tool deveria orquestrar `start → done` atomicamente, ou existir um `taskdog_start_task` @tool separado. **Status: open gap, defer até demanda concreta.**

### §2.4 Reliability layer

Todos os 4 taskdog @tools são wrappados por `@circuit_breaker` + `@retry_with_backoff` (`src/agents/reliability.py`):

- **3 attempts** com exponential backoff (0.55s, 0.61s, ...)
- **Graceful FileNotFoundError**: retorna string `"⚠️ taskdog unavailable (binary not found): ..."` em vez de crash
- **Circuit breaker**: após N falhas consecutivas, abre o circuito e short-circuita

### §2.5 E2E test contract

`tests/test_taskdog_harness_e2e.py` (commit `6502326`, 2026-08-31) cobre:

1. `test_ikigai_tools_includes_four_taskdog_tools` — contract test: IKIGAI_TOOLS tem os 4 nomes esperados
2. `test_ikigai_tools_total_count_is_twelve` — drift detector: count não pode mudar (sinal de algo algorítmico re-introduzido)
3. `test_taskdog_create_task_invokes_binary` — invocação direta do @tool (sem LLM)
4. `test_taskdog_list_tasks_returns_at_least_one_task` — listagem funciona
5. `test_taskdog_create_then_complete_roundtrip` — lifecycle completo com `start → done`
6. `test_taskdog_create_task_handles_missing_binary` — graceful failure sem taskdog.exe
7. `test_make_agent_builds_with_taskdog_tools` — smoke test que o agent factory constrói

**Resultado verificado main-session:** 7/7 PASS em Windows box com taskdog v0.23.0.

---

## §3 — Path 2: Mesh SQLite adapter (ALTERNATIVE)

### §3.1 Quando usar

Path 2 é para **cross-fork propagation events** que vão para o data mesh queue (`data/review_queue/`). O adapter materializa o evento em uma row SQLite na store do mesh, **não na store do taskdog**. Convenção: paths 2 é **read-after-write** entre forks (cli/taskdog/upi) — ver `src/mesh/adapters/base.py` Protocol.

### §3.2 Anatomia

```
src/mesh/review_queue/ → PropagationEvent → TaskdogAdapter.propagate()
  → data/taskdog/tasks.db (SQLite) UPSERT on ueid
    → Trigger sync para fork taskdog (best-effort)
```

### §3.3 Componentes

| Componente | Path | Responsabilidade |
|:-----------|:-----|:----------------|
| `TaskdogAdapter` | `src/mesh/adapters/taskdog.py` | Implements `ForkAdapter` Protocol |
| `TASKDOG_DB` | `src/mesh/adapters/taskdog.py` | `data/taskdog/tasks.db` |
| Fields suportados | `src/mesh/adapters/taskdog.py` | `title, due, priority, status, ueid, planned_start, planned_end, actual_end, tags` |
| v1 scope | `src/mesh/adapters/taskdog.py:83-84` | `if event.action.value != "create": return` — apenas create, update/delete/done deferidos para v1.2+ |

**Importante:** Path 2 é **separado** do Path 1. Path 1 escreve direto no taskwarrior store; Path 2 escreve no SQLite mesh store. São stores **independentes**. Path 2 é para **observability cross-fork**, não para gerenciar tasks diretamente.

### §3.4 v1 scope limitation

Per `task_change.py:46-57` + B5.B memory + Phase 3 v1 spec: **mesh v1 = create only**. Outros actions (`update`, `delete`, `done`) deferred para v1.2-v1.4 (gate: system-readiness, não SONHO log counter — ver memory `algorithm-gate-system-readiness-not-sonho-2026-08-29`).

---

## §4 — Path 3: MCP gateway factory (DEFERRED)

### §4.1 Status verificado main-session 2026-08-31

```bash
$ python scripts/mcp_inspect.py
# Advertised tools: 15
# ['ikigai_score', 'ikigai_regime', 'ikigai_phase', 'ikigai_decompose',
#  'ikigai_corrections', 'ikigai_plan_cycle', 'ikigai_checkpoint',
#  'ikigai_sync_vault', 'ikigai_write_tasks', 'ikigai_read_tasks',
#  'ikigai_mesh_show', 'ikigai_task_create', 'ikigai_health',
#  'vault_write', 'vault_read']
# ZERO taskdog_*

$ python -m taskdog_mcp.server
ModuleNotFoundError: No module named 'taskdog_mcp'

$ grep -r "taskdog_" src/ikigai/src/ikigai/gateway/
# src/ikigai/src/ikigai/gateway/clients/taskdog.py:  (factory only)
# src/ikigai/src/ikigai/gateway/downstream.py:        (registration only)
# ZERO advertised tools — registration silently fails when subprocess startup fails
```

### §4.2 Por que está deferred

Path 3 exigiria:

1. **Build do módulo `taskdog_mcp.server`** (Python package separado) que:
   - Lê o fork taskdog HTTP API (`taskdog-server` de doc 21 §2.1)
   - Expõe 4-7 tools MCP stdio (provavelmente: `taskdog_add`, `taskdog_list`, `taskdog_show`, `taskdog_done`)
   - Stdlib-only ou wrap de httpx + mcp ≥1.2,<2
2. **Wire-up no gateway** (`register_default_adapters()` em `downstream.py:25`) — já existe factory `taskdog_adapter()`, só precisa que subprocess startup funcione
3. **E2E test** que faça JSON-RPC handshake com o módulo via stdio (padrão já usado para tuiboard + solverforge-calendar tools em Phase A — memory `phase-a-fork-connection-complete-2026-08-30`)

**Estimativa de esforço:** 12-24h wall-clock (não-trivial: requer instalar package, configurar JSON-RPC handshake, lidar com Windows binary-mode fix já documentado em memory `windows-stdio-binary-mode-fix-2026-08-30`).

**Por que NÃO construir agora:**

1. Path 1 já funciona (E2E 7/7 PASS) — adicionar Path 3 seria duplicação de capability
2. Não há consumer concreto demandando taskdog via MCP (a única chamada a `register_default_adapters()` é silenciosa — o gateway cai no fallback graceful)
3. YAGNI — construir quando houver demanda real de uma interface (fork, agent, ou UI) que precise MCP-form ao invés de subprocess

### §4.3 Quando reviver (recipe)

Recipe para construir Path 3 quando demandado:

```bash
# 1. Criar Python package taskdog_mcp (mirror do tuiboard/solverforge pattern)
mkdir -p src/ikigai/src/ikigai/gateway/clients/taskdog_mcp/
# src/ikigai/src/ikigai/gateway/clients/taskdog_mcp/server.py
#   - Initialize FastMCP server
#   - Register 4 tools: taskdog_add, taskdog_list, taskdog_show, taskdog_done
#   - Each tool wraps HTTP call to http://localhost:8765/tasks (taskdog-server)
#   - JSON-RPC 2.0 over Content-Length-framed stdio

# 2. Wire-up em clients/taskdog.py factory
# Subprocess: ["python", "-m", "taskdog_mcp.server"]
# Use sys.stdin.buffer.readline() (Windows binary-mode fix)
# call_timeout_s=15s (taskdog CLI is fast)

# 3. E2E test
# tests/ikigai/gateway/test_taskdog_mcp_e2e.py
# - Real subprocess + JSON-RPC initialize handshake
# - pytest.skip if MCP server absent
# - Call taskdog_add, expect tool result with id
# - Verify subprocess killed on timeout
```

**Imports canônicos:**

```python
from src.ikigai.src.ikigai.gateway.clients.taskdog import taskdog_adapter
from src.ikigai.src.ikigai.gateway.downstream import register_default_adapters
from src.ikigai.src.ikigai.gateway.gateway import UnifiedMCPGateway
```

---

## §5 — Decision tree (qual path usar?)

```
Quer taskdog via Deep Agent planning?
  ├─ SIM → Path 1 (harness @tool) ✅ CANONICAL
  └─ NÃO → Quer cross-fork propagation?
              ├─ SIM → Path 2 (mesh SQLite) ✅ ALTERNATIVE
              └─ NÃO → Quer taskdog via MCP gateway from external client?
                          └─ SIM → Path 3 (gateway factory) ❌ DEFERRED — build on demand
```

**Default sempre Path 1.** Path 2 só para mesh events. Path 3 só se demandado.

---

## §6 — Anti-patterns a evitar

1. **❌ Adicionar taskdog_* tools no IKIGAI_TOOLS** — já estão lá (4), drift detector enforced
2. **❌ Chamar `taskdog done` sem `taskdog start` antes** — taskdog v0.23.0 enforces lifecycle
3. **❌ Claimar "taskdog MCP connected"** sem verificar com `mcp_inspect.py` primeiro (REFUTED claim de 2026-08-31)
4. **❌ Adicionar `taskdog_complete_task` start logic** sem criar `taskdog_start_task` @tool separado (split ou compound, escolha consciente)
5. **❌ Wire Path 3 sem demanda concreta** — YAGNI, Path 1 já cobre o caso de uso
6. **❌ Misturar Path 1 + Path 2 stores** — são stores independentes; sincronização entre elas é best-effort eventual

---

## §7 — Verification checklist (qualquer mudança em taskdog wiring)

```bash
# 1. IKIGAI_TOOLS contract intacto
cd src/ikigai && python -m pytest tests/test_taskdog_harness_e2e.py -v
# Expected: 7/7 PASS

# 2. ruff clean
python -m ruff check src/ikigai/tests/test_taskdog_harness_e2e.py
# Expected: All checks passed!

# 3. MCP gateway NÃO anuncia taskdog_* (a menos que Path 3 seja revivido)
python scripts/mcp_inspect.py
# Expected: 15 tools, ZERO taskdog_*

# 4. taskdog.exe v0.23.0+ instalado
taskdog --version
# Expected: taskdog 0.23.0 ou superior

# 5. Mesh adapter SQLite existe
ls -la data/taskdog/tasks.db
# Expected: file present (Path 2 store)
```

---

## §8 — Related memories

- [[subagent-fabrication-taskdog-mcp-2026-08-31]] — fabrication original do claim "7 taskdog MCP tools live"
- [[verify-agent-fabricated-failures]] — sempre re-verificar subagent claims em main session
- [[phase-a-fork-connection-complete-2026-08-30]] — Phase A shipped sf_* + tuiboard_* (NOT taskdog_*)
- [[fork-connection-diagnostic-correction-2026-08-30]] — diagnostic correction: scope real é build-missing-server
- [[windows-stdio-binary-mode-fix-2026-08-30]] — sys.stdin.buffer.readline() para MCP stdio em Windows
- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — gate = system readiness, não SONHO counter

---

## §9 — Path 3 archived 2026-09-03

**Decision:** Path 3 MCP server (`src/ikigai/src/mcp_server/taskdog_mcp/`) archived 2026-09-03.
Path 1 stays canonical. Source + tests moved to `archive/legacy-paths/taskdog-mcp-path3/`.

**Why archive:** Path 3 was redundant with Path 1 — it delegated to the same `@tool` functions that
Path 1 already exposes. No concrete consumer required Path 3 over Path 1. YAGNI.

**What was archived:**
- `src/ikigai/src/mcp_server/taskdog_mcp/server.py` (FastMCP server, 4 tools)
- `src/ikigai/src/mcp_server/taskdog_mcp/__init__.py`
- `src/ikigai/tests/test_taskdog_mcp_server.py`

**What survives:** Path 1 (4 `@tool` wrappers in `src/ikigai/src/agents/tools.py`) — 7/7 E2E PASS.

**Recovery:** If a future use case requires taskdog via MCP stdio (distinct from Path 1 harness),
revive from `archive/legacy-paths/taskdog-mcp-path3/` and wire as a separate FastMCP server
entry point. See §4.3 recipe.

---

*3 paths to taskdog — Path 1 canonical, Path 2 alternative, Path 3 archived 2026-09-03*
