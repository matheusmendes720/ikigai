---
name: M191-paperclip-dynamic-workflows
description: Paperclip Dynamic Workflows — 9-node skeleton, MVP mock LLM.
status: DONE
owner: matheus-mendes
created: 2026-10-12
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - reversibility_over_cleverness
  - composition_over_inheritance
  - multi_package_boundaries_are_sacred
estimated_cost_usd: 0.00
---

# M191 — Paperclip Dynamic Workflows (skeleton)

**Status:** 🟢 DONE (MVP skeleton)
**Date:** 2026-10-12
**Author:** matheus-mendes (with Claude Code assist)

---

## TL;DR

Paperclip Dynamic is the **fifth LangGraph graph** in `life-oss/life`,
registered in `langgraph.json` as `ikigai_dynamic`. It implements
Anthropic's "Dynamic Workflows" pattern (per
`deep-dive-dynamic-workflows.md`):

```
classify → planner → harness_builder → subagent_1 → subagent_2 → subagent_3
                                                       ↓
                                              per_subagent_verifier
                                                       ↓
                                              global_evaluator
                                                       ↓
                                                 synthesizer → END
```

A second graph alongside `ikigai_paperclip` (M169 — fixed topology
spec → worktree → agent → merge). The dynamic graph is a
**meta-orchestrator**: classify → planner (LLM-A) → harness builder
(LLM-B) → N sub-agents (LLM-C, one per task) → per-sub-agent verifier
(LLM-D) → global evaluator (LLM-E) → synthesizer (LLM-F).

Mock LLM calls for MVP — real LLM wiring is followup. Static fan-out
of 3 sub-agent slots in MVP; the harness builder warns + drops excess.

---

## What changed

```
src/ikigai/src/agents/paperclip_dynamic/        # NEW
├── __init__.py                                  # package marker
├── state.py                                     # DynamicWorkflowState (TypedDict, all NotRequired)
├── graph.py                                     # make_dynamic_graph + _build_dynamic_graph + 7 nodes + 3 slots
├── nodes/
│   ├── __init__.py
│   ├── classify.py                              # naive slash-command router (research/audit/fix)
│   ├── planner.py                               # LLM-A mock → emit 3-task sub-agent list
│   ├── harness_builder.py                       # LLM-B mock → emit workflow_spec.md (per §5 schema)
│   ├── subagent.py                              # LLM-C factory → make_subagent_node(index) per slot
│   ├── per_subagent_verifier.py                 # LLM-D mock → 3-check pass/fail per task
│   ├── global_evaluator.py                      # LLM-E mock → cross-check findings + confidence
│   └── synthesizer.py                           # LLM-F mock → final markdown report
└── tests/
    ├── __init__.py
    ├── test_graph_smoke.py                      # 4 tests: compiles, factory sig, state schema, empty query
    └── test_workflow_spec.py                    # 3 tests: spec md, task keys, cross findings

src/ikigai/tests/test_paperclip_drift.py          # +1 test: ikigai_dynamic registered in langgraph.json
specs/M191-paperclip-dynamic-workflows/SPEC.md   # this file
.claude/loop/roadmap.md                          # 1 M191 entry added
langgraph.json                                   # 1-line edit: 5th graph registered (ikigai_dynamic)
```

**Total: ~14 new files, 1-line langgraph.json edit, ~1,000 LOC.**

---

## Architecture decisions

### Why a fifth graph (not a feature on Paperclip)

`ikigai_paperclip` (M169) is a **fixed-topology** meta-orchestrator:
spec → HIL → worktree → agent → merge. The dynamic workflow graph is
a different shape entirely: it materialises its own sub-agents per
run, from a planner. Two distinct lanes:

- `ikigai_paperclip` → fixed shape, one workflow per invocation
- `ikigai_dynamic` → dynamic shape (planner emits subgraph at runtime)

Same package family (paperclip_*) because they share the meta-
orchestrator pattern + identical `_safe_node` wrapper. Distinct
factory function so langgraph.json can keep them side-by-side.

### Why static fan-out (not Send API) in MVP

Per deep-dive §9 the canonical LangGraph blueprint uses `Send` API
or subgraph injection for the sub-agent fan-out. We chose static
fan-out with `_MAX_SUBAGENT_SLOTS = 3` for MVP because:

1. **Simpler to test** — fixed topology, deterministic 9-node graph.
2. **Simpler to reason about** — the planner's "max 3 sub-agents"
   cap matches the graph's slot count exactly.
3. **Migration path is mechanical** — replacing 3 hardcoded slots
   with N Send-API dispatchers is graph surgery, not architecture.

Real implementation would use Send API; the planner already emits
the same shape (list of dicts) so the migration is local.

### Why mock LLM calls (not real Claude) for MVP

Per the user's project-wide discipline (CLAUDE.md): "Real LLM
wiring is followup." The skeleton proves the **graph topology** +
**state model** + **node contracts** without burning tokens. The
planner mock emits a deterministic 3-task list; the synthesizer
mock renders a deterministic markdown report; the rest are no-op
deterministic variants.

Real LLM calls would:

- Planner → call Claude to decompose the user query
- Harness builder → call Claude to write the workflow_spec.md
- Sub-agent → call Claude (per-task, large model)
- Verifier → call Claude (per-task, small model — cost discipline)
- Global evaluator → call Claude (analytical pass)
- Synthesizer → call Claude (best prose model)

The state model + node contracts in this MVP are the surface real
LLM calls would plug into. The wiring is followup.

### Why `workflow_spec.md` (Markdown) and not JSON

Per deep-dive §5: "Why Markdown? It's human-readable (debuggable),
serialisable (one big string), diffable (good for traces + historical
runs), LLM-friendly (planner outputs MD natively)." Identical rationale
for the harness builder.

The `workflow_spec_md` lives in state as a `str`. It's a **debuggable
artifact**: a user can `cat workflow_spec.md` and see what the planner
asked for, which is the same shape the runtime materialised into
sub-agents.

---

## State model

Per deep-dive §4 (state model). All fields `NotRequired` per OPEN-3
(Cloud Studio chat input requires this). The `messages` channel
carries the `Annotated[list[dict], operator.add]` reducer.

```python
class DynamicWorkflowState(TypedDict, total=False):
    # Inputs (set by caller)
    user_query: NotRequired[str]
    command: NotRequired[str]  # "research" | "audit" | "fix"

    # Planner output
    plan: NotRequired[dict[str, Any]]
    subagent_tasks: NotRequired[list[dict[str, Any]]]
    max_attempts: NotRequired[int]

    # Harness builder output
    workflow_spec_md: NotRequired[str]
    subagent_results: NotRequired[dict[str, Any]]
    subagent_retries: NotRequired[dict[str, int]]
    subagent_warnings: NotRequired[list[str]]

    # Global evaluator output
    cross_check_findings: NotRequired[list[str]]
    confidence: NotRequired[float]

    # Synthesizer output
    final_report_md: NotRequired[str]

    # Meta / observability
    trace: NotRequired[list[dict[str, Any]]]
    messages: NotRequired[Annotated[list[dict[str, Any]], operator.add]]
    last_step: NotRequired[str]

    # Error channel (mirrors Paperclip + v2 graph's pattern)
    originating_node: NotRequired[str]
    error_type: NotRequired[str]
    error_message: NotRequired[str]
    traceback_str: NotRequired[str]
```

---

## Node contracts

Per deep-dive §6. Each node is a plain
`def(state: DynamicWorkflowState) -> dict[str, Any]` function. The
graph factory wraps them in `_safe_node` (same pattern as `paperclip/
graph.py` and `v2/graph.py`).

| Node | Input | Output | Failure mode | Model class (real) |
|---|---|---|---|---|
| `classify` | raw user text | `command` (route) | bad routing → wrong planner | tiny (regex / keywords) |
| `planner` | user query + command | `plan`, `subagent_tasks`, `max_attempts` | hallucinated tools / data sources | mid-size, instruction-tuned |
| `harness_builder` | `plan` | `workflow_spec_md` | malformed spec → runtime errors | mid-size, structured-output |
| `subagent_1` / `_2` / `_3` | task + data + tools | `SubAgentResult` (per spec) | flaky data / API errors | **largest** model (worker) |
| `per_subagent_verifier` | task + result | pass / fail + warning | false positive → bad data through | small, fast (cheap gate) |
| `global_evaluator` | all `subagent_results` | `cross_check_findings`, `confidence` | misses cross-sub-agent conflicts | mid-size, analytical |
| `synthesizer` | all results + findings | `final_report_md` | drops nuance | **best prose model** |

The expensive models are at the ends — planner + harness builder are
mid-size (planning is not the expensive part); synthesizer is the
biggest (user-facing prose). The verifier is intentionally small —
a tax on every sub-agent completion, so cheap matters.

---

## Verification

```bash
# 1. Smoke tests for the new graph
python -m pytest src/ikigai/src/agents/paperclip_dynamic/tests/ -v
# Expected: 7 passed (4 in test_graph_smoke + 3 in test_workflow_spec)

# 2. Full drift net
python -m pytest src/ikigai/tests/test_drift_invariants.py \
                   src/ikigai/tests/test_drift_extended_invariants.py \
                   src/ikigai/tests/test_canonical_scope.py \
                   src/ikigai/tests/test_paperclip_drift.py
# Expected: 76+ passed (was 75 + 1 new)

# 3. langgraph.json validates
python -c "import json; d = json.load(open('langgraph.json')); assert 'ikigai_dynamic' in d['graphs']; print('5 graphs:', list(d['graphs'].keys()))"

# 4. Sanity: graph importable + has 9 nodes
python -c "from src.ikigai.src.agents.paperclip_dynamic.graph import make_dynamic_graph, NODES; g = make_dynamic_graph(); print('nodes:', NODES)"
```

---

## Acceptance

- [x] `ikigai_dynamic` registered in `langgraph.json` (5th graph)
- [x] 9-node StateGraph: classify, planner, harness_builder, 3×subagent, per_subagent_verifier, global_evaluator, synthesizer
- [x] `_safe_node` wrapper mirrors paperclip/v2 graph patterns
- [x] 2-arg `make_dynamic_graph(runtime, config)` signature (M102 mandate)
- [x] `SqliteSaver` checkpointer (data/paperclip_dynamic.db default)
- [x] `DynamicWorkflowState` — all fields `NotRequired`, `messages` carries the `Annotated[list, operator.add]` reducer (OPEN-3 lesson)
- [x] Static fan-out of 3 sub-agent slots; planner caps at same number
- [x] All node functions are no-LLM mocks (deterministic, fast, free)
- [x] Drift test: `test_paperclip_dynamic_graph_registered` (+1 invariant)
- [x] Smoke tests: 4/4 PASS
- [x] Workflow spec tests: 3/3 PASS

---

## Lessons

1. **Static vs dynamic fan-out is a graph-surgery choice, not an
   architecture choice.** The state model + node contracts in MVP
   are identical to what a Send-API real implementation would need.
   Migration is local, not systemic.

2. **Mock LLM calls + real node contracts is the right MVP shape.**
   The graph topology is provable without burning tokens; the
   state model is exercisable without provider flakiness; the test
   cycle is sub-second. Real LLM calls are plug-in later.

3. **Drift tests on registries are cheap insurance.** +1 test
   (`test_paperclip_dynamic_graph_registered`) guards against the
   single failure mode that breaks the entire graph: a missing
   `langgraph.json` entry. Cost: 6 lines of test code.

---

## Deferred (future waves)

| Wave | Adds | Drift count |
|------|------|-------------|
| **M191 (this)** | 7-node skeleton, mock LLM, static 3-slot fan-out | 76/76 |
| N+1 | Send API for true N-slot fan-out; planner emits arbitrary N | 76/76 |
| N+2 | Real LLM wiring (per-node model selection from `.env`) | 76/76 |
| N+3 | Sub-agent retry subgraph (closed-loop on verifier FAIL) | 76/76 |
| N+4 | Strict MD parser for `workflow_spec.md` (catches hallucinations) | 77/77 |

---

## Related

- `deep-dive-dynamic-workflows.md` — reverse-engineered reference
  from Ronald Hawk's video on Anthropic Dynamic Workflows
- `specs/M169-paperclip/SPEC.md` — sibling graph
  (`ikigai_paperclip`, fixed-topology meta-orchestrator)
- `src/ikigai/src/agents/paperclip/graph.py` — reused `_safe_node`
  pattern + `make_<name>_graph(runtime, config)` factory shape
- `src/ikigai/src/agents/paperclip/state.py` — reused NotRequired +
  messages channel discipline (OPEN-3 lesson)
- ADR-012 (vault_write is sole vault writer) — same model for
  node discipline: every state field has exactly one writer
