# AGENTS.md — src/ikigai/tests

## OVERVIEW
The IKIGAI subpackage test suite: 112 `.py` + 4 generated reports, 31 049 LOC, 1 332 test functions, 113 `Test*` classes. Earned its file at score 9 — a distinct domain (pytest-only, no production code imports it) whose conventions differ sharply from the runtime.

## STRUCTURE
```
src/ikigai/tests/
├── conftest.py      # suite entry: sys.path bootstrap, legacy aliasing, autouse isolation
├── test_*.py        # 105 flat modules (drift net, v2 graph, vault, taskdog, meta-plan)
├── e2e/             # vault↔agent round trip; session-scoped trace writer
├── mcp/             # multi-tool chain + full taskdog tool surface
├── skills/          # only subpackage with __init__.py
└── reports/         # committed, run-generated Implementer-Report markdown
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Import bootstrap | `conftest.py` | inserts `<repo>/` and `<repo>/src/` at the **front** of `sys.path` before any test module imports |
| Legacy namespace aliasing | `conftest.py` | 15 `sys_ikigai.*` modules pre-registered in `sys.modules` under their old `ikigai.*` names |
| Review-queue isolation | `conftest.py` | autouse fixture monkeypatches `src.mesh.queue.QUEUE_DIR` → `tmp_path` |
| HTTP bridge isolation | `conftest.py` | autouse fixture sets `TASKDOG_HTTP_ENABLED=0` |
| E2E fixtures | `e2e/conftest.py` | `tmp_vault`, `tmp_taskdog_db`, `tmp_queue_dir`, `tmp_state_file`, `tmp_vault_with_strategics`; session-scoped autouse writes `reports/b7-4-report.md` |
| Skills contract tests | `skills/test_taskdog_triage.py`, `skills/test_vault_intent_extract.py` | assert `propose()` never touches the adapter and never writes to disk |
| Generated reports | `reports/b{3,7}-*-report.md` | rewritten by fixtures — running e2e dirties the working tree |

## CONVENTIONS
- **Drift tests are static AST scans, not runtime probes.** 10 modules `ast.parse` production `.py` and assert on import/function/class shapes. The `FORBIDDEN_IMPORTS` / `FORBIDDEN_FUNCTIONS` / `FORBIDDEN_CLASSES` / `FORBIDDEN_MCP_TOOLS` frozensets live **in the test files**, never in production code.
- **`tmp_path` is the canonical isolation primitive.** `tmp_path_factory.mktemp()` is banned here — on Windows it creates dirs under a shared user temp path and raises `PermissionError [WinError 5]` on stale locks.
- **`tempfile.tempdir` + `TMPDIR`/`TEMP`/`TMP` are redirected** to `<repo>/data/pytest-tmp/` at conftest import time, and `pytest_configure` forces `config.option.asyncio_mode = "auto"` to disable pytest-asyncio collection (no test here is async).
- **Helpers are deliberately duplicated per file** — `_resolve_repo_root` ×5, `_iter_python_files` ×6, `vault_root` ×5, `tmp_vault` ×3. Drift tests must stay independent of each other; do not refactor them into a shared module.
- **Repo root is found by parent walk**, not `__file__` arithmetic — `_resolve_repo_root()` scans parents for `src/ikigai/src/agents`.
- **Skip-as-deferral is the sanctioned way to park unfinished work**: 63 `pytest.skip(...)` calls plus 8 `skipif` guards, 0 `xfail`. Environment-dependent tests degrade, they do not fail.
- **Naming**: `test_*.py` flat at the root; milestone prefixes (`test_m159_*`, `test_m161_*`, `test_m162_*`, `test_m256_*`); subsystem prefixes (`test_v2_*` ×23 files, `test_vault_*` ×12, `test_td_*` ×9).
- **Docstrings carry the ADR ids they enforce**, a `Run::` command block, and the milestone id.

## ANTI-PATTERNS
- **Drift tests are append-only.** Never delete or weaken an assertion — add a new test in `test_drift_extended_invariants.py` instead. That file is 1 775 LOC and reads as a log.
- **NEVER** let a test write the real `data/review_queue/`, and never shell out to pytest from a drift test (re-running the suite is CI's job).
- **NEVER** weaken the vault-writer allowlist, the `IKIGAI_TOOLS == 12` count, or the UEID 4-part regex.
- **NEVER** delete or rewrite `data/review_queue/` files — enqueue only.
- **NEVER** import `src/ikigai/tools` from a test — it is CLI-only with no importers.
- **NEVER** let a test write into `vault/` outside a tmp dir, and never let `surface_intentions` write to the vault.
- **Fixture shadowing is a real hazard**: `vault_root` is redefined in 5 modules, `tmp_vault` in 3. Before adding a fixture, check it does not shadow an existing name.

## NOTES
- `tests/skills/__init__.py` documents `uv run pytest` — **wrong**, this subpackage is Poetry-managed. Use `poetry run pytest`.
- The 3 drift-net files (`test_canonical_scope.py` 1 414 LOC, `test_drift_invariants.py`, `test_drift_extended_invariants.py` 1 775 LOC) hold ~11% of the suite's LOC and dominate wall time — they walk the whole production tree with `rglob` + `ast.parse`.
- 348 stale `__pycache__/*.pyc` from 3 CPython versions × 2 pytest versions live in-tree — churn noise, not source.
- 8 files use fixed `time.sleep` (`test_event_log_cli.py`, `test_gateway.py`, `test_m159_vault_cache.py`, `test_stdio_adapter.py`, `test_v2_graph_execution.py`, `test_v2_graph_smoke.py`, `test_vault_lock.py`, `test_vault_write.py`) — the likeliest flake sources.
