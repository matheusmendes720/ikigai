# AGENTS.md — `src/mesh/adapters/`

**Score 8 (6 files, 100% code, 51 symbols, 15 exports, imported by 58 repo files) — updated: distinct domain.** The fork boundary: one `ForkAdapter` Protocol, two published implementations, one wire schema.

## OVERVIEW
Adapters are the only code that reads or writes a fork's own store. Everything upstream of them speaks UEID + `PropagationEvent`. The calendar fork (`SolverforgeCalendarAdapter`) was retired with the serverless pivot (ADR-037, 2026-11-01).

## WHERE TO LOOK
| File | Role |
|---|---|
| `base.py` | `ForkAdapter` Protocol — `name`, `read(ueid)`, `apply_change(event)`, `supports_field(field)` |
| `cli.py` | `CliAdapter` — the `life` fork; JSONL at `data/tasks.jsonl` |
| `taskdog.py` | `TaskdogAdapter` — the Taskdog fork; SQLite `tasks` table (992 LOC) |
| *(retired)* | `SolverforgeCalendarAdapter` — the calendar fork. The module is **deleted**; `__init__.py` keeps only an explanatory comment. |
| `a2ui_schema.py` | A2UI wire models (Pydantic v2 strict) |
| `tests/test_a2ui_schema.py` | the only test in this directory |

## CONVENTIONS
- **The Protocol is `@runtime_checkable` and structural** — `isinstance(x, ForkAdapter)` checks method presence, not inheritance. Implement all four members.
- **`read()` returns `None` for "not present"**, never raises for a missing record. Missing fork data is not an exception.
- **`apply_change()` must be idempotent** — the queue can replay an event after a crash, so a repeated write is a no-op, not a duplicate.
- **`supports_field(field_name)` is how the mesh decides what to propagate.** A field an adapter does not persist is dropped, not written blindly.
- **Each adapter owns a module-level path constant** (`TASKS_JSONL`, `TASKDOG_DB`, `UPI_DB`) derived from `PROJECT_ROOT = Path(__file__).parent.parent.parent[.parent]`. Redirects work by **mutating the module global**, not by passing a parameter.
- **`a2ui_schema.py` models are `frozen=True, extra="forbid"`**, with JSON-RPC `2.0` only and error codes restricted to `-32799..-32000`.
- **Every import in this directory is dotted.** `base.py` uses `from src.contracts.common import UEID` and `from src.contracts.task_change import PropagationEvent`; `__init__.py` uses `from src.mesh.adapters.…`. A bare `contracts.…` import would need `src/` on `sys.path` — do not add one.

## ANTI-PATTERNS
- **The `adapters/__init__.py` docstring is stale.** It says "v1 scope: only CREATE actions are wired. UPDATE/DELETE/DONE return early". That is true for `CliAdapter` (it early-returns on `action != "create"`), but **not** for `TaskdogAdapter`, whose `apply_change` dispatches `create`, `update`, `done`, `delete`, `tag_add`, `tag_remove`, `tag_clear`. Trust the code, not the docstring.
- **Each adapter's `apply_change()` is the only sanctioned write path into that fork's store.** Nothing upstream of it may touch the store directly; the queue->validate->propagate->apply_change chain in the parent file is the only caller.
- **Never hard-delete a task.** `rm` is a soft delete (`status='deleted'`) with the audit log preserved; `restore` is its inverse.
- **Never re-introduce the calendar fork.** `solverforge_calendar.py` is deleted and the adapter is out of `__all__`; a drift test fails if that stem reappears under `src/mesh/adapters/`.
- **Never add a fifth UEID regex here.** `taskdog.py` inlines a byte-identical copy of `src/contracts/common.py`'s pattern "to avoid a circular import" — keep the copy in sync with that source rather than editing it independently.
- **Never drop the tag audit trail.** `add_tags` / `remove_tags` / `clear_tags` / `get_tags` are module-level functions that write both the `tags` column and an audit record; bypassing them loses the trail.
- **The A2UI test parametrizes `create|update|delete|done`**, which reads as contradicting the mesh-v1 create-only scope. Treat mesh v1 as authoritative: the A2UI layer models the wire format, not the shipped action set.
