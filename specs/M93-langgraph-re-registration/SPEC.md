---
name: M93-langgraph-re-registration
description: Verify langgraph.json v2 graph registration + add drift tests
owner: matheus-mendes
status: DONE
milestone: M93
estimated_cost_usd: 0.03
constitution_refs:
  - state_on_disk_not_conversation
  - tests_are_the_contract
---

# M93 - langgraph.json v2 graph re-registration verified

## Context

Per M77 roadmap, `ikigai_maintainer_v2` was stripped from `langgraph.json`
during attribution §3 cleanup. Per M93 plan, re-register it.

**Discovery**: The registration was already in place. The current
`langgraph.json` lists `ikigai_maintainer_v2: ./src/ikigai/src/agents/v2/graph.py:make_v2_graph`
and `ikigai_fork_smoke`. Either:
- M77 actually re-registered it (and the spec was correct)
- Someone added it back later without tracking
- It's been there all along

Either way: **the registration works**. This milestone adds drift tests
to keep it that way.

## What changed

### tests/test_langgraph_json_spec.py (NEW)

7 tests covering:
- `langgraph.json` exists at repo root
- File parses as JSON with required fields (graphs, dependencies, env)
- `ikigai_maintainer_v2` is registered
- Registered factory imports + is callable
- Calling factory builds `CompiledStateGraph` with >=10 nodes
- All declared NODES (entry_points) build successfully
- Declared `python_version` matches our interpreter's major

## Acceptance

- [x] `langgraph.json` registers `ikigai_maintainer_v2` → `make_v2_graph`
- [x] Factory imports, builds CompiledStateGraph with 15 nodes
- [x] All 13 entry_points (per graph.NODES) build successfully
- [x] 7/7 unit tests PASS
- [x] Drift 18/18 PASS
- [x] root 368 PASS + 27 SKIP (was 361, +7 new tests)

## Lessons

- **Always verify before re-doing**: When M93 scope was "re-register the
  graph", the first action should have been reading the current state
  of `langgraph.json`. The work was already done.
- **Drift tests for config files matter**: `langgraph.json` is the
  deployment contract for `langgraph dev`. A test that loads + builds
  each registered graph catches: stale factory paths, broken imports,
  missing nodes, removed registrations.
- **Fake `langgraph_cli.dev` doesn't matter**: The official langgraph
  CLI is a development tool. The important thing is the registration
  contract — does the factory import, does it build, does it have nodes?
  These three questions, plus `importlib`-free loading, are enough.

## Out of scope (M93+ candidates)

- `langgraph dev` server actual startup test (requires `langgraph_cli`
  in ikigai venv, currently absent — install via `uv pip install
  langgraph-cli` if needed)
- Wire `langgraph dev` into `make dev-graph` so the visual debugger
  becomes available (already wired in root Makefile but uses wrong venv)
- Run the v2 graph via `langgraph dev` and verify it processes
  `ikigai-daily` skill (requires LLM API key + transport)
