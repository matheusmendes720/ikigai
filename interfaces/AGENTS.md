# interfaces/ — Interface Layer

**Score:** 9 (53 files, 72% code, 398 module-level symbols, 286 exports)
**Role:** consumer surfaces over `data/`. Read-only on `vault/`.

## OVERVIEW

Three unrelated surfaces that share no package: a Typer CLI, a FastAPI + HTML
dashboard, and a Textual operator TUI. `interfaces/` and `interfaces/tui/` are
implicit namespace packages (no `__init__.py`); `interfaces/cli/` and
`interfaces/studio/` are regular packages.

## STRUCTURE

```
interfaces/
├── cli/           # Typer CLI + mesh consumer + IKIGAI v2 sub-app -> cli/AGENTS.md
├── studio/        # FastAPI + vanilla-JS dashboard               -> studio/AGENTS.md
└── tui/operator/  # Textual operator control plane              -> operator/AGENTS.md
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Mesh task read/write | `interfaces/cli/read_tasks.py` | reads `data/tasks.jsonl`; `task-add` is the only producer |
| IKIGAI v2 surface | `interfaces/cli/v2.py` | 1098 lines; `plan`, `agent`, `chat`, `vault-*`, `td` alias |
| Backend topology | `interfaces/cli/server.py` | `ADAPTER_REGISTRY`: cli / taskdog / solverforge_calendar / a2ui |
| Kill-switch UX | `interfaces/cli/kill_switch.py` | pure consumer of `sys_ikigai.security.kill_switch` |
| Notifications | `interfaces/cli/notify.py` | router: stdout, file, telegram |
| MCP spawn + tool loader | `interfaces/cli/mcp_runtime.py` | `_ensure_ikigai_src_on_path`, `get_mcp_tools_async/sync` |
| Taskdog dashboard | `interfaces/cli/td_tui.py` | Textual; modes dashboard / timeline / gantt |
| Browser dashboard | `interfaces/studio/server.py` | uvicorn on 127.0.0.1:8765 |
| Operator control plane | `interfaces/tui/operator/app.py` | 5 Textual tabs, read-only |

## CONVENTIONS

- The `sys.path` bootstrap lives in the package `__init__.py`, not in
  `conftest.py`: pytest resolves the test module's package chain *before*
  conftest runs, so conftest fixups arrive too late for `from src.contracts...`.
- Sub-apps are mounted by `register_*(app: typer.Typer)` functions, never by
  module-level `@app.command` on a shared root. That indirection is what breaks
  the `agents.v2.subgraph` <-> `proposal_executor` <-> `interfaces.cli.v2`
  import cycle.
- Windows-first runtime: `taskkill`, `ctypes` `TerminateProcess`, `pathlib`
  everywhere; comments note "Windows: SIGTERM not always available".
- `from __future__ import annotations` is missing in several `__init__.py`
  files (`interfaces/cli/__main__.py`, `interfaces/studio/__init__.py`).
- `interfaces/tui/README.md` is SUPERSEDED (2026-08-30): it describes the
  planned daily/kanban/calendar consumer apps. User-facing views now live in
  the forks; `interfaces/tui/` is the operator control plane only.

## ANTI-PATTERNS

- Never write `vault/` from an interface. Deep Agent is the sole vault writer;
  interface writes land in `data/` only (mesh queue + jsonl, append-only).
- Never raise at import time from an interface module. Register a placeholder
  sub-app that reports the failure on invocation; an import-time `typer.Exit`
  once took down every `life v2 *` command.
- Never swallow an exception silently. A failed taskdog fires a warning and
  queues the request for human review.
- Never add a schema to `src/contracts/` from an interface layer. Declare a
  local strict Pydantic model instead (`KillSwitchAuditEntry`,
  `CreateTaskBody`, `ChatBody`).
- Operator TUI MUST NOT mutate state (dual-layer architecture invariant).
- Never assume the `interfaces/cli` venv has `src/ikigai` installed: it is a
  Poetry project reached only via `PYTHONPATH` plus a `sys.path` bootstrap.
