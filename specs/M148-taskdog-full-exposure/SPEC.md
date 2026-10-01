---
name: M148-taskdog-full-exposure
description: Full taskdog exposure via IKIGAI bridge — 12 MCP tools. Writes via ADR-014 queue.
status: PENDING
owner: loop-orchestrator
created: 2026-09-29
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
  - reversibility_over_cleverness
  - state_on_disk_not_conversation
estimated_cost_usd: 0.80
---

# M148 — Full taskdog exposure via IKIGAI bridge

## Goal
Expose all taskdog operations to Deep Agent via IKIGAI MCP bridge. Every write routes through the existing review queue (ADR-014 intact). Agent_consumer validates, propagator fans out to the 3 forks (CLI + taskdog + calendar).

## Scope (honest inventory, verified by reading code)

### Layer 1 — `src/mesh/adapters/taskdog.py` (adapter expansion)
Currently `apply_change(event)` only handles `action="create"` (line ~200). We extend it to handle:

| TaskAction | SQLite op | Notes |
|---|---|---|
| `CREATE` | `INSERT OR REPLACE` | already works |
| `UPDATE` | `UPDATE` with field whitelist | new |
| `DONE` | `UPDATE ... SET status='done'` | new |
| `DELETE` | `DELETE FROM tasks WHERE ueid=?` | new |

Schema is `tasks(ueid PRIMARY KEY, name, status, priority, planned_start, planned_end, deadline, created_at)`.

Add ~120 LOC of UPDATE/DELETE/DONE branches to `apply_change()`. Fields whitelist = `SUPPORTED_FIELDS` (ueid, title, due, priority, status, planned_start, planned_end). Status must be in `_KNOWN_STATUSES` (planned, in_progress, done, cancelled).

### Layer 2 — `src/mesh/agent_consumer.py` (validation)
Currently `validate_task_change()` (or equivalent) only handles CREATE. Extend to:
- **CREATE**: existing rules (title >= 5 chars, not in banned words, due not in past)
- **UPDATE**: check UEID exists in DB (read adapter.read first); reject update that changes UEID field
- **DONE**: same UEID-exists check + reject if already status=done (idempotency)
- **DELETE**: UEID-exists check + reject delete of tasks with `status=done` (audit trail preservation)

Add ~100 LOC of per-action rule branches.

### Layer 3 — `src/ikigai/src/mcp_server/taskdog_tools.py` (new tools)
Add 8 new tools (3 read-only already exist):

| Tool | Action | Args |
|---|---|---|
| `taskdog_create` | CREATE | `ueid, title, due=None, priority=None, planned_start=None, planned_end=None` |
| `taskdog_done` | DONE | `ueid` |
| `taskdog_set_status` | UPDATE | `ueid, status` (planned/in_progress/done/cancelled) |
| `taskdog_set_priority` | UPDATE | `ueid, priority` (1/2/3) |
| `taskdog_set_due` | UPDATE | `ueid, due` (ISO date) |
| `taskdog_set_planned_dates` | UPDATE | `ueid, planned_start, planned_end` |
| `taskdog_cancel` | UPDATE | `ueid` (sets status=cancelled) |
| `taskdog_delete` | DELETE | `ueid` |
| `taskdog_search` | READ | `query, status=None, priority=None, limit=10` (substring match on title + filters) |

Each tool builds a `TaskChange` Pydantic model, queues via `src/mesh/queue.py` enqueue_task_change(), returns the change_id. Add ~250 LOC.

### Layer 4 — `.claude/loop/mcp_bridge.py` (wrapper exposure)
Each new tool needs a wrapper that calls `_call("taskdog_X", kwargs)`. Add ~100 LOC for 9 new wrappers + drift test updates.

## What is NOT in scope

- ❌ PAV-math reactivation (ADR-013, user confirmed out)
- ❌ HTTP fallback path in `TaskdogAdapter` (legacy, unused)
- ❌ Bikeshed on field names or status enum values
- ❌ Cross-fork reconciliation logic (already handled by agent_propagator)

## Test plan

| Test file | Count |
|---|---|
| `tests/mesh/test_taskdog_write_actions.py` | 12 tests (3 per action: success/validation-reject/db-error) |
| `tests/mesh/test_agent_consumer_extended_actions.py` | 8 tests (2 per action class) |
| `tests/mesh/test_taskdog_search.py` | 4 tests (substring, filter, no-match, limit) |
| `tests/test_m148_taskdog_full_bridge.py` | 9 tests (1 per new wrapper + drift detector) |
| **Total** | **+33 new tests** |

## LOC budget (honest, bumped)

| Layer | Target LOC | Why |
|---|---|---|
| Adapter (apply_change expansion) | ≤180 | UPDATE/DELETE/DONE branches + field validation |
| agent_consumer (extended validation) | ≤140 | per-action rules |
| taskdog_tools.py (new tools) | ≤320 | 9 tools with full docstrings |
| mcp_bridge.py (wrappers) | ≤140 | 9 wrappers + drift test |
| **Total** | **≤780 LOC** | + 33 tests = ~1100 LOC total |

## Risks

| Risk | Mitigation |
|---|---|
| SQLite UPDATE mutates existing rows | Add test that backs up DB before mutations and restores after |
| Agent_consumer rejects too aggressively | First-pass: prefer lenient (gate only on hard rules), strict rules added in M149 if needed |
| Drift detector complains about new wrappers | Bump wrapper count in M147 SPEC from 14 to 23 (14 + 9 new) |
| Contract changes affect downstream forks | `Supported_fields` already shared; new field whitelist is additive |

## Estimated cost

- Single session, no sub-agents → **$0.30-0.80 real cost**
- ~3 hours of focused implementation
- All changes local to bridge layer + taskdog adapter (no schema migrations, no fork restructuring)

## Commit

`git -c user.email="loop@hermes.local" -c user.name="loop-orchestrator" commit -m "feat(loop): M148 — full taskdog exposure via IKIGAI bridge (CREATE/UPDATE/DONE/DELETE/READ + 9 new tools)"`
