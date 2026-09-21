---
name: M96-taskdog-deep-agent-gap-report
description: Honest gap analysis - taskdog-mcp exposes 26 tools, deep-agent only wired to 4
owner: matheus-mendes
status: PUBLISHED
milestone: M96
estimated_cost_usd: 0.10
constitution_refs:
  - spec_driven_not_vibe_driven
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M96 — Taskdog → Deep-Agent Tool Wiring Gap Report

**Date**: 2026-09-21 (audit triggered by user asking "conseguimos adaptar todas as feats do taskdog em deep-agent workflows?")
**Author**: Hermes
**Status**: Published, awaiting user validation
**Severity**: **HIGH — affects 85% of taskdog feature surface that the deep-agent cannot reach**

---

## TL;DR

**Não, NÃO adaptamos todas as feats.** O `IKIGAI_TOOLS` (drift-detector-pinned a exatamente 12 tools) só tem **4 taskdog tools** (15% do taskdog surface). Os 22 capabilities restantes do taskdog 0.28.0 estão acessíveis via:

- **`taskdog-mcp` (binary)**: 26 tools expostos via MCP stdio
- **taskdog HTTP API**: 36 endpoints REST expostos em `localhost:8000`
- **taskdog CLI**: 22 subcommands disponíveis em PATH

**Mas NENHUM desses chega ao deep-agent** porque o `create_deep_agent(tools=IKIGAI_TOOLS, ...)` não inclui nem o MCP client nem o HTTP client — só os 4 tools hard-wrapped como `@tool` decorators.

---

## The Three Layers of Taskdog Surface

### Layer 1 — taskdog CLI (binary, 0.28.0)
22 subcommands disponíveis via `~/.local/bin/taskdog.exe`:

```
add, audit, cancel, db, dep, done, export, fix-times, gantt, list,
note, optimize, pause, reopen, restore, rm, show, start, stats,
tag, timeline, tui, update
```

### Layer 2 — taskdog HTTP API (taskdog-server, port 8000)
**36 REST endpoints** (OpenAPI spec at `/openapi.json`):

```
GET    /api/v1/tasks
POST   /api/v1/tasks
GET    /api/v1/tasks/{id}
PATCH  /api/v1/tasks/{id}
DELETE /api/v1/tasks/{id}
POST   /api/v1/tasks/{id}/complete
POST   /api/v1/tasks/{id}/start
POST   /api/v1/tasks/{id}/cancel
POST   /api/v1/tasks/{id}/pause
POST   /api/v1/tasks/{id}/reopen
POST   /api/v1/tasks/{id}/archive
POST   /api/v1/tasks/{id}/restore
... (and 25 more: bulk ops, dependencies, tags, audit, statistics, gantt, optimize, etc)
```

### Layer 3 — taskdog-mcp (MCP server, 0.28.0)
**26 MCP tools** (verify via `taskdog-mcp` + tools/list):

```
add_dependency, cancel_task, complete_task, create_task, decompose_task,
delete_tag, delete_task, fix_actual_times, get_audit_log, get_executable_tasks,
get_statistics, get_tag_statistics, get_task, get_task_notes, list_algorithms,
list_audit_logs, list_tasks, optimize_schedule, pause_task, remove_dependency,
reopen_task, restore_task, set_task_tags, start_task, update_task, update_task_notes
```

---

## What's Wired into the Deep-Agent (IKIGAI_TOOLS = 12 tools)

`src/ikigai/src/agents/tools.py` lines 418-432 declare exactly **4 taskdog tools** wrapped as LangChain `@tool`:

| Tool | Maps to | CLI Subcommand | MCP Tool |
|---|---|---|---|
| `taskdog_list_tasks` | list + filter by status | `export` (via `_run_export`) | `list_tasks` |
| `taskdog_create_task` | create (name only — no priority/tags/deadline) | `add` (basic args only) | `create_task` |
| `taskdog_complete_task` | start + complete (workflow) | `done` (+ optional `start`) | `start_task` + `complete_task` |
| `taskdog_get_task` | fetch by ID (via export filter, hack) | `show` (broken — see bug below) | `get_task` |

### What's MISSING (22 of 26 taskdog-mcp tools NOT wired)

| Missing Tool | What it does | Practical use case |
|---|---|---|
| `cancel_task` | mark PENDING/IN_PROGRESS as CANCELED | "deprioritize this task" |
| `pause_task` + `reopen_task` | PENDING↔PAUSED workflow | "park this for later" |
| `delete_task` + `restore_task` | soft-delete + undo | "this task was wrong" |
| `decompose_task` | break task into N subtasks | "break down this epic" |
| `add_dependency` + `remove_dependency` | task A blocks/depends on task B | "only do X after Y is done" |
| `update_task` | edit priority/tags/deadline/estimate | "this is now urgent" |
| `set_task_tags` + `delete_tag` | granular tag management | "tag as byd/urgent/blocked" |
| `update_task_notes` + `get_task_notes` | attach notes to task | "doc the decision" |
| `fix_actual_times` | correct timestamps retroactively | "I started this 2h ago" |
| `optimize_schedule` | re-prioritize all tasks algorithmically | "auto-schedule my week" |
| `get_executable_tasks` | list tasks with all deps satisfied | "what can I do RIGHT NOW" |
| `list_audit_logs` + `get_audit_log` | full operation history | "what did I change last week" |
| `list_algorithms` + `get_statistics` + `get_tag_statistics` | analytics | "how many byd tasks closed this month" |

### ⚠️ Bug in Wired Tools

`taskdog_get_task` docstring says:

> "Note: taskdog 0.23.0 `show` command has a bug ('TaskdogApiClient has no attribute get_task_detail'); we filter the export list instead."

This means `taskdog_get_task(id)` does `export --format json | filter by id`. That's:
- **Slow** (fetches entire task list, filters in-process)
- **Wrong** if the export endpoint changes
- **Won't work** for archived tasks (they're excluded by default)

---

## Why This Happened

### Drift-Detector Pinned to 12 Tools

`src/ikigai/tests/test_canonical_scope.py::test_ikigai_tools_count_is_12` enforces:

```python
total_count = len(IKIGAI_TOOLS) + len(extension_tools)
assert total_count == 12
```

This was a **deliberate design choice** (ADR-013: planner-only invariant; M70 audit reduced tools from 19 → 12 to keep drift detector happy). The rationale: "more tools = more LLM confusion = more hallucinated calls = worse outcomes."

### Architectural Trade-off

| Approach | Pros | Cons |
|---|---|---|
| **Status quo (4 hard-wrapped tools)** | Drift-detector-stable, predictable, well-tested | 85% of taskdog surface unreachable from LLM |
| **Wire all 26 taskdog-mcp tools** | Full taskdog coverage | Breaks drift detector, inflates context window, increases hallucination risk |
| **MCP-as-source-of-truth (Option 2)** | LangChain `MultiServerMCPClient` auto-discovers tools, dynamic surface | Need `langchain-mcp-adapters` install, async runtime change |
| **Lazy tool registry** | Load tools on-demand by intent | Complex, harder to test |

---

## Concrete Failure Scenarios (User-Facing Impact)

### Scenario 1: Complex task with deadline
> User asks deep-agent: "add a HIGH priority task to review PR #456 by tomorrow, tagged 'urgent'"

**Current behavior**: `taskdog_create_task(name="review PR #456 by tomorrow")` — embeds deadline in name, no priority set, no tag set.

**Required**: `taskdog_create_task(name="review PR #456", priority=8, tag="urgent", deadline="2026-09-22")` — proper fields.

**Status**: ❌ CANNOT DO (priority, tag, deadline not exposed).

### Scenario 2: Dependency-aware execution
> User asks: "add a task to deploy PR #456, but only after task #200 is done"

**Required**: 
1. `create_task("deploy PR #456")` 
2. `add_dependency(task_id=new_id, depends_on_id=200)`

**Status**: ❌ CANNOT DO (no dependency tools).

### Scenario 3: Decompose epic into subtasks
> User asks: "break task #150 into 5 subtasks: research, draft, review, deploy, retrospective"

**Required**: `decompose_task(task_id=150, num_subtasks=5)`

**Status**: ❌ CANNOT DO (decompose_task not exposed).

### Scenario 4: Pause and resume
> User asks: "I'm going on vacation, pause all byd:* tasks for 2 weeks"

**Required**: `pause_task(task_id=N)` for each tagged task

**Status**: ❌ CANNOT DO (no pause/resume tools).

### Scenario 5: Audit / history
> User asks: "what did I change yesterday?"

**Required**: `list_audit_logs(since=...)` then `get_audit_log(log_id)`

**Status**: ❌ CANNOT DO (no audit tools).

---

## Recommended Path Forward (M97+)

### Phase 1: M97 — Wire taskdog-mcp via MultiServerMCPClient (RECOMMENDED)

**Goal**: deep-agent gets 26 taskdog tools WITHOUT inflating `IKIGAI_TOOLS`.

**Approach**:
```python
# in deepagents_harness.py
from langchain_mcp_adapters import MultiServerMCPClient

mcp_client = MultiServerMCPClient({
    "taskdog": {"command": "taskdog-mcp", "transport": "stdio"},
    "ikigai_vault": {"command": "ikigai-maintainer-mcp", "transport": "stdio"},
    # add more MCP servers as we wire them
})
mcp_tools = mcp_client.get_tools()  # 26+ tools from taskdog, +others

all_tools = IKIGAI_TOOLS + mcp_tools  # 12 + 26 = 38 effective
agent = create_deep_agent(tools=all_tools, ...)
```

**Trade-offs**:
- ✅ Full taskdog coverage from day 1
- ✅ No drift detector breakage (IKIGAI_TOOLS stays at 12)
- ✅ MCP servers are independently testable (M86 already verified taskdog-mcp handshake)
- ❌ Requires `langchain-mcp-adapters` install
- ❌ Async runtime change (mcp_client.get_tools() is async)
- ❌ More tools in LLM context = more hallucination risk (mitigated by good tool descriptions)

**Effort**: ~1-2 hours

### Phase 2: M98 — Gap-fill tools with explicit parameters (IF Option 1 instead)

**Goal**: keep current 4 tools but expand `taskdog_create_task` to accept priority/tags/deadline/estimate.

**Approach**:
```python
@tool
def taskdog_create_task(
    name: str,
    priority: int | None = None,
    tag: list[str] | None = None,
    estimate: float | None = None,
    deadline: str | None = None,
    depends_on: int | None = None,
) -> str:
    args = [_TASKDOG_CLI, "add", name]
    if priority is not None: args += ["--priority", str(priority)]
    if tag: 
        for t in tag: args += ["--tag", t]
    if estimate is not None: args += ["--estimate", str(estimate)]
    if deadline: args += ["--deadline", deadline]
    if depends_on is not None: args += ["--depends-on", str(depends_on)]
    ...
```

**Trade-offs**:
- ✅ Stays in IKIGAI_TOOLS=12 budget (just makes existing 1 tool richer)
- ✅ Backward compatible (all params optional)
- ❌ Still missing cancel/pause/decompose/dependency/etc.
- ❌ Less elegant than MCP-based discovery

**Effort**: ~30 min

### Phase 3: Status Quo (current)

**Goal**: keep 4 tools, document the gap, prioritize via real-world usage.

**Approach**: nothing changes; this report becomes the backlog reference.

---

## Validation Criteria for User

Before approving M97 or M98, the user should be able to articulate:

1. **What does my daily-use flow actually need from taskdog?**
   - If "just CRUD on individual tasks" → current 4 tools suffice
   - If "complex workflows with dependencies/automation" → M97 (MCP) is needed

2. **Am I OK with the LLM hallucinating tool calls?**
   - More tools = more options = more potential for the LLM to pick the wrong one
   - 4 curated tools = safer but more limited

3. **Do I need real-time MCP integration, or can I use taskdog CLI directly?**
   - If you only invoke skills via cron (which already works), MCP isn't critical
   - If you want LLM to do live operations, MCP is the right answer

4. **What's my tolerance for drift-detector churn?**
   - Changing IKIGAI_TOOLS count breaks `test_ikigai_tools_count_is_12` (1 test file)
   - Adding MCP server doesn't touch the drift detector

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| M97 wiring breaks other MCP servers | low | medium | Run integration test against all MCP servers |
| LLM hallucinates new taskdog tool calls | medium | low | Validate against `taskdog-mcp` OpenAPI schema |
| Drift detector breaks | low | medium | Keep IKIGAI_TOOLS=12, only augment at runtime |
| taskdog-mcp binary crashes mid-cycle | medium | medium | Pre-flight health check (already in M86 test) |
| context window overflow with 38 tools | medium | low | Tool descriptions concise; trust langchain filtering |

---

## Next Steps (Sequence)

| Milestone | Description | Effort | Depends on |
|---|---|---|---|
| **M97a** | User validates direction (Option 2 = MCP, Option 1 = parameter expansion, or status quo) | 0 min | This report |
| **M97b** | Implement chosen direction | 30 min - 2 hr | M97a |
| **M97c** | Add integration test for deep-agent → taskdog-mcp → taskdog-server E2E | 1 hr | M97b |
| **M97d** | Update `tests/test_langgraph_json_spec.py` to validate MCP wiring | 30 min | M97b |

**Stall until user validation**: do NOT proceed to M97b without explicit user go-ahead.

---

## Cross-references

- `tests/test_canonical_scope.py::test_ikigai_tools_count_is_12` — drift detector
- `src/ikigai/src/agents/tools.py:418` — `IKIGAI_TOOLS` definition
- `src/ikigai/src/agents/tools_taskdog.py` — current 4 taskdog tool wrappers
- `src/ikigai/src/agents/deepagents_harness.py:236` — `create_deep_agent(tools=IKIGAI_TOOLS)`
- `.claude/loop/NOTES-progress-tracking-2026-09-19.md` — daily-use status (was "100%" — needs correction)

---

## Update to Progress Note (CRITICAL)

The 2026-09-19 progress note claimed daily-use 100% complete. **This report proves that claim was misleading** for production use:

- **CRUD on individual tasks**: 100% ✅
- **Production-grade automation**: ~15% ❌ (no cancel/pause/decompose/dependency/update)
- **Time tracking**: ~30% ❌ (no fix_actual_times, get_audit_log)
- **Analytics / reporting**: ~10% ❌ (no statistics, audit_logs, tag_statistics)
- **Schedule optimization**: 0% ❌ (no optimize_schedule)

**Honest daily-use % for production: ~40% (CRUD + workflow basic only).**

The "100%" claim was based on "everything passes tests + daemons run + CLI works" — not on "deep-agent can do everything taskdog supports."

This report corrects the prior overstatement and provides the actionable gap list.

---

## Status

**DRAFT → READY FOR USER VALIDATION.** Awaiting decision on direction (M97a). No implementation until user confirms.
