# TESTS

## OVERVIEW

The repository's entire pytest + shell test surface: one flat root suite of 35 Python modules plus eight sub-suites.
Pins contract shapes, drift invariants, fork boundaries and hermetic-runtime guarantees.

**Role:** 85 tracked files (71 Python, 12 shell/batch, 2 markdown), ~15k LOC — the only place behaviour is pinned.

## STRUCTURE
```
tests/
├── conftest.py          # session bootstrap: repo root on sys.path, ikigai.* alias table, temp isolation
├── test_m<NNN>_*.py     # 18 milestone-named modules (M117 … M151)
├── test_<topic>*.py     # 17 topic-named modules (backtest, baseline, LLM judge, CLI, drift)
├── test_*.sh            # 5 standalone shell suites — not pytest-collected
├── contracts/           # 11 modules pinning src/contracts Pydantic v2 shapes (44 tests)
├── gateway/             # gateway boot + /health smoke
├── ikigai/security/     # 1 module: phase-transition validator
├── integration/         # cross-fork create flow
├── interfaces/          # 2 modules: notify router (+ its own conftest)
├── loop/                # bash notify-wrap smoke + its pytest wrapper
├── mesh/                # 18 files: fork boundary conformance
└── smoke/               # platform-paired .sh/.bat vault <-> taskdog sync
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Import roots / session setup | `conftest.py` | three roots live at once — see CONVENTIONS |
| `ikigai.*` alias table | `conftest.py` `_ALIAS_MODULES` | 14 modules, pre-registered via `sys.modules.setdefault` |
| Canonical MCP transport | `src/ikigai/tests/transport/test_mcp_tools.py` | pins the 6 artifact tools + `IKIGAI_MCP_TRANSPORT` selection |
| Vault drift kinds | `test_m117`–`test_m140` | priority, tag, due date, checkbox, baseline |
| Vault toggle / preview-apply chain | `test_vault_propagation.py` | `audit_drift` is read-only |
| Real-LLM smoke | `test_m126_real_llm_smoke.py` | module-level `importorskip` on `langchain-core` (optional dep) + key-based skips |
| tasks.jsonl single-writer guard | `test_tasks_jsonl_single_writer_path.py` | AST-scans `src/` + `sys_ikigai/` |
| UEID single-source guard | `test_ueid_regex_single_source.py` | byte-equality of both `_UEID_PATTERN` copies |
| Backtest / baseline tooling | `test_backtest_*`, `test_baseline_*`, `test_drift_*` | `tools.backtest.*` is the surface under test |
| Contract shapes | `contracts/` | 44 tests over the 11 Pydantic v2 modules |
| Fork boundary | `mesh/` | 184 tests — see `mesh/AGENTS.md` |
| Shell suites (not pytest-collected) | `test_dispatch.sh`, `test_cost_dashboard.sh`, `test_notify.sh`, `test_streak_tracker.sh`, `test_worktree_helper.sh` | run `bash <file>` from repo root |

## CONVENTIONS

- **Three import roots are live at once.** `pytest.ini` sets `pythonpath = src src/ikigai/src`; `conftest.py` prepends the repo root. `from src.contracts.X` and `from contracts.X` are therefore two distinct module objects with separate globals — patch both, and read constants off the live module (`queue_mod.QUEUE_DIR`) instead of a frozen `from … import CONST`.
- **`pytest.ini` beats `pyproject.toml`.** The `unit` / `integration` / `smoke` / `e2e` markers declared in `[tool.pytest.ini_options]` are never registered (the ini file wins) and no test uses them.
- **`conftest.py` owns the bootstrap — do not copy it.** A large share of the 72 Python modules still carry their own `sys.path.insert` preamble.
- **Milestone filenames.** 18 root modules are `test_m<NNN>_<topic>.py`; `NNN` is the milestone/spec id, not the module under test (`test_m140_vault_search.py` tests `tools/vault/search.py`).
- **CLI under test is a plain function returning an exit code** (`rc.main(...) == 2`), not a runner. Only `test_life_task_cli.py` and `test_task_http_path.py` use Typer's `CliRunner`.
- **Hermetic by default.** `tmp_path` / `monkeypatch` / `capsys` everywhere; HTTP is faked at the `urlopen` level and `ChatAnthropic` is mocked — no network, no paid API.
- **Optional anything → `pytest.skip`,** never assert-fail because a venv, `gpg`, an optional module or an API key is missing.
- **Temp isolation is forced.** `conftest.py` points `tempfile.tempdir` and `TMPDIR`/`TEMP`/`TMP` at `data/pytest-tmp/` (gitignored) to dodge the Windows `PermissionError [WinError 5]` on a stale pytest temp dir, and sets `asyncio_mode = "auto"` to disable pytest-asyncio collection.
- **The legacy MCP-server bridge is gone.** `.claude/loop/mcp_bridge.py` and its drift modules (`test_m142`–`test_m145`) were removed with the legacy harness (ADR-037). The canonical MCP surface is `src/transport/mcp_server.py`, pinned by `src/ikigai/tests/transport/test_mcp_tools.py`.
- **Shell suites are standalone.** `set -euo pipefail`, `PASS`/`FAIL` counters, `ok()`/`fail()`, `mktemp -d` sandbox with `trap 'rm -rf' EXIT`; they copy the production script in so `$(dirname "$0")/..` resolves to the sandbox. Exit code 1 on any failure.
- **Docstrings are the spec contract.** Each module names the acceptance criterion / ADR / invariant id it pins plus a `Run::` command; sections split on `# ---- Acceptance #N: … ----`.

## ANTI-PATTERNS

- **Never write to real `data/` paths** (`data/review_queue/`, `data/tasks.jsonl`). The autouse conftest fixtures exist exactly for this.
- **Never re-enable `TASKDOG_HTTP_ENABLED` in a test** — the live daemon shadows the SQLite fixture ("expected 3 tasks, got 69").
- **Never weaken a drift guard to make a change pass.** Drift assertions are append-only; add a new assertion instead.
- **Never let a real LLM call slip through.** `IKIGAI_FAKE_LLM=1` forces stub scoring; real-LLM paths must be skipped or mocked.
- **Never touch the real baseline passphrase.** `baseline_sign` tests mint a random per-test `LIFE_BASELINE_PASSPHRASE`.
- **Never let a test rewrite `vault/`** — the vault is append-only; copy into `tmp_path` first.
- **Never add an `_ALIAS_MODULES` entry for a `sys_ikigai.*` module that no longer exists** — the table is imported at conftest load, so one stale name aborts the whole pytest session.
- **Never patch only one identity of a dual-imported module.** `src.mesh.X` vs `mesh.X` and `src.contracts.X` vs `contracts.X` are separate module objects, so a single `monkeypatch.setattr` leaves the other reading the real path.

## COMMANDS
```bash
pytest tests/ -v                                  # the entire pytest surface
pytest tests/mesh/ -v                             # fork boundary conformance
pytest tests/contracts/ -v                       # contract shapes
pytest tests/test_tasks_jsonl_single_writer_path.py -v
bash tests/test_dispatch.sh                       # shell suite; exits 1 on failure
```
