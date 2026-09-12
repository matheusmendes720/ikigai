# Interface Usability Diagnostic — 2026-09-08

**Scope:** `python -m interfaces.cli` (Typer) + `python -m interfaces.tui.operator` (Textual)  
**Directive:** Test functional requirements, document findings — do NOT fix (backend not ready)

---

## CLI — `python -m interfaces.cli`

### ✅ PASS — Commands that work correctly

| Command | Result |
|---------|--------|
| `list` | Renders Rich table, 4 tasks, ✅/⬜ done markers, horizon/priority/project columns |
| `stats` | Aggregate counts by horizon + priority, completion % |
| `done <id>` | Marks task done, appends to `data/feedback.jsonl`, prints confirmation |
| `task-add --title "Teste urgency"` | Returns JSON with ueid, event_id, status=pending, review queue message |
| `mesh-show <ueid>` | JSON cross-fork view: cli slice populated, taskdog/solverforge=null, mismatches=[] |
| `plan-list` (default) | Rich table with UEID/title/due/priority |
| `plan-list --all-forks` | Rich table joining CLI + taskdog + solverforge columns per task; shows "OK" for CLI slice |
| `deep-agent-tasks` | Correctly returns "No Deep Agent tasks found." (no agent tasks exist yet) |
| `kill-switch status` | Rich table: env_var/vault_file/data_file all INACTIVE, events_in_1h=0 |
| `server ls` | Rich table: 4 adapters (a2ui, cli ✅, solverforge ❌, taskdog ❌) with slice type + path |

### ❌ FAIL — `v2 plan`

```
v2 plan "que horas são?"
```

**Error:** `ModuleNotFoundError: No module named 'observability'`

```
src/ikigai/src/agents/v2/nodes/balance.py:1
  from src.ikigai.src.agents.v2 import mcp_bridge

src/ikigai/src/agents/v2/mcp_bridge.py:32
  from observability.otel_init import get_tracer
```

**Root cause:** `observability` is a namespace package not on `sys.path` when CLI invokes the v2 graph directly. The `src.ikigai.src.agents.v2` module chain imports `mcp_bridge` → `observability.otel_init` → fails. The MCP server (which runs as a subprocess) works because `ikigai.bat mcp` sets up the correct Python path.

**Impact:** `v2 plan` command is completely broken for direct CLI invocation.

---

## TUI — `python -m interfaces.tui.operator`

### ✅ PASS — Startup + Tasks tab (tab 1)

- Starts without crash
- Renders 4 tasks in DataTable with UEID / Title / Due / Priority / Source Fork
- Live filesystem watcher correctly shows `mtime: None` when file is clean (first render)
- Footer shows keyboard bindings: `1` Tasks `2` Adapters `3` Backend `4` Queue `5` KillSwitch `d` Detail `r` Refresh `q` Quit

### ❌ FAIL — DuplicateIds on tab switch (tabs 2–5)

When pressing `2` (Adapters), `3` (Backend), `4` (Queue), or `5` (KillSwitch), the app crashes with:

```
textual.errors.DuplicateIds: An attempt was made to mount a widget with id 'summary-line' but that id is already in use.
```

**Root cause (confirmed):** Every `_render_*` method calls `content.remove_children()` then mounts `SummaryPanel(id="summary-line")`. On the second and subsequent renders of the same tab (including auto-refresh via `set_interval`), Textual's DOM re-registers the widget with the same ID — `remove_children()` only removes widgets from the DOM hierarchy, it does NOT unregister their IDs from the parent's widget registry.

**Reproduction:**
1. Start TUI → Tasks tab renders
2. Press `2` → DuplicateIds crash

**Note:** The `DuplicateIds` bug also fires on the Tasks tab itself during auto-refresh when the file mtime changes and `_render_tasks()` is called again. The 5-second auto-refresh (`_non_task_refresh`) only fires on non-tasks tabs — but `_poll_tasks_file` can trigger `_render_tasks` on its 2-second interval. In practice, if the file changes while on the Tasks tab, the crash occurs.

---

## Findings Summary

### CLI

| # | Severity | Finding |
|---|----------|---------|
| CLI-1 | HIGH | `v2 plan` crashes with `ModuleNotFoundError: observability` — broken import chain in v2 graph nodes prevents any planning invocation |
| CLI-2 | HIGH | 2 test files in `tests/ikigai/agents/v2/` fail collection with `ModuleNotFoundError: observability` — same import chain as CLI-1 |

### TUI

| # | Severity | Finding |
|---|----------|---------|
| TUI-1 | HIGH | `DuplicateIds` crash on any tab switch (tabs 2–5) — widget IDs not unregistered on `remove_children()` |
| TUI-2 | MEDIUM | `DuplicateIds` risk on Tasks tab auto-refresh when `data/tasks.jsonl` is modified externally |

### Test Suite

| # | Severity | Finding |
|---|----------|---------|
| TEST-1 | HIGH | 2 test files in `tests/ikigai/agents/v2/` fail collection — `observability` module not on pytest Python path |

---

## Recommendations

- **CLI-1:** The `v2 plan` import chain needs `observability` on the Python path, OR the lazy import in `v2.py` needs to go through the MCP subprocess route (i.e., invoke `ikigai.bat mcp` as a subprocess rather than importing the graph directly). Current architecture: the graph is invoked in-process, which requires all transitive dependencies to be importable.
- **CLI-2 / TEST-1:** Same root cause as CLI-1 — the `observability.otel_init` import in `mcp_bridge.py` is not on the Python path for direct pytest invocation. Tests that import `graph.py` or `subgraph.py` fail at collection. Fixing the `observability` path issue (CLI-1) will resolve both.
- **TUI-1:** Replace `remove_children()` + re-mount with a widget update pattern. Options: (a) keep SummaryPanel mounted permanently and just call `.update()` on it, (b) give each render a unique suffix for the widget IDs. Per directive, do NOT fix until backend is ready.

---

---

## Test Suite Results

| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| `interfaces/cli/tests/` | 98 | 0 | All CLI integration tests PASS |
| `interfaces/tui/tests/` | 5 | 0 | All TUI tests PASS |
| `tests/ikigai/agents/v2/test_commit_node.py` | — | COLLECT ERROR | `ModuleNotFoundError: observability` — same root cause as CLI-1 |
| `tests/ikigai/agents/v2/test_tag_and_persist_node.py` | — | COLLECT ERROR | Same `observability` import chain |

**Total: 103 passed, 2 collection errors (same root cause as CLI-1)**

The 2 collection errors in `tests/ikigai/agents/v2/` are the same `observability.otel_init` import chain that breaks `v2 plan` — `graph.py` → `mcp_bridge.py` → `observability.otel_init` is not on the pytest Python path for direct invocation.

---

*Diagnostic run: 2026-09-08 (updated 2026-09-09). CLI suite: 8/9 commands PASS, 1 FAIL (`v2 plan`). TUI: startup PASS, tab-switch FAIL. Test suite: 103 PASS, 2 collection errors (same root cause as CLI-1).*
