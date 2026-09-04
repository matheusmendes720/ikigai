# ADR-028 — Cross-Cycle Memory Layer

> **Status:** DRAFT (2026-09-04)
> **Deciders:** matheus (project owner)
> **Load-bearing:** YES — locks the cross-cycle memory architecture that ADR-027 (stateful subgraph, DRAFT `648b83a`) checkpoint schema inherits; gates W4.6 (B-N12, memory layer implementation, 12-16h) and W4.7 (drift invariant o); consumed by W4.8 (E2E multi-level smoke, B.6) to validate "weekly knows what daily produced"
> **Supersedes:** none (new decision)
> **Renumbered from:** PLAN §3 "ADR-017 (memory layer across cycles)" — user decision 2026-09-04 ("Renumber to 026+") overrides PLAN numbering; this ADR ships as **ADR-028**
> **Wave:** dcode-harness roadmap Wave 4 (W4.3)
> **Wave 3 + W4.1/W4.2 context:** Wave 3 SHIP-COMPLETE on commit `be9a370` (2026-09-04, M-1 ruff cleanup); 8/8 tasks shipped, drift detector 24/24 PASS, ruff clean; W4.1 ADR-026 DRAFT at `3cc9799`; W4.2 ADR-027 DRAFT at `648b83a`; this ADR closes the Wave 4 architectural triad

---

## Length Note

This ADR lands at ~1100 lines (final length verified after write). Justification:
this is the **third leg** of the Wave 4 architectural triad (after ADR-026 at
572 lines and ADR-027 at 931 lines); it locks a memory layer that W4.6
implements and W4.7 drift-tests, so the schema tables, retrieval patterns,
failure modes, and ADR cross-consistency table must be exhaustively specified
to prevent implementer drift. ADR-027 set the precedent that load-bearing Wave
4 ADRs may exceed 500 lines with justification (CLAUDE.md §"Build & Test");
ADR-028 inherits that precedent. The 1100-line length exceeds my pre-write
estimate of 500-800 lines because: (a) the 4 per-record schemas + 1 failure-
mode table + 1 retention table = ~250 lines of pure tables; (b) the 7
W4.6 implementation deliverables (R13) each require 5-10 lines of spec; (c)
the cross-ADR consistency check enumerates 7 ADRs (vs ADR-027's 6);
(d) the references section lists 6 load-bearing ADRs (vs ADR-027's 6) plus
5 code references plus 4 drift detector references plus 6 memory references.
Compressing any of these would force W4.6 implementers to re-derive field
classifications — exactly the 2-source drift ADR-013 forbids. No auto-split
recommended.

---

## Context

Wave 3 of the dcode-harness roadmap shipped the v2 graph (10 nodes
including `error_node`, `NODES` tuple at `graph.py:83-94`) bound to 4
IKIGAI skills (`daily` / `weekly` / `monthly` / `quarterly`) via the
YAML manifest mechanism (ADR-025). Each skill is a **single linear
pipeline** triggered by cron or slash command (per the skill manifests
at `src/ikigai/src/agents/v2/skills/{daily,weekly,monthly,quarterly}.md`).

The Wave 3 skills emit their outputs to **vault markdown** (e.g.,
`closing-2026/*/weekly-review/{date}.md` written by `vault_write`) but
the cross-cycle consumption pattern is implicit and brittle:

```
Daily cycle → writes daily.md / cycle_state/{date}.md
Weekly cycle → reads 7 daily.md files (manual path glob), aggregates
Monthly cycle → reads 4 weekly-review files (manual path glob), synthesizes
Quarterly cycle → reads 3 monthly-review files + 13 weekly-review files
```

Three problems with this pattern:

1. **No canonical cross-cycle join key.** Weekly reads daily by **path
   glob** (`closing-2026/*/04-relatorios-diarios/*.md`). This works at
   the data level but the query has no discriminator: any markdown file
   in that path is consumed, regardless of authorship, schema, or
   freshness. There is no concept of "this daily.md was written by the
   `daily` skill at 2026-09-03 08:57 UTC by actor=user".
2. **No retention policy.** Daily.md files accumulate forever in
   `closing-2026/`. Weekly aggregates must scan 90+ dailies to find
   "the last 7." Quarterly must scan 12+ monthlies. Cost grows linearly
   with history; the system never prunes.
3. **No actor scoping.** Per ADR-025, `daily = actor=user`,
   `weekly/monthly/quarterly = actor=agent`. A weekly query reading
   dailies cannot filter by actor — it reads user-written dailies AND
   any agent-written files in the same path. ADR-025 R3's
   `vault_write(actor=...)` discipline is recorded in
   `.vault_audit.log` but the cross-cycle consumer never consults it.

Wave 4 Scenario B (Sub-agents + stateful subgraphs, 32-44h) makes this
problem load-bearing. The four skills must compose: weekly's output
must be a deterministic function of daily's outputs (per ADR-013
planner-only invariant; weekly reads daily's `commit_summary`,
`active_*_ueids`, `prospective_buffer`, `retrospective_log`,
`corrections`, `balancer_verdict`). Without a memory layer, the
composition is implicit and untestable.

ADR-026 (DRAFT, shipped `3cc9799`) handles **intra-cycle** sub-agent
dispatch (parent ↔ child). ADR-027 (DRAFT, shipped `648b83a`) handles
**per-cycle persistence** (SqliteSaver checkpoint schema, R5 field
classification). Neither handles **cross-cycle** queries.

This ADR formalizes the **cross-cycle memory layer**. It is
**architectural decision only** — implementation ships in W4.6 (B-N12,
12-16h).

---

## Decision

**The cross-cycle memory layer is a HYBRID: a SQLite database
(`<root>/data/ikigai_memory.db`) for structured, UEID-indexed queries
PLUS vault markdown frontmatter for human-readable summaries.** The
SqliteSaver checkpoint DB at `<root>/data/ikigai_checkpoints.db`
(per ADR-027) is **per-cycle replay state**, NOT cross-cycle memory;
ADR-028 introduces a **separate** SQLite file dedicated to cross-cycle
queries.

The schema has 4 parts (R1–R4), 8 rules (R5–R12), and 5 per-record
schemas (one per memory type). All memory tuning constants live in
`prompts/algorithm_constants.json` per ADR-019.

### R1 — Memory table schemas (SQLite)

Four memory tables, one per skill, each indexed by 4-part UEID. The
schema is **additive-only** across versions (R11).

```sql
-- Daily intentions — written by ikigai-daily (actor=user)
CREATE TABLE IF NOT EXISTS memory_daily_intentions (
    daily_ueid    TEXT PRIMARY KEY,        -- 4-part UEID per ADR-014
    cycle_id      TEXT NOT NULL,           -- parent cycle UUID
    skill         TEXT NOT NULL,           -- always "ikigai-daily"
    actor         TEXT NOT NULL,           -- "user" | "agent" | "system"
    ts            TEXT NOT NULL,           -- ISO 8601 UTC (vault_write timestamp)
    cycle_start   TEXT NOT NULL,
    cycle_end     TEXT NOT NULL,
    body_markdown TEXT NOT NULL,           -- frontmatter + body of daily.md
    vault_path    TEXT NOT NULL,           -- relative to vault_root
    sha256        TEXT NOT NULL,           -- sha256 of body_markdown
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL            -- ISO 8601 UTC (write timestamp)
);
CREATE INDEX IF NOT EXISTS idx_memory_daily_ts
    ON memory_daily_intentions(ts);
CREATE INDEX IF NOT EXISTS idx_memory_daily_actor
    ON memory_daily_intentions(actor);

-- Weekly aggregations — written by ikigai-weekly (actor=agent)
CREATE TABLE IF NOT EXISTS memory_weekly_aggregations (
    weekly_ueid   TEXT PRIMARY KEY,        -- 4-part UEID
    cycle_id      TEXT NOT NULL,
    skill         TEXT NOT NULL,           -- "ikigai-weekly"
    actor         TEXT NOT NULL,           -- "agent"
    ts            TEXT NOT NULL,
    cycle_start   TEXT NOT NULL,
    cycle_end     TEXT NOT NULL,
    source_ueids  TEXT NOT NULL,           -- JSON list of daily_ueids aggregated
    body_markdown TEXT NOT NULL,
    vault_path    TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_weekly_ts
    ON memory_weekly_aggregations(ts);
CREATE INDEX IF NOT EXISTS idx_memory_weekly_source
    ON memory_weekly_aggregations(source_ueids);  -- JSON LIKE query for join

-- Monthly syntheses — written by ikigai-monthly (actor=agent)
CREATE TABLE IF NOT EXISTS memory_monthly_syntheses (
    monthly_ueid  TEXT PRIMARY KEY,        -- 4-part UEID
    cycle_id      TEXT NOT NULL,
    skill         TEXT NOT NULL,           -- "ikigai-monthly"
    actor         TEXT NOT NULL,           -- "agent"
    ts            TEXT NOT NULL,
    cycle_start   TEXT NOT NULL,
    cycle_end     TEXT NOT NULL,
    source_ueids  TEXT NOT NULL,           -- JSON list of weekly_ueids
    body_markdown TEXT NOT NULL,
    vault_path    TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_monthly_ts
    ON memory_monthly_syntheses(ts);

-- Quarterly strategies — written by ikigai-quarterly (actor=agent)
CREATE TABLE IF NOT EXISTS memory_quarterly_strategies (
    quarterly_ueid TEXT PRIMARY KEY,       -- 4-part UEID
    cycle_id      TEXT NOT NULL,
    skill         TEXT NOT NULL,           -- "ikigai-quarterly"
    actor         TEXT NOT NULL,           -- "agent"
    ts            TEXT NOT NULL,
    cycle_start   TEXT NOT NULL,
    cycle_end     TEXT NOT NULL,
    source_ueids  TEXT NOT NULL,           -- JSON list of monthly_ueids
    body_markdown TEXT NOT NULL,
    vault_path    TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_quarterly_ts
    ON memory_quarterly_strategies(ts);

-- Schema registry (mirrors ADR-027 R1 pattern)
CREATE TABLE IF NOT EXISTS memory_schema_registry (
    schema_version INTEGER PRIMARY KEY,    -- monotonic, never reused
    description    TEXT NOT NULL,
    applied_at     TEXT NOT NULL           -- ISO 8601 UTC
);

-- ADR-028 R12: WAL mode + tuning constants loaded at connection
PRAGMA journal_mode = WAL;                 -- R12 (mirrors ADR-027 R8)
PRAGMA synchronous = NORMAL;               -- R12
PRAGMA busy_timeout = 5000;                -- R12 (5s busy timeout)
PRAGMA foreign_keys = ON;                  -- referential integrity (future FKs)
```

**Why separate from ADR-027 checkpoint DB:** the checkpoint DB
(`<root>/data/ikigai_checkpoints.db`) is per-cycle replay state —
one row per LangGraph invocation, pruned aggressively per
`CHECKPOINT_RETENTION_COUNT=1000` (ADR-027 R10). Memory records are
**cross-cycle artifacts** that must persist for trend queries
(monthly reads 4 weeks of weekly aggregations; quarterly reads 3
months of monthly syntheses). Mixing them in one DB conflates the
retention policies and forces the checkpoint DB to grow beyond the
per-cycle bound. Separate DBs = independent retention, independent
backup cadence.

### R2 — Vault frontmatter contract (human-readable layer)

Each skill writes a markdown file to vault that mirrors the SQLite
record's `body_markdown`. The markdown is the **human-readable
summary**; the SQLite row is the **structured query index**. The
mandatory frontmatter schema is:

```yaml
---
# Identity (per ADR-014 4-part UEID, ADR-025 actor)
ueid: <4-part UEID>
cycle_id: <UUID>
skill: ikigai-daily | ikigai-weekly | ikigai-monthly | ikigai-quarterly
actor: user | agent | system
ts: 2026-09-03T08:57:00Z            # ISO 8601 UTC

# Cross-cycle join
schema_version: 1

# Memory-specific (per skill)
# daily.md:
daily_intentions:
  - intention: <pt-BR string>
    target_ueid: <4-part UEID>      # optional
  - ...
# weekly.md:
source_ueids: [<daily_ueid>, ...]    # JSON list of source UEIDs

# monthly.md:
source_ueids: [<weekly_ueid>, ...]
# quarterly.md:
source_ueids: [<monthly_ueid>, ...]

# Audit trail (per ADR-012)
audit_sha256: <sha256 of body_markdown>
---

# Markdown body
...
```

The vault markdown is the **canonical source for human readers**; the
SQLite row's `body_markdown` field is a denormalized mirror for query
convenience. `audit_sha256` lets a consumer verify that the SQLite row
matches the on-disk vault file (per ADR-012 audit-log integrity).

### R3 — UEID discipline

All cross-cycle join keys are **4-part UEIDs** per ADR-014 (canonical
regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`). The memory
schema enforces this via:

1. **Primary key shape.** Every `*_ueid` column is `TEXT` with a CHECK
   constraint that the value matches the 4-part regex. The constraint
   is added in W4.6 implementation (not this ADR; the regex lives in
   `src/contracts/common.py:UEID` per ADR-014 R1).
2. **Source UEID lists.** `source_ueids` (R1 tables) stores a JSON list
   of 4-part UEIDs. W4.6 implementation MUST validate each element
   matches the regex before INSERT. Reject 5-part UEIDs (per ADR-014
   R3: tests use 4-part only).
3. **`active_*_ueids` join.** Per ADR-027 R5.5, `active_dream_ueid`,
   `active_goal_ueids`, etc., are 4-part. The weekly aggregation's
   `source_ueids` MUST be a subset of `active_*_ueids` from the daily
   cycle that contributed to it.

### R4 — Write protocol (actor-tagged, audit-logged)

Every memory write MUST flow through `vault_write(actor=...)` per
ADR-012 §1 + ADR-025 R3. The W4.6 implementation pattern:

```
1. Skill node computes body_markdown + ueid + ts.
2. Skill node calls vault_write(
       vault_root=vault_root,
       vault_path=<derived path>,    # e.g., "closing-2026/.../daily-{date}.md"
       frontmatter_fields={ueid, cycle_id, skill, actor, ts, ...},
       body=<body_markdown>,
       actor=<manifest["actor"]>,
   )
3. vault_write returns {written, sha256, actor}.
4. Skill node calls memory_write(
       memory_db=<ikigai_memory.db path>,
       table=<memory_*>,
       ueid=<ueid>,
       body_markdown=<body_markdown>,
       sha256=<sha256>,
       vault_path=<vault_path>,
       actor=<manifest["actor"]>,
   )
5. memory_write validates 4-part UEID, INSERTs into the table.
6. memory_write also appends to .vault_audit.log (same as vault_write).
```

Both writes MUST succeed atomically OR both MUST roll back. W4.6
implementation uses a transaction:

```python
with vault_lock, sqlite3.connect(memory_db) as conn:
    vault_write_result = vault_write(...)
    conn.execute("INSERT INTO memory_daily_intentions ...")
    conn.commit()
    audit_log_append(...)
```

If either step fails, both roll back. The user re-invokes the skill.
Per ADR-013, retries are NOT automatic — deterministic pipelines.

### R5 — Retrieval patterns

Each consuming skill has a typed retrieval function:

```python
def read_daily_intentions(
    week_range: tuple[date, date],
    actor: Literal["user", "agent", "system"] | None = None,
) -> list[DailyIntentionRecord]:
    """Read daily intentions for a date range.

    Filters by ts range (inclusive) and optional actor tag.
    Returns records sorted by ts ASC.
    """

def read_weekly_aggregations(
    month_range: tuple[date, date],
    actor: Literal["user", "agent", "system"] | None = None,
) -> list[WeeklyAggregationRecord]:
    """Read weekly aggregations for a date range."""

def read_monthly_syntheses(
    quarter_range: tuple[date, date],
    actor: Literal["user", "agent", "system"] | None = None,
) -> list[MonthlySynthesisRecord]:
    """Read monthly syntheses for a date range."""

def read_quarterly_strategies(
    year: int,
    actor: Literal["user", "agent", "system"] | None = None,
) -> list[QuarterlyStrategyRecord]:
    """Read quarterly strategies for a year."""
```

Permission model: **default-deny** — `actor=None` returns records from
ALL actors (used by agent introspection). `actor="agent"` returns only
agent-written records (used by agent cross-cycle reads). `actor="user"`
returns only user-written records (rare; weekly rarely reads user
records).

Caching strategy: per ADR-027 R8 WAL mode + per-actor reads, no
memoization layer is needed. `sqlite3.connect()` with `check_same_thread
=False` (mirroring ADR-027 R8) supports parallel reads from a single
parent + N children. W4.6 implementation may add an LRU cache if
profiling shows repeated queries are a hotspot (deferred).

### R6 — Per-record schemas

Each memory type has a Pydantic v2 strict model (per
`CLAUDE.md` §"Global Conventions"):

```python
class DailyIntentionRecord(TypedDict, total=True):
    daily_ueid: str            # 4-part UEID (PRIMARY KEY)
    cycle_id: str
    skill: Literal["ikigai-daily"]
    actor: Literal["user", "agent", "system"]
    ts: str                    # ISO 8601 UTC
    cycle_start: str
    cycle_end: str
    body_markdown: str
    vault_path: str
    sha256: str
    schema_version: Literal[1]
    created_at: str

class WeeklyAggregationRecord(TypedDict, total=True):
    weekly_ueid: str           # 4-part UEID
    cycle_id: str
    skill: Literal["ikigai-weekly"]
    actor: Literal["user", "agent", "system"]
    ts: str
    cycle_start: str
    cycle_end: str
    source_ueids: list[str]    # list of 4-part UEIDs
    body_markdown: str
    vault_path: str
    sha256: str
    schema_version: Literal[1]
    created_at: str

class MonthlySynthesisRecord(TypedDict, total=True):
    monthly_ueid: str
    cycle_id: str
    skill: Literal["ikigai-monthly"]
    actor: Literal["user", "agent", "system"]
    ts: str
    cycle_start: str
    cycle_end: str
    source_ueids: list[str]    # list of 4-part weekly_ueids
    body_markdown: str
    vault_path: str
    sha256: str
    schema_version: Literal[1]
    created_at: str

class QuarterlyStrategyRecord(TypedDict, total=True):
    quarterly_ueid: str
    cycle_id: str
    skill: Literal["ikigai-quarterly"]
    actor: Literal["user", "agent", "system"]
    ts: str
    cycle_start: str
    cycle_end: str
    source_ueids: list[str]    # list of 4-part monthly_ueids
    body_markdown: str
    vault_path: str
    sha256: str
    schema_version: Literal[1]
    created_at: str
```

Each `source_ueids` list enforces a **referential integrity** invariant
at write time (not DB-level FK, since FK would couple memory tables to
each other across the per-skill partition). The validation function
(added in W4.6) checks every element matches the 4-part regex AND
exists in the parent table (`memory_daily_intentions` for weekly's
`source_ueids`, etc.).

### R7 — Cross-cycle data flow (concrete handoffs)

The handoffs are **queries**, not row mutations. The consumer reads
the parent's row by `ueid`; the producer's row is immutable once
written (per append-only invariant).

```
ikigai-daily writes memory_daily_intentions (actor=user)
   ↓
ikigai-weekly reads memory_daily_intentions WHERE ts BETWEEN week_start AND week_end
   ↓
ikigai-weekly aggregates, writes memory_weekly_aggregations (actor=agent)
   ↓
ikigai-monthly reads memory_weekly_aggregations WHERE ts BETWEEN month_start AND month_end
   ↓
ikigai-monthly synthesizes, writes memory_monthly_syntheses (actor=agent)
   ↓
ikigai-quarterly reads memory_monthly_syntheses WHERE ts BETWEEN quarter_start AND quarter_end
   ↓
ikigai-quarterly strategizes, writes memory_quarterly_strategies (actor=agent)
```

Each consuming skill reads from the **immediate predecessor** (weekly
reads daily's outputs, NOT monthly's); this preserves the natural
pyramid flow (Sonho → Quarterly → Monthly → Weekly → Daily per
`state.py:60` PlanTier enum).

### R8 — Retention policy (memory layer-specific)

ADR-027 R10 retention (`CHECKPOINT_RETENTION_COUNT=1000`,
`MAX_CHECKPOINT_AGE_DAYS=90`) applies to the **checkpoint DB**, not
the memory DB. The memory layer has its own retention:

| Layer | Max age | Pruning trigger |
|-------|---------|-----------------|
| `memory_daily_intentions` | 30 days | Monthly cycle rolls up after 7 days |
| `memory_weekly_aggregations` | 90 days | Quarterly cycle rolls up after 30 days |
| `memory_monthly_syntheses` | 365 days | Annual review rolls up |
| `memory_quarterly_strategies` | Forever (append-only) | None |

The 4 tuning constants land in `prompts/algorithm_constants.json` per
ADR-019:

| Key | Default | Meaning |
|-----|---------|---------|
| `MEMORY_RETENTION_DAILY_DAYS` | 30 | Daily rows pruned after 30 days |
| `MEMORY_RETENTION_WEEKLY_DAYS` | 90 | Weekly rows pruned after 90 days |
| `MEMORY_RETENTION_MONTHLY_DAYS` | 365 | Monthly rows pruned after 1 year |
| `MEMORY_RETENTION_QUARTERLY_DAYS` | None (forever) | Quarterly rows never pruned (canonical SONHO-level artifacts) |

The drift detector's `test_no_algorithm_constants_in_agent_code`
invariant (l, ADR-019 R7) extends at W4.7 ship to cover these 4 new
keys' absence from `.py` files. No Python `DEFAULT_MEMORY_*` constants
permitted.

The pruning job is **not** a cron; it's an **inline prune-on-write**
trigger. When a monthly cycle writes a new monthly synthesis, it
prunes `memory_daily_intentions` rows older than 30 days. This avoids
a separate cron and ensures retention is always up-to-date.

### R9 — Sub-agent memory propagation (per ADR-026 S2)

Per ADR-026 S2 (context propagation), each sub-agent receives a
**narrowed slice** of `IKIGAiStateDict`. The memory layer's
read functions are NOT in the slice — sub-agents MUST NOT directly
query `memory_*` tables. Instead:

1. The parent cycle (e.g., weekly's parent) calls `read_daily_intentions(...)`
   **before** dispatching to children.
2. The parent injects the result into each child's `initial_state`
   under a new `memory_daily_intentions` slot (or as part of
   `prospective_buffer` if ADR-026 S3 `append` merge strategy applies).
3. Children read the injected slot, NOT the SQLite DB.

This rule is consistent with ADR-026 S2's "narrowed slice" principle:
the parent's memory queries are part of the parent's pre-dispatch
work; children receive derived state, never raw DB access.

**Memory writes by sub-agents** follow ADR-026 S3 `append` merge
strategy: child writes append to `prospective_buffer` /
`retrospective_log` (which use `Annotated[list[X], operator.add]`
reducers per `state.py:156-162`). The parent cycle, on termination,
calls `memory_write(...)` to persist the final aggregated record.

### R10 — Failure modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| **Memory DB corrupt** (SQLite header corruption) | `sqlite3.connect()` raises `sqlite3.DatabaseError` | `memory_init()` raises with explicit message; user runs `memory_init(memory_db=...)` against a fresh DB at `<root>/data/ikigai_memory.db.bak-<timestamp>`. Old DB is archived (never deleted; append-only). |
| **Memory DB missing** (fresh clone) | `memory_db.exists()` is False | `memory_init()` auto-creates the DB with R1 schema. First write per skill is the seed. |
| **Vault write fails** (disk full, permission denied) | `vault_write` raises `ValueError` or `OSError` | The W4.6 implementation wraps the `vault_write + memory_write` sequence in a try/except; on vault_write failure, the memory write MUST NOT execute (atomic rollback per R4). Caller (skill orchestrator) logs the failure; the cycle is NOT retried automatically (per ADR-013). |
| **Memory write fails** (DB locked, FK violation) | `sqlite3.OperationalError` or `sqlite3.IntegrityError` | Same rollback: vault write succeeded but memory write failed. W4.6 implementation rolls back the vault write (best-effort: delete the file via `vault_root / vault_path .unlink()` if it was just created). Caller logs + emits TaskChange to `data/review_queue/` (per Wave 3 partial-success invariant). |
| **Schema version mismatch** (old code reading new row) | `schema_version > max_known_version` triggers migration loader | W4.6 ships `_migrate_v1_to_v2(row)` stub (raises `NotImplementedError` until v2 ships). Mirrors ADR-027 R9. |
| **Schema version mismatch** (new code reading old row) | `schema_version < SCHEMA_VERSION` triggers migration | Same: oldest-first migrations. |
| **Concurrent writes** (two skills writing simultaneously) | `sqlite3.OperationalError: database is locked` | `busy_timeout=5000` retries for 5s. After timeout, raises. Caller logs + emits TaskChange. |
| **UEID format violation** (5-part UEID passed) | Regex check in `memory_write` raises `ValueError` | Caller (skill orchestrator) sees the validation error; the cycle aborts. No write proceeds. |
| **Stale child row** (parent pruned but child remains) | `memory_*_source_ueids` references UEID that no longer exists | `read_*` functions ignore stale references silently (filter out at read time, not at write time). W4.6 adds a `WEEKLY_CLEANUP_STALE_REFS` step that emits a TaskChange to `data/review_queue/` for human review. |
| **Disk full mid-write** | `sqlite3.OperationalError: disk full` | Mirrors ADR-027 R11 disk-full handling: caller logs + emits TaskChange; cycle is NOT retried. |

### R11 — Schema versioning

`schema_version` is **monotonic, never reused**. The current version is
**1** (set by this ADR). Future versions follow the ADR-027 R9 pattern:

- **Backward-compatible additions** (e.g., a new field on
  `DailyIntentionRecord`) → `schema_version` STAYS AT 1; new field is
  `NotRequired`. Old code reads new rows fine.
- **Breaking changes** (rename, drop, type change) → `schema_version`
  INCREMENTS. Migration function `_migrate_v1_to_v2(row)` reads v1 JSON,
  transforms to v2 shape, writes back. Migration runs **on read**
  (lazy); old rows persist for audit.

The `memory_schema_registry` table records the version transition
history (mirrors ADR-027 R1 `ikigai_schema_registry`):

```sql
INSERT INTO memory_schema_registry (schema_version, description, applied_at)
VALUES (1, 'Initial memory layer (W4.3 ADR-028)', '2026-09-04T17:00:00Z');
```

### R12 — WAL mode + thread safety

SQLite connections to `ikigai_memory.db` use the same 4 PRAGMAs as
ADR-027 R8 (`journal_mode=WAL`, `synchronous=NORMAL`,
`busy_timeout=5000`, `foreign_keys=ON`). The connection factory is
`memory_init(memory_db: Path) -> sqlite3.Connection` and MUST be
called at graph init (W4.6) and at the start of each standalone
read function. Drift invariant (o) at W4.7 ship verifies these PRAGMAs
are present.

**Why same PRAGMAs as checkpoint DB:** per ADR-027 R8 rationale,
sub-agent fan-out (parent + N children) writes concurrently. Weekly's
parent + monthly's parent may both write to the memory DB in
overlapping cron windows (e.g., Monday 09:00 weekly + 1st-of-month
10:00 monthly). WAL mode + busy_timeout are the **minimum** needed to
prevent serialization and deadlock.

### R13 — Implementation deliverables (W4.6)

This ADR does NOT ship code. W4.6 (B-N12, 12-16h) implements:

1. **`src/ikigai/src/agents/v2/memory_schema.py`** (new file)
   - Exports `MEMORY_SCHEMA_VERSION = 1`
   - Exports the 4 TypedDict records (`DailyIntentionRecord`, etc.)
   - Exports `memory_init(memory_db: Path) -> sqlite3.Connection` with
     the 4 PRAGMAs (R12) + 4 CREATE TABLE IF NOT EXISTS statements (R1)
2. **`src/ikigai/src/agents/v2/memory_write.py`** (new file)
   - `memory_write(memory_db, table, ueid, body_markdown, sha256,
     vault_path, actor, source_ueids=None)` — validates 4-part UEID
     (R3), inserts row (R1), writes audit log (R4).
   - Atomic vault_write + memory_write wrapper per R4.
3. **`src/ikigai/src/agents/v2/memory_read.py`** (new file)
   - `read_daily_intentions(week_range, actor=None)` — R5
   - `read_weekly_aggregations(month_range, actor=None)` — R5
   - `read_monthly_syntheses(quarter_range, actor=None)` — R5
   - `read_quarterly_strategies(year, actor=None)` — R5
4. **`src/ikigai/src/agents/v2/memory_migrations.py`** (new file)
   - `_migrate_v1_to_v2(row: dict) -> dict` stub (raises
     `NotImplementedError` until v2 ships) — R11
   - `apply_migrations(row: dict, target_version: int) -> dict`
5. **`src/ikigai/src/agents/v2/memory_prune.py`** (new file)
   - Inline prune-on-write: when a monthly cycle writes, prune
     `memory_daily_intentions` rows older than
     `MEMORY_RETENTION_DAILY_DAYS` (R8).
6. **Add 4 keys to `prompts/algorithm_constants.json`** (R8) +
   defensive defaults in `load_constants.py`.
7. **Drift invariant (o) in
   `src/ikigai/tests/test_canonical_scope.py`** — verify the 4 PRAGMAs
   are present after `sqlite3.connect()` (R12) + the 4 new JSON keys
   are NOT in any `.py` file (R8) + every `*_ueid` field in the
   schema is 4-part regex.

---

## Rationale

1. **Hybrid is the right answer; vault-only and SQLite-only both fail.**
   Vault-only (Option A) makes cross-cycle queries expensive: weekly
   must read N daily.md files and parse YAML frontmatter per query.
   No retention, no actor scoping, no UEID join key. SQLite-only
   (Option B) loses the human-readable audit trail that ADR-012
   mandates and that the existing skill manifests
   (`weekly.md:14`, `monthly.md:14`, `quarterly.md:15`) already
   declare as `vault_write: <path>`. Hybrid (Option C) gives both:
   SQLite for queries, vault for humans, atomic writes per R4.

2. **Separate DB from ADR-027 checkpoint DB.** The checkpoint DB is
   per-cycle replay state (one row per LangGraph invocation, pruned
   aggressively). Memory is cross-cycle artifacts (one row per skill
   invocation, retained for trend queries). Mixing them forces the
   checkpoint retention policy to govern memory retention, which is
   too aggressive (90-day max vs 365-day monthly retention per R8).
   Separate DBs = independent retention, independent backup, simpler
   drift detection (one invariant per DB).

3. **UEID as the canonical cross-cycle join key.** Per ADR-014, UEIDs
   are the canonical join across all forks (CLI / taskdog / UPI).
   Adding memory as a 4th join target (alongside the 3 forks) makes
   memory discoverable by the same UEIDs that the rest of the system
   uses. `active_*_ueids` from ADR-027 R5.5 are the cycle-level
   join keys; `daily_ueid` / `weekly_ueid` / `monthly_ueid` /
   `quarterly_ueid` are the per-record join keys. The
   `source_ueids` list on aggregation records is the chain link
   that proves "this weekly aggregation was built from these specific
   daily intentions."

4. **Prune-on-write avoids cron overhead.** Per `CLAUDE.md`
   §"Global Conventions" (single-user local), a separate pruning
   cron is overkill. Inline pruning on monthly cycle write ensures
   `memory_daily_intentions` is bounded at 30 days without needing a
   scheduler. This mirrors the inline-PII-redaction pattern of
   `vault_write` (no cron).

5. **Actor-tagged writes respect ADR-025 R3.** The `actor` column
   on every record flows from `manifest["actor"]` (per ADR-025 R2:
   `daily = user`, `weekly/monthly/quarterly = agent`). The audit
   log gets the same tag. The `read_*` functions' `actor` parameter
   enables role-based reads (e.g., the user reading the daily's
   own daily record; the agent reading dailies it aggregated from).

6. **WAL mode mirrors ADR-027 R8.** Per ADR-027 R8 rationale,
   sub-agent fan-out needs concurrent readers + 1 writer. The same
   rationale applies to memory writes: weekly + monthly cycles can
   overlap (Monday 09:00 weekly + 1st-of-month 10:00 monthly).
   WAL mode is the SqliteSaver-supported concurrency primitive;
   adopting it here is the minimum to avoid serialization.

7. **Algorithm constants in JSON (per ADR-019).** 4 new keys land
   in `prompts/algorithm_constants.json` (R8). No Python
   `DEFAULT_MEMORY_*` constants. The drift detector's invariant (l)
   extends at W4.7 ship to cover these keys' absence from `.py`
   files. This is the same pattern W3.2 used for the 14 QHE
   constants and W4.5 uses for the 5 checkpoint constants
   (ADR-027 R10).

8. **Atomic vault_write + memory_write is non-negotiable.** If the
   vault write succeeds but the memory write fails, the system is
   inconsistent: vault has a markdown file that no SQLite row
   references. Conversely, if the memory write succeeds but the
   vault write fails, the SQLite row references a non-existent
   file. Per ADR-013 deterministic pipelines, retries are NOT
   automatic — the user re-invokes. R4's atomic wrapper is the
   minimum to make failure modes recoverable.

9. **Per-skill partition mirrors the data flow pyramid.** Per
   `state.py:60` `PlanTier` (Sonho → Quarterly → Monthly → Weekly →
   Daily), the natural flow is downward. The 4 memory tables
   (`memory_daily_intentions`, `memory_weekly_aggregations`,
   `memory_monthly_syntheses`, `memory_quarterly_strategies`)
   mirror the pyramid. Each consumer reads from the immediate
   predecessor; no cross-tier reads (quarterly reads monthly's
   syntheses, NOT weekly's aggregations directly).

10. **Append-only invariant extends to memory.** Per `CLAUDE.md`
    §"Refactor Protocol" (`vault/`, `vibe-ops/`, `strategics/`,
    `data/review_queue/`), the project is append-only. Memory rows
    are append-only by R11 versioning: new versions add columns /
    rows, never rename or drop. Old rows persist for audit. Quarterly
    rows are **forever** (per R8 retention table); they are the
    SONHO-level artifacts that subsequent Sonho cycles reference.

---

## Implementation Rules Summary

**R1 — Memory table schemas** — 4 tables (`memory_daily_intentions`,
`memory_weekly_aggregations`, `memory_monthly_syntheses`,
`memory_quarterly_strategies`) + `memory_schema_registry`; 4 PRAGMAs
at connection.

**R2 — Vault frontmatter contract** — mandatory frontmatter schema
for all 4 memory markdown files; `audit_sha256` links SQLite row to
on-disk vault file.

**R3 — UEID discipline** — 4-part UEIDs only (ADR-014); CHECK
constraint on every `*_ueid` column; `source_ueids` validated at
INSERT.

**R4 — Write protocol** — atomic `vault_write + memory_write`
sequence; rollback on either failure; audit log gets the same
`actor` tag.

**R5 — Retrieval patterns** — 4 typed `read_*` functions; default-
deny actor scoping; no memoization layer (WAL mode is sufficient).

**R6 — Per-record schemas** — 4 TypedDict records
(`DailyIntentionRecord`, `WeeklyAggregationRecord`,
`MonthlySynthesisRecord`, `QuarterlyStrategyRecord`).

**R7 — Cross-cycle data flow** — pyramid (Sonho → Daily); each
consumer reads from immediate predecessor; no cross-tier reads.

**R8 — Retention policy** — 4 new keys in `algorithm_constants.json`
(`MEMORY_RETENTION_DAILY_DAYS=30`, `MEMORY_RETENTION_WEEKLY_DAYS=90`,
`MEMORY_RETENTION_MONTHLY_DAYS=365`,
`MEMORY_RETENTION_QUARTERLY_DAYS=None`); inline prune-on-write.

**R9 — Sub-agent memory propagation** — parent queries memory DB
before spawning children; children receive derived state in the
narrowed slice, NOT raw DB access; memory writes use ADR-026 S3
`append` merge strategy.

**R10 — Failure modes** — 10-row table covering corrupt / missing /
write-fail / version-mismatch / concurrent / disk-full / UEID
violation / stale-ref.

**R11 — Schema versioning** — monotonic, never reused; additive
backward-compat by default; lazy migration on read.

**R12 — WAL mode + thread safety** — same 4 PRAGMAs as ADR-027 R8;
drift invariant (o) at W4.7 ship.

**R13 — Implementation deliverables** — 7 W4.6 deliverables
(non-binding on this ADR's DRAFT status).

---

## Cross-ADR Consistency Check

- **vs ADR-026 (sub-agent dispatch, DRAFT `3cc9799`):** memory
  propagation respects S2 contract ✓ — parent queries memory DB
  before spawning children (R9); children receive derived state in
  the narrowed slice, NOT raw DB access; S2.4 error channel
  isolation applies (memory write failure does NOT propagate to
  parent `error_type`); S3 `append` merge strategy used for
  children's `prospective_buffer` contributions to the parent's
  memory write.
- **vs ADR-027 (stateful subgraph, DRAFT `648b83a`):** memory layer
  reads from / writes to a SEPARATE SQLite file (R1), NOT the
  checkpoint DB. Memory inherits ADR-027 R5.5 UEID discipline (R3),
  R8 PRAGMAs (R12), R9 versioning pattern (R11), R11 disk-full /
  contention handling (R10). ADR-027 R13 implementation
  deliverables (W4.5) ship `checkpoint_schema.py` + PRAGMAs at
  connection; ADR-028 R13 (W4.6) ships `memory_schema.py` with the
  SAME PRAGMA pattern. The two ADRs ship parallel artifacts in
  parallel tasks.
- **vs ADR-019 (algorithm_constants.json, Proposed 2026-09-04):** 4
  new tuning values land in JSON (R8); drift detector (l) extends at
  W4.7 ship to cover the 4 new keys' absence from `.py` files.
- **vs ADR-025 (skill binding, Accepted 2026-09-04):** actor
  consistency ✓ — every memory write passes
  `actor=manifest["actor"]` to `vault_write` (R4) and stores the
  same `actor` in the SQLite row (R1). `daily = actor=user`;
  `weekly/monthly/quarterly = actor=agent` per shipped R2 table.
- **vs ADR-012 (vault_write sole writer, Accepted 2026-08-30):**
  every memory write flows through `vault_write(actor=...)` (R4);
  the markdown file in vault IS the canonical source; the SQLite
  row is the query index. `audit_sha256` in frontmatter (R2) links
  the SQLite row to the vault file's content hash.
- **vs ADR-013 (canonical scope discipline, Accepted 2026-08-31):**
  planner-only ✓ — memory layer stores planner state (UEIDs, body
  markdown, actor, timestamps), never computed values (no scoring,
  no heuristics, no QHE). Memory retrieval is deterministic
  (`WHERE ts BETWEEN ...`); the schema stores retrieval results,
  not LLM reasoning that produced them.
- **vs ADR-014 (UEID canonical 4-part, Accepted 2026-09-04):** all
  cross-cycle join keys are 4-part UEIDs (R3); CHECK constraint on
  every `*_ueid` column; 5-part UEIDs REJECTED at INSERT.

---

## Consequences

### Positive

- **Locked cross-cycle memory architecture unblocks W4.6 / W4.7 /
  W4.8.** Every downstream Wave 4 task has a stable contract:
  W4.6 ships the 7 implementation deliverables (R13); W4.7
  adds drift invariant (o); W4.8 E2E validates "weekly knows
  what daily produced" against the locked schema.
- **Hybrid gives both queryability AND auditability.** SQLite
  gives fast UEID-indexed queries; vault markdown gives the
  human-readable audit trail ADR-012 mandates. Neither alone
  satisfies both.
- **UEID join keys make memory discoverable from the rest of the
  system.** `memory_daily_intentions.daily_ueid` joins to
  `ikigai_checkpoints.checkpoint.cycle_id` (via ADR-027 R5.5
  `active_dream_ueid`) and to `taskdog` task IDs (via Phase 3 v1
  mesh). The 4-part UEID is the canonical join across all 3 forks
  AND memory.
- **Independent retention per layer.** Checkpoint DB prunes at
  90 days (ADR-027 R10); memory DB prunes at 30/90/365/forever
  per layer (R8). The two policies never interfere.
- **Append-only invariant extends to memory.** R11 versioning
  never drops or renames columns. Per `CLAUDE.md` §"Refactor
  Protocol," this matches project-wide convention.
- **WAL mode is the right concurrency primitive for memory
  writes.** Per ADR-027 R8, parent + N children write concurrently;
  weekly + monthly cycles can overlap cron windows. WAL mode +
  busy_timeout handle contention.
- **Algorithm tuning is JSON-only.** 4 new keys in
  `algorithm_constants.json` (per ADR-019); zero new Python
  constants.

### Negative

- **Separate SQLite file adds operational surface.** `<root>/data/`
  gains `ikigai_memory.db` in addition to `ikigai_checkpoints.db`
  (ADR-027). Drift invariant (o) at W4.7 catches regressions.
- **4 new algorithm constants** extend the JSON SOT; the
  defensive-default in `load_constants.py` must mirror them
  exactly (per ADR-019 R6).
- **Schema versioning migration** adds a new file
  (`memory_migrations.py`). W4.6 ships an empty migration
  registry + a stub `_migrate_v1_to_v2` (raises
  `NotImplementedError` until v2 ships).
- **Atomic vault_write + memory_write has cost.** Wrapping the
  two writes in a transaction (R4) adds latency (one extra
  `commit()` per skill invocation). For typical cycles
  (1 vault write + 1 memory write = ~50ms total), the cost is
  negligible; for high-frequency cycles (sub-agent fan-out with
  N memory writes), it compounds. W4.6 may batch if profiling
  shows hot paths.
- **Inline prune-on-write is opportunistic.** A cycle that
  never runs (e.g., user skips monthly) leaves the daily rows
  unpruned. Acceptable per `CLAUDE.md` §"Global Conventions"
  (single-user local); the next monthly cycle catches up.
- **Vault frontmatter `source_ueids` lists grow.** A quarterly
  that aggregates 3 monthly syntheses carries 3 source UEIDs;
  each monthly carries 4 weekly UEIDs. The JSON list is small,
  but it grows linearly with the pyramid depth. R8 retention
  caps it.

### Neutral

- **Hybrid is two storage layers, not one.** Vault markdown
  + SQLite. The redundancy is by design (auditability +
  queryability), but the data lives in two places. Audit log
  (`audit_sha256` per R2) detects divergence.
- **Per-skill partition mirrors the data flow pyramid.** Sonho
  → Quarterly → Monthly → Weekly → Daily. Each consumer reads
  from the immediate predecessor. Cross-tier reads are not
  implemented (quarterly reads monthly, NOT weekly directly).
  Acceptable trade-off for the locked-scope architecture; a
  future ADR could add cross-tier reads if SONHO-log evidence
  demands it.
- **Memory writes are skill-internal.** The 4 skills own their
  memory tables; sub-agents (per ADR-026) do not directly
  write to memory. The parent cycle is the only writer.

---

## Alternatives Considered

### Alt A — Vault frontmatter only

Daily.md frontmatter has `## daily_intentions`; weekly.md reads
daily.md + parses YAML. No SQLite.

- **Rejected:** cross-cycle queries are O(N) glob + YAML parse per
  read. No retention policy. No actor scoping. No UEID join key.
  Fails the W4.8 E2E invariant "weekly knows what daily produced"
  because the query has no canonical key.

### Alt B — SQLite only

A single SQLite file with all memory tables; vault markdown is
optional or removed.

- **Rejected:** violates ADR-012 vault_write sole-writer invariant
  (existing skill manifests declare `vault_write: <path>` for weekly,
  monthly, quarterly — removing vault writes would break the
  existing contract). Loses human-readable audit trail. Hard to
  inspect memory by eye.

### Alt C — Hybrid (chosen)

Vault frontmatter for human-readable summaries + SQLite for
structured query + checkpoint DB for per-cycle state (per
ADR-027).

- **Accepted:** gives both queryability AND auditability; UEID
  join keys make memory discoverable from the rest of the system;
  independent retention per layer; append-only invariant extends
  naturally.

### Alt D — Single SQLite file for both checkpoint + memory

Reuse `<root>/data/ikigai_checkpoints.db` for both per-cycle
checkpoints AND cross-cycle memory.

- **Rejected:** retention policies conflict (ADR-027 R10 = 90 days;
  memory = 365 days for monthly). Conflates per-cycle and cross-cycle
  data. Drift detection becomes a 1-table / 2-purpose problem.

### Alt E — Postgres instead of SQLite

Use Postgres for cross-cycle memory (production-grade concurrency +
JSONB columns).

- **Rejected:** violates "fully local" invariant (per `CLAUDE.md`
  §"Global Conventions"). Single-user personal OS does not need
  Postgres. SQLite with WAL mode is sufficient for the volume.

### Alt F — In-memory memory only

Memory lives in `IKIGAiStateDict` for the duration of a session;
no SQLite.

- **Rejected:** breaks W4.8 E2E (multi-level smoke runs across
  multiple sessions); breaks SONHO-level retention (per R8, quarterly
  rows are forever). Without persistence, the pyramid cannot
  span cron windows.

### Alt G — Reuse ADR-027 checkpoint DB rows for cross-cycle reads

The checkpoint DB already stores `prospective_buffer`,
`retrospective_log`, `corrections` per ADR-027 R5.7. Why not read
THOSE rows for cross-cycle aggregation?

- **Rejected:** checkpoint rows are per-LangGraph-invocation,
  with retention `CHECKPOINT_RETENTION_COUNT=1000` (ADR-027 R10).
  A weekly cycle reading the past 7 dailies needs 7 rows; a
  quarterly reading 13 weeks needs 91 rows; a SONHO reading 4
  quarters needs 365+ rows. The retention policy is too
  aggressive. Memory rows are **deliberately longer-lived**.

---

## Forward Dependencies

| Consumer | Field/section consumed | Status |
|----------|------------------------|--------|
| ADR-026 (sub-agent dispatch, DRAFT `3cc9799`) | R9 memory propagation; S2 contract for parent pre-dispatch queries; S3 `append` merge for child writes | DRAFT, awaiting this ADR's accept |
| ADR-027 (stateful subgraph, DRAFT `648b83a`) | R3 4-part UEID discipline; R8 PRAGMA pattern; R9 versioning pattern; R10 retention (separate from this ADR's R8); R11 failure modes | DRAFT, awaiting this ADR's accept |
| W4.4 (sub-agent dispatch node, B-N10, 12-16h) | R9 memory propagation rule; pre-dispatch query pattern | next, blocking on this ADR |
| W4.5 (stateful subgraph consumer, B-N11, 12-16h) | R12 PRAGMA pattern (parallel implementation in `checkpoint_schema.py`) | next, blocking on this ADR |
| **W4.6 (memory layer implementation, B-N12, 12-16h)** | R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13 — ENTIRE ADR | next, blocking on this ADR |
| W4.7 (drift invariants) | R8 JSON keys + R12 PRAGMAs → invariant (o) | next, blocking on this ADR |
| W4.8 (E2E multi-level smoke, B.6, 8-12h) | R5 retrieval patterns; R6 record schemas; R7 cross-cycle data flow | next, blocking on this ADR |

**Key forward dependency: W4.6 (B-N12, 12-16h) ships the 7
implementation deliverables (R13).** This ADR is architectural
decision only; the SQLite schema, the read functions, the
prune-on-write logic, the migrations, and the drift invariant
(o) all land in W4.6 / W4.7.

---

## References

### Load-bearing prior ADRs

- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) —
  planner-only invariant: memory layer stores planner state (UEIDs,
  body markdown, actor, timestamps), never computed values (R6
  schemas are TypedDict, not algorithm outputs).
- **ADR-014 — UEID canonical format (4-part)** (Accepted 2026-09-04)
  — R3 4-part UEID discipline; CHECK constraint on every `*_ueid`
  column; 5-part UEIDs REJECTED.
- **ADR-025 — Skill binding mechanism** (Accepted 2026-09-04, R2
  amended) — R4 actor consistency: every memory write passes
  `actor=manifest["actor"]` (daily = user, weekly/monthly/quarterly
  = agent per shipped R2 table).
- **ADR-012 — vault_write sole writer** (Accepted 2026-08-30) —
  R4 every memory write flows through `vault_write(actor=...)`;
  R2 `audit_sha256` frontmatter links SQLite row to vault file.
- **ADR-019 — QHE → prompt-template constants** (Proposed 2026-09-04
  per W3.2 ship) — R8 4 new keys land in `algorithm_constants.json`;
  drift detector (l) extends at W4.7 ship.
- **ADR-026 — Sub-agent dispatch protocol** (DRAFT 2026-09-04,
  `3cc9799`) — R9 memory propagation respects S2/S3/S5 contracts;
  parent queries before dispatching; children receive derived
  state.
- **ADR-027 — Stateful subgraph strategy** (DRAFT 2026-09-04,
  `648b83a`) — R3 UEID discipline inherited; R8 PRAGMA pattern
  inherited (R12); R9 versioning pattern inherited (R11); R11
  failure mode handling inherited (R10). The two ADRs ship
  parallel artifacts (checkpoint DB vs memory DB) with parallel
  drift invariants (n vs o).

### Code references

- `src/ikigai/src/agents/v2/graph.py:83-94` — `NODES` tuple
  (sub-agent `entry_point` values MUST be in this set; relevant
  for R9 sub-agent memory propagation)
- `src/ikigai/src/agents/v2/graph.py:102-123` — `_safe_node` wrapper
  (R10 failure mode handling: child failures populate `error_type`
  but R9 ensures memory write failure does NOT propagate to parent)
- `src/ikigai/src/agents/v2/graph.py:215-243` — `make_v2_graph`
  factory (R12 PRAGMA pattern at `graph.py:332` mirrors R12
  PRAGMA pattern in `memory_init`)
- `src/ikigai/src/agents/v2/state.py:60` — `PlanTier` enum
  (Sonho → Quarterly → Onda → Weekly → Daily pyramid; R7 data flow)
- `src/ikigai/src/agents/v2/state.py:115-198` — `IKIGAiStateDict`
  (R9 parent injects memory results into child's narrowed slice)
- `src/ikigai/src/agents/v2/state.py:156-162` — operator.add reducers
  (R9 sub-agent memory writes use `append` merge strategy)
- `src/ikigai/src/agents/v2/state.py:189-190` — `actor` field
  (R4 actor source: `manifest["actor"]` per ADR-025 R3)
- `src/ikigai/src/agents/v2/skills/{daily,weekly,monthly,quarterly}.md`
  — R2 vault frontmatter contract; `daily.md:14`, `weekly.md:14`,
  `monthly.md:14`, `quarterly.md:15` declare `vault_write: <path>`
  outputs (already shipped in W3.5 / W3.6)
- `src/ikigai/src/ikigai/vault/vault_write.py:41-67` —
  `vault_write(vault_root, vault_path, frontmatter_fields, body,
  actor=...)` signature (R4 atomic wrapper target)
- `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` —
  14 existing tuning values + 4 new keys (R8) at W4.6 ship
- `src/ikigai/src/agents/v2/prompts/load_constants.py` — loader
  with `_defensive_default()` mirroring JSON exactly (ADR-019 R6)

### Drift detector references

- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_hardcoded_entry_points_*` (drift invariant k, ADR-025 R4)
- `src/ikigai/tests/test_canonical_scope.py` —
  `test_no_algorithm_constants_in_agent_code` (drift invariant l,
  ADR-019 R7) — extends to cover 4 new JSON keys (R8) + UEID 4-part
  regex checks on every `*_ueid` field at W4.7 ship
- `src/ikigai/tests/test_canonical_scope.py` — ADR-027 R11 / W4.7
  drift invariant (n) for checkpoint DB PRAGMAs (parallel to R12
  memory DB PRAGMAs)
- **W4.7 — new drift invariant (o) for memory DB PRAGMAs + JSON-key
  absence + UEID 4-part regex** (planned, this ADR's R12 + R8 + R3)

### Roadmap / spec references

- `docs/superpowers/specs/2026-09-04-dcode-harness-PLAN.md` §3 —
  W4.3 task spec (this ADR)
- `docs/superpowers/specs/2026-09-04-dcode-harness-TASKS.md` —
  W4.3 acceptance criteria (lifecycle, failure modes, prototype
  reference, user review)
- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §2 — lists
  ADR-017 → ADR-028 (renumbered) as one of 6 new ADRs needed for
  Wave 4 Scenario B
- `docs/superpowers/specs/2026-09-04-adr-spec-gap.md` §8 step 4 —
  recommended write order (ADR-027 → ADR-026 → ADR-028; this ADR
  ships third in the Wave 4 architectural triad)

### Memory references

- `memory/wave-3-ship-complete-2026-09-04` — Wave 3 SHIP-COMPLETE
  on commit `be9a370`; drift 24/24 PASS; ruff clean; this ADR
  continues the load-bearing sequence
- `memory/master-branch-carro-chefe-2026-08-28` — canonical master
  branch direction (memory layer lives in
  `src/ikigai/src/agents/v2/`, not `src/operational/` or
  `archive/`)
- `memory/algorithm-scope-reframed-2026-08-30` — IKIGAI = planner
  with stochastic PAE feedback; memory layer stores planner state
  only (R6 schemas)
- `memory/algo-strip-agent-layer-complete-2026-08-31` — agent
  layer stripped of algo execution; memory layer inherits this
  constraint
- `memory/algorithm-gate-dropped-2026-09-03` — algorithm work
  allowed on explicit demand; 4 new JSON keys land via W4.6
  ship-time
- `memory/feedback-precision-calibration-2026-08-28` — when user
  pushes back on X, apply correction NARROWLY (X-not-X), not
  opposite extreme; this ADR's "hybrid, not vault-only" follows
  the same pattern (R7 data flow narrows to pyramid, does not
  over-enforce cross-tier reads)

### Wave 3 + W4.1/W4.2 ship context

- Wave 3 SHIP-COMPLETE on commit `be9a370` (2026-09-04)
- 8/8 tasks shipped: W3.1, W3.2, W3.3, W3.4, W3.5, W3.6, W3.7, W3.8
- Drift detector 24/24 PASS
- Ruff clean on all Wave 3 files
- ADR-025 R2 amended 2026-09-04 to reflect shipped
  (weekly/monthly/quarterly = `observe` + `actor: agent`)
- W4.1 ADR-026 DRAFT at `3cc9799` (sub-agent dispatch)
- W4.2 ADR-027 DRAFT at `648b83a` (stateful subgraph schema)
- W4.3 ADR-028 DRAFT (this ADR — memory layer across cycles)

---

*ADR-028 — DRAFT 2026-09-04 — Wave 4 W4.3 — third leg of Wave 4 architectural triad (after ADR-026 + ADR-027) — gates W4.6 / W4.7 / W4.8 — user review pending*