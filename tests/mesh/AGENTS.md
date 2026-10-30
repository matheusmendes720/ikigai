# tests/mesh/ — Phase 3 Mesh Test Suite

**Score:** 7 (18 files, 100% code, 249 module-level symbols, 221 exports)
**Role:** the Phase 3 data-mesh surface — queue, adapters, CLIs, propagation.

## OVERVIEW

The largest subpackage in the test tree (187 test functions) and the only one whose
`conftest.py` redirects a runtime-state path (`src.mesh.queue.QUEUE_DIR`). Covers
`src/mesh/` end to end: the review queue, the three fork adapters, the mesh CLIs, the
agent consumer and propagator, and the dependency graph. No `__init__.py` —
rootdir-relative collection.

## STRUCTURE

```
tests/mesh/
├── conftest.py              # autouse isolation + src/ on sys.path
├── adapters/                # 4 files: CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter, schema v2
├── test_queue.py            # review-queue helpers, atomic writes
├── test_investigation_queue.py
├── test_review_queue_cli.py # + test_review_queue_autoisolate.py
├── test_cli_cli.py          # CliAdapter read-only CLI
├── test_taskdog_cli.py      # TaskdogAdapter read-only CLI (592 LOC)
├── test_mesh_cli.py         # cross-fork mesh_cli.show
├── test_td_dep.py           # M164 dependency graph (484 LOC)
├── test_td_note.py          # M164 td note subsystem
├── test_agent_consumer.py   # PAE validation
├── test_agent_propagator.py
├── test_agent_pipeline_e2e.py
└── test_vault_read_path_traversal.py
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Runtime isolation | `conftest.py` | autouse `TASKDOG_HTTP_ENABLED=0` + `src.mesh.queue.QUEUE_DIR` -> tmp dir |
| Queue semantics | `test_queue.py` | atomic writes; a failed `os.replace` leaves no target file |
| Investigation lifecycle | `test_investigation_queue.py` | `resolved -> archived` is NOT allowed (both terminal) |
| Adapter contracts | `adapters/` | each test builds its own SQLite schema inline |
| CLI contract | `test_cli_cli.py`, `test_taskdog_cli.py`, `test_mesh_cli.py` | `--json`/`--human` mutually exclusive; subcommand required |
| Dep graph | `test_td_dep.py` | `CycleDetected`, `SelfLoopError` |
| Taskdog note cap | `test_td_note.py` | text capped at 1024 chars; control chars stripped, newlines kept |
| Vault path safety | `test_vault_read_path_traversal.py` | absolute path, `..` traversal, symlink escape all rejected |

## CONVENTIONS

- **Three import identities coexist** in this package: `from src.mesh...` (dotted),
  `from mesh...` (bare), and `from contracts...` (bare). `test_taskdog_cli.py` and
  `test_td_dep.py` patch **both** `src.mesh.adapters.taskdog` and `mesh.adapters.taskdog`;
  `test_investigation_queue.py` imports the bare `mesh.investigation_queue` form.
  Patching only one identity silently no-ops.
- `conftest.py` inserts `<repo>/src` on `sys.path` (the root `tests/conftest.py` inserts
  `<repo>`); both are needed.
- Every adapter/CLI test creates its own SQLite schema inline
  (`CREATE TABLE tasks (...)`) rather than sharing a fixture library — the duplication is
  deliberate so each test is self-contained.
- CLI subprocess tests use `src/ikigai/.venv/Scripts/python.exe` (Windows venv layout),
  not `sys.executable`.
- Malformed queue files are skipped, not fatal: `test_read_events_skips_malformed_files`
  and `test_list_skips_malformed_lines` assert the CLI survives bad input.
- The dep-subsystem tests duplicate the same schema literal and the same dual-identity
  `TASKDOG_DB` restore dance as `test_taskdog_cli.py`.

## ANTI-PATTERNS

- NEVER let a mesh test write to the real `data/review_queue/`. The autouse
  `_isolate_review_queue` fixture exists so a forgotten override cannot pollute the
  developer's machine.
- NEVER let the taskdog HTTP daemon answer a mesh test. Without
  `TASKDOG_HTTP_ENABLED=0` the live daemon shadows the SQLite fixture and you get
  "expected 3 tasks, got 69".
- NEVER patch only one import identity. Patch both `src.mesh.*` and `mesh.*`.
- NEVER allow a terminal-state transition. `resolved -> archived` is rejected.
- NEVER let a queue write leave a `.tmp` file behind; the target must not exist after a
  failed `os.replace`.
- NEVER let a CLI crash on malformed input; skip the bad record and continue.
