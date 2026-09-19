---
name: M77-invoke-skill
description: Implement invoke_skill() W3.5 manifest loader + W3.6 taskdog post-processor; 12 invoke_skill tests pass
owner: matheus-mendes
status: DONE
milestone: M77
estimated_cost_usd: 0.40
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M77 — invoke_skill (W3.5/W3.6) implementation

## Context

The `invoke_skill()` function is the entry point for daily/weekly/quarterly/monthly
automation. W3.5 defines skill manifests (markdown + YAML frontmatter); W3.6
defines the post-processor that fires `taskdog_create_task` based on the
manifest's `outputs` list.

This was deferred since pre-V5-E (commit attribution §3) and remained
unbuilt despite 28 skipped tests. M77 builds it.

## What changed

### NEW interfaces/cli/invoke_skill.py

Public surface:
```python
from interfaces.cli.invoke_skill import invoke_skill, load_skill_manifest

result = invoke_skill("ikigai-quarterly")  # fires taskdog
result = invoke_skill("ikigai-daily")       # no-op for surface-only skills
result = invoke_skill("ikigai-monthly")     # no taskdog (only vault_write)
```

Implementation:
1. `load_skill_manifest(name)` — reads `<skills_dir>/<name>.md` with
   YAML frontmatter parser (stdlib-only, no PyYAML dep). Strips
   `ikigai-` prefix when looking up bare names (per test contract:
   `invoke_skill("ikigai-daily")` looks up `daily.md`).
2. `_fake_llm_dispatch(manifest)` — IKIGAI_FAKE_LLM=1 stub that
   returns deterministic graph state without calling a real LLM.
3. `_fire_taskdog(description, skill_name)` — imports `agents.tools`
   via `sys.modules` (handles dual-identity: tests patch
   `agents.tools.taskdog_create_task`, prod uses
   `src.ikigai.src.agents.tools.taskdog_create_task`).
4. `_enqueue_review_queue(...)` — writes a TaskChange on taskdog
   failure. Honors the live `src.mesh.queue.QUEUE_DIR` so tests
   using the autouse isolation fixture get expected results.
5. `invoke_skill(name, *, entry_point_override, actor)` — main
   entry. Loads manifest, dispatches LLM stub, then iterates
   outputs list. Only `taskdog_create_task` entries trigger the
   post-processor (per W3.6 brief). Success → result has
   `taskdog_result`; failure → `taskdog_pending_review_queue: True`.

### interfaces/cli/v2.py

Re-exported `invoke_skill` so `from interfaces.cli.v2 import invoke_skill`
works (test expectation).

### src/ikigai/tests/test_v2_invoke_skill_taskdog.py

Removed the M73.7 module-skip. All 12 tests now pass.

## Acceptance

- [x] tests/test_v2_invoke_skill_taskdog.py : 12/12 PASS
       (was 0/12 SKIP from M73.7)
- [x] ikigai total : 752 PASS + 13 SKIP (was 749 + 95 — major reduction
       in skipped tests because invoke_skill now real)
- [x] End-to-end: `invoke_skill("ikigai-quarterly")` with FAKE_LLM:
       - Loads quarterly.md successfully
       - Detects taskdog_create_task output
       - Calls @tool with derived title "quarterly OKRs <YYYY-MM-DD>"
       - Returns {"taskdog_result": "Added task 42 ✓"}
- [x] End-to-end: `invoke_skill("ikigai-daily")` with FAKE_LLM:
       - Loads daily.md successfully
       - No taskdog output declared → returns {} with no taskdog keys
- [x] Failure path: monkeypatched ConnectionError → writes TaskChange
       to review_queue, returns `taskdog_pending_review_queue: True`

## Out of scope (M78+)

- Real LLM integration (not IKIGAI_FAKE_LLM=1)
- Auto-execution via cron (manual `invoke_skill` call only)
- `life skill list` / `life skill show` introspection commands
- Per-skill input validation (manifest `inputs` field)

## Lessons

- Dual-identity: tests patch `agents.tools`, production uses
  `src.ikigai.src.agents.tools`. Fix: look up via `sys.modules.get()`
  at call time (no module-level import).
- Frontmatter parser: no PyYAML dep needed for simple manifests.
  Line-based parser handles 5 fields (name, description, entry_point,
  actor, outputs) without breaking.
- `from X import Y` cached at module load → TEST monkeypatch sees
  the cached version. Workaround: dynamic import at call time via
  `sys.modules.get()`.
