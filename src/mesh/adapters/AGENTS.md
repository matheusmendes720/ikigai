# src/mesh/adapters/ — Fork Adapters

**Score:** 11 (7 files, 100% code, 73 symbols, 50 exports, 58 import sites)
**Role:** the per-fork storage boundary — one `ForkAdapter` implementation per fork.

## OVERVIEW

Every fork the mesh writes to is reached through a `ForkAdapter`. Three
implementations exist: `CliAdapter` (JSONL), `TaskdogAdapter` (SQLite),
`SolverforgeCalendarAdapter` (SQLite UPI). `a2ui_schema.py` defines the
agent-to-UI wire protocol but has no adapter yet.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| The protocol | `base.py` | `ForkAdapter`: `name`, `read`, `apply_change`, `supports_field` |
| Adapter exports | `__init__.py` | `CliAdapter`, `ForkAdapter`, `SolverforgeCalendarAdapter`, `TaskdogAdapter` |
| JSONL fork | `cli.py` | `data/tasks.jsonl`, 14-field unified schema |
| SQLite task fork | `taskdog.py` | 992 lines; HTTP-first read, local SQLite write |
| Calendar fork | `solverforge_calendar.py` | `data/solverforge_calendar/unified_planning.db` |
| A2UI wire schemas | `a2ui_schema.py` | JSON-RPC 2.0 envelopes, `A2UIAction` = create/update/delete/done |
| A2UI tests | `tests/test_a2ui_schema.py` | 25 tests; run directly — the root `pytest.ini` sets `testpaths = tests`, so this in-package suite is **not** collected by a bare `pytest` |

## CONVENTIONS

- `apply_change` must be **idempotent** — safe to retry. The queue may redeliver.
- `read(ueid)` returns the fork's slice or `None`; slices never merge across forks.
- `supports_field(name)` is the field whitelist; each adapter declares its own set.
- Path constants are module globals (`TASKS_JSONL`, `TASKDOG_DB`, `UPI_DB`) so
  CLIs can override them for tests and ops.
- `TaskdogAdapter` defers its contracts import into function bodies to break a
  circular import back through `src/mesh/queue.py`.
- JSONL writes take a sidecar lock file (`tasks.jsonl.lock`) in **binary** mode;
  `msvcrt.locking` fails on text-mode handles on Windows.

## ANTI-PATTERNS

- Never write `data/tasks.jsonl` from anywhere but `CliAdapter.apply_change`.
  `tests/test_tasks_jsonl_single_writer_path.py` enforces a single writer and
  keeps an explicit reader allowlist.
- Do not hard-delete. `TaskdogAdapter.apply_change` handles `DELETE` by removing
  the row — that path is for the agent's explicit delete action, distinct from
  the CLI's soft `rm` (which flips `status='deleted'`).
- Do not add fields to `SUPPORTED_FIELDS` without checking the fork's actual
  schema; the sets are not uniform across adapters.
- Do not make `apply_change` raise on an unknown action — unknown actions are
  forward-compatible no-ops.
- `adapters/__init__.py` still describes v1 as CREATE-only. That is stale for
  `TaskdogAdapter` (all seven actions) but accurate for `CliAdapter` and
  `SolverforgeCalendarAdapter`, which still return early on non-create.
