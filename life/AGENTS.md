# life

The meta-package behind the `life` console command. Earns its file: score 17
(21 files, 100% code, 78 symbols, 231 referencing files, 6 subdirectories) — the
repo's user-facing entry point.

## OVERVIEW
`life` is a Typer **hub**, not a monolith: it mounts its own centrals and
handlers and re-mounts sub-apps owned by `interfaces/cli`. Two entry points
resolve to the same app — the console script `life` (`life.cli:_main_console`)
and `python -m life.cli` (`life/cli/__main__.py`).

## WHERE TO LOOK
| Task | Path | Notes |
|------|------|-------|
| Root Typer app | `cli/cli.py` | 12 KB; mounts centrals, handlers, `notify` (the `v2`/`taskdog` sub-apps were retired with the PC-only scope, ADR-037) |
| Config + paths | `cli/config.py` | `LifeConfig`, `load_config()`, `config/life.yaml` |
| Console bootstrap | `cli/__init__.py` | `_bootstrap_repo_paths()` puts `<repo>`, `<repo>/src`, `<repo>/interfaces` on `sys.path` |
| Structured logging | `cli/log.py` | `PlainFormatter` / `JsonFormatter` |
| Cross-submodule test runner | `cli/test_runner.py` | `find_test_dirs()`, `run_pytest()`, `run_unittest()` |
| Pillar hubs | `centrals/` | `task`, `knowledge`, `research` (see `centrals/AGENTS.md`) |
| Daily / weekly flows | `handlers/` | shell out to `python -m life.cli <cmd> --json` |
| Plugin system | `plugins/` | `PluginProtocol`, `loader.py`, `builtin/health_check.py` |

## CONVENTIONS
- **Config resolution order.** `load_config()` reads `config/life.yaml` when
  present; every key is optional and falls back to a default. YAML import is
  optional (`try: import yaml`) — without PyYAML the defaults are used.
- **`DEFAULT_SUBMODULES` points at directories that actually exist**
  (`interfaces/cli`, `taskwarrior`, `strategics`, `specs`). The pre-M60 defaults
  pointed at `system/raise_data/...` paths that never existed, and the
  `interfaces/tui` entry was dropped with the PC-only scope (ADR-037) — do
  not restore them.
- **Plugin discovery order** is `life/plugins/builtin` then `<repo>/plugins`.
  A plugin is a `.py` file or a package exposing a module-level `PLUGIN` /
  `plugin` / `Plugin` attribute that is a `PluginProtocol` instance (or a
  zero-arg factory returning one).
- **Handlers re-enter the CLI.** `handlers/daily.py` and `handlers/weekly.py`
  spawn `python -m life.cli <args> --json` rather than calling the centrals
  directly, and parse the child's stdout as JSON.
- **`life status`** is a snapshot reader, not an orchestrator: it reads
  `.claude/loop/schedules.json` (presence check, not a live PID check),
  probes `http://127.0.0.1:8000/api/v1/tasks` for taskdog and reports the
  drift gate from the canonical invariant guards.
- The JSON flag name is not uniform: `json_out` in most commands, `json_output`
  in `status`, `json` in `config_show`, `json_format` in `log`. Match the
  command you are editing instead of renaming the flag.

## ANTI-PATTERNS
- **Never write to `vault/` from this package.** `life` is a reader of the
  vault; feedback goes to `data/feedback.jsonl`.
- **Never add business logic to `cli/cli.py`.** It is wiring only — a command
  belongs to a central, a handler or a plugin.
- **Never import `interfaces.cli` lazily from a command body.** `cli.py`
  imports `interfaces.cli.notify_cli` at module scope.
- **Never assume a plugin is a Python file in `<repo>/plugins`.** That
  directory is not published (ADR-037): a local tree may still hold an
  untracked `paperclipai/` plugin, but in the canonical clone
  `life.plugins.loader` only discovers `life/plugins/builtin`.
- `life/.life/logs/life.log` is a **stale artifact** from before the M60
  restructure. The live log directory is `<repo>/.life/logs` (override with
  `LIFE_LOG_DIR`).
- **New files under `life/` are not git-ignored.** `.gitignore:509-513` swallows any
  1–4 letter root dir, but `!/src/`, `!/docs/`, `!/bin/`, `!/life/` (522-536) let git
  descend into those four again (fixed 2026-11-01). `data/` and `logs/` stay
  swallowed — a new file there needs `git add -f`.
- `cli/log.py` uses `datetime.utcnow()`, which is deprecated in 3.12+.

## COMMANDS
```bash
life --help
life status [--json]
life config show [--path] [--json]
life submodules [--json]
life features [<submodule>] [--json]
life plugins [--json]
life test [--list] [--submodule NAME] [--json]
life daily run [--skip-task] [--json]
life weekly run [--skip-review] [--skip-metrics] [--json]
```
