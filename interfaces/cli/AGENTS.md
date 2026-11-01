# interfaces/cli

Typer command surface of the mesh (`life ...`). Earns its file: distinct
domain (CLI consumer, not the Textual TUI), complexity score 12, 23 importing
files repo-wide.

## OVERVIEW
Consumer/producer CLI over `data/` — reads task slices, enqueues `TaskChange`
events, manages backend processes. Entry: `python -m interfaces.cli <cmd>`.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Root Typer app + task commands | `read_tasks.py` | `list`, `done`, `stats`, `mesh-show`, `task-add`, `plan-add`, `plan-list`, `deep-agent-tasks` |
| v2 sub-app (plan/skill/agent/chat/vault) | `v2.py` | 1097 lines; 10 `register_*(app)` factories |
| Backend process control | `server.py` | `ADAPTER_REGISTRY`, `BACKEND_PROCESSES`, pidfiles |
| Kill switch consumer UX | `kill_switch.py`, `_kill_switch_helpers.py` | status/history/pause/resume/recover |
| Notifications | `notify.py`, `notify_cli.py` | file / telegram channels |
| MCP tool discovery | `mcp_runtime.py` | spawns the taskdog MCP server over stdio |
| Live taskdog dashboard | `td_tui.py` | Textual, 3 modes (dashboard/timeline/gantt) |
| Skill invocation | `invoke_skill.py`, `_skill_outputs.py` | 42-branch dispatcher |
| Tests | `tests/` | package-local `pytest.ini` |

## CONVENTIONS
- `__init__.py` puts `<repo>/src` and `<repo>` on `sys.path` *before* importing
  siblings: pytest imports the package before `conftest.py` runs, so the fixup
  cannot live there. Three more bootstraps exist — `tests/conftest.py`,
  `mcp_runtime._ensure_ikigai_src_on_path`, `v2.py`.
- The `server` and `v2` sub-apps are mounted from `__init__.py`, not declared
  at module top level.
- `v2.py` wires commands through `register_*(app)` factories with
  in-function imports; its docstring marks this "Pattern preserved (NOT
  refactored)".
- `interfaces/cli/pyproject.toml` declares no `src/ikigai` dependency (Poetry
  layout). Every third-party package imported at *module level* by
  `src.ikigai.src.agents.v2` / `mcp_server` must be mirrored there, or a clean
  `uv sync` yields `ModuleNotFoundError`.
- Package-local `pytest.ini`, `[tool.mypy]` and `[tool.ruff]` override the
  repo-root ones: `--basetemp=.pytest-tmp` avoids Windows `%TEMP%` locks, and
  `mypy_path=["../.."]` avoids "source file found twice under two module names".
- `server.py` imports adapter storage paths from the adapter modules
  (`TASKS_JSONL`, `TASKDOG_DB`, `UPI_DB`) so the registry cannot drift.

## ANTI-PATTERNS
- Never write to `vault/` from this package. Writes go to `data/` (mesh queue
  + append-only jsonl).
- Never set the kill switch here. `kill_switch.py` is a pure consumer: no new
  `src/contracts/` schema, no new `algorithm_constants.json` entry, no new
  drift invariant.
- Do not move the lazy imports in `v2.py` to module level — that recreates the
  `agents.v2.subgraph` <-> `interfaces.cli.v2` cycle.
- `typer >= 0.21` vendors Click as `typer._click`; `typer.Exit` is not a
  subclass of `click.exceptions.Exit`. Assert on `typer.Exit`.
- `mcp` is pinned `<2` — mcp 2.x removed `mcp.server.fastmcp`.
- `agent_consumer` / `agent_propagator` are functions inside
  `review_queue_worker`, not processes: `life server start/stop` must not
  spawn them.
- `plan-add` / `plan-list` carry zero policy-engine, QHE or scoring imports.
- Two `life` console scripts exist — `interfaces/cli/pyproject.toml` ->
  `interfaces.cli.read_tasks:app` and root `pyproject.toml` ->
  `life.cli:_main_console`. Know which one is installed.

## COMMANDS
```bash
python -m interfaces.cli <command>       # module entry point
cd interfaces/cli && uv run pytest        # package-local suite
cd interfaces/cli && uv run ruff check . && uv run mypy .
```
