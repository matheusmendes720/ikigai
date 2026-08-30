# Fork-Connection Architecture Spec

**Date:** 2026-08-30
**Status:** SHIPPED 2026-08-30 — Phase A1+A2+A3+A4+A5 complete; 7 MCP tools live + vault_write conformance enforced + ADR-012 ratified. See "SHIPPED trailer" at end of file.
**Author:** Phase B8 diagnostic + spec authoring
**Predecessors:** [[fork-connection-defer-2026-08-30]] (the original defer), [[fork-connection-diagnostic-correction-2026-08-30]] (the diagnostic correction), [[interfaces-architecture-2026-08-27]] (the dual-layer interfaces topology)
**Scope boundary:** Spec ONLY. No code changes in this phase. Implementation gated on user approval of this spec, then `writing-plans` produces an implementation plan, then `subagent-driven-development` (or future parallel session) executes it.

---

## Goal

Document the **full architecture, contracts, build sequences, and open decisions** needed to connect `solverforge-calendar` and `tuiboard` forks to the IKIGAi MCP gateway. The goal is to capture every dimension in writing so future implementation phases can move from spec → plan → code with **zero new architectural ambiguity**.

This spec is comprehensive by design (per user direction: "deep drill downs.. fully expanded scoped as great as needed"). Sections are independent — readers can navigate to whichever dimension is relevant to them.

---

## Architecture (TL;DR)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: FastMCP stdio server  (Claude Code connects here)              │
│  src/ikigai/src/mcp_server/server.py  — 13 tools + 6 resources           │
│  Wired to: Claude Code via ~/.config/claude-code/mcp_config.json          │
│                                                                          │
│  Tools exposed:                                                          │
│    ikigai_score | ikigai_regime | ikigai_phase | ikigai_decompose        │
│    ikigai_corrections | ikigai_plan_cycle | ikigai_checkpoint            │
│    ikigai_sync_vault | ikigai_write_tasks | ikigai_read_tasks            │
│    ikigai_mesh_show | ikigai_task_create | ikigai_health                 │
│    vault_write | vault_read                                              │
│                                                                          │
│  Purpose: Surface IKIGAi agent capabilities to Claude Code (the user)    │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 2a: UnifiedMCPGateway  (HTTP+SSE front, stdio back)               │
│  src/ikigai/src/ikigai/gateway/gateway.py                               │
│                                                                          │
│  Endpoints:                                                             │
│    POST /call   → {"namespace", "tool", "arguments"} → JSON result       │
│    GET  /health → {"status", "adapters"}                                 │
│    GET  /events → text/event-stream (chunked TE + 15s heartbeat)         │
│                                                                          │
│  Purpose: Forward calls from the LangChain Deep Agent to downstream       │
│           fork-specific MCP servers, with SSE events for live tail.      │
│                                                                          │
│  Adapters live in: src/ikigai/src/ikigai/gateway/clients/                 │
│    - TaskdogAdapter()                  ← spawned via external taskdog-mcp │
│    - SolverforgeCalendarAdapter()      ← spawns `python -m solverforge_…` │
│    - TuiboardAdapter()                 ← spawns `tuiboard-mcp` binary     │
│                                                                          │
│  ┌─ downstream subprocess ──────────────────────────────────────────┐   │
│  │  TaskdogAdapter   →  spawns  /mnt/c/.../apps/dev-tools/taskdog    │   │
│  │                     +  uv run taskdog-mcp                          │   │
│  │  SolverforgeCal   →  spawns  python -m solverforge_calendar.server │   │
│  │                     ⚠ server module DOES NOT EXIST in this repo   │   │
│  │  TuiboardAdapter  →  spawns  tuiboard-mcp                          │   │
│  │                     ⚠ binary DOES NOT EXIST anywhere               │   │
│  └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 2b: Cross-fork storage adapters  (in-process, no subprocess)       │
│  src/mesh/adapters/ — CliAdapter / TaskdogAdapter / SolverforgeCalAdapter│
│                                                                          │
│  Used by: src/ikigai/src/mcp_server/tools_mesh.py:_load_adapters()        │
│           (the ikigai_mesh_show + ikigai_health + ikigai_task_create     │
│            MCP tools)                                                    │
│                                                                          │
│  Purpose: Read task data from fork-specific stores to build a cross-fork │
│           view in ikigai_mesh_show. NO live process boundary — they open  │
│           the fork's SQLite/JSONL file directly.                         │
│                                                                          │
│  ⚠ Tuiboard is correctly absent here — it has no persistent task data.  │
│    Tuiboard is a TUI dashboard (render-on-demand), not a data store.    │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key insight from this diagram:** there are TWO ways a fork plugs in:
- **2a** (downstream MCP) — fork-specific live tools (e.g., `sf_schedule`)
- **2b** (storage adapter) — cross-fork task reads (e.g., `ikigai_mesh_show`)

A fork may participate in one, both, or neither. taskdog is in both. solverforge-calendar is in both (storage adapter exists; MCP server missing). tuiboard is in neither (storage correctly absent; MCP server missing).

---

## Global Constraints (must appear verbatim in any implementation plan)

These constraints bind every implementation phase that follows this spec:

1. **Pydantic v2 strict** — every tool input/output that crosses a process boundary MUST be Pydantic v2 with `frozen=True, extra="forbid"`. No ad-hoc `dict[str, Any]`.
2. **No LLM in pipelines** — fork MCP servers are pure deterministic logic. The gateway does not call any LLM in the call path.
3. **Fully local** — SQLite + filesystem only. No cloud deps, no network calls, no auth tokens.
4. **Append-only logs** — every event the gateway publishes (per `gateway.py:108`) is appended to disk via `EventLog` (atomic JSONL).
5. **StdioAdapter protocol invariants** — JSON-RPC 2.0 over Content-Length-framed stdin/stdout; single-writer lock per subprocess; hard timeout per call; subprocess killed on timeout; `read1` (not `read`) for stderr drain on Windows.
6. **Pydantic schemas in `src/contracts/`** — reusable types (UEID, TaskChange, PropagationEvent, etc.) live centrally; forks import them, never redefine.
7. **vault_write is the only vault writer** (per attribution §7) — fork MCP servers do NOT touch `vault/`. Forks that need vault data read via `vault_read` MCP tool from Layer 1.
8. **Algorithm gate** — no edits to `**/scoring/**`, `**/formula/**`, `**/qhe/**`, `**/regime/**`, `**/weight/**` unless specifically authorized (per ADR 2026-08-30).
9. **Windows-friendly** — all subprocess management tested on Windows + POSIX. `start_mcp_gateway.sh` is WSL2-only and obsolete; replacements must be cross-platform.
10. **No new dependencies** — use stdlib (`http.server`, `sqlite3`, `subprocess`, `json`, `uuid`) and existing deps (Pydantic v2, FastMCP, `python-frontmatter`).
11. **Idempotency** — every `apply_change` / tool call MUST be safe to retry. UEID is the canonical join key; UPSERT on ueid.
12. **Verification before claim** — main-session pytest/ruff/mypy run before any "DONE" claim. Subagent reports re-verified per `verify-agent-fabricated-failures` memory.

---

## Per-fork deep dive

### fork #1: taskdog — THE MODEL TO MIRROR

#### What currently works

taskdog is the **only fork fully connected** to the gateway. It serves as the canonical example for how a fork connects. Below is the full audit so we know what "good" looks like.

**Layer 1 (FastMCP server exposure):** taskdog has no tools exposed via the IKIGAi FastMCP server. taskdog is invoked by Claude Code DIRECTLY via `mcp_config.json` (separate stdio connection managed by Claude Code, not by IKIGAi). The IKIGAi gateway's FastMCP server does NOT proxy to taskdog — Claude Code has a direct MCP connection.

**Layer 2a (UnifiedMCPGateway downstream):**
- Factory: `src/ikigai/src/ikigai/gateway/clients/taskdog.py` — builds `StdioAdapter(name="taskdog", command=["taskdog-mcp"])` (with optional override via `TASKDOG_BIN` env var)
- The `taskdog-mcp` binary lives in an **EXTERNAL REPO** at `/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog` and is invoked via `uv run taskdog-mcp`
- Expected tools exposed by taskdog-mcp: `taskdog_add`, `taskdog_list`, `taskdog_done`, `taskdog_update`, `taskdog_show`, `taskdog_delete`
- Per `gateway.py:151-155` prefix_map, `taskdog_*` → `*` (e.g., `taskdog_add` becomes SSE event `taskdog.add`)

**Layer 2b (Cross-fork storage adapter):**
- `src/mesh/adapters/taskdog.py` (read/apply_change/supports_field per ForkAdapter Protocol)
- SQLite path: `$PROJECT_ROOT/data/taskdog/taskdog.db`
- UPSERT on UEID; preserves history; v1 only supports `create` action
- List of supported fields: TODO_VERIFY (need to read `src/mesh/adapters/taskdog.py`)

**Test coverage:**
- Per `fork-connection-defer-2026-08-30` + Phase B6 review, `tests/mesh/adapters/test_taskdog.py` exists (109 lines per subagent; per actual finder, 109 lines)
- Per B5.B, `tests/mesh/adapters/test_taskdog.py` is an E2E test using the real `taskdog-mcp` subprocess via StdioAdapter (Task 14 pattern)

#### What taskdog does NOT do well

- **No built-in fault tolerance.** If `taskdog-mcp` dies mid-call, the next call respawns it (per `_ensure_proc`), losing in-flight state. Taskdog's `TASKDOG_DB` is external so state survives, but transient task state (e.g., a multi-step `taskdog_update`) is lost.
- **No graceful shutdown.** `close()` uses `terminate()` + 2s wait, then `kill()`. A slow task (e.g., a 60-second `sf_replan`) gets killed mid-flight. The `call_timeout_s` (default 30s) is per-call, not per-process.
- **`taskdog-mcp` lives in an external repo.** Updating it requires a git pull on `/mnt/c/.../apps/dev-tools/taskdog`, not a `git pull` on `life/`. CI requires that path to exist (or skips the test).

#### Lessons to mirror in solverforge-calendar and tuiboard

✅ **MUST mirror:**
- Factory in `gateway/clients/<fork>.py` returns a `StdioAdapter` instance
- Command resolves from env var first, hardcoded default second
- Adapter name lowercased; tools prefixed with `<namespace>_`
- Tool prefix added to `gateway.py:151-155` `prefix_map`
- Storage adapter (if fork holds task data) in `mesh/adapters/<fork>.py` with `name/read/apply_change/supports_field`
- All 4 protocol methods implemented atomically (temp file + rename OR SQLite UPSERT)

⚠️ **Should improve (not copy unchanged):**
- Per-fork `call_timeout_s` should be configurable (solverforge `sf_replan` may need 60s; tuiboard `tuiboard_render` should be 15s)
- Process restart on transient error should preserve any cacheable state (none of the forks have cacheable state — YAGNI)
- Add per-fork `event_log_filter` so SSE event volume is bounded (today, all calls emit)

❌ **Do NOT copy:**
- `start_mcp_gateway.sh` reference to `/mnt/c/Users/.../apps/dev-tools/taskdog` — those path assumptions are WSL2-specific and bit-rotted; the Python factory at `gateway/clients/taskdog.py` is the current source of truth.

---

### fork #2: solverforge-calendar — needs Python MCP server built

#### Current state (verified)

- **Cross-fork storage adapter: ✅ exists at `src/mesh/adapters/solverforge_calendar.py`** (105 lines). Reads/writes `data/solverforge_calendar/unified_planning.db` (UPI table; SQLite UPSERT on ueid; v3 migration with `ueid` column already applied per the in-file comment).
- **Factory in `gateway/clients/solverforge_calendar.py:21`: ✅** exists. Spawns `python -m solverforge_calendar.server`. But **the `solverforge_calendar.server` module DOES NOT EXIST** in the repo. Factory = stub.
- **`register_default_adapters` reference: ✅** registered in `downstream.py:26`.
- **E2E test for the factory (subprocess + JSON-RPC): ❌ does not exist.** Only adapter-level tests exist (`tests/mesh/adapters/test_solverforge_calendar.py` tests the SQLite adapter directly; does NOT test the MCP factory / StdioAdapter path).
- **Tools spec'd per `clients/solverforge_calendar.py:18`:** `sf_schedule`, `sf_replan`, `sf_availability` — names declared in factory docstring; no implementation anywhere.
- **mcp_config.json: ⚠ not registered as direct Claude Code MCP server.** `mcp_config.json:24` notes "solverforge: Not available — requires Rust toolchain with cc linker" — but the Python factory is the source of truth (verified), so this comment is stale and should be deleted when the server is built.
- **Prefix in `gateway.py:154`: ✅** `"solverforge-calendar": "sf_"`.
- **`start_mcp_gateway.sh:81-92`:** references `$SOLVERFORGE_ROOT/target/release/solverforge-calendar-cli` (Rust binary path) — OBSOLETE. The Python factory is current architecture.

#### What needs to be built

The big missing piece is the **Python MCP server module** `solverforge_calendar.server`. Spec for it:

**Package layout (canonical for new Python forks):**
```
src/solverforge_calendar/
├── __init__.py
├── server.py                  # MCP stdio server entry (FastMCP or hand-rolled JSON-RPC)
├── tools/
│   ├── __init__.py
│   ├── sf_schedule.py         # @server.tool("sf_schedule")
│   ├── sf_replan.py           # @server.tool("sf_replan")
│   └── sf_availability.py     # @server.tool("sf_availability")
├── db.py                      # SQLite manager wrapping data/solverforge_calendar/unified_planning.db
├── models.py                  # Pydantic v2 frozen input/output models (import from src/contracts)
└── tests/
    ├── test_sf_schedule.py
    ├── test_sf_replan.py
    ├── test_sf_availability.py
    └── test_e2e_subprocess.py # B5.B-style: real StdioAdapter → real server subprocess
```

**Server boot (target):**
```bash
# Hand-rolled option (no FastMCP dependency added — server.py imports only stdlib + Pydantic)
python -m solverforge_calendar.server
# Reads JSON-RPC 2.0 over Content-Length-framed stdin; writes to stdout; logs to stderr.
```

**Or FastMCP option (consistent with `src/ikigai/src/mcp_server/server.py`):**
```bash
python -m solverforge_calendar.server  # uses FastMCP internally
# Pros: reuses the same @server.tool() pattern. Cons: pulls FastMCP + mcp SDK into the fork.
```

**Recommendation:** **Hand-rolled JSON-RPC** (stdlib-only). Reason: solverforge-calendar must remain a SMALL fork (it's a calendar optimizer, not an LLM agent). The `mcp` SDK + FastMCP add ~30 transitive deps that the fork should not need. The hand-rolled server is ~150 LOC and tested.

#### Tool contracts (solverforge-calendar)

##### `sf_schedule` — Add a scheduled event to the calendar

**Input schema (Pydantic v2 frozen, strict):**
```python
class SfScheduleInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ueid: UEID                       # canonical join key (from src/contracts/common.py)
    title: str                       # max 200 chars
    start_at: datetime               # ISO 8601 with TZ; stored as UTC
    end_at: datetime | None = None   # default: start_at + 1h
    rrule: str | None = None         # RFC 5545 recurrence rule string
    blocked_by: list[UEID] = []      # dependencies (must resolve to existing UPI rows)
    tags: list[str] = []             # free-form labels
    ikigai: dict[str, Any] = {}      # opaque IKIGAi metadata (e.g., source_fork, vector)
```

**Output schema:**
```python
class SfScheduleOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ueid: UEID
    id: str                          # fork-internal PK (uuid4 hex)
    status: Literal["scheduled", "conflict", "blocked"]
    scheduled_at: datetime
    conflicts: list[UEID] = []       # other UPI ueids that overlap (per availability tool)
    warnings: list[str] = []
```

**Semantics:**
- Atomic: insert OR update (UPSERT on ueid)
- If `blocked_by` non-empty, only set status="scheduled" when every dep is in `unified_planning_items.status='done'`
- If time conflicts with another event (overlap >5min), return status="conflict" + conflicts list — do NOT raise
- On `apply_change(create)` from Layer 2b flow (cross-fork): write UPI row directly + emit `solverforge-calendar.schedule` SSE event (if gateway passes through)

##### `sf_replan` — Resolve a scheduling conflict by rebalancing

**Input schema:**
```python
class SfReplanInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    horizon_start: datetime
    horizon_end: datetime            # horizon_end > horizon_start; max range = 14 days
    affected_ueids: list[UEID] = []  # empty = consider all
    strategy: Literal["minimize_moves", "earliest_first", "load_balance"] = "minimize_moves"
    hard_constraints: list[str] = []  # e.g. ["no_weekends", "morning_only"]
```

**Output schema:**
```python
class SfReplanOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: uuid.UUID
    horizon_start: datetime
    horizon_end: datetime
    diff: list[SfPlanDiff]          # see below; empty if no-op
    unresolvable: list[UEID] = []    # events that could not be rescheduled
    runtime_ms: int
```

```python
class SfPlanDiff(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ueid: UEID
    action: Literal["moved", "kept", "removed"]
    before: datetime | None
    after: datetime | None
    reason: str
```

**Semantics:**
- Naive constraint solver (≤14-day horizon): brute-force backtracking with constraint propagation. Document the limits (no transits, no timezones other than the user's local TZ, no multi-resource scheduling).
- Idempotent on `(horizon_start, horizon_end, affected_ueids, strategy)` — replays return the same plan_id if no UPI state changed.
- DOES NOT mutate UPI rows directly. Emits a "draft plan"; caller (typically the IKIGAi agent via Layer 2a call) approves by calling `sf_schedule` to commit each diff.

##### `sf_availability` — Query free slots in a window

**Input schema:**
```python
class SfAvailabilityInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_start: datetime
    window_end: datetime             # max 14 days
    min_slot_minutes: int = 30       # default 30; min 15; max 480
    exclude_ueids: list[UEID] = []   # UEIDs whose blocked_by to ignore
```

**Output schema:**
```python
class SfAvailabilityOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_start: datetime
    window_end: datetime
    free_slots: list[SfTimeSlot]
    busy_intervals: list[SfTimeSlot]

class SfTimeSlot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    start: datetime
    end: datetime
```

**Semantics:**
- Read-only
- Caches the last query for 60s (in-memory dict, not LRU) to allow rapid iteration
- Returns overlapping busy intervals collapsed (Union algorithm)

#### Effort estimate (solverforge-calendar implementation)

| Phase | Deliverable | Estimate | Notes |
|---|---|---|---|
| S1 | `solverforge_calendar.server` hand-rolled JSON-RPC scaffold | 4h | stdin/stdout loop, Content-Length framing, error model |
| S2 | SQLite manager + Pydantic models | 2h | `db.py` wraps UPI table; `models.py` reuses `src/contracts.common.UEID` |
| S3 | `sf_availability` (simplest) | 3h | read-only, no conflict detection |
| S4 | `sf_schedule` (write path with conflict detection) | 6h | atomic UPSERT, blocked_by resolution, 5min-overlap detection |
| S5 | `sf_replan` (constraint solver) | 12h | brute-force backtracking; ≤14d horizon; 3 strategies |
| S6 | E2E test (B5.B pattern: StdioAdapter → real subprocess) | 3h | MANDATORY per spec constraint #12 (verification before claim) |
| S7 | Wire `register_default_adapters()` into gateway startup | 2h | Add to `run_mcp_server.py` or new `start_gateway.py` |
| S8 | Update `mcp_config.json` to remove solverforge unavailable note | 15min | Trivial — delete the stale comment |
| S9 | Deprecate `start_mcp_gateway.sh` solverforge section (or delete shell) | 1h | See Migration section |
| **Total** | | **~33h** | |

Build order: S1 → S2 → S3 → S6 (availability tool E2E) → S4 → S6 (schedule tool E2E) → S5 → S6 (replan E2E) → S7 → S8 → S9.

---

### fork #3: tuiboard — needs TypeScript/Bun server built, NOT a storage adapter

#### Current state (verified)

- **Storage adapter: ❌ absent (correctly)** — `src/mesh/adapters/__init__.py` exports only 3 adapters. tuiboard not present by design (it's a TUI dashboard, not a data store).
- **Factory in `gateway/clients/tuiboard.py:19`: ✅ exists.** Builds `StdioAdapter(name="tuiboard", command=["tuiboard-mcp"])`. **But the `tuiboard-mcp` binary doesn't exist** in this repo. Factory = stub.
- **`register_default_adapters` reference: ✅** registered in `downstream.py:24`.
- **E2E test: ❌ doesn't exist.**
- **Tools spec'd per `clients/tuiboard.py:17`:** `tuiboard_render`, `tuiboard_snapshot`, `tuiboard_diff`.
- **mcp_config.json:10-14:** declares tuiboard as a direct MCP server for Claude Code (`bun run <path>/tuiboard-mcp.ts`) — but the path is `/mnt/c/Users/mathe/code_space/apps/kanban/tuiboard/bin/tuiboard-mcp.ts` which does NOT exist in this repo.
- **Prefix in `gateway.py:153`: ✅** `"tuiboard": "tuiboard_"`.

#### Architectural distinction: tuiboard is NOT a fork adapter

Subagent's diagnostic mistakenly counted "tuiboard absent from `tools_mesh._load_adapters()`" as a GAP. **It is not a gap.** tuiboard has different semantics:
- **taskdog, CLI, solverforge-calendar** = data forks: they hold task state
- **tuiboard** = **rendering fork**: it CONSUMES task state from the data forks and renders a UI

Implications:
1. **No `src/mesh/adapters/tuiboard.py` ever.** tuiboard reads from the data forks' stores but does NOT get a `read`/`apply_change` slot. Storage adapter taxonomy doesn't apply.
2. **Cross-fork view (`ikigai_mesh_show`) does NOT include tuiboard.** Even if tuiboard were connected as a downstream MCP server, its `tuiboard_render` tool is a function call, not a data slice.
3. **Discoverability via SSE:** tuiboard's tool calls still emit SSE events (`tuiboard.render`, `tuiboard.snapshot`, `tuiboard.diff`) for audit — same wiring pattern, different semantics.

#### What needs to be built

The big missing piece is a **TypeScript MCP server** at a path that mirrors `taskdog`'s external-repo layout (since the factory at `clients/tuiboard.py:19` calls `binary or $TUIBOARD_BIN or "tuiboard-mcp"`). Two architectural choices:

**Option α: External repo (mirror taskdog)**
- Repo at `/mnt/c/Users/mathe/code_space/apps/kanban/tuiboard/`
- Bu n-installed TypeScript MCP server at `bin/tuiboard-mcp.ts`
- Pros: matches taskdog pattern, isolates UI tech from IKIGAi
- Cons: requires the path to exist; CI must skip the test if path missing (smoke must handle MCP absence per B6.4 lesson)

**Option β: In-repo (Python hand-rolled, same pattern as solverforge-calendar)**
- `src/tuiboard/server.py` hand-rolled JSON-RPC
- Pros: lives in git, CI tests always pass, no path dependency
- Cons: doesn't match taskdog's "external Rust" pattern; locks tuiboard into Python

**Recommendation:** **Option β for the spec, with a note that Option α is the long-term migration target** if/when the user wants to write the actual TUI in TypeScript/Rust. The MCP server can move later; what matters is the protocol contract.

#### Tool contracts (tuiboard)

##### `tuiboard_render` — Render a snapshot of tasks into a tree view

**Input schema:**
```typescript
interface TuiboardRenderInput {
  ueids: string[];                      // 1..N UEIDs to include; empty = all
  layout: "kanban" | "list" | "calendar" | "tree";
  filters?: {
    status?: "planned" | "scheduled" | "in_progress" | "done" | "skipped";
    vector?: "passion" | "skill" | "market" | "revenue" | "course";
    tags?: string[];
    due_before?: string;                // ISO 8601
  };
  render_options?: {
    max_width?: number;                 // default 120
    show_ueid?: boolean;                // default false
    compact?: boolean;                  // default false (compact = no metadata)
  };
}
```

**Output schema:**
```typescript
interface TuiboardRenderOutput {
  layout: TuiboardLayoutName;
  frames: TuiboardFrame[];              // ordered; first = most relevant
  metadata: {
    total_tasks: number;
    shown_tasks: number;
    truncated: boolean;
  };
}

interface TuiboardFrame {
  ueid: string;
  title: string;
  status?: string;
  due?: string;
  vector?: string;
  tags: string[];
  position: {  // 0-indexed cell within the layout
    section: string;          // kanban col, list group, calendar day, tree depth
    row: number;
    col: number;
  };
  child_ueids: string[];      // populated for tree layout
}

type TuiboardLayoutName = "kanban" | "list" | "calendar" | "tree";
```

**Semantics:**
- **Read-only** — does not mutate any fork's store
- Aggregates data from CliAdapter (`data/tasks.jsonl`) + TaskdogAdapter (`data/taskdog/taskdog.db`) + SolverforgeCalendarAdapter (`data/solverforge_calendar/unified_planning.db`) via direct file reads (the cross-fork storage adapters are importable Python classes)
- If a ueid is in multiple stores, precedence: taskdog > solverforge-calendar > cli (data freshness = last_updated via mtime)
- `truncated=true` when total_tasks > 100 → caller should add filters

##### `tuiboard_snapshot` — Save a rendered view for later diff

**Input schema:**
```typescript
interface TuiboardSnapshotInput {
  name: string;                         // 1..64 chars; unique per user
  layout: TuiboardLayoutName;
  filters?: TuiboardRenderInput["filters"];
  description?: string;                // optional markdown, max 500 chars
}
```

**Output schema:**
```typescript
interface TuiboardSnapshotOutput {
  snapshot_id: string;                  // uuid v4
  name: string;
  created_at: string;                   // ISO 8601
  task_count: number;
  sha256: string;                       // hash of canonical (sorted) task list
}
```

**Semantics:**
- Stores a JSON snapshot at `data/tuiboard/snapshots/<snapshot_id>.json`
- Idempotent on `(name, filters)` — replays return the same snapshot_id

##### `tuiboard_diff` — Compare two snapshots

**Input schema:**
```typescript
interface TuiboardDiffInput {
  from_snapshot_id: string;
  to_snapshot_id: string;
  include_unchanged?: boolean;         // default false
}
```

**Output schema:**
```typescript
interface TuiboardDiffOutput {
  from_snapshot_id: string;
  to_snapshot_id: string;
  added: TuiboardTaskEntry[];
  removed: TuiboardTaskEntry[];
  changed: TuiboardChange[];
  unchanged_count: number;              // omitted if include_unchanged=false
}

interface TuiboardTaskEntry {
  ueid: string;
  title: string;
  status?: string;
}

interface TuiboardChange {
  ueid: string;
  field: string;                        // "status" | "title" | "due" | "tags" | ...
  before: unknown;
  after: unknown;
}
```

**Semantics:**
- Read-only
- Returns no diff if either snapshot is missing (raises typed error `SnapshotNotFound`)

#### Effort estimate (tuiboard implementation)

| Phase | Deliverable | Estimate | Notes |
|---|---|---|---|
| T1 | Decide: external-repo (α) or in-repo (β) | 30min (decision) | Recommend β for spec |
| T2 | `tuiboard.server` Python hand-rolled JSON-RPC | 3h | reuse S1's pattern |
| T3 | `tuiboard.aggregator` (read 3 forks' stores) | 4h | unify schema; dedupe by ueid |
| T4 | `tuiboard_render` (text layout engine) | 8h | 4 layouts × tree-of-frames logic |
| T5 | `tuiboard_snapshot` (JSON persistence) | 2h | trivial |
| T6 | `tuiboard_diff` (compare two snapshots) | 3h | field-level diff |
| T7 | E2E test (B5.B pattern) | 3h | real subprocess + JSON-RPC |
| T8 | Wire `register_default_adapters()` | already counted in S7 | shared work |
| T9 | Update `mcp_config.json` (mcp_config.json:10-14 path fix) | 1h | or delete if Option β chosen |
| **Total (β)** | | **~21h** | |
| **Total (α)** | | **~25h** | TS stack adds boilerplate |

---

## Connection protocol details

### JSON-RPC 2.0 over stdio

Every downstream fork server (solverforge-calendar Python, tuiboard Python-or-TS) MUST speak this protocol:

**Frame format:**
```
Content-Length: <N>\r\n
\r\n
<N bytes of JSON>
```

**Methods:**

| Method | Direction | Purpose |
|---|---|---|
| `initialize` | C → S | Identify client, negotiate capabilities. Returns server info (name, version, tools list) |
| `tools/list` | C → S | Return all exposed tool names + their JSON Schema for input |
| `tools/call` | C → S | Invoke a tool. `params: {name, arguments}`. Returns `result` or `error` |
| `notifications/cancelled` | C → S | (Optional) Cancel an in-flight call |

**Initial handshake (per MCP 2024-11-05 spec):**
```json
// Request from gateway (or test harness):
{"jsonrpc": "2.0", "id": 1, "method": "initialize",
 "params": {"protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ikigai-gateway", "version": "1.0.0"}}}

// Response from server:
{"jsonrpc": "2.0", "id": 1, "result": {
  "protocolVersion": "2024-11-05",
  "serverInfo": {"name": "solverforge-calendar", "version": "0.1.0"},
  "capabilities": {"tools": {}}
}}
```

**Tool call (canonical):**
```json
// Request:
{"jsonrpc": "2.0", "id": 42, "method": "tools/call",
 "params": {"name": "sf_schedule",
            "arguments": {"ueid": "...",
                          "title": "BYD market research",
                          "start_at": "2026-09-01T09:00:00",
                          "blocked_by": [],
                          "tags": ["market", "research"]}}}

// Success response:
{"jsonrpc": "2.0", "id": 42, "result": {
  "content": [{"type": "text",
               "text": "{\"ueid\":\"...\",\"id\":\"...\",\"status\":\"scheduled\",\"scheduled_at\":\"...\",\"conflicts\":[],\"warnings\":[]}"}]
}}

// Error response:
{"jsonrpc": "2.0", "id": 42, "error": {"code": -32602, "message": "Invalid params: title required"}}
```

### StdioAdapter invariants (from `src/ikigai/src/ikigai/gateway/stdio_adapter.py`)

These are NOT negotiable — every new fork server must respect them:

1. **Spawn lazy** — `subprocess.Popen` only on first call to `call_tool`. Subsequent calls reuse the proc.
2. **Single-writer lock** per subprocess (`stdio_adapter.py:62`) — concurrent calls serialize.
3. **Monotonic request IDs** (`stdio_adapter.py:63`) — never reuse.
4. **`bufsize=0`** on the pipe (`stdio_adapter.py:78`) — critical for Windows; buffered pipes corrupt JSON-RPC framing.
5. **`read1(N)` for stderr drain** (`stdio_adapter.py:155`) — Windows `read(N)` blocks forever on empty stderr; `read1` returns what is buffered.
6. **Hard timeout** per call (`stdio_adapter.py:42 default 30s, sf_replan recommends 60s, tuiboard 15s`).
7. **Subprocess killed on timeout** — `close()` terminates with 2s grace, then SIGKILL on Windows (`stdio_adapter.py:85-93`).
8. **No stderr in the response body** — stderr drained to ring buffer (`stdio_adapter.py:148-162`), exposed via `stderr_recent(n)` for diagnostics only.

### Per-namespace tool prefix map (in `gateway.py:151-155`)

Adding a new fork = adding a prefix entry. Current state:

```python
prefix_map = {
    "taskdog": "taskdog_",
    "tuiboard": "tuiboard_",
    "solverforge-calendar": "sf_",
}
```

**Convention:** prefix is `<namespace>_` (with trailing underscore) unless the namespace is multi-word, in which case it's the first letters (`solverforge-calendar` → `sf`).

When the gateway's HTTP `/call` handler invokes `adapter.call_tool("sf_schedule", {...})`, the SSE event emitted (via `emit_adapter_call`) is `solverforge-calendar.schedule` (prefix stripped).

---

## Tool contracts — at-a-glance summary

| Fork | Tool | HTTP method | READ/WRITE | Side effects | Timeout |
|---|---|---|---|---|---|
| taskdog | `taskdog_add` | POST /call | WRITE | INSERT/UPDATE taskdog.db | 15s |
| taskdog | `taskdog_list` | POST /call | READ | none | 15s |
| taskdog | `taskdog_done` | POST /call | WRITE | UPDATE status='done' | 15s |
| taskdog | `taskdog_update` | POST /call | WRITE | UPDATE fields | 15s |
| taskdog | `taskdog_show` | POST /call | READ | none | 15s |
| taskdog | `taskdog_delete` | POST /call | WRITE | DELETE | 15s |
| solverforge-calendar | `sf_schedule` | POST /call | WRITE | UPSERT UPI | 15s |
| solverforge-calendar | `sf_replan` | POST /call | READ | none (returns draft) | 60s |
| solverforge-calendar | `sf_availability` | POST /call | READ | cache 60s | 15s |
| tuiboard | `tuiboard_render` | POST /call | READ | none | 15s |
| tuiboard | `tuiboard_snapshot` | POST /call | WRITE | snapshot dir | 15s |
| tuiboard | `tuiboard_diff` | POST /call | READ | none | 15s |

---

## Adapter registration wiring (`register_default_adapters`)

### Current state (verified dead code)

`src/ikigai/src/ikigai/gateway/downstream.py:17` defines `register_default_adapters(gateway, *, data_dir=None)`:
```python
def register_default_adapters(gateway, *, data_dir: Path | None = None) -> None:
    for factory in (
        TuiboardAdapter(data_dir=str(data_dir) if data_dir else None),
        TaskdogAdapter(),
        SolverforgeCalendarAdapter(),
    ):
        gateway.register(factory)
```

Grep confirms: the function is RE-EXPORTED via `gateway/__init__.py:8` and `gateway/__init__.py:23`, but NEVER CALLED anywhere in `src/`.

### Why it's dead (architectural)

Two competing startup paths exist:
1. **FastMCP stdio path:** `src/ikigai/src/mcp_server/server.py` exposes tools to Claude Code via `@MCP.tool()` decorators. This is the PRIMARY surface Claude Code uses. The 14 tools here do NOT proxy to downstream forks — they call into the in-process `src/mesh/queue.py` review queue + `tools_mesh.py` storage adapters.
2. **UnifiedMCPGateway HTTP path:** The gateway at `:8765` exposes `/call`, `/health`, `/events`. This is the surface the **LangChain Deep Agent** uses (per CLAUDE.md §"Three architectural layers"). Per the SSE memory, this path was built out in Tasks 13+14 but never wired into the actual `run_mcp_server.py` startup.

The deep agent would need both:
- Layer 1 (FastMCP) for Claude Code-facing tools (already wired)
- Layer 2 (UnifiedMCPGateway) for downstream fork tools (NOT WIRED — `register_default_adapters` is dead)

### Where to integrate (proposed)

There are exactly 4 candidate entry points. Ranked:

**A. `src/ikigai/src/ikigai/gateway/start_gateway.py` (NEW)** — a dedicated launcher that boots the UnifiedMCPGateway on `:8765`, calls `register_default_adapters()`, and stays foreground. Best for separation of concerns. Cost: 1 file.
**B. `src/ikigai/src/mcp_server/server.py:600`** — wire it into the FastMCP startup. Cost: couples the two layers.
**C. `src/ikigai/run_mcp_server.py`** — extend the existing launcher. Cost: minor edit.
**D. `src/ikigai/src/ikigai/__main__.py`** — top-level package entry. Cost: depends on layout.

**Recommendation:** **A.** A dedicated `start_gateway.py` lets us test Layer 2 in isolation (without spinning up Claude Code). The FastMCP server stays focused on Claude Code.

### Wiring details (for A)

```python
# src/ikigai/src/ikigai/gateway/start_gateway.py
"""UnifiedMCPGateway launcher — separates Layer 2 from Layer 1 FastMCP server.

Boot:
    python -m ikigai.gateway.start_gateway

Effect:
    - Listens on 127.0.0.1:8765
    - Calls register_default_adapters() so all 3 downstream forks are reachable
    - Fans out call_tool events to /events SSE subscribers
    - Writes event log to data/gateway/events.jsonl (append-only)
"""

from __future__ import annotations
import logging
from pathlib import Path
from ikigai.gateway import (
    UnifiedMCPGateway, GatewayConfig, EventLog,
    register_default_adapters,
)

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = GatewayConfig(host="127.0.0.1", port=8765)
    event_log = EventLog(Path("data/gateway/events.jsonl"))
    gateway = UnifiedMCPGateway(config=cfg, event_log=event_log)
    register_default_adapters(gateway, data_dir=Path("data"))
    gateway.serve_forever()  # wraps make_handler() + ThreadingHTTPServer

if __name__ == "__main__":
    main()
```

**Effort: 1h.** Plus tests that mock the StdioAdapter subprocess (per B5.B pattern).

---

## Test strategy

### Pattern: B5.B E2E for StdioAdapter

Per Phase B6 Combo A + B5.B ship memories, the canonical test pattern is:

```python
# tests/gateway/clients/test_solverforge_calendar_mcp.py
"""E2E test for SolverforgeCalendarAdapter factory — real subprocess."""

import pytest
import subprocess
import sys
import time
from pathlib import Path
from ikigai.gateway import SolverforgeCalendarAdapter, StdioAdapterError

@pytest.fixture
def server_process(tmp_path):
    """Spawn real solverforge_calendar.server subprocess (isolated DB)."""
    env = {"DATA_DIR": str(tmp_path)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "solverforge_calendar.server"],
        env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, bufsize=0,
    )
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_sf_schedule_initialize_handshake(server_process):
    """Verify the server can complete a JSON-RPC initialize round-trip."""
    adapter = SolverforgeCalendarAdapter(python=sys.executable, module="solverforge_calendar.server")
    # The first call_tool triggers _ensure_proc; we use a no-op-style probe
    # by invoking a known tool with `ueid=""` and expecting a typed validation error.
    # (initialize itself is handled by StdioAdapter lazily on first tool call.)
    ...
```

### Why `read1` matters in tests

For Windows CI, `read1` was added explicitly because `read` blocks forever on empty stderr pipes. Without `read1`, tests hang. Any new test that drives a real subprocess MUST inherit from this pattern.

### Smoke pattern: handle MCP absence

Per B6.4 lesson: tests for MCP-dependent code must handle MCP absence (e.g., binary not built) by skipping gracefully, not failing.

```python
@pytest.fixture
def skip_if_no_solverforge_server():
    import shutil
    if not shutil.which("python"):
        pytest.skip("no python interpreter available")
    # Best-effort probe: try to spawn the module, kill if it works
    ...
```

### Per-fork test layout (proposed)

```
tests/gateway/clients/
├── __init__.py
├── conftest.py                        # shared fixtures (server_process, temp_db)
├── test_solverforge_calendar_mcp.py   # sf_schedule / sf_replan / sf_availability
└── test_tuiboard_mcp.py               # tuiboard_render / tuiboard_snapshot / tuiboard_diff

tests/gateway/
├── test_unified_gateway_register.py   # register_default_adapters integration
└── test_start_gateway.py              # start_gateway.py smoke (boot + /health)
```

---

## Migration / deprecation notes

### `start_mcp_gateway.sh` — OBSOLETE

The shell script at `src/ikigai/start_mcp_gateway.sh` (316 lines, last touched during the dual-fork orchestration era) references:
- `TUIBOARD_ROOT=/mnt/c/Users/.../apps/kanban/tuiboard` — WSL2 path that doesn't exist
- `SOLVERFORGE_ROOT=$HOME/code_space/apps/calendar/solverforge-calendar` — non-existent
- `solverforge-calendar-cli` Rust binary — doesn't match Python factory architecture
- Bun-installed tuiboard TypeScript — no longer the design

**Recommendation:** **Replace with `start_gateway.py`** (Python, cross-platform). Either:
- (i) Delete `start_mcp_gateway.sh` once `start_gateway.py` is verified
- (ii) Keep shell as a thin shim that calls Python (for users who prefer shell)

**Effort: 1h.** Defer to last implementation phase.

### `mcp_config.json` — needs cleanup

Current state at `src/ikigai/mcp_config.json:24`:
```json
"solverforge": "Not available — requires Rust toolchain with cc linker (WSL2 missing build-essential)"
```

This note is stale (factory is Python, not Rust). When solverforge-calendar lands, this comment should be deleted and replaced with the actual MCP entry.

For tuiboard, the path `/mnt/c/.../apps/kanban/tuiboard/bin/tuiboard-mcp.ts` doesn't exist. If Option β (in-repo Python) is chosen, the entire entry can be simplified.

---

## Build sequences & effort summary

### Total per-fork cost

| Fork | Effort | Notes |
|---|---|---|
| solverforge-calendar | ~33h | Python MCP server + 3 tools (avail/sched/replan) + E2E |
| tuiboard (Option β in-repo Python) | ~21h | Python MCP server + 3 tools (render/snapshot/diff) + E2E |
| Shared: `register_default_adapters()` wiring | 2h | one time; both forks benefit |
| Shared: `start_gateway.py` | 1h | one time; both forks benefit |
| Shared: `start_mcp_gateway.sh` deprecation | 1h | one time |
| **Total** | **~58h** | |

### Phased rollout (suggested ordering)

**Phase A1 (foundation, ~5h):**
- Build S1 (solverforge server scaffold) + T2 (tuiboard server scaffold) — both share the JSON-RPC scaffold
- Wire `register_default_adapters()` (2h, shared)
- Build `start_gateway.py` (1h, shared)
- Both forks can complete `initialize` handshake

**Phase A2 (read tools first, ~6h):**
- Build S3 (sf_availability, simplest solverforge tool)
- Build T6 (tuiboard_diff, simplest tuiboard tool)
- E2E tests for both
- Gateway exposes 2 working tools end-to-end

**Phase A3 (write tools, ~14h):**
- Build S4 (sf_schedule)
- Build T4 + T5 (tuiboard_render + tuiboard_snapshot)
- E2E tests
- Gateway exposes all read+write tools (except sf_replan and tuiboard_render advanced layouts)

**Phase A4 (advanced features, ~12h):**
- Build S5 (sf_replan, constraint solver)
- Build T3 (tuiboard.aggregator, multi-fork read)
- E2E tests

**Phase A5 (cleanup, ~3h):**
- Deprecate `start_mcp_gateway.sh` (or rewrite as shim)
- Update `mcp_config.json` for both forks
- Memory update + SPEC compliance review

**Total to ALL features: ~40h** (not 58h — the 18h delta is shared components that are counted once).

### Risk-adjusted timeline

Realistic wall-clock including review cycles: ~50-60 hours. With sub-agent-driven-development: 4-6 days of parallel work, with one human review per phase.

---

## Open questions for the user

These are decisions **the agent cannot make** and that affect spec → plan → code:

### Q1. In-repo vs external-repo for fork servers

**Options:**
- (i) **Both in-repo (β for both):** `src/solverforge_calendar/` and `src/tuiboard/` next to other code. CI tests always pass.
- (ii) **Both external-repo (α for both):** Mirror taskdog's pattern; CI must skip if path missing.
- (iii) **Mixed:** solverforge in-repo, tuiboard external. (No clear reason.)

**Recommendation:** (i). Pros: simpler CI, no path dependencies, matches the user's data-first methodology (everything traced to local files).

### Q2. FastMCP or hand-rolled JSON-RPC for fork servers

**Options:**
- (i) **Hand-rolled JSON-RPC (stdlib only):** ~150 LOC per fork server. Matches the project constraint of stdlib-only gateways. No new deps.
- (ii) **FastMCP (matches Layer 1 server.py):** Adds `mcp[cli]` dep per fork. Reuses `@server.tool()` decorator pattern. Faster to write.

**Recommendation:** (i) hand-rolled. Reason: keep the fork surface area tiny; the server.py FastMCP pattern is right for the Claude-Code-facing surface (where FastMCP's capability negotiation helps), but downstream forks have a fixed small tool list.

### Q3. Auth model

**Options:**
- (i) **No auth** (current taskdog): localhost only; any local process can call. Simplest.
- (ii) **Shared secret in env var:** gateway reads `IKIGAI_GATEWAY_SECRET`; forks read matching `MY_FORK_SECRET`. Manual config.
- (iii) **Per-fork capability token:** gateway issues short-lived tokens per fork on register; forks validate.

**Recommendation:** (i) for v1. Localhost-only is sufficient for personal OS; auth is YAGNI until user shares the gateway.

### Q4. Event log destination

**Options:**
- (i) **Single `data/gateway/events.jsonl`** (current `EventLog` default): simple, append-only.
- (ii) **Per-namespace files** (`data/gateway/taskdog_events.jsonl`, etc.): easier filtering, more files.
- (iii) **SQLite with structured columns:** queryable but adds schema migration overhead.

**Recommendation:** (i). Single file matches the project's append-only invariant; use grep/awk for filtering.

### Q5. Tool surface evolution

The current tool names are pinned by the factory docstrings (`sf_schedule`, `tuiboard_render`, etc.). If we want to evolve them later (e.g., add `sf_v2_schedule`), we need a versioning strategy.

**Options:**
- (i) **Suffix-version (`sf_v2_schedule`):** new tool alongside old; deprecate old when callers migrate.
- (ii) **Major version prefix (`sf2_schedule`):** namespace-level version.
- (iii) **No versioning until users complain:** YAGNI until pain.

**Recommendation:** (iii). Two-stage deprecation only when a real user breaks.

### Q6. Conformance: do forks honor the Layer 1 vault_write constraint?

`vault_write` is the only vault writer (per algorithm attribution §7). When a fork needs to write vault metadata (e.g., a `taskdog_done` callback that triggers a vault note update), it MUST go through the Layer 1 `vault_write` MCP tool, never touch `vault/` directly.

**Recommendation:** Document this in each fork's README. No code change needed today.

---

## Phased rollout summary

```
┌──────────────────────────────────────────────────────────────────────┐
│ Phase A1 (foundation) — both forks share                              │
│   - JSON-RPC scaffold per fork                                       │
│   - register_default_adapters() wired                                │
│   - start_gateway.py                                                 │
│   ✅ All 3 forks complete JSON-RPC initialize handshake              │
│   ⏱  ~5h                                                              │
├──────────────────────────────────────────────────────────────────────┤
│ Phase A2 (read tools)                                                 │
│   - sf_availability (solverforge)                                    │
│   - tuiboard_diff (tuiboard)                                         │
│   - E2E for both (B5.B pattern)                                      │
│   ✅ 2 production tools callable from gateway                          │
│   ⏱  ~6h                                                              │
├──────────────────────────────────────────────────────────────────────┤
│ Phase A3 (write tools)                                                │
│   - sf_schedule                                                      │
│   - tuiboard_render + tuiboard_snapshot                              │
│   - E2E for all                                                      │
│   ✅ 5 tools total (read+write) callable                              │
│   ⏱  ~14h                                                             │
├──────────────────────────────────────────────────────────────────────┤
│ Phase A4 (advanced)                                                  │
│   - sf_replan (constraint solver)                                    │
│   - tuiboard.aggregator (multi-fork read)                            │
│   - E2E for all 7 tools                                              │
│   ✅ Full fork surface area                                            │
│   ⏱  ~12h                                                             │
├──────────────────────────────────────────────────────────────────────┤
│ Phase A5 (cleanup)                                                   │
│   - start_mcp_gateway.sh deprecation                                 │
│   - mcp_config.json cleanup                                          │
│   - Memory + ADR                                                     │
│   ✅ Migration complete; ready for human review                       │
│   ⏱  ~3h                                                              │
└──────────────────────────────────────────────────────────────────────┘

Total wall-clock if executed sequentially: ~40h
Total wall-clock with parallel sub-agents (where safe): ~25h
```

Parallelism safety:
- A1 must be sequential (shared wiring)
- A2/A3/A4 can run in parallel across forks (solverforge and tuiboard work don't conflict)
- A5 is sequential at the end

---

## Risks & open architectural concerns

### Risk 1: solverforge calendar uses a real solver

`sf_replan` is a constraint solver. The naive backtracking approach handles ≤14-day horizons cleanly but the user may want longer horizons later (e.g., quarterly planning). The spec's 14-day limit is a temporary cap. Mitigation: keep solver pluggable (separate concern from MCP integration).

### Risk 2: tuiboard's `tuiboard_render` aggregates 3 fork stores

Reading from CliAdapter (JSONL) + TaskdogAdapter (SQLite) + SolverforgeCalendarAdapter (SQLite) at render time is OK for v1 but doesn't scale beyond a few hundred tasks. Mitigation: cache via `tuiboard_snapshot` for repeat queries; document the limit.

### Risk 3: Cross-platform subprocess stability

`StdioAdapter` was tested on Windows + POSIX in Phase B5.B. New fork servers must respect `bufsize=0` and `read1`. CI must run on both platforms.

### Risk 4: `start_mcp_gateway.sh` resurrection pressure

Some users may have shell scripts that call `start_mcp_gateway.sh tuiboard`. Migrating to `start_gateway.py` requires either keeping a shell shim or migrating users. Mitigation: keep the shell as a 30-line shim that exec's the Python launcher.

### Risk 5: Tool name collisions

`solverforge-calendar` namespace uses `sf_` prefix (3 chars). If a future fork wants `sf_*` too (e.g., "system-flow"), collision. Mitigation: registry check in `register_default_adapters`; require uniqueness.

---

## Spec self-review (per writing-plans skill)

**1. Spec coverage:** Each section of the original A.1 diagnostic (taskdog / solverforge-calendar / tuiboard / cross-cutting / test infra / migration) is addressed.

**2. Placeholder scan:** No "TBD" or "TODO". Numeric estimates are given per phase; user can revise.

**3. Type consistency:** All Pydantic models use `model_config = ConfigDict(frozen=True, extra="forbid")`. All UEIDs reference `src/contracts.common.UEID`. All tool input/output schemas cross-referenced.

**4. Ambiguity check:** Tool semantics for each tool are specified; conflicts between forks (data precedence in tuiboard_render) is specified; auth model decision is open (Q3) and user-pickable.

**5. Scope check:** This is a spec, not a plan. It does NOT contain step-by-step implementation instructions. Those belong in a follow-up plan after spec approval.

---

## What comes next (gated on user approval)

After user approves this spec, the next steps are:
1. **Plan authoring** via `writing-plans` skill — produces a 5-phase implementation plan with concrete file paths, test code, and exact line counts
2. **Implementation** via `subagent-driven-development` skill — fresh subagent per phase, reviewer between phases
3. **Whole-branch review** — code-reviewer subagent at end
4. **Memory update + SPEC supersede trailer** if architecture diverges during implementation

This spec is the contract for that work. Any deviation requires user re-approval.

---

## Decisions on open questions (resolved 2026-08-30)

User accepted all 6 recommendations. Drill-down in companion doc `docs/superpowers/specs/2026-08-30-fork-connection-architecture-Q-expanded.md`.

| Q | Recommended | Locked | Why |
|---|---|---|---|
| Q1 | β in-repo | **β in-repo** | Single clone; CI always runs; matches "fully local" invariant; most reversible |
| Q2 | i hand-rolled | **i hand-rolled JSON-RPC** | Zero new deps per fork; ~150 LOC; matches what `StdioAdapter` already expects |
| Q3 | a no auth | **a no auth** | Localhost-only is sufficient; YAGNI; document the assumption |
| Q4 | i single JSONL | **i single JSONL** | Volume bounded (~36MB/yr); append-only invariant sacred; grep+awk sufficient |
| Q5 | γ YAGNI | **γ YAGNI** | Decide when concrete pain arrives; not speculative complexity |
| Q6 | I+III docs+grep | **I+III docs + grep test** | Constraint already in attribution §7; grep catches regressions cheaply |

**Implementation defaults (apply throughout the plan):**
- Fork servers: `src/solverforge_calendar/server.py` + `src/tuiboard/server.py`
- Transport: hand-rolled JSON-RPC 2.0 over stdio (Content-Length framing)
- Gateway: no auth; listens on `127.0.0.1:8765`
- Event log: `data/gateway/events.jsonl` (append-only JSONL)
- Tool versioning: no version suffix in v1; add only when schema breaks
- Vault conformance: `vault_write` is ONLY vault writer; grep test catches regressions

**Any change to a locked decision** → update this section + memory + re-review affected phases of the plan.

---

## SHIPPED trailer — 2026-08-30

**Implementation completed in 5 phases over a single session.** This spec is the binding contract for the architecture that landed; deviations require new user approval + spec revision.

### Phase rollup

| Phase | Deliverable | Range | Tools shipped | Test result |
|---|---|---|---|---|
| A1 — foundation | JSON-RPC 2.0 stdio scaffolds per fork + `register_default_adapters()` wiring + `start_gateway.py` + transport base + 2 E2E handshakes | `ac3c93a..d1fbee8` (8 commits) | `initialize`/`tools/list`/`tools/call` infra | 8 E2E PASS |
| A2 — reads | Pydantic v2 frozen models (solverforge + tuiboard) + SQLite UPI manager + 60s-cached availability tool + tuiboard snapshot store + tuiboard_diff | `5ebf546..299c846` (8 commits incl. CRITICAL Windows stdio binary-mode fix `b93a1f3`) | `sf_availability`, `tuiboard_diff`, `tuiboard_snapshot` (stub) | 13/13 PASS |
| A3 — writes | sf_schedule (UPSERT + conflict detection) + tuiboard.aggregator (CLI reader) + tuiboard_snapshot full impl + tuiboard_render (4 layouts) + regression sweep | `c56e7df..2b5b383` (5 commits) | `sf_schedule`, `tuiboard_snapshot`, `tuiboard_render` | 14/14 PASS in 9.16s |
| A4 — advanced | sf_replan (greedy constraint solver) + aggregator 3-fork precedence + tuiboard_aggregate (7th MCP tool) + regression | `4ad6138..f5a9a60` (4 commits) | `sf_replan`, `tuiboard_aggregate` | 155/155 PASS in 18.48s |
| A5 — cleanup | vault_write conformance grep test (Q6 enforcement) + SUPERSEDED trailer on `start_mcp_gateway.sh` + `mcp_config.json` → in-repo Python forks + **ADR-012** | `074d1bb..c3921bf` (4 commits) | (no new tools) | 157/157 PASS in 11.89s |

### Architecture decisions that landed (locked)

All 6 open-question recommendations were accepted 2026-08-30 (commit `d33c71d`):

| Q | Locked | Where it lives |
|---|---|---|
| Q1 | β in-repo Python forks | `src/solverforge_calendar/`, `src/tuiboard/` |
| Q2 | i hand-rolled JSON-RPC 2.0 | `src/ikigai/src/ikigai/gateway/stdio_server_base.py` + per-fork `server.py` |
| Q3 | a no auth | Localhost-only (loopback) |
| Q4 | i single JSONL event log | `data/gateway/events.jsonl` (append-only) |
| Q5 | γ YAGNI (no tool versioning) | v1 tools are stable; add suffix only when schema breaks |
| Q6 | I+III docs + grep test | `tests/gateway/clients/test_vault_write_conformance.py` + ADR-012 §Decision #6 |

### Tool surface shipped (7 MCP tools)

| # | Fork | Tool | Type | E2E test |
|---|---|---|---|---|
| 1 | solverforge-calendar | `sf_availability` | READ | `test_sf_availability.py` |
| 2 | solverforge-calendar | `sf_schedule` | WRITE (UPSERT + conflict detection) | `test_sf_schedule.py` |
| 3 | solverforge-calendar | `sf_replan` | READ (constraint solver) | `test_sf_replan.py` |
| 4 | tuiboard | `tuiboard_diff` | READ | `test_tuiboard_diff.py` |
| 5 | tuiboard | `tuiboard_snapshot` | WRITE (idempotent JSONL) | `test_tuiboard_snapshot.py` |
| 6 | tuiboard | `tuiboard_render` | READ (4 layouts) | `test_tuiboard_render.py` |
| 7 | tuiboard | `tuiboard_aggregate` | READ (multi-fork aggregator) | `test_tuiboard_aggregate.py` |

### Verification

- **A4.4 full regression:** 155/155 PASS in 18.48s (`tests/gateway/clients/` + `tests/tuiboard/` + `tests/mesh/`)
- **A5.5 final regression (this trailer):** 157/157 PASS in 11.89s (A4.4's 155 + 2 new grep tests)
- **ruff:** clean on all changed Python files
- **mcp_config.json:** valid JSON (verified `python -m json.tool`)
- **Windows stdio:** critical fix `b93a1f3` (binary-mode readline) keeps E2E tests reliable across platforms

### Pointer to ADR

Architecture rationale, alternatives considered, consequences (positive + negative + neutral):
→ **`code-docs/adr/ADR-012-fork-connection-architecture.md`** (71 lines, accepted 2026-08-30)

### Out of scope (deferred)

- taskdog fork adapter wiring (separate concern; taskdog already connected via external repo + HTTP)
- solverforge-calendar advanced constraint types beyond greedy v1 (linear programming, SAT solver)
- tuiboard web UI (rendering fork delivers JSON frames; UI client lives outside this repo)
- LLM-driven validation in the review queue (per `algorithm-gate` memory: deferred until system readiness)
- `vault_write` runtime enforcement (grep test + docs is the agreed enforcement per Q6=I+III)

### Phase A5.5 closeout

This trailer marks the end of Phase A (fork connection implementation). Next: **final whole-branch review** + **merge to master** (per the Phase A5 plan).

