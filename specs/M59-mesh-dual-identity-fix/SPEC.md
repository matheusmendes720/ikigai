---
name: M59-mesh-dual-identity-fix
description: Resolve mesh module dual-identity (src.mesh vs mesh) so monkeypatch on TASKS_JSONL + queue are honored
owner: matheus-mendes
status: DONE
milestone: M59
estimated_cost_usd: 0.50
constitution_refs:
  - tests_are_the_contract
  - correctness_over_speed
  - state_on_disk_not_conversation
---

# M59 — Mesh module dual-identity fix

## Context

The Phase 3 mesh layer has been flaky for months. 27 of 163 tests in
`tests/mesh/` failed at master HEAD on 2026-09-18, all because the test
fixtures' `monkeypatch.setattr` was applied to the **wrong module instance**.

Two import styles coexisted:

- **Production path** (PYTHONPATH=src, smoke test, conftest): `from src.mesh.X import Y`
- **Source-code path** (inside `src/mesh/*.py`): `from mesh.X import Y`

Python loaded both as distinct module entries in `sys.modules`:
`src.mesh.adapters.cli` (id `2236486696160` in this trace) and
`mesh.adapters.cli` (id `2236527714736`). The test conftest patched
`cli_mod.TASKS_JSONL` on the prefixed one, but the consumer read from the
bare one — producing 27 false negatives + polluting fixtures.

## What changed

1. `src/mesh/cli_cli.py`, `mesh_cli.py`, `agent_consumer.py`,
   `agent_propagator.py`, `review_queue_worker.py`, `taskdog_cli.py`,
   `adapters/__init__.py`, `adapters/tests/test_a2ui_schema.py` —
   replace `from mesh.X import Y` → `from src.mesh.X import Y` and
   `from mesh import queue` → `from src.mesh import queue`. Now all
   imports in `src/mesh/*` resolve to the same module instances that
   the conftest sees.

2. `tests/test_chat_system.py` at repo root — removed (stale duplicate
   of `src/ikigai/tests/test_chat_system.py` against the pre-M58 API).

## Acceptance

- [x] `tests/mesh/` → 136/136 PASS (was 27 failing)
- [x] `tests/` (Phase 3 full) → 323 passed, 1 skipped (was 31 failing)
- [x] `tests/test_chat_system.py` (repo root) → deleted; canonical lives at
  `src/ikigai/tests/test_chat_system.py` (5/5 from M58)
- [x] Phase 3 v1 smoke → SMOKE TEST PASSED

## Why this matters operationally

Production code (smoke test, future CI) calls the mesh CLIs through
`PYTHONPATH=src python -m src.mesh.cli_cli ...`. The source code MUST
use absolute imports with the `src.` prefix too; otherwise two module
instances exist for every Python process that imports `src.mesh`,
and any monkeypatch only affects half of the call graph. This bug was
a perfect setup for silent debugging hell.

## Risk / out-of-scope

- Other directories (interfaces/, vibe-ops/) were not swept; they may
  have their own dual-identity bugs. Out of scope for M59 (mesh only).
- `sys_ikigai.vault.vault_write` import path used by
  `src/ikigai/src/mcp_server/tools_vault.py` references a non-existent
  module — this is a separate failure mode that pre-dates M59 (the
  delete-PAV archival left dangling imports). Will be cleaned up in
  M62 alongside other PAV-removal follow-ups.

## Next

- **M60** — root `pyproject.toml` OR documented venv activation contract
  (resolves the `python -m life.cli ...` ModuleNotFoundError that has been
  misleading AGENTS.md readers for months)
- **M62** — sweep sys_ikigai/* dangling imports + tests
  `tests/mcp_server/test_vault_write_actor.py` + `tests/test_reasoning_chain.py`
