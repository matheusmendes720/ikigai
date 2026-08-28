# Agent 4 — mcp-gateway + interfaces + data layer

**Source:** `Agent` tool dispatched 2026-08-27
**Scope:** Map mcp-gateway, native interfaces (cli/tui), data/ directory, CI, fork inventory
**Status:** COMPLETE

---

## 1. mcp-gateway — `C:\Users\mathe\code_space\apps\mcp-gateway\`

**Status: REAL gateway.** `DELEGATION_REPORT.md` documents 10 commits (`1f1b137` → `1aa0905`) completed 2026-08-26; 2 test files (`test_router.py` 5 tests, `test_integration.py` 5 tests) all passing per report.

### Stack
- **FastAPI** + **uvicorn** (HTTP transport on port 3737)
- **pyyaml** for config, **sse-starlette** for streaming
- Entry: `mcp-gateway = "mcp_gateway.main:main"` (file: `pyproject.toml:1-13`)
- Routes: `/mcp` POST + `/health` GET
- Env: `MCP_GATEWAY_PORT`

### src/ files

| File | Role |
|------|------|
| `__init__.py` | empty |
| `config.py` | `BackendConfig` dataclass + `load_config()` |
| `stdio_client.py` | `StdioClient` (asyncio subprocess JSON-RPC) |
| `process_manager.py` | `ProcessManager` (spawn/restart, restart_delay=5s) |
| `router.py` | `build_router()` (prefix routing: `board_*`, `taskdog_*`, `calendars_*`, etc.) |
| `protocol.py` | `handle_mcp_request()` (initialize / tools/list / tools/call / ping) |
| `main.py` | FastAPI app |

### Wiring (config/gateways.yaml)

- `board_*` → tuiboard (bun, cwd `C:/Users/mathe/code_space/apps/kanban/tuiboard`)
- `taskdog_*`, `list_tasks`, `get_task`, `create_task`, etc. → taskdog (python)
- `calendars_*`, `events_*`, `projects_*`, `dependencies_*`, `google_*`, `upi_*` → solverforge-calendar (cargo)
- default = solverforge-calendar

### ⚠️ CRITICAL BUG — STALE cwd paths

```yaml
# gateways.yaml:4,9,14
cwd: "C:/Users/mathe/code_space/apps/kanban/tuiboard"
cwd: "C:/Users/mathe/code_space/apps/dev-tools/taskdog"
cwd: "C:/Users/mathe/code_space/apps/calendar/solverforge-calendar"
```

**These paths no longer exist.** Forks were moved to `life-oss/interfaces/{tuiboard,taskdog,solverforge-calendar}`. Gateway would crash on `start_all()` until someone updates the config.

### Zero ikigai references

`grep -r "ikigai" apps/mcp-gateway/` returns ZERO matches. The gateway is for user-view forks, NOT the AI kernel. Confirms the AI-native strategic model migration.

---

## 2. data/ directory inventory — `life-oss/life/data/`

| File | Type | Size | Runtime/Session | Owner |
|------|------|------|-----------------|-------|
| `vibe_ops.db` | SQLite | 143,360 B | runtime (19 tables, schema v4, last written 2026-06-03) | vibe-ops |
| `vibe_mesh.db` | SQLite | 0 B | runtime — empty placeholder, never opened | vibe-ops |
| `chroma_db/chroma.sqlite3` | SQLite | 188,416 B | runtime (1 collection, 2 segments, 18 migrations, 0 embeddings) | chroma |
| `boulder.json` | JSON | 21,361 B | runtime, STALE — last updated 2026-06-30T15:07:58.507Z | atlas/Sisyphus-Junior |
| `test-fixtures/test_f3.db` | SQLite | 49,152 B | test | test suite |
| `test-fixtures/test_f3_empty.db` | SQLite | 49,152 B | test | test suite |
| `test-fixtures/test_full.db` | SQLite | 49,152 B | test | test suite |
| `test-fixtures/test_migration.db` | SQLite | 49,152 B | test | test suite |
| `test-fixtures/test_no_vault.db` | SQLite | 49,152 B | test | test suite |
| `test-fixtures/test_orphan.db` | SQLite | 49,152 B | test | test suite |
| `period-4-verify.py` | Python | 4,514 B | session scratch | unknown |
| `session-ses_0e68.md` | Markdown | 766,070 B | session leftover | Sisyphus-Junior |
| `session-ses_118c.md` | Markdown | 330,294 B | session leftover | Sisyphus-Junior |
| `2026-08-26-184318-preciso-encaixar-o-pav-system-no-cusersmathe.txt` | transcript | 69,805 B | session leftover | Claude |
| `2026-08-27-113757-this-session-is-being-continued-from-a-previous-c.txt` | transcript | 72,165 B | session leftover | Claude |

### vibe_ops.db schema (19 tables, ALL 0 rows except `sqlite_sequence` placeholder)

`dev_backlogs`, `dev_changelogs`, `dev_projects`, `dev_roadmaps`, `habit_states`, `habits`, `mesh_metadata_catalog`, `mesh_state_machine`, `planning_entities`, `policy_decisions`, `roadmap_sync`, `study_notes`, `study_plans`, `study_sessions`, `study_topics`, `temporal_cycles`, `temporal_phases`, `temporal_waves`.

### Missing JSONL files

- **`tasks.jsonl`**: does not exist (CLI `interfaces/cli/read_tasks.py:27-29` would return `[]`)
- **`feedback.jsonl`**: does not exist (CLI `done` would create on first write at `read_tasks.py:144`)
- **`sync_log.jsonl`**: does not exist (not referenced anywhere)

### boulder.json (stale — 2026-06-30)

```json
{
  "active_plan": "C:\\Users\\mathe\\code_space\\life-oss\\life\\.omo\\plans\\agentic-markdown-system.md",
  "started_at": "2026-06-30T13:22:01.819Z",
  "session_ids": ["opencode:ses_118cec609ffeXHWfC78wFT5ADp"],
  "plan_name": "agentic-markdown-system"
}
```

References `.omo/plans/` paths — `.omo/` was renamed to `vault/` per reorg. Active work ID `agentic-markdown-system-40d0ce47` worktree doesn't exist anymore.

---

## 3. Native interfaces — `life-oss/life/interfaces/`

### cli/

- **pyproject.toml:** `name = "life-interface-cli"`, `version = "0.1.0"`. Deps: `typer>=0.12`, `rich>=13.7`. Entry: `life-tasks = "read_tasks:app"`. Description: "Interface CLI — reads structured tasks from data/tasks.jsonl".
- **read_tasks.py commands (206 lines):**
  - `list` (line 66) — filters by `--horizon`, `--done`, `--json`, `--limit`
  - `done` (line 105) — marks task done, appends to `data/feedback.jsonl` (line 144)
  - `stats` (line 157) — total/done/pending %, by-horizon, by-priority breakdown
  - Helpers: `_tasks_path()` (line 27), `_feedback_path()` (line 32), `_read_tasks()` (line 37)
  - Reads `data/tasks.jsonl`, writes `data/feedback.jsonl`

### tui/

- **Status: README-ONLY placeholder.** Single file: `README.md` (44 lines).
- No pyproject.toml, no code, no entry point. README describes planned Textual TUIs (`daily-view`, `kanban`, `calendar`) but none are built.

---

## 4. CI — `.github/workflows/`

### ci.yml (5 jobs)

| # | Job | Trigger | What runs |
|---|-----|---------|-----------|
| 1 | `code-review-checks` | PR only | `code_review.py` static checks |
| 2 | `quality-gates` (matrix) | push/PR | `ruff check src/` + `ruff format --check` + `mypy src/` + `pytest -m "not e2e"` |
| 3 | `operational-e2e` | push/PR | `cd src/operational && uv run pytest -m e2e` |
| 4 | `vibe-ops-scratch` | push/PR | `cd vibe-ops && uv run python verify_mesh.py` |
| 5 | `git-hooks` | push/PR | `cd src/operational && uv run pre-commit run --all-files` |

### Quality-gates matrix (lines 56-67)

- `operational-core` → `src/operational/packages/core`, Python 3.11, uv
- `ikigai` → `src/ikigai`, Python 3.11, poetry
- `vibe-ops` → `vibe-ops`, Python 3.11, uv

### Test coverage gaps

- **ikigai**: YES
- **PAV (operational)**: YES
- **interfaces**: **NO.** Neither `interfaces/cli` nor `interfaces/tui` is in any CI matrix. Zero CI coverage for native interfaces.

### openwiki-update.yml

Daily cron `0 8 * * *` UTC, runs `openwiki code --update --print` using MiniMax M2.7-highspeed via Anthropic-compatible gateway at `api.minimax.io`. Creates auto-PR.

---

## 5. Forks inventory

| Fork | Lang | Source files | Framework | MCP entry point |
|------|------|--------------|-----------|-----------------|
| `tuiboard` | TypeScript (Bun) | 113 (total 11,489 incl. node_modules) | `@opentui/solid`, `solid-js`, `zod`, `chokidar`, `@opentelemetry/sdk-node` | `bin/tuiboard.ts` (TUI), `bin/tuiboard-mcp.ts` (MCP server); v0.8.4 |
| `taskdog` | Python (uv workspace, 5 packages) | 2,101 (total 7,683 incl. .venv) | `taskdog-core/client/server/ui/mcp`, `mcp>=1.2.0`, `opentelemetry-api/sdk/exporter-otlp-proto-http` | `taskdog-mcp = "taskdog_mcp.main:main"`; v0.23.0 |
| `solverforge-calendar` | Rust (Cargo) | 60 (total 11,926 incl. target/) | `ratatui 0.29`, `crossterm 0.28`, `rmcp 3.1` (MCP), `tokio`, `rusqlite 0.38`, `google-calendar3 7.0`, `keyring 3`, `rrule 0.14`, `opentelemetry 0.32`, `axum 0.8` | `solverforge-calendar-mcp` bin at `src/bin/solverforge-calendar-mcp.rs`; v0.3.0 |

### Worktree branches

Each fork ships with a parallel `-otel-worktree/` for OpenTelemetry instrumentation:
- `tuiboard-otel-worktree`
- `taskdog-otel-worktree`
- `solverforge-calendar-otel-worktree`
- `solverforge-build-fix-worktree` (extra)

All are git worktrees with OTel branches.

---

## 6. Key Cross-Cutting Findings

1. **mcp-gateway is fully decoupled from ikigai.** Zero ikigai references. Gateway is user-view transport (HTTP→stdio for 3 forks); ikigai is AI kernel with its own MCP server.

2. **mcp-gateway config has STALE cwd paths** pointing to `code_space/apps/...`. Forks now live at `life-oss/interfaces/...`. Gateway would fail on `start_all()` until config is updated.

3. **All `data/*.jsonl` files are MISSING.** The CLI in `interfaces/cli/read_tasks.py` returns empty results. Consistent with "data-first methodology" memory — IKIGAi in data-first mode awaiting 5+ manual logs.

4. **`data/vibe_ops.db` has full schema but ZERO rows.** Schema was migrated (last write 2026-06-03) but never populated.

5. **`data/boulder.json` is from 2026-06-30** (Sisyphus-Junior era, references `.omo/plans/` pre-reorg). Entirely stale.

6. **`interfaces/tui/` is README-only.** No code.

7. **CI does NOT test interfaces.** No ruff/mypy/pytest for `interfaces/cli/` or `interfaces/tui/`.

8. **Session leftovers ~1.2MB** in `data/session-ses_*.md` and `data/2026-08-2*.txt` — should live in `logs/` or be gitignored.

9. **3 forks each have their own MCP server** (bin/tuiboard-mcp.ts, taskdog-mcp, solverforge-calendar-mcp.rs). Deep Agent bridges to them via 10 tool wrappers.

10. **mcp-gateway orphan**: ~1600 lines of gateway + adapters + tests in worktree `feat/data-model-unification`, **NEVER MERGED**. Decision pending: merge or discard? (see [[ag3-gateway-orphan-2026-08-27]])
