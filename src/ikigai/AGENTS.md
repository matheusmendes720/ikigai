# AGENTS.md — `src/ikigai/`

**Score 10 (360 files, 10 subdirs, own Poetry config, 2131 symbols, 177 exports, imported by 95 repo files) — created: distinct domain.** The IKIGAI Poetry sub-project: MCP server, deep agent, paperclip orchestrator, souls, and their drift net.

## OVERVIEW
A standalone Poetry project (`name = "ikigai"`, `version = "0.1.0"`, `python = "^3.11"`) with its own `.venv`, its own `poetry.lock`, and its own `pyproject.toml`. It does **not** inherit the root's build config.

## STRUCTURE
```
src/ikigai/
├── pyproject.toml       # Poetry; console scripts + packages + pytest + ruff config
├── poetry.lock          # Poetry lockfile
├── uv.lock              # ALSO present — see ANTI-PATTERNS
├── src/                 # the importable packages (agents, chat, mcp_server, ...)
├── bin/                 # ikigai_serve.py — HTTP server entrypoint (127.0.0.1:8765)
├── scripts/             # sitecustomize.py (auto-imported) + observability repro scripts
├── souls/               # 3 soul profiles (planner/critic/stoic) + loader
├── tools/               # vault_taskdog_sync.py, views.py (dev CLIs)
├── contracts/           # proposal.py — Meta-Planner contracts (NOT src/contracts)
├── tests/               # 104 pytest files incl. the whole drift net
├── data/matheus/        # per-persona runtime data (dreams, objectives, projects)
├── vault/               # local vault tree + .vault_audit.log
├── docs/                # observability specs, session logs, backend deep-dive report
└── .env.example         # template only; .env is gitignored
```

## WHERE TO LOOK
| Task | Location |
|---|---|
| MCP server | `src/mcp_server/server.py`; run via `python -m mcp_server` from `src/ikigai/src` |
| Deep agent harness | `src/agents/deepagents_harness.py` (`--chat --thread <id>`) |
| Planner tools (12) | `src/agents/tools.py` → `IKIGAI_TOOLS` |
| v2 LangGraph graph | `src/agents/v2/graph.py` — registered in root `langgraph.json` |
| Paperclip orchestrator | `src/agents/paperclip/` (graph, policy, router, persistence, cli) |
| Soul profiles | `souls/*.md` + `souls/loader.py` |
| Drift net | `tests/test_canonical_scope.py`, `test_drift_invariants.py`, `test_drift_extended_invariants.py` |
| Meta-Planner contracts | `contracts/proposal.py` (11 Pydantic models) |

## CONVENTIONS
- **Console scripts** (from `[tool.poetry.scripts]`): `ikigai-maintainer-mcp` → `run_mcp_server:main`, `ikigai-deep-agent` → `agents.deepagents_harness:main`, `paperclip` → `agents.paperclip.cli:main`, `paperclipai-bridge` → `plugins.paperclipai_bridge.main:app`.
- **Poetry `packages` installs top-level names, not `ikigai.*`.** `agents`, `chat`, `mcp_server`, `observability`, `strategics`, `plugins`, and `ikigai_wrapper.py` are installed from `src/`, plus `sys_ikigai` from the repo root (`from = "../.."`). That is why runtime code writes `from agents.v2…`, not `from ikigai.agents.v2…`.
- **Pytest config lives in this project's `pyproject.toml`**: `testpaths = ["tests"]`, `pythonpath = ["src", "../.."]`, `addopts = "-v --tb=short"`. Root `pytest.ini` is a separate, root-only config.
- **`scripts/sitecustomize.py` is auto-imported** whenever that directory is on `PYTHONPATH` (the `langgraph-dev.bat` / `langgraph-bg.bat` launchers). It patches Starlette's `StaticFiles` for the `/ui/` mount; it is idempotent via a module flag. Do not stack a second copy.
- **`souls/loader.py` exports exactly `load_soul` and `known_profiles`.** Profile names are validated before any filesystem access; path traversal is rejected.
- **`contracts/proposal.py` is a separate contract family from `src/contracts/`.** It defines its own `Proposal` with `approval_state`, its own `IntentClassification`, and its own UEID regex (`{2,5}` 4-part) — it is *not* the canonical `TaskChange`.

## ANTI-PATTERNS
- **Never move dev tools out of `[tool.poetry.group.dev.dependencies]`.** A previous move to a PEP-735 `[dependency-groups]` table made Poetry 2.x resolve the group from there only, silently dropping `pytest`/`ruff`/`mypy` from `poetry.lock` and leaving CI without a runner. The `pyproject.toml` comment records this — do not undo it.
- **Never commit `.env`.** It is gitignored; `.env.example` is the template, and it instructs rotating a previously leaked key before use.
- **Never import `sys_ikigai.core.scoring`, `ikigai.core.heuristics`, or `cybernetics.daily_loop`** from this package (ADR-013 planner-only).
- **Never import `src/ikigai/src/agents/v2/tools_legacy_reference.py` or `harness_legacy_reference.py`.** They are frozen `if False:` blocks preserved for inspection.
- **`uv.lock` and `poetry.lock` both exist.** Poetry is the source of truth for this project; the stray `uv.lock` is a leftover — do not add uv-specific config to `pyproject.toml`.
- **Doc drift to ignore:** `README.md` says `poetry run ikigai` (no such script) and `MCP_GATEWAY.md` says `poetry run ikigai-mcp` (the real name is `ikigai-maintainer-mcp`).

## COMMANDS
```bash
cd src/ikigai && poetry install
cd src/ikigai && poetry run pytest            # testpaths = ["tests"]
cd src/ikigai && poetry run pytest tests/test_canonical_scope.py -v
python run_mcp_server.py                       # from src/ikigai/
python -m src.ikigai.bin.ikigai_serve          # 127.0.0.1:8765
ruff check src/ikigai                          # uses src/ikigai/pyproject.toml [tool.ruff]
```
