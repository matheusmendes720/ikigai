# M5 — IKIGAI MCP Integration

> **What:** Wire the orchestrator prompt to IKIGAI MCP tools (14 total) so the loop can delegate "research / knowledge / task" work to the Deep Agent layer.
> **Why:** Today the orchestrator knows nothing about IKIGAI tools — workers can't invoke them through MCP from inside the loop. This milestone makes the agent layer reachable from the loop layer.

## Current state (verified 2026-09-08)

- IKIGAI MCP server lives at `src/ikigai/src/mcp_server/server.py`
- 14 tools exposed (verified by reading `server.py` + `taskdog_tools.py`):
  - 8 IKIGAI planning tools: `ikigai_decompose`, `ikigai_write_tasks`, `ikigai_read_tasks`, `ikigai_mesh_show`, `ikigai_task_create`, `ikigai_health`, `vault_write`, `vault_read`
  - 3 Plan C investigation tools: `investigation_enqueue`, `investigation_status`, `investigation_complete`
  - 3 taskdog fork tools: `taskdog_read`, `taskdog_list`, `taskdog_supports_field`
- 6 resources: `ueid://{ueid}`, `queue://pending`, `queue://events/{event_id}`, `health://gateway`, `plans://cycles`, `plans://cycles/{cycle_id}`
- Server start command: `ikigai.bat mcp` (Windows) / `cd src/ikigai && uv run ikigai mcp` (POSIX)
- Handshake protocol: stdio JSON-RPC (uses `sys.stdin.buffer.readline()` per Windows fix `b93a1f3`)
- The orchestrator prompt `.claude/agents/loop/orchestrator.md` does NOT mention these tools today.

## Scope

**This milestone is the orchestrator-prompt-only layer**, NOT a new gateway
implementation. IKIGAI MCP already works standalone (verified by
`scripts/mcp_inspect.py` and the 6 existing MCP tool tests). We just need to
expose the surface to the loop.

The agent layer is planner-only per ADR-013 — it cannot execute math/policy/
scoring tools. The orchestrator must respect this boundary when delegating.

## Acceptance criteria

1. **Prompt section** — `.claude/agents/loop/orchestrator.md` gains a
   "IKIGAI MCP Tool Surface (M5)" section between HARD RULES and Prompt Template,
   listing all 14 tools + 6 resources in a table with one-line invocation syntax.
2. **Standup entry** — The orchestrator prompt's prompt-template phase explicitly
   delegates one of these tools to the worker: `ikigai_read_tasks` or
   `ikigai_health` (the two safest read-only tools).
3. **No new gateway code** — No files in `src/ikigai/src/mcp_server/` are modified
   by M5. M5 is additive documentation only.
4. **Worker prompt update** — `.claude/agents/loop/worker.md` gains a sentence
   acknowledging that IKIGAI MCP tools are accessible (so the worker knows to ask
   the orchestrator to delegate).
5. **One tick uses IKIGAI MCP** — A new test `tests/test_m5_ikigai_mcp_integration.py`
   spawns `ikigai.bat mcp` (or POSIX equivalent), performs the stdio JSON-RPC
   `initialize` handshake, calls `ikigai_health`, and asserts the response includes
   `{"status": "ok"}` (or whatever the actual shape is — recorded in the test).
6. **No regression** — `test_loop_infra.py` (11/11), `test_m4_langgraph_integration.py`
   (9/9), `test_canonical_scope.py` (31/31) all still PASS.

## Sub-tasks

### T-5.1 — Add IKIGAI tool surface to orchestrator prompt
- **status:** pending
- **spec_ref:** acceptance criterion #1
- **acceptance:**
  - [ ] `.claude/agents/loop/orchestrator.md` adds "IKIGAI MCP Tool Surface (M5)" section
  - [ ] Section lists all 14 tools (8 IKIGAI + 3 investigation + 3 taskdog) + 6 resources in a table
  - [ ] Each row has: name, one-line invocation, source path
  - [ ] Cron entrypoint pointer (`ikigai.bat mcp` / `cd src/ikigai && uv run ikigai mcp`)
  - [ ] Existing sections preserved (additive change)
- **estimated_cost_usd:** 0.20
- **estimated_minutes:** 5

### T-5.2 — Worker prompt acknowledges IKIGAI MCP availability
- **status:** pending
- **spec_ref:** acceptance criterion #4
- **acceptance:**
  - [ ] `.claude/agents/loop/worker.md` adds a sentence about IKIGAI MCP tools
  - [ ] No other worker.md sections modified
- **estimated_cost_usd:** 0.10
- **estimated_minutes:** 2

### T-5.3 — One-tick IKIGAI MCP integration test
- **status:** pending
- **spec_ref:** acceptance criterion #5
- **acceptance:**
  - [ ] `tests/test_m5_ikigai_mcp_integration.py` exists (≥50L)
  - [ ] Test spawns `ikigai.bat mcp` subprocess via stdio JSON-RPC handshake
  - [ ] Calls `ikigai_health` tool and asserts response structure
  - [ ] No LLM cost (subprocess + JSON parsing only)
  - [ ] Test passes locally (Windows Git Bash + bash on PATH)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 12

### T-5.4 — Regression + closeout
- **status:** pending
- **spec_ref:** acceptance criterion #6
- **acceptance:**
  - [ ] `pytest tests/test_loop_infra.py` 11/11 PASS
  - [ ] `pytest tests/test_m4_langgraph_integration.py` 9/9 PASS
  - [ ] `pytest src/ikigai/tests/test_canonical_scope.py` 31/31 PASS
  - [ ] All T-5.1..T-5.3 marked status=done in tasks.md
  - [ ] `roadmap.md` M5 marked `STATUS: DONE`
  - [ ] `progress.md` M5 entry appended with verdict + commit SHA
  - [ ] Atomic commit
- **estimated_cost_usd:** 0.10
- **estimated_minutes:** 4

## Out of scope (deferred)

- Calling IKIGAI tools FROM the orchestrator prompt mid-tick (would require
  stdio handshake in the orchestrator's bash subprocess). Deferred to M5.1+ if
  requested.
- Adding new IKIGAI tools (the 14 count is the current surface — new tools come
  via the IKIGAI roadmap, not the loop roadmap).
- Wiring MCP resources (URIs like `ueid://{ueid}`) — the spec focuses on tools
  only for now.

## Risks

- **stdio handshake Windows quirks** — `sys.stdin.readline()` HANGS on Windows
  pipes (per memory entry windows-stdio-binary-mode-fix-2026-08-30). The MCP
  server already uses `sys.stdin.buffer.readline()` (commit `b93a1f3`), so the
  test must use the same buffer-level reads.
- **ikigai.bat subprocess spawn** — needs PATH to find `ikigai.bat` and `taskdog.exe`.
  Test must use `shutil.which("bash")` + subprocess.run with proper env.
- **Cost creep** — T-5.3 must NOT spawn an LLM agent. Subprocess + JSON parsing
  only.

## Dependencies

- M4 (DONE) — `.claude/agents/loop/orchestrator.md` already has the LangGraph
  graph surface section. We mirror the pattern for IKIGAI MCP.

## Estimated ticks

3-4 (state-machine + 2 prompt edits + 1 test + 1 closeout)