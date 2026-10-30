# interfaces/cli/ — Mesh + IKIGAI v2 Command Line

**Score:** 12 (36 files, 294 module-level symbols, 221 exports, own uv project)
**Role:** the `life` CLI proper — mesh consumer/producer plus the IKIGAI v2 sub-app.

## OVERVIEW

Standalone **uv** project with its own `pyproject.toml`, `uv.lock`, `pytest.ini`
and in-tree `.venv` — independent of the root setuptools project. Its console
script `life = "interfaces.cli.read_tasks:app"` collides with the root
project's `life = "life.cli:_main_console"`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| list / done / stats / mesh-show / task-add | `read_tasks.py` | 520 lines; `data/tasks.jsonl` |
| `server ls/inspect/status/start/stop` | `server.py` | `ADAPTER_REGISTRY` is the fork registry |
| v2 commands | `v2.py` | 1098 lines; 12 `register_*` wirings |
| Skill manifests + LLM dispatch | `invoke_skill.py` | 641 lines; `invoke_skill` has 37 branches |
| Kill switch status/pause/resume | `kill_switch.py` | exit codes 0 / 1 / 2 / 3 |
| taskdog MCP passthrough | `taskdog_app.py` | 26 tools, no LLM roundtrip |
| Taskdog TUI | `td_tui.py` | dashboard / timeline / gantt |
| MCP server spawn | `mcp_runtime.py` | `taskdog-mcp` on PATH, else `python -m mcp_server` |

## CONVENTIONS

- **Deferred imports are load-bearing.** `v2.py` keeps `Proposal`,
  `make_meta_plan_subgraph` and `execute_proposal` inside `_run_plan`'s body
  and takes the Typer instance as a parameter. Its header says
  "Pattern preserved (NOT refactored)". Do not hoist them to module level.
- Missing optional deps produce a placeholder sub-app, never an import-time
  raise: `life/cli/cli.py` gates on `find_spec("langchain_mcp_adapters")` and
  falls back to an explanatory placeholder.
- `vault-toggle` is a guarded mutation: `--plan-path` must be vault-relative
  (no `..`, no absolute), plus `--line` and `--expected`; apply/toggle also
  need `--reason` and `--actor`. Events land in `vault/.vault_events.jsonl`.
  `preview` never mutates and `apply` refuses when preview fails.
- Kill-switch exit-code matrix: 0 ok/no-op, 1 active or refused, 2 resume
  without `--confirm`, 3 empty `--reason`.
- Skill manifests gate side effects through their `outputs` list: `outputs: []`
  is surface-only, `outputs: [taskdog_create_task: ...]` fires taskdog; a
  failure must warn and write a `TaskChange` to `data/review_queue/`.
- Local tool config overrides the root: ruff `line-length = 100`,
  `select = [E,F,W,I,N,UP,B,A,C4,PT,RUF]`, `ignore = [E501]`, plus a
  `[tool.mypy]` section — the root `mypy.ini` reports "Source file found twice
  under different module names" here.
- `IKIGAI_FAKE_LLM=1` makes `invoke_skill` return a stub with no LLM call.

## ANTI-PATTERNS

- Never write `vault/` from the CLI. `read_tasks.py` is a pure consumer; all
  writes go to `data/` (mesh queue + jsonl, append-only).
- Never set the kill switch programmatically — activation lives only in
  `sys_ikigai/security/kill_switch.py` (R5/R11 forbid it).
- Never add a contract to `src/contracts/`, a constant to
  `algorithm_constants.json`, or a drift invariant from this package.
- Never let a skill invocation swallow an exception silently.
- The mesh read path is zero-LLM by design; do not introduce an LLM call into
  `list` / `done` / `stats` / `mesh-show`.

## TESTS

`uv run pytest` from `interfaces/cli/` (own `pytest.ini`: `--strict-markers`,
`--strict-config`, `--basetemp=.pytest-tmp` for Windows temp-dir locks;
markers `unit` / `integration` / `e2e`).

Patch **both** module identities in `tests/conftest.py`: `mesh.queue` and
`src.mesh.queue`. Both resolve, so patching one leaves the worker reading an
unpatched `QUEUE_DIR` and `run_once()` finds nothing.
`tests/reports/` holds append-only review reports.

## COMMANDS

```bash
cd interfaces/cli && uv sync
uv run python -m interfaces.cli --help
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy .
```
