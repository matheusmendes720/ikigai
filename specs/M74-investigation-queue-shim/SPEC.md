---
name: M74-investigation-queue-shim
description: Fix investigation_status reading real queue dir (dual-identity bug in test fixtures); final root-suite green
owner: matheus-mendes
status: DONE
milestone: M74
estimated_cost_usd: 0.10
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
  - state_on_disk_not_conversation
---

# M74 — Investigation queue dual-identity fix (root suite 100% GREEN)

## Context

After M73.7 the ikigai suite was 749 PASS + 95 SKIP + 0 FAIL but the
root suite had regressed to 328 PASS + 1 FAIL. The remaining failure
was `tests/mcp_server/test_investigation_lifecycle.py::test_status_summary`
returning `total=9` instead of expected `2`.

## Root cause

Production code (MCP server) uses:
```python
from src.mesh.investigation_queue import get, list_all  # CORRECT path
```

Test fixtures patched:
```python
import mesh.investigation_queue as q
monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)  # SHADOW module
```

When `investigation_status()` is called, it imports `list_all` from
`src.mesh.investigation_queue` (canonical). The patched `QUEUE_DIR` is on
the `mesh.investigation_queue` shadow module. Production reads from the
real `data/review_queue/` dir (193 items, but filtered to 9 by some logic).

## Fix

Updated test fixtures to patch the canonical `src.mesh.investigation_queue`:

```python
import src.mesh.investigation_queue as q
monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
```

Files patched:
- `tests/mcp_server/test_investigation_lifecycle.py`
- `src/ikigai/tests/test_canonical_scope.py`
- `src/ikigai/tests/agents/v2/test_investigation_dispatcher.py`
- `tests/integration/test_investigation_queue_smoke.py`

Intentionally NOT patched: `tests/mesh/test_investigation_queue.py` — that
file tests the `mesh` module itself, so it must keep its `mesh.X` imports.

## Acceptance

- [x] tests/mcp_server/test_investigation_lifecycle.py : 10/10 PASS
       (was 9 PASS + 1 FAIL — test_status_summary)
- [x] tests/integration/test_investigation_queue_smoke.py : still green
- [x] tests/ root : **329 PASS + 1 SKIP, 0 FAIL** (was 328 PASS + 1 FAIL)
- [x] Drift net canônico : 18/18 PASS
- [x] ikigai : 749 PASS + 95 SKIP (no regression)

## Note

This is the SAME bug class as M59 / M73.3 / M73.5 — dual-identity between
`mesh.X` and `src.mesh.X`. Production code consistently uses `src.mesh.X`
after those fixes, but test fixtures sometimes still use `mesh.X`. The
diff is hard to spot because both modules are importable on the current
PYTHONPATH; the test only fails when monkeypatched and the production
read disagree.

## Out of scope (M75+)

- Implement `invoke_skill` (W3.5/W3.6) — 28 tests still skip
- v2 graph wiring recovery — 17 tests still skip
- TUI testing — `tests/interfaces/` still ignored

## Lesson

Dual-identity sweep should grep BOTH production code AND test fixtures.
M59/M73.3 swept production only. Tests that use `mesh.X` directly are
"production by analogy" and need the same canonical import.
