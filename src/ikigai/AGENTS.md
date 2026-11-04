# AGENTS.md — `src/ikigai/`

**Canonical scope (ADR-037, 2026-11-01).** This is the Poetry sub-project that used to host the whole agent runtime. The PC-only runtime (LangChain/LangGraph harness, local chat REPL, stdio MCP fork servers, paperclip bridge, OpenTelemetry stack) is **not published** anymore. What stays is the strategic-prose loader, the meta-planner contracts, the soul profiles and the drift net.

## OVERVIEW
A standalone Poetry project (`name = "ikigai"`, `version = "0.1.0"`, `python = "^3.11"`) with its own `.venv`, its own `poetry.lock` and its own `pyproject.toml`. It does **not** inherit the root build config. The canonical MCP transport lives outside this project, at `src/transport/mcp_server.py` (repo root, ADR-011).

## STRUCTURE
```
src/ikigai/
├── pyproject.toml       # Poetry; packages + deps + pytest + ruff + mypy config
├── poetry.lock          # Poetry lockfile (source of truth for this project)
├── uv.lock              # ALSO present — see ANTI-PATTERNS
├── src/                 # the ONLY installable package left: strategics/
├── scripts/             # 3 standalone scripts (migrate_plan_entities + 2 repro scripts)
├── souls/               # 3 soul profiles (planner/critic/stoic) + loader
├── tools/               # vault_taskdog_sync.py, views.py (dev CLIs)
├── contracts/           # proposal.py — Meta-Planner contracts (NOT src/contracts)
├── tests/               # 67 pytest files incl. the whole drift net
├── data/matheus/        # per-persona runtime data (dreams, objectives, projects)
├── docs/                # HISTORICAL — describes the retired server runtime
├── SPEC.md / CHANGELOG.md / README.md
└── vault/               # local vault tree (untracked)
```

## WHERE TO LOOK
| Task | Location |
|---|---|
| Strategic prose loader | `src/strategics/loader.py` — read-only |
| Canonical MCP surface (6 tools) | `src/transport/mcp_server.py` (repo root, ADR-011) |
| Data-layer contracts | `src/contracts/` (repo root — canonical Pydantic v2) |
| Planner layer (memory, reflection) | the agent is EXTERNAL (ADR-037 D7) — the harness is `pi`, and it is not in this repository |
| Meta-Planner contracts | `contracts/proposal.py` (11 Pydantic models) |
| Drift net | `tests/test_canonical_scope.py`, `tests/test_drift_invariants.py`, `tests/test_gitignore_root_scope.py` |
| Transport tests | `tests/transport/test_mcp_tools.py` |

## CONVENTIONS
- **The Poetry project installs top-level names, not `ikigai.*`.** `packages` ships only `strategics` (from `src/`). The `sys_ikigai` entry was removed on 2026-11-02: shipping the retired runtime from the repo root was the coupling that kept 91 legacy files on the branch (ADR-037). Runtime code therefore writes `from strategics.loader import ...` — there is no `ikigai.*` prefix.
- **No console scripts.** `ikigai-maintainer-mcp`, `ikigai-deep-agent`, `paperclip` and `paperclipai-bridge` were removed with the harness — they only started the PC-local server. The cloud harness is specified in `specs/harness/`.
- **The MCP SDK stays a declared dependency** (`mcp = "^1.1"`) because this package's own suite (`tests/transport/`) exercises the canonical transport from this venv.
- **Pytest config lives in this project's `pyproject.toml`**: `testpaths = ["tests"]`, `pythonpath = ["src", "../.."]`, `addopts = "-v --tb=short"`. Root `pytest.ini` is a separate, root-only config.
- **`souls/loader.py` exports exactly `load_soul` and `known_profiles`.** Profile names are validated before any filesystem access; path traversal is rejected.
- **`contracts/proposal.py` is a separate contract family from `src/contracts/`.** It defines its own `Proposal` with `approval_state`, its own `IntentClassification`, and its own UEID regex (`{2,5}` 4-part) — it is *not* the canonical `TaskChange`.
- **`docs/` and `scripts/repro_*.py` are historical.** They describe the retired server runtime (observability, the local HTTP server); read them as an archive, not as a spec.

## ANTI-PATTERNS
- **Never re-add an agent harness here.** No `src/agents`, `src/chat`, `src/mcp_server`, `src/plugins`, `src/observability` — the canonical transport is `src/transport/mcp_server.py` and a drift test fails if any of those paths is tracked again.
- **Never move dev tools out of `[tool.poetry.group.dev.dependencies]`.** A previous move to a PEP-735 `[dependency-groups]` table made Poetry 2.x resolve the group from there only, silently dropping `pytest`/`ruff`/`mypy` from `poetry.lock` and leaving CI without a runner. The `pyproject.toml` comment records this — do not undo it.
- **Never commit `.env`.** It is gitignored; the root `.env.example` is the template, and it instructs rotating a previously leaked key before use.
- **Never import `sys_ikigai.core.scoring`, `ikigai.core.heuristics`, or `cybernetics.daily_loop`** from this package (ADR-013 planner-only).
- **`uv.lock` and `poetry.lock` both exist.** Poetry is the source of truth for this project; the stray `uv.lock` is a leftover — do not add uv-specific config to `pyproject.toml`.
- **Never let the retired runtime back into the wheel.** `sys_ikigai` is not installed from the repo root any more (`packages` ships only `strategics`), and it is not vendored under `src/ikigai/`. The frontmatter shim it used to hold now lives at `src/strategics/frontmatter_compat.py` — self-contained, PyYAML only.

## COMMANDS
```bash
cd src/ikigai && poetry install
cd src/ikigai && poetry run pytest            # testpaths = ["tests"]
cd src/ikigai && poetry run pytest tests/test_canonical_scope.py -v
ruff check src/ikigai                          # uses src/ikigai/pyproject.toml [tool.ruff]
python -m pytest src/ikigai/tests -q           # from the repo root
```
