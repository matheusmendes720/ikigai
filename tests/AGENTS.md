# TESTS

## OVERVIEW

This subtree contains the repository's pytest and shell-based test surface, split by subsystem.
It pins cross-boundary behavior, drift invariants, and hermetic runtime safeguards.

**Role:** the repo's only test surface — 155 tracked files (143 Python, 12 shell/batch), ~24k LOC, ~1,100 test functions, organised as one flat root suite plus 11 sub-suites.

## STRUCTURE
```
tests/
├── conftest.py             # session bootstrap: sys.path, ikigai.* aliases, temp isolation
├── contracts/              # Pydantic v2 contract pinning (11 files)
├── gateway/                # gateway boot + stdio server base
│   └── clients/            # fork MCP E2E over real subprocess JSON-RPC
├── ikigai/                 # v2 graph nodes, security validators, path bootstrap
├── integration/            # cross-subsystem create-flow + investigation lifecycle
├── interfaces/             # CLI surfaces + operator TUI
├── loop/                   # bash loop smoke + its pytest wrapper
├── mcp_server/             # vault_write + investigation MCP tools
├── mesh/                   # Phase 3 mesh v1: adapters, review queue, read CLIs
├── smoke/                  # platform-paired .sh/.bat vault <-> taskdog sync
├── solverforge_calendar/   # fork DB + schedule/availability models
└── tuiboard/               # aggregator + snapshot models
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Import resolution / session setup | `conftest.py` | see CONVENTIONS |
| MCP bridge wrapper surface | `test_m142_mcp_bridge.py` | 36 wrappers: 8 read-only, 6 write-side |
| Bridge spans, write tools, binding | `test_m143`–`test_m148` | 7 files, ~2.2k LOC, one module under test |
| Vault drift kinds | `test_m117`–`test_m140` | priority, tag, due date, checkbox, baseline |
| Vault toggle chain | `test_m121/125/131/133/135/140` | one shared `CHECKBOX_VAULT_RE` parser |
| Real-LLM smoke | `test_m126_real_llm_smoke.py` | skipped unless `ANTHROPIC_API_KEY` / `CLAUDE_API_KEY` |
| tasks.jsonl single-writer guard | `test_tasks_jsonl_single_writer_path.py` | AST-scans `src/` + `sys_ikigai/` |
| UEID single-source guard | `test_ueid_regex_single_source.py` | ADR-014 / ADR-033 R1.5 |
| Backtest / baseline tooling | `test_backtest_*`, `test_baseline_*`, `test_drift_*` | `tools.backtest.*` is the surface under test |
| Shell suites (not pytest-collected) | `test_dispatch.sh`, `test_cost_dashboard.sh`, `test_notify.sh`, `test_streak_tracker.sh`, `test_worktree_helper.sh` | run with `bash <file>` from repo root |

## CONVENTIONS

- **Milestone filenames.** 34 root-suite files are `test_m<NNN>_<topic>.py`; `NNN` is the milestone/spec id, not the module under test. A new feature normally means a new `test_mNNN_*` file.
- **`conftest.py` owns the bootstrap — do not copy it.** 53 of 143 Python files still carry their own `sys.path.insert` preamble (31 with `# noqa: E402`) and spell `REPO_ROOT` 14 different ways (`resolve().parent.parent`, `parents[1]`, `os.path.abspath`, upward walks). New test files should import directly.
- **CLI under test is a plain function returning an exit code** (`rc.main(...) == 2`), not a runner. Only 4 files use Typer's `CliRunner`: `test_life_task_cli.py`, `test_skill_show_cli.py`, `test_task_http_path.py`, `interfaces/test_invoke_skill_cli.py`.
- **Hermetic by default.** `tmp_path` (579 uses), `monkeypatch` (393), `capsys` (308). HTTP is faked at the `urlopen` level and `ChatAnthropic` is mocked — no network, no paid API calls.
- **Optional anything → `pytest.skip`.** 22 files skip when a module, venv, `gpg` or API key is absent; never assert-fail because a dependency is missing.
- **`from __future__ import annotations`** in 111/143 files; the 7 `__init__.py` markers and every `tests/contracts/` module omit it.
- **Shell tests are standalone.** `set -euo pipefail`, `PASS`/`FAIL` counters, `ok()`/`fail()` helpers, `mktemp -d` sandbox with `trap 'rm -rf' EXIT`. They copy the production script into the sandbox so its `$(dirname "$0")/..` root resolution lands there.
- **Docstrings are the spec contract.** Each module names the acceptance criterion, ADR or invariant id it pins, plus a `Run::` command. Sections are separated by `# ---- Acceptance #N: ... ----` blocks.

## ANTI-PATTERNS

- **Never write to real `data/` paths** (`data/review_queue/`, `data/tasks.jsonl`). The autouse conftest fixtures exist exactly for this, and `tests/mesh/test_review_queue_autoisolate.py` fails loudly if that isolation regresses.
- **Never re-enable `TASKDOG_HTTP_ENABLED`** in a test — the live daemon shadows the SQLite fixture ("expected 3 tasks, got 69").
- **Never weaken a drift guard to make a change pass.** Drift assertions are append-only; add a new assertion instead.
- **Never touch the real baseline passphrase.** `baseline_sign` tests mint a random per-test `LIFE_BASELINE_PASSPHRASE`.
- **Never let a test rewrite `vault/`** — the vault is append-only; copy into `tmp_path` first.
- **Never let a real LLM call slip through.** Real-LLM paths must be skipped or mocked (`IKIGAI_FAKE_LLM`).

## COMMANDS
```bash
pytest tests/mesh/ -v                 # mesh + adapters
pytest tests/gateway/clients/ -v     # fork MCP E2E
pytest tests/contracts/ -v           # contract suite
bash tests/test_dispatch.sh           # shell suite; exits 1 on failure
```
