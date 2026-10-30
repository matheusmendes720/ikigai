# src/mesh/ — Phase 3 Data Mesh

**Score:** 17 (29 files, 100% code, 242 symbols, 139 exports, 89 import sites)
**Role:** cross-fork task view + bidirectional sync — the mesh's read/write spine.

## OVERVIEW

The only subsystem that spans all four forks (CLI, taskdog, solverforge-calendar,
tuiboard). Write path: CLI enqueues a `TaskChange` into `data/review_queue/` →
agent validates → agent propagates a `PropagationEvent` to every adapter.
Read path: `python -m src.mesh.mesh_cli show <ueid>` joins each fork's slice.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Canonical fork read | `mesh_cli.py` | joins all 3 adapters; `ueid` is a positional arg |
| Taskdog operator CLI | `taskdog_cli.py` | 1035 lines, the hub; registers every sub-CLI |
| Review queue (append-only) | `queue.py` | JSON files in `data/review_queue/`, temp+rename |
| Validation rules | `agent_consumer.py` | vague-title / past-due / no-fields rejections |
| Fan-out to forks | `agent_propagator.py` | per-adapter failure isolation |
| Queue drain loop | `review_queue_worker.py` | `run-once` / `start` / `stop`; pidfile liveness |
| Dependency graph | `dep_subsystem.py`, `td_dep.py` | cycle detection, `CycleDetected`/`SelfLoopError` |
| Gantt + scheduler | `gantt_engine.py`, `optimizer.py`, `optimizer_strategies.py` | pure functions, no I/O |
| Fork adapters | `adapters/` | see `adapters/AGENTS.md` |
| Extra sub-CLIs | `cli/td_advanced.py`, `cli/td_gantt.py`, `cli/td_tag.py` | soft-delete, gantt, tags |

## CONVENTIONS

- Two import identities coexist *inside this package*: `queue.py`,
  `agent_consumer.py`, `agent_propagator.py` and `adapters/base.py` use the
  **bare** `from contracts.task_change import ...`, while `taskdog_cli.py` uses
  the **dotted** `from src.contracts.task_change import ...`. Monkeypatch both.
- `--json` / `--human` on every CLI; `--json` wins, otherwise TTY means table.
- `src/mesh/queue.py` shadows stdlib `queue` — deliberate, carries `# noqa: A005`.
- Atomic writes: temp file + `os.replace`, wrapped in `_retry_atomic_write`
  (4 attempts, exponential backoff + jitter). Duplicated verbatim in
  `queue.py` and `investigation_queue.py` — a drift candidate.
- Adapter path overrides mutate module globals (`TASKDOG_DB`, `TASKS_JSONL`,
  `UPI_DB`) rather than passing arguments.
- `taskdog` adapter reads HTTP-first with a SQLite fallback; `TASKDOG_HTTP_ENABLED=0`
  forces SQLite. Writes always go to local SQLite.

## ANTI-PATTERNS

- Never hard-delete a task. `td_advanced.py` sets `status='deleted'` and writes an
  audit row; `restore` reverses it.
- Queue and audit data are append-only. Notes live in the row's `audit_log`
  (`action='note'`, text ≤ 1024 chars after control-char stripping).
- Investigation states are terminal once `resolved`/`archived` — no resurrection.
- Vault writes are best-effort: a failure is logged, never raised, so it can
  never crash propagation.
- Reflection must never block a mutation. `_record_decision` swallows its own
  exceptions and warns on stderr.
- `DELETE` carries no fields — use `UPDATE` with `status='cancelled'`.
- Do not copy adapter internals into a CLI; import the adapter's helpers so
  validation and the audit log stay in one place.
- Do not re-export `TaskChange` from `src/contracts/__init__.py` — it is
  deliberately absent to keep the import surface acyclic.
