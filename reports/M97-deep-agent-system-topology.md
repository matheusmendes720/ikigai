---
name: M97-deep-agent-system-topology
description: Full topology map of life-oss agentic system - 5 layers, 12 deep-agent tools, 19 MCP server tools, 13-node v2 graph
owner: matheus-mendes
status: PUBLISHED
milestone: M97
estimated_cost_usd: 0.15
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M97 — Deep-Agent System Topology & Practical Usage Guide

**Date**: 2026-09-21 (audit triggered by user: "vista da topologia geral ... inspecao detalhada de cada um dos componentes")
**Author**: Hermes
**Status**: Published
**Purpose**: show user how to use the system TODAY + what each component does + what's wired + what's not.

---

## TL;DR — What Can I Actually Do Right Now?

| Use case | How | Status |
|---|---|---|
| Add a single task via LLM agent | `life v2 plan <request>` or `python -m life.cli.cli task add` | ✅ works |
| Run daily cycle (cron) | cron fires `invoke-skill ikigai-daily` | ✅ works (9/9 daemons) |
| Inspect any skill | `life skill-show ikigai-quarterly` | ✅ works |
| Visual debugger (LangGraph dev) | `make dev-graph NAME=ikigai_maintainer_v2` | ⚠️ needs `langgraph-cli` install |
| Update next-week planning via chat | `life v2 daily "plan my next week"` | ⚠️ depends on what LLM dispatches |
| LLM does complex taskdog ops (cancel/pause/deps/decompose) | via deep-agent | ❌ **NOT WIRED** (see M96) |

---

## Top-Level View: 5 Layers

```
┌──────────────────────────────────────────────────────────────────────┐
│                    LAYER 5: USER INTERFACES                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ life CLI    │  │ LangGraph   │  │ Claude Code │  │ taskdog CLI  │  │
│  │ (20+ cmds)  │  │ dev (opt)   │  │ + MCP       │  │ (direct)     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  │
└─────────┼───────────────┼───────────────┼───────────────┼──────────────┘
          │               │               │               │
┌─────────┴───────────────┴───────────────┴───────────────┴──────────────┐
│             LAYER 4: SKILL MANIFESTS + INVOKE-SKILL                       │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ invoke_skill(name, entry_point_override, actor)                     │  │
│  │   - Loads <name>.md manifest from src/ikigai/src/agents/v2/skills/ │  │
│  │   - Validates entry_point against graph.NODES (13 nodes)         │  │
│  │   - Runs make_v2_graph(checkpoint_db=":memory:", entry_point=...) │  │
│  │   - Returns user_suggestions + commit_summary to top-level       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│  Skill manifests: daily.md, weekly.md, monthly.md, quarterly.md,     │
│                   meta_plan.md (5 manifests)                          │
└──────────────────────────────────────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────────────────────────────────────┐
│             LAYER 3: V2 GRAPH (LangGraph StateGraph)                    │
│  13 nodes (per graph.py NODES tuple):                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ observe → recall → reason → score_vectors → heuristics          │  │
│  │   → balance → decompose → plan → tag_and_persist               │  │
│  │   → reflect → commit → dispatch_sub_agents → surface_intentions │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  + error_node (terminal fallback)                                     │
│  + meta_plan subgraph (3 nodes: classify_intent, fetch_context,        │
│    generate_proposal)                                                  │
│  Dispatch: dispatch_sub_agents (sub-agent fan-out, ADR-026)           │
│  Checkpoint: SqliteSaver with thread_id (per LangGraph requirement)    │
│  Bound: MAX_REASON_LOOPS = 3 (M88 — prevents infinite recall/reason)    │
│  Failure isolation: safe_node wrapper + error_type field               │
└──────────────────────────────────────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────────────────────────────────────┐
│             LAYER 2: AGENTS (LangChain @tool decorators)               │
│  ══════════════════════════════════════════════════════════════════    │
│  IKIGAI_TOOLS (12, drift-detector-pinned):                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Solverforge Calendar (2):                                       │  │
│  │   - solverforge_list_events(days=7)                             │  │
│  │   - solverforge_create_event(title, date, time="09:00")         │  │
│  │ Tuiboard Kanban (4):                                            │  │
│  │   - tuiboard_list_boards()                                      │  │
│  │   - tuiboard_get_tasks(board_path, column, filter_)              │  │
│  │   - tuiboard_create_task(board_path, title, column=0)            │  │
│  │   - tuiboard_update_task(board_path, task_id, done, priority,   │  │
│  │                          tags)                                   │  │
│  │ Taskdog (4 — INCOMPLETE, see M96):                              │  │
│  │   - taskdog_list_tasks(status, include_archived)                │  │
│  │   - taskdog_create_task(name) ← only "name", no priority/tags!  │  │
│  │   - taskdog_complete_task(task_id) ← start + complete in one     │  │
│  │   - taskdog_get_task(task_id) ← hack: filter from export list    │  │
│  │ Vault-grounded (2):                                              │  │
│  │   - ikigai_read_strategics                                       │  │
│  │   - ikigai_read_vault                                            │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  NOT in IKIGAI_TOOLS (registry elsewhere):                             │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ ikigai_sync_vault — extracted from v2 archive, tested separately │  │
│  │ cli_native_fallback — passive fallback, not registered            │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────────────────────────────────────┐
│             LAYER 1: DATA INFRASTRUCTURE                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ taskdog-server  │  │ taskdog-mcp     │  │ taskdog CLI      │        │
│  │ (port 8000)     │  │ (stdio MCP)     │  │ (pipx 0.28.0)   │        │
│  │ 36 REST         │  │ 26 MCP tools    │  │ 22 subcommands   │        │
│  │ endpoints       │  │ (full feature   │  │ (same surface    │        │
│  │ (CRUD+stats+    │  │  surface)       │  │  as MCP)         │        │
│  │  gantt+opt)     │  │                 │  │                  │        │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│                                                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ IKIGAI MCP      │  │ vault/          │  │ memory_db       │        │
│  │ server          │  │ (markdown       │  │ (SQLite,        │        │
│  │ (19 @MCP.tool    │  │  source of      │  │  daily journals │        │
│  │  decorators,    │  │  truth,         │  │  + proposals)   │        │
│  │  stdio)         │  │  Obsidian-style)│  │                 │        │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
          |
          v
┌──────────────────────────────────────────────────────────────────────┐
│             LAYER 0: SUPPORTING INFRA                                  │
│  - 9 daemons (cron schedules, 5 system + 4 IKIGAI cadences)           │
│  - UEID validation (canonical 4-part + 5-part legacy + decimal ns)      │
│  - Contracts (Pydantic v2 frozen, extra="forbid")                      │
│  - Drift net (18 canonical invariants, 18/18 PASS)                    │
│  - Notify router (file channel only, telegram gated by env vars)       │
│  - LangGraph dev server (optional, NOT installed: pip install ...)      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Layer-by-Layer Inspection

### Layer 1: Data Infrastructure

#### taskdog-server (HTTP daemon, port 8000)
- **Process**: `taskdog-server.exe` (pipx 0.28.0), PID 36336, background process
- **API**: 36 REST endpoints documented in `/openapi.json`
- **Storage**: SQLite (data dir, persists across restarts)
- **Current state**: 193 tasks live
- **Health**: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`
- **CRUD operations exposed**: create, read, update, delete, complete, start, cancel, pause, reopen, archive, restore, bulk ops, dependencies, tags, audit logs, statistics, gantt, optimize
- **Y access via**: `life task {add,start,done,ls}` (M83 wrapper) OR `taskdog` CLI OR `curl http://127.0.0.1:8000/api/v1/tasks` OR `taskdog-mcp` (MCP)
- **What you can do today**: full CRUD on any task from any layer

#### taskdog-mcp (MCP stdio server)
- **Process**: spawned on-demand (no background daemon needed)
- **Surface**: **26 MCP tools** (verified via `tools/list`):
  - `add_dependency, cancel_task, complete_task, create_task, decompose_task, delete_tag, delete_task, fix_actual_times, get_audit_log, get_executable_tasks, get_statistics, get_tag_statistics, get_task, get_task_notes, list_algorithms, list_audit_logs, list_tasks, optimize_schedule, pause_task, remove_dependency, reopen_task, restore_task, set_task_tags, start_task, update_task, update_task_notes`
- **Status**: ✅ WORKS (M86 repair from 0.23.0 → 0.28.0)
- **Critical gap**: **NOT WIRED to deep-agent** (see M96 report) — needs `MultiServerMCPClient` integration
- **Y access today**: Claude Code (via MCP config), direct stdio from Python

#### taskdog CLI (pipx 0.28.0)
- **22 subcommands**: `add, audit, cancel, db, dep, done, export, fix-times, gantt, list, note, optimize, pause, reopen, restore, rm, show, start, stats, tag, timeline, tui, update`
- **Y access**: `taskdog <subcmd>` from any shell
- **Status**: ✅ works (M86 reinstalled 0.28.0)

#### IKIGAI MCP server (`src/ikigai/src/mcp_server/server.py`)
- **19 `@MCP.tool` decorators** registered:
  - 3 plan C investigation: `ikigai_decompose, ikigai_write_tasks, ikigai_read_tasks, ikigai_mesh_show, ikigai_task_create, ikigai_health`
  - 3 vault: `vault_write, vault_read` (+ `ikigai_sync_vault` private)
  - 3 investigation: `investigation_enqueue, investigation_status, investigation_complete`
  - 7 v2 graph entry_points: `ikigai_observe_state, ikigai_score_vectors, ikigai_heuristics, ikigai_balance, ikigai_plan, ikigai_reflect, ikigai_tag_and_persist, ikigai_commit_summary`
- **Y access**: Claude Code (via MCP config), `taskdog-mcp` for taskdog, `ikigai-maintainer-mcp` for v2
- **Status**: ✅ registered (M93 verified), used by LangGraph dev server + Claude Code

#### vault/ (markdown source of truth)
- **Layout**: Obsidian-style markdown files with YAML frontmatter (UEID, dates, tags)
- **Locked**: `vault_write` is the ONLY writer (ADR-029); all other access is read-only
- **Path-traversal protection**: enforced at write-time
- **Atomic writes**: yes (read-modify-write cycle)
- **Y access**: `vault_write`, `vault_read`, `ikigai_read_vault`, `ikigai_write_strategics` tools
- **Y practical**: `life` CLI uses it for skill outputs, vault_write atomic per cycle

#### memory_db (SQLite)
- **Tables**: `memory_daily_intentions`, `memory_weekly_aggregations`, `memory_monthly_syntheses`, `memory_quarterly_strategies` (per ADR-028 R5)
- **Y access**: `read_daily_intentions`, `read_weekly_aggregations`, etc.
- **Used by**: `recall_node` in v2 graph (loads last 14 days of daily intentions for context)
- **Y practical**: feeds the IKIGAI cycle state with recent journal content

---

### Layer 2: Agents (LangChain `@tool` Decorators)

`src/ikigai/src/agents/tools.py` defines **IKIGAI_TOOLS = [...]** with exactly **12 entries** (drift-detector-pinned via `test_ikigai_tools_count_is_12`).

#### Tool inventory (12 active)

| # | Tool | Purpose | When agent uses it |
|---|---|---|---|
| 1 | `solverforge_list_events(days=7)` | list calendar events | "what's on my calendar this week" |
| 2 | `solverforge_create_event(title, date, time)` | create event | "add meeting Friday 3pm" |
| 3 | `tuiboard_list_boards()` | list kanban boards | "what boards exist" |
| 4 | `tuiboard_get_tasks(board, column, filter_)` | read board | "show me doing column" |
| 5 | `tuiboard_create_task(board, title, column)` | add card | "add to kanban" |
| 6 | `tuiboard_update_task(board, task_id, done, priority, tags)` | edit card | "mark done / set priority" |
| 7 | `taskdog_list_tasks(status, include_archived)` | list tasks | "show my tasks" |
| 8 | `taskdog_create_task(name)` | create task | "add task X" |
| 9 | `taskdog_complete_task(task_id)` | start+complete | "mark task done" |
| 10 | `taskdog_get_task(task_id)` | fetch task | "task #123 details" |
| 11 | `ikigai_read_strategics` | read strategics/ | "read playbooks" |
| 12 | `ikigai_read_vault` | read vault/ | "read journals" |

#### What CAN'T the agent do today (per M96)

Of 26 taskdog-mcp tools, only **4 are wired** (15%):

- ❌ `cancel_task`, `pause_task`, `reopen_task` — workflow management
- ❌ `delete_task`, `restore_task` — soft-delete
- ❌ `decompose_task` — break into subtasks
- ❌ `add_dependency`, `remove_dependency` — task graphs
- ❌ `update_task` (rich params) — priority/tags/deadline/estimate
- ❌ `set_task_tags`, `delete_tag` — granular tags
- ❌ `update_task_notes`, `get_task_notes` — notes
- ❌ `fix_actual_times` — correct timestamps
- ❌ `optimize_schedule` — algorithmic reschedule
- ❌ `get_executable_tasks` — what's ready NOW
- ❌ `list_audit_logs`, `get_audit_log` — history
- ❌ `list_algorithms`, `get_statistics`, `get_tag_statistics` — analytics

Plus `taskdog_create_task` only takes `name` — no priority/tags/deadline.

---

### Layer 3: V2 Graph (LangGraph StateGraph)

`src/ikigai/src/agents/v2/graph.py` defines `make_v2_graph(checkpoint_db, entry_point)` returning a `CompiledStateGraph`.

#### Node inventory (13 nodes per `NODES`)

```
LINEAR CHAIN (default):
  observe → recall → reason → score_vectors → heuristics → balance
         → decompose → plan → tag_and_persist → reflect → commit
         → dispatch_sub_agents → surface_intentions

TERMINAL:
  error_node (catches safe_node wrapper exceptions)

ENTRY POINTS (any of these 13):
  observe (default for daily cycle)
  recall
  reason
  score_vectors
  heuristics
  balance
  decompose
  plan (exposed as `v2 plan` CLI)
  tag_and_persist
  reflect
  commit
  dispatch_sub_agents
  surface_intentions (default for daily cycle per manifest entry_point)

META-PLAN SUBGRAPH (Plan D, separate):
  classify_intent → fetch_context → generate_proposal
  (invoked via invoke_skill("meta_plan", ...))
```

#### Node behavior

| Node | Purpose | State changes |
|---|---|---|
| `observe` | gather intent hint | adds `intent_classification` |
| `recall` | memory fetch (M88 — real impl, reads memory_db) | populates `context.recent_intentions` |
| `reason` | produce proposal (M88 — bumps `iteration`) | populates `draft_proposal` |
| `score_vectors` | score 5 IKIGAi vectors | updates `vector_scores` |
| `heuristics` | apply heuristics | updates `corrections` |
| `balance` | workload vs capacity | updates `workload_estimate` |
| `decompose` | break proposal into tasks | adds operations |
| `plan` | finalize plan | updates `phase`, `phase_weights` |
| `tag_and_persist` | write to vault (M89 — real impl) | sets `persisted`, `vault_path` |
| `reflect` | review | populates `retrospective_log` |
| `commit` | fire taskdog ops (M89 — real impl) | sets `commit_summary`, `terminated` |
| `dispatch_sub_agents` | fan-out to sub-agents (ADR-026) | populates `sub_agent_results` |
| `surface_intentions` | produce user-facing suggestions | populates `user_suggestions`, `commit_summary` |
| `error_node` | terminal fallback | sets `error_type`, `error_message` |

#### Graph safety rails

- **MAX_REASON_LOOPS = 3**: bounds recall↔reason loop (M88 fix)
- **`safe_node` wrapper**: catches exceptions per-node, populates `error_type`
- **In-memory checkpoint by default**: `make_v2_graph(checkpoint_db=":memory:")` for tests
- **Thread_id required**: SqliteSaver config needs `configurable.thread_id`
- **Failure isolation**: parent error channel NEVER propagates to sub-agents (ADR-026 S2.4)

#### LangGraph dev server (optional visual debugger)

- **File**: `langgraph.json` at repo root
- **Status**: registered (`ikigai_maintainer_v2: ./src/ikigai/src/agents/v2/graph.py:make_v2_graph`) — verified by M93
- **NOT installed**: `langgraph_cli` missing from ikigai venv
- **Would enable**: visual graph inspector at `langgraph dev --port 2024`
- **To enable**: `uv pip install langgraph-cli --python src/ikigai/.venv/Scripts/python.exe`
  OR: `make dev-graph NAME=ikigai_maintainer_v2` (wires Makefile but needs CLI installed)

---

### Layer 4: Skill Manifests + invoke_skill

`src/ikigai/src/agents/v2/skills/` contains 5 manifests:

| File | Cadence | Entry Point | Outputs | Post-processor |
|---|---|---|---|---|
| `daily.md` | 1440m (cron) | `surface_intentions` | user_suggestions pt-BR | (none — read-only cycle) |
| `weekly.md` | 10080m (cron) | TBD | TBD | (none yet) |
| `monthly.md` | 43200m (cron) | TBD | TBD | (none yet) |
| `quarterly.md` | 129600m (cron) | `observe` | taskdog_create_task: "quarterly OKRs <date>" | taskdog_create_task fires |
| `meta_plan.md` | on-demand | meta_plan subgraph | Proposal (approval_state=pending) | proposal_executor (after approval) |

**Practical note**: only `daily.md` and `quarterly.md` actually have post-processors wired. The others are loaded but their `outputs:` declarations don't fire taskdog operations yet.

#### invoke_skill(name) lifecycle (M77+M94)

```
1. Load manifest from src/ikigai/src/agents/v2/skills/<name>.md
2. Validate entry_point against graph.NODES → ValueError if invalid
3. Log warning if entry_point_override differs from manifest default
4. Run make_v2_graph(checkpoint_db=":memory:", entry_point=<entry_point>)
5. Promote user_suggestions, commit_summary to top-level result
6. Detect taskdog output declaration → fire _fire_taskdog
7. On taskdog failure: enqueue TaskChange to data/review_queue/
8. Return result dict
```

---

### Layer 5: User Interfaces

#### life CLI (primary surface, M83-M95)

```bash
# Tasks (via taskdog-server)
life task list                                 # list 193 tasks
life task add "X" --priority 8 --tag daily     # create
life task start 162                             # PENDING → IN_PROGRESS
life task done 162                              # IN_PROGRESS → COMPLETED

# Skills (cron + on-demand)
life invoke-skill ikigai-daily                  # daily cycle (FAKE_LLM by default)
life invoke-skill ikigai-quarterly              # quarterly (fires taskdog_create_task)
life skill-list                                 # list 5 skills
life skill-show ikigai-quarterly                # full manifest dump

# v2 graph entry_points (M95)
life v2 plan                                    # meta-planner
life v2 daily                                   # alias for invoke-skill ikigai-daily
life v2 score                                   # score_vectors entry_point
life v2 regime                                  # heuristics entry_point
life v2 suggest                                 # surface_intentions entry_point
life v2 cycle                                   # observe entry_point (full cycle)

# Notify
life notify --status                           # show last notification
life notify "title" "body"                      # ad-hoc notify

# Daemons
bash .claude/helpers/daemon-manager.sh list     # 9/9 RUNNING
```

#### LangGraph dev server (optional, not installed)

```bash
make install   # installs langgraph + langgraph-checkpoint
make dev       # starts langgraph dev --port 2024
```

Then open `http://localhost:2024` for visual graph inspector. **NOT WORKING** until `langgraph-cli` is installed.

#### Claude Code (planned integration)

`Claude Code` can connect to the MCP servers (ikigai-maintainer-mcp, taskdog-mcp, vault-mcp) and use all 45+ tools directly. **NOT WIRED** — needs MCP config in `~/.claude/settings.json` or similar.

#### Direct taskdog CLI / HTTP

For power users wanting to bypass the LLM:
```bash
taskdog list                                    # 22 subcommands
taskdog add "X" --priority 8 --tag urgent       # full CLI args
curl http://127.0.0.1:8000/api/v1/tasks          # 36 REST endpoints
```

---

## Practical Usage Scenarios

### Scenario 1: Daily morning check (CRUD on tasks)

```bash
# Just list tasks
life task list | head -20

# Or via LLM
life invoke-skill ikigai-daily
# → runs surface_intentions graph → produces 4 pt-BR suggestions
# → no tasks created (daily.md has no taskdog output declared)
```

**Status**: ✅ works. **Result**: 4 surface suggestions per day.

### Scenario 2: Add high-priority task with deadline

```bash
# Via CLI (full args available)
life task add "Review PR #456" --priority 8 --tag urgent --tag byd

# Via LLM (limited — see M96)
life invoke-skill ikigai-quarterly "add review PR #456 task"
# → invoke_skill generates a proposal
# → M89 commit_node fires taskdog_create_task
# → task created with NAME = proposal target ("Review PR #456 task")
# → BUT: priority/tags/deadline NOT propagated (tool only takes name)
```

**Status**: ⚠️ partial. CLI works fully. LLM only sets name (priority/tags lost).

### Scenario 3: Complex workflow with dependencies

```bash
# CLI (works)
taskdog add "Deploy PR #456" --depends-on 200

# LLM (CANNOT)
life invoke-skill ikigai-quarterly "deploy task that depends on #200"
# → cannot express dependency (no add_dependency tool wired)
```

**Status**: ❌ CLI works, LLM cannot.

### Scenario 4: Decompose epic into subtasks

```bash
# CLI (works)
taskdog decompose 150

# LLM (CANNOT)
# → no decompose_task tool wired
```

**Status**: ❌ CLI works, LLM cannot.

### Scenario 5: Audit / history

```bash
# CLI (works)
taskdog audit-logs --since 2026-09-01

# LLM (CANNOT)
# → no list_audit_logs tool wired
```

**Status**: ❌ CLI works, LLM cannot.

### Scenario 6: Pause and resume

```bash
# CLI (works)
taskdog pause 162
taskdog reopen 162

# LLM (CANNOT)
# → no pause_task / reopen_task tools wired
```

**Status**: ❌ CLI works, LLM cannot.

### Scenario 7: Schedule optimization

```bash
# CLI (works)
taskdog optimize

# LLM (CANNOT)
# → no optimize_schedule tool wired
```

**Status**: ❌ CLI works, LLM cannot.

---

## What's Wired vs What's Not (Honest Map)

### ✅ Currently works via deep-agent (4 taskdog operations)

1. **list_tasks** — get task list (with optional status filter)
2. **create_task** — create task with NAME only (priority/tags/deadline lost)
3. **complete_task** — start + complete (combines both into one call)
4. **get_task** — fetch task details by ID

### ❌ NOT wired to deep-agent (22 of 26 taskdog-mcp tools)

See M96 report for the full gap inventory + recommended fix path (M97).

---

## Limitations — What Deep-Agent CANNOT Do (Honest)

### Functional limitations

| Cannot do | Reason | Workaround |
|---|---|---|
| Cancel a task | `cancel_task` not in IKIGAI_TOOLS | `taskdog cancel 162` direct |
| Pause a task | `pause_task` not wired | `taskdog pause 162` direct |
| Decompose epic | `decompose_task` not wired | `taskdog decompose 150` direct |
| Set task dependencies | `add_dependency` not wired | `taskdog dep 162 200` direct |
| Update task priority/tags | `update_task` not wired | `taskdog update 162 --priority 9` direct |
| View audit log | `list_audit_logs` not wired | `taskdog audit-logs` direct |
| Optimize schedule | `optimize_schedule` not wired | `taskdog optimize` direct |
| Get statistics | `get_statistics` not wired | `taskdog stats` direct |
| Decompose via LLM | `decompose_task` not wired | use `taskdog decompose` |

### Architectural limitations

- **IKIGAI_TOOLS = 12** is drift-detector-pinned (can't add more without breaking `test_ikigai_tools_count_is_12`)
- **`taskdog_create_task(name)` takes only name** — priority/tags/deadline args lost
- **`taskdog_get_task(id)` is hacky** — filters `export` list in-process (slow, doesn't see archived)
- **No retry on taskdog-server downtime** (circuit breaker exists but only retries 3 times)

### LLM context limitations

- Each `@tool` description is ~50-200 tokens
- 12 tools × ~150 tokens = ~1800 tokens of tool definitions in every prompt
- More tools = more context bloat = higher cost + more hallucination risk
- LLM sometimes calls wrong tool or invents parameters not in schema

### What the LLM is GOOD at

- Summarizing task lists
- Translating vague intent into specific task names
- Suggesting next actions based on context
- Routing between tools (call list before get)

### What the LLM is BAD at

- Long chains of dependent tool calls
- Precise task IDs (frequently confuses old vs new IDs)
- Understanding taskdog flag interactions (e.g. `--priority 8 --tag urgent` ordering)
- Error recovery (when a tool fails, LLM may retry the same way)

---

## Recommended Next Steps (Prioritized)

| Priority | Action | Effort | Impact |
|---|---|---|---|
| **P0** | User validates direction on M96 (Option 2 = MCP, Option 1 = param expansion, status quo) | 0 min | unblocks M97+ |
| **P1** | M97: wire `taskdog-mcp` via `MultiServerMCPClient` to deep-agent | 1-2 hr | +22 taskdog tools reachable from LLM |
| **P2** | M98: install `langgraph-cli` in ikigai venv | 30 min | visual debugger at `langgraph dev` |
| **P3** | M99: configure Claude Code to use ikigai-maintainer-mcp + taskdog-mcp | 1 hr | direct LLM access in Claude Code |
| **P4** | M100: extend `taskdog_create_task` to accept priority/tags/deadline (if Option 1 chosen) | 30 min | richer task creation |

**Total to 100% deep-agent coverage**: ~3-5 hours of focused work.

---

## Cross-references

- `reports/M96-taskdog-deep-agent-gap-report.md` — detailed gap inventory + decision tree
- `.claude/loop/NOTES-progress-tracking-2026-09-19.md` — daily-use status (needs correction per M96)
- `src/ikigai/src/agents/tools.py:418` — IKIGAI_TOOLS definition
- `src/ikigai/src/agents/tools_taskdog.py` — current 4 taskdog tool wrappers
- `src/ikigai/src/agents/deepagents_harness.py:236` — `create_deep_agent(tools=IKIGAI_TOOLS)`
- `src/ikigai/src/agents/v2/graph.py:57` — NODES tuple
- `src/ikigai/src/mcp_server/server.py` — 19 @MCP.tool decorators
- `langgraph.json` — graph registration

---

## Status

**SUPERSEDED by M97b + M98 + M99 + M100 (shipped 2026-09-21).**

The "Awaiting user validation" status is resolved:
- M97a: user chose Option A (MCP-wire)
- M97b (commit `873f0881`): `MultiServerMCPClient` wired → 38 tools
- M98 (`9b96e2b2`): `life v2 agent` one-shot
- M99 (`be43accf`): `life v2 chat` REPL
- M100 (`1aeb1ec2`): `life taskdog *` direct sub-app (26 commands)

This report remains as historical reference of what was true at the
moment of audit (M96 timestamp). Use the live README index in
`reports/README.md` for current status.
