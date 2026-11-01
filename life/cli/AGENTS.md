# life/cli

The Typer application behind the `life` console command. Earns its own file:
score 10 (6 files, 100% code, 22 exports, 33 referencing files) — a distinct
domain (process entry point and app wiring).

## OVERVIEW
Five modules plus `__main__.py`. `cli.py` is the app; `config.py` is the
single source of paths and settings; `log.py` and `test_runner.py` are
support services; `__init__.py` owns the console-script bootstrap.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| App + command wiring | `cli.py` | 14.8 KB; `app = typer.Typer(name="life", no_args_is_help=True)` |
| Config dataclass | `config.py` | `LifeConfig`, `load_config()`, `DEFAULT_SUBMODULES` |
| Console entry | `__init__.py` | `_main_console()` + `_bootstrap_repo_paths()` |
| Module entry | `__main__.py` | `python -m life.cli` → `app()` |
| Logging | `log.py` | `get_logger(name)`; file handler + stderr handler |
| Test discovery | `test_runner.py` | `find_test_dirs()`, `run_pytest()`, `run_unittest()` |

## CONVENTIONS
- **Mount order in `cli.py`**: centrals (`task`, `knowledge`, `research`) →
  handlers (`daily`, `weekly`) → `notify` → `v2` → `taskdog` → plugin
  commands (`register_plugins(app)` runs last).
- **`taskdog` is conditional.** The sub-app is only mounted when
  `importlib.util.find_spec("langchain_mcp_adapters")` resolves. Otherwise a
  placeholder app prints the install hint and exits 1. `life --help` therefore
  works from any venv.
- **`_bootstrap_repo_paths()` is idempotent** via the
  `_LIFE_REPO_BOOTSTRAPPED` attribute on `sys`, and resolves the repo root two
  ways: `parents[2]` from `life/cli/__init__.py` (editable install), or by
  walking up from CWD looking for a `pyproject.toml` next to a `life/` dir
  (non-relative install). It adds `<repo>`, `<repo>/src` and `<repo>/interfaces`.
- **Config never blocks the CLI.** `config.py` degrades instead of raising:
  a missing or unparsable `config/life.yaml`, or a missing PyYAML, yields
  `LifeConfig()` with every default filled in.
- `ensure_dirs()` creates the log dir and every plugin dir on demand.

## ANTI-PATTERNS
- **Never let the `taskdog` registration leak JSON to stdout.** This is a
  live bug: `interfaces.cli.taskdog_app.register_taskdog_app` calls
  `typer.echo(json.dumps({...}))` — which writes to **stdout** — and *then*
  raises `typer.Exit`. `cli.py` catches the `typer.Exit` with
  `except typer.Exit: pass`, so the error block survives. Every
  `python -m life.cli ...` invocation therefore prints
  `{"ok": false, "error": "failed to discover MCP tools: ..."}` on stdout
  before the real output, and `--json` emits **two** JSON documents. Verified
  on `life --help`, `life task ls`, `life knowledge read x`,
  `life research search x` and `life plugins`. Fix by routing that message to
  stderr, or by deferring the registration to the sub-app callback.
- **Never call `register_taskdog_app` at import time without the guard.** The
  `find_spec` check is what keeps `life --help` working in a venv without
  `langchain-mcp-adapters`.
- **Never add a command to `cli.py` that belongs to a central, a handler or a
  plugin.** `cli.py` is wiring.
- **Never call `run_pytest()` without a timeout.** The default is 300 s per
  submodule path; `find_test_dirs` returns every submodule that has a `tests/`
  dir, so an unbounded run can hang the console.
- `log.py` uses `datetime.utcnow()` (deprecated in 3.12+); the formatter
  timestamps are UTC but the call should be `datetime.now(timezone.utc)`.

## COMMANDS
```bash
python -m life.cli --help
python -m life.cli status --json
python -m life.cli test --list
python -m life.cli config show --path
```
