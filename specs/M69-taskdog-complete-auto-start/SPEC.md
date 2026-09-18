---
name: M69-taskdog-complete-auto-start
description: taskdog_complete_task auto-calls start when PENDING guard detected
owner: matheus-mendes
status: DONE
milestone: M69
estimated_cost_usd: 0.20
constitution_refs:
  - tests_are_the_contract
  - correctness_over_speed
---

# M69 — taskdog_complete_task auto-starts PENDING tasks

## Context

taskdog 0.23.0 enforces a PENDING → IN_PROGRESS → COMPLETED state
machine. The deep-agent workflow with 4 LangChain tools (M67) worked,
but `taskdog_complete_task` was hitting the PENDING guard every time:

```
✗ Error: Cannot complete task 1: task is PENDING. Start the task
  first with 'taskdog start 1'
```

That made the deep-agent workflow 2-step (start → complete) when
ideally it should be a single ergonomic call. Deep agents express
intent ("complete this task") — the agent shouldn't have to know
about the state machine.

## What changed

src/ikigai/src/agents/tools_taskdog.py — single function rewritten:

`taskdog_complete_task(task_id)` now:

1. First attempt: `taskdog.exe done <id>` (the natural call)
2. If error message contains "PENDING" + "Start" (the canonical
   guard-message shape), call `taskdog.exe start <id>` next, then
   retry `done`
3. Return `{"ok": True, ..., "auto_started": True}` so the agent can
   tell the user "I had to start+complete this"

The retry+circuit-breaker decorators stay on the outside; on the
third-attempt failure path (start+done both fail), they trigger
normally and surface the new error.

## Acceptance

- [x] `taskdog_complete_task(id)` works for PENDING tasks in 1 call
  (auto-starts → does)
- [x] `taskdog_complete_task(id)` returns `{ok, auto_started: True}` envelope on the auto-started path
- [x] `taskdog_complete_task(id)` still works for IN_PROGRESS / COMPLETED
  tasks unchanged (no start call fired, fall-through path)
- [x] End-to-end 7-step deep-agent daily-review workflow verified:
  list → create 3 → auto-start+complete 1 → get → filtered list →
  error path → cleanup 2
- [x] Drift + chat + canonical_scope + taskdog_mcp tests: 91/91 + 1 SKIP

## Idempotency guarantee

If a task is already in IN_PROGRESS (rare-but-real concurrent
edit race), the auto-start call surfaces "task is IN_PROGRESS",
which `taskdog done <id>` then completes anyway. Idempotent: calling
`complete` twice on the same task ends up the same — task COMPLETED.

## Out of scope (M70+)

- `taskdog_pause_task`, `taskdog_cancel_task`, `taskdog_reopen_task`
  not exposed as tools yet (taskdog CLI has these — see `taskdog --help`)
- `taskdog_gantt` / `taskdog_timeline` rich-formatters not exposed yet
- `taskdog stats` analytics not integrated
- `taskdog start` tool isn't separate yet — only auto-fired from
  complete. Could expose if a user explicitly wants to mark
  IN_PROGRESS without completing.
