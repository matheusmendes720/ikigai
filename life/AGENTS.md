# life/ — Life OS Meta-Package

**Score:** 8 (20 files, 100% code, 69 module-level symbols, 49 exports)
**Role:** the `life` CLI hub — centrals, handlers, plugins, composition root.

## OVERVIEW

Layering, top to bottom:

```
life/centrals/  pillar hubs (task, knowledge, research) — BaseCentral ABC
life/handlers/  daily + weekly flows that orchestrate centrals
life/plugins/   PluginProtocol hooks (before/after daily/weekly)
life/cli/       Typer composition root + config + logging + test runner
```

Each layer reaches the one below via `python -m life.cli ... --json` or `BaseCentral.run_cli`; no hub imports a sibling hub directly.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Composition root | `life/cli/cli.py` | mounts every sub-app; `status_cmd` is the system snapshot |
| Config single source | `life/cli/config.py` | `config/life.yaml`, `LIFE_LOG_DIR`, submodule map |
| Console-script bootstrap | `life/cli/__init__.py` | `_bootstrap_repo_paths()` + `_main_console()` |
| Structured logging | `life/cli/log.py` | `get_logger()`; plain or JSON formatter |
| Cross-submodule pytest | `life/cli/test_runner.py` | `find_test_dirs` / `run_pytest` |
| Task pillar | `life/centrals/task.py` | HTTP-first to taskdog-server, CLI fallback |
| Knowledge / research pillars | `life/centrals/knowledge.py`, `research.py` | dispatch to submodules |
| Plugin discovery | `life/plugins/loader.py` | scans `plugin_dirs` for `*.py` and packages |
| Plugin contract | `life/plugins/protocol.py` | `register()` plus 4 daily/weekly hooks |

## CONVENTIONS

- **Two `life` console scripts exist.** Root `pyproject.toml` declares
  `life = "life.cli:_main_console"`; `interfaces/cli/pyproject.toml` declares
  `life = "interfaces.cli.read_tasks:app"`. `life/cli/cli.py` re-mounts the
  interface apps (`notify`, `v2`, `taskdog`) so both surfaces expose
  overlapping commands.
- `life/cli/__init__.py::_bootstrap_repo_paths()` puts the repo root, `src/`
  and `interfaces/` on `sys.path` before importing `life.cli.cli` — required
  when the package is installed non-editably and `src/*` is not importable.
- Config precedence: `config/life.yaml` -> env (`LIFE_LOG_DIR`) -> defaults.
  `ROOT` is `Path(__file__).resolve().parents[2]`.
- Default plugin dirs are `life/plugins/builtin` **and** `<root>/plugins`; default
  submodules are `interfaces_cli`, `interfaces_tui`, `taskwarrior`, `strategics`, `specs`.
- The task central hits `taskdog-server` on `http://127.0.0.1:8000` first, then
  falls back to the `taskdog` CLI via `_http_or_cli` (`transport: "http"|"cli"`).
- Plugin instances are found by the attribute name `PLUGIN`, `plugin` or
  `Plugin`; a plugin whose `register()` raises is logged as a warning, not fatal.

## ANTI-PATTERNS

- **Never write files from this package** — `life/` holds no `vault` reference
  and no write call; persistence belongs to the sanctioned write path.
- **Never swallow exceptions** — every central/handler turns `except Exception`
  into `{"ok": false, ...}`; that is how the `TASK_BIN` bug below degrades silently.
- **Never let an import-time registration raise** — `cli.py` wraps the taskdog
  registration in `except typer.Exit` and falls back to a placeholder sub-app.
- **Never hoist the `interfaces.*` imports in `life/cli/cli.py`** — they sit at
  lines 352-371, below the composition code, on purpose.
- **Never shell out to a submodule without `--json`** — `BaseCentral.run_cli` and
  both handlers append it and parse stdout as JSON.

## GOTCHAS

- `life/centrals/task.py::_run_task` builds `cmd = [TASK_BIN] + args`, but
  `TASK_BIN` is never defined (only `TASKDOG_BIN` is), so `life task today`
  returns an error dict instead of a task list.
- `life/handlers/daily.py` and `weekly.py` run `python -m life.cli`, so they
  need the repo root on `sys.path`; they do not work from an installed wheel.

## COMMANDS

```bash
python -m life.cli --help        # or `life` after `pip install -e .`
life test --list                 # discovered submodule test dirs
life status --json               # daemons, taskdog, MCP servers, langgraph, drift gate
```
