# AGENTS.md — `src/`

**Canonical scope (ADR-037) — the serverless source layer.** The retired PC-only runtime (the LangChain/LangGraph harness, the local chat REPL, the stdio MCP fork servers and the TUI) is no longer published; what stays is the **data layer canonical** plus the surfaces a cloud client can actually call.

## OVERVIEW
`src/` holds several independent Python toolchains with different import identities and test runners. Root `AGENTS.md` names the layers; this file records how they differ on disk.

## STRUCTURE
```
src/
├── contracts/           # canonical Pydantic v2 contracts — Hatchling project, own uv.lock + .venv
├── mesh/                # Phase 3 data mesh — NO pyproject; import-path-only; own ruff.toml
├── services/            # domain services (artifact / relation / embedding) — the only layer clients reach
├── transport/           # MCP surface over the services (FastMCP) — ADR-011
├── data/                # runtime state (pytest-tmp, *.db) — NOT source
├── agents/              # planner layer: memory/ + reflection/
├── ikigai/              # Poetry project; only the strategics loader remains under src/
├── life_tatics/         # time-block / screentime CLI (Typer)
└── planner/             # markdown-only planning docs, no code
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Shared model definitions | `src/contracts/` | the single source of truth — never re-define `UEID`, `Task`, `TaskChange` |
| Cross-fork task view | `src/mesh/` | write path via `data/review_queue/`; adapters: `base`, `cli`, `taskdog` |
| Domain services | `src/services/` | validation, versioning, idempotency live here |
| MCP tool surface | `src/transport/mcp_server.py` | exactly six tools, drift-guarded; transport via `IKIGAI_MCP_TRANSPORT` |
| Cross-session memory | `src/agents/memory/cross_session.py` | structural extraction, not an LLM call |
| Reflection subsystem | `src/agents/reflection/` | LLM-free by contract |
| Strategic prose loader | `src/ikigai/src/strategics/loader.py` | read-only |
| Time-block / screentime CLI | `src/life_tatics/` | Typer; `cli.py` → `domain/` |
| Planning specs (no code) | `src/planner/`, `src/life_tatics/time-lenghts_reviews.md` | markdown only; canonical temporal model lives in the `life_tatics` copy |

## CONVENTIONS
- **Build systems differ per sub-directory — never merge them.** `src/contracts/` is a standalone Hatchling project (`pyproject.toml`, `uv.lock`, own `.venv`); `src/ikigai/` is a Poetry project (`poetry.lock`, own `.venv`) whose `packages` list installs `strategics` from `src/` plus `sys_ikigai` from the repo root; `src/mesh/` has **no** `pyproject.toml` and is **not** in the root setuptools `packages` list, so it is import-path-only — the root console script `td = "src.mesh.taskdog_cli:main"` resolves solely because the repo root is on `sys.path`.
- **`src/` is not a package.** No `src/__init__.py`. `import src.contracts.X` works because the *repo root* is on `sys.path`; `import contracts.X` works because `src/` is on `sys.path` (`pytest.ini` sets `pythonpath = src src/ikigai/src`). Both spellings are live in production code — pick the one the surrounding package already uses.
- **One `agents` package.** `src/agents/` (planner: `memory/`, `reflection/`) is the only `agents` package in the tree; the IKIGAI-internal harness directory that used to merge into it is retired.
- **The transport is the client boundary.** A client speaks MCP to `src/transport/mcp_server.py`; the transport calls `src/services/`; the services own the domain rules. No layer may skip a level.
- **Ruff config is per-package, not inherited.** Root `pyproject.toml` has **no** `[tool.ruff]` table. Real configs: `src/mesh/ruff.toml`, `src/contracts/pyproject.toml`, `src/ikigai/pyproject.toml` — all `line-length = 100`, `target-version = "py311"`.
- **`from __future__ import annotations`** at the top of nearly every module; `src/life_tatics/domain/` and `src/mesh/adapters/{cli,base}.py` are the exceptions.

## ANTI-PATTERNS
- **Never re-introduce the retired runtime** (ADR-037): no `src/ikigai/src/agents`, `chat`, `mcp_server`, `plugins`, no `src/tuiboard`, no `src/solverforge_calendar`, no `interfaces/tui`. A drift test fails if any of them is tracked again.
- **Never add a `pyproject.toml` to `src/mesh/`** to "fix" its tooling — it is deliberately import-path-only, and the nested `ruff.toml` (not `pyproject.toml`) is what Ruff reads there.
- **Never let a transport tool contain SQL or policy.** The transport translates intent; the services decide.
- **Never edit `src/data/`.** It holds `pytest-tmp/` and stray `*.db`; `src/data/` is runtime state that leaked into the source tree, not code.
- **Never treat `src/planner/` as code.** It is markdown-only (SCALAR backlog, temporal-model reviews); no Python module may be added there.

## NOTES
- **Import identity:** `from src.contracts.X` and `from sys_ikigai.X` are *two distinct module objects* — monkeypatching must patch BOTH.
- **UEID drift is real:** the shipped `src/contracts/common.py::_UEID_PATTERN` is wider than the canonical literal (`^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`, ADR-014). Never re-define `UEID` — extend the canonical one.
- **Temporal model:** `src/life_tatics/time-lenghts_reviews.md` is canonical (`rho = 11/15`, `WAVE = 15 D = 11 W`, `CYCLE = 45 D = 33 W`, `PHASE = 180 D = 132 W`); `src/planner/time-lenghts_reviews.md` is the earlier variant. When a temporal number is disputed, the `life_tatics` copy wins.
