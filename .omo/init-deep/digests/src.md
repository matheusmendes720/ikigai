# DIGEST — subtree `src/`

Writer scope: `src/` (contracts, mesh, ikigai, agents, tuiboard, solverforge_calendar, life_tatics, planner).
Depth limit honored: no file deeper than level 3 (`src/ikigai/src/`). `src/ikigai/tests/` reported only, never written.

## LOCATIONS WRITTEN

| Path | Score | Role |
|---|---|---|
| `src/AGENTS.md` | 9 | Source-layer root: 4 build systems, dual import identity, the two `agents/` packages |
| `src/contracts/AGENTS.md` | 9 | Canonical Pydantic v2 models; 4 divergent UEID regexes; plan-tree entities |
| `src/mesh/AGENTS.md` | 12 | Phase 3 mesh: fork adapters, append-only review queue, `td` CLI |
| `src/mesh/adapters/AGENTS.md` | 8 | Fork boundary: `ForkAdapter` Protocol, 3 implementations, A2UI wire schema |
| `src/ikigai/AGENTS.md` | 10 | Poetry sub-project root: console scripts, packaging, drift net, souls |
| `src/ikigai/src/AGENTS.md` | 11 | Agent runtime: v2 graph, 2 FastMCP servers, paperclip, skills, prompts |

**Skipped below threshold** (covered in `src/AGENTS.md` instead): `src/agents/` (6 — planner memory+reflection), `src/agents/reflection/` (6), `src/tuiboard/` (4 — MCP fork), `src/solverforge_calendar/` (4 — MCP fork), `src/life_tatics/` (2), `src/planner/` (0 — markdown only), `src/mesh/cli/` (2 — covered by `src/mesh/`), `src/data/` (runtime state, not code).

## FACTS THE ROOT FILE MUST KNOW

**Build systems are split four ways under `src/`** — the root file's "Tooling split" table needs updating:
- `src/contracts/` — standalone **Hatchling** project (own `pyproject.toml`, `uv.lock`, `.venv`).
- `src/ikigai/` — **Poetry** project (own `poetry.lock`, `.venv`); its `packages` list installs `agents`, `chat`, `mcp_server`, `observability`, `strategics`, `plugins` from `src/` plus `sys_ikigai` from the repo root. A stray `uv.lock` also exists.
- `src/mesh/` — **no** `pyproject.toml`, **not** in the root setuptools `packages` list; import-path-only. The root console script `td = "src.mesh.taskdog_cli:main"` works only because the repo root is on `sys.path`.
- `src/agents/`, `src/life_tatics/`, `src/tuiboard/`, `src/solverforge_calendar/`, `src/planner/` — plain Python, no packaging.

**Root `pyproject.toml` has NO `[tool.ruff]` table** (the root file claims one). Real Ruff configs: `src/mesh/ruff.toml`, `src/contracts/pyproject.toml`, `src/ikigai/pyproject.toml` — all line-length 100, py311, `select = [E,F,W,I,N,UP,B,A,C4,PT,RUF]`, `ignore = [E501]`.

**`src/` has no `__init__.py`.** `src.contracts.X` needs the repo root on `sys.path`; `contracts.X` needs `src/` on it (`pytest.ini` sets `pythonpath = src src/ikigai/src`). Both spellings appear in production code — inside `src/mesh/`, `agent_consumer`/`queue`/`investigation_queue`/`review_queue_cli` use bare `contracts.`, while `taskdog_cli`/`agent_propagator`/`mesh_cli`/`optimizer_strategies`/`review_queue_worker`/`td_dep` use dotted `src.contracts.` / `src.mesh.`.

**Two directories named `agents`** — `src/agents/` and `src/ikigai/src/agents/` — merged into ONE logical package: each `__init__.py` appends the sibling dir to `__path__`. Symmetric, must stay in sync.

**Four UEID regexes coexist** — the root file states one canonical form:
- `src/contracts/common.py` — **triple-pattern**: 4-part short | 4-part long-UUID | 5-part legacy, namespace `{2,8}`.
- `src/mesh/adapters/taskdog.py` — byte-identical inline copy of the above.
- `src/ikigai/contracts/proposal.py` — `{2,5}` 4-part (matches the root file's ADR-014 form).
- `src/ikigai/src/chat/schema.py` — `{2,10}` 4-part.
Not kept in sync; each is asserted separately by a different test.

**Mesh v1 scope is contradicted by the code.** Root file says "Phase 3 mesh v1 ships `create` action only". True for `CliAdapter` and `SolverforgeCalendarAdapter` (both early-return unless `action == "create"`), **false for `TaskdogAdapter`**, whose `apply_change` dispatches `create`, `update`, `done`, `delete`, `tag_add`, `tag_remove`, `tag_clear`. The `src/mesh/adapters/__init__.py` docstring still claims create-only — it is stale.

**Two `Proposal` classes with different fields**: `src/ikigai/contracts/proposal.py` uses `approval_state`; `src/ikigai/src/chat/schema.py` uses `status`. Neither is the canonical `TaskChange`.

**Agent surface numbers (verified by AST):** `IKIGAI_TOOLS` = exactly 12 (10 in the literal + 2 via `.extend`). `mcp_server/server.py` registers 31 `@MCP.tool` + 6 `@MCP.resource` on `FastMCP("ikigai-gateway")`; `mcp_server/taskdog_tools.py` registers 25 `@mcp.tool` on a **second** `FastMCP(name="taskdog")`. `v2/graph.py` `NODES` = 16 names; the graph registers 17 nodes (adds terminal `error`). `algorithm_constants.json` = 31 tuning keys.

**Largest files in the subtree:** `src/mesh/taskdog_cli.py` 1035, `src/mesh/adapters/taskdog.py` 992, `src/mesh/cli/td_advanced.py` 961, `src/ikigai/src/mcp_server/taskdog_tools.py` 691, `src/ikigai/src/agents/v2/subgraph.py` 749, `src/ikigai/src/agents/v2/checkpoint.py` 679, `src/ikigai/src/agents/v2/graph.py` 606, `src/ikigai/src/mcp_server/server.py` 549, `src/ikigai/src/agents/tools.py` 558.

**Docs with drift** (do not trust): `src/ikigai/README.md` says `poetry run ikigai` (no such script); `src/ikigai/MCP_GATEWAY.md` says `poetry run ikigai-mcp` (real name `ikigai-maintainer-mcp`); `src/ikigai/SPEC.md` D10 calls UEID a "tri-key" while `taskdog_cli` expects 5 colon-separated components; `src/ikigai/tools/views.py` documents itself as `python -m tools.ikigai_views`.

**Reported but NOT written — `src/ikigai/tests/`** (104 test files, the drift net). No `AGENTS.md` created there by instruction. Facts the root file should carry: the drift net lives in `test_canonical_scope.py` (planner-only scope, 12-tool count), `test_drift_invariants.py` (UEID 4-part, append-only, `vault_write` sole writer), `test_drift_extended_invariants.py` (wave 3+ invariants a–h), plus `test_drift_detector.py` and `test_drift_state.py`. Drift tests are **append-only — never delete or weaken one**. Two known stale comments inside `src/ikigai/src/mcp_server/server.py` claim "11 total" / "8 IKIGAI + 3 Plan C investigation" tools; the real count is 31. `src/ikigai/src/agents/v2/tools_legacy_reference.py` (722 LOC) and `harness_legacy_reference.py` (370 LOC) are frozen `if False:` blocks — never import.

**Two temporal-model documents with different math** (both PT-BR markdown, both misspelled `time-lenghts_reviews.md`): `src/life_tatics/time-lenghts_reviews.md` (1583 LOC) is canonical — `rho = 11/15`, `WAVE = 15 D = 11 W`, `CYCLE = 45 D = 33 W`, `PHASE = 180 D = 132 W`, explicit `floor` for D→W and `ceil` for W→D, `BUFFER_CYCLE = 3 D`. `src/planner/time-lenghts_reviews.md` (1173 LOC) is the earlier variant — `WORK_RATIO = 22/30` (same 0.7333 value, different form), no `BUFFER_CYCLE`, floors both directions. When a temporal number is disputed, the `life_tatics` copy wins.

**Windows note:** `pytest-asyncio` `PermissionError [WinError 5]` on stale temp dirs — `tests/conftest.py` redirects `tempfile.tempdir` to `data/pytest-tmp/`. `src/data/` also holds a leaked `pytest-tmp/` copy.
