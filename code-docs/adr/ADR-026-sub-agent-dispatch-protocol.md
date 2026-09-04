# ADR-026 — Sub-Agent Dispatch Protocol

> **Status:** DRAFT (2026-09-04)
> **Deciders:** matheus (project owner)
> **Load-bearing:** YES — gates W4.4 sub-agent dispatch node implementation (B-N10, 12-16h); precedes ADR-027 (stateful subgraph checkpoint schema) and ADR-028 (memory layer) in the Wave 4 Sequence-B stack
> **Supersedes:** none (new decision)
> **Renumbered from:** PLAN §3 "ADR-015 (write first)" — user decision 2026-09-04 ("Renumber to 026+") overrides PLAN numbering; ADR-014 is now UEID canonical format (per ADR-014, Accepted 2026-09-04)
> **Wave:** dcode-harness roadmap Wave 4 (W4.1)
> **Wave 3 context:** Wave 3 SHIP-COMPLETE on commit `be9a370` (2026-09-04, M-1 ruff cleanup); 8/8 tasks shipped, drift detector 24/24 PASS, ruff clean
> **Forward dependency:** checkpoint schema details are TBD per ADR-027 (stateful subgraph) — this ADR references the schema but does not lock it
> **Related code:** `src/ikigai/src/agents/v2/graph.py:83-94` (NODES tuple), `graph.py:215-243` (make_v2_graph factory), `graph.py:102-123` (_safe_node wrapper), `src/ikigai/src/agents/v2/state.py` (IKIGAiStateDict), `interfaces/cli/v2.py:160-215` (invoke_skill loader), `interfaces/cli/_skill_outputs.py` (W3.6 post-processor pattern)

---

## Context

Wave 3 of the dcode-harness roadmap shipped the v2 graph (9 nodes + error node,
`NODES` tuple at `graph.py:83-94`) bound to 4 IKIGAI skills via the YAML manifest
mechanism (ADR-025). All 4 skills (`daily` / `weekly` / `monthly` / `quarterly`)
enter the graph at a single `entry_point` and execute **one linear pipeline**.
The dispatcher (currently `invoke_skill` in `interfaces/cli/v2.py:160-215`) hands
the skill name to `make_v2_graph(entry_point=...)` and the graph runs the
chosen subgraph from start to `END`.

Wave 4 (Scenario B — Sub-agents + stateful subgraphs, 32-44h) requires the
parent graph to **fork**: at certain nodes (the brief specifies `decompose` as
the prime example, but also `plan` and `reflect`) the parent must spawn **one
or more child sub-agents** that run in parallel with a narrowed context, then
collect their outputs and merge them back into the parent state. Concrete
motivations:

- **Per-skill decomposition.** The `decompose` node currently produces a flat
  list of subtasks. Wave 4 needs each top-level task to be decomposed by a
  dedicated child agent that has access to its task's vault subtree, not the
  whole planning tree. This is a horizontal fan-out.
- **Parallel research.** `observe` and `reflect` would benefit from concurrent
  sub-agents reading disjoint vault slices (e.g., one reading SONHO-tree
  evidence, another reading OndaTree corrections) and aggregating findings.
- **Recursive planning.** `plan` may need to delegate sub-planning to a child
  sub-agent that runs its own `decompose → plan → commit` subgraph on a
  scoped context (a single project subtree).

The architectural problem: **what is the protocol** for spawning these
sub-agents, populating their context, executing them, collecting their
outputs, and merging into parent state — without violating ADR-013
(planner-only), ADR-014 (UEID 4-part canonical), ADR-025 (skill binding),
ADR-012 (`vault_write` sole writer), or ADR-019 (algorithm_constants.json
single source of truth)?

This ADR formalizes the dispatch contract. It is **architectural decision
only** — implementation ships in W4.4 (B-N10, 12-16h). A spike / prototype
reference is included per Diag 04 risk flag (no shipped prototype yet —
the spike is itself out of scope for W4.1 and is the first task of W4.4).

---

## Decision

**Sub-agent dispatch is a deterministic, async-or-sync, in-process LangGraph
sub-invocation that propagates a narrowed slice of `IKIGAiStateDict` to a
child graph, runs the child to completion (success / partial / failure),
isolates its error channel from the parent, and merges its terminal state
fields back into the parent's `IKIGAiStateDict` via a reducer-aware merge.**

The protocol has 5 contracts (S1–S5 below) and 6 rules (R1–R6 below).

### S1 — Spawn contract

A parent node (e.g., `decompose`, `plan`, `reflect`) signals "spawn N
sub-agents" by writing a `dispatch_plan` field to `IKIGAiStateDict`:

```python
class SubAgentSpec(TypedDict):
    sub_agent_id: str            # ULID/UUID — unique within parent cycle
    entry_point: str             # one of NODES (graph.py:83-94)
    context_slice: list[str]     # fields to propagate from parent state
    timeout_s: float             # hard timeout; default 60.0
    actor: Literal["user", "agent"]   # vault_write actor tag

class DispatchPlan(TypedDict):
    sub_agents: list[SubAgentSpec]
    merge_strategy: Literal["append", "reduce", "last-write-wins"]
```

The parent node does NOT call `make_v2_graph` directly. It writes
`dispatch_plan` and routes to a new dedicated **dispatch_node** (the
W4.4 B-N10 implementer names this node; ADR-026 reserves the name
`dispatch_sub_agents`). `dispatch_node` reads `dispatch_plan`, spawns
each child, awaits results, applies the merge strategy, and clears
`dispatch_plan` from state (single-use).

### S2 — Context propagation

Each child receives a **narrowed `IKIGAiStateDict`** containing only fields
named in `SubAgentSpec.context_slice`. The valid slice keys are the keys
of `IKIGAiStateDict` (`src/ikigai/src/agents/v2/state.py:115-198`). The
dispatcher:

1. **Copies** the named fields from parent state to the child `initial_state`
   (defensive copy — child mutations MUST NOT bleed back).
2. **Always** injects `cycle_id`, `cycle_start`, `cycle_end`, `iteration`
   from parent (these are required fields of `IKIGAiStateDict` per
   `state.py:118-122`).
3. **Always** injects `actor` from `SubAgentSpec.actor` (defaults to
   `"agent"` per ADR-025 R2 mapping for non-`daily` skills; **never
   `user`** because sub-agents are spawned by the parent graph at runtime,
   not by the user).
4. **Never** propagates `error_type`, `error_message`, `traceback_str`,
   `error_traceback`, `commit_summary` from parent to child (parent's error
   channel is isolated; child starts fresh).

The narrowed slice is the ONLY contract the parent and child share. There
is no implicit shared state.

### S3 — Collection contract

When all sub-agents have terminated (success / partial / failure / timeout),
the dispatcher merges their results into the parent state according to
`DispatchPlan.merge_strategy`:

| Strategy | Behavior |
|----------|----------|
| `append` | Append child output to a `list` parent field (e.g., `prospective_buffer`, `retrospective_log`, `corrections`). Parent uses LangGraph's `Annotated[list[X], operator.add]` reducer. |
| `reduce` | Apply a registered reducer to combine child outputs (e.g., `vector_scores` aggregation). Reducer name is a string in `SubAgentSpec.reducer` field (TBD schema — see ADR-027 forward dependency). |
| `last-write-wins` | Take the last successful child's output. Used for single-output dispatches (e.g., one child scoring one task). |

Each child's terminal output is recorded under `sub_agent_results:
list[SubAgentResult]` on the parent state, where:

```python
class SubAgentResult(TypedDict):
    sub_agent_id: str
    entry_point: str
    status: Literal["success", "partial", "failure", "timeout"]
    duration_s: float
    fields_written: list[str]      # names of parent fields this result touched
    error: NotRequired[str]        # populated only on failure/timeout
```

### S4 — Termination

A sub-agent terminates when one of:

1. **Success** — child graph reaches `END` with no error channel fields populated.
2. **Partial** — child graph reaches `surface_intentions` (the W3.5
   surface-only terminal node per `graph.py:209-323`); `user_suggestions`
   is set on child state; treated as successful completion with
   `status: "partial"` to signal the parent that the child emitted
   suggestions instead of executing downstream.
3. **Failure** — child graph reaches `error_node` (per
   `graph.py:102-123` safe-node wrapper); `error_type` / `error_message`
   populated. Captured into `SubAgentResult.error`; **parent
   `error_type` MUST NOT be set** (R5 isolation).
4. **Timeout** — wall-clock exceeds `SubAgentSpec.timeout_s`. Child
   graph is forcibly cancelled (LangGraph SqliteSaver supports this); a
   stub `SubAgentResult` with `status: "timeout"` is recorded.

The dispatcher awaits ALL spawned sub-agents (parallel execution via
LangGraph's standard async runtime) and only then proceeds to merge.

### S5 — Failure isolation

Per the Phase 3 v1 propagation pattern (`src/mesh/agent_propagator.py`
per-adapter failure isolation) and ADR-012 audit-log attribution:

1. A child failure or timeout MUST NOT cause the parent to enter
   `error_node`. The parent's `error_type` field is NEVER set by the
   dispatcher's child-merge step.
2. The parent receives `sub_agent_results` containing the failed
   child's `status` and `error` fields. The parent's routing logic at
   the next node MAY inspect `sub_agent_results` and route differently
   (e.g., skip downstream commit if a critical child failed).
3. Per-sub-agent failure isolation is MANDATORY: one child's failure
   MUST NOT prevent sibling children from completing.

---

## Rationale

1. **Single dispatch surface.** Putting all dispatch logic on a dedicated
   `dispatch_sub_agents` node (instead of inlining at each spawning parent
   node) gives us **one place** to enforce planner-only (ADR-013),
   `vault_write` sole-writer (ADR-012), and 4-part UEID (ADR-014)
   invariants. Inlining would multiply the invariant-check surface by
   `len(NODES)`, making drift detection intractable.

2. **Defensive state copy.** ADR-013's planner-only contract means
   sub-agents read state and write only via `vault_write(actor="agent")`.
   A child that mutated the parent's `IKIGAiStateDict` in place would
   silently violate that contract. The defensive copy in S2 makes the
   contract mechanically enforced — children can mutate freely without
   affecting the parent.

3. **Append-only log via reducer.** LangGraph's
   `Annotated[list[X], operator.add]` reducer (already used by
   `prospective_buffer`, `retrospective_log`, `corrections` in
   `state.py:156-162`) gives us **free parallel-append semantics** for
   child outputs that match the canonical prospective / retrospective
   channels. No bespoke merge logic is needed for these.

4. **Failure isolation matches Phase 3 v1.** The mesh data-fabric
   (`src/mesh/agent_propagator.py`) already implements per-adapter
   failure isolation. ADR-026 inherits that pattern: per-child isolation
   in the dispatcher mirrors per-adapter isolation in the mesh. Both
   share the "one failure must not cascade" invariant.

5. **Tunable dispatch via manifest.** Per ADR-025, skills declare their
   `entry_point` and `outputs` in YAML frontmatter. ADR-026 EXTENDS
   this: skills MAY declare `sub_agents: list[SubAgentSpec]` in their
   manifest to pre-declare dispatch patterns (planned for v2 manifest;
   current v1 is single-pipeline). This keeps the manifest as the
   canonical binding surface (ADR-013 single-source-of-truth).

6. **Algorithm constants in JSON only.** Per ADR-019, all tuning values
   (timeouts, retry counts, max-fan-out) live in
   `prompts/algorithm_constants.json`. No `DEFAULT_DISPATCH_*` Python
   constants are permitted in the dispatcher module. Drift detector
   `test_no_algorithm_constants_in_agent_code` (ADR-019 R7) extends
   to the new dispatcher module when W4.4 ships.

7. **Actor consistency.** Per ADR-025 R3 + ADR-012, every `vault_write`
   call from a sub-agent MUST pass `actor="agent"` (sub-agents are
   spawned by the parent graph at runtime, never directly by the user).
   The dispatcher injects `actor` into every child's initial state per
   S2.3; this guarantees consistency without per-node boilerplate.

8. **Checkpoint schema deferred to ADR-027.** The SqliteSaver checkpoint
   schema for sub-agent state is intentionally NOT specified here.
   ADR-027 (stateful subgraph, B-N11) will lock the schema for parent
   + child checkpoint rows. ADR-026's S2/S3 contracts specify the
   in-memory state shape (TypedDict fields), which ADR-027 will
   serialize to SQLite. This keeps ADR-026's scope tight and avoids
   pre-empting ADR-027's design.

---

## Implementation Rules

**R1 — Dispatcher is a dedicated node.** All sub-agent dispatch lives in
`src/ikigai/src/agents/v2/nodes/dispatch_sub_agents.py` (name reserved by
this ADR; the W4.4 implementer may adjust the module path but not the
node name). No parent node inlines dispatch logic. The dispatcher node
appends to `NODES` (W4.4 implementation task).

**R2 — Planner-only invariant.** Sub-agents MUST be planner-only
(ADR-013). The dispatcher enforces this by:
- Rejecting any `SubAgentSpec.entry_point` not in `NODES`
  (`graph.py:83-94`).
- Injecting `actor="agent"` (never `"user"`) into every child's
  initial state (S2.3).
- Forbidding direct `vault_write` calls from sub-agents (they MUST go
  through the same `vault_write` MCP tool the parent uses, with
  `actor="agent"`).

**R3 — vault_write sole-writer enforcement.** Per ADR-012 §1, the
dispatcher MUST validate that no child attempted to bypass
`vault_write`. The drift detector gains invariant (m) at W4.4 ship
(see W4.7): any path in a child that writes a `vault/` file via
`Path.write_text` / `open(..., "w")` / `os.replace` is flagged.
This invariant is the canonical enforcement of R3.

**R4 — UEID 4-part canonical.** Every UEID flowing between parent and
child (e.g., `active_dream_ueid`, `active_goal_ueids`, etc.) MUST match
`^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (ADR-014). The
dispatcher MUST NOT rewrite or migrate UEIDs; it copies them as-is
from parent to child state. 5-part UEIDs are REJECTED.

**R5 — Failure isolation.** Per S5: child's failure / timeout MUST NOT
populate parent `error_type`. The dispatcher's merge step is wrapped
in `try/except`; any exception during merge is logged but does NOT
route the parent to `error_node`. The parent's `sub_agent_results`
list carries the failure for parent-routing decisions at the next
node.

**R6 — Algorithm constants in JSON only.** Per ADR-019 R2: any new
tuning value (default timeout, max-fan-out, retry count, etc.) lives
in `prompts/algorithm_constants.json` ONLY. No `DEFAULT_DISPATCH_*`
Python constants in `src/ikigai/src/agents/v2/*.py`. The drift
detector's `test_no_algorithm_constants_in_agent_code` invariant
extends to the dispatcher module at W4.4 ship.

---

## Spike / Prototype Reference

Per Diag 04 risk flag (no shipped prototype yet), this ADR documents
the planned spike for W4.4:

- **Spike location:** `src/ikigai/src/agents/v2/spikes/sub_agent_dispatch_spike.py`
  (NEW — first task of W4.4 implementation)
- **Spike goal:** Stand up the 5-contract protocol (S1-S5) against a
  minimal `decompose` fan-out (2 children, 1 succeeds + 1 times out)
  with deterministic mocked nodes (no LLM calls).
- **Spike acceptance:** All 5 contracts verified via unit tests:
  - S1: parent writes `dispatch_plan`, routes to dispatcher, dispatcher
    spawns 2 children with the right initial state.
  - S2: child state is a defensive copy of parent's narrowed slice;
    child's mutation does not bleed back.
  - S3: parent state after merge contains `sub_agent_results` with 2
    entries, both with correct `status` (`success` + `timeout`).
  - S4: timeout sub-agent's `error` field is populated; success
    sub-agent's `error` field is `NotRequired` (None).
  - S5: parent `error_type` is NOT set after dispatch (verified via
    `_route_after_*` checks that `error_type` is empty).
- **Spike deliverables:** (1) `sub_agent_dispatch_spike.py` running
  end-to-end with mocked nodes; (2) `tests/test_sub_agent_dispatch_spike.py`
  with 12-15 unit tests covering S1-S5 + edge cases (zero children,
  all-children-fail, max-fan-out); (3) `docs/spikes/sub-agent-dispatch-spike-report.md`
  summarizing findings + ADR-026 amendments if any.
- **Risk if spike fails:** the architecture in this ADR is invalidated;
  W4.4 escalates to ADR-026 amendment (write a new ADR with revised
  S1-S5) rather than shipping an in-spec but untested dispatcher.

The spike is the **first task** of W4.4 (W4.4.1) and gates W4.4.2+
implementation tasks. W4.4.1 is 2-4h; W4.4.2+ is 10-14h.

---

## Consequences

### Positive

- **Single dispatch surface** (R1) — one place to enforce planner-only,
  vault_write sole-writer, 4-part UEID invariants. Drift detector has
  one file to scan, not `len(NODES)`.
- **Deterministic, async-or-sync runtime.** LangGraph's standard
  parallel-subgraph invocation handles the parallelism; the dispatcher
  just composes it. No bespoke concurrency primitive needed.
- **Append-only reducer for free.** Parent's `prospective_buffer` /
  `retrospective_log` / `corrections` fields already use
  `Annotated[list[X], operator.add]`, so `append` merge strategy
  requires zero new code.
- **Failure isolation** (R5) — one child's failure does not cascade
  to parent or siblings. Mirrors Phase 3 v1 mesh propagation pattern.
- **Algorithm-tunable dispatch** (R6) — tuning via JSON edit, no Python
  refactor (per ADR-019 build order: backend → data → agent →
  algorithms LAST).
- **Manifest-driven dispatch** — skills MAY declare `sub_agents:` in
  their YAML frontmatter (planned for v2 manifest), extending ADR-025
  binding mechanism naturally.

### Negative

- **Checkpoint schema deferred.** ADR-027 (stateful subgraph) must lock
  the SqliteSaver schema for parent + child rows. Until then, the
  dispatcher cannot be checkpointed (W4.4 ships without checkpoint
  resume; ADR-027 brings it online).
- **Defensive copy has cost.** Copying the narrowed `IKIGAiStateDict`
  per child has memory + time overhead. For typical fan-out (3-5
  children, ~20 fields each) this is negligible; for pathological
  fan-out (50+ children) it may bite. Mitigated by R6's max-fan-out
  constant (TBD in `algorithm_constants.json`).
- **Error channel visibility cost.** Per R5, parent `error_type` is
  never set by child failures. Parent routing logic MUST inspect
  `sub_agent_results` instead. This is a contract shift from the
  pre-W4 linear pipeline (where parent `error_type` was the single
  source of routing truth). The W4.4 spike verifies the new contract
  is workable.
- **Drift detector extension needed.** R3 (vault_write sole-writer for
  children) and R6 (algorithm constants in JSON) both require drift
  detector extensions at W4.4 / W4.7 ship. This is on the critical
  path; W4.7 cannot slip without blocking R3 enforcement.
- **No shipped prototype.** The spike is W4.4.1; until then, the S1-S5
  contracts are architectural-only. This ADR is therefore ACCEPTABLE
  as a draft but RISKY to implement without spike validation first.
  Per Diag 04 risk flag, the spike MUST be the first W4.4 task.

### Neutral

- **Manifest extension is optional.** v1 manifest (single
  `entry_point`) ships unchanged. v2 manifest (with `sub_agents:`) is
  a backward-compatible extension; existing skills continue to work.
- **Sub-agent NODES are not new nodes.** Sub-agents reuse existing
  `NODES` (`graph.py:83-94`). They are NOT a separate "sub-agent
  taxonomy." This keeps the graph topology simple.
- **Checkpoint DB location.** Parent and children share the same
  SqliteSaver DB at `<project_root>/data/ikigai_checkpoints.db`
  (per `graph.py:240-242`). ADR-027 may decide to shard; not this
  ADR's concern.

---

## Alternatives Considered

### Alt A — Direct parent-to-child invocation (no dispatcher node)

Each spawning parent node (`decompose`, `plan`, `reflect`) directly
invokes the child graph via `make_v2_graph().invoke(...)` without a
dedicated dispatcher.

- **Rejected:** scatters planner-only / vault_write / 4-part UEID
  enforcement across `len(NODES)` sites. Drift detection becomes
  intractable. Single dispatch surface (R1) is the better tradeoff.

### Alt B — Out-of-process sub-agents (separate Python processes)

Each sub-agent runs in its own Python process (subprocess or actor
model); communicates via IPC or filesystem queue.

- **Rejected:** violates "fully local" / "single-process where possible"
  invariant. Adds complexity (IPC, serialization, lifecycle management)
  for no architectural benefit. In-process LangGraph sub-invocation
  is the right boundary for in-process planner-only work.

### Alt C — LLM-driven dispatcher (LLM picks sub-agents at runtime)

The dispatcher node is itself an LLM call that decides which
sub-agents to spawn based on parent state.

- **Rejected:** violates ADR-013 planner-only for dispatch logic.
  Dispatch must be **deterministic** (ADR-019 build order: algorithms
  LAST). LLM-driven dispatch is a v2+ candidate once a baseline
  deterministic protocol is shipped and SONHO-log-evidence justifies
  the change.

### Alt D — Shared mutable state (no defensive copy)

Children receive a reference to parent's `IKIGAiStateDict` and mutate
it directly.

- **Rejected:** silently violates ADR-013 planner-only. A child that
  mutates parent's `error_type` field would route the parent to
  `error_node` without parent consent. Defensive copy (S2) is the
  mechanical enforcement.

### Alt E — Async-only (mandatory asyncio)

Sub-agents run only via `await graph.ainvoke(...)`; no sync path.

- **Rejected:** breaks the existing sync invocation surface
  (`v2.py:241` `compiled.invoke({})`). Async-or-sync is the right
  tradeoff: LangGraph supports both; the dispatcher wraps both.

### Alt F — Per-child checkpoint DB (separate SQLite file per child)

Each sub-agent gets its own `ikigai_checkpoints_<sub_agent_id>.db`.

- **Rejected:** scatters checkpoint state; complicates debugging; no
  performance benefit at typical fan-out (3-5 children). ADR-027 may
  revisit if shard-by-fork becomes necessary.

---

## Forward Dependencies

This ADR is one of **three** Wave 4 ADRs that gate the W4.4-W4.7
implementation work. The other two are:

- **ADR-027 — Stateful subgraph strategy** (Wave 4 W4.2, 16-20h,
  B-N11) — locks the SqliteSaver checkpoint schema for parent +
  child rows. **This ADR's S2 (context propagation) and S3
  (collection contract) reference ADR-027's schema but do not
  pre-empt it.** When ADR-027 ships, ADR-026's R-Ref-ADR-027
  cross-reference updates with the canonical schema citations.
- **ADR-028 — Memory layer across cycles** (Wave 4 W4.3, 8-12h, B-N12)
  — specifies cross-cycle memory persistence. Out of scope for
  ADR-026 (which is intra-cycle, parent ↔ child only).

Per `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §2, the
recommended write order is: ADR-027 (stateful subgraph) → ADR-026
(this) → ADR-028 (memory layer). **ADR-026 ships first per PLAN §3
dispatch order; its checkpoint-schema assumption is explicitly TBD
and references ADR-027.**

---

## References

### Load-bearing prior ADRs

- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) —
  sub-agent dispatcher enforces planner-only (R2). Math execution
  in sub-agents is FORBIDDEN per ADR-013 §"Drift Detector."
- **ADR-014 — UEID canonical format (4-part)** (Accepted 2026-09-04) —
  sub-agent dispatcher propagates 4-part UEIDs only (R4).
- **ADR-025 — Skill binding mechanism** (Accepted 2026-09-04, R2
  amended) — sub-agent dispatch extends ADR-025's manifest binding
  with optional `sub_agents:` field (planned v2 manifest).
- **ADR-012 — vault_write sole vault writer** (Accepted 2026-08-30) —
  sub-agents MUST use `vault_write(actor="agent")`; never bypass
  via direct filesystem I/O (R3).
- **ADR-019 — QHE → prompt-template constants** (Proposed 2026-09-04
  per W3.2 ship) — sub-agent dispatcher reads tuning values from
  `algorithm_constants.json` only (R6).

### Code references

- `src/ikigai/src/agents/v2/graph.py:83-94` — `NODES` tuple
  (sub-agent `entry_point` values MUST be in this set)
- `src/ikigai/src/agents/v2/graph.py:102-123` — `_safe_node` wrapper
  (child failures populate `error_type` per node)
- `src/ikigai/src/agents/v2/graph.py:215-243` — `make_v2_graph`
  factory (sub-agents call `make_v2_graph(entry_point=...)`)
- `src/ikigai/src/agents/v2/state.py:115-198` — `IKIGAiStateDict`
  (the narrowed slice source)
- `src/ikigai/src/agents/v2/state.py:118-122` — required identity
  fields (always propagated to children per S2.2)
- `src/ikigai/src/agents/v2/state.py:156-162` — operator.add reducers
  (free parallel-append semantics for `append` merge strategy)
- `src/ikigai/src/agents/v2/state.py:189-190` — `actor` field (injected
  by dispatcher per S2.3)
- `src/ikigai/src/agents/v2/state.py:191` — `persisted` field (set
  by `tag_and_persist` after `vault_write` success)
- `interfaces/cli/v2.py:160-215` — `invoke_skill` loader (the
  precedent for dispatcher pattern: read manifest, call
  `make_v2_graph`, post-process)
- `interfaces/cli/_skill_outputs.py` — W3.6 post-processor (the
  pattern for dispatcher-style post-processing of graph results)
- `src/ikigai/vault/vault_write.py:41-67` — `vault_write` signature
  with `actor` parameter (R3 enforcement target)
- `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` —
  tuning values live here (R6)
- `src/ikigai/src/agents/v2/prompts/load_constants.py` — loader
  for R6 enforcement

### Drift detector references

- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_hardcoded_entry_points_*` (drift invariant k, ADR-025 R4)
- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_algorithm_constants_in_agent_code` (drift invariant l,
  ADR-019 R7) — extends to dispatcher module at W4.4 ship
- **W4.7 — new drift invariant (m) for vault_write sole-writer
  enforcement on sub-agents** (planned, this ADR's R3)

### Roadmap / spec references

- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §2 — lists
  ADR-015 → ADR-026 (renumbered) as one of 6 new ADRs needed for
  Wave 4 Scenario B
- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §8 step 3 —
  recommended write order (ADR-027 first; ADR-026 ships first per
  PLAN §3 dispatch order with explicit TBD on checkpoint schema)
- `docs/superpowers/specs/2026-09-04-dcode-harness-PLAN.md` §3 —
  W4.1 task spec (this ADR)
- `docs/superpowers/specs/2026-09-04-dcode-harness-TASKS.md` — W4.1
  acceptance criteria (lifecycle, failure modes, prototype reference,
  user review)
- `docs/superpowers/specs/2026-09-04-diag-04-backend-tasks.md` —
  Diag 04 risk flag on no-shipped-prototype

### Memory references

- `memory/master-branch-carro-chefe-2026-08-28` — canonical master
  branch direction (sub-agent dispatch lives in `src/agents/` not
  `src/operational/` or `archive/`)
- `memory/algorithm-scope-reframed-2026-08-30` — IKIGAI = planner
  with stochastic PAE feedback; sub-agents follow same model
- `memory/algo-strip-agent-layer-complete-2026-08-31` — agent layer
  stripped of algo execution; sub-agents inherit this constraint
- `memory/algorithm-gate-dropped-2026-09-03` — algorithm work
  allowed on explicit demand; R6 JSON-edit pattern aligns
- `memory/feedback-precision-calibration-2026-08-28` — when user
  pushes back on X, apply correction NARROWLY (X-not-X), not
  opposite extreme; this ADR's "sub-agents MUST be planner-only"
  follows the same pattern (narrow R2, do not over-enforce)

### Wave 3 ship context

- Wave 3 SHIP-COMPLETE on commit `be9a370` (2026-09-04)
- 8/8 tasks shipped: W3.1, W3.2, W3.3, W3.4, W3.5, W3.6, W3.7, W3.8
- Drift detector 24/24 PASS
- Ruff clean on all Wave 3 files
- ADR-025 R2 amended 2026-09-04 to reflect shipped
  (weekly/monthly/quarterly = `observe` + `actor: agent`)
- W4 Wave 3 → Wave 4 transition brief at
  `.git/sdd/w41-adr-026-sub-agent-dispatch-brief.md`

---

*ADR-026 — DRAFT 2026-09-04 — Wave 4 W4.1 — gates W4.4 implementation — user review pending*
