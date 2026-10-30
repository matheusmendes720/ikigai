# PROJECT KNOWLEDGE BASE

**Generated:** 2026-10-30T13:39:29Z
**Commit:** a264877
**Branch:** master

## OVERVIEW

Algorithmic Life OS — a personal productivity orchestration system: 100% local, single-user, append-only at the vault layer, no cloud dependencies (SQLite + filesystem only).

Three layers: **INTERFACE** (CLI v2, FastAPI Studio, Textual 5-tab TUI) → **AGENT** (Deep Agent "carro-chefe", planner-only per ADR-013) → **DATA** (`vault/` markdown source of truth, `data/` runtime state, `vibe-ops/` cybernetic engine). Daily/weekly pipelines are pure arithmetic — zero LLM in the pipeline.

Canonical flow: `vault` (NL planning) → Deep Agent → MCP Gateway → interfaces → manual feedback → Deep Agent observes the gap → updates `vault`.

Repo: `github.com/matheusmendes720/ikigai` · Board: `github.com/users/matheusmendes720/projects/5`

**Current mode — data-first.** IKIGAI is paused for *new algorithm decisions* (M01/N01/A02/A06, IKIGAI vector weights): write no new algorithm code until 5+ SONHO logs land in `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/`. The "pausado" directive covers **algorithm decisions only** — agent/harness plumbing and Drift net work are NOT paused.

**Planning Note channel (human → agent).** Template `vault/ikigai/templates/sonho-log.md` (1 section: `## Mudança`); manual trigger after any planning delta; event-driven, not daily; 1–3 bullets per note, <2 min; lands in `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/YYYY-MM-DD.md`.

## STRUCTURE

```
{root}/
├── src/ikigai/            # Poetry: MCP gateway, v2 agent, Paperclip, drift net
├── src/mesh/              # Phase 3 cross-fork mesh (plain Python; needs src/ on PYTHONPATH)
├── src/contracts/         # canonical Pydantic v2 contracts (own hatchling dist + uv.lock)
├── src/agents/            # planner agent layer; merged with src/ikigai/src/agents
├── src/tuiboard/ src/solverforge_calendar/  # kanban + calendar fork MCP servers
├── src/planner/ src/life_tatics/            # planner core / stub (not wired to a CLI)
├── sys_ikigai/            # bare-namespace kernel: entities, vault, security, gateway, FSMs
├── vibe-ops/              # uv-only cybernetic engine (Target→Sensor→Adjuster, SQLite, ChromaDB)
├── interfaces/            # cli/ (uv, standalone), studio/ (FastAPI), tui/operator/ (Textual)
├── life/                  # meta-package: cli→centrals→handlers→plugins (git-ignored!)
├── tools/                 # standalone CLI tooling; backtest/ holds the real vault-write engine
├── tests/                 # root suite; dual-import bootstrap in conftest.py
├── vault/                 # primary notes layer (Obsidian-style markdown, append-only)
├── data/                  # runtime state: vibe_ops.db, vibe_mesh.db, boulder.json, chroma_db/, review_queue/
├── scripts/ .github/ taskwarrior/  # dev entry points, CI/automation, Taskwarrior config
├── code-docs/ docs/ diagrams/ specs/ examples/ reports/ notes/ openwiki/ logs/ strategics/  # PRD/BRD/ADR/ARD, docs, supporting
└── archive/legacy-pav/    # superseded PAV kernel — do not edit
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Mesh read path | `life mesh show <ueid>` → `interfaces/cli/` | joins CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter |
| Building interfaces | `interfaces/cli/v2.py`, `interfaces/tui/operator/` | `interfaces/cli` is a standalone uv project with its own ruff/mypy/pytest config |
| Deep Agent dev | `src/ikigai/src/agents/v2/` | graph `ikigai_maintainer_v2` in root `langgraph.json` |
| Canonical contracts | `src/contracts/` + `src/mesh/` | single source of truth for `UEID`/`Task`/`TaskChange`; 91 import sites |
| Vault writes | `sys_ikigai/vault/vault_write.py` behind `sys_ikigai/security/vault_write_wrapper.py` | outside the agent: `tools/backtest/vault_propagation.py` |
| MCP surface | `src/ikigai/src/mcp_server/server.py` | 8 `ikigai_*` stub tools + `FastMCP("taskdog")` with 26 `taskdog_*` tools |
| Kill switch | `sys_ikigai/security/kill_switch.py` | env → `vault/.kill_switch.md` → `data/.kill_switch` |
| Drift net | `src/ikigai/tests/test_canonical_scope.py`, `test_drift_invariants.py`, `test_drift_extended_invariants.py` | append-only — add, never weaken |
| Paperclip | `src/ikigai/src/agents/paperclip/` + `specs/M169-paperclip/...M193` + ADR-036 | 10-node graph with cost/risk gates |
| Understanding the system | `docs/ARCHITECTURE_INDEX.md`, `code-docs/adr/` | canonical ADRs live in `code-docs/adr/` |

## CODE MAP

Repo-wide reference counts, measured. Subdirectory files carry the detail; this table is the hot core only.

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `vault_read` | function | `sys_ikigai/vault/` | 147 | vault read mirror |
| `IKIGAiRecord` | model | `sys_ikigai/entities/` | 137 | polymorphic record root (`extra="allow"`, not frozen) |
| `audit_drift` | function | `tools/backtest/vault_propagation.py` | 106 | vault drift audit — the most-referenced symbol in the tree |
| `StdioAdapter` / `EventLog` / `UnifiedMCPGateway` | class | `sys_ikigai/gateway/` | 69 / 54 | hand-rolled JSON-RPC 2.0 stdio transport, append-only event log, pure-stdlib HTTP+SSE gateway (`POST /call`, `GET /health`, `GET /events`) |
| `StateMachine` | class | `sys_ikigai/state_machines/` | 61 | phase transitions |
| `SQLiteAdapter` | class | `sys_ikigai/propagation/` | 54 | append-only SQLite mirror (delete/update triggers abort) |
| `BidirectionalSync` | class | `vibe-ops/src/middleware/` | 52 | vault↔code sync engine (9 files) |
| `vault_write_wrapper` | function | `sys_ikigai/security/` | 28 | ADR-029 8-step enforcement ladder |

## CONVENTIONS

- Python 3.11+ (see `.python-version`); `from __future__ import annotations` at the top of every module (missing from several `life/` and `interfaces/` `__init__.py`).
- Pydantic v2 strict `frozen=True, extra="forbid"` in `src/contracts/` — deliberately **inverted** in `vibe-ops/src/models/` (5 modules `extra="allow"`, none forbid) and in the `sys_ikigai/entities/` polymorphic roots, so user-authored frontmatter survives validation. `TimestampMixin` is the one contract model that is not frozen.
- Shared models live in `src/contracts/{common,task,task_change,planning,metrics}.py` — never re-define `UEID`, `Task`, `TaskChange`. Canonical UEID is 4-part (`src/contracts/common.py`, ADR-014). `src/ikigai/contracts/` is only the Meta-Planner `Proposal` vocabulary, NOT the canonical package.
- Deprecated shims — do not extend: `sys_ikigai/entities/plan/`, `sys_ikigai/types.py` (legacy 5-part UEID), `sys_ikigai/adapters/sqlite_bridge.py`, `sys_ikigai/gateway/downstream.py`.
- CLI: Typer sub-apps, `--json` everywhere feasible. `tools/vault/` exit codes: 0 success, 1 refused/no match, 2 usage/runtime error; the Bash loop tools use exit 2 as a cost/streak threshold break.
- Windows-first runtime: atomic write = temp file in the same directory + `os.replace()` (never `Path.rename()`); `msvcrt`/`fcntl` dual lock; WAL journal mode.
- Add a test for every new behavior in the same package as the code. No secrets in the repo — `.env` is gitignored, `.env.example` is the template.

## ANTI-PATTERNS (THIS PROJECT)

- **Never** write to `vault/`, `vibe-ops/`, `strategics/` outside the sanctioned path. Append-only — never delete or prune. Refactor protocol: stop → propose an Action Plan → wait for an explicit "go" → verify every pre-existing string survives.
- **Never** add PAV/IKIGAI scoring math to the agent layer or `vibe-ops/` (ADR-013): `compute_score`, `compute_qhe`, `compute_meta_vector`, `IkigaiScorer`, `cybernetics.daily_loop` imports fail CI.
- **Never** let interfaces write the vault — they read only. Feedback → `data/feedback.jsonl`; fork writes → `data/review_queue/`.
- **Never** delete or weaken a drift test. Crossing an invariant boundary means adding a test to `test_drift_extended_invariants.py`.
- **Never** import `vibe_ops.*` — the dotted path cannot exist (hyphenated directory); `vibe-ops/src` goes on `sys.path` and modules import top-level.
- **Never** use `tmp_path_factory.mktemp()` (Windows `PermissionError [WinError 5]`) — use `tmp_path`.
- **Never** mutate the user's live Taskwarrior config; `taskwarrior/config/taskrc.template` is copied to `~/.taskrc`.
- **Never** write into `data/` or `src/ikigai/data/` — gitignored runtime state.
- **Never** source the MCP tool surface from `src/ikigai/MCP_GATEWAY.md` — it advertises a different tool set than `src/ikigai/src/mcp_server/server.py`.

## UNIQUE STYLES

- **Mesh write path:** fork → CLI enqueues a `TaskChange` to `data/review_queue/` → agent validates → propagates a `PropagationEvent` to every fork; the read path joins all three adapters. `TaskdogAdapter` handles all 7 `TaskAction` values; `CliAdapter` and `SolverforgeCalendarAdapter` still return early on non-`create` (the "v1 = create only" rule is stale for taskdog).
- **Append-only is enforced twice:** every record in `vault/.vault_events.jsonl` carries `invariant: "VAULT_WRITE_INVARIANT"` (only `vault.toggle_applied` / `vault.reopen_applied` have inverses — rollback writes a NEW event), and `sys_ikigai/propagation/sqlite_adapter.py` installs `plan_entities_no_delete` / `plan_entities_no_update` triggers that `RAISE(ABORT)` (the only allowed UPDATE is archival, `archived_at`).
- **Single enforcement point:** `sys_ikigai/security/vault_write_wrapper.py` is the only sanctioned write path (ADR-029 §S2/R2) — kill switch → rate limit → actor validation → transition validator → legal-caller whitelist → pre-audit → `vault_write` → post-audit. `LEGAL_CALLERS` = `memory_write_atomic`, `dispatch_sub_agents`, `tag_and_persist`, `skill_orchestrator`; actors are `user | agent | system`.
- **Drift tests are AST scans, not runtime probes.** Forbidden-symbol frozensets live inside the test files and helpers are deliberately duplicated per file so the drift tests stay independent. `src/ikigai/tests` uses 63 `pytest.skip` + 8 `skipif` and 0 `xfail` — unfinished work parks as a skip.
- **Two `agents` packages, merged on purpose:** `src/agents/` (planner) and `src/ikigai/src/agents/` extend each other's `__path__`; 63 files import the `agents` namespace. A one-sided change hides the other half.
- **`tools/backtest/` is production code:** `tools/backtest/vault_propagation.py` (828 LOC) is the vault-write engine outside the Deep Agent; `tools/vault/` is a thin CLI facade over it.
- **Contract catalog rule:** a breaking change means a new version, never a silent mutation (`vibe-ops/src/contracts/registry.yaml`, ADR-001 §2.1). `SyncContractV1` requires `idempotency_key == "upstream_id"`.
- **Two import identities per layer:** dotted `from src.X import ...` and bare `from X import ...` coexist (`src.contracts` vs `contracts`, `src.ikigai.src.agents` vs `agents`, `src.mesh` vs `mesh`). **When monkeypatching, patch BOTH** — patching one identity silently no-ops. `tests/mesh/test_taskdog_cli.py` and `tests/mesh/test_td_dep.py` are the worked examples.
- **Two UEID formats live in the tree:** canonical is 4-part (`src/contracts/common.py`, ADR-014); `sys_ikigai/types.py` keeps a legacy 5-part alias and `vibe-ops/src/storage/ueid.py` a 3-part local one. The local ones must never leak into mesh payloads or `data/review_queue/`.

## COMMANDS

```bash
# install
pip install -e ".[dev,mesh]"           # root: setuptools installs only life*; src/* resolves via PYTHONPATH=src
cd src/ikigai && poetry install        # Poetry: agents, chat, mcp_server, observability, strategics, plugins
cd src/contracts && uv sync            # hatchling dist with its own lockfile + .venv
cd vibe-ops && uv sync                 # uv; puts vibe-ops/src on sys.path
cd interfaces/cli && uv sync           # uv; standalone CLI project
# test
pytest tests/ -v                       # root suite: 1,281 collected; 1,229 test functions in 143 files
cd src/ikigai && poetry run pytest     # drift-net suite (1,332 tests)
cd vibe-ops && uv run pytest
cd interfaces/cli && uv run pytest
bash scripts/smoke/phase3_v1.sh        # Phase 3 e2e in an isolated temp tree — never touches real data/
# lint / types
ruff check .                           # root has NO [tool.ruff]; policy: src/mesh/ruff.toml + src/contracts/pyproject.toml
mypy .                                 # root mypy.ini (mypy_path = src .. ../..)
cd src/ikigai && poetry run mypy -p src.ikigai.src   # by module identity, never by path
pre-commit run --all-files
# run
python -m life.cli --help              # or `life` after editable install
life mesh show <ueid>
python -m sys_ikigai.cli.app --help    # vault|vector|regime|phase|sync, --json everywhere
make install && make dev               # LangGraph dev server on port 2024
```

Console scripts: `life` → `life.cli:_main_console` (root `pyproject.toml`) and `interfaces.cli.read_tasks:app` (`interfaces/cli`); `td` → `src.mesh.taskdog_cli:main`, which only works when `src/` is on `PYTHONPATH`.

## NOTES

- **Windows quirks:** `sys.stdin.readline()` HANGS on Windows pipes during the MCP stdio handshake — use `sys.stdin.buffer.readline()` (`b93a1f3`); pytest-asyncio hits `PermissionError [WinError 5]` on stale temp dirs — `tests/conftest.py` redirects `tempfile.tempdir` to `data/pytest-tmp/` (`ff3037f`); an empty directory locked by another process is marked for deletion via the `PendingFileRenameOperations` registry. The ambient `python` is 3.14 and `pytest` cannot start (langsmith → opentelemetry `StopIteration` at import) — `src/ikigai/.venv/Scripts/python.exe` (3.11.16) runs the suite green.
- **`.gitignore` hides four-letter top-level directories:** the rule at `.gitignore:507` matches `life`, `docs`, `logs`, `data` (also `open`, `test`, `main`, `core`), so every NEW file below them is silently untracked. `!/src/` exists at `:514`; there is no `!/life/` — force-add with `git add -f life/AGENTS.md` or fix the rule.
- **`make test` is partially broken** — it references the removed `langgraph_tests/` and `src/operational/`; use `pytest tests/ -v`. Zero-byte root artifacts (`0`, `14`, `agent('Execute`, …) are stray bash-redirect typos — gitignored, leave them. The `strategics/planning-with-files` submodule is intentionally dirty (vendored third-party) — never commit its contents.
- **Overlapping docs:** root `CLAUDE.md` and `archive/legacy-pav/src-operational/CLAUDE.md` describe overlapping scopes — check `git log -- <path>` for ground truth. `docs/` mixes Portuguese and English and keeps historical plans — read `SUPERSEDED`/`PENDING`/dated markers; `openwiki/` and `docs/openwiki-visualizer/` are generated output.
- **Known broken on disk** (documented, not silently patched): `life/centrals/task.py::_run_task` references an undefined `TASK_BIN` — the swallowed `NameError` makes `life task today` return an error dict; `vibe-ops/src/agents/pae_maintainer/channels.py` imports a nonexistent `.state`; vibe-ops PowerShell scripts invoke the removed `src/main.py`; `.github/scripts/type_review.py` has a duplicate `text=True` and cannot parse; `src/life_tatics/` is a placeholder (`cmd_routine` returns `{"status": "pending_implementation"}`).
- **`plugins/paperclipai` is the repo's only TypeScript.** Its README drifts from the code (`LIFE_PAPERCLIP_PORT` vs the documented `LIFE_PAPERCLIP_BRIDGE_PORT`, stdlib server vs uvicorn, `vault/paperclipai_issues/` vs `vault/paperclipai_sync/`), and `_handle_issue_sync` writes into `vault/` — an unresolved ADR-012 ownership question.
- **Env vars:** `IKIGAI_FAKE_LLM`, `IKIGAI_MODEL` (default `MiniMax-M2.7-highspeed`), `IKIGAI_DISABLE_OTEL`, `IKIGAI_DEV_MODE`, `IKIGAI_VAULT_ROOT`, `LIFE_VAULT_ROOT`, `IKIGAI_KILL_SWITCH`, `TASKDOG_HTTP_ENABLED` (must be 0 in tests), `LIFE_PAPERCLIP_BRIDGE_PORT` (8741), `PAPERCLIP_*` cost/risk thresholds.
- **Commits:** branch off the default branch (`master` here), never push to it directly; conventional commits `feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`.