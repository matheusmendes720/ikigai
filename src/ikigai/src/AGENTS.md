# AGENTS.md — `src/ikigai/src/`

**Score 11 (167 files, 98% code, 6 subdirs, 492 symbols, 156 exports, imported by 95 repo files) — created: distinct domain.** The importable runtime of the IKIGAI package: agent graph, MCP servers, chat, observability.

## OVERVIEW
Poetry installs these directories as **top-level** package names (`agents`, `chat`, `mcp_server`, `observability`, `strategics`, `plugins`) — there is no `ikigai.*` prefix at runtime.

## STRUCTURE
```
src/ikigai/src/
├── agents/                  # 125 files — the agent layer
│   ├── v2/                  # 81 files — LangGraph v2 graph, nodes, prompts, skills, memory, checkpoint
│   ├── paperclip/           # 21 files — orchestrator graph + policy/router/persistence + 6 adapters
│   ├── paperclip_dynamic/   # 11 files — 3-slot sequential sub-agent fan-out
│   ├── tools.py             # IKIGAI_TOOLS (exactly 12) + vault read/write tools
│   ├── tools_taskdog.py, tools_sf.py, tools_tuiboard.py
│   ├── reliability.py       # retry_with_backoff / circuit_breaker decorators
│   ├── deepagents_harness.py, taskdog_mcp_graph.py, mcp_taskdog_client.py
│   └── ikigai_read_vault.py, ikigai_read_strategics.py, ikigai_write_vault.py
├── mcp_server/              # FastMCP gateway (31 tools + 6 resources) + a 2nd FastMCP for taskdog
├── chat/                    # read_thread / write_entry / write_proposal
├── observability/           # init_tracing / get_tracer / observed_tool (OTel)
├── plugins/paperclipai_bridge/  # FastAPI bridge server (127.0.0.1:8741)
├── strategics/loader.py     # loads strategics/*.md; NEVER writes
├── gateway_client.py        # MCP client + singleton reset
└── ikigai_wrapper.py        # LangGraph-dev entry (absolute imports only)
```

## WHERE TO LOOK
| Task | Location |
|---|---|
| Graph wiring | `agents/v2/graph.py` — `NODES` tuple (16) + `_safe_node` wrapper |
| Individual steps | `agents/v2/nodes/*.py` (16 node modules) + `nodes/meta_plan/` (3) |
| Prompt renderers | `agents/v2/prompts/` — 15 `render_*` modules + `algorithm_constants.json` |
| Skills | `agents/v2/skills/` — registry of 6 (`taskdog-triage`, `vault-intent-extract`, `ikigai-{daily,weekly,monthly,quarterly}`) |
| Memory / checkpoint | `agents/v2/memory_*.py` (ADR-028), `agents/v2/checkpoint*.py` (ADR-027) |
| MCP tools | `mcp_server/server.py`; taskdog-specific tools in `mcp_server/taskdog_tools.py` |
| Paperclip gates | `agents/paperclip/policy.py`; adapter selection in `router.py` |

## CONVENTIONS
- **Graph factories use the LangGraph-API signature `make_<name>_graph(runtime, config)`** and delegate to an internal `_build_<name>_graph(...)` that keeps the original API for tests. `langgraph.json` at the repo root registers 5 of them.
- **Every node is wrapped in `_safe_node(name, fn)`** so an exception becomes state (`originating_node` / `error_type` / `error_message` / `traceback_str`) instead of a crash. The wrapper is duplicated in `v2/graph.py` and `v2/fork_smoke_graph.py` — keep both copies in sync.
- **`NODES` in `v2/graph.py` is the single source of truth for valid entry points** (16 names). `v2/subgraph.py` rebinds a *local* `NODES` that appends `meta_plan`, because the module-level tuple is immutable under a drift invariant.
- **`v2/nodes/*.py` are `state -> dict` functions.** The 5 M12 stubs (`balance`, `heuristics`, `plan`, `reflect`, `score_vectors`) return an `error_channel` entry naming the deleted bridge wrapper instead of calling it.
- **Two FastMCP instances exist on purpose**: `mcp_server/server.py` (`"ikigai-gateway"`, 31 tools + 6 resources) and `mcp_server/taskdog_tools.py` (`"taskdog"`, 25 tools). They must not cross-talk.
- **MCP handlers return JSON strings**, with errors shaped `{"error": ..., "code": -32601|-32602|-32603}`.
- **LangChain tools are decorated `@tool` → `@circuit_breaker(...)` → `@retry_with_backoff(...)`** in that order (3 attempts, 0.5s initial backoff, 8s cap, jitter; breaker threshold 5, 30s reset).
- **Paperclip policy gates are deliberately asymmetric**: `CostGate` and `WallClockGate` are **fail-OPEN** (missing/malformed data allows dispatch); `RiskGate` is **fail-CLOSED** (dangerous-keyword match refuses).

## ANTI-PATTERNS
- **Algorithm tuning constants live ONLY in `agents/v2/prompts/algorithm_constants.json`** (31 keys, ADR-019), read via `load_constants.get()`. New `DEFAULT_*` / `HYSTERESIS_*` constants in `agents/v2/*.py` are forbidden; the drift detector enforces it.
- **Never call raw `vault_write` from a node.** `agents/v2/nodes/proposal_executor.py` exposes a `vault_write` sentinel that raises `RuntimeError` — route writes through `wrap_vault_write` (ADR-029) and only when `approval_state == "approved"`.
- **Never add a graph-facing MCP wrapper that is not in `server.py`'s `@MCP.tool` registry.** `mcp_bridge.py` currently exposes exactly one (`ikigai_decompose`); adding one requires editing the bridge *and* the drift detector.
- **Never auto-execute writes.** `dep_graph`, `gantt_suggest`, `tag_propagation` only compute a proposal.
- **Skills observe and propose; they never apply.** A skill exposes `SKILL_NAME`, `propose(...)`, `run_skill(...)`; `propose` must not write to disk.
- **`v2/__init__.py` monkey-patches `anthropic.OverloadedError` at import time**, before any `langchain_anthropic` import. Importing `langchain_anthropic` first raises `AttributeError` and makes every LLM call silently return "0 suggestions". Do not remove the shim (browser-use 0.13.10 pins `anthropic` 0.76.0).
- **Never import `v2/tools_legacy_reference.py` or `v2/harness_legacy_reference.py`.** Their bodies are wrapped in `if False:` purely to keep the drift detector from seeing live definitions.

## COMMANDS
```bash
python -m mcp_server                       # from src/ikigai/src
python -m agents.deepagents_harness --chat --thread default
python -m src.ikigai.src.plugins.paperclipai_bridge.main   # uvicorn 127.0.0.1:8741
langgraph dev                              # loads langgraph.json graphs
```
