# PROJECT KNOWLEDGE BASE

**Generated:** 2026-11-01 01:48 UTC
**Commit:** ac71dbf7
**Branch:** fix/ci-gates-green

## OVERVIEW

Algorithmic Life OS — a personal productivity orchestration system: 100% local, single-user, append-only at the vault layer.

Three layers — **INTERFACE** (CLI/TUI consumers: read `data/`, write feedback) → **AGENT** (Deep Agent "carro-chefe": reads `vault/`, applies strategics + planning, writes tasks to `data/`, observes planned-vs-actual; planner-only per ADR-013) → **DATA** (`vault/` markdown source of truth, `data/` runtime state, `vibe-ops/` cybernetic engine). Pydantic contracts in `src/contracts/` bind the layers.

Canonical flow: `vault` (NL planning) → Deep Agent → MCP Gateway → interfaces → manual feedback → agent observes the gap → updates `vault`.

Repo: github.com/matheusmendes720/ikigai — Board: github.com/users/matheusmendes720/projects/5

## STRUCTURE

```
{root}/
├── life/        # `life` meta-package: cli, centrals, handlers, plugins
├── src/         # contracts (canonical) + mesh + ikigai + agents
├── sys_ikigai/  # bare-namespace kernel: entities, gateway, vault, security
├── interfaces/  # cli (Typer) + studio (FastAPI) + tui/operator (Textual)
├── vibe-ops/    # cybernetic engine: Python pkg + Rust TUI + specs
├── vault/       # markdown notes (Obsidian-style, append-only)
├── data/        # runtime state: tasks.jsonl, *.db, boulder.json, review_queue/
├── tests/       # the entire pytest surface
├── tools/       # offline analysis + backtest/drift pipeline
├── scripts/     # operator tooling, smoke drivers, codemods
├── taskwarrior/ # legacy workspace — no longer the task store
├── strategics/  # strategy notes (append-only)
├── specs/       # milestone specs (M### dirs, e.g. M169-paperclip)
└── code-docs/   # prd / brd / adr / ard
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| User-facing CLI | `life/cli/` | `python -m life.cli`; see `life/AGENTS.md` |
| Canonical models | `src/contracts/` | Pydantic v2, the single source of truth |
| Cross-fork task view | `src/mesh/` | 3 adapters; write path via `data/review_queue/` |
| Deep Agent runtime | `src/ikigai/src/agents/v2/` | `ikigai_maintainer_v2` in `langgraph.json` |
| Paperclip (4 nested loops) | `src/ikigai/src/agents/paperclip/` | graph.py, policy.py, router.py, state.py, cli.py; ADR-036 `code-docs/adr/ADR-036-paperclip-four-nested-loops.md`; milestone specs `specs/M169-paperclip/` … `specs/M193-paperclip-stacks-comparison/` |
| Vault I/O | `sys_ikigai/vault/` | `vault_write` = sole vault writer (ADR-012) |
| MCP gateway | `sys_ikigai/gateway/` | stdlib JSON-RPC, HTTP+SSE front / stdio back |
| Cybernetic kernel | `vibe-ops/src/pipeline/contracts.py`, `vibe-ops/src/pipeline/policy_engine.py` | Target→Sensor→Adjuster orchestration; `PolicyEngine` = the Adjuster; `PolicyState` enum defined in `vibe-ops/src/schemas/pydantic_v2.py` (`vibe-ops/src/cybernetics/engine.py` is a knowledge tree, not the kernel) |
| Drift net | `src/ikigai/tests/test_drift_*.py` | append-only invariant guards |
| CI + PR-review bots | `.github/` | 5 workflow jobs, orchestrator scripts |
| Specs / ADRs | `code-docs/adr/`, `docs/superpowers/` | ADR-012/013/014/029/033/036 |

## CODE MAP

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `UEID` | Pydantic model | `src/contracts/common.py` | high | Canonical 4-part join key (ADR-014): `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (`<CLUSTER>:<ENTITY>:<HASH>:<SEQ>`; ADR-023 — the 4-part form wins over the 5-part legacy form) |
| `Task` / `TaskChange` | Pydantic model | `src/contracts/task.py`, `task_change.py` | high | Shared task + propagation payloads |
| `ForkAdapter` | Protocol | `src/mesh/adapters/__init__.py` | 3 impls | Fork boundary (Cli, Taskdog, Calendar) |
| `vault_write` | function | `sys_ikigai/vault/` | high | Only sanctioned vault write path |
| `UnifiedMCPGateway` | class | `sys_ikigai/gateway/` | high | HTTP+SSE front, stdio back |
| `IKIGAI_TOOLS` | constant | `src/ikigai/src/agents/tools.py` | drift-guarded | Exactly 12 planner tools (ADR-013) |
| `LifeConfig` | class | `life/cli/` | medium | Config defaults + plugin discovery |
| `BaseCentral` | class | `life/centrals/` | medium | task / knowledge / research dispatch |

## CONVENTIONS

- Python 3.11+, `from __future__ import annotations` at the top of every module.
- Canonical contracts: Pydantic v2 `frozen=True`, `extra="forbid"`, imported from `src/contracts/` only — never re-define `UEID`, `Task`, `TaskChange`.
- `src/` has **no `__init__.py`**: `from src.contracts.X` needs the repo root on `sys.path`; `from contracts.X` needs `src/` on it (`pytest.ini` sets `pythonpath = src src/ikigai/src`). Both spellings are live in production code.
- `vibe-ops/src` is a **separate import root** — flat sibling imports (`from pipeline.x import Y`); `vibe-ops/src/contracts/` is *not* the canonical `src/contracts/`.
- Two directories named `agents` (`src/agents/`, `src/ikigai/src/agents/`) merge into ONE logical package via `__path__` — keep them in sync.
- CLI: Typer sub-apps, `--json` everywhere feasible. Module docstrings carry a task/ADR tag (`M72`, `B3.4`, `ADR-029`) — keep it when editing.
- Tooling split (do not mix):

| Subpath | Build system | Notes |
|---|---|---|
| root, `src/mesh/`, `src/life_tatics/`, `src/agents/` | setuptools / plain Python | `src/` on `PYTHONPATH`; `src/mesh/` has no `pyproject.toml` |
| `src/contracts/` | **Hatchling** | own `pyproject.toml`, `uv.lock`, `.venv` |
| `src/ikigai/` | **Poetry** | own `poetry.lock` + `.venv`; launcher `ikigai.bat` |
| `interfaces/cli/` | **uv** | own `pyproject.toml`, `pytest.ini`, local ruff/mypy |
| `vibe-ops/` | **uv** + **Rust** (`ratatui`) | own `uv.lock`; TUI reads a hardcoded `../vibe_ops.db` |
| `archive/legacy-pav/src-operational/` | archived | do not revive |

- Ruff: the root `pyproject.toml` has **no** `[tool.ruff]` table. Real configs: `src/mesh/ruff.toml`, `src/contracts/pyproject.toml`, `src/ikigai/pyproject.toml` (line-length 100, py311).

## ANTI-PATTERNS (THIS PROJECT)

- **Deep Agent is the only writer to `vault/`** (ADR-012). Interfaces read vault only; user feedback goes to `data/feedback.jsonl`; fork writes go to `data/review_queue/`.
- **Append-only** — never delete or prune `vault/`, `vibe-ops/`, `strategics/`. vibe-ops additionally requires a stop → action plan → user-approval gate before restructuring *any* file (markdown included).
- **IKIGAI is planner-only** (ADR-013): no PAV math / policy / scoring tools in the agent layer; `IKIGAI_TOOLS` is exactly 12 and drift-guarded.
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
| `src/ikigai/tests/test_canonical_scope.py` | planner-only scope (forbidden imports/calls/classes/MCP wrappers/algorithm constants), `IKIGAI_TOOLS` count = 12, UEID canonical regex enforcement, `review_queue` append-only, `investigation_queue` invariants, skill manifest, memory schema, meta-plan write approval |
| `src/ikigai/tests/test_drift_invariants.py` | kill-switch key constants present and mirrored, no kill-switch constants in agent code, `vault_write` wrapper exposes the canonical API, drift invariant E (`vault_write` actor bypasses validator), legacy invariants a–d |
| `src/ikigai/tests/test_drift_extended_invariants.py` | wave-3+ invariants: `vault_write` sole writer, `review_queue` append-only, UEID regex canonical across modules, MCP bridge wrapped-tool count, LangGraph graph registry drift, milestone-spec frontmatter/status |
| `src/ikigai/tests/test_drift_detector.py`, `test_drift_state.py` | detector + state persistence |

- **Kill switch:** `sys_ikigai/security/kill_switch.py` + CLI `life kill-switch status|pause|resume|history` (registered in `interfaces/cli/kill_switch.py`); the TUI Kill Switch tab spawns `life kill-switch pause|resume`.
- **UEID drift is real** — the shipped `src/contracts/common.py::_UEID_PATTERN` is a *wider* triple-pattern (4-part short | 4-part long-UUID | 5-part legacy), so it does **not** match the canonical literal above; a byte-identical copy sits in `src/mesh/adapters/taskdog.py`, `{2,5}` in `src/ikigai/contracts/proposal.py`, `{2,10}` in `src/ikigai/src/chat/schema.py`; `sys_ikigai/types.py` keeps a legacy 5-part form and `vibe-ops/src/storage/ueid.py` builds a 3-part id. Never re-define `UEID` — extend the canonical one.
- **Mesh v1 scope:** `create`-only is enforced by `CliAdapter` and `SolverforgeCalendarAdapter`, but `TaskdogAdapter.apply_change` also dispatches `update`/`done`/`delete`/`tag_*`; the create-only docstring in `src/mesh/adapters/__init__.py` is stale.
- **Two `life` console scripts:** root `pyproject.toml` → `life.cli:_main_console`; `interfaces/cli/pyproject.toml` → `interfaces.cli.read_tasks:app`. Root `td` → `src.mesh.taskdog_cli:main` (works only because the repo root is on `sys.path`).
- **Windows quirks:** `sys.stdin.readline()` hangs on Windows pipes — use `sys.stdin.buffer.readline()` (the gateway stdio server must read binary); pytest-asyncio `PermissionError [WinError 5]` on stale temp dirs → `tests/conftest.py` redirects `tempfile.tempdir` to `data/pytest-tmp/`.
- **Known live defects:** every `life` call leaks `{"ok": false, ...}` JSON to stdout first (`interfaces.cli.taskdog_app.register_taskdog_app` echoes, then raises `typer.Exit`); `life task today` raises `NameError` (`TASK_BIN` undefined in `life/centrals/task.py`); knowledge/research centrals always fail (`leitura`/`notes`/`mindmaps`/`research` missing from `DEFAULT_SUBMODULES`); `sys_ikigai/propagation/markdown_db.py::MarkdownDB.read` raises `ImportError` (shims export `Dream`/`Task`, not `DreamEntity`/`TaskEntity`); three `.github/scripts` modules don't compile and three imports are untracked → a fresh clone fails `code-review-checks`.
- **`.gitignore` swallows every 4-letter root directory** (`/[a-zA-Z]{4}` matches `life`, `data`, `docs`, `logs`); only `src/` is negated. `git add -f` new files under `life/`.
- **Docs that drifted:** `src/ikigai/README.md` (`poetry run ikigai` does not exist), `src/ikigai/MCP_GATEWAY.md` (real script: `ikigai-maintainer-mcp`), `src/ikigai/SPEC.md` D10 ("tri-key" vs 5 components), `interfaces/tui/operator/README.md` (5 tabs, not 3).
- **Version pins that bite:** `typer >= 0.21` vendors Click as `typer._click` (so `typer.Exit` is not `click.exceptions.Exit`); `mcp` is pinned `<2` (2.x dropped `mcp.server.fastmcp`); `fastapi`/`uvicorn` are optional — `interfaces/studio` exits if they are missing.
- **Taskwarrior is no longer the task store** (taskdog-server on `127.0.0.1:8000` replaced it), yet `taskwarrior/scripts` is still the `task_scripts` path used by `life task daily-review|weekly-review|metrics`.
- **Makefile is partly broken:** `make test` references removed `langgraph_tests/` and `src/operational/` — use `pytest tests/ -v`. Port-2024 LangGraph dev runs via machine-locked `scripts/langgraph-dev.bat` (same for `scripts/ruvocal-start.bat`); `scripts/td_shim_build/__main__.py` hardcodes the author's absolute repo path. The 12 `.sh`/`.bat` suites under `tests/` aren't pytest-collected (`set -euo pipefail`, sandboxed in `mktemp -d`).
- Commit conventions: branch from `main`, never push to `main`; conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`). No secrets in the repo — `.env` is gitignored, `.env.example` is the template.
