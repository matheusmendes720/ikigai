# Agent 1 — ikigai MCP + Deep Agent + LangGraph

**Source:** `Agent` tool dispatched 2026-08-27
**Scope:** Map IKIGAI MCP server, Deep Agent harness, LangGraph orchestrators, contracts layer
**Status:** COMPLETE

---

## 1. MCP Server — `src/ikigai/src/mcp_server/server.py` (701 lines)

### Tool inventory (lines 25-130)

10 tools declared, ALL 10 in `_TOOL_DISPATCH` (lines 647-658) — **ZERO gaps**:

| Tool | Purpose |
|------|---------|
| `ikigai_score` | IKIGAI vector scoring (passion/skill/market/revenue/course) |
| `ikigai_regime` | Q_HE regime classification (PUSH/MAINTAIN/REDUCE/RECOVER) |
| `ikigai_phase` | Current planning phase + transitions |
| `ikigai_decompose` | Decompose a goal into subtasks with UEID |
| `ikigai_corrections` | Retrieve corrections from latest cycle |
| `ikigai_plan_cycle` | Run a full planning cycle |
| `ikigai_checkpoint` | Save/load LangGraph checkpoints |
| `ikigai_sync_vault` | Sync vault markdown to data layer |
| `ikigai_write_tasks` | Append tasks to `data/tasks.jsonl` |
| `ikigai_read_tasks` | Read tasks from `data/tasks.jsonl` |

### Entry point

`async def main()` at line 699. Stdout protocol only (no HTTP transport).

---

## 2. Contracts layer — `src/contracts/`

| Module | Models |
|--------|--------|
| `common.py` | UEID, Period, Priority, EntityType, RegimeState |
| `task.py` | Task, Subtask, ChecklistItem, Project, Milestone, Deliverable |
| `planning.py` | PlanningCycle, Wave, Sprint, VaultEvent |
| `metrics.py` | Burndown, ExecutionRate, QHEScore |

### UEID format divergence

- `src/contracts/common.py`: `^[a-z][a-z0-9]{2,30}_[a-z0-9_]+` (underscore separator, single type prefix)
- `src/ikigai/src/ikigai/entities/ueid.py`: `namespace:type:slug:uuid:hash` (5-part, colon-separated, hash-suffixed)
- `data/tasks.jsonl` uses ikigai format; contracts enforce underscore
- **No cross-imports** between the two UEID modules

### Circular dependency

`src/contracts/metrics.py:21`:
```python
from ikigai.core.scoring.qhe import compute_qhe
```

Contracts should be a leaf layer (no upstream deps), but it depends on ikigai scoring. Breaks layering rule.

---

## 3. Deep Agent — `src/ikigai/src/agents/deepagents_harness.py`

### Tool inventory (18 tools total)

- 8 IKIGAI core tools (ikigai_score, regime, decompose, ...)
- 2 Solverforge tools (`solverforge_list_events`, `solverforge_create_event`)
- 4 Tuiboard tools (`tuiboard_list_boards`, `_get_tasks`, `_create_task`, `_update_task`)
- 4 Taskdog tools (`taskdog_list_tasks`, `_create_task`, `_complete_task`, `_get_task`)
- 4 filesystem builtins (ls, read, write, edit, glob, grep)

Tool wrappers defined at `src/ikigai/src/agents/tools.py:930-953`. **Deep Agent IS already wired to the 3 forks.**

### LLM client

```python
ChatAnthropic(
    base_url="https://api.minimax.io/anthropic",
    model="MiniMax-M2.7-highspeed"  # NOT a real Anthropic model
)
```

The Deep Agent uses a MiniMax proxy, not direct Anthropic API. This may be a development-only configuration.

---

## 4. LangGraph `ikigai_maintainer` graph

**File:** `src/ikigai/src/agents/ikigai_maintainer/graph.py` (170+ lines)

8-node pipeline:
```
observe → score_vectors → heuristics → balance → decompose → plan → reflect → commit
```

- `SqliteSaver` checkpointing (line ~120)
- 6 conditional edges
- 8 nodes implemented (verified)
- **Dead code:** routing functions `_route_after_*` (lines 139-146) — only `_route_after_observe` is used; others are unreachable

---

## 5. Hardcoded stub data (verified)

### `observe.py:117`
Returns `q_he_score: 0.65` hardcoded — not reading from real habit data.

### `score_vectors.py:_compute_passion_score` (lines 89-98)
```python
return state.get("q_he_score", 0.65) * 100.0
```
Docstring: "TODO: wire to real habit streak data — Currently uses Q_HE * 100 as placeholder".

**Bug B3 from retrospective claimed fixed — IS NOT.**

---

## 6. Empty placeholders

- `src/ikigai/src/ikigai/persistence/` — empty dir (placeholder)
- `src/ikikigai/src/ikigai/override/` — empty dir (placeholder)
- `src/ikigai/src/ikigai/cli/` — empty dir
- `src/ikigai/src/ikigai/tui/` — empty dir

These are intentional empty subpackages after reorg (per memory: "PAV cli/tui deprecated for deletion").

---

## 7. Path issues (reorg leftovers)

- `langgraph_entry.py:27` references `life-ops/ikigai/src` which no longer exists
- ikigai moved to `src/ikigai/src/agents/ikigai_maintainer/`
- `make_ikigai_graph` factory will fail at import-time without path patching

---

## 8. Test status

- 2446 unit tests passing (per prior session log)
- 13 integration tests passing
- No MCP-specific test coverage discovered in this scan
- No conftest discovery issues
