---
name: M71-taskdog-http-bridge
description: Mesh TaskdogAdapter now reads from daemon-managed taskdog-server via HTTP — falls back to SQLite for tests
owner: matheus-mendes
status: DONE
milestone: M71
estimated_cost_usd: 0.30
constitution_refs:
  - correctness_over_speed
  - state_on_disk_not_conversation
---

# M71 — Mesh TaskdogAdapter HTTP bridge

## Context

After M68 daemonized `taskdog-server`, the daemon-managed SQLite-backed
taskdog fork was fully operational for **agent tools** (M67-M70). But
the MESH layer (`src/mesh/adapters/taskdog.py`) still pointed at a
nonexistent local DB at `data/taskdog/tasks.db`. Production code paths
like `mesh_cli.show`, `mesh_cli.list`, and the cross-fork-join machinery
all called `TaskdogAdapter().list_all()` which silently returned `[]`.

This was a real gap: the user-facing mesh CLI advertised 3 forks (CLI,
taskdog, solverforge_calendar) but taskdog was always empty.

## What changed

### src/mesh/adapters/taskdog.py — full rewrite

The adapter now implements an **HTTP-first with SQLite-fallback**
strategy:

- **`list_all()`**: HTTP GET `/api/v1/tasks` (daemon-managed) → SQLite
  fallback if server unreachable, test fixture, or explicit disable
- **`read(ueid)`**: still SQLite-only (taskdog-server uses numeric `id`,
  not UEID strings; cross-fork UEID join stays on local write store)
- **`apply_change(event)`**: still local SQLite (write-side kept simple
  — agents use `taskdog.exe` for live mutations separately)
- New helper: `_http_enabled()` reads env flag at call-time (not module-
  import-time) so test fixtures using `monkeypatch.setenv` take effect
  even after module is loaded
- New helper: `_normalize_http_task()` projects API server dict to the
  adapter's slice shape (8 required keys + bonus fields tags/depends_on)

### tests/conftest.py and src/ikigai/tests/conftest.py

Two autouse `monkeypatch.setenv("TASKDOG_HTTP_ENABLED", "0")` fixtures
ensure tests using local SQLite fixtures (monkeypatched `TASKDOG_DB`)
aren't silently shadowed by the daemon-managed server's 75 real tasks.

## Acceptance (verified 2026-09-19)

- [x] **316 passed + 1 skipped** across `tests/` (Phase 3 root)
- [x] **91 passed + 1 skipped** across critical `src/ikigai/tests/`
- [x] All 13 previously-failing `test_taskdog_cli.py` tests now GREEN
  (they monkeypatch SQLite; autouse env-fix prevents server shadow)
- [x] Phase 3 v1 smoke test: **SMOKE TEST PASSED**
- [x] Live HTTP bridge call: 75 tasks visible via
  `TaskdogAdapter().list_all()` (instead of the old `[]`)
- [x] Each task has full adapter contract: ueid, name, status,
  priority, planned_start, planned_end, deadline, actual_end,
  created_at — plus bonus tags, depends_on
- [x] Drift net canônico: 18/18 PASS

## Bug elementar found during M71

A subtle bug: my first attempt cached `TASKDOG_HTTP_ENABLED` at module
import time. Even with `monkeypatch.setenv("TASKDOG_HTTP_ENABLED","0")`
in tests, the cached value was read by the adapter. M71 fix: read the
env at every call (`_http_enabled()` callable) so test fixtures
can override.

## Out of scope (M72+)

- **Read-by-UEID via HTTP**: taskdog-server `GET /api/v1/tasks/{id}`
  uses numeric `id`, not UEID. Need either a UEID↔id index mapping in
  the local SQLite, or a taskdog-server extension that exposes
  `GET /api/v1/tasks/by-ueid/{ueid}`. Out of M71 scope.
- **Write-via-HTTP**: agents already have `taskdog_create_task` etc.
  tools (M67). For the mesh layer to round-trip writes, would need
  to call `POST /api/v1/tasks` from the propagation path. Out of M71.
- **`taskdog-mcp` pipx venv broken** (host-side pipx issue) — M72+
- **tests/mcp_server/ tests** not all green (collected-error pre-M71) —
  M72+

## Network effect

The M68 daemon-managed taskdog-server is now visible to **both**:
1. **IKIGAI deep agents** (via `tools_taskdog` LangChain tools from M67)
2. **Mesh layer** (via `TaskdogAdapter().list_all()` cross-fork join from M71)

Both surfaces see the same 75 tasks. The single source of truth
(network-local taskdog-server) is now universally readable.
