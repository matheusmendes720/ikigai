# interfaces/cli

Typer command surface of the mesh (`life ...`). This is the **only** published
interface: the operator TUI (Textual) and the local studio server were
retired with the serverless pivot (ADR-037).

## OVERVIEW
Consumer/producer CLI over `data/` — reads task slices, enqueues `TaskChange`
events, inspects backend adapters. Entry: `python -m interfaces.cli <cmd>`.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Root Typer app + task commands | `read_tasks.py` | `list`, `done`, `stats`, `mesh-show`, `task-add`, `plan-add`, `plan-list`, `deep-agent-tasks` |
| Backend adapter control | `server.py` | `ADAPTER_REGISTRY` (`cli`, `taskdog`, `a2ui` spec-only), `ls`, `inspect`, `status`, `start`, `stop` |
| Kill switch consumer UX | `kill_switch.py`, `_kill_switch_helpers.py` | status/history/pause/resume/recover |
| Notifications | `notify.py`, `notify_cli.py` | file / telegram channels |
| Path bootstrap | `__init__.py` | puts `<repo>/src` and `<repo>` on `sys.path` **before** sibling imports |
| Package config | `pyproject.toml`, `uv.lock`, `pytest.ini` | uv-managed; deps: typer, rich, pydantic, click, pyyaml |

**Retired with the PC-only runtime (ADR-037):** `v2.py`, `mcp_runtime.py`,
`td_tui.py`, `invoke_skill.py`, `_skill_outputs.py` and the package-local
`tests/` directory are not published. The canonical agent surface is the MCP
transport at `src/transport/mcp_server.py` (repo root).

## CONVENTIONS
- `__init__.py` puts `<repo>/src` and `<repo>` on `sys.path` *before* importing
  siblings: pytest imports the package before `conftest.py` runs, so the fixup
  cannot live there.
- The `server` sub-app is mounted from `__init__.py`, not declared at module
  top level.
- `server.py` imports adapter storage paths from the adapter modules
  (`TASKS_JSONL`, `TASKDOG_DB`, `UPI_DB`) so the registry cannot drift.
- `server.py` keeps the `a2ui` adapter as **spec-only** (`storage_path=None`)
  — it documents a protocol, it is not a live fork.
- Package-local `pytest.ini`, `[tool.mypy]` and `[tool.ruff]` override the
  repo-root ones: `--basetemp=.pytest-tmp` avoids Windows `%TEMP%` locks, and
  `mypy_path=["../.."]` avoids "source file found twice under two module names".
- The CLI is a **consumer**: it never writes to `vault/` and never runs an LLM
  in the request path (zero LLM in pipelines).

## ANTI-PATTERNS
- Never write to `vault/` from this package. Writes go to `data/` (mesh queue
  + append-only jsonl).
- Never set the kill switch here. `kill_switch.py` is a pure consumer: no new
  `src/contracts/` schema, no new `algorithm_constants.json` entry, no new
  drift invariant.
- Never re-add a TUI or a stdio MCP fork server to this package (ADR-037).
  A new client surface belongs in `src/transport/`.
- `typer >= 0.21` vendors Click as `typer._click`; `typer.Exit` is not a
  subclass of `click.exceptions.Exit`. Assert on `typer.Exit`.
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
cd interfaces/cli && uv run ruff check . && uv run mypy .
```
