# Diag-08 — Taskdog Integration Capability Status

**Diagnostic agent:** 08 of 10
**Date:** 2026-09-04
**Branch:** `sonho-tree/plan-a-planning-contract` @ `ff158da`
**Scope:** Capability status — Taskdog integration (3 paths × 8 capabilities)

---

## 1. 3×8 Capability Matrix

Legend: ✅ working · ⚠️ partial/blocked · ❌ broken/missing · 🟡 N/A

| Path                                              | C1 Create | C2 Read | C3 Update | C4 Done | C5 Delete | C6 List | C7 Sync taskdog→mesh | C8 Sync mesh→taskdog |
|---------------------------------------------------|:---------:|:-------:|:---------:|:-------:|:---------:|:-------:|:--------------------:|:--------------------:|
| **Path 1** — harness @tool → subprocess → taskdog.exe | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ✅ | ❌ | ❌ |
| **Path 2** — mesh SQLite adapter (`data/taskdog/tasks.db`) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | 🟡¹ | ✅² |
| **Path 3** — MCP gateway → `taskdog_mcp.server` | ✅³ | ✅³ | ❌ | ✅³ | ❌ | ✅³ | ❌ | ❌ |

¹ Taskdog→mesh sync is INDIRECT: when taskdog is the `source_fork` of a TaskChange, the worker drains it from the queue and propagates to all forks; there is no native polling/pull from the taskdog fork binary.
² Mesh→taskdog sync only supports `action=create` (per `taskdog.py:83-84` `if event.action.value != "create": return`). Update/delete/done are explicitly out of v1 scope.
³ Path 3 capability was SHIPPED 2026-09-03 (commit `fe61dcc`) and ARCHIVED 2026-09-03 (commit `1cd4f31`). On-disk at HEAD, the canonical module exists at `src/ikigai/src/mcp_server/taskdog_mcp/server.py` (lines 41-122: `_handle_*` wrappers delegating to Path 1 @tools) AND the archive copy at `archive/legacy-paths/taskdog-mcp-path3/server.py`. **Working tree at 2026-09-04 has UNCOMMITTED deletes** of the canonical copy (`src/ikigai/src/mcp_server/taskdog_mcp/`); on-disk state is inconsistent with HEAD.

---

## 2. Per-Path Detail

### 2.1 Path 1 — Harness subprocess (CANONICAL)

**Source:** `src/ikigai/src/agents/tools.py`
**E2E test:** `src/ikigai/tests/test_taskdog_harness_e2e.py` (9207 bytes, 7 tests, last touched 2026-08-31)

| Capability | File:Line | Status | Notes |
|------------|-----------|--------|-------|
| **C1 Create** | `src/ikigai/src/agents/tools.py:427-453` `taskdog_create_task` | ✅ | `subprocess.run([_TASKDOG_CLI, "add", name])` (line 438). Circuit-breaker + retry decorators at lines 420-426. E2E PASS at `test_taskdog_harness_e2e.py:93-103` (`test_taskdog_create_task_invokes_binary`). |
| **C2 Read** | `src/ikigai/src/agents/tools.py:499-530` `taskdog_get_task` | ⚠️ | `subprocess.run([_TASKDOG_CLI, "show", str(task_id)])` (line 510). Lines 515-521 NOTE: `taskdog 0.23.0 'show'` has known bug (`TaskdogApiClient has no attribute get_task_detail`) — surfaces as ⚠️ string instead of raising. Functional but flaky. |
| **C3 Update** | NOT IMPLEMENTED | ❌ | No `taskdog_update_task` @tool. Drift detector at `test_taskdog_harness_e2e.py:71-84` enforces IKIGAI_TOOLS count = 12. Adding update would break the count. |
| **C4 Done** | `src/ikigai/src/agents/tools.py:463-489` `taskdog_complete_task` | ⚠️ | `subprocess.run([_TASKDOG_CLI, "done", str(task_id)])` (line 474). **Lifecycle gap**: taskdog v0.23.0 requires `start` before `done` (per memory `taskdog-3-paths-architecture-canonical-2026-08-31` and §2.3 of design doc line 56-62). E2E test at `test_taskdog_harness_e2e.py:122-157` explicitly invokes `subprocess.run([TASKDOG_CLI, "start", ...])` outside the @tool layer. Open gap (no `taskdog_start_task` @tool). |
| **C5 Delete** | NOT IMPLEMENTED | ❌ | No `taskdog_delete_task` @tool. |
| **C6 List** | `src/ikigai/src/agents/tools.py:390-417` `taskdog_list_tasks` | ✅ | `subprocess.run([_TASKDOG_CLI, "list"])` (line 401). E2E at `test_taskdog_harness_e2e.py:106-119`. |
| **C7 Sync taskdog→mesh** | NOT IMPLEMENTED | ❌ | Path 1 writes directly to taskwarrior store (`~/.task/data.db`); no code path from taskdog fork to `data/review_queue/`. |
| **C8 Sync mesh→taskdog** | NOT IMPLEMENTED | ❌ | Path 1 does not consume from `data/review_queue/`; the review-queue-worker (`src/mesh/review_queue_worker.py:42-91`) propagates to `TaskdogAdapter` (Path 2) but not to Path 1's `taskdog.exe`. The two stores are independent. |

### 2.2 Path 2 — Mesh SQLite adapter (ALTERNATIVE)

**Source:** `src/mesh/adapters/taskdog.py` (130 lines)
**CLI:** `src/mesh/taskdog_cli.py` (276 lines, read-only ops: `list`, `status`, `show`)
**Test:** `tests/mesh/adapters/test_taskdog.py` (4 tests); `src/ikigai/tests/test_taskdog_adapter_list_all.py`

| Capability | File:Line | Status | Notes |
|------------|-----------|--------|-------|
| **C1 Create** | `src/mesh/adapters/taskdog.py:82-126` `apply_change` | ✅ | Native SQLite UPSERT on `ueid` UNIQUE constraint (line 115-123). v1 ONLY supports `action="create"` (line 83-84 `if event.action.value != "create": return`). Called from `src/mesh/agent_propagator.py:23-102` `propagate()` which the review-queue-worker invokes. |
| **C2 Read** | `src/mesh/adapters/taskdog.py:31-54` `read` | ✅ | SELECT by ueid; returns dict slice or None. CLI at `taskdog_cli.py:180-202` `cmd_show`. Test at `tests/mesh/adapters/test_taskdog.py:69-79`. |
| **C3 Update** | `src/mesh/adapters/taskdog.py:83-84` | ❌ | Hard early-return on non-create actions. **Roadmap A.3 reference**: per `roadmap-2026-09-04-harness-mvp.md` §"Blocked", update/done deferred. Drift invariant is v1 create-only. |
| **C4 Done** | (same line 83-84) | ❌ | Same hard early-return. |
| **C5 Delete** | NOT IMPLEMENTED | ❌ | No delete path. |
| **C6 List** | `src/mesh/adapters/taskdog.py:56-80` `list_all` | ✅ | Returns all rows. CLI at `taskdog_cli.py:116-138` `cmd_list`. CLI at `taskdog_cli.py:140-177` `cmd_status` provides count-by-status. |
| **C7 Sync taskdog→mesh** | Indirect only | 🟡 | Taskdog fork has no producer code path into `data/review_queue/`. Reverse sync requires external actor (CLI: `python -m src.mesh.mesh_cli task add ...` enqueues a TaskChange with `source_fork="taskdog"`). Verified: `data/review_queue/*.json` shows one such event with `source_fork:"taskdog"`, `action:"done"` (status `clarified`). No automated polling. |
| **C8 Sync mesh→taskdog** | `src/mesh/agent_propagator.py:23-102` | ✅² | `propagate()` fans approved events to all 3 adapters including `TaskdogAdapter`. Worker at `src/mesh/review_queue_worker.py:42-91` calls `propagate()` per pending event. Net effect: mesh → taskdog SQLite is CREATE-ONLY (`taskdog.py:83-84`). |

### 2.3 Path 3 — MCP gateway (ARCHIVED 2026-09-03)

**Source at HEAD:** `src/ikigai/src/mcp_server/taskdog_mcp/server.py` (137 lines, ships 4 tools)
**Source archived:** `archive/legacy-paths/taskdog-mcp-path3/server.py` (137 lines)
**Archive doc:** `docs/design-system/24-taskdog-paths-architecture.md:259-281` §9 "Path 3 archived 2026-09-03"

| Capability | File:Line | Status | Notes |
|------------|-----------|--------|-------|
| **C1 Create** | `src/ikigai/src/mcp_server/taskdog_mcp/server.py:50-57` `_handle_create_task` (delegates to `taskdog_create_task`); MCP registration at lines 97-103 | ✅³ | Delegates verbatim to Path 1. Path 3 = thin MCP wrapper. |
| **C2 Read** | `src/ikigai/src/mcp_server/taskdog_mcp/server.py:70-77` `_handle_get_task`; MCP at lines 115-121 | ✅³ | Same delegation pattern. Inherits Path 1's taskdog 0.23.0 `show` bug. |
| **C3 Update** | NOT IMPLEMENTED | ❌ | No update tool registered. |
| **C4 Done** | `src/ikigai/src/mcp_server/taskdog_mcp/server.py:60-67` `_handle_complete_task`; MCP at lines 106-112 | ✅³ | Delegates to Path 1. Inherits start-before-done lifecycle gap. |
| **C5 Delete** | NOT IMPLEMENTED | ❌ | No delete tool registered. |
| **C6 List** | `src/ikigai/src/mcp_server/taskdog_mcp/server.py:41-47` `_handle_list_tasks`; MCP at lines 85-94 | ✅³ | Delegates to Path 1. |
| **C7 Sync taskdog→mesh** | NOT IMPLEMENTED | ❌ | Path 3 is gateway-only (stdio MCP server), no consumer of mesh queue. |
| **C8 Sync mesh→taskdog** | NOT IMPLEMENTED | ❌ | Same as C7. |

**Note on Path 3 lifecycle (2026-08-31 → 2026-09-03 → 2026-09-04):**
- `taskdog-3-paths-architecture-canonical-2026-08-31.md` (memory, 3 days old per `SubagentStart` reminder): Path 3 = "DEFERRED (module missing; mcp_inspect shows 15 tools, ZERO `taskdog_*`)" — accurate as of 2026-08-31.
- `option-a-phase-9-shipped-2026-09-03.md` (memory): claims "Path 3 taskdog MCP server SHIPPED" at `src/taskdog_mcp/` — **MISIDENTIFIED LOCATION**. Actual location was `src/ikigai/src/mcp_server/taskdog_mcp/`, not `src/taskdog_mcp/`. Verified by commit `fe61dcc` message and tree.
- Commit `fe61dcc` (2026-09-03 17:49): `feat(taskdog-mcp): Path 3 taskdog MCP gateway server (4 tools)` — 5/5 tests PASS at `src/ikigai/tests/test_taskdog_mcp_server.py` (file currently deleted in working tree).
- Commit `f7ba1e5` (2026-09-03 18:05): resolved duplicate Path 3 implementations; archived one to `archive/duplicate-taskdog-mcp-2026-09-03/`.
- Commit `1cd4f31` (2026-09-03 19:31): `chore(taskdog): archive Path 3 MCP server, Path 1 stays canonical` — moved to `archive/legacy-paths/taskdog-mcp-path3/` BUT did NOT remove from `src/ikigai/src/mcp_server/taskdog_mcp/` (confirmed via `git show 1cd4f31 --stat`: only adds, no removes). Result: **both copies exist at HEAD**.
- Working tree at 2026-09-04: `git status` shows `deleted: src/ikigai/src/mcp_server/taskdog_mcp/__init__.py`, `deleted: src/ikigai/src/mcp_server/taskdog_mcp/server.py`, `deleted: src/ikigai/tests/test_taskdog_mcp_server.py` (all uncommitted). On-disk: canonical Path 3 module is GONE; archive copy survives.

**Effective state at 2026-09-04 disk:** Path 3 is reachable via archive (`archive/legacy-paths/taskdog-mcp-path3/server.py`) but NOT installed — `python -m mcp_server.taskdog_mcp.server` will fail with `ModuleNotFoundError` since the package directory is uncommitted-deleted.

---

## 3. Path 3 Status Confirmation

**Per memory `taskdog-3-paths-architecture-canonical-2026-08-31.md` (verified pre-Phase 9):** Path 3 = DEFERRED, module missing. ✅ accurate on 2026-08-31.

**Per memory `option-a-phase-9-shipped-2026-09-03.md`:** Path 3 SHIPPED at `src/taskdog_mcp/`. ❌ **WRONG LOCATION** — actual module shipped at `src/ikigai/src/mcp_server/taskdog_mcp/`.

**Per `git log --all` reconstruction:** Path 3 was:
1. Shipped 2026-09-03 17:49 (commit `fe61dcc`) at `src/ikigai/src/mcp_server/taskdog_mcp/` with 5/5 tests PASS.
2. Archived 2026-09-03 19:31 (commit `1cd4f31`) to `archive/legacy-paths/taskdog-mcp-path3/`. The archive commit ADDED files but did NOT REMOVE the canonical copies — both exist at HEAD (verified via `git ls-tree HEAD`).
3. Working tree at 2026-09-04 07:27 has UNCOMMITTED DELETES of the canonical copies (`src/ikigai/src/mcp_server/taskdog_mcp/__init__.py`, `server.py`, `tests/test_taskdog_mcp_server.py`).

**Verdict for diag-08:** Path 3 is in a TRANSITIONAL/INCONSISTENT state. As-shipped in commit history it provides Create/Read/List/Done capabilities, but on the live working tree (uncommitted deletes), it is functionally OFF — only the archive copy survives. Until the deletes are committed (or reverted), `python -m mcp_server.taskdog_mcp.server` will return `ModuleNotFoundError` matching the original 2026-08-31 fabricated-claim verdict.

**Recovery path:** `git checkout HEAD -- src/ikigai/src/mcp_server/taskdog_mcp/ src/ikigai/tests/test_taskdog_mcp_server.py` (restores canonical copy). OR use archive copy: `cd archive/legacy-paths/taskdog-mcp-path3 && python -m server`.

---

## 4. Critical Blockers (top 5)

1. **`taskdog start` gap blocks Path 1 C4 Done** — `tools.py:463-489` wraps `taskdog done` directly, but taskdog v0.23.0 enforces `pending → active → completed`. E2E test at `test_taskdog_harness_e2e.py:122-157` sidesteps by calling `taskdog start` via subprocess OUTSIDE the @tool layer. No `taskdog_start_task` @tool exists. **Blocks: agent-driven done flows.**

2. **Mesh v1 = create-only** — `taskdog.py:83-84` hard early-return on non-create actions. Update/Delete/Done NOT supported at the mesh level (Path 2). **Blocks: full lifecycle sync via mesh propagation.**

3. **Path 3 module deleted from working tree** — Canonical copy `src/ikigai/src/mcp_server/taskdog_mcp/{__init__.py,server.py}` shows as uncommitted delete in `git status`. Survives only in `archive/legacy-paths/taskdog-mcp-path3/`. **Blocks: any Path 3 consumer; aligns with subagent fabrication memory which said Path 3 was missing.**

4. **`taskdog 0.23.0 show` bug** — Per `tools.py:515-521` NOTE: `TaskdogApiClient has no attribute get_task_detail`. Path 1 C2 Read surfaces error string instead of raising. **Blocks: reliable single-task lookup.**

5. **Path 1 ↔ Mesh dual-store inconsistency** — Path 1 writes to `~/.task/data.db` (taskwarrior); Path 2 writes to `data/taskdog/tasks.db`. There is NO code that reconciles these two stores. Per design doc §6 anti-pattern #5 (`docs/design-system/24-taskdog-paths-architecture.md:218`): "Misturar Path 1 + Path 2 stores — são stores independentes; sincronização entre elas é best-effort eventual." **Blocks: unified observability; user-visible divergence.**

---

## 5. Coverage Summary

**Per-capability totals (across 3 paths, 8 caps each = 24 cells):**

| Status | Count | Cells |
|--------|------:|-------|
| ✅ working | 9 | P1: C1, C6; P2: C1, C2, C6, C8; P3: C1, C2, C4, C6 |
| ⚠️ partial/blocked | 2 | P1: C2, C4 |
| ❌ broken/missing | 12 | P1: C3, C5, C7, C8; P2: C3, C4, C5, C7; P3: C3, C5, C7, C8 |
| 🟡 N/A | 1 | P2: C7 (indirect only) |

**Coverage by capability (8 caps × 3 paths):**
- **C1 Create**: 3/3 paths (P1 ✅, P2 ✅, P3 ✅³)
- **C2 Read**: 3/3 paths (P1 ⚠️, P2 ✅, P3 ✅³)
- **C3 Update**: 0/3 paths (all ❌)
- **C4 Done**: 2/3 paths (P1 ⚠️, P3 ✅³, P2 ❌)
- **C5 Delete**: 0/3 paths (all ❌)
- **C6 List**: 3/3 paths (P1 ✅, P2 ✅, P3 ✅³)
- **C7 Sync taskdog→mesh**: 0/3 paths (P2 🟡 indirect via TaskChange producer)
- **C8 Sync mesh→taskdog**: 1/3 paths (P2 ✅ create-only)

**Path 3 coverage is theoretical** — depends on working-tree delete resolution.

---

## 6. Verified Claims vs Unverifiable

### Verified claims (read directly from disk/git)

1. ✅ Path 1 has 4 taskdog @tools wired at `src/ikigai/src/agents/tools.py:566-569` (`IKIGAI_TOOLS` block)
2. ✅ Path 1 `_TASKDOG_CLI` defaults to `"taskdog.exe"` at `tools.py:45`
3. ✅ Path 1 drift detector at `src/ikigai/tests/test_taskdog_harness_e2e.py:71-84` enforces 12-tool count
4. ✅ Path 1 E2E test file exists at `src/ikigai/tests/test_taskdog_harness_e2e.py` (9207 bytes, dated 2026-08-31)
5. ✅ Path 2 adapter at `src/mesh/adapters/taskdog.py:83-84` hard early-returns on non-create
6. ✅ Path 2 SQLite path = `data/taskdog/tasks.db` (per `taskdog.py:10-11` `TASKDOG_DB = PROJECT_ROOT / "data" / "taskdog" / "tasks.db"`); directory DOES NOT exist on disk at 2026-09-04 (created lazily on first write per `taskdog.py:86` `TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)`)
7. ✅ Path 2 CLI at `src/mesh/taskdog_cli.py` (276 lines) supports `list`, `status`, `show` subcommands
8. ✅ Path 2 review queue worker at `src/mesh/review_queue_worker.py:203-208` builds 3 adapters (CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter)
9. ✅ Path 3 was shipped in `fe61dcc` (2026-09-03) with 5/5 tests
10. ✅ Path 3 was archived to `archive/legacy-paths/taskdog-mcp-path3/` in `1cd4f31` (2026-09-03)
11. ✅ Both canonical and archive Path 3 copies exist at HEAD (`git ls-tree HEAD` confirmed)
12. ✅ Working tree has uncommitted deletes of canonical Path 3 module (`git status` confirmed)
13. ✅ MCP gateway `src/ikigai/src/mcp_server/server.py` registers 17 tools, NONE named `taskdog_*` (verified via grep: only mentions at lines 377, 466 are descriptive comments)
14. ✅ `data/review_queue/*.json` contains TaskChanges with `source_fork:"taskdog"` (verified one event at `data/review_queue/0b583b99-98ad-4290-8a1f-5fdae4418edc.json` with `action:"done"`, `status:"clarified"`)
15. ✅ Drift detector `ForkAdapter` coverage at `src/ikigai/tests/test_canonical_scope.py:347-364` includes taskdog adapter (comment at line 350)

### Unverifiable claims (memory-only, NOT independently verified on disk today)

1. ⚠️ Memory `taskdog-3-paths-architecture-canonical-2026-08-31.md` says "7/7 E2E PASS" for Path 1 — file `test_taskdog_harness_e2e.py` exists with 7 test functions, but actual current PASS/FAIL status NOT re-run (taskdog.exe binary presence not verified at 2026-09-04).
2. ⚠️ Memory `option-a-phase-9-shipped-2026-09-03.md` claims Path 3 lives at `src/taskdog_mcp/` — **REFUTED by git log** (actual location `src/ikigai/src/mcp_server/taskdog_mcp/`).
3. ⚠️ Memory `roadmap-2026-09-04-harness-mvp.md` line 92 says taskdog Path 1 has "7/7 E2E pass" — file has 7 test functions but pytest invocation not run for this diagnostic.
4. ⚠️ Lifecycle behavior: `taskdog 0.23.0 done requires prior start` — per doc + memory only, not re-executed.

---

## 7. Counts

- **Verified claims:** 15
- **Unverifiable claims:** 4
- **3×8 cells:** 24 total
  - ✅ working: 9
  - ⚠️ partial/blocked: 2
  - ❌ broken/missing: 12
  - 🟡 N/A: 1

---

*Diag-08 — Taskdog Capability Status — 2026-09-04 — Read-only investigation; no code modified*