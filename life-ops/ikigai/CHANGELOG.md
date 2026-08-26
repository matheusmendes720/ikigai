# Changelog — IKIGAi

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
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

### Changed
- **`src/ikigai/entities/plan/dream.py`** — `horizon_days` Literal extended with `547` (1.5yr anchor)

---

## [0.1.0] — 2026-08-26

### Added
- Initial project structure
- `src/ikigai/` — IKIGAi entity models (Dream, Goal, Objective, Project, Task)
- `pyproject.toml` — langgraph, langgraph-checkpoint-sqlite, mcp, pydantic, python-frontmatter
