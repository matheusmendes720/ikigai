# AGENTS.md

Algorithmic Life OS — a Python productivity orchestration CLI hub (daily/weekly handlers + task/knowledge/research centrals + plugin system). Personal, single-user, 100% local, append-only at the vault layer.

## Setup commands

- Python: 3.11+ (see `.python-version`)
- Editable install: `pip install -e ".[dev,mesh]"` (root)
- `src/ikigai/` (Poetry): `cd src/ikigai && poetry install`
- `vibe-ops/` (uv): `cd vibe-ops && uv sync`
- Run the CLI: `python -m life.cli --help` (or `life` after editable install)
- LangGraph dev: `make install && make dev` (port 2024)

## Build / Test / Lint

- Build: setuptools auto-discovery via `pyproject.toml` (`packages = ["life", ...]`)
- Test: `pytest tests/ -v` (root; Phase 3 mesh + contracts + integration). Submodule suites: `cd src/ikigai && poetry run pytest`, `cd vibe-ops && uv run pytest`
- Phase 3 v1 e2e driver: `bash scripts/smoke/phase3_v1.sh` (or `scripts\smoke\phase3_v1.bat` on Windows)
- Lint: `ruff check .` (`[tool.ruff]` in `pyproject.toml`)
- Typecheck: `mypy .` (`mypy.ini` at root, `mypy_path = src .. ../..`)
- Pre-commit: `pre-commit run --all-files` (`.pre-commit-config.yaml` at root)
- Console scripts declared in root `pyproject.toml`: `life` → `life.cli:_main_console`, `td` → `src.mesh.taskdog_cli:main`

## Project layout

- `life/` — meta-package (`cli/`, `centrals/`, `handlers/`, `plugins/`, `plugins/builtin/`)
- `src/` — three independent Python subpackages: `ikigai/` (Poetry, MCP/deep-agent), `mesh/` (uv, Phase 3 data mesh), `contracts/` (canonical Pydantic v2), `life_tatics/`, `planner/`
- `sys_ikigai/` — bare-namespace entities, gateway, state machines, vault, security, adapters
- `vibe-ops/` — cybernetic engine (Target→Sensor→Adjuster loop, SQLite, ChromaDB)
- `interfaces/{cli,tui}/` — consumer surfaces
- `vault/` — primary notes layer (Obsidian-style markdown, append-only)
- `data/` — runtime state (`vibe_ops.db`, `vibe_mesh.db`, `boulder.json`, `chroma_db/`, `review_queue/`)
- `scripts/smoke/` — Phase 3 v1 driver + other smoke tests
- `code-docs/{prd,brd,adr,ard}/`, `docs/`, `diagrams/`, `specs/` — requirements + architecture
- `archive/legacy-pav/` — superseded PAV kernel (do not edit)
- `strategics/`, `taskwarrior/`, `tools/`, `examples/`, `reports/`, `notes/`, `openwiki/`, `logs/` — supporting

## Tooling split (do not mix)

| Subpath | Build system | Notes |
|---|---|---|
| root + `src/contracts/`, `src/mesh/`, `src/life_tatics/` | setuptools / plain Python | `src/` on `PYTHONPATH` (set by `pytest.ini`) |
| `src/ikigai/` | Poetry | has its own venv; launcher `ikigai.bat` |
| `vibe-ops/` | uv | owns its own lockfile |
| `archive/legacy-pav/src-operational/` | archived | do not revive |

## Code style

- Python 3.11+, `from __future__ import annotations` at top of every module
- Pydantic v2 strict: `frozen=True`, `extra="forbid"` for all shared contracts in `src/contracts/`
- Single source of truth for shared models: `src/contracts/{common,task,task_change,planning,metrics}.py` — never re-define `UEID`, `Task`, `TaskChange`, etc.
- CLI: Typer sub-apps, `--json` everywhere feasible
- UEID format: 4-part `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per `code-docs/adr/ADR-014-ueid-canonical-format.md`

## Testing instructions

- Unit + integration: `pytest tests/ -v` from repo root (120 root tests, Phase 3 scope)
- Submodule suites: `cd src/ikigai && poetry run pytest`, `cd vibe-ops && uv run pytest`
- Drift net: `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` — invariant tests are append-only, never delete
- E2E: `bash scripts/smoke/phase3_v1.sh` (isolated temp dir, does not touch real `data/`)
- Add a test for every new behavior in the same package as the code

## Architectural rules (load-bearing)

- **Append-only:** `vault/`, `vibe-ops/`, `strategics/` — never delete or prune. Refactor protocol: stop → propose Action Plan → wait for "go" → only then mutate
- **IKIGAI is planner-only** per ADR-013 — no PAV math/policy/scoring tools in agent layer (`IKIGAI_TOOLS` count guarded by drift test)
- **Deep Agent is the sole writer to `vault/`** (per ADR-012) — interfaces read only
- **Phase 3 mesh v1** ships `create` action only; `update`/`delete`/`done` are out of scope
- **Vault dual-tree identity:** `from src.contracts.X` vs `from sys_ikigai.X` resolve through `<repo>/src` and `<repo>/sys_ikigai` respectively; both work via `tests/conftest.py`. When monkeypatching in tests, patch BOTH
- **No secrets in repo** — `.env` is gitignored; `.env.example` is the template

## PR & commit conventions

- Branch from `main`; never push to it directly
- Conventional commits: `feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`
- Drift tests are append-only — when crossing an invariant boundary, add a test in `test_drift_extended_invariants.py` instead of weakening an existing one

## Pitfalls

- `make test` is partially broken — it references removed `langgraph_tests/` and `src/operational/`. Use `pytest tests/ -v` directly
- Zero-byte root artifacts (`0`, `14`, `agent('Execute`, etc.) are stray bash-redirect typos — do not edit, leave gitignored
- `strategics/planning-with-files` submodule is intentionally dirty (vendored third-party); do not commit its contents
- Root `CLAUDE.md` and archived `archive/legacy-pav/src-operational/CLAUDE.md` describe overlapping scopes; verify against `git log -- <path>` for ground truth

## Where to start

| Task | Start here |
|------|-----------|
| Using the mesh | `python -m life.cli mesh show <ueid>` |
| Adding CLI commands | `life/cli/cli.py` + `life/centrals/` |
| Editing the agent | `src/ikigai/src/agents/` (v2 graph at `v2/`) |
| Touching contracts | `src/contracts/` (Pydantic v2 strict) |
| Drift / invariant work | `tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` |