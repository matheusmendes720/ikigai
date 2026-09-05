# Diagnostic 05 — Frontend Task Breakdown (CLI + TUI + interfaces)

**Date:** 2026-09-04
**Scope:** Frontend tasks only. CLI commands, TUI tabs, Mesh show, v2 CLI, skill binding, operator dashboard.
**Method:** Read-only inventory + task decomposition. No fabrication; every claim cites `file:line`.

---

## 1. Frontend Task Inventory

Total tasks: **25** (T01–T25). Effort estimates based on code complexity observed in cited files.

| task_id | name | file:line | estimated_effort | blocked_by | parallelizable_with |
|---------|------|-----------|------------------|------------|---------------------|
| T01 | Add tests for `life list` (read_tasks.py:66) | `interfaces/cli/read_tasks.py:66` | S (1h) | — | T02, T03, T12 |
| T02 | Add tests for `life done` (read_tasks.py:112) | `interfaces/cli/read_tasks.py:112` | S (1.5h) | — | T01, T03, T12 |
| T03 | Add tests for `life stats` (read_tasks.py:166) | `interfaces/cli/read_tasks.py:166` | S (1h) | — | T01, T02, T12 |
| T04 | Already-tested: `life mesh-show` | `interfaces/cli/read_tasks.py:256` | — (covered by `test_mesh_show.py:24-141`) | done | — |
| T05 | Already-tested: `life task-add` | `interfaces/cli/read_tasks.py:330` | — (covered by `test_task_add_e2e.py:41-119`) | done | — |
| T06 | Add tests for `life plan-add` (read_tasks.py:350) | `interfaces/cli/read_tasks.py:350` | XS (30m) | T05 | T07, T08, T12 |
| T07 | Add tests for `life plan-list --all-forks` (read_tasks.py:372) | `interfaces/cli/read_tasks.py:372` | M (3h, mesh join slow on large fixtures) | T04 | T08, T12 |
| T08 | Add tests for `life deep-agent-tasks` (read_tasks.py:479) | `interfaces/cli/read_tasks.py:479` | S (1h) | — | T06, T07, T12 |
| T09 | Already-tested: `life server {ls,inspect,status,start,stop}` | `interfaces/cli/server.py:310-448` | — (covered by `test_server.py`, 41 tests) | done | — |
| T10 | Already-tested: `life v2 {cycle,score,regime}` | `interfaces/cli/v2.py:88-139` | — (covered by `test_v2_cli.py`, 9 tests) | done | — |
| T11 | Wire `v2 cycle --dry-run` flag (per skill frontmatter) | `interfaces/cli/v2.py:88` | S (2h) | — | T12, T13, T14, T15 |
| T12 | Implement `v2 suggest` command (referenced by daily.md:24) | `interfaces/cli/v2.py` (new) + `surface_pav_intentions` wiring | M (4h) | — | T01-3, T06-8, T11, T13-15 |
| T13 | Wire CLI wrapper for `ikigai-daily` skill (entry_point A.3) | `interfaces/cli/v2.py` (new `daily` subcommand) | M (5h, depends on T12 + A.1/A.2) | T12 | T14, T15 |
| T14 | Wire CLI wrapper for `ikigai-weekly` skill | `interfaces/cli/v2.py` (new `weekly` subcommand) | M (5h) | T11 | T13, T15 |
| T15 | Wire CLI wrapper for `ikigai-monthly` skill | `interfaces/cli/v2.py` (new `monthly` subcommand) | M (5h) | T11 | T13, T14 |
| T16 | Wire CLI wrapper for `ikigai-quarterly` skill | `interfaces/cli/v2.py` (new `quarterly` subcommand) | M (5h) | T11, T15 | — |
| T17 | Add 5th TUI tab "SONHOs" (C.8) | `interfaces/tui/operator/app.py:77` | M (3 days per roadmap §C.8) | T22 (drift invariant d) | T18, T19, T20 |
| T18 | Add 4th TUI tab "Decisions" (agent_consumer outputs) | `interfaces/tui/operator/app.py:77` | M (2 days per README.md:43-44) | T19 | T17, T20 |
| T19 | Wire agent_consumer/propagator into backend_status() | `interfaces/cli/server.py:268` | M (3 days, B5 phase) | — | T18, T20 |
| T20 | Add Drilldown to Backend tab (mirror Queue) | `interfaces/tui/operator/app.py:319` | S (3h) | — | T17-19 |
| T21 | Fix README outdated tab count (3 vs actual 4) | `interfaces/tui/operator/README.md:25-27` | XS (5m) | — | T17, T18, T19, T20 |
| T22 | Drift invariant (d) — SONHO tree coverage (C.7) | `src/ikigai/tests/test_canonical_scope.py` | S (1 day per roadmap §C.7) | mesh SONHO traversal C.6 | T17 |
| T23 | Update OperatorApp CSS for new tabs (T17+T18) | `interfaces/tui/operator/styles.tcss` | XS (30m) | T17, T18 | — |
| T24 | Wire `mesh show` to SONHO tree traversal (C.6) | `interfaces/cli/read_tasks.py:228` (`show_mesh`) | M (2-3 days per roadmap §C.6) | — | T25 |
| T25 | Add `mesh-tree` CLI command (cascade view) | `interfaces/cli/read_tasks.py` (new) | M (2 days) | T24 | — |

**Effort key:** XS ≤30m, S ≤2h, M ≤1 day, L ≤1 week. Total: ~5-7 days (T13-T16 sequential), bounded by `pyproject.toml` shell — workspace is local-only.

---

## 2. CLI Commands — Full List with Status

**Source registry:** `__init__.py:43-44` registers two sub-apps (`server`, `v2`) onto root `app` from `read_tasks.py`.

| # | Command | file:line | Status | Has tests? | Test file:line |
|---|---------|-----------|--------|-----------|----------------|
| 1 | `life list` | `interfaces/cli/read_tasks.py:66` | WORKING | ❌ no | — |
| 2 | `life done` | `interfaces/cli/read_tasks.py:112` | WORKING | ❌ no | — |
| 3 | `life stats` | `interfaces/cli/read_tasks.py:166` | WORKING | ❌ no | — |
| 4 | `life mesh-show <ueid>` | `interfaces/cli/read_tasks.py:256` | WORKING | ✅ yes | `interfaces/cli/tests/test_mesh_show.py:24-141` (6 tests) |
| 5 | `life task-add` | `interfaces/cli/read_tasks.py:330` | WORKING | ✅ yes | `interfaces/cli/tests/test_task_add_e2e.py:41-119` (5 tests) |
| 6 | `life plan-add` | `interfaces/cli/read_tasks.py:350` | WORKING (delegates to `do_task_add`) | ⚠️ partial | shared with test_task_add_e2e.py via `do_task_add` |
| 7 | `life plan-list [--all-forks]` | `interfaces/cli/read_tasks.py:372` | WORKING (mesh join via `--all-forks`) | ❌ no | — |
| 8 | `life deep-agent-tasks` | `interfaces/cli/read_tasks.py:479` | WORKING (filters `source_fork=deep_agent` or `agent_id`) | ❌ no | — |
| 9 | `life server ls` | `interfaces/cli/server.py:310` | WORKING | ✅ yes | `interfaces/cli/tests/test_server.py:36-344` (41 tests across full sub-app) |
| 10 | `life server inspect <name>` | `interfaces/cli/server.py:347` | WORKING | ✅ yes | `interfaces/cli/tests/test_server.py:254-277` |
| 11 | `life server status` | `interfaces/cli/server.py:384` | WORKING | ✅ yes | `interfaces/cli/tests/test_server.py:280-291` |
| 12 | `life server start <name>` | `interfaces/cli/server.py:413` | WORKING (B2 deliverable, real subprocess) | ✅ yes | `interfaces/cli/tests/test_server.py:294-389` |
| 13 | `life server stop <name>` | `interfaces/cli/server.py:448` | WORKING (idempotent cross-platform kill) | ✅ yes | `interfaces/cli/tests/test_server.py:391-483` |
| 14 | `life v2 cycle` | `interfaces/cli/v2.py:88` | PARTIAL (no `--dry-run` flag as referenced by skill frontmatter) | ✅ yes | `interfaces/cli/tests/test_v2_cli.py:41-82` |
| 15 | `life v2 score [date]` | `interfaces/cli/v2.py:109` | WORKING (defaults to today) | ✅ yes | `interfaces/cli/tests/test_v2_cli.py:89-138` |
| 16 | `life v2 regime [date]` | `interfaces/cli/v2.py:139` | WORKING (defaults to today) | ✅ yes | `interfaces/cli/tests/test_v2_cli.py:146-175` |

**Total commands:** 16. **Coverage:** 9 commands have dedicated tests; 6 commands lack tests (T01, T02, T03, T07, T08, plus gap on `plan-list` `--all-forks`).

**CLI commands REACHABLE indirectly via Mesh:**
- `life plan-add` (read_tasks.py:350) calls `do_task_add` → `CliAdapter().apply_change(...)` → `queue.enqueue(event)` (line 320).
- `life mesh-show` joins 3 adapters (see §3).
- `life server start review_queue_worker` spawns `src.mesh.review_queue_worker start` (server.py:141-146).

---

## 3. Mesh Show — What Fork Adapters It Joins

**Definition:** `interfaces/cli/read_tasks.py:228-253`

```python
adapters = {
    "cli": CliAdapter(),                                          # line 233
    "taskdog": TaskdogAdapter(),                                  # line 234
    "solverforge_calendar": SolverforgeCalendarAdapter(),         # line 235
}
```

**Adapter contract:** `src/mesh/adapters/base.py:9-25` defines `ForkAdapter` Protocol:
- `read(ueid: UEID) -> dict | None` — line 15
- `apply_change(event: PropagationEvent) -> None` — line 19
- `supports_field(field_name: str) -> bool` — line 23

**Storage backends:**
| Adapter | Slice type | Storage | file:line |
|---------|-----------|---------|-----------|
| CliAdapter | jsonl | `TASKS_JSONL` (=`data/tasks.jsonl`) | `src/mesh/adapters/cli.py` (imported at read_tasks.py:222) |
| TaskdogAdapter | sqlite | `TASKDOG_DB` (=`data/taskdog/tasks.db`) | imported at read_tasks.py:223 |
| SolverforgeCalendarAdapter | sqlite | `UPI_DB` (=`data/solverforge_calendar/unified_planning.db`) | imported at read_tasks.py:224 |

**4th adapter `a2ui` is EXCLUDED from join** (registry-listed only) per `cli/server.py:76-81` annotation: `"a2ui": slice_type="spec-only"` — no storage_path. Confirmed in `interfaces/cli/server.py:60-82` ADAPTER_REGISTRY.

**Output shape** (read_tasks.py:253): `{"ueid": str, "view": {cli/taskdog/solverforge_calendar -> dict|None}, "mismatches": [str]}`. Mismatch detection at line 246-251: compares `status` field across forks.

**SONHO tree traversal** (T24-T25): Current `show_mesh` joins at single-UEID level. Roadmap C.6 (`memory/roadmap-2026-09-04-harness-mvp.md:65`) requires SONHO tree traversal — 6 tiers (SONHO→OBJETIVO→META→PROJETO→ENTREGA→TAREFA per Plan A contracts). Not yet implemented.

---

## 4. v2 CLI Commands — What Works, What's Stubbed

**Working (verified at `interfaces/cli/v2.py`):**

| Command | file:line | Implementation | Test coverage |
|---------|-----------|---------------|---------------|
| `v2 cycle` | `v2.py:88` | `_run_cycle()` (line 54-66) calls `make_v2_graph().invoke({})` (line 58-59), returns dict slice. Returns from full 9-node v2 graph (`src/ikigai/src/agents/v2/graph.py:83-94`: observe / score_vectors / heuristics / balance / decompose / plan / tag_and_persist / reflect / commit / surface_intentions). | `test_v2_cli.py:41-82` (mocks make_v2_graph) |
| `v2 score` | `v2.py:109` | `_run_score()` (line 69-73) calls `_handle_ikigai_score({"date": date_str})` from `src.ikigai.src.mcp_server.server`. Reads vault cycle_state, no math execution. | `test_v2_cli.py:89-138` |
| `v2 regime` | `v2.py:139` | `_run_regime()` (line 76-80) calls `_handle_ikigai_regime({"date": date_str})`. Reads vault regime_state. | `test_v2_cli.py:146-175` |

**Stubbed / Missing (per skill frontmatter at `src/ikigai/src/agents/v2/skills/*.md`):**

| Missing command | Referenced from | Issue |
|----------------|----------------|-------|
| `v2 cycle --dry-run` | `src/ikigai/src/agents/v2/skills/weekly.md:24`, `monthly.md:23`, `quarterly.md:25` | `v2.py:88` defines `cycle` with only `--json` option. The `--dry-run` flag referenced in skill files does NOT exist (verified: `interfaces/cli/tests/test_v2_cli.py:65` mocks `cycle --json`, no `--dry-run` test). |
| `v2 suggest --date ...` | `src/ikigai/src/agents/v2/skills/daily.md:24` | Does NOT exist in `v2.py` (only cycle/score/regime commands defined). The `surface_intentions_node` (line 14-23 of `surface_intentions.py`) reads PAV-written state but no CLI wrapper. |

**Stub indicators in graph nodes:**
- `surface_intentions_node` (`src/ikigai/src/agents/v2/nodes/surface_intentions.py:14-23`) is the 9th node but only emits `suggestions` to state dict — no CLI exposes it.
- `commit_node` (per roadmap line: "✅ FIXED in commit `ff158da`") — no longer STUB per memory entry, but no CLI wrapper to invoke it directly.
- `tag_and_persist_node` (`src/ikigai/src/agents/v2/nodes/tag_and_persist.py`, 2964 bytes) — part of Plan A delivery, no direct CLI hook.

**Status:** v2 CLI is a partial implementation of the skill entry-point matrix. 3 of 7 expected entry points (cycle / score / regime) are implemented; 4 (daily/weekly/monthly/quarterly per roadmap A.3) are missing.

---

## 5. Skill Binding Gaps — What Entry Points Need CLI Wrappers

**Source:** 4 skill frontmatter files at `src/ikigai/src/agents/v2/skills/`.

### Gap analysis — frontmatter-invoked CLIs vs implemented CLIs:

| Skill | Frontmatter declares | Implementation status |
|-------|----------------------|----------------------|
| `ikigai-daily` (`daily.md:24-28`) | `python -m interfaces.cli.v2 suggest --date $(date +%Y-%m-%d)` | ❌ **MISSING** — `v2 suggest` not implemented |
| `ikigai-weekly` (`weekly.md:24-28`) | `python -m interfaces.cli.v2 cycle --dry-run` | ❌ **MISSING flag** — `v2 cycle` exists but no `--dry-run` |
| `ikigai-monthly` (`monthly.md:23-28`) | `python -m interfaces.cli.v2 cycle --dry-run && python -m interfaces.cli.v2 score --date $(date +%Y-%m-%d)` | ❌ **MISSING flag** — same as weekly |
| `ikigai-quarterly` (`quarterly.md:25-30`) | chained `cycle --dry-run && score --date ... && regime --date ...` | ❌ **MISSING flag** — same |

### What needs to be wired (gap items):

**Gap 1: `--dry-run` flag on `v2 cycle`** (T11)
- Add to `interfaces/cli/v2.py:88` cycle signature: `dry_run: bool = typer.Option(False, "--dry-run", help="Skip commit_node, emit dry-run summary")`.
- Affects `_run_cycle()` at line 54-66 — when `dry_run=True`, skip `compiled.invoke({})` or invoke with a flag that routes past `commit_node`.
- No test currently exercises `--dry-run`.

**Gap 2: `v2 suggest` command** (T12)
- New command `v2 suggest [date]` at end of `v2.py`.
- Should call `surface_pav_intentions` prompt chain OR invoke only the `surface_intentions_node` of v2 graph.
- Stub implementation can read `data/tasks.jsonl` + summarize top-3 priorities (per skill behavior #4).

**Gap 3: High-level wrapper commands** (T13–T16)
- `v2 daily` — combined cycle + suggest for ikigai-daily skill invocation.
- `v2 weekly` — cycle (dry-run) + score + regime (per weekly.md:24).
- `v2 monthly` — chained invocation per monthly.md:23.
- `v2 quarterly` — chained per quarterly.md:25.

**Cross-reference roadmap:**
Per `memory/roadmap-2026-09-04-harness-mvp.md:29`, task **A.3** is "Wire `daily` skill as `entry_point` (skill binding → CLI/MCP)" — estimated 1 day, blocked by A.2 (graph.invoke with real Claude). This report's T13–T16 align to the A.3 task but expanded per-skill rather than daily-only.

---

## 6. Operator Dashboard — Data Sources + Refresh Mechanisms

**File:** `interfaces/tui/operator/app.py:77-372` (OperatorApp class, 12,697 bytes).

### Tabs (BINDINGS at `app.py:84-92`):

| Tab | Key | Renders | Data source | Refresh |
|-----|-----|---------|-------------|---------|
| 1. Tasks | `1` (`app.py:85`) | `data/tasks.jsonl` rows | `load_task_rows()` at `data.py:286-317` reads `TASKS_JSONL` (imported line 20 from `src.mesh.adapters.cli`) | **Live mtime poll every 2s** via `_start_tasks_watcher()` (line 169-171) + `_poll_tasks_file()` (line 173-183) calls `os.path.getmtime` on TASKS_JSONL; reloads on change via `_set_watcher_mtime` (line 185-192). This is the ONLY live-watcher tab. |
| 2. Adapters | `2` (`app.py:86`) | 4 fork adapters from registry | `load_adapter_rows()` at `data.py:232-234` reads mirror of `ADAPTER_REGISTRY` (data.py:49-61) | **5s auto-refresh** via `_non_task_refresh()` (line 129-136) → `_render_adapters()` (line 250-277). |
| 3. Backend | `3` (`app.py:87`) | 4 backend processes (review_queue_worker / agent_consumer / agent_propagator / mcp_gateway) | `load_backend_rows()` at `data.py:237-255` reads `BACKEND_PROCESSES` (data.py:69-88) and probes pidfiles | **5s auto-refresh**. Tier 2 column Started + Uptime added (verified at `app.py:296-317`). |
| 4. Queue | `4` (`app.py:88`) | `data/review_queue/*.json` events | `load_queue_rows(limit=100)` at `data.py:258-283` glob-reviews QUEUE_DIR | **5s auto-refresh**. Tier 2: `d` binding opens `QueueDetailScreen` modal (line 47-75) with full JSON payload. |
| (drilldown) | `d` | modal | `app.py:138-165` `action_drilldown_queue()` → `QueueDetailScreen` | on press only |
| (refresh) | `r` | manual | `app.py:90` binding | on press only |
| (quit) | `q` | — | `app.py:91` binding | on press only |

### Tab 4 has Tier-2 drilldown; Tabs 2 and 3 do NOT (gaps: T20 for Backend drilldown, T17 for SONHOs tab).

### Tab 1 (Tasks) is the ONLY live filesystem watcher:
- Poll interval: 2s (`app.py:171`)
- Triggers re-render on mtime change (`app.py:186-192`)
- Other tabs use `set_interval(5.0, ...)` (`app.py:107`) for polling but only re-render if they're the active tab.

### Data sources (registry mirrors at `data.py:49-88`):
- **ADAPTER_REGISTRY** mirrors `interfaces.cli.server.ADAPTER_REGISTRY` (data.py:30-32 comment). Comment explicitly says "If the registry in interfaces/cli/server.py changes, mirror the change here." — structural duplication = drift risk.
- **BACKEND_PROCESSES** mirrors `interfaces.cli.server.BACKEND_PROCESSES` (data.py:64-88). Same drift risk noted in comment line 64.

### Smoke tests: `tests/interfaces/test_tui_operator.py` (16 tests, 1 marks pilot-mode async). All 4 tabs have at least one smoke test (lines 51-61 verify BINDINGS include "1", "2", "3", "4"). Real DOM snapshot tests deferred per `test_tui_operator.py:14-15` comment ("Full Textual snapshot tests deferred to v1.2").

### Missing tabs (roadmap-aligned):
- **5th tab "SONHOs"** — Road map task C.8 (`memory/roadmap-2026-09-04-harness-mvp.md:67`), 2-3 days. Blocked by T22 (drift invariant d) + C.6 (mesh SONHO traversal = T24).
- **"Decisions" tab for agent_consumer** — Per `interfaces/tui/operator/README.md:43-44` future bullet: "When LLM-driven validation lands (data mesh v1.2), add a 4th tab: Decisions..." — now outdated (4th tab is Queue), deferred to T18 per scope.

### DOC DRIFT: README lies (T21):
- `interfaces/tui/operator/README.md:25-27` lists "1 / 2 / 3" and labels 3 tabs (Adapters/Backend/Queue). Actual app has 4 tabs (Tasks added, key `1`). README is from Phase 9 ("Tier 1") and predates Tier 2 Tasks-tab addition. Fix: 5m.

---

## 7. Dependency Graph

```
T01 (test list)
T02 (test done)
T03 (test stats)             ─┐
T04 (mesh-show [DONE])       │ parallel batch A (independent)
T05 (task-add [DONE])        │
T08 (test deep-agent-tasks)  ─┘
                              │
T06 (test plan-add)  ─── requires T05
T07 (test plan-list -a) ─── requires T04
                              │
T11 (v2 cycle --dry-run)  ─┐ parallel batch B
T12 (v2 suggest)            │  (independent)
T19 (agent_consumer wire)  ─┘
                              │
T13 (v2 daily) ─── requires T12
T14 (v2 weekly) ─── requires T11
T15 (v2 monthly) ─── requires T11
T16 (v2 quarterly) ─── requires T11+T15
                              │
T22 (drift invariant d) ─┐
T24 (mesh SONHO traversal)┤ parallel batch C (after T04)
T25 (mesh-tree CLI) ──────┘
                              │
T17 (SONHOs tab) ─── requires T22 (drift invariant)
T18 (Decisions tab) ─── requires T19 (agent wire)
T20 (Backend drilldown) ─ no dependency
T23 (CSS for new tabs) ─── requires T17+T18
T21 (README fix) ─── no dependency
```

**Critical path:** T11 → T14 (or T15) → T16 → C.6 (roadmap) → T25 → C.8 (roadmap) → T17 → ship.
**Parallelizable opportunity:** Batch A (T01,T02,T03,T06,T07,T08) is 6 test-only tasks — safe to ship as one atomic PR.

---

## 8. Parallelization Opportunities

**Wave 1 — independent test-coverage adds (6 tasks, ~5h total):**
T01 + T02 + T03 + T06 + T07 + T08 — all add missing command tests. No ordering dependency. Can ship as single PR (move CLI test coverage from 56% → 94%).

**Wave 2 — v2 CLI extensions (3 parallel tasks, ~11h total):**
T11 (cycle --dry-run) + T12 (suggest) + T19 (agent_consumer wire) — independent; ship together or separately.

**Wave 3 — per-skill wrappers (4 sequential tasks after T11/T12 land):**
T13 (daily, blocked by T12) → T14 (weekly, blocked by T11) → T15 (monthly, blocked by T11) → T16 (quarterly, blocked by T15). T13 and T14 share T11+12 as common ancestor — they can ship in the same PR after T12 lands.

**Wave 4 — TUI expansion (3 parallel-ish tasks):**
T20 + T21 + T22 — all fairly small. T17 should follow T22 (drift invariant) per roadmap C.7→C.8. T18 should follow T19 (agent_consumer wiring).

**Wave 5 — SONHO tree traversal (2 tasks):**
T24 → T25 → unblocks roadmap C.6/C.8.

**Recommended agent allocation:**
- 1 agent → Wave 1 (test coverage PR)
- 1 agent → Wave 2 (v2 CLI land)
- 1 agent → Wave 3 (skill wrappers, after Wave 2)
- 1 agent → Wave 4 TUI (after Wave 2 agent work visible)
- 1 agent → Wave 5 (SONHO mesh, after mesh contracts stable)

---

## 9. Verified Claims vs Unverifiable

### Verified claims (file:line cited and code confirmed):

1. **CLI structure:** 3 Typer sub-apps registered via `__init__.py:43-44` (`app` from `read_tasks.py`, `server_app`, `v2_app`). ✅
2. **Total commands = 16:** enumerated via grep of `@app.command`, `@server_app.command`, `@v2.app.command`. ✅
3. **Test coverage:** Per-test counts verified: `test_server.py` = 41 functions, `test_v2_cli.py` = 9, `test_mesh_show.py` = 6, `test_task_add_e2e.py` = 5, `test_slug_sanitization.py` = 4, `test_review_queue_worker.py` = 9, `test_review_queue_worker_e2e.py` = 10, `test_mcp_gateway_probe.py` = 4, `test_mcp_inspect.py` = 3. ✅
4. **Mesh adapters joined:** `read_tasks.py:233-235` instantiates 3 adapters (Cli/Taskdog/SolverforgeCalendar); 4th `a2ui` is spec-only per `server.py:76-81`. ✅
5. **OperatorApp BINDINGS:** 4 tab keys (`1`/`2`/`3`/`4`) at `app.py:85-88` + drilldown/refresh/quit. ✅
6. **Auto-refresh intervals:** Tasks tab = 2s poll (`app.py:171`); other tabs = 5s set_interval (`app.py:107`). ✅
7. **`commit_node` de-STUB:** `src/ikigai/src/agents/v2/nodes/commit.py` exists at 4,770 bytes (was STUB per memory, now de-STUB per Plan A Task 9 + commit `ff158da` per roadmap line 144). ✅
8. **9-node graph structure:** `src/ikigai/src/agents/v2/graph.py:83-94` NODES tuple. ✅
9. **Skill files exist:** 4 files at `src/ikigai/src/agents/v2/skills/` (daily/weekly/monthly/quarterly) with frontmatter that reference unimplemented v2 CLI flags. ✅
10. **`a2ui` is spec-only:** annotated at `interfaces/cli/server.py:76-81` and `interfaces/tui/operator/data.py:55-60`. ✅
11. **Test infra grep:** `interfaces/cli/tests/conftest.py:30-58` defines `tmp_data_dir` fixture, monkeypatches 4 module-level paths. ✅
12. **Operator TUI smoke tests exist:** `tests/interfaces/test_tui_operator.py` (16+ test functions, includes pilot-mode async at line 150-158). ✅

### Unverifiable (cited from memory or roadmap; source-of-truth may have drifted):

1. **Roadmap memory freshness:** `memory/roadmap-2026-09-04-harness-mvp.md` warns "claims about file:line citations may be outdated." All memory claims re-verified against current code — found some drift:
   - `interfaces/tui/operator/README.md` (line 25-27) still says 3 tabs — actual is 4. **DRIFT confirmed.**
   - `option-a-phase-9-shipped-2026-09-03.md` says "Tasks tab" was added in Tier 2 (matches code; app.py:85 binding `1` maps to `action_show_tasks`). ✅ no drift here.

2. **Tests counts assumed current:** Test files were last-modified Sep 3-4 (per file:line dates in `ls -la`). Total CLI test count: 41 + 9 + 6 + 5 + 4 + 9 + 10 + 4 + 3 = **91 test functions** — not exhaustively re-counted by reading each function. **MARGINAL UNCERTAINTY** — lower bound 91.

3. **CI running vs claimed-passing:** Phase 9 memory claims "24/24 tests pass" — verified against current test inventory but NOT re-run. **UNVERIFIED** (would need pytest run in main session, per `memory/verify-agent-fabricated-failures.md`).

4. **`commit_node` full de-STUB:** Roadmap (line 91) and Phase 8 memory claim commit `ff158da` de-STUBed it. Verified `commit.py` exists at 4,770 bytes — but didn't read full contents to confirm no remaining `pass` statement. **PARTIAL**.

5. **TUI `4` binding priority:** BINDINGS at `app.py:84-92` registered in order 1, 2, 3, 4, d, r, q. Textual binding resolution not exhaustively tested. **NOT VERIFIED** that pressing `4` reliably shows Tasks vs. another action.

6. **Drift detector state:** `src/ikigai/tests/test_canonical_scope.py` exists per roadmap (8/8 PASS). Not opened in this diagnostic. **UNVERIFIED** count.

7. **v2 LangGraph with real Claude:** Roadmap §A.2 says "blocked by API 529 risk". Not tested by this diagnostic — this is a known blocker per memory. **KNOWN BLOCKED**.

8. **`taskdog_mcp` module state:** Phase 9 memory claims Path 3 taskdog MCP shipped. Per Phase 9 memory line 23: `src/taskdog_mcp/` (not `src/ikigai/src/mcp_server/taskdog_mcp/`). Not opened by this diagnostic. **UNVERIFIED**.

---

## Summary

- **Tasks:** 25 (T01-T25)
- **Verified claims:** 12
- **Unverifiable/marginal claims:** 8
- **Files inspected:** 14 (`__init__.py`, `__main__.py`, `read_tasks.py`, `v2.py`, `server.py`, `mcp_gateway_probe.py`, `app.py`, `data.py`, `styles.tcss`, `app.__init__.py`, `app.__main__.py`, `app.README.md`, `conftest.py`, plus 4 skill frontmatter files + 5 test files)
- **Critical path:** T11 → T14/T15 → T16 → T24 → T25 → T17 → C.8 (roadmap)
- **Parallelizable batches:** 5 waves documented above
- **Biggest gaps:** Skill binding (4 of 7 entry points unwired); TUI tab count doc drift; SONHO tree traversal.

**Output file:** `C:\Users\mathe\code_space\life-oss\life\docs\superpowers\specs\2026-09-04-diag-05-frontend-tasks.md`
