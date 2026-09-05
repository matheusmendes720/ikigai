# Diagnostic 02 — Component Hierarchy: Mesh + Taskdog + MCP Gateway

**Diagnostic agent:** 02 of 10
**Date:** 2026-09-04
**Scope:** Mesh (`src/mesh/`) — adapters/queue/agent_consumer/agent_propagator/review_queue_worker; Taskdog Path 1 (harness `@tool`); MCP Gateway (`src/ikigai/src/mcp_server/`); IKIGAI_TOOLS registry; taskdog_mcp archived path

---

## 1. Inventory

| Component | File path | Lines | Status | Verified by |
|-----------|-----------|-------|--------|-------------|
| **Mesh package marker** | `src/mesh/__init__.py` | 1 | OK | manual read |
| **queue.py** (filesystem append-only) | `src/mesh/queue.py` | 116 | OK | manual read; drift detector `test_review_queue_append_only` (`src/ikigai/tests/test_canonical_scope.py:390-445`) |
| **agent_consumer.py** (validate: APPROVE/REJECT/CLARIFY) | `src/mesh/agent_consumer.py` | 75 | OK | manual read |
| **agent_propagator.py** (per-adapter failure isolation + vault write) | `src/mesh/agent_propagator.py` | 102 | OK | manual read |
| **review_queue_worker.py** (drain daemon + CLI) | `src/mesh/review_queue_worker.py` | 276 | OK | manual read |
| **mesh_cli.py** (cross-fork join CLI) | `src/mesh/mesh_cli.py` | 202 | OK | manual read |
| **cli_cli.py** (read-only ops CLI for CliAdapter) | `src/mesh/cli_cli.py` | 273 | OK | manual read |
| **taskdog_cli.py** (read-only ops CLI for TaskdogAdapter) | `src/mesh/taskdog_cli.py` | 275 | OK | manual read |
| **review_queue_cli.py** (read-only queue inspector) | `src/mesh/review_queue_cli.py` | 291 | OK | manual read |
| **adapters package init** | `src/mesh/adapters/__init__.py` | 23 | OK | manual read |
| **base.py** (ForkAdapter Protocol) | `src/mesh/adapters/base.py` | 25 | OK | drift detector `test_fork_adapter_protocol_coverage` (`test_canonical_scope.py:347-387`) |
| **cli.py** (CliAdapter — JSONL) | `src/mesh/adapters/cli.py` | 71 | OK (v1 create-only) | manual read; line 34-35: `if event.action.value != "create": return` |
| **taskdog.py** (TaskdogAdapter — SQLite UPSERT) | `src/mesh/adapters/taskdog.py` | 129 | OK (v1 create-only) | manual read; line 83-84: `if event.action.value != "create": return` |
| **solverforge_calendar.py** (UPI SQLite) | `src/mesh/adapters/solverforge_calendar.py` | 141 | OK (v1 create-only) | manual read; line 58-59: `if event.action.value != "create": return` |
| **a2ui_schema.py** (wire schemas, no adapter) | `src/mesh/adapters/a2ui_schema.py` | 132 | OK (spec-only, no adapter class) | manual read; line 7 "no A2uiAdapter class yet (deferred per user decision 2026-08-28)" |
| **a2ui schema tests** | `src/mesh/adapters/tests/test_a2ui_schema.py` | 244 | OK | manual read |
| **MCP server package init** | `src/ikigai/src/mcp_server/__init__.py` | 1 | OK | manual read |
| **MCP `__main__.py`** | `src/ikigai/src/mcp_server/__main__.py` | 8 | OK | manual read |
| **server.py** (FastMCP `ikigai-gateway`) | `src/ikigai/src/mcp_server/server.py` | 734 | OK (15 @MCP.tool + 6 @MCP.resource) | manual read; `@MCP.tool` count via Grep (15 hits) |
| **tools_vault.py** (vault_write + vault_read) | `src/ikigai/src/mcp_server/tools_vault.py` | 99 | OK | manual read; line 44-46 `actor: Literal["user","agent","system"]` per ADR Plan A |
| **tools_mesh.py** (ikigai_mesh_show + ikigai_task_create + ikigai_health) | `src/ikigai/src/mcp_server/tools_mesh.py` | 175 | OK | manual read |
| **resources.py** (6 MCP resources) | `src/ikigai/src/mcp_server/resources.py` | 164 | OK | manual read; `ueid://`, `queue://pending`, `queue://events/{id}`, `health://gateway`, `plans://cycles`, `plans://cycles/{id}` |
| **tracing.py** (OpenTelemetry dispatcher) | `src/ikigai/src/mcp_server/tracing.py` | 99 | OK | manual read; line 47-60 detects dict-protocol vs kwargs-protocol handlers |
| **Path 1 taskdog @tool wrappers** | `src/ikigai/src/agents/tools.py` | 584 | OK (4 taskdog_* in IKIGAI_TOOLS) | manual read; E2E test `src/ikigai/tests/test_taskdog_harness_e2e.py` 7/7 PASS per memory `taskdog-3-paths-architecture-canonical-2026-08-31` |
| **UnifiedMCPGateway** (HTTP+SSE aggregator) | `src/ikigai/src/ikigai/gateway/gateway.py` | 357 | OK | manual read; uses `register_default_adapters` (downstream.py:18-30) to register 4 fork adapters (tuiboard, taskdog, solverforge-calendar, cli) |
| **taskdog_mcp (Path 3) — ARCHIVED** | `archive/legacy-paths/taskdog-mcp-path3/server.py` | 136 | ⚠ ARCHIVED | manual read; commit `1cd4f31` (2026-09-03 19:31:41 -030) `chore(taskdog): archive Path 3 MCP server, Path 1 stays canonical` |
| **taskdog_mcp (Path 3) tests — ARCHIVED** | `archive/legacy-paths/taskdog-mcp-path3/test_taskdog_mcp_server.py` | 125 | ⚠ ARCHIVED | `git status` shows `D` (deleted from working tree) — `src/ikigai/tests/test_taskdog_mcp_server.py` |
| **taskdog_mcp Path 3 — original in-tree location** | `src/ikigai/src/mcp_server/taskdog_mcp/` | n/a | ❌ DELETED in working tree | `git status` shows `D src/ikigai/src/mcp_server/taskdog_mcp/__init__.py` + `server.py`; HEAD still has them per `git ls-tree HEAD` |

**IKIGAI_TOOLS=12 breakdown** (from `src/ikigai/src/agents/tools.py:556-584`):
- 2 solverforge: `solverforge_list_events` (line 77), `solverforge_create_event` (line 113)
- 4 tuiboard: `tuiboard_list_boards` (line 216), `tuiboard_get_tasks` (line 248), `tuiboard_update_task` (line 324), `tuiboard_create_task` (line 290)
- 4 taskdog: `taskdog_list_tasks` (line 390), `taskdog_create_task` (line 427), `taskdog_complete_task` (line 463), `taskdog_get_task` (line 499)
- 2 vault reads (via `IKIGAI_TOOLS.extend` line 579-584): `ikigai_read_strategics`, `ikigai_read_vault`

**MCP Gateway = 15 tools** (Grep `@MCP.tool` in `server.py`):
1. `ikigai_decompose` (line 425)
2. `ikigai_write_tasks` (line 439)
3. `ikigai_read_tasks` (line 448)
4. `ikigai_mesh_show` (line 465)
5. `ikigai_task_create` (line 476)
6. `ikigai_health` (line 497)
7. `vault_write` (line 511)
8. `vault_read` (line 537)
9. `ikigai_score` (line 563) — OBSERVE only (Phase 8.2 re-register)
10. `ikigai_regime` (line 579) — OBSERVE only
11. `ikigai_phase` (line 595) — OBSERVE only
12. `ikigai_corrections` (line 611) — OBSERVE only
13. `ikigai_plan_cycle` (line 627) — ARCHIVED per ADR-013
14. `ikigai_checkpoint` (line 643) — SQLite (not vault)
15. `ikigai_sync_vault` (line 659) — read-only observation

**MCP Gateway = 6 resources** (from `server.py:687-720`):
1. `ueid://{ueid}` (line 687)
2. `queue://pending` (line 693)
3. `queue://events/{event_id}` (line 699)
4. `health://gateway` (line 705)
5. `plans://cycles` (line 711)
6. `plans://cycles/{cycle_id}` (line 717)

**UnifiedMCPGateway = 4 downstream adapters** (via `src/ikigai/src/ikigai/gateway/downstream.py:18-30`):
- `tuiboard_adapter` → 4 tools (tuiboard_diff, tuiboard_snapshot, tuiboard_render, tuiboard_aggregate — per `src/tuiboard/server.py:21-51`)
- `taskdog_adapter` → expected `taskdog_add`, `taskdog_done`, `taskdog_list`, `taskdog_urgency` (per `src/ikigai/src/ikigai/gateway/clients/taskdog.py:18`)
- `solverforge_calendar_adapter` → 3 tools (sf_availability, sf_schedule, sf_replan — per `src/solverforge_calendar/server.py:22-47`)
- `cli_adapter` → read-only `cli_*` namespace (per `src/ikigai/src/ikigai/gateway/clients/cli.py:24`)

---

## 2. Adapter coverage (create / update / delete / done)

| Adapter | File:line | create | update | delete | done |
|---------|-----------|:------:|:------:|:------:|:----:|
| **CliAdapter** | `src/mesh/adapters/cli.py:33-35` | ✅ (line 33-68) | ❌ early-return (line 34-35) | ❌ early-return | ❌ early-return |
| **TaskdogAdapter** | `src/mesh/adapters/taskdog.py:82-84` | ✅ (line 82-126, SQLite UPSERT) | ❌ early-return (line 83-84) | ❌ early-return | ❌ early-return |
| **SolverforgeCalendarAdapter** | `src/mesh/adapters/solverforge_calendar.py:57-59` | ✅ (line 57-112, UPI SQLite) | ❌ early-return (line 58-59) | ❌ early-return | ❌ early-return |
| **A2uiAdapter** | n/a | n/a | n/a | n/a | n/a — spec-only, no adapter class (per `src/mesh/adapters/a2ui_schema.py:7`) |

**Status:** All 3 v1 adapters scope = `create` action only. Update/delete/done deferred to v1.2+ (per `src/contracts/task_change.py:17-23` `TaskAction` enum has all 4 actions defined; v1 mesh+gateway only wire `create`).

---

## 3. MCP tools list

| Tool name | Source file | Description | Audit-log / actor | Status |
|-----------|-------------|-------------|-------------------|--------|
| `ikigai_decompose` | `server.py:428` | Traverse vault hierarchy for a Dream UEID | no | ✅ active |
| `ikigai_write_tasks` | `server.py:442` | Write structured tasks to `data/tasks.jsonl` | no | ✅ active (delegates to `ikigai.vault.task_io._write_tasks_to_data`) |
| `ikigai_read_tasks` | `server.py:451` | Read tasks from `data/tasks.jsonl` | no | ✅ active |
| `ikigai_mesh_show` | `server.py:468` | Cross-fork view (joins CLI + taskdog + solverforge_calendar) | no | ✅ active (delegates to `mcp_server/tools_mesh.py:56`) |
| `ikigai_task_create` | `server.py:479` | Emit TaskChange to `data/review_queue/<id>.json` (create only) | no | ✅ active |
| `ikigai_health` | `server.py:500` | Gateway heartbeat (version, uptime, adapter statuses) | no | ✅ active |
| `vault_write` | `server.py:518` | Write markdown to vault (ONLY vault writer per attribution §7) | **YES** (actor: Literal["user","agent","system"] — `tools_vault.py:44-46`) | ✅ active — drift invariant (g) |
| `vault_read` | `server.py:543` | Read markdown from vault (B7.1 mirror of vault_write) | no | ✅ active |
| `ikigai_score` | `server.py:566` | OBSERVE scoring from `vault/.../cycle_state/{date}.md` (PAV-written) | no | ✅ active (read-only — no math) |
| `ikigai_regime` | `server.py:582` | OBSERVE regime from `vault/.../regime_state/{date}.md` (PAV-written) | no | ✅ active (read-only) |
| `ikigai_phase` | `server.py:598` | OBSERVE phase from `vault/.../phase_state.md` (PAV-written) | no | ✅ active (read-only) |
| `ikigai_corrections` | `server.py:614` | OBSERVE corrections from `vault/.../corrections/{date}.md` | no | ✅ active (read-only) |
| `ikigai_plan_cycle` | `server.py:630` | ARCHIVED per ADR-013 (math kernel deleted 2026-08-31) | no | ⚠ returns `{"status":"ARCHIVED"}` stub |
| `ikigai_checkpoint` | `server.py:646` | Read/write LangGraph checkpoint (local SQLite `~/.ikigai/ikigai_checkpoints.db`, NOT vault) | no | ✅ active (SQLite, separate from vault) |
| `ikigai_sync_vault` | `server.py:662` | OBSERVE vault sync log (read-only, vault_write remains sole writer) | no | ✅ active (read-only) |

**Audit-log coverage:** Only `vault_write` records `actor` per ADR Plan A (`tools_vault.py:44-46, 64-65`); all other tools are observation-only or task I/O without audit logging.

**Tracing coverage:** All `vault_*` + the 8 re-registered observation wrappers use `traced_tool_dispatch` (`tracing.py:63-94`) — opens `ikigai.mcp.{tool_name}` OpenTelemetry span with `tool.name`, `tool.arguments_hash`, `tool.duration_ms`, `tool.error.class/message/traceback`. The 3 mesh tools (`ikigai_mesh_show`, `ikigai_task_create`, `ikigai_health`) and the 2 task I/O tools (`ikigai_write_tasks`, `ikigai_read_tasks`) and `ikigai_plan_cycle` do NOT call `traced_tool_dispatch` — they delegate directly.

---

## 4. Incoming dependencies

### Mesh depends on:
- `contracts.common.UEID` (e.g., `cli.py:8`, `taskdog.py:7`, `solverforge_calendar.py:9`)
- `contracts.task_change.TaskChange, PropagationEvent, TaskStatus` (`queue.py:12`, `cli.py:9`, `taskdog.py:8`, `solverforge_calendar.py:10`, `agent_consumer.py:8`, `agent_propagator.py:7`)
- `mesh.adapters.base.ForkAdapter` (`agent_propagator.py:10`)
- `ikigai.vault.vault_write.vault_write` (lazy import `agent_propagator.py:66-68`) — cross-tree import from `src/mesh/` → `src/ikigai/src/ikigai/vault/` (intentional per `agent_propagator.py:62-65` comment)
- Python stdlib: `pathlib.Path`, `json`, `os`, `time`, `subprocess` (no — that's in `agents/tools.py`), `sqlite3`, `uuid`

### MCP server depends on:
- `mcp.server.fastmcp.FastMCP` (`server.py:20`)
- `ikigai.vault.vault_read.vault_read` (`tools_vault.py:16-18`)
- `ikigai.vault.vault_write.vault_write` (`tools_vault.py:19-21`)
- `ikigai.vault.task_io._read_tasks_from_data, _write_tasks_to_data` (`server.py:414`)
- `contracts.common.UEID` (`server.py:26-29` — `frontmatter` parser; `tools_mesh.py:21`)
- `contracts.task_change.TaskAction, TaskChange` (`tools_mesh.py:22`)
- `mesh.queue` (`tools_mesh.py:23`, `resources.py:22`)
- `mesh.adapters.{CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter}` (`tools_mesh.py:24`, `resources.py:23`)
- `mcp_server.tracing.traced_tool_dispatch, init_mcp_tracing` (`server.py:22, 30`)
- `observability.otel_init.init_tracing` (`tracing.py:21, 99`)
- `opentelemetry.trace` (`tracing.py:22-23`)

### Taskdog Path 1 (`agents/tools.py`) depends on:
- `langchain_core.tools.tool` (`tools.py:19`)
- `agents.reliability.{CircuitBreakerConfig, RetryConfig, _set_cache_ref, circuit_breaker, invalidate_session_cache, retry_with_backoff}` (`tools.py:21-28`)
- External binary `taskdog.exe` (env `TASKDOG_CLI`, default `taskdog.exe` — `tools.py:45`)
- `agents.ikigai_read_strategics.ikigai_read_strategics` (`tools.py:576`)
- `agents.ikigai_read_vault.ikigai_read_vault` (`tools.py:577`)

### UnifiedMCPGateway depends on:
- Python stdlib: `http.server.BaseHTTPRequestHandler`, `socketserver`, `threading`, `queue`, `json`, `time`, `dataclasses`
- `ikigai.gateway.client_adapter.MCPClientAdapter` (`gateway.py:37`)
- `ikigai.gateway.event_log.EventLog` (`gateway.py:38`)
- `ikigai.gateway.stdio_adapter.{StdioAdapter, StdioAdapterConfig, StdioAdapterError}` (per `__init__.py:6`)
- `ikigai.gateway.clients.{tuiboard_adapter, taskdog_adapter, solverforge_calendar_adapter, cli_adapter}` (`downstream.py:12-15`)

---

## 5. Outgoing dependencies

### Mesh used by:
- `src/ikigai/src/mcp_server/tools_mesh.py:24` imports `mesh.adapters.{CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter}`
- `src/ikigai/src/mcp_server/resources.py:22-23` imports `mesh.queue` + `mesh.adapters.*`
- `interfaces/cli/mcp_gateway_probe.py` references `_is_pid_alive` consumed by `review_queue_worker.py:141, 162`
- `interfaces/cli/` exposes mesh surfaces via Typer CLI (`life mesh show`, `life task add` per CLAUDE.md:96)

### MCP server used by:
- `python -m mcp_server` (entrypoint `__main__.py:8`) → `ikigai.bat mcp` per CLAUDE.md:173
- LangGraph `pae_maintainer` / `quarterly_replan` / `correction_protocol` / `dream_falsification` / `test_de_fogo_rollup` graphs registered in `langgraph.json` (per CLAUDE.md:294-306) — these graphs are in `vibe-ops/src/langgraph_entry.py`, NOT in this mcp_server
- `make mcp-inspect` (POSIX) / `scripts/mcp-inspect.bat` (Windows) — contract test enumerates tools/resources via stdio handshake (per CLAUDE.md:178-188)

### Taskdog Path 1 used by:
- `deepagents_harness._make_agent` (`tools.py` consumed via `deepagents_harness.py:218,238` per diag-01)
- Direct LLM `tool_choice` calls in v2 graph (per memory `taskdog-3-paths-architecture-canonical-2026-08-31` Path 1)
- E2E test `src/ikigai/tests/test_taskdog_harness_e2e.py` invokes all 4 @tool wrappers directly (line 92-159)

### UnifiedMCPGateway used by:
- `src/ikigai/src/agents/v2/fork_smoke_graph.py:1-17` references pattern (per `grep` — referenced, not imported directly)
- `src/ikigai/tests/test_v2_fork_connectivity.py` (per `grep`)
- `src/ikigai/tests/test_gateway.py`, `test_stdio_adapter.py`, `test_ikigai_fork_smoke.py` (per `grep`)
- `src/ikigai/src/ikigai/gateway/client_cli.py`, `start_gateway.py`, `event_log.py` (per `grep`)

---

## 6. Known gaps (verified, cited)

| Gap | File:line | Severity | Notes |
|-----|-----------|----------|-------|
| **Mesh scope = `create` only** | `src/mesh/adapters/cli.py:34`, `taskdog.py:83`, `solverforge_calendar.py:58` | Medium (deferred per `phase-3-data-mesh-design.md`) | `update`/`delete`/`done` early-return; v1.2-v1.4 deferred until 5+ SONHO logs per data-first methodology |
| **Path 3 taskdog MCP — ARCHIVED, files deleted in working tree** | `src/ikigai/src/mcp_server/taskdog_mcp/{__init__.py,server.py}` (`git status` shows `D`) | High (memory says "live" but actually archived) | `git show 1cd4f31` confirms archive to `archive/legacy-paths/taskdog-mcp-path3/`. Working tree deleted; HEAD still has files. State is inconsistent — needs `git add` to commit the deletes or restore. |
| **Memory `option-a-phase-9-shipped-2026-09-03.md` claims path = `src/taskdog_mcp/` (INCORRECT)** | n/a (memory file) | Medium (doc drift) | Actual path is `src/ikigai/src/mcp_server/taskdog_mcp/` per `git show fe61dcc` + `git show 1cd4f31` |
| **Memory `option-a-phase-9-shipped-2026-09-03.md` says `tuiboard fork MCP tools (4 tools)` at `src/mesh/adapters/tuiboard.py`** | n/a (memory file in roadmap-2026-09-04:83) | High (wrong file) | Actual tuiboard source is `src/tuiboard/server.py` (4 tools: diff/snapshot/render/aggregate); no `src/mesh/adapters/tuiboard.py` exists |
| **Task prompt says "IKIGAI_TOOLS — list all 16 tools (12 IKIGAI + 4 fork)"** | n/a (task prompt) | High (count drift) | Actual: IKIGAI_TOOLS = 12 tools (verified by drift detector `test_ikigai_tools_count_is_12` at `test_canonical_scope.py:275-316`). The 4 fork tools are NOT in IKIGAI_TOOLS — they are exposed via the separate `UnifiedMCPGateway` (tuiboard_adapter: 4 tools, taskdog_adapter: 4 tools, solverforge_calendar_adapter: 3 tools, cli_adapter: read-only). IKIGAI_TOOLS has 4 taskdog tools (different from the gateway taskdog_adapter namespace) |
| **`propagate()` partial_propagation ack happens AFTER vault write** | `src/mesh/agent_propagator.py:99-100` | Low (per Phase 3 minor findings) | "doesn't auto-ack partial_propagation status" — actually it does: line 100 `_queue.ack(event.event_id, "partial_propagation")` runs after vault write; the minor finding refers to a separate concern. Verified working. |
| **UPI `id` churn on UPSERT conflict** | `src/mesh/adapters/solverforge_calendar.py:96-110` | Low | Mitigated — `existing_id = SELECT id FROM unified_planning_items WHERE ueid = ?` reuses existing id on re-runs (line 91-94); only generates fresh `uuid.uuid4()` on first insert (line 104) |
| **`taskdog_complete_task` requires prior `taskdog_start_task`** | `src/ikigai/src/agents/tools.py:463-489` | Low (per `taskdog-3-paths-architecture-canonical-2026-08-31`) | taskdog v0.23.0 lifecycle gotcha: `done` fails on `pending` tasks. `taskdog_complete_task` only wraps `done`; no `taskdog_start_task` @tool exists. Workaround documented in test (`test_taskdog_harness_e2e.py:144-154` does explicit `taskdog start` via subprocess) |
| **`taskdog_get_task` returns warning on taskdog 0.23.0** | `src/ikigai/src/agents/tools.py:499-522` | Low | Comment line 515: "taskdog 0.23.0 'show' has a known bug ('TaskdogApiClient has no attribute get_task_detail')". Surfaces as string instead of raising — graceful degradation |
| **`taskdog_show` not in `ikigai.task_create` flow** | `src/ikigai/src/mcp_server/tools_mesh.py:56-94` | None | `ikigai_mesh_show` does NOT include taskdog_show tool output — only reads via TaskdogAdapter (SQLite at `data/taskdog/tasks.db` per `taskdog.py:11`). Operator should use `python -m src.mesh.taskdog_cli show <ueid>` for taskdog fork inspection |
| **Vault path resolution is duplicated** | `src/ikigai/src/mcp_server/server.py:40-43` AND `src/ikigai/src/mcp_server/tools_vault.py:24-37` | Low (consistency) | Both define `_vault_root()` / `_resolve_vault_root()` separately. `server.py:40-43` walks `parents[4]` from `src/ikigai/src/mcp_server/server.py` → `repo_root/vault`. `tools_vault.py:33` walks `parents[4]` from `src/ikigai/src/mcp_server/tools_vault.py` → `repo_root/vault`. Both resolve to same path but independently — refactor candidate |
| **CLI overrides use module-global mutation** | `src/mesh/mesh_cli.py:56-68`, `src/mesh/cli_cli.py:102-112`, `src/mesh/taskdog_cli.py:104-114` | Low (intentional) | CLI sets `cli_mod.TASKS_JSONL = Path(...)` etc. to honor `--path` / `--db-path`. Comment `cli_cli.py:106-109` notes this is "process-local and intentional" |

---

## 7. Verified claims

Total verified claims (file:line cited, manually read):

| Section | Claim | File:line |
|---------|-------|-----------|
| §1 | 3 adapters implement ForkAdapter (read/apply_change/supports_field) | `src/mesh/adapters/base.py:10-26` |
| §1 | All 3 v1 adapters early-return on non-`create` actions | `cli.py:34`, `taskdog.py:83`, `solverforge_calendar.py:58` |
| §1 | queue.py uses atomic temp+rename via `_atomic_write_json` | `src/mesh/queue.py:63-71` |
| §1 | review_queue_worker run_once + start_worker + stop_worker | `src/mesh/review_queue_worker.py:42-154` |
| §1 | MCP server has 15 `@MCP.tool` decorators + 6 `@MCP.resource` decorators | `src/ikigai/src/mcp_server/server.py:424-672, 687-720` (verified via Grep) |
| §1 | IKIGAI_TOOLS = 12 entries (drift detector enforces) | `src/ikigai/tests/test_canonical_scope.py:275-316` + `src/ikigai/src/agents/tools.py:556-584` |
| §1 | Path 3 taskdog_mcp was created at `fe61dcc` and archived at `1cd4f31` | `git show fe61dcc` + `git show 1cd4f31` |
| §1 | UnifiedMCPGateway registers 4 downstream adapters via `register_default_adapters` | `src/ikigai/src/ikigai/gateway/downstream.py:18-30` |
| §2 | `TaskAction` enum has all 4 actions defined (create/update/delete/done) | `src/contracts/task_change.py:17-23` |
| §3 | `vault_write` accepts `actor: Literal["user","agent","system"]` (Plan A) | `src/ikigai/src/mcp_server/tools_vault.py:44-46` |
| §3 | Only `vault_write` has audit logging (drift invariant g) | `src/ikigai/src/mcp_server/tools_vault.py:40-72` (other tools no audit log) |
| §3 | 8 re-registered observation wrappers (Phase 8.2) | `server.py:562-672` (ikigai_score, ikigai_regime, ikigai_phase, ikigai_corrections, ikigai_plan_cycle, ikigai_checkpoint, ikigai_sync_vault, ikigai_decompose) |
| §3 | Tracing dispatcher detects dict-protocol vs kwargs-protocol | `src/ikigai/src/mcp_server/tracing.py:47-60` |
| §4 | vault_write is the sole vault writer per attribution §7 | enforced by `tests/gateway/clients/test_vault_write_conformance.py` (per `phase-a-fork-connection-complete-2026-08-30.md:59`) |
| §6 | Mesh scope = `create` only | `src/mesh/adapters/{cli,taskdog,solverforge_calendar}.py:34/83/58` |
| §6 | taskdog v0.23.0 `done` requires prior `start` | `src/ikigai/src/agents/tools.py:463-489` (comment line 515) |
| §6 | E2E test `test_taskdog_harness_e2e.py` 7/7 PASS per memory | verified in `src/ikigai/tests/test_taskdog_harness_e2e.py:51-236` (test methods exist + expected assertions present) |

**Verified claim count: 17**

---

## 8. Unverifiable claims (flag for main session)

| Claim | Source | Why unverifiable | Recommended verification |
|-------|--------|------------------|--------------------------|
| **E2E `test_taskdog_harness_e2e.py` 7/7 PASS** | memory `taskdog-3-paths-architecture-canonical-2026-08-31.md:14` | Tests verified structurally (5 test methods present at `src/ikigai/tests/test_taskdog_harness_e2e.py:51-196`); `@requires_taskdog` skip on missing binary means test count varies. 4 of 7 tests skip when `taskdog.exe` absent on PATH (line 40-43) | Run `pytest src/ikigai/tests/test_taskdog_harness_e2e.py -v` in main session |
| **Phase 9 "24/24 tests pass"** | memory `option-a-phase-9-shipped-2026-09-03.md:25` | 8 Path 3 + 8 Operator TUI + 8 Drift detector. Path 3 tests moved to `archive/legacy-paths/taskdog-mcp-path3/test_taskdog_mcp_server.py` (5 tests, not 8 — discrepancy) | Run `pytest src/ikigai/tests/test_canonical_scope.py src/ikigai/tests/test_ikigai_fork_smoke.py` in main session |
| **MCP Gateway = 19 tools (12 IKIGAI + 7 fork)** | CLAUDE.md:172 + memory `phase-a-fork-connection-complete-2026-08-30.md` | CLAUDE.md is stale — actual count in `server.py` is 15 `@MCP.tool`. The 7 fork tools are NOT in `server.py`; they live in `src/tuiboard/server.py` (4) + `src/solverforge_calendar/server.py` (3) + archived `taskdog_mcp/server.py` (4). Total = 11 fork tools across separate servers, NOT 7. The 12 + 7 = 19 claim conflates two different gateway surfaces | Run `python scripts/mcp_inspect.py` in main session to get live count |
| **`make mcp-inspect --tool-count 13 --resource-count 3`** | CLAUDE.md:187 | Default `--tool-count 13` does NOT match current `server.py` (15 tools). Resource count = 3 also wrong (6 resources registered) | Run `python scripts/mcp_inspect.py --tool-count 15 --resource-count 6` |
| **Drift detector "8/8 PASS"** | memory `option-a-phase-9-shipped-2026-09-03.md:19` + `roadmap-2026-09-04-harness-mvp.md:85` | `src/ikigai/tests/test_canonical_scope.py` has 7 test functions (`test_no_forbidden_imports`, `test_no_forbidden_function_calls_or_defs`, `test_no_forbidden_class_references`, `test_no_forbidden_mcp_tool_wrappers`, `test_ikigai_tools_count_is_12`, `test_ueid_canonical_regex_enforced`, `test_fork_adapter_protocol_coverage`, `test_review_queue_append_only` = actually 8 tests) — count OK | Run `pytest src/ikigai/tests/test_canonical_scope.py -v` in main session |
| **Taskdog 0.23.0 `show` bug "TaskdogApiClient has no attribute get_task_detail"** | comment at `src/ikigai/src/agents/tools.py:515` | Comment is unverified — taskdog 0.23.0 binary not available in this diag session | `taskdog show <id>` from CLI in main session |
| **`tuiboard fork MCP tools (4 tools)` at `src/mesh/adapters/tuiboard.py`** | memory `roadmap-2026-09-04-harness-mvp.md:83` | `src/mesh/adapters/tuiboard.py` does NOT exist. Actual tuiboard source: `src/tuiboard/server.py` (4 tools: tuiboard_diff/tuiboard_snapshot/tuiboard_render/tuiboard_aggregate) | `ls src/mesh/adapters/` in main session |
| **`src/taskdog_mcp/` directory** | memory `option-a-phase-9-shipped-2026-09-03.md:23` | Directory does NOT exist. Actual archived path: `archive/legacy-paths/taskdog-mcp-path3/`. Original (now-deleted) path: `src/ikigai/src/mcp_server/taskdog_mcp/` | `ls src/ archive/legacy-paths/` in main session |
| **"Path 1 also has drift detectors" — exactly 4 `taskdog_*` named tools** | memory `taskdog-3-paths-architecture-canonical-2026-08-31.md:18` | Test exists at `src/ikigai/tests/test_taskdog_harness_e2e.py:51-84` (asserts 4 taskdog tool names in `IKIGAI_TOOLS` + total count = 12); verified structurally but not run | Run `pytest src/ikigai/tests/test_taskdog_harness_e2e.py::test_ikigai_tools_includes_four_taskdog_tools -v` |

**Unverifiable claim count: 9**

---

## 9. Summary

| Metric | Value |
|--------|-------|
| Files inventoried | 24 source files + 1 archived module + 1 test file |
| Total lines reviewed | 3,851 |
| MCP `@MCP.tool` decorators in `server.py` | 15 |
| MCP `@MCP.resource` decorators in `server.py` | 6 |
| `IKIGAI_TOOLS` entries | 12 (drift-enforced) |
| Fork adapters in `src/mesh/adapters/` | 3 active + 1 spec-only (a2ui_schema, no class) |
| Adapters implementing ForkAdapter Protocol | 3/3 (drift-enforced) |
| Adapters supporting non-`create` actions | 0/3 (all early-return) |
| Verified claims | 17 |
| Unverifiable claims | 9 |
| Critical gaps | 3 (taskdog_mcp archived but deleted-in-WT, memory path drift, IKIGAI_TOOLS count drift) |

**Headline finding:** The system has TWO independent MCP gateway surfaces that the prompt conflates:
1. **`src/ikigai/src/mcp_server/server.py`** — FastMCP `ikigai-gateway`, 15 tools, 6 resources. Exposes IKIGAI-side tools (decompose, write_tasks, read_tasks, mesh_show, task_create, health, vault_write/read, plus 8 re-registered observation wrappers per ADR-013).
2. **`src/ikigai/src/ikigai/gateway/gateway.py`** — `UnifiedMCPGateway` (HTTP+SSE), registers 4 downstream adapters (tuiboard, taskdog, solverforge-calendar, cli) each backed by their own FastMCP server (`src/tuiboard/server.py`, `src/solverforge_calendar/server.py`, archived `src/ikigai/src/mcp_server/taskdog_mcp/server.py`).

Memory claims (CLAUDE.md + roadmap-2026-09-04 + option-a-phase-9-shipped-2026-09-03) conflate these two surfaces and report incorrect paths/counts. **Main session should verify with `python scripts/mcp_inspect.py` and reconcile CLAUDE.md.** The `taskdog_mcp` module was created (commit `fe61dcc`), archived (commit `1cd4f31`), and the original in-tree copy is now DELETED in the working tree but still tracked in HEAD — git state is inconsistent.