# Changelog — IKIGAi

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- **`ikigai_decompose`** — real vault traversal: reads `data/matheus/` frontmatter to resolve UEID hierarchy (dream → objective → project)
- **`ikigai_sync_vault`** — writes cycle snapshot as `data/matheus/ikigai_state/cycle-{date}.md` with frontmatter + markdown table
- **`ikigai-deep-agent` CLI** — `IKIGAiDeepAgent` class with `invoke()`, `resume()`, `list_checkpoints()`; full CLI via `python -m agents.deepagents_harness` with `--thread`, `--checkpoint-db`, `--human-in-the-loop`, `--list-checkpoints`, `--resume`
- **`agents` package** — `src/agents/` with `ikigai_maintainer` LangGraph agent and `deepagents_harness`

### Fixed
- **`ikigai_sync_vault`** — now reads from `plan_entities.db` (written by `ikigai_plan_cycle`) instead of empty `_read_checkpoint()`
- **`_read_checkpoint`** — fixed LangGraph schema query (uses `checkpoint_id`/`checkpoint` BLOB, not `created_at`/`state TEXT`)
- **`_read_plan_entity`** — new helper reading `plan_entities.db` for cycle state
- **`ikigai_plan_cycle`** — persists final state to `plan_entities.db` after graph execution

### Changed
- **`score_vectors.py`** — replaced `solverforge-calendar-mcp` subprocess calls with direct vault frontmatter reads; `skill` from DONE projects, `market` from ACTIVE project count, `revenue` from revenue-tagged projects
- **`src/mcp_server/`** — MCP 1.x server with 8 tools via stdio transport:
  - `ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_decompose`,
    `ikigai_corrections`, `ikigai_plan_cycle`, `ikigai_checkpoint`, `ikigai_sync_vault`
- **`src/agents/`** — agents package with `ikigai_maintainer` LangGraph agent:
  - 8-node StateGraph: observe → score_vectors → heuristics → balance → decompose → plan → reflect → commit
  - `SqliteSaver` checkpointing to `~/.ikigai/ikigai_checkpoints.db`
- **`src/agents/__init__.py`** — agents package init

### Fixed
- **`src/mcp_server/server.py`** — MCP handler signatures (TypedDict attribute access, proper `ListToolsResult`/`CallToolResult` return types)
- **`src/mcp_server/server.py`** — `ikigai_checkpoint` schema collision with LangGraph's own `checkpoints` table; now uses LangGraph's actual schema with `INSERT OR REPLACE`
- **`src/agents/ikigai_maintainer/`** — all internal imports converted from absolute (`from ikigai_maintainer.X`) to relative (`from .X` / `from ..X`)
- **`deepagents_harness.py`** — `list_checkpoints()` fixed LangGraph schema (thread_id/checkpoint_ns, not created_at)

### Changed
- **`src/ikigai/entities/plan/dream.py`** — `horizon_days` Literal extended with `547` (1.5yr anchor)
- **`pyproject.toml`** — added `agents` package + `ikigai-deep-agent` console_scripts entry

---

## [0.1.0] — 2026-08-26

### Added
- Initial project structure
- `src/ikigai/` — IKIGAi entity models (Dream, Goal, Objective, Project, Task)
- `pyproject.toml` — langgraph, langgraph-checkpoint-sqlite, mcp, pydantic, python-frontmatter
