# TESTS/MESH

## OVERVIEW

Exercises the Phase 3 mesh boundary: adapter contracts, review-queue writes, agent propagation, and read-side joins.
Focuses on fork isolation, dual module identities, and dependency-graph correctness.

**Role:** Phase 3 mesh conformance — the 3 fork adapters, the review queue, the agent consumer/propagator, the read-side CLIs and the dependency graph.

## STRUCTURE
```
tests/mesh/
├── conftest.py                 # src/ on sys.path + 2 autouse isolation fixtures
├── adapters/                   # ForkAdapter conformance (3 forks, 23 tests)
│   ├── test_cli.py
│   ├── test_taskdog.py
│   ├── test_taskdog_schema_v2.py
│   └── test_solverforge_calendar.py
├── test_queue.py               # TaskChange -> data/review_queue/*.json
├── test_review_queue_cli.py    # review-queue CLI (--json)
├── test_review_queue_autoisolate.py
├── test_agent_consumer.py      # validate() -> Decision / ValidationResult
├── test_agent_propagator.py    # PropagationEvent fan-out
├── test_agent_pipeline_e2e.py  # in-process pipeline with _FakeAdapter
├── test_mesh_cli.py            # multi-fork join
├── test_cli_cli.py             # CLI fork read
├── test_taskdog_cli.py         # taskdog fork read
├── test_td_dep.py              # dependency graph
├── test_td_note.py
├── test_investigation_queue.py
└── test_vault_read_path_traversal.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Adapter protocol conformance | `adapters/` | `ForkAdapter` Protocol; `SUPPORTED_FIELDS` |
| Taskdog schema v2 slices | `adapters/test_taskdog_schema_v2.py` | `TaskdogSlice` / `TaskdogAuditEntry` |
| Review queue write path | `test_queue.py`, `test_review_queue_cli.py` | `TaskChange` -> queued JSON events |
| Queue isolation guard | `test_review_queue_autoisolate.py` | fails loudly if conftest isolation regresses |
| Agent validation | `test_agent_consumer.py` | `Decision`, `ValidationResult` |
| Propagation | `test_agent_propagator.py` | `PropagationEvent` to all forks |
| End-to-end pipeline | `test_agent_pipeline_e2e.py` | `_FakeAdapter`, no subprocess |
| Read-side joins | `test_mesh_cli.py`, `test_cli_cli.py`, `test_taskdog_cli.py` | `--json` is part of the contract |
| Dependency graph | `test_td_dep.py` | `detect_cycle`, `SelfLoopError`, `CycleDetected` |
| Investigation queue | `test_investigation_queue.py` | bare `contracts.investigation` import |
| vault_read traversal | `test_vault_read_path_traversal.py` | read-side twin of `vault_write` |

## CONVENTIONS

- **`src/` only, no inline bootstrap.** `tests/mesh/conftest.py` puts `<repo>/src` on `sys.path`, so the default import is `from src.mesh.X` / `from src.contracts.X`. Three files use the other tree on purpose: `test_investigation_queue.py` (`contracts.investigation`, `mesh.investigation_queue`) and `test_vault_read_path_traversal.py` (`sys_ikigai.vault.vault_read`).
- **Patch BOTH module identities.** `sys.path` holds the repo root *and* `src/`, so `src.mesh.adapters.taskdog` and `mesh.adapters.taskdog` are two distinct module objects with separate globals. `test_taskdog_cli.py`, `test_td_dep.py` and `test_td_note.py` patch both inside the same fixture; patching one leaves the other reading the real DB.
- **Read `QUEUE_DIR` off the live module** (`queue_mod.QUEUE_DIR`), never via `from src.mesh.queue import QUEUE_DIR` — the local binding freezes the import-time value and hides the autouse monkeypatch.
- **Explicit fixtures beat autouse.** `_isolate_review_queue` redirects `src.mesh.queue.QUEUE_DIR` into a per-test tmp dir; a test that asks for its own `queue_dir` fixture overrides it (pytest runs explicit fixtures after autouse).
- **Adapters are SQLite-fixture driven.** `TASKDOG_HTTP_ENABLED=0` (autouse) keeps the daemon path off, and the local `tasks` table schema is created per test.
- **Windows-aware subprocess calls** use `bufsize=0`, `cwd=REPO_ROOT`, an explicit `PYTHONPATH`, and a bounded `timeout` (30-60 s).

## ANTI-PATTERNS

- **Never write to the real `data/review_queue/`** — the autouse fixture exists for that, and `test_review_queue_autoisolate.py` guards it.
- **Never let the HTTP taskdog path shadow the SQLite fixture** — keep `TASKDOG_HTTP_ENABLED=0`.
- **Never patch only one of the two queue/adapter module identities.**
- **Never assert-fail when a fork server, venv or optional module is absent** — skip with a reason.
- **`audit_drift()` is read-only** — it must never mutate the vault.
- **`TaskAction` is broader than the mesh write path.** The enum carries `create`/`update`/`delete`/`done` plus the M164 tag actions; a mesh test asserts the behaviour that actually ships, not the enum's full surface.

## COMMANDS
```bash
pytest tests/mesh/ -v
pytest tests/mesh/adapters/ -v
pytest tests/mesh/test_review_queue_autoisolate.py -v
```
