# ADR-027 — Stateful Subgraph Checkpoint Schema

> **Status:** ACCEPTED (2026-09-05) — promoted from DRAFT after W4.5 implementation REVIEWER APPROVED (`693efe7`)
> **Deciders:** matheus (project owner)
> **Load-bearing:** YES — locks the SqliteSaver checkpoint schema consumed by ADR-026 (sub-agent dispatch, DRAFT `3cc9799`) and inherited by ADR-028 (memory layer, W4.3 next); gates W4.5 (stateful subgraph consumer, B-N11, 12-16h) and W4.4 (sub-agent dispatch node, B-N10, 12-16h)
> **Supersedes:** none (new decision)
> **Renumbered from:** PLAN §3 "ADR-016 (write first)" — user decision 2026-09-04 ("Renumber to 026+") overrides PLAN numbering; this ADR ships as **ADR-027**
> **Wave:** dcode-harness roadmap Wave 4 (W4.2)
> **Wave 3 context:** Wave 3 SHIP-COMPLETE on commit `be9a370` (2026-09-04, M-1 ruff cleanup); 8/8 tasks shipped, drift detector 24/24 PASS, ruff clean; W4.1 ADR-026 DRAFT at `3cc9799`; this ADR closes the TBD that ADR-026 line 10 noted ("checkpoint schema is TBD per forward dependency")

---

## Length Note

This ADR exceeds the 500-line guideline (`CLAUDE.md` §"Build & Test") by
~40%. Justification: schema locks are the most consequential Wave 4
artifact (they bind W4.4 dispatch, W4.5 consumer, W4.7 drift invariants,
and ADR-028 memory layer); ADR-026 (572 lines) is accepted precedent
for an architectural-locking ADR with similar consumer count; compressing
schema tables would force implementers to re-derive field
classifications. Pre-existing convention set by ADR-026: load-bearing
ADRs may exceed 500 lines with justification. No auto-split recommended.

---

## Context

Wave 3 of the dcode-harness roadmap shipped the v2 graph (10 nodes
including `error_node`, `NODES` tuple at `graph.py:83-94`) bound to 4
IKIGAI skills via the YAML manifest mechanism (ADR-025). The graph
factory `make_v2_graph(checkpoint_db=..., entry_point=...)` at
`graph.py:215-243` wires SqliteSaver with
`sqlite3.connect(checkpoint_db, check_same_thread=False)` and compiles
the StateGraph. Persistence is implicit — LangGraph writes checkpoint
rows to the SQLite file, but the **schema** of those rows (which
`IKIGAiStateDict` fields persist, which are ephemeral, which are
visible across cycles) is not formalized anywhere.

Wave 4 Scenario B (Sub-agents + stateful subgraphs, 32-44h) requires
the parent graph to **fork**: at certain nodes (`decompose`, `plan`,
`reflect`) the parent must spawn child sub-agents that run in parallel
with a narrowed context (per ADR-026 S2), then collect outputs (S3)
and merge back. This creates three new persistence requirements:

1. **Sub-agent rows.** Each spawned sub-agent must have its own
   checkpoint row (parent + N child rows). The dispatcher must
   differentiate parent rows from child rows without parsing JSON.
2. **Cross-cycle visibility.** Weekly reads daily's outputs; monthly
   reads weekly; quarterly reads monthly. Without a stable join key
   the cross-cycle query is unbounded. The checkpoint schema must
   encode the cross-cycle join.
3. **Vault-write attribution.** Every `vault_write` call within a
   cycle must be reconstructable from the checkpoint (per ADR-012
   sole-writer audit log + ADR-025 R3 actor tagging). Without
   persisted `vault_writes_log`, the audit trail is locked to the
   `.vault_audit.log` file (which is append-only and not included in
   the checkpoint).

ADR-026 (DRAFT, just shipped `3cc9799`) consumes this schema but
defers its definition to this ADR (line 10: "checkpoint schema is TBD
per forward dependency"). ADR-028 (memory layer, W4.3) will inherit
the schema fields verbatim and add cross-cycle memory persistence.

This ADR formalizes the checkpoint schema. It is **architectural
decision only** — implementation ships in W4.5 (stateful subgraph
consumer, B-N11, 12-16h).

---

## Decision

**The IKIGAi v2 checkpoint schema is a versioned SQLite table
`ikigai_checkpoints` with one row per LangGraph checkpoint; the row
encodes the **entire** `IKIGAiStateDict` (serialized JSON) plus three
schema-control fields (`schema_version`, `thread_role`,
`vault_writes_log`). All checkpoint tuning constants live in
`prompts/algorithm_constants.json` per ADR-019.**

The schema has 4 parts (R1-R4), 7 rules (R5-R11), and a 5-axis
classification for every `IKIGAiStateDict` field
(persistence / cross-cycle visibility / actor / audit-trail /
node-mutability).

### R1 — Checkpoint table schema (SQLite)

```sql
CREATE TABLE IF NOT EXISTS ikigai_checkpoints (
    -- LangGraph SqliteSaver-managed columns (DO NOT EDIT)
    thread_id    TEXT NOT NULL,            -- per R5 thread-id strategy
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type         TEXT,                     -- e.g. 'msgpack' or 'json'
    checkpoint   BLOB NOT NULL,            -- serialized IKIGAiStateDict (JSON)
    metadata     BLOB,                     -- LangGraph metadata (json)
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Schema-control table (this ADR owns these rows; SqliteSaver does not touch them)
CREATE TABLE IF NOT EXISTS ikigai_schema_registry (
    schema_version INTEGER PRIMARY KEY,    -- monotonic, never reused
    description    TEXT NOT NULL,
    applied_at     TEXT NOT NULL           -- ISO 8601 UTC
);

-- ADR-027 R3: per-row metadata for parent/child discrimination
CREATE TABLE IF NOT EXISTS ikigai_subgraph_links (
    parent_thread_id TEXT NOT NULL,
    parent_checkpoint_id TEXT NOT NULL,
    child_thread_id  TEXT NOT NULL,
    child_checkpoint_id  TEXT NOT NULL,
    created_at       TEXT NOT NULL,        -- ISO 8601 UTC
    sub_agent_id     TEXT,                 -- SubAgentSpec.sub_agent_id (ADR-026 S1)
    PRIMARY KEY (parent_thread_id, parent_checkpoint_id, child_thread_id, child_checkpoint_id)
);
CREATE INDEX IF NOT EXISTS idx_subgraph_links_child
    ON ikigai_subgraph_links(child_thread_id);
CREATE INDEX IF NOT EXISTS idx_subgraph_links_parent
    ON ikigai_subgraph_links(parent_thread_id);

-- ADR-027 R4: WAL mode + tuning constants loaded at graph init
PRAGMA journal_mode = WAL;                 -- R8
PRAGMA synchronous = NORMAL;               -- R8 (WAL mode safe default)
PRAGMA busy_timeout = 5000;                -- R8 (5s busy timeout)
PRAGMA foreign_keys = ON;                  -- referential integrity for ikigai_subgraph_links
```

The schema is **additive-only** across versions (R9). New columns may
be added by an ADR amendment; existing columns are never renamed or
dropped (append-only invariant per `CLAUDE.md` §"Refactor Protocol").

### R2 — Checkpoint payload shape (JSON serialization)

The `checkpoint` BLOB is a UTF-8 JSON object with **every**
`IKIGAiStateDict` field from `src/ikigai/src/agents/v2/state.py:115-198`:

```json
{
  "schema_version": 1,
  "thread_role": "parent" | "child" | "skill",
  "vault_writes_log": [...],
  "<every IKIGAiStateDict field by name>": "<JSON value or null>"
}
```

The three schema-control fields (`schema_version`, `thread_role`,
`vault_writes_log`) are JSON-prepended to the dict before
serialization. The remaining fields are written by `_safe_node`
wrappers as `state` updates flow through the graph (LangGraph
SqliteSaver semantics).

**Why every field:** SqliteSaver stores the full state dict per
checkpoint. Reconstructing a checkpoint requires the complete shape;
truncating fields would silently break replay. Persistence decisions
(R3-R5 below) determine which fields are **queried** or
**propagated**, not which are **stored**.

### R3 — Thread-id strategy (per-skill, hierarchical)

`thread_id` is a hierarchical string with **4 segments** (matches the
4-part UEID format from ADR-014; underscores replace colons since
LangGraph SqliteSaver treats thread_ids as opaque strings):

```
<actor>-<skill>-<cycle_id_short>-<sub_role>
```

| Segment | Values | Example |
|---------|--------|---------|
| `<actor>` | `user` \| `agent` \| `system` | `agent` |
| `<skill>` | `daily` \| `weekly` \| `monthly` \| `quarterly` \| `ad-hoc` | `weekly` |
| `<cycle_id_short>` | First 8 hex chars of `cycle_id` UUID | `a3f19c2d` |
| `<sub_role>` | `parent` \| `child-<sub_agent_id>` \| `skill` | `parent` |

**Example:** `agent-weekly-a3f19c2d-parent` (parent row of a weekly
cycle that started 2026-09-04 17:00 UTC, cycle_id=`a3f19c2d-...`)

**Example:** `agent-weekly-a3f19c2d-child-01HXY...` (a child
sub-agent spawned by the parent weekly cycle)

**Why hierarchical, not per-skill-per-cycle only:** per-skill-per-cycle
thread_ids are the LangGraph default and produce one row per cycle.
Wave 4's sub-agent dispatch (ADR-026) needs **N+1 rows per cycle**
(parent + children). Hierarchical thread_ids let queries reconstruct
the full fan-out from the `ikigai_subgraph_links` table (R3 table
above) without parsing JSON.

**Why 4 segments, not 2 or 6:** 2 segments collapse actor+skill info
(makes cross-skill audits impossible); 6 segments adds an unused
discriminator. 4 is the minimum that satisfies ADR-014 (4-part UEID
discipline applied to thread_ids) and ADR-025 (actor tagging).

### R4 — `vault_writes_log: list[VaultWriteRecord]`

Every `vault_write` call within a cycle appends a
`VaultWriteRecord` to the in-memory `IKIGAiStateDict` under
`vault_writes_log`. The schema is the canonical
`VaultWriteRecord` (defined in
`src/ikigai/src/ikigai/vault/vault_write.py` per ADR-026 fix):

```python
class VaultWriteRecord(TypedDict):
    vault_path: str             # relative path within vault/
    actor: Literal["user", "agent", "system"]
    timestamp: str              # ISO 8601 UTC
    sha256: str                 # sha256 of written body
    operation: Literal["create", "update", "delete"]  # always "create" for v1 mesh
```

Persisting `vault_writes_log` in the checkpoint allows **replay
without re-reading `.vault_audit.log`**. Replay semantics: given a
checkpoint row, the consumer can reconstruct the cycle's vault
mutations by iterating `vault_writes_log` and replaying each
`vault_write` call. The audit log file remains the **primary** audit
trail per ADR-012 §1; the checkpoint is a **cache** for replay.

The `vault_writes_log` field is **NOT** added to the static
`IKIGAiStateDict` TypedDict. Instead, it is appended dynamically by
the dispatcher (parent) and by each sub-agent (child) using the
existing `Annotated[list[X], operator.add]` reducer pattern (per
`state.py:156-162`). This means the schema spec does not change
`state.py`; it changes the **runtime contract** between nodes.

### R5 — Field classification (every IKIGAiStateDict field)

Every field in `IKIGAiStateDict` is classified on 5 axes:

| Axis | Values | Meaning |
|------|--------|---------|
| **Persistence** | `always` \| `full-cycle-only` \| `ephemeral` | When is the field stored? |
| **Cross-cycle** | `visible` \| `internal` | Visible to child cycles (weekly → daily)? |
| **Actor** | `user` \| `agent` \| `system` \| `n/a` | Who is the authoritative writer? |
| **Audit** | `vault_audit` \| `checkpoint_only` \| `none` | Does it appear in `.vault_audit.log`? |
| **Node-mutability** | `read-only` \| `append-only` \| `read-write` | Can a node mutate, append, or just read? |

The full classification table follows. Empty cell means the axis does
not apply (e.g., `ephemeral` fields are `internal` by definition and
have no audit trail).

#### R5.1 — Required identity fields (`state.py:118-122`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `cycle_id` | always | visible | system | none | read-only (set at graph init) |
| `cycle_start` | always | internal | system | none | read-only |
| `cycle_end` | always | internal | system | none | read-write (set by `commit`) |
| `iteration` | always | internal | system | none | read-write (incremented by `reflect`) |

**Rationale:** Identity fields are the join keys for cross-cycle
queries (per ADR-028). `cycle_id` is the canonical primary key.

#### R5.2 — Optional state (`state.py:124-125`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `last_step` | always | internal | agent | none | read-write (updated by every node via `_safe_node`) |

#### R5.3 — Regime FSM / Phase FSM (`state.py:128-138`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `regime_state` | full-cycle-only | visible | agent | none | read-write (`observe`) |
| `q_he_score` | full-cycle-only | internal | agent | none | read-write (`score_vectors`) |
| `days_in_regime` | full-cycle-only | internal | agent | none | read-write (`observe`) |
| `is_hysteresis_active` | full-cycle-only | internal | agent | none | read-write (`balance`) |
| `phase` | full-cycle-only | visible | agent | none | read-write (`observe`) |
| `phase_iteration` | full-cycle-only | internal | agent | none | read-write (`observe`) |
| `phase_converged` | full-cycle-only | internal | agent | none | read-write (`observe`) |
| `phase_weights` | full-cycle-only | internal | agent | none | read-write (`score_vectors`) |

**Rationale:** FSM state is per-cycle. Cross-cycle reads (e.g.,
weekly reads daily's `regime_state`) are needed for trend detection
(ADR-028). `q_he_score` is internal because it's an intermediate
calculation, not a contractually visible value.

#### R5.4 — IKIGAi 5-vector scores (`state.py:140-141`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `vector_scores` | full-cycle-only | visible | agent | none | read-write (`score_vectors`) |
| `meta_vector_score` | ephemeral | internal | agent | none | read-write (DEPRECATED per ADR-013 — never computed) |

**Rationale:** `vector_scores` is the canonical output of
`score_vectors`; downstream nodes (`heuristics`, `balance`) consume
it. Per ADR-013, `compute_meta_vector` is FORBIDDEN; the field exists
only for backward compatibility (typed-but-unused). Marking it
`ephemeral` signals "do not query" to implementers.

#### R5.5 — UEID hierarchy (`state.py:144-148`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `active_dream_ueid` | always | visible | agent | vault_audit | read-write (`plan`) |
| `active_goal_ueids` | always | visible | agent | vault_audit | append-only (`plan`) |
| `active_objective_ueids` | always | visible | agent | vault_audit | append-only (`plan`) |
| `active_project_ueids` | always | visible | agent | vault_audit | append-only (`plan`) |
| `active_task_ueids` | always | visible | agent | vault_audit | append-only (`plan`) |

**Rationale:** UEIDs are the canonical join keys across all forks
(per ADR-014, 4-part regex enforced). They MUST persist across cycles
and across forks. They MUST be 4-part format (drift detector
enforces; 5-part REJECTED).

#### R5.6 — Balancer (`state.py:151-153`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `workload_estimate` | full-cycle-only | visible | agent | none | read-write (`balance`) |
| `capacity_estimate` | full-cycle-only | internal | agent | none | read-write (`balance`) |
| `balancer_verdict` | full-cycle-only | visible | agent | none | read-write (`balance`) |

**Rationale:** Balancer output drives commit edge guard (`OK` /
`OVERLOAD` / `UNDERLOAD` / `RECOVER`). Cross-cycle visibility
enables trend detection (weekly reads daily's `balancer_verdict`).

#### R5.7 — Reducer-annotated fields (`state.py:156-162`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `prospective_buffer` | always | visible | agent | vault_audit | append-only (operator.add) |
| `retrospective_log` | always | visible | agent | vault_audit | append-only (operator.add) |
| `corrections` | always | visible | agent | vault_audit | append-only (operator.add) |

**Rationale:** These use LangGraph's `Annotated[list[X],
operator.add]` reducer (free parallel-append semantics per ADR-026
S3 `append` merge strategy). Per Cycle invariant: append-only across
the whole cycle; never truncate. Cross-cycle visibility is critical
for trend reports (weekly reads daily's
`prospective_buffer`+`retrospective_log`).

#### R5.8 — Kill switch (`state.py:165-166`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `kill_switch_triggered` | ephemeral | internal | user | none | read-write (any node) |
| `terminated` | ephemeral | internal | system | none | read-write (any node) |

**Rationale:** Kill switch is per-invocation; persistent state would
let a prior cycle's kill persist into a new cycle (catastrophic).
Both fields are cleared at graph init.

#### R5.9 — Error channel (`state.py:169-174`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `originating_node` | full-cycle-only | internal | system | none | read-write (`_safe_node`) |
| `error_type` | full-cycle-only | internal | system | none | read-write (`_safe_node`) |
| `error_message` | full-cycle-only | internal | system | none | read-write (`_safe_node`) |
| `traceback_str` | full-cycle-only | internal | system | none | read-write (`_safe_node`) |
| `error_traceback` | full-cycle-only | internal | system | none | read-write (`_safe_node`) |
| `commit_summary` | full-cycle-only | visible | agent | none | read-write (`commit` / `error`) |

**Rationale:** Error channel is internal to the cycle per ADR-026
S2.4 ("NEVER propagate to child"). `commit_summary` is the
**terminal** output that downstream consumers (CLI, post-processor)
inspect; it is `visible` so cross-cycle reports can summarize what
happened (e.g., "weekly cycle failed at `commit` with `commit_summary
= 'OVERLOAD'`"). Per ADR-026 S5, parent `error_type` is NEVER set by
child failures — child errors live in `sub_agent_results` (R5.13
below), not in the parent's error channel.

#### R5.10 — Chat mode (`state.py:177-178`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `messages` | always | visible | user | none | append-only (operator.add) |
| `user_input` | ephemeral | internal | user | none | read-write (graph init) |

**Rationale:** Chat messages are the conversation history; they
persist across cycles for context continuity. `user_input` is the
current turn only; cleared after `commit` consumes it.

#### R5.11 — Plan A Task 8 (`state.py:187-190`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `proposed_entity` | full-cycle-only | internal | agent | vault_audit | read-write (`plan`) |
| `vault_path` | full-cycle-only | internal | agent | vault_audit | read-write (`plan`) |
| `actor` | always | visible | agent | vault_audit | read-only (set at graph init per ADR-025 R3) |
| `persisted` | full-cycle-only | internal | system | none | read-write (`tag_and_persist`) |

**Rationale:** `proposed_entity` is the Pydantic v2 contract to be
persisted (per Plan A spec); `vault_path` is its destination;
`persisted=True` is set by `tag_and_persist` after a successful
`vault_write`. The `actor` field is the **runtime** actor tag (per
ADR-025 R3); it persists across cycles because it determines
downstream audit-log filtering. Plan A's `actor` is **separate**
from `vault_writes_log[i].actor` — the former is the cycle-level
actor, the latter is per-write.

#### R5.12 — Surface intentions (`state.py:195-197`)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `user_suggestions` | ephemeral | internal | agent | none | read-write (`surface_intentions`) |
| `suggestions_count` | ephemeral | internal | agent | none | read-write (`surface_intentions`) |
| `suggestions_language` | ephemeral | internal | agent | none | read-write (`surface_intentions`) |

**Rationale:** `surface_intentions` is W3.5's terminal node for
`daily` skill (actor=user). Suggestions are shown to the user and
discarded. Daily cycle has no follow-up; no need to persist.

#### R5.13 — Sub-agent results (ADR-026 S3 schema, NEW)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `sub_agent_results` | full-cycle-only | internal | agent | checkpoint_only | append-only (operator.add, new reducer) |
| `dispatch_plan` | ephemeral | internal | agent | checkpoint_only | read-write (`dispatch_sub_agents`, cleared after use) |

**Rationale:** `sub_agent_results` is appended by the dispatcher
after each child terminates (per ADR-026 S3). It is
`checkpoint_only` (not `vault_audit`) because sub-agent state is
internal orchestration detail, not a user-visible mutation. The
`dispatch_plan` is ephemeral (single-use per parent cycle).

#### R5.14 — Schema-control fields (NEW, this ADR)

| Field | Persistence | Cross-cycle | Actor | Audit | Node-mutability |
|-------|-------------|-------------|-------|-------|-----------------|
| `schema_version` | always | internal | system | none | read-only (set at graph init) |
| `thread_role` | always | internal | system | none | read-only (set at graph init per R3) |
| `vault_writes_log` | always | internal | agent | checkpoint_only | append-only (operator.add, new reducer) |

**Rationale:** `schema_version` is for migration (R9). `thread_role`
discriminates parent / child / skill rows. `vault_writes_log` is
defined in R4 above.

### R6 — Cross-cycle state passing (concrete data flow)

Cycle handoffs are **queries**, not row mutations. The consumer
queries the checkpoint DB by `cycle_id` + skill; the producer's row
is read-only.

```
Daily cycle (parent thread_id="agent-daily-a3f19c2d-parent")
  ↓
  writes: cycle_id, active_*_ueids, balancer_verdict, prospective_buffer,
          retrospective_log, corrections, messages, commit_summary
  ↓
Weekly cycle (parent thread_id="agent-weekly-<weekly_cycle_id_short>-parent")
  ↓
  READS daily's row by daily's cycle_id (join via active_*_ueids)
  USES: trends in balancer_verdict, prospective_buffer append,
        retrospective_log append, corrections merge
  ↓
Monthly → Quarterly follows the same pattern
```

**Implementation:** ADR-028 (memory layer, W4.3) defines the
querying API. This ADR locks the **schema**; ADR-028 implements the
**read patterns**.

### R7 — Ephemeral vs persistent classification summary

| Category | Fields | Reset behavior |
|----------|--------|----------------|
| **Ephemeral** (cleared at graph init) | `kill_switch_triggered`, `terminated`, `user_input`, `user_suggestions`, `suggestions_count`, `suggestions_language`, `meta_vector_score`, `dispatch_plan` | Reset to `None`/`False`/empty at every graph invocation |
| **Full-cycle-only** (persists within cycle, visible in rows but not propagated) | Regime/Phase FSM, Balancer output, `originating_node`, `error_*`, `proposed_entity`, `vault_path`, `persisted`, `sub_agent_results` | Persisted for the cycle's lifetime; not visible to child cycles |
| **Always-persistent** (persists across cycles) | `cycle_id`, `cycle_start`, `cycle_end`, `iteration`, `last_step`, UEID hierarchy, reducer-annotated fields (`prospective_buffer`, `retrospective_log`, `corrections`, `messages`), `actor`, schema-control fields | Persisted forever (subject to R10 retention) |

### R8 — WAL mode + thread safety

SqliteSaver connections use `sqlite3.connect(checkpoint_db,
check_same_thread=False)` per the existing `make_v2_graph` factory
(`graph.py:332`). The following PRAGMAs MUST be set on connection:

| PRAGMA | Value | Rationale |
|--------|-------|-----------|
| `journal_mode` | `WAL` | Concurrent readers + 1 writer; required for parallel sub-agent dispatch |
| `synchronous` | `NORMAL` | WAL-mode safe default; full sync would defeat WAL's throughput |
| `busy_timeout` | `5000` | 5s wait on contended writers (sub-agent fan-out) |
| `foreign_keys` | `ON` | Referential integrity for `ikigai_subgraph_links` |

These are set inside `make_v2_graph` immediately after the
`sqlite3.connect()` call (after `graph.py:332` line, before
`SqliteSaver(conn)` at `graph.py:333`). Drift invariant (n) at W4.7
ship will verify these PRAGMAs are present (R11).

### R9 — Schema versioning + migration story

`schema_version` is **monotonic, never reused**. The current version
is **1** (set by this ADR). Future versions:

- **Backward-compatible additions** (e.g., a new field added to
  `IKIGAiStateDict`) → `schema_version` STAYS AT 1; the new field is
  `NotRequired` in the TypedDict and omitted from older checkpoint
  rows. Old code reading new rows skips the unknown field. **No
  migration needed.**
- **Breaking changes** (rename, drop, type change) → `schema_version`
  INCREMENTS to 2. A migration function `_migrate_v1_to_v2(row)`
  reads v1 JSON, transforms to v2 shape, writes back. Migration
  functions live in `src/ikigai/src/agents/v2/checkpoint_migrations.py`
  (new file, W4.5). Migration runs **on read** (lazy); migration
  writes a new row, keeping the old row for audit.

The `ikigai_schema_registry` table records the version transition
history:

```sql
INSERT INTO ikigai_schema_registry (schema_version, description, applied_at)
VALUES (1, 'Initial schema (W4.2 ADR-027)', '2026-09-04T17:00:00Z');
```

### R10 — Checkpoint retention

Two tuning constants are added to `prompts/algorithm_constants.json`
(per ADR-019, JSON is single source of truth):

| Key | Default | Meaning |
|-----|---------|---------|
| `CHECKPOINT_RETENTION_COUNT` | 1000 | Max checkpoints per `(actor, skill)` tuple. Older rows are pruned by a daily job. |
| `MAX_CHECKPOINT_AGE_DAYS` | 90 | Max age of a checkpoint row. Older rows are pruned. |
| `SUBAGENT_PARENT_TIMEOUT_S` | 60.0 | Wall-clock budget for a child sub-agent before timeout (ADR-026 S4). |
| `SUBAGENT_MAX_FAN_OUT` | 5 | Max children a parent may spawn per dispatch (ADR-026 S6 anti-pathological). |
| `SUBAGENT_CHECKPOINT_KEEP_AFTER_REPLAY` | true | Whether child checkpoint rows persist after parent completes (true = audit; false = prune-on-replay). |

Drift detector's `test_no_algorithm_constants_in_agent_code`
invariant (l) extends to cover these 5 new keys (per ADR-019 R7, this
invariant already scans for `DEFAULT_*` / `HYSTERESIS_*` patterns; W4.7
extends it to scan for the 5 new keys' absence from `.py` files).

### R11 — Failure mode behavior

| Failure | Detection | Recovery |
|---------|-----------|----------|
| **Corrupt checkpoint DB** (SQLite header corruption) | `sqlite3.connect()` raises `sqlite3.DatabaseError` | `make_v2_graph` raises with explicit message; user runs `make_v2_graph(checkpoint_db=...)` against a fresh DB at `<root>/data/ikigai_checkpoints.db.bak-<timestamp>`. Old DB is archived (never deleted; append-only). |
| **Missing checkpoint DB** (fresh clone) | `_CONSTANTS_PATH.exists()` equivalent check; PRAGMA `journal_mode=WAL` on a fresh file is no-op | Default location `<root>/data/ikigai_checkpoints.db` is auto-created at graph init (`graph.py:245`: `Path(checkpoint_db).parent.mkdir(parents=True, exist_ok=True)`). New DB starts at `schema_version=1`. |
| **Schema version mismatch** (old code reading new row) | `schema_version > max_known_version` triggers migration loader | Migration loader (`checkpoint_migrations.py`) reads `schema_version`, applies oldest-first migrations until version matches code's `SCHEMA_VERSION` constant. |
| **Schema version mismatch** (new code reading old row) | `schema_version < SCHEMA_VERSION` triggers migration | Same: oldest-first migrations. Migration writes a new row, keeps the old. |
| **Disk full** (write fails) | `sqlite3.connect().execute()` raises `sqlite3.OperationalError: disk full` | `make_v2_graph` propagates the exception; the calling CLI / sub-agent logs the failure. The cycle is **NOT** retried automatically (per ADR-013 deterministic pipelines). User must free disk and re-invoke. |
| **Stale child row** (parent pruned but child remains) | `ikigai_subgraph_links` `parent_thread_id` not found in `ikigai_checkpoints` | Stale-link cleanup job (W4.5 implementation) deletes rows whose parent is gone. Runs daily. |
| **Concurrent writer contention** (two skills writing simultaneously) | `sqlite3.OperationalError: database is locked` | `busy_timeout=5000` retries for 5s. After timeout, raises. Caller (`invoke_skill` or dispatcher) logs + emits a TaskChange to `data/review_queue/` (per Wave 3 partial-success invariant). |

### R12 — Cross-ADR consistency

| ADR | Field | This ADR's relationship |
|-----|-------|-------------------------|
| ADR-013 | planner-only | ✅ Schema stores planner state, not computed values (R5) |
| ADR-014 | UEID 4-part | ✅ All UEID fields validated as 4-part (R5.5) |
| ADR-025 | actor tagging | ✅ `actor` field per checkpoint (R5.11) |
| ADR-012 | vault_write sole writer | ✅ `vault_writes_log` reconstructs cycle mutations (R4) |
| ADR-019 | algorithm constants JSON | ✅ 5 new keys added to JSON (R10) |
| ADR-026 | sub-agent dispatch | ✅ `thread_role` + `ikigai_subgraph_links` (R1, R5.13) |

### R13 — Implementation deliverables (W4.5)

This ADR does NOT ship code. W4.5 (B-N11, 12-16h) implements:

1. **`src/ikigai/src/agents/v2/checkpoint_schema.py`** (new file)
   - Exports `CHECKPOINT_SCHEMA_VERSION = 1`
   - Exports `THREAD_ROLE_LITERAL = Literal["parent", "child", "skill"]`
   - Exports `VaultWriteRecord` TypedDict (alias of canonical)
2. **`src/ikigai/src/agents/v2/checkpoint_migrations.py`** (new file)
   - `_migrate_v1_to_v2(row: dict) -> dict` stub (raises
     `NotImplementedError` until v2 ships)
   - `apply_migrations(row: dict, target_version: int) -> dict`
3. **Modify `src/ikigai/src/agents/v2/graph.py:332`** — add 4 PRAGMA
   calls after `sqlite3.connect(...)` (R8).
4. **Add 5 keys to `prompts/algorithm_constants.json`** (R10) +
   defensive defaults in `load_constants.py`.
5. **Drift invariant (n) in
   `src/ikigai/tests/test_canonical_scope.py`** — verify the 4 PRAGMAs
   are present after `sqlite3.connect()` (R8) + the 5 new JSON keys
   are NOT in any `.py` file (R10).

---

## Rationale

1. **Single dispatch surface (architectural foundation).** This ADR
   is the **load-bearing** Wave 4 artifact. It binds:
   - **W4.4** (B-N10 sub-agent dispatch node) — dispatcher must
     populate `thread_role` per row (R1, R5.14) and write to
     `ikigai_subgraph_links` (R1 table).
   - **W4.5** (B-N11 stateful subgraph consumer) — implements R1-R11.
   - **W4.7** (drift invariants) — adds invariant (n) for PRAGMAs +
     JSON-key absence.
   - **ADR-028** (memory layer, W4.3) — inherits R5.5, R5.6, R5.7,
     R5.11 as the cross-cycle join keys.

   Without locking the schema here, **each** downstream implementer
   would re-derive field classifications, creating the 2-source drift
   that ADR-013 forbids.

2. **Hierarchical thread_id encodes actor + skill + cycle + role.**
   ADR-026 S2 injects `actor="agent"` into every sub-agent's initial
   state; ADR-025 R3 ensures `vault_write` is called with
   `actor=manifest["actor"]`. The hierarchical thread_id makes
   these values queryable from the SQLite file directly without
   parsing the JSON `checkpoint` BLOB. This is the cheapest possible
   audit-log query (an `INDEX` on the first segment of thread_id).

3. **Append-only invariant extends to checkpoints.** Per `CLAUDE.md`
   §"Refactor Protocol" (`vault/`, `vibe-ops/`, `strategics/`), the
   project is append-only. This ADR's R9 schema versioning is
   append-only by construction: new versions add columns / rows,
   never rename or drop. Old rows persist for audit (per
   `append-only-invariant on data/review_queue/` from CLAUDE.md §
   "Pitfalls").

4. **WAL mode is the SqliteSaver-supported concurrency primitive.**
   Per `graph.py:332`, the existing factory uses
   `check_same_thread=False`, which already breaks Python's GIL
   guarantee. WAL mode is the **minimum** needed for sub-agent
   fan-out (parent + N children writing concurrently). Without WAL,
   every write serializes; typical fan-out (3-5 children) would
   deadlock or busy-timeout.

5. **Algorithm constants in JSON (per ADR-019).** 5 new keys land
   in `prompts/algorithm_constants.json` (R10). No Python
   `DEFAULT_*` constants. The drift detector's existing invariant
   (l) extends to scan for these keys' absence from `.py` files at
   W4.7 ship. This is the same pattern W3.2 used for the 14 QHE
   constants.

6. **vault_writes_log decouples replay from audit log.** Per
   ADR-012, `.vault_audit.log` is the primary audit trail. The
   checkpoint's `vault_writes_log` is a **replay cache**: it lets a
   consumer reconstruct cycle mutations by iterating the list. This
   is faster than re-reading the audit log (which is append-only
   JSONL across all cycles). The audit log remains authoritative
   for cross-cycle audits; the checkpoint is for single-cycle replay.

7. **Ephemeral vs persistent classification matches ADR-013
   planner-only.** Ephemeral fields are computation artifacts (kill
   switch, dispatch plan, current turn user_input). Persistent fields
   are user intent (UEID hierarchy, balancer verdict, prospective /
   retrospective logs). The classifier maps directly to the
   ADR-013 invariant: planner state persists; computation state does
   not.

---

## Implementation Rules Summary

**R1 — Checkpoint table schema** — R1 SQL above; SqliteSaver-managed
columns + schema-control tables; PRAGMAs at connection.

**R2 — JSON payload shape** — every IKIGAiStateDict field + 3
schema-control fields; serialised as UTF-8 JSON.

**R3 — Thread-id strategy** — hierarchical 4-segment string;
`actor-skill-cycle_short-sub_role`.

**R4 — vault_writes_log** — append-only list of `VaultWriteRecord` per
cycle; enables replay without audit-log re-read.

**R5 — Field classification** — 5-axis table for every
IKIGAiStateDict field (R5.1-R5.14).

**R6 — Cross-cycle state passing** — query-based handoffs (not row
mutation); ADR-028 implements.

**R7 — Ephemeral / full-cycle-only / always-persistent summary** —
reset behavior table.

**R8 — WAL mode + PRAGMAs** — `journal_mode=WAL`,
`synchronous=NORMAL`, `busy_timeout=5000`, `foreign_keys=ON`.

**R9 — Schema versioning** — monotonic, never reused; additive
backward-compat by default; lazy migration on read.

**R10 — Algorithm constants** — 5 new keys in
`prompts/algorithm_constants.json` (per ADR-019).

**R11 — Failure modes** — 7-row table covering corrupt / missing /
version-mismatch / disk-full / stale-link / contention.

**R12 — Cross-ADR consistency** — 6-row table mapping every
load-bearing ADR to a field.

**R13 — Implementation deliverables** — 5 W4.5 deliverables
(non-binding on this ADR's DRAFT status).

---

## Cross-ADR consistency check

- **vs ADR-026 (sub-agent dispatch, DRAFT `3cc9799`):** schema fields
  consumed by sub-agent dispatch ✓ — `thread_role` (R5.14) +
  `sub_agent_results` (R5.13) + `dispatch_plan` (R5.13) +
  `ikigai_subgraph_links` (R1) all map to ADR-026 S2/S3/S5 fields.
  ADR-026 forward-dependency TBD (line 10) is closed by this ADR.
- **vs ADR-019 (algorithm_constants.json, Proposed 2026-09-04):** no
  hardcoded constants ✓ — 5 new keys land in JSON (R10); drift
  detector (l) extends to cover them at W4.7 ship.
- **vs ADR-025 R2 (skill binding):** actor persisted per checkpoint ✓
  — `actor` field is `always`-persistent (R5.11); sub-agents inject
  `actor="agent"` per ADR-026 S2.3; daily injects `actor="user"` per
  ADR-025 R2 mapping.

---

## Consequences

### Positive

- **Locked schema unblocks W4.4 / W4.5 / W4.7 / ADR-028.** Every
  downstream Wave 4 task has a stable contract. Implementers do
  not need to re-litigate field classifications.
- **Audit-log replay is fast.** `vault_writes_log` is a per-cycle
  cache; replay avoids re-reading the cross-cycle JSONL audit log.
- **Hierarchical thread_id enables parent/child reconstruction.**
  The `ikigai_subgraph_links` table joins parent + N children
  without parsing JSON. Wave 4's fan-out is queryable.
- **Append-only invariant extends to checkpoints.** R9 versioning
  never drops or renames columns. Per `CLAUDE.md` §"Refactor
  Protocol," this matches project-wide convention.
- **WAL mode is the right concurrency primitive for sub-agent
  dispatch.** Per ADR-026 R6, parent + N children write
  concurrently; WAL mode + busy_timeout handle contention.
- **Algorithm tuning is JSON-only.** 5 new keys in
  `algorithm_constants.json` (per ADR-019); zero new Python
  constants.

### Negative

- **3 new schema-control tables** (`ikigai_schema_registry`,
  `ikigai_subgraph_links`, plus PRAGMAs at connection) add
  operational surface. Drift invariant (n) at W4.7 catches
  regressions.
- **5 new algorithm constants** extend the JSON SOT; the
  defensive-default in `load_constants.py` must mirror them
  exactly (per ADR-019 R6).
- **Schema versioning migration** adds a new file
  (`checkpoint_migrations.py`). W4.5 ships an empty migration
  registry + a stub `_migrate_v1_to_v2` (raises
  `NotImplementedError` until v2 ships).
- **Hierarchical thread_id breaks per-cycle-by-skill queryability**
  for older tooling that assumes `thread_id=skill-name`. Existing
  code (`interfaces/cli/v2.py:202` uses
  `thread_id=f"skill-{skill_name}"`) MUST migrate to the
  4-segment format at W4.5 ship. Pre-existing convention is
  superseded by this ADR.
- **vault_writes_log grows unbounded** within a cycle. R10's
  `CHECKPOINT_RETENTION_COUNT=1000` caps it indirectly (the parent
  row is pruned; child rows are pruned when their parent is
  pruned).

### Neutral

- **Schema-control tables are not part of LangGraph SqliteSaver
  semantics.** They are **application-managed** and only the W4.5
  implementation touches them. SqliteSaver is unaware of these
  tables; it only manages the `ikigai_checkpoints` table.
- **Schema-control fields (`schema_version`, `thread_role`,
  `vault_writes_log`) are JSON-prepended, not new
  `IKIGAiStateDict` TypedDict fields.** This keeps `state.py`
  unchanged (per `CLAUDE.md` §"Global Conventions" — minimal blast
  radius).
- **Per-cycle checkpoint DB is not sharded** (per ADR-026 Alt F
  rejection). All cycles share `<root>/data/ikigai_checkpoints.db`.
  ADR-027 may revisit if shard-by-fork becomes necessary.

---

## Alternatives Considered

### Alt A — Per-cycle SQLite file (one DB per cycle)

Each cycle gets its own `ikigai_checkpoints_<cycle_id>.db`. WAL mode +
atomic-rename guarantee isolation.

- **Rejected:** scatters checkpoint state across files; cross-cycle
  queries require opening N files; debugging is harder. One DB with
  the `cycle_id` indexed column is the better tradeoff.

### Alt B — LangGraph PostgresSaver (instead of SqliteSaver)

Use Postgres for production-grade concurrency + JSONB columns.

- **Rejected:** violates "fully local" invariant (per `CLAUDE.md`
  §"Global Conventions"). Single-user personal OS does not need
  Postgres. SqliteSaver with WAL mode is sufficient.

### Alt C — In-memory state only (no checkpoint DB)

Cycles are in-memory; no persistence across cycles.

- **Rejected:** breaks ADR-028 (memory layer) which requires
  cross-cycle queries. Breaks replay (a failed cycle cannot be
  re-driven from checkpoint).

### Alt D — Append JSONL file (not SQLite)

Each checkpoint row is appended to a JSONL file at
`data/ikigai_checkpoints.jsonl`.

- **Rejected:** no concurrency primitive (WAL); no index on
  `cycle_id` or `thread_id`; reads are O(N). SqliteSaver + WAL is
  strictly better.

### Alt E — Defer schema lock (status quo)

Continue with implicit SqliteSaver schema; each implementer
discovers it from LangGraph docs.

- **Rejected:** Wave 4's sub-agent dispatch needs the schema
  locked NOW (W4.4 cannot start without R1 + R5.13). Status quo
  is the exact drift ADR-013 forbids.

---

## Forward Dependencies

| Consumer | Field/section consumed | Status |
|----------|------------------------|--------|
| ADR-026 (sub-agent dispatch, DRAFT `3cc9799`) | R1 `ikigai_subgraph_links`, R3 thread-id, R5.13 sub-agent results | DRAFT, awaiting this ADR's accept |
| ADR-028 (memory layer, W4.3) | R5.5 (UEID hierarchy), R5.6 (balancer), R5.7 (reducers), R5.11 (`actor`) | next-wave, blocking on this ADR |
| W4.4 (sub-agent dispatch node, B-N10, 12-16h) | R1, R3, R5.13 | next, blocking on this ADR |
| W4.5 (stateful subgraph consumer, B-N11, 12-16h) | R1-R13 (entire ADR) | next, blocking on this ADR |
| W4.7 (drift invariants) | R8 PRAGMAs + R10 JSON keys → invariant (n) | next, blocking on this ADR |
| ADR-012 (vault_write sole writer) | R4 `vault_writes_log` | Accepted, this ADR locks the replay contract |

---

## References

### Load-bearing prior ADRs

- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) —
  R5 classification maps planner state to persistent, computation
  state to ephemeral.
- **ADR-014 — UEID canonical format (4-part)** (Accepted 2026-09-04) —
  R5.5 UEID hierarchy fields are validated as 4-part; drift detector
  enforces.
- **ADR-025 — Skill binding mechanism** (Accepted 2026-09-04, R2
  amended) — R5.11 `actor` field is the runtime actor tag (per ADR-025
  R3); sub-agents inject `actor="agent"` per ADR-026 S2.3.
- **ADR-012 — Fork-connection architecture** (Accepted 2026-08-30) —
  R4 `vault_writes_log` reconstructs cycle mutations without
  re-reading `.vault_audit.log`.
- **ADR-019 — QHE → prompt-template constants** (Proposed 2026-09-04
  per W3.2 ship) — R10 adds 5 new keys to `algorithm_constants.json`;
  drift detector (l) extends at W4.7 ship.
- **ADR-026 — Sub-agent dispatch protocol** (DRAFT 2026-09-04, `3cc9799`)
  — this ADR's R1/R3/R5.13 close ADR-026's TBD on checkpoint schema.

### Code references

- `src/ikigai/src/agents/v2/graph.py:83-94` — `NODES` tuple
- `src/ikigai/src/agents/v2/graph.py:102-123` — `_safe_node` wrapper
  (populates `originating_node`, `error_type`, `error_message`,
  `traceback_str`, `last_step`)
- `src/ikigai/src/agents/v2/graph.py:215-243` — `make_v2_graph`
  factory (SqliteSaver at line 333, `check_same_thread=False` at
  line 332)
- `src/ikigai/src/agents/v2/state.py:115-198` — `IKIGAiStateDict`
  TypedDict (every field classified in R5.1-R5.14)
- `src/ikigai/src/agents/v2/state.py:156-162` — operator.add reducers
  for `prospective_buffer`, `retrospective_log`, `corrections`
- `src/ikigai/src/agents/v2/state.py:189-190` — `actor` field
  (R5.11, ADR-025 R3)
- `src/ikigai/src/agents/v2/state.py:191` — `persisted` field
  (set by `tag_and_persist` after `vault_write`)
- `interfaces/cli/v2.py:160-215` — `invoke_skill` loader (existing
  `thread_id=f"skill-{skill_name}"` must migrate to R3 format at
  W4.5 ship)
- `interfaces/cli/v2.py:202` — current `thread_id` construction
  (superseded by this ADR's R3 hierarchical format)
- `interfaces/cli/_skill_outputs.py` — W3.6 post-processor pattern
- `src/ikigai/src/ikigai/vault/vault_write.py:41-67` —
  `vault_write(vault_root, vault_path, frontmatter_fields, body,
  actor=...)` signature (R4 canonical `VaultWriteRecord`)
- `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` —
  14 existing tuning values + 5 new keys (R10) at W4.5 ship
- `src/ikigai/src/agents/v2/prompts/load_constants.py` — loader
  with `_defensive_default()` mirroring JSON exactly (ADR-019 R6)

### Drift detector references

- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_hardcoded_entry_points_*` (drift invariant k, ADR-025 R4)
- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_algorithm_constants_in_agent_code` (drift invariant l,
  ADR-019 R7) — extends to cover 5 new JSON keys at W4.7 ship
- **W4.7 — new drift invariant (n) for WAL PRAGMAs + JSON-key
  absence** (planned, this ADR's R8 + R10)

### Roadmap / spec references

- `docs/superpowers/specs/2026-09-04-dcode-harness-PLAN.md` §3 —
  W4.2 task spec (this ADR)
- `docs/superpowers/specs/2026-09-04-dcode-harness-TASKS.md` —
  W4.2 acceptance criteria (lifecycle, failure modes, prototype
  reference, user review)
- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §2 — lists
  ADR-016 → ADR-027 (renumbered) as one of 6 new ADRs needed for
  Wave 4 Scenario B
- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §8 step 3 —
  recommended write order (ADR-027 first; ADR-026 ships first per
  PLAN §3 dispatch order with explicit TBD on checkpoint schema)

### Memory references

- `memory/wave-3-ship-complete-2026-09-04` — Wave 3 SHIP-COMPLETE
  on commit `be9a370`; drift 24/24 PASS; ruff clean; this ADR
  continues the load-bearing sequence
- `memory/master-branch-carro-chefe-2026-08-28` — canonical master
  branch direction (stateful subgraph lives in
  `src/ikigai/src/agents/v2/`, not `src/operational/` or
  `archive/`)
- `memory/algorithm-scope-reframed-2026-08-30` — IKIGAI = planner
  with stochastic PAE feedback; schema stores planner state only
- `memory/algo-strip-agent-layer-complete-2026-08-31` — agent
  layer stripped of algo execution; R5 classification reflects this
- `memory/algorithm-gate-dropped-2026-09-03` — algorithm work
  allowed on explicit demand; 5 new JSON keys land via W4.5
  ship-time
- `memory/feedback-precision-calibration-2026-08-28` — when user
  pushes back on X, apply correction NARROWLY (X-not-X), not
  opposite extreme; this ADR's "subgraphs are planner-only" follows
  the same pattern (R5 classification narrows persistence to
  planner-relevant fields, does not over-enforce)
- `memory/wave-3-ship-complete-2026-09-04` — confirms 8/8 Wave 3
  tasks shipped, this ADR is Wave 4 entry point

### Wave 3 ship context

- Wave 3 SHIP-COMPLETE on commit `be9a370` (2026-09-04)
- 8/8 tasks shipped: W3.1, W3.2, W3.3, W3.4, W3.5, W3.6, W3.7, W3.8
- Drift detector 24/24 PASS
- Ruff clean on all Wave 3 files
- ADR-025 R2 amended 2026-09-04 to reflect shipped
  (weekly/monthly/quarterly = `observe` + `actor: agent`)
- W4 Wave 3 → Wave 4 transition briefs at
  `.git/sdd/w41-adr-026-sub-agent-dispatch-brief.md` +
  `.git/sdd/w42-adr-027-stateful-subgraph-brief.md`

---

*ADR-027 — DRAFT 2026-09-04 — Wave 4 W4.2 — closes ADR-026 TBD — gates W4.4 / W4.5 / W4.7 / ADR-028 — user review pending*