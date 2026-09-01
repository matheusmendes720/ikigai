# SUPERSEDED — Recovered Agentic-Systems Code (2026-09-01)

> **Status:** READ-ONLY REFERENCE — recovered from git history for inspection
> **NOT live:** drift detector scan excludes `archive/` — these files do NOT
> run, do NOT import into the live agent, do NOT count toward `IKIGAI_TOOLS = 12`.
> **Purpose:** foundation for the global refactor "all at once" that user
> authorized 2026-09-01 after reading the recovered code.

## Why this archive exists

Per the binding sequence (2026-08-31), user instructed deletion of all math
kernel code from the IKIGAI agent layer. Five commits executed that cascade:

| Commit | Scope |
|--------|-------|
| `8992e0c` | Strip 8 algo `@tool` wrappers from `tools.py`; simplified `deepagents_harness.py` |
| `c542ff9` | Inline QHE formula in `contracts/`, sever algo dep |
| `56cf9d7` | Strip `make_ikigai_graph` langgraph wrapper + `langgraph.json` entry |
| `cf44619` | Archive 4 algo CLI subcommands |
| `ab5570e` | Archive 6 algo entry points from `vibe-ops/` |
| `240ae08` | DELETE math kernel: `ikigai_maintainer/` + `core/scoring/` + `core/heuristics/` + 7 `@MCP.tool` wrappers in `server.py` |

User liked the original architecture scaffolding (8-node LangGraph, prompt-chain
structure, observation/reflection/planning/commit loops). On 2026-09-01 user
authorized recovery of this effort to:

1. **Inspect** the original design before refactoring
2. **Propose** a global refactor "all at once" that:
   - Replaces math execution (`compute_score`, regime FSM, H1-H6 heuristics,
     RICE, Q_HE, vector_scores, meta_vector) with **prompt chains and workflows
     defined between MCP tools** per the binding:
     > "IKIGAI = planning assistant, a nivel de prompt chains e workflows
     > definidos entre as tools com o mcp da interface"
   - Keeps the **structure** (graphs, nodes, state machines, pipeline
     orchestration) intact — that is what user explicitly approved.
   - Same treatment for `pae_maintainer` (still alive at
     `vibe-ops/src/agents/pae_maintainer/`) which has the same math-payload
     problem.

## What was recovered

| Path (archive/) | Original path | Lines | Source commit | Note |
|-----------------|---------------|-------|---------------|------|
| `src_ikigai_src_agents/ikigai_maintainer/` | `src/ikigai/src/agents/ikigai_maintainer/` | 13 files: graph.py (392) + state.py (230) + 9 nodes (incl. heuristics.py 161) + 2 __init__.py | `240ae08^` | Full 8-node LangGraph scaffolding |
| `src_ikigai_src_ikigai/core/scoring/` | `src/ikigai/src/ikigai/core/scoring/` | 5 files: meta_vector.py (98) + qhe.py (103) + rice.py (74) + vector_scores.py (186) + __init__.py | `240ae08^` | Math entry points — to be REPLACED |
| `src_ikigai_src_ikigai/core/heuristics/` | `src/ikigai/src/ikigai/core/heuristics/` | 7 files: regime.py (192) + cross_priority + opportunity_fit + phase_pivot + skill_velocity + weight_ucb + __init__.py | `240ae08^` | H1-H6 heuristics — to be REPLACED |
| `src_ikigai_src_ikigai/core/__init__.py` | `src/ikigai/src/ikigai/core/__init__.py` | 39 lines (re-exports) | `240ae08^` | Module entrypoint |
| `src_ikigai_src_agents/tools_PRE_STRIP_8992e0c.py` | `src/ikigai/src/agents/tools.py` | 1020 lines (with 8 algo `@tool` wrappers) | `8992e0c^` | Pre-strip agent tools surface |
| `src_ikigai_src_agents/deepagents_harness_PRE_STRIP_8992e0c.py` | `src/ikigai/src/agents/deepagents_harness.py` | 566 lines (with algo CLI dispatch) | `8992e0c^` | Pre-strip harness wiring |
| `src_ikigai_src_mcp_server_server_STRIPPED_WRAPPERS_240ae08.patch` | `src/ikigai/src/mcp_server/server.py` | 173-line patch (7 `@MCP.tool` removals: ikigai_score, ikigai_regime, ikigai_phase, ikigai_corrections, ikigai_plan_cycle, ikigai_checkpoint, ikigai_sync_vault) | `240ae08^ → 240ae08` | Orphan handlers remain in live server.py |
| `vibe_ops_src_langgraph_entry_STRIPPED_IKIGAI_WRAPPER_56cf9d7.patch` | `vibe-ops/src/langgraph_entry.py` | 96-line patch (make_ikigai_graph factory + 7 F401 imports) | `56cf9d7^ → 56cf9d7` | The 8-node wrapper for langgraph dev |
| `langgraph_json_STRIPPED_ikigai_maintainer_entry_56cf9d7.patch` | `langgraph.json` | 40-line patch (ikigai_maintainer entry removed) | `56cf9d7^ → 56cf9d7` | Entry deleted from langgraph.json |

Total: 32 files + 3 patches. ~2,500 LOC of scaffolding + ~1,000 LOC of math
modules + 309 lines of patch context.

## What was NOT recovered (and why)

- **7 `@MCP.tool` handler bodies** in `src/ikigai/src/mcp_server/server.py` —
  these were NOT deleted in `240ae08`, only the `@MCP.tool` decorator was
  removed. The handlers remain as "orphan archive" per the commit message.
  They can be inspected in the live file directly (grep for `async def
  ikigai_`).
- **CLI subcommands (4)** — `cf44619` already archived these into a separate
  archive location; not duplicated here.
- **`vibe-ops` algo entry points (6)** — `ab5570e` already archived these;
  not duplicated here.
- **The entire `src/operational/` tree** — that was archived separately on
  2026-08-31 (commit `411cce0`) at `archive/legacy-pav/src-operational/`. The
  PAV math kernel is the canonical PAV-side implementation; IKIGAI's math was
  a thin re-implementation. Recovering this archive does NOT change the
  "math lives in PAV, not IKIGAI" boundary.

## Reading order for inspection

1. **The 8-node LangGraph structure** (the part user wants to keep):
   - `src_ikigai_src_agents/ikigai_maintainer/graph.py` — 392 lines
   - `src_ikigai_src_agents/ikigai_maintainer/state.py` — 230 lines
   - `src_ikigai_src_agents/ikigai_maintainer/nodes/*.py` — 9 nodes
2. **The math surface** (the part to be replaced):
   - `src_ikigai_src_ikigai/core/scoring/*` — meta_vector, qhe, rice, vector_scores
   - `src_ikigai_src_ikigai/core/heuristics/*` — H1-H6
3. **The pre-strip agent layer** (what tools.py + harness looked like before):
   - `src_ikigai_src_agents/tools_PRE_STRIP_8992e0c.py` — 1020 lines with 8 algo `@tool`
   - `src_ikigai_src_agents/deepagents_harness_PRE_STRIP_8992e0c.py` — 566 lines
4. **The removed MCP wrappers** (what `@MCP.tool` decorators looked like):
   - `src_ikigai_src_mcp_server_server_STRIPPED_WRAPPERS_240ae08.patch`
5. **The removed langgraph wrapper** (how `make_ikigai_graph` integrated with `langgraph dev`):
   - `vibe_ops_src_langgraph_entry_STRIPPED_IKIGAI_WRAPPER_56cf9d7.patch`
   - `langgraph_json_STRIPPED_ikigai_maintainer_entry_56cf9d7.patch`

## Refactor target (post-inspection)

User authorized a global refactor "all at once". The transformation:

| Before (recovered) | After (target) |
|--------------------|----------------|
| `nodes/score_vectors.py` calls `ikigai.core.scoring.compute_score()` (math) | `nodes/score_vectors.py` calls `vault_read` + `taskdog_list_tasks` + prompts LLM to produce planning vector (no math) |
| `nodes/heuristics.py` calls `H1..H6` functions (math) | `nodes/heuristics.py` invokes prompt chains via MCP `vault_read` + `ikigai_read_strategics` (no math) |
| `core/scoring/*` (98+103+74+186 LOC math) | REMOVED — replaced by MCP `vault_read` over observed signals |
| `core/heuristics/*` (192+47+72+145+63+70 LOC math) | REMOVED — replaced by LLM dispatch on strategics markdown |
| `tools.py` 1020 LOC with 8 algo `@tool` wrappers | RESTORED at <= 500 LOC (plan budget), 12 IKIGAI_TOOLS total (drift detector enforced) |
| `deepagents_harness.py` 566 LOC with CLI dispatch | REFACTORED — only `_make_agent` + `run_chat` (current shape, math-free) |

PAV-side math (the canonical implementation in `archive/legacy-pav/src-operational/`)
remains the system-of-record for math execution. IKIGAI agent **observes**
PAV output via `vault_read` (which reads daily cycles, planning cycles,
regime transitions, etc.) but never executes math itself.

## Related

- [[archive/legacy-pav/SUPERSEDED.md]] — canonical PAV math kernel (sibling archive)
- [[docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md]] — §3
  (math not in agent), §7 (vault_write sole writer)
- [[code-docs/adr/ADR-013-canonical-scope-discipline.md]] — scope discipline
- `archive/recovered-agentic-2026-09-01/RECOVERY_INDEX.md` — file-by-file index
