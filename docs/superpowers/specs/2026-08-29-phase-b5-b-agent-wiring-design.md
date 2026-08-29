# Phase B5.B — Agent Wiring Minimum Viable Wire-Up — Design Spec

**Date:** 2026-08-29
**Phase:** B5.B of `2026-08-28-backend-audit-data-mesh` layering plan
**Layer:** 4 (Agent Layer)
**Status:** Design — pending spec self-review + user approval before writing-plans
**Inputs:**
- Phase B5.0 audit: `memory/b5-0-audit-findings-2026-08-29.md`
- Phase B5.1-B5.5 closures: `memory/phase-b5-{1,2,3,4,5}-*.md`
- Phase B4 review queue worker: `src/mesh/review_queue_worker.py`
- Phase B3 MCP gateway: `src/ikigai/src/mcp_server/server.py`
- B5.0 audit §1.6 F14 finding (commit.py broken import)

---

## Context

Phase B5 (Layer 4 — Agent Layer) was originally framed as "wire
agent_consumer + agent_propagator into the review queue worker". A
review of the B4 deliverable shows **the wire-up is already complete**:

- `src/mesh/review_queue_worker.py:42-91` (`run_once()`) orchestrates
  `queue.consume_pending → validate(event) → propagate(event, adapters)
  → queue.ack(...)` end-to-end.
- `start_worker()` / `stop_worker()` / `worker_status()` provide pidfile
  lifecycle (lines 94-185).
- 9 unit tests at `interfaces/cli/tests/test_review_queue_worker.py`
  + 6 E2E tests at `interfaces/cli/tests/test_review_queue_worker_e2e.py`
  cover the full decision matrix (APPROVE/REJECT/CLARIFY, partial
  propagation, idempotency, real `CliAdapter` file write).

What remains for "minimum viable" is **the residual gaps** that the
B5.0 audit and B5.x sweeps surfaced but did not close:

| # | Item | Origin |
|---|------|--------|
| 1 | F14 broken import in `commit.py:12` | B5.0 audit §1.6 |
| 2 | E2E coverage gap: TaskdogAdapter + SolverforgeCalendarAdapter | observed during this spec |
| 3 | Dead test shim in `tests/ikigai/test_error_node.py:19-62` (function body) | worked around F14 in B5.1 |

B5.B closes all three.

---

## Decisions (D1..D3, locked)

### D1. F14 fix uses src-prefixed import (Option A)

Replace `from ikigai.mcp_server.server import _write_tasks_to_data`
(`src/ikigai/src/agents/ikigai_maintainer/nodes/commit.py:12`) with the
src-prefixed path that actually resolves:

```python
from src.ikigai.src.mcp_server.server import _write_tasks_to_data
```

This matches the existing `sys.path` convention already required by
`tests/ikigai/test_error_node.py:48` (prepend `src/ikigai/src/` to
`sys.path`). The dependency on `sys.path` is documented, not hidden.

**Rejected alternatives:**
- **D1.B** — Create `src/ikigai/src/ikigai/mcp_server/server.py` as a
  re-export shim. Cleaner site-packages-style import, but introduces a
  new package + new file with zero net benefit beyond cosmetics.
- **D1.C** — Inline `_write_tasks_to_data` body into `commit.py`. Breaks
  the single-writer rule for `data/tasks.jsonl` and duplicates logic.

### D2. Multi-adapter E2E tests added in same file

Add two new tests to `interfaces/cli/tests/test_review_queue_worker_e2e.py`,
mirroring the existing `test_end_to_end_with_cli_adapter_writes_real_file`
(lines 203-239) pattern:

1. `test_end_to_end_with_taskdog_adapter_writes_real_db` — drives the
   full pipeline through real `TaskdogAdapter`, verifies the row was
   UPSERTED into the temporary SQLite DB (uses
   `monkeypatch.setattr(adapter_mod, "DB_PATH", tmp_path_db)`).
2. `test_end_to_end_with_solverforge_calendar_adapter_writes_real_upi`
   — drives the full pipeline through real
   `SolverforgeCalendarAdapter`, verifies the `ueid` column was
   written to the temporary SQLite DB.

Both tests:
- Use the real queue at `data/review_queue/` (existing pattern)
- Use `tmp_path` for the adapter's DB / file (existing pattern)
- Cleanup `_cleanup(event_id)` after run (existing pattern)

### D3. Shim removed AFTER F14 fix lands

`_install_ikigai_mcp_shim()` at
`tests/ikigai/test_error_node.py:19-62` (function body) is a workaround
for F14. After D1 ships, the shim is dead code — delete it in the
same change set (or in a separate immediately-following commit if
commit hygiene prefers).

Files affected:
- `tests/ikigai/test_error_node.py` — delete lines 11-13, 19-62, 64-67,
  79, 86 (shim imports, function body, comment + top-level call,
  `graph_module` fixture call, `observe_module` fixture call)

Verify 10/10 tests in `test_error_node.py` still PASS post-deletion.

---

## Architecture (unchanged from B4)

```
            ┌──────────────────────────────────┐
            │  data/review_queue/*.json        │
            │  (pending events)                │
            └─────────────┬────────────────────┘
                          │ consume_pending()
                          ▼
            ┌──────────────────────────────────┐
            │  review_queue_worker.run_once    │  ← SHIPPED (B4)
            │  ├─ validate(event)              │
            │  ├─ propagate(event, adapters)    │
            │  └─ queue.ack(...)               │
            └─────────────┬────────────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
  ┌─────────┐      ┌──────────┐      ┌──────────────┐
  │Cli      │      │Taskdog   │      │Solverforge   │
  │Adapter  │      │Adapter   │      │Calendar      │
  │tasks    │      │SQLite    │      │Adapter       │
  │.jsonl   │      │UPSERT    │      │UPI ueid      │
  └─────────┘      └──────────┘      └──────────────┘
```

The B5.B deliverable does NOT modify this architecture. It's pre-existing
debt cleanup + test coverage expansion.

---

## Components & Files

### Modified — F14 fix

**File:** `src/ikigai/src/agents/ikigai_maintainer/nodes/commit.py`

- **Line 12:** Replace
  `from ikigai.mcp_server.server import _write_tasks_to_data`
  with
  `from src.ikigai.src.mcp_server.server import _write_tasks_to_data`
  (or equivalent that resolves under the canonical `src/` layout).
- **Line 16-17 (comment):** Note the sys.path dependency.

If `src.ikigai.src.mcp_server.server` is unreachable from the graph's
import context, alternative: lazy-import inside `commit_node()` body
(line 19) where `_write_tasks_to_data` is called. This decouples module
import from function-call resolution. Decision deferred to implementer
based on actual import behavior at runtime.

### Modified — Shim removal

**File:** `tests/ikigai/test_error_node.py`

- Delete lines 11-13 (`importlib`, `sys`, `types` imports — verify
  not used elsewhere in file first).
- Delete lines 19-62 (`_install_ikigai_mcp_shim` function body).
- Delete lines 64-67 (preceding comment block + top-level
  `_install_ikigai_mcp_shim()` call).
- Delete line 79 (fixture-level call inside `graph_module`).
- Delete line 86 (fixture-level call inside `observe_module`).

Final file should retain: docstring, `from pathlib import Path`,
`import pytest`, all `@pytest.fixture` definitions (without the shim
call), and all test functions.

Verify 10/10 tests in `test_error_node.py` still PASS post-deletion.

### Modified — E2E test additions

**File:** `interfaces/cli/tests/test_review_queue_worker_e2e.py`

Append two new tests after
`test_end_to_end_with_cli_adapter_writes_real_file` (line 239).

Each test follows the pattern:
1. `monkeypatch.setattr(<adapter_module>, "<PATH_ATTR>", tmp_path_asset)`
2. Enqueue a real `TaskChange` via `queue_mod.enqueue(event)`
3. Construct real adapter, call `worker_mod.run_once([adapter])`
4. Assert `result.consumed == 1, result.approved == 1, result.partial == 0`
5. Read back from `tmp_path_asset` and assert the row/line was written
6. `finally: _cleanup(event_id)`

---

## Error Handling (unchanged)

Existing partial-propagation semantics from B4 carry over:

- One adapter raises → `result.partial == 1`, queue file acked to
  `partial_propagation` status, other adapters still received event.
- All adapters raise → still partial (per-adapter isolation).
- DLQ / retry (audit F7) → out of scope, deferred to v1.2+.

---

## Testing

### Pre-flight baseline (must be green before B5.B ships)

```bash
TMPDIR=/c/tmp TMP=/c/tmp PYTHONPATH=. \
  pytest tests/mesh/ tests/ikigai/ \
         interfaces/cli/tests/test_review_queue_worker.py \
         interfaces/cli/tests/test_review_queue_worker_e2e.py -v
```

Expected: 9 unit + 6 E2E + ~10 ikigai graph = ~25 tests, all PASS.

### New verification (after B5.B ships)

1. **F14 import resolves cleanly:**
   ```bash
   PYTHONPATH=. python -c "
   from src.ikigai.src.agents.ikigai_maintainer.nodes.commit import commit_node
   print('commit_node import OK')
   "
   ```
   Expected: prints OK without `ImportError`.

2. **TaskdogAdapter E2E:** `test_end_to_end_with_taskdog_adapter_writes_real_db` PASS.
   Verify: row exists in tmp SQLite, ueid matches event.ueid.

3. **SolverforgeCalendarAdapter E2E:** `test_end_to_end_with_solverforge_calendar_adapter_writes_real_upi` PASS.
   Verify: `ueid` column populated in tmp SQLite, matches event.ueid.

4. **Shim removal non-regression:** `test_error_node.py` 10/10 PASS without the shim.

### Out of scope (per B5.0 audit + algorithm gate)

- F7 (propagator DLQ/retry) — deferred to v1.2+ per audit §1.3.
- F8 (CLI dual-layout) — architectural decision needed.
- Algorithm polishing (`**/scoring/**`, `**/formula**`, `**/qhe**`,
  `**/regime/**`, `**/weight`) — frozen per
  `memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`.
- commit.py functional tests beyond import resolution
  (`_write_tasks_to_data` is a thin wrapper).

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| `from src.ikigai.src.mcp_server.server` fails at graph compile time (sys.path race) | Medium | Lazy-import inside `commit_node()` body as fallback. Test the import in isolation before commit. |
| TaskdogAdapter / SolverforgeCalendarAdapter E2E tests reveal latent bugs in those adapters | Low | Pre-existing adapter tests cover the adapter surface. E2E just verifies the worker pipeline. If bugs surface, defer to separate B5.x sub-task (don't expand B5.B scope). |
| Shim removal breaks tests in other files that import `commit.py` | Low | Only `test_error_node.py` imports the graph module. Verified via grep pre-removal. |

---

## Estimated Scope

| Sub-task | LoC changed | Effort |
|----------|-------------|--------|
| B5.B.1 F14 fix | ~5 lines in commit.py | 30 min |
| B5.B.2 E2E tests | ~100 lines (2 tests) | 2 hours |
| B5.B.3 Shim removal | ~65 lines deleted (function + 3 call sites + imports) | 30 min |
| B5.B.4 Spec commit + verification | trivial | 30 min |
| **Total** | **~155 lines** | **~3-4 hours** |

---

## Related

- `memory/b5-0-audit-findings-2026-08-29.md` — F14 source (audit §1.6)
- `memory/phase-b5-1-shipped-2026-08-29.md` — original shim workaround
- `memory/phase-b5-2-shipped-2026-08-29.md` — multi-finding sweep
- `memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md` —
  scope fence for B5.x (no math edits)
- `memory/verify-agent-fabricated-failures.md` — verify E2E claims in
  main session before acting on subagent reports
- `memory/master-branch-carro-chefe-2026-08-28.md` — master branch =
  deep-agent harness; B5.B feeds into this goal
- `docs/superpowers/specs/2026-08-28-phase3-data-mesh-design.md` —
  Phase 3 v1 mesh design (the system B5.B verifies)
