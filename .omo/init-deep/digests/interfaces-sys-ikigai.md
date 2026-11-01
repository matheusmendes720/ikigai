# DIGEST — subtree `interfaces/` + `sys_ikigai/`

Scope: `interfaces/` (cli, studio, tui/operator) and `sys_ikigai/`
(entities, gateway, vault, security, propagation, state_machines, adapters,
cli, plus legacy types/enums/exceptions/constants).
Sources: chunk reports c17, c18, spot-checked against the real code.

## LOCATIONS WRITTEN (7)

| Path | Score | Role |
|------|-------|------|
| `interfaces/cli/AGENTS.md` | 12 | Typer `life ...` consumer surface; v2/server sub-apps, kill-switch UX, MCP runtime, dependency-mirroring rule |
| `interfaces/tui/operator/AGENTS.md` | 8 | Textual control-plane dashboard, 5 tabs (tasks/adapters/backend/queue/kill_switch) |
| `sys_ikigai/AGENTS.md` | 10 | Bare-namespace kernel package: map of the 8 subpackages + the legacy-vs-canonical model split |
| `sys_ikigai/vault/AGENTS.md` | 11 | `vault_write` (sole vault writer), `vault_read`, locking, frontmatter, vault->fork sync engine |
| `sys_ikigai/gateway/AGENTS.md` | 11 | `UnifiedMCPGateway` HTTP+SSE front / stdio back, stdlib only, per-fork client factories |
| `sys_ikigai/entities/AGENTS.md` | 11 | Legacy `PlanEntity` family + `plan/` shims aliasing `src.contracts` |
| `sys_ikigai/security/AGENTS.md` | 8 | Kill switch (ADR-029), `vault_write` enforcement wrapper, phase-transition validator |

## NOT WRITTEN (parent covers) — scores from the init-deep matrix

`interfaces/` 0, `interfaces/tui/` 0, `interfaces/studio` 6,
`interfaces/cli/tests` 6, `interfaces/studio/tests` 2,
`interfaces/tui/operator/tests` 4, `interfaces/cli/tests/reports` 1,
`sys_ikigai/cli` 6, `sys_ikigai/propagation` 6, `sys_ikigai/adapters` 6,
`sys_ikigai/state_machines` 6, `sys_ikigai/gateway/clients` 4,
`sys_ikigai/gateway/adapters` 6.

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

**Interfaces are three surfaces, not one.** `interfaces/cli` is a Typer CLI
(`python -m interfaces.cli <cmd>`), `interfaces/studio` is a FastAPI + vanilla
HTML/CSS dashboard, `interfaces/tui/operator` is a Textual TUI. `interfaces/`
itself is a bare container with no `__init__.py`.

**`interfaces/studio` needs an optional dependency.** `fastapi`/`uvicorn` are
NOT in the root dependency set; `server.py` raises `SystemExit("FastAPI not
installed...")` when they are missing. Default bind `127.0.0.1:8765`
(`STUDIO_HOST`/`STUDIO_PORT`/`STUDIO_LANGGRAPH_API`/`STUDIO_CHAT_TIMEOUT`/
`STUDIO_HEARTBEAT`).

**Two competing `life` console scripts.** `interfaces/cli/pyproject.toml` ->
`life = "interfaces.cli.read_tasks:app"`; root `pyproject.toml` ->
`life = "life.cli:_main_console"`. The root `td` script ->
`src.mesh.taskdog_cli:main`.

**`interfaces/cli` is a separate uv package.** It has its own `pyproject.toml`,
`pytest.ini` (`testpaths=tests`, `--basetemp=.pytest-tmp` to dodge Windows
`%TEMP%` locks), and package-local ruff/mypy config. It does NOT declare
`src/ikigai` as a dependency (Poetry layout), so every module-level
third-party import of `src.ikigai.src.agents.v2` / `mcp_server` must be
mirrored in its `pyproject.toml` or a clean `uv sync` breaks.

**Dual import identity is live here.** `sys_ikigai.X` (bare) and `src.X`
(dotted) resolve to two distinct module instances of overlapping code. Tests
that monkeypatch must patch both.

**Two identifier regimes.** `src/contracts/common.py` holds the canonical
4-part UEID (ADR-014); `sys_ikigai/types.py` holds a LEGACY 5-part UEID
kept for old fixtures, and `sys_ikigai/entities/ueid.py` delegates to the
canonical pattern while still accepting legacy IDs.

**The gateway is stdlib-only and unauthenticated.** No starlette/fastapi,
hand-rolled JSON-RPC 2.0 over `Content-Length` framing, binds `127.0.0.1`
by decision. Its stdio server must read `sys.stdin.buffer` in binary mode or
it hangs on Windows pipes.

**Known break (verified by execution, not inferred).**
`sys_ikigai/propagation/markdown_db.py::MarkdownDB.read` imports
`DreamEntity`/`TaskEntity`/... from `sys_ikigai/entities/plan/*`, but those
shims export only `Dream`/`Task`/... — the call raises
`ImportError: cannot import name 'DreamEntity'`.

**Known documentation drift.** `interfaces/tui/operator/README.md` claims 3
tabs and "never writes anywhere"; the code has 5 tabs and the Kill Switch tab
spawns `python -m interfaces.cli kill-switch pause|resume` via `Popen`.

**Version pins that bite.** `typer >= 0.21` vendors Click as `typer._click`
(so `typer.Exit` is not a `click.exceptions.Exit`); `mcp` is pinned `<2`
because 2.x removed `mcp.server.fastmcp`.

**Docstring convention.** Modules in this subtree carry a task/ADR tag in the
docstring (`M72`, `B3.4`, `W5.3`, `ADR-029`, `ADR-033`). Keep it when editing.
