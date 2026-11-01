# PROJECT KNOWLEDGE BASE

**Generated:** 2026-11-01 01:48 UTC
**Commit:** ac71dbf7
**Branch:** fix/ci-gates-green

## OVERVIEW

Algorithmic Life OS — a personal productivity orchestration system: 100% local, single-user, append-only at the vault layer.

Three layers — **INTERFACE** (CLI consumers: read `data/`, write feedback) → **AGENT** (planner-only per ADR-013: reads `vault/`, applies strategics + planning, writes tasks to `data/`, observes planned-vs-actual) → **DATA** (`vault/` markdown source of truth, `data/` runtime state, `vibe-ops/` cybernetic engine). Pydantic contracts in `src/contracts/` bind the layers.

**Canonical scope (ADR-037, 2026-11-01): the repository is serverless / cloud-native.** The PC-only runtime is NOT published: no local chat REPL, no stdio MCP fork servers, no Textual TUI, no LangChain/LangGraph harness, no tracing stack. What a client calls is the **MCP surface** (`src/transport/mcp_server.py`) over the **data layer** (`src/services/` → `src/contracts/`).

Repo: github.com/matheusmendes720/ikigai — Board: github.com/users/matheusmendes720/projects/5

## STRUCTURE

```
{root}/
├── life/        # `life` meta-package: cli, centrals, handlers, plugins
├── src/         # contracts (canonical) + mesh + services + transport + agents + ikigai
├── sys_ikigai/  # bare-namespace kernel: entities, gateway, vault, security
├── interfaces/  # cli (Typer) — the only published consumer surface
├── vibe-ops/    # cybernetic engine: Python package + specs
├── vault/       # markdown notes (Obsidian-style, append-only)
├── data/        # runtime state: tasks.jsonl, *.db, boulder.json, review_queue/
├── tests/       # the entire pytest surface
├── tools/       # offline analysis + backtest/drift pipeline
├── scripts/     # operator tooling, smoke drivers, codemods
├── taskwarrior/ # legacy workspace — no longer the task store
├── strategics/  # strategy notes (append-only)
├── specs/       # milestone specs (M### dirs)
└── code-docs/   # prd / brd / adr / ard
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| User-facing CLI | `life/cli/` | `python -m life.cli`; see the root AGENTS.md |
| Canonical models | `src/contracts/` | Pydantic v2, the single source of truth |
| Cross-fork task view | `src/mesh/` | cloud-safe adapters (`cli`, `taskdog`); write path via `data/review_queue/` |
| MCP tool surface | `src/transport/mcp_server.py` | six tools over the data layer; transport via `IKIGAI_MCP_TRANSPORT` (ADR-011) |
| Domain services | `src/services/` | validation, versioning, idempotency — the only layer a client reaches |
| Vault I/O | `sys_ikigai/vault/` | `vault_write` = sole vault writer (ADR-012) |
| Local JSON-RPC gateway | `sys_ikigai/gateway/` | stdlib JSON-RPC; local/legacy path, NOT the client surface |
| Cybernetic kernel | `vibe-ops/src/pipeline/contracts.py`, `vibe-ops/src/pipeline/policy_engine.py` | Target→Sensor→Adjuster orchestration; `PolicyEngine` = the Adjuster; `PolicyState` enum defined in `vibe-ops/src/schemas/pydantic_v2.py` (`vibe-ops/src/cybernetics/engine.py` is a knowledge tree, not the kernel) |
| Drift net | `src/ikigai/tests/test_drift_*.py` | append-only invariant guards |
| CI + PR-review bots | `.github/` | 5 workflow jobs, orchestrator scripts |
| Specs / ADRs | `code-docs/adr/`, `docs/superpowers/` | ADR-012/013/014/029/033/036 |

## CODE MAP

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `UEID` | Pydantic model | `src/contracts/common.py` | high | Canonical 4-part join key (ADR-014): `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (`<CLUSTER>:<ENTITY>:<HASH>:<SEQ>`; ADR-023 — the 4-part form wins over the 5-part legacy form) |
| `Task` / `TaskChange` | Pydantic model | `src/contracts/task.py`, `task_change.py` | high | Shared task + propagation payloads |
| `ForkAdapter` | Protocol | `src/mesh/adapters/__init__.py` | 2 impls | Fork boundary (Cli, Taskdog) |
| `vault_write` | function | `sys_ikigai/vault/` | high | Only sanctioned vault write path |
| `UnifiedMCPGateway` | class | `sys_ikigai/gateway/` | medium | Local stdlib JSON-RPC gateway; the retired fork servers are gone |
| `LifeConfig` | class | `life/cli/` | medium | Config defaults + plugin discovery |
| `BaseCentral` | class | `life/centrals/` | medium | task / knowledge / research dispatch |

## CONVENTIONS

- Python 3.11+, `from __future__ import annotations` at the top of every module.
- Canonical contracts: Pydantic v2 `frozen=True`, `extra="forbid"`, imported from `src/contracts/` only — never re-define `UEID`, `Task`, `TaskChange`.
- `src/` has **no `__init__.py`**: `from src.contracts.X` needs the repo root on `sys.path`; `from contracts.X` needs `src/` on it (`pytest.ini` sets `pythonpath = src src/ikigai/src`). Both spellings are live in production code.
- `vibe-ops/src` is a **separate import root** — flat sibling imports (`from pipeline.x import Y`); `vibe-ops/src/contracts/` is *not* the canonical `src/contracts/`.
- **One `agents` package.** `src/agents/` (planner: `memory/`, `reflection/`) is the only one in the tree; the IKIGAI-internal harness directory that used to merge into it is retired (ADR-037).
- CLI: Typer sub-apps, `--json` everywhere feasible. Module docstrings carry a task/ADR tag (`M72`, `B3.4`, `ADR-029`) — keep it when editing.
- Tooling split (do not mix):

| Subpath | Build system | Notes |
|---|---|---|
| root, `src/mesh/`, `src/life_tatics/`, `src/agents/` | setuptools / plain Python | `src/` on `PYTHONPATH`; `src/mesh/` has no `pyproject.toml` |
| `src/contracts/` | **Hatchling** | own `pyproject.toml`, `uv.lock`, `.venv` |
| `src/ikigai/` | **Poetry** | own `poetry.lock` + `.venv`; drift net lives in `src/ikigai/tests/` |
| `interfaces/cli/` | **uv** | own `pyproject.toml`, `pytest.ini`, local ruff/mypy |
| `vibe-ops/` | **uv** | own `uv.lock`; the Rust TUI is not published |
| `archive/legacy-pav/src-operational/` | archived | do not revive |

- Ruff: the root `pyproject.toml` has **no** `[tool.ruff]` table. Real configs: `src/mesh/ruff.toml`, `src/contracts/pyproject.toml`, `src/ikigai/pyproject.toml` (line-length 100, py311).

## ANTI-PATTERNS (THIS PROJECT)

- **Deep Agent is the only writer to `vault/`** (ADR-012). Interfaces read vault only; user feedback goes to `data/feedback.jsonl`; fork writes go to `data/review_queue/`.
- **Append-only** — never delete or prune `vault/`, `vibe-ops/`, `strategics/`. vibe-ops additionally requires a stop → action plan → user-approval gate before restructuring *any* file (markdown included).
- **IKIGAI is planner-only** (ADR-013): no PAV math / policy / scoring tools in the agent layer.
- **Zero LLM in the pipeline** — daily/weekly pipelines are pure arithmetic. **Fully local** — SQLite + filesystem only, zero cloud deps.
- **Drift tests are append-only**: never delete or weaken one; add to `test_drift_extended_invariants.py` instead.
- **Refactor protocol:** touching `vault/`, `vibe-ops/` or `strategics/` → stop → propose an Action Plan → wait for an explicit "go" → verify every pre-existing string survives.
- **Do not write new algorithm code** while IKIGAI is paused for algorithm decisions (M01/N01/A02/A06, vector weights). The pause covers algorithm decisions only — agent/harness plumbing and Drift net work are allowed.
- **`strategics/planning-with-files/` is a vendored third-party fork** with its own `.git/`, untracked here (`.gitignore` line 480 `/strategics/planning-with-files/`, M41 unlink) — never commit its contents.
- **~100 zero-byte files sit in the repo root** (`0`, `14`, `agent('Execute`, `console.log(i`, `dict[str`, …) — stray shell-redirect leftovers. They are gitignored: leave them alone, no edits, no deletes.

## UNIQUE STYLES

- Planning Note channel (human → agent): template `vault/ikigai/templates/sonho-log.md` (one section, `## Mudança`), manual trigger after any planning delta, 1–3 bullets, written to `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/YYYY-MM-DD.md`.
- Repo vocabulary is PT-BR in `vault/`, `taskwarrior/` and `vibe-ops/`; code, docs and commits are EN.
- `vibe-ops/src/models/` and `vibe-ops/src/schemas/` are deliberately permissive (`extra="allow"`, mutable) — the inverse of the repo-wide strict contracts. Intentional, not a bug.
- Temporal model: `src/life_tatics/time-lenghts_reviews.md` is canonical (`rho = 11/15`, `WAVE = 15 D = 11 W`, `CYCLE = 45 D = 33 W`, `PHASE = 180 D = 132 W`); `src/planner/time-lenghts_reviews.md` is the earlier variant. When a temporal number is disputed, the `life_tatics` copy wins.

## COMMANDS

```bash
pip install -e ".[dev,mesh]"                             # root editable install
pytest tests/ -v                                         # the entire pytest surface
cd src/ikigai && poetry install && poetry run pytest     # ikigai suite (drift net)
cd src/contracts && uv sync && uv run pytest             # contracts suite
cd vibe-ops && uv sync && uv run pytest                  # vibe-ops suite
bash scripts/smoke/phase3_v1.sh                          # Phase 3 e2e (isolated temp dir)
python -m life.cli --help                                # CLI (or `life` after install)
mypy .                                                   # mypy.ini at root
ruff check .                                             # per-project only: src/mesh, src/contracts, src/ikigai
pre-commit run --all-files
```

## NOTES

- **Import identity:** `from src.contracts.X` and `from sys_ikigai.X` are *two distinct module objects* — monkeypatching must patch BOTH. `tests/conftest.py` puts the repo root on `sys.path` and pre-registers legacy `ikigai.*` aliases in `sys.modules`.
- **Drift net** — CI fails if a load-bearing invariant is weakened without a version bump:

| File | Purpose |
|---|---|
| `src/ikigai/tests/test_canonical_scope.py` | the retired runtime stays unpublished (ADR-037), canonical surface stays published, contracts are the single source of truth, mesh exposes only the cloud-safe adapters, UEID canonical regex, planner-only + LLM-free guards |
| `src/ikigai/tests/test_drift_invariants.py` | kill-switch key constants present and mirrored, no kill-switch constants in agent code, `vault_write` wrapper exposes the canonical API, drift invariant E (`vault_write` actor bypasses validator), legacy invariants a–d |
| `src/ikigai/tests/test_drift_detector.py`, `test_drift_state.py` | detector + state persistence |

- **Kill switch:** `sys_ikigai/security/kill_switch.py` + CLI `life kill-switch status|pause|resume|history` (registered in `interfaces/cli/kill_switch.py`). The tuning constants live in `sys_ikigai/security/algorithm_constants.json` (ADR-019 R1) — never in Python.
- **UEID drift is real** — the shipped `src/contracts/common.py::_UEID_PATTERN` is a *wider* triple-pattern (4-part short | 4-part long-UUID | 5-part legacy), so it does **not** match the canonical literal above; a byte-identical copy sits in `src/mesh/adapters/taskdog.py`, `{2,5}` in `src/ikigai/contracts/proposal.py`; `sys_ikigai/types.py` keeps a legacy 5-part form and `vibe-ops/src/storage/ueid.py` builds a 3-part id. Never re-define `UEID` — extend the canonical one.
- **Mesh v1 scope:** `create`-only is enforced by the cloud-safe adapters (`CliAdapter`, `TaskdogAdapter`); the retired calendar fork adapter is gone with the PC-only scope.
- **Two `life` console scripts:** root `pyproject.toml` → `life.cli:_main_console`; `interfaces/cli/pyproject.toml` → `interfaces.cli.read_tasks:app`. Root `td` → `src.mesh.taskdog_cli:main` (works only because the repo root is on `sys.path`).
- **Windows quirks:** `sys.stdin.readline()` hangs on Windows pipes — use `sys.stdin.buffer.readline()` (a stdio MCP server must read binary); pytest-asyncio `PermissionError [WinError 5]` on stale temp dirs → `tests/conftest.py` redirects `tempfile.tempdir` to `data/pytest-tmp/`.
- **Known live defects:** `life task today` raises `NameError` (`TASK_BIN` is undefined in `life/centrals/task.py`); knowledge/research centrals always fail (`leitura`/`notes`/`mindmaps`/`research` missing from `DEFAULT_SUBMODULES`). Fixed in the ADR-037 wave: the `{"ok": false, ...}` stdout leak (the PC-only taskdog sub-app was removed) and the `.github/scripts` breakage (all ten modules compile; the four `code_review` modules are tracked).
- **`.gitignore` swallows every 4-letter root directory** (`/[a-zA-Z]{4}` matches `life`, `data`, `docs`, `logs`); only `src/` is negated. `git add -f` new files under `life/`.
- **Docs that drifted:** `src/ikigai/README.md` (`poetry run ikigai` does not exist), `src/ikigai/MCP_GATEWAY.md` (describes the retired PC-local gateway; the live surface is `src/transport/mcp_server.py`), `src/ikigai/SPEC.md` D10 ("tri-key" vs 5 components).
- **Version pins that bite:** `typer >= 0.21` vendors Click as `typer._click` (so `typer.Exit` is not `click.exceptions.Exit`); `mcp` is pinned `<2` (2.x dropped `mcp.server.fastmcp`).
- **Taskwarrior is no longer the task store** (taskdog-server on `127.0.0.1:8000` replaced it), yet `taskwarrior/scripts` is still the `task_scripts` path used by `life task daily-review|weekly-review|metrics`.
- **There is no `Makefile`** (removed with the PC-only scope, ADR-037): run `pytest tests/ -v` from the repo root. `scripts/ruvocal-start.bat` and `scripts/td_shim_build/__main__.py` hardcode the author's absolute repo path. The 12 `.sh`/`.bat` suites under `tests/` aren't pytest-collected (`set -euo pipefail`, sandboxed in `mktemp -d`).
- Commit conventions: branch from `main`, never push to `main`; conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`). No secrets in the repo — `.env` is gitignored, `.env.example` is the template.
