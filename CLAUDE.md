# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Algorithmic Life OS** — A personal productivity orchestration system written in Python. It is a CLI hub (`life`) that integrates domain "centrals" (task, finance, knowledge, research) with daily/weekly handlers and a plugin system. The repo also contains two submodules:

- `life-ops/` (`life-tatics`): Standalone time-management CLI (Poetry project, Typer).
- `vibe-ops/`: Architecture docs, ADRs, data-mesh specs, and planning documents.

## Running the Code

### Main CLI
The repo root (`life/`) is intended to be the Python package `life`. The main CLI entry point is `cli/cli.py` (`life.cli:app`).

```bash
# From repo root (requires parent dir on PYTHONPATH, or a proper editable install)
python -m life.cli

# Common commands
python -m life.cli --help
python -m life.cli daily run
python -m life.cli weekly run
python -m life.cli task today
python -m life.cli finance report --period week
python -m life.cli submodules
python -m life.cli health
```

**Note on imports:** The codebase is in a transitional state. Some files import from `life.cli.config` / `life.cli.log`, while others still import from `life.config` / `life.log`. The root `__init__.py` was deleted from git; restoring it may be needed for `python -m life.cli` to work.

### Tests
There is no Makefile or pytest.ini. Tests are run via the built-in CLI command:

```bash
python -m life.cli test           # Run pytest across all submodules with tests/
python -m life.cli test --list    # List discovered test dirs
python -m life.cli test -s <name> # Run only one submodule
```

`cli/test_runner.py` discovers submodules containing `tests/` or `test_*.py` and runs `pytest` in each.

### life-ops Submodule (`life-tatics`)
This is a standalone Poetry project. It must remain decoupled from the main `life/` orchestrator.

```bash
cd life-ops
poetry install
poetry run life-tatics --help
```

## Architecture

### Central-Handler Pattern
- **`centrals/`** are domain hubs (`task`, `finance`, `knowledge`, `research`). Each central exposes Typer subcommands that dispatch to submodules or external scripts (Taskwarrior, fin_ops, etc.).
- **`handlers/`** (`daily.py`, `weekly.py`) orchestrate centrals by running the main CLI as a subprocess (`python -m life.cli <central> <cmd> --json`) and aggregating results.

### BaseCentral
All centrals inherit from `BaseCentral` (`centrals/base.py`). It provides a single key method:

```python
run_cli(cwd: Path, module: str, args: list[str], json_out: bool = True) -> dict[str, Any]
```

This runs `python -m <module> <args> [--json]` in a subprocess and returns `{ok, stdout, stderr, data}`.

### Submodule Dispatch
Most centrals do not contain heavy logic directly. Instead, they delegate to standalone submodules configured in `LifeConfig.submodules`:

| Central   | Submodule(s)                                    |
|-----------|-------------------------------------------------|
| `task`    | Taskwarrior binary (`task`), bash scripts in `taskwarrior/scripts/` |
| `finance` | `fin_ops` (Python CLI run via `BaseCentral.run_cli`) |
| `knowledge` | `leitura`, `mindmaps`, `notes` (each standalone Python CLIs) |
| `research`| `research` (standalone Python CLI)              |

Submodules are resolved by `cli/config.py` (`LifeConfig.get_submodule_path`).

### Plugin System
Plugins implement `PluginProtocol` (`plugins/protocol.py`) with `register(app)` and optional lifecycle hooks (`before_daily`, `after_daily`, etc.).

- `plugins/loader.py` discovers plugins from `plugin_dirs` (configurable in `config/life.yaml`).
- `plugins/builtin/health_check.py` is the built-in plugin; it registers the `health` command.
- Plugins are auto-registered at startup in `cli/cli.py` via `register_plugins(app)`.

### Config
`cli/config.py` (`LifeConfig`, `load_config`) is the single source of truth. It loads `config/life.yaml` if present, otherwise falls back to hardcoded defaults. Key paths include `submodules`, `task_scripts`, `log_dir`, and `plugin_dirs`.

## Important Rules (from Cursor/Copilot configs)

### `life-ops/` (`life-tatics`)
- **Must remain standalone.** Do not import or depend on modules from the root `life/` package or `taskwarrior/` scripts.
- **Machine-readable output:** Any new CLI command must support a `--json` flag.
- **Spec alignment:** When modifying domain logic or CLI features, update `life-ops/SPEC.md`.

### `vibe-ops/`
- **Strict append-only.** Deleting, summarizing, or rewriting existing content is prohibited.
- If the user explicitly asks to refactor, first present a plan and wait for explicit approval before making destructive changes.
