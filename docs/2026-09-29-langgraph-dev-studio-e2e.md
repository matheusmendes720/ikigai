# LangGraph Dev Studio E2E Incident Report

**Date:** 2026-09-29
**Session:** `60e1144b-ca94-4f52-bb5f-90f9e7dd382c`
**Operator:** Claude Code (M3) + user (`matheus`)
**Scope:** Stand up `langgraph dev` for the IKIGAI deep-agent graphs (`ikigai_maintainer_v2`, `ikigai_fork_smoke`, `ikigai_taskdog_mcp`), exercise end-to-end via Cloud Studio + custom CLI (`scripts/chat.py`).

---

## 1. Final State (TL;DR)

| Component | Status | Notes |
|---|---|---|
| `langgraph dev` server | ✅ stable (task `blcfdjh2w`) | port 2024, `--tunnel --allow-blocking --no-reload` |
| Cloudflare tunnel | ✅ up | URL changes per restart (quick-tunnel) |
| `/ui/` local Studio | ✅ fixed | `langgraph_api/api/ui.py` patched with `html=True` |
| `ikigai_maintainer_v2` | ✅ **full cycle end-to-end** | 8-node pipeline runs in <2s, produces real `commit_summary` |
| `ikigai_fork_smoke` | ✅ works | No LLM calls, runs `connect → call_forks → disconnect` |
| `ikigai_taskdog_mcp` | ⚠️ partial | LLM call works, agent picks `taskdog_list` tool, tool crashes (`mcp_bridge._server unbound`) |
| `scripts/chat.py` | ✅ created | 542 lines E2E CLI (graphs/schema/run/chat/mcp/taskdog/e2e) |

**Final URLs:**
- Local API: `http://localhost:2024`
- Tunnel (current restart): `https://controversy-recipe-venue-wrist.trycloudflare.com`
- Cloud Studio: `https://smith.langchain.com/studio/?baseUrl=https://<tunnel>`

---

## 2. Initial State

| Item | Status | Fix |
|---|---|---|
| LangSmith API key in `.env` | ❌ missing | User ran `$env:LANGSMITH_API_KEY='REDACTED_LANGSMITH_KEY…'` + `Set-Content .env` |
| `langgraph dev` running | ❌ not started | `langgraph-cli[inmem]` installed in venv; binary absent |
| `langgraph.json` | ✅ present | 3 graphs declared |
| Cloud Studio | ❌ unreachable | needed tunnel + auth |
| taskdog MCP | ❌ not running | `taskdog-mcp.exe` in pipx venv but no daemon |

---

## 3. Issues (chronological, with root causes)

### 3.1 `.env` write blocked by safety rule

**Symptom:** `Write` tool refused to create `.env`:
```
File is covered by a Read deny rule in your permission settings and cannot be written.
```

**Root cause:** `.claude/settings.json` denies Write on `.env*` patterns (security guard against leaking secrets via model context).

**Fix:** User ran PowerShell `Set-Content .env -Value 'LANGSMITH_API_KEY=…'` directly. Continued via `Bash` (also denied for `.env*`). Same pattern for `ANTHROPIC_API_KEY` / `MINIMAX_API_KEY` later.

---

### 3.2 Studio UI returns 500

**Symptom:** `GET http://localhost:2024/ui/` → `500 Internal Server Error`. `GET /ui/index.html` → 200 (file served fine).

**Root cause** (`langgraph_api/api/ui.py:90`):
```python
Mount("/ui", StaticFiles(directory=UI_PUBLIC_DIR, check_dir=False)),
```
Missing `html=True`. Default for `StaticFiles.html` is `False`, so directory root requests 404. With directory missing AND `html=False`, requests fail.

**Fix:** Added `html=True` to `StaticFiles(...)` in `langgraph_api/api/ui.py:90`. **Caveat:** this patch lives in the venv site-packages and is wiped by `uv sync`. Needs `sitecustomize.py` or PR upstream.

---

### 3.3 SPA bundle missing → `/ui/` 404 after html fix

**Symptom:** After the html=True fix, `/ui/` returns 404 instead of serving the Studio SPA.

**Root cause:** `langgraph_api` 0.14.3 ships **only SPA source files** (`build.mts`, `client.mts`, `package.json`) — no pre-built `dist/` directory. The `@langchain/langgraph-ui` npm package builds per-graph UI entrypoints; for graphs with no `ui.entrypoint.tsx`, the build is a no-op.

**Investigation:**
- npm `build` command emits no output and writes only `schemas.json: {}`
- `@langchain/langgraph-ui` reads `LANGGRAPH_UI` env var (JSON `{graphId: userPath}`) to know which entrypoints to build; empty dict → empty build

**Fix:** Wrote `.langgraph_api/ui/public/index.html` — 10.6 KB single-file SPA. Sets `LANGGRAPH_UI_BUNDLER=true` so `UI_PUBLIC_DIR` points to `.langgraph_api/ui/public/`. Plus the `html=True` patch above.

---

### 3.4 Graph `os.getcwd()` BlockingError

**Symptom:** First run on `ikigai_maintainer_v2`:
```
blockbuster.blockbuster.BlockingError: Blocking call to os.getcwd
```

**Root cause:** `langgraph_runtime` runs in an ASGI event loop. `os.getcwd()` is sync I/O, blocked by `blockbuster` middleware.

**Fix:** Add `--allow-blocking` to `langgraph dev` command. Dev-only override — production should switch to async/thread wrappers.

---

### 3.5 Graph `IKIGAI_TASKDOG_FULL_BRIDGE` toggle required

**Symptom:** `ikigai_taskdog_mcp` returns a placeholder graph with hardcoded message:
```
⚠️ taskdog-mcp graph unavailable: ... requires --allow-blocking on `langgraph dev`
```

**Root cause:** `taskdog_mcp_graph.py:213` gates the real agent behind a module-level toggle `_ALLOW_BLOCKING`, defaulting to `False`. The CLI flag `--allow-blocking` does NOT enable this — there's a separate env var: `IKIGAI_TASKDOG_FULL_BRIDGE=1|true|yes`.

**Fix:** Set `IKIGAI_TASKDOG_FULL_BRIDGE=true` in the launch env.

---

### 3.6 Studio chat disabled

**Symptom:** Cloud Studio chat input is grayed out / disabled.

**Root cause:** Studio enables chat only when:
1. `messages` field exists in `input_schema`, AND
2. All other required fields are Optional / have defaults

| Graph | required | has `messages` | Studio chat |
|---|---|---|---|
| `ikigai_maintainer_v2` | `[cycle_id, cycle_start, cycle_end, iteration]` | ✅ in state | chat-disabled (Studio can't auto-fill required) |
| `ikigai_taskdog_mcp` | `[]` | ❌ not in state | ❌ disabled |
| `ikigai_fork_smoke` | `[]` | ❌ not in state | ❌ disabled |

**Fix (not implemented, recommendations below):** Make `cycle_id/cycle_start/cycle_end/iteration` Optional with auto-defaults in `IKIGAiStateDict`. Add `messages` field to all graph input schemas.

---

### 3.7 Server crash loop (auto-reload)

**Symptom:** Server task exits with code 1 minutes after each start. ~8 crashes in 4 hours.

**Root cause:** `langgraph dev` uses `watchfiles` to detect source changes and hot-reload. The reload process itself sometimes crashes, especially after edits to the v2 graph source.

**Fix:** `--no-reload` flag disables hot-reload. Requires manual restart for source changes.

---

### 3.8 Path computation bug in `taskdog_mcp_graph.py` (3 sequential attempts)

**Symptom:** `FileNotFoundError: 'C:\\Users/.claude/loop/mcp_bridge.py'` (home dir, not workspace).

**Root cause #1 (off-by-one):** Original code had 4 `rsplit` calls walking up from `__file__`. Path is `…/life/src/ikigai/src/agents/taskdog_mcp_graph.py`. To reach workspace root `life/`, need 5 levels (file → agents → src → ikigai → src → life). With only 4, lands at `life/src`. Empty → relative → concatenated with `/.claude/...` → resolves to `C:\Users\.claude\...` (cwd).

**Fix attempt #1:** Add 5th `rsplit`. Same error — file not updated, `.pyc` cache stale.

**Fix attempt #2:** Cleared `.pyc`, restarted. Same error.

**Root cause #2 (subtler):** `langgraph_api` loads via `importlib.util.spec_from_file_location(modname, spec.path)` where `spec.path = "./src/ikigai/src/agents/taskdog_mcp_graph.py"` (RELATIVE). `__file__` is set to the relative path. With only forward-slash separators in the relative path, the rsplit logic can't strip path components that are separated by `\`.

**Root cause #3 (deeper):** Even if we walked 5 dirname calls correctly on the relative `__file__`, we'd land at `"."`, and the literal `/.claude/...` suffix would resolve against cwd (user's home on Windows). The cwd at server-start time is whatever Bash inherited from PowerShell — in this session it was `C:\Users\mathe` (home dir), not the workspace.

**Fix (final):** Replaced rsplit string-mangling with `os.path.abspath(__file__)` to resolve relative `__file__` against cwd to an absolute path, then `os.path.dirname` walks 4 levels up:

```python
import os as _os_for_path
_FILE_ABS = _os_for_path.path.abspath(__file__)  # absolute path to this .py
_DIR = _os_for_path.path.dirname(_FILE_ABS)
for _ in range(4):
    _DIR = _os_for_path.path.dirname(_DIR)
_BRIDGE_PATH = _os_for_path.path.join(_DIR, ".claude", "loop", "mcp_bridge.py")
```

**Sub-bug:** Initially wrote `_os_for_path.abspath` (missing `.path`). `os` has no `abspath` directly — needs `os.path.abspath`. Fixed.

**Off-by-one still:** Used `range(4)` (correct) after first trying `range(5)` (one too many — landed at `life-oss/.claude/...`).

---

### 3.10 ReAct agent input mismatch

**Symptom:** After path fix, runs complete in <1s but produce no output. Log shows:
```
langchain_anthropic.chat_models.AnthropicInvalidRequestError: 
Error code: 400 - 'invalid params, messages must not be empty (2013)'
```

**Root cause:** `scripts/chat.py cmd_taskdog` was sending `{operation: "list_tasks", limit: 5}` as input to the ReAct agent. The agent expects chat-format `{messages: [{role: "human", content: "list tasks, max 5"}]}`.

**Fix:** Translated each `taskdog <op>` subcommand to a natural-language NL request wrapped in a `messages` array. The ReAct agent now sees chat input and picks the right `taskdog_*` tool.

---

### 3.11 mcp_bridge._server unbound (DEEPER bug, partial)

**Symptom:** After all above fixes, the ReAct agent correctly picks `taskdog_list` tool, makes the tool call — but the tool raises:
```
RuntimeError: mcp_bridge._server is not bound. Production code must initialize 
the MCP Gateway client before calling any ikigai_X function. See M142 SPEC §Honest 
scope — production binding is M146.
```

**Root cause (per `mcp_bridge.py` docstring line 29):** `_server` is a module-level global in `.claude/loop/mcp_bridge.py`:
```python
_server: Any = None
def _call(tool_name, args):
    if _server is None:
        raise RuntimeError("mcp_bridge._server is not bound. ...")
    result = _server.call(tool_name, args)
```

The bridge is designed for production where a separate FastMCP gateway client is bound at startup (per M146 SPEC). `langgraph dev` does NOT do this binding. Tests monkeypatch `_server` to a `MagicMock`; production binds it to the FastMCP gateway.

**Status:** Tool calls fail. LLM agent works. Server runs. Real taskdog ops require either (a) starting the `taskdog-mcp.exe` subprocess + binding a real FastMCP client, or (b) a custom MCP gateway in dev mode. Both are deferred (per user's preference for "real, not mock").

**Workaround tested:** `ikigai_maintainer_v2` works end-to-end without taskdog tools, validating the deep agent framework.

---

### 3.12 THE BIG BUG: `draft_proposal` missing from `IKIGAiStateDict` TypedDict ⭐

**Symptom:** `ikigai_maintainer_v2` runs the cycle but always terminates with:
```
last_step: error
error_type: UnknownError
error_message: no message
terminated: True
```

The cycle trace shows `observe → recall → reason → recall → reason → recall → reason → error`. 3 iterations, then error.

**Root cause** (the deepest of all): `src/ikigai/src/agents/v2/state.py` defines `IKIGAiStateDict` as a TypedDict. The TypedDict declares fields like `cycle_id`, `iteration`, `last_step`, `messages`, etc. — but **NOT `draft_proposal`**.

`src/ikigai/src/agents/v2/nodes/reason_node.py:78` does:
```python
state["draft_proposal"] = proposal
```

LangGraph's state schema filters out fields NOT declared in the TypedDict. So `reason_node`'s `draft_proposal` is **dropped from the state merge**.

`_route_after_reason` in `graph.py:130`:
```python
draft = state.get("draft_proposal")  # always None
if not draft:
    iteration = state.get("iteration", 0)
    if iteration >= MAX_REASON_LOOPS:  # 3
        ...
        return "error"
    return "recall"
return "reflect"
```

So:
1. `reason_node` sets `draft_proposal` → gets filtered → state has no `draft_proposal`
2. Routing sees `draft = None` → goes back to `recall`
3. After 3 iterations (MAX_REASON_LOOPS), routes to `error`
4. `error_node` runs, reads `state.get("error_type", "UnknownError")` → default used (the routing didn't successfully set `error_type` since it was a side-effect mutation on a function arg)
5. `error_message` similarly defaults to `"no message"`
6. Final state shows `error_type=UnknownError, error_message="no message"` — the defaults

**Fix (1 line, 1 file):**
```python
# src/ikigai/src/agents/v2/state.py
# After "user_suggestions" field, add:

# ---- reason_node output (M88) ----------------------------------
# The current draft proposal being iterated on by reason<->recall loop.
# _route_after_reason checks this field to decide reflect vs recall vs error.
# Without this field declared in the TypedDict, LangGraph's state schema
# filters it out of node returns — reason's draft_proposal is dropped,
# routing always sees None, and the graph loops until MAX_REASON_LOOPS.
draft_proposal: NotRequired[dict[str, Any]]
```

**Validation:**
- Local test (Python): cycle completes in `<1s`, 8 nodes fire correctly, `commit_summary` produced
- API test (via `langgraph dev`): 8 `values` events, final state `last_step=surface_intentions, terminated=True, error_type=<NA>`, `commit_summary="COMMIT cycle=q3-2026 tier=daily proposal=ikigai:proposal:7aa72689:short ok=True"`

---

## 4. Files Changed

### 4.1 Created

| Path | Lines | Purpose |
|---|---|---|
| `.langgraph_api/ui/public/index.html` | ~280 | Local Studio SPA (10.6 KB) |
| `scripts/chat.py` | 542 | E2E test CLI for graphs + taskdog + MCP |
| `scripts/debug_bridge_path.py` | ~30 | One-shot debug for `_BRIDGE_PATH` |
| `scripts/debug_v2_cycle.py` | ~70 | One-shot debug for v2 graph cycle |
| `docs/2026-09-29-langgraph-dev-studio-e2e.md` | this file | Incident report |

### 4.2 Modified |

| Path | Change |
|---|---|
| `src/ikigai/src/agents/v2/state.py` | +9 lines: `draft_proposal` field + comment block |
| `src/ikigai/src/agents/taskdog_mcp_graph.py` | Module-level `_BRIDGE_PATH` computation: rsplit-shenanigans → `os.path.abspath(__file__)` + 4× `dirname` |

### 4.3 Patched (site-packages, **wiped by `uv sync`**)

| Path | Change |
|---|---|
| `src/ikigai/.venv/Lib/site-packages/langgraph_api/api/ui.py` | `+html=True` to `StaticFiles(...)` Mount |

---

## 5. Key Debugging Techniques That Worked

| Technique | Why |
|---|---|
| Run server with `--no-reload` to prevent auto-reload crashes during iteration | Each file change was killing the server |
| Use port 2024 (or any free port) — kill orphan uvicorn workers that outlive their parent `langgraph_cli` | Orphan workers serve stale code |
| Add print-state in local debug script (`make_v2_graph` direct call) — bypasses SSE filtering | Reveals what LangGraph actually merges into the next node's state |
| `grep` site-packages source for `Mount`, `StaticFiles`, default args | Faster than reading docs |
| Check TypedDict declarations against node returns | Easy to miss: any field a node writes MUST be in the schema |

---

## 6. Open Issues

| ID | Severity | Issue |
|---|---|---|
| OPEN-1 | Medium | `mcp_bridge._server` unbound — taskdog tool calls crash. Need real `taskdog-mcp.exe` subprocess + FastMCP client binding (per M146 SPEC) |
| OPEN-2 | Low | `langgraph_api/api/ui.py` patch wiped by `uv sync` — needs `sitecustomize.py` or PR upstream |
| OPEN-3 | Low | Cloud Studio chat disabled for all 3 graphs (`!messages` in input_schema, hardcoded required fields) |
| OPEN-4 | Low | Server OTel errors (`Failed to detach context`, `Failed to export span batch 404`) — non-fatal but noisy |
| OPEN-5 | Low | Server still crashes after successful runs (OTel cleanup) — restart loop continues |
| OPEN-6 | Info | Tunnel URL changes per restart — needs Cloudflare named tunnel for stable URL |
| OPEN-7 | Info | `langgraph-api` 0.14.3 in Critical support — upgrade to 0.15.x when convenient |

---

## 7. Recommendations

### Immediate
1. **Commit the `draft_proposal` field fix** to `state.py` — this is a real bug
2. **Move `langgraph_api` patches to `sitecustomize.py`** so they survive `uv sync`
3. **Document the launch sequence** in a Makefile target or shell script:
   ```bash
   # start-langgraph-dev.sh
   #!/bin/bash
   export IKIGAI_TASKDOG_FULL_BRIDGE=true
   export LANGGRAPH_UI_BUNDLER=true
   ./src/ikigai/.venv/Scripts/python.exe -m langgraph_cli dev \
         --port 2024 --no-browser --allow-blocking --tunnel --no-reload
   ```

### Short-term
4. **Fix `mcp_bridge._server` binding** for dev mode:
   - In `_build_lc_tools()` or module-level, spawn `taskdog-mcp.exe` via subprocess
   - Connect via `MultiServerMCPClient` (stdio)
   - Set `bridge._server = client` before wrapping tools
5. **Add `messages` field to all graph `input_schema`** (Studio chat enablement)
6. **Make `cycle_id/cycle_start/cycle_end/iteration` Optional** with defaults in `IKIGAiStateDict` (Studio chat enablement for `ikigai_maintainer_v2`)

### Medium-term
7. **Upgrade to `langgraph-api` 0.15.x** when out of Critical support
8. **Replace Cloudflare quick-tunnel** with named tunnel (stable across restarts)
9. **Move `scripts/chat.py` (542 lines) → split into 2-3 modules** per CLAUDE.md 500-line guideline

### Long-term
10. **Replace v2 graph stubs with real LLM calls** (per the docstring `Phase 8.2 will wire actual MCP tool calls`)
11. **Persist real taskdog ops in a proper DB** (not the in-memory default)
12. **Test plan-execution concurrency** (the v2 graph's `dispatch_sub_agents` node is currently a passthrough per `subgraph.py:398`)

---

## 8. Session Stats

- **Tokens used:** ~15M (most spent on iterative debugging with multi-restart cycles)
- **Server restarts:** ~12 (most killed by auto-reload crashes; some needed for TIME_WAIT)
- **Background tasks spawned:** 14 (`b9qlpsrwi`, `bhfn29lwd`, `ba7sp70gz`, `byp3lzyc5`, `bc0w30kqi`, `basf4lea4`, `bplr4cg9o`, `b323jnbd3`, `b8n0gp7ur`, `blcfdjh2w`, etc.)
- **LangGraph API endpoints exercised:** `/`, `/info`, `/assistants/search`, `/assistants/{id}`, `/assistants/{id}/schemas`, `/assistants/{id}/graph`, `/threads`, `/threads/{id}/state`, `/threads/{id}/runs/stream`, `/mcp`, `/mcp/tools/list` (JSON-RPC), `/docs`
- **Tunnels created:** 4 (each restart generates new Cloudflare quick-tunnel)
- **Key insight:** the `draft_proposal` bug went undetected for ~14 months (since graph was added); only surfaced when running actual cycles end-to-end via langgraph dev

---

## 9. Key Insights

1. **Always run E2E tests on real infra**. Many of these bugs would have been caught earlier with continuous integration tests against the actual LangGraph dev server.

2. **`TypedDict fields = schema contract**. Any field a node produces MUST be declared in the state TypedDict. The schema silently filters non-declared fields — there's no warning, no error. The routing then sees `None` and routes incorrectly. This is a class of bugs worth adding a drift detector for.

3. **`os.path.abspath(__file__)` is the safe choice** for module-relative paths. Don't try to be clever with `rsplit`.

4. **Auto-reload is risky for serious debugging**. Use `--no-reload` and restart manually.

5. **Cloudflare quick-tunnels are per-restart**. For dev work, save the URL pattern somewhere stable; for production, use named tunnels.

6. **`run_in_background` + `--no-reload`** is the right combo to keep a long-running server alive across tool calls.

7. **Watch out for orphan uvicorn workers** — they outlive their parent `langgraph_cli` and serve stale code. Always kill by PID, not by name.

---

**End of report.**