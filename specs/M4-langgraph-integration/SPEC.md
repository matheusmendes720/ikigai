# M4 — LangGraph Integration

**Status:** DRAFT (2026-09-07)
**Slug:** `langgraph-integration`
**Owner:** orchestrator
**Dependencies:** M3 (DONE)

## What

Wrap the 3 LangGraph graphs registered in `langgraph.json` as orchestrator
sub-agent tools. Today the graphs are manual-invocation via `make dev-graph NAME=...`.
Make them reachable from inside the loop tick.

## Graphs in scope

Per `langgraph.json` (verified 2026-09-07, actual registry):

| Graph key | Entry factory | Path |
|---|---|---|
| `pae_maintainer` | `make_pae_graph` | `./vibe-ops/src/langgraph_entry.py` |
| `ikigai_maintainer_v2` | `make_v2_graph` | `./src/ikigai/src/agents/v2/graph.py` |
| `ikigai_fork_smoke` | `make_fork_smoke_graph` | `./src/ikigai/src/agents/v2/fork_smoke_graph.py` |

CLAUDE.md table is stale (still references removed `quarterly_replan`,
`correction_protocol`, `dream_falsification`, `test_de_fogo_rollup`). The 3
graphs above are the live registry.

## Acceptance criteria

1. **Graph tool surface** — orchestrator prompt registers the 3 graph names
   as callable tools with one-line invocation syntax
   (`make dev-graph NAME=<key>` or direct factory call).
2. **State persists across ticks** — SqliteSaver (already wired in both
   `make_pae_graph` and `make_v2_graph` factories) checkpoint file lives at
   `.swarm/langgraph_checkpoint.db` (gitignored). Same path used across ticks
   so `thread_id` survives daemon restarts.
3. **Deterministic gate** — `bash .claude/loop/loop-tick.sh --graph <key>`
   flag added; `--graph` skips orchestrator LLM and runs the named graph
   end-to-end, exiting with the graph's terminal status code. Required so
   cron can run graphs unattended without burning orchestrator tokens.
4. **Integration test** — `tests/test_m4_langgraph_integration.py` exercises
   each of the 3 graphs (5/5 PASS) and asserts checkpoint DB exists after each
   run. ~30 LOC.
5. **No regression** — existing `tests/test_loop_infra.py` (11/11) still
   passes. No drift invariant regression
   (`src/ikigai/tests/test_canonical_scope.py` 33/33 + interfaces 68/68
   baseline preserved).

## Out of scope (deferred)

- Wiring real MCP tool calls in v2 nodes (Phase 8.2 — already documented in
  `src/ikigai/src/agents/v2/graph.py:7`)
- Replacing the math-stubbed nodes with real PAE math (PAV archived per
  ADR-013, drift invariant Wave h enforces non-regression — see
  `archived-feature-not-vocabulary-2026-09-06` memory)
- Building the missing 4 graphs (`quarterly_replan` / `correction_protocol` /
  `dream_falsification` / `test_de_fogo_rollup`) — only if M9 (production mode)
  demands them

## Estimated ticks

3-5 (one per acceptance criterion, plus verification tick)

## Risk

- **Low:** graph factories already exist and were tested in Phase 8.1
  (commit `fb41578`). The work is glue, not new graph logic.
- **Medium:** SqliteSaver path collision between cron runs. Mitigated by
  single shared `.swarm/langgraph_checkpoint.db` with `thread_id` per tick.
- **Low:** orchestrator prompt change risks worker/verifier confusion.
  Mitigated by keeping tool surface additive (existing tools preserved).

## How to verify (deterministic gates first)

```bash
# 1. Test infra still green
pytest tests/test_loop_infra.py tests/test_m4_langgraph_integration.py -v

# 2. Each graph runs end-to-end via loop-tick.sh --graph
bash .claude/loop/loop-tick.sh --graph pae_maintainer
bash .claude/loop/loop-tick.sh --graph ikigai_maintainer_v2
bash .claude/loop/loop-tick.sh --graph ikigai_fork_smoke

# 3. Checkpoint DB exists + has rows
ls -la .swarm/langgraph_checkpoint.db
sqlite3 .swarm/langgraph_checkpoint.db "SELECT COUNT(*) FROM checkpoints;"
```

PASS only when all 3 graphs exit cleanly + checkpoint DB exists + 5/5 new
tests pass + 0 regression in existing suites.
