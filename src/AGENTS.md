# AGENTS.md — `src/`

**Score 9 (files 448, subdirs 9, symbol density 2419, exports 279) — created: distinct domain.** `src/` is the source layer, split across **four independent Python toolchains**. Nothing here is a single package.

## OVERVIEW
Eight sub-directories with separate build systems, import identities, and test runners. Root `AGENTS.md` names them; this file records how they actually differ on disk.

## MCP FORK SERVERS (own subtree, no separate file)
`src/tuiboard/` and `src/solverforge_calendar/` are complete stdio MCP servers built on `sys_ikigai.gateway.stdio_server_base.StdioServerBase`. Both register tools via `server.register_tool(name=..., handler=..., schema=Model.model_json_schema())` where the handler is a module-level `handle(args: dict) -> dict`. Six of the 12 planner tools in `src/ikigai/src/agents/tools.py` target them (`solverforge_list_events`, `solverforge_create_event`, `tuiboard_list_boards`, `tuiboard_get_tasks`, `tuiboard_create_task`, `tuiboard_update_task`). Env: `TUIBOARD_DATA_DIR`, `TUIBOARD_SNAPSHOTS_DIR` (default `data/tuiboard/snapshots`), `SOLVERFORGE_DATA_DIR` (default `data/solverforge_calendar`). `sf_schedule` upserts its row even when the computed status is `conflict` or `blocked` — the caller decides whether to retry.

## PLANNER LAYER (`src/agents/`, no separate file)
- **`src/agents/memory/cross_session.py`** (425 LOC) — `SessionSummarizer` writes session summaries to `vault/ikigai/runtime/sessions/<session_id>.md`. Summarization is a **structural extraction, not an LLM call** (cost, latency, determinism). Re-storing the same `session_id` **appends** a timestamped section; it never overwrites.
- **`src/agents/reflection/`** — observational memory only. `patterns.py` holds 3 detectors (`underestimation_2x` ratio 2.0 / min sample 3, `fast_finish_tag_combo` 24h / min sample 3, `priority_churn`) as module-level constants so tests can pin them. Findings become `Proposal`s a human adjudicates; the agent never applies them itself.
- **The reflection package must stay LLM-free.** No `openai`, `anthropic`, `langchain`, `litellm`, or `MiniMax` import may appear anywhere under `src/agents/reflection/` — a drift test asserts this.

## LIFE TATICS (`src/life_tatics/`, no separate file)
Typer app with 3 commands (`block`, `screentime`, `routine`). `--json` prints via `print(json.dumps(...))` rather than `typer.echo`. `routine` is a **stub** — it always returns `{"routine": kind, "status": "pending_implementation"}`. The domain layer (`domain/time_blocks.py`, `domain/screentime.py`) is 30 LOC of stubs that echo the call back; the two files lack `from __future__ import annotations`.

## TEMPORAL MODEL — TWO NEAR-DUPLICATE DOCS (no code, but load-bearing)
`src/life_tatics/time-lenghts_reviews.md` (1583 lines) is the **canonical** version; `src/planner/time-lenghts_reviews.md` (1173 lines) is the earlier proportional variant. They differ in substance, not just length:
- Canonical: `rho = 11/15`, `WAVE = 15 D = 11 W`, `CYCLE = 45 D = 33 W`, `PHASE = 180 D = 132 W`, with explicit `floor` for D→W and `ceil` for W→D, plus `BUFFER_CYCLE = 3 D`.
- Earlier: `WORK_RATIO = 22/30` (the same 0.7333 value, different form), `WAVE = 15 dias`, and **no** `BUFFER_CYCLE`. It floors both directions.
Both are PT-BR markdown with Obsidian frontmatter and the misspelled filename `time-lenghts_reviews.md`. When a number is disputed, the `life_tatics` copy wins.

## STRUCTURE
```
src/
├── contracts/           # canonical Pydantic v2 contracts — Hatchling project, own uv.lock + .venv
├── mesh/                # Phase 3 data mesh — NO pyproject; import-path-only; own ruff.toml
├── ikigai/              # deep agent + MCP server — Poetry project (own poetry.lock + .venv)
│   └── src/             # the actual agent runtime packages (agents, chat, mcp_server, ...)
├── agents/              # planner layer — memory/ + reflection/; merged into ikigai's `agents` pkg
├── tuiboard/            # kanban MCP server (stdio)
├── solverforge_calendar/# calendar MCP server (stdio)
├── life_tatics/         # time-block / screentime CLI (Typer)
├── planner/             # markdown-only planning docs, no code
└── data/                # runtime state that landed here (pytest-tmp, checkpoint DBs) — NOT source
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Shared model definitions | `src/contracts/` | imported by 91 repo files |
| Cross-fork task sync | `src/mesh/` | imported by 89 repo files |
| Agent runtime | `src/ikigai/src/` | v2 LangGraph graph, MCP servers, paperclip |
| Cross-session memory | `src/agents/memory/cross_session.py` | 425 LOC, the largest planner file |
| Reflection subsystem | `src/agents/reflection/` | LLM-free by contract |
| Kanban fork (MCP) | `src/tuiboard/` | `server.py` registers 4 tools; `tools/` = 4 `handle()` modules |
| Calendar fork (MCP) | `src/solverforge_calendar/` | `server.py` registers 3 tools; `tools/` = 3 `handle()` modules |
| Time-block / screentime CLI | `src/life_tatics/` | Typer; `cli.py` -> `domain/` |
| Planning specs (no code) | `src/planner/`, `src/life_tatics/time-lenghts_reviews.md` | markdown only; canonical temporal model lives in the `life_tatics` copy |

## CONVENTIONS
- **Build systems differ per sub-directory — never merge them.** `src/contracts/` is a standalone Hatchling project (`pyproject.toml`, `uv.lock`, own `.venv`); `src/ikigai/` is a Poetry project (`poetry.lock`, own `.venv`) whose `packages` list installs `agents`, `chat`, `mcp_server`, `observability`, `strategics`, `plugins` from `src/` plus `sys_ikigai` from the repo root; `src/mesh/` has **no** `pyproject.toml` and is **not** in the root setuptools `packages` list, so it is import-path-only — the root console script `td = "src.mesh.taskdog_cli:main"` resolves solely because the repo root is on `sys.path` (i.e. run it from the repo root).
- **`src/` is not a package.** No `src/__init__.py`. `import src.contracts.X` works because the *repo root* is on `sys.path`; `import contracts.X` works because `src/` is on `sys.path` (`pytest.ini` sets `pythonpath = src src/ikigai/src`). Both spellings are live in production code — pick the one the surrounding package already uses.
- **Two directories named `agents`.** `src/agents/` (planner: `memory/`, `reflection/`) and `src/ikigai/src/agents/` (IKIGAI internal) are merged into ONE logical package: each `__init__.py` appends the sibling directory to `__path__`. Symmetric — both files must stay in sync.
- **Ruff config is per-package, not inherited.** Root `pyproject.toml` has **no** `[tool.ruff]` table despite `AGENTS.md` claiming one. Real configs: `src/mesh/ruff.toml`, `src/contracts/pyproject.toml`, `src/ikigai/pyproject.toml` — all `line-length = 100`, `target-version = "py311"`, same `select`/`ignore` set.
- **`from __future__ import annotations`** at the top of nearly every module; `src/life_tatics/domain/` and `src/mesh/adapters/{cli,base,solverforge_calendar}.py` are the exceptions.

## ANTI-PATTERNS
- **Never add a `pyproject.toml` to `src/mesh/`** to "fix" its tooling — it is deliberately import-path-only, and the nested `ruff.toml` (not `pyproject.toml`) is what Ruff reads there.
- **Never move or merge the two `agents/` directories.** The `__path__` merge is the only reason `agents.memory` and `agents.v2` coexist.
- **Never edit `src/data/`.** It holds `pytest-tmp/` and stray `*.db`; `src/data/` is runtime state that leaked into the source tree, not code.
- **Never treat `src/planner/` as code.** It is markdown-only (SCALAR backlog, temporal-model reviews); no Python module may be added there.
