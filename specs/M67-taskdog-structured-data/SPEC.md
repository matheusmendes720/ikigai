---
name: M67-taskdog-structured-data
description: IKIGAI taskdog tools return JSON structured data + remove duplicate inline definitions in tools.py
owner: matheus-mendes
status: DONE
milestone: M67
estimated_cost_usd: 0.30
constitution_refs:
  - tests_are_the_contract
  - correctness_over_speed
---

# M67 — Taskdog tools return structured JSON + de-duplicate definitions

## Context

End-to-end audit (2026-09-18) showed the 4 IKIGAI taskdog tools
(`taskdog_list_tasks`, `taskdog_create_task`, `taskdog_complete_task`,
`taskdog_get_task`) returned raw `subprocess.stdout` — a mix of
ASCII art and human-readable strings. LangChain deep-agents require
**structured JSON** to:
1. Match the tool-return contract (parseable, indexable fields)
2. Make decisions based on field values (e.g., `id`, `count`, `ok`)

Worse: `tools.py` (the canonical IKIGAI_TOOLS registry) defined its
**own copies** of these 4 functions inline, never importing from
`tools_taskdog.py`. So even after fixing tools_taskdog.py, the
deep agent's view would still get the broken raw-string versions.

## What changed

### src/ikigai/src/agents/tools_taskdog.py (full rewrite)

All 4 tools now:
- Run `taskdog export --format json` (returns clean JSON array)
- Parse with `json.loads`, return `json.dumps(...)`
- Return stable envelopes: `{"ok": True, "count": N, "tasks": [...]}`
  or `{"ok": False, "error": "..."}` for failures
- Strip CRLF (Windows leftover from edit) — caught by grep heuristic
  during the rewrite
- `taskdog_get_task(id)` filters the export list in-process to
  work around the upstream bug in taskdog 0.23.0 `show`:
  `'TaskdogApiClient' object has no attribute 'get_task_detail'`
- `taskdog_create_task` extracts `(ID: <int>)` from `add` stdout via
  regex `(ID: <int>)` so the agent receives structured ID

### src/ikigai/src/agents/tools.py

Removed 148-line inline block that re-defined all 4 taskdog tools.
Now imports from `.tools_taskdog` (the canonical location).

## Acceptance

- [x] All 4 tools return JSON strings: `{"ok": True, ...}`
- [x] End-to-end smoke (real taskdog-server up):
  - LIST: returns `{ok: True, count: N, tasks: [...]}`
  - CREATE: returns `{ok: True, id: <int>, name, raw}`
  - GET existing: returns `{ok: True, task: {...}}`
  - GET missing: returns `{ok: False, error: "not found"}`
  - LIST filtered by status: returns filtered count
- [x] Drift invariants: 18/18 PASS (test_drift_extended_invariants.py)
- [x] Chat + system: 13/13 PASS
- [x] canonical_scope: 35/35 PASS
- [x] test_reasoning_chain.py: 3/3 PASS
- [x] taskdog_mcp tests: 17/17 + 1 SKIP PASS

## Out of scope (M68+)

- `taskdog-server` daemon startup is still manual (must run
  `taskdog-server &` before any agent call). Should be a scheduled
  taskdog-server daemon.
- `taskdog-mcp` pipx venv broken with `No module named 'taskdog_client'`
  (host-side pipx-injection issue, NOT in repo scope).
- `tools.py` has a side-import bug at the bottom
  (`from .ikigai_read_strategics import ikigai_read_strategics`)
  that triggers `ModuleNotFoundError: No module named 'strategics'`
  on cold-import. This is M68+ cleanup.
- `taskdog_complete_task` semantically requires `start` before
  `done` (PENDING → IN_PROGRESS → COMPLETED). The retry+circuit-breaker
  correctly raises ConnectionError on the failure, but a future
  improvement is for the tool to auto-call `start` first.

## Quick win unlocked

Before this milestone, every deep agent invocation against taskdog
returned raw ANSI tables and required manual parsing. Now the deep
agent receives structured data that:
- Can be passed downstream to other tool calls
- Can be diffed in tests (deterministic JSON output)
- Can be rendered with `json.dumps(indent=2)` for human inspection
- Surfaces a stable `{"ok": True, "error": "..."}` envelope so the
  agent can branch on success/failure without parsing strings
