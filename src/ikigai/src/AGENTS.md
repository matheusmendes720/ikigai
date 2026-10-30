# AGENTS.md — src/ikigai/src

## OVERVIEW
Runtime source of the IKIGAI subpackage: 6 Poetry packages (`agents`, `chat`, `mcp_server`, `observability`, `strategics`, `plugins`) plus `gateway_client.py` and `ikigai_wrapper.py`. Earned its file at score 16 — 167 files, 160 Python, 767 symbols, 353 import sites in 72 repo files.

## STRUCTURE
```
src/ikigai/src/
├── agents/            # agent layer: v2 graph, Paperclip, tool registry
│   ├── v2/            # LangGraph v2: graph, subgraph, checkpoint, memory, prompts, skills
│   ├── paperclip/     # spec-driven orchestrator: graph, policy, router, persistence
│   └── paperclip_dynamic/  # dynamic-workflow variant, fixed 3 subagent slots
├── mcp_server/        # FastMCP surfaces: server.py + taskdog_tools.py
├── chat/              # thread reader/writer over the vault
├── observability/     # OTel init + error capture
├── plugins/           # paperclipai_bridge (FastAPI)
├── strategics/        # read-only strategics loader
├── gateway_client.py  # typed singleton over the MCP gateway handle
└── ikigai_wrapper.py  # langgraph dev loader (absolute imports only)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| v2 graph topology | `agents/v2/graph.py` | `NODES` = 16 nodes, `observe` → `gantt_suggest`; `_build_v2_graph` wires 16 conditional edges |
| Sub-agent dispatch | `agents/v2/subgraph.py` | largest file (749 L); `dispatch_sub_agents` + `_invoke_subagent` |
| Checkpointing | `agents/v2/checkpoint.py` | `IkigaiCheckpointer`, `build_thread_id`; `checkpoint.py` re-defines `build_thread_id` etc. as wrappers **on purpose** — a drift test greps those names |
| Memory store | `agents/v2/memory_{schema,write,read}.py` | SQLite tables in `data/ikigai_checkpoints.db` |
| Prompt renderers | `agents/v2/prompts/` | 15 renderer modules of 88–90 L each — near-identical copies of one template; change one, change all |
| Algorithm tuning | `agents/v2/prompts/algorithm_constants.json` | single source of truth; read via `load_constants.get()` only |
| Skills | `agents/v2/skills/` | `SKILL_REGISTRY`; each skill exposes `SKILL_NAME` + `propose()` and emits a `Proposal` — never executes |
| Meta-plan chain | `agents/v2/nodes/meta_plan/` | `classify_intent` → `fetch_context` → `generate_proposal`; all read-only, no LLM |
| Tool registry | `agents/tools.py` | `IKIGAI_TOOLS` = 10 external-data tools + 2 vault reads. `cli_native_fallback` is **not** registered |
| Retry / circuit breaker | `agents/reliability.py` | `retry_with_backoff`, `circuit_breaker`, `invalidate_session_cache` — shared by all 4 tool modules |
| Paperclip gates | `agents/paperclip/policy.py` | `CostGate`, `WallClockGate` (fail-**OPEN**), `RiskGate` (fail-**CLOSED**) — a deliberate asymmetry |
| Paperclip adapters | `agents/paperclip/agents/` | `claude`/`omo`/`openclaw`/`pi` are real; `hermes`/`mcode` are stubs |
| MCP gateway surface | `mcp_server/server.py` | `FastMCP("ikigai-gateway")`; `TOOLS` is built from the private `MCP._tool_manager._tools.values()` |
| Taskdog tools | `mcp_server/taskdog_tools.py` | separate `FastMCP(name="taskdog")`, 26 `taskdog_*` tools |
| Vault tools | `mcp_server/tools_vault.py` | `vault_write` / `vault_read` — the only vault writer per ADR-012 |
| Mesh tools | `mcp_server/tools_mesh.py` | v1 scope is `create` action only |
| HTTP bridge | `plugins/paperclipai_bridge/main.py` | uvicorn on `127.0.0.1:8741` (`LIFE_PAPERCLIP_BRIDGE_PORT`) |

## CONVENTIONS
- **Node signature is fixed**: every node is a plain `def node(state: XStateDict) -> dict[str, Any]`, wrapped in `_safe_node` so exceptions land in the error channel instead of crashing the graph. `paperclip/nodes/__init__.py` states this rule explicitly.
- **`if False:` is the sanctioned way to park forbidden/legacy code** (11 occurrences in 5 files) — it keeps AST drift scanners from seeing live `FunctionDef`/`Import` nodes. Do not "clean it up".
- **No `DEFAULT_*` tuning constants under `agents/v2/*.py`** (ADR-019). Values live in `algorithm_constants.json`.
- **`from __future__ import annotations` in every module** except the 4 `__init__.py` files and the 2 legacy-reference files (their bodies are inside `if False:`).
- **State is a `TypedDict`** with `Annotated[..., operator.add]` reducers and `NotRequired` for optional branches.
- **Local imports break cycles** — `subgraph.py` imports `NODES` from `.graph` locally; `mcp_server/server.py` and `taskdog_tools.py` import mid-file under `# noqa: E402` on purpose (moving them changes import-time side effects).
- **Logger name is inconsistent by design**: 14 modules use `log =`, 7 use `logger =`. Both accepted.
- **Docstring template**: purpose → `Public API:` → `Drift invariants enforced:` → `Architectural reference:` (ADR ids + rule ids) → `Companion modules:`.
- **UEID regex is duplicated byte-for-byte in 3 files** (`v2/subagent_types.py`, `v2/checkpoint_thread_id.py`, `v2/subgraph.py`) — drift-enforced, change all three.

## ANTI-PATTERNS
- **NEVER** import `sys_ikigai.core.scoring`, `ikigai.core.heuristics`, or `cybernetics.daily_loop` from the agent layer (ADR-013 planner-only). The 8 `ikigai_*` tools in `mcp_server/server.py` are **stubs** returning `{"stub": True}` — they exist only to keep the wire surface aligned with the bridge.
- **NEVER** register `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections`, `ikigai_plan_cycle`, `ikigai_checkpoint`, `ikigai_sync_vault` as `@MCP.tool` — forbidden by drift test.
- **NEVER** call raw `vault_write` from `agents/v2/nodes/proposal_executor.py`; go through `wrap_vault_write`. `execute_proposal` must refuse any `approval_state != "approved"`.
- **NEVER** auto-execute writes from `nodes/dep_graph.py`, `nodes/gantt_suggest.py`, `nodes/tag_propagation.py` — they compute a proposal only.
- **NEVER** propagate error-channel fields to children (ADR-026 S2.4) — a parent's `error_type` is never set by a child failure.
- **NEVER** import `v2/tools_legacy_reference.py` or `v2/harness_legacy_reference.py` — read-only reference copies.
- **NEVER** re-sort the `gantt_suggest` batch alphabetically; the heap-pop order is load-bearing.
- **NEVER** let an agent adapter escape its worktree cwd (`paperclip/agents/base.py`).

## NOTES
- `agents/v2/__init__.py` monkey-patches `anthropic.OverloadedError` at import time (browser-use pins `anthropic==0.76.0`, `langchain_anthropic` 1.7.2 needs ≥0.120.0). Every v2 entry point must import the package first.
- `v2/__init__.py` is also a **read-only parallel branch**: all math calls were replaced with prompt-chain stubs.
- `strategics/loader.py` and `mcp_server/resources.py` are read-only by contract; `paperclip/persistence.py` writes run snapshots atomically (tmp + rename) with a `MAX_RUNS` GC cap.
- `agents/paperclip_dynamic/graph.py` has a **hard-coded** 3-slot fan-out (`SUBAGENT_SLOT_NAMES`) — the planner caps at that count and drops extras with a warning.
