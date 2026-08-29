# Phase B6 Combo A — Bidirectional Vault Sync (B6.6 + B6.7)

**Date:** 2026-08-29
**Status:** Drafted (awaiting user review)
**Scope:** Closes the vault↔taskdog loop. Adds reverse sync (B6.6) + vault writer (B6.7).
**Companion:** Closes gaps #1 + #4 from the expanded-next analysis.

---

## Goal

After Combo A: when a user marks a task done in taskdog (or otherwise changes
its state), the change **propagates back to vault** via the existing
review_queue + agent path. Vault remains the single source of truth (SOT);
taskdog is a view. The two directions form one closed loop.

**Today:** B6.1 ships vault→taskdog only. Marking a task done in taskdog
sits in taskdog SQLite forever. Vault never learns.

---

## Architecture (1 paragraph)

Add `reverse_sync()` (B6.6) that enumerates taskdog state, diffs against a
last-known snapshot stored in `data/sync-state-reverse.json`, and emits
`TaskChange` events to the existing `data/review_queue/` filesystem queue
(already shipped via `src/mesh/queue.py`). Add `vault_write` MCP tool (B6.7)
that, when the agent emits a `PropagationEvent` whose UEID target is the
vault, mutates the canonical markdown file. The MCP tool is the **only**
vault writer per attribution report §7. `VaultLock` (existing) provides
cross-platform concurrency safety. All file writes use `os.replace()`
(atomic, Windows-safe).

---

## Tech Stack

- Python 3.11+
- Pydantic v2 strict (frozen=True, extra="forbid") on all new schemas
- sqlite3 stdlib (TaskdogAdapter SQLite reads)
- `frontmatter` library (existing; YAML frontmatter parsing/dumping)
- `VaultLock` (existing; cross-platform file locking)
- `src/mesh/queue.py` (existing; filesystem append-only queue)

---

## Global Constraints (verbatim)

- **Vault write invariant** (attribution report §7): ALL vault writes go
  through `vault_write` MCP tool. Deep agent, native CLI, forks — same
  path. Enforcement duplo: MCP server rejects non-`vault_write` writes;
  `vault/.db` is gitignored.
- **Append-only invariant** (CLAUDE.md): `vault/` never deleted, only
  appended. Mutations via `vault_write` rewrite the file but git history
  stays clean (no destructive ops).
- **No edits to scoring/formula/qhe/regime/weight** (algorithm gate per
  attribution report).
- **Frozen models + extra="forbid"** on all new Pydantic schemas.
- **`os.replace()` for atomic file writes** (Windows-safe; B6.4 lesson).
- **No new deps** (existing stack only).
- **Pre-flight regression** mandatory before each commit (per
  `verify-agent-fabricated-failures`): main-session `pytest` + `ruff` +
  `mypy` before claiming success.

---

## Sub-Phase B6.6 — Reverse Sync (taskdog → review_queue)

### What it does

```python
def reverse_sync(
    state_path: Path,           # data/sync-state-reverse.json
    adapter: Any,               # TaskdogAdapter or mock
    review_queue_dir: Path,     # data/review_queue/ (defaults if None)
    source_fork: str = "taskdog",
) -> ReverseSyncResult:
    """Read taskdog, diff vs snapshot, emit TaskChange events."""
```

### Pipeline

1. **Load reverse snapshot** from `data/sync-state-reverse.json` (or
   initialize empty)
2. **Enumerate taskdog** via `TaskdogAdapter.list_all()` (new method)
3. **Compute diff** vs snapshot:
   - NEW (ueid in taskdog, not in snapshot) → emit `TaskChange(action=UPDATE, fields={...})` only if corresponding vault task exists; otherwise skip (orphan)
   - CHANGED (status/title differs) → emit `TaskChange(action=UPDATE)`
   - CHANGED_TO_DONE (status moved to "done") → emit `TaskChange(action=DONE)`
   - UNCHANGED → skip
4. **Emit events** to `review_queue/<event_id>.json` via
   `src/mesh/queue.enqueue()` (existing)
5. **Update snapshot** atomically (write .tmp + `os.replace()`)

### New schemas (all frozen + extra="forbid")

```python
class ReverseSyncTaskEntry(BaseModel):
    """Per-UEID entry stored in sync-state-reverse.json."""
    last_seen_status: str
    last_seen_title: str
    taskdog_id: int | None = None


class ReverseSyncState(BaseModel):
    """Full reverse sync state document."""
    version: int = 1
    last_sync_at: str | None = None
    tasks: dict[str, ReverseSyncTaskEntry] = Field(default_factory=dict)


class ReverseSyncResult(BaseModel):
    """Summary returned by reverse_sync() — NOT frozen, accumulates."""
    scanned: int = 0
    emitted: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    duration_s: float = 0.0
```

### CLI subcommand

`ikigai sync vault-from-taskdog [--dry-run] [--state-file PATH]`

- `--dry-run` — show diff, don't emit events
- Default `--state-file`: `data/sync-state-reverse.json`

### Files to modify

| File | Change |
|---|---|
| `src/mesh/adapters/taskdog.py` | + `list_all() -> list[dict[str, Any]]` method |
| `src/ikigai/src/ikigai/vault/sync.py` | + `reverse_sync()` + 3 new Pydantic models + `load_reverse_state()` / `save_reverse_state()` |
| `src/ikigai/src/ikigai/cli/app.py` | + `vault-from-taskdog` subcommand |

---

## Sub-Phase B6.7 — Vault Writer (review_queue → vault)

### What it does

Add `vault_write` MCP tool. **Only writer per attribution report §7.**

```python
async def vault_write(
    vault_path: str,        # relative to vault root, e.g. "plans/q3/task-x.md"
    frontmatter: dict,      # YAML key/values
    body: str,              # markdown body below frontmatter
) -> dict:
    """Write markdown file to vault. ONLY writer per attribution §7.
    
    Security: rejects paths that resolve outside vault/ (path traversal).
    Concurrency: VaultLock (existing).
    Atomicity: os.replace() (Windows-safe).
    Returns: {written: bool, vault_path: str, sha256: str}
    """
```

### Wire-up

The agent propagator (`src/mesh/agent_propagator.py`) needs to know when a
`PropagationEvent` is vault-bound. **Convention chosen** (see Open
Questions): UEIDs whose `source_fork` is `vault` (set by B6.6's reverse
sync) signal "vault target". The propagator reads this and calls
`vault_write` MCP tool.

```
B6.6 reverse_sync emits:
  TaskChange(action=DONE, ueid="...", fields={status: "done"},
             source_fork="taskdog")

mesh/agent_consumer validates → APPROVE
mesh/agent_propagator:
  - For taskdog adapter: writes to taskdog SQLite (existing)
  - For vault target:    calls vault_write MCP tool (NEW)
```

### Files to modify

| File | Change |
|---|---|
| `src/ikigai/src/mcp_server/server.py` | + `_vault_write()` helper, + `vault_write` in tools list, + dispatch entry |
| `src/mesh/agent_propagator.py` | + vault target detection (UEID `source_fork == "vault"`) → call `vault_write` |
| `.gitignore` | + `vault/.db` (defense-in-depth per attribution §7) |
| `src/ikigai/src/ikigai/vault/agentic_writer.py` | unchanged (separate path for IKIGAiRecord; vault_write is the lower-level tool) |

### Security

- `vault_write` MUST reject paths that resolve outside `vault/` root
  (path traversal via `..` blocked)
- `vault_write` MUST use `VaultLock` for cross-platform concurrency
- `vault_write` MUST atomic-write via `os.replace()`
- `vault_write` MUST return sha256 for idempotency tracking
- `vault_write` MUST reject empty body + empty frontmatter (refuse
  accidental blank writes)

---

## Tests Required

### Unit
- `src/ikigai/tests/test_reverse_sync.py` (8+ tests):
  - `list_all()` returns N tasks from SQLite fixture
  - reverse_sync emits NEW TaskChange for unseen UEID
  - reverse_sync emits UPDATE for changed status
  - reverse_sync emits DONE for moved-to-done status
  - reverse_sync skips orphan (taskdog-only, no vault match)
  - reverse_sync is idempotent (re-run with same state = 0 emitted)
  - reverse_sync atomic write (simulate concurrent read = no partial state)
  - reverse_sync per-task try/except isolation

- `src/ikigai/tests/test_vault_write.py` (6+ tests):
  - vault_write writes valid markdown to vault/
  - vault_write rejects path outside vault/ (security)
  - vault_write uses VaultLock (concurrent calls serialize)
  - vault_write atomic (os.replace, no partial file)
  - vault_write returns sha256 for idempotency
  - vault_write rejects empty body+frontmatter (no-op protection)

### Integration
- Extend `src/ikigai/tests/test_review_queue_worker_e2e.py`:
  - DONE action propagates to vault via vault_write
  - UPDATE action propagates status change to vault
  - vault path resolution correct (path under vault/)

### E2E
- `src/ikigai/tests/test_bidirectional_vault_sync_e2e.py`:
  - Full roundtrip: vault → taskdog → reverse → review_queue →
    agent → propagator → vault_write → vault
  - Verify vault markdown reflects final state (status: done)

### Smoke (bash + bat)
- `tests/smoke/test_reverse_sync_vault_from_taskdog.sh/.bat`
- `tests/smoke/test_vault_write.sh/.bat`

---

## Out of Scope

- ❌ Solverforge-calendar reverse sync (different adapter shape; v1.3+)
- ❌ Multi-fork consolidation (B6 v1 = taskdog only)
- ❌ Conflict resolution when vault and taskdog both modified same task
- ❌ Real-time event hooks (still polling)
- ❌ LLM-driven agent decisions (`mesh/agent_consumer.py` is rule-based)
- ❌ Reverse sync for `tuiboard` fork (not built yet; v1.4+)
- ❌ Migrating `IKIGAiAgenticWriter` to use `vault_write` (separate path;
  future consolidation)

---

## Open Questions (decision required)

### Q1 — Vault target routing in `PropagationEvent`

How does the propagator know an event is vault-bound?

- **A:** Add `target` field to `PropagationEvent` (breaking change to v1
  contract — all adapters need updating)
- **B:** Convention — UEIDs with `source_fork == "vault"` are vault-bound
  (least invasive, no schema change; relies on B6.6 setting source_fork
  correctly)
- **C:** Separate event type `VaultTaskChange` (cleaner but duplicates
  mesh/queue.py logic)

**Recommendation:** **B** (convention). Zero schema change. B6.6 already
controls `source_fork` in emitted events.

---

## Success Criteria

- ✅ `vault → taskdog → reverse → review_queue → vault` roundtrip works
  end-to-end with no manual intervention
- ✅ 20+ tests PASS (8 reverse_sync + 6 vault_write + 4 integration + 2
  E2E + smoke)
- ✅ 2 new CLI subcommands (`vault-from-taskdog` + smoke `vault_write`)
- ✅ `vault_write` MCP tool exists, dispatched, enforces vault-only writes
- ✅ `vault/.db` in `.gitignore` (defense-in-depth)
- ✅ Zero algorithm code touched
- ✅ git diff shows: only `src/mesh/`, `src/ikigai/src/ikigai/vault/`,
  `src/ikigai/src/mcp_server/`, `.gitignore`, `tests/`
- ✅ Pre-flight regression suite still PASS (B5.B + B6.x baseline)

---

## Deliverables (Combo A)

1. `docs/superpowers/specs/2026-08-29-phase-b6-6-bidirectional-vault-sync.md` (this file)
2. `docs/superpowers/plans/2026-08-29-phase-b6-6.md` (after writing-plans)
3. Memory: `phase-b6-combo-a-shipped-YYYY-MM-DD.md` (after ship)
4. CHANGELOG.md entry

---

## Related Memory

- [[algorithm-attribution-decisions-2026-08-29]] — vault_write invariant + revival criteria
- [[phase-b6-vault-sync-shipped-2026-08-29]] — B6.1 unidirectional baseline
- [[backend-phase-reordering-2026-08-28]] — Phase B sequencing
- [[interfaces-architecture-2026-08-27]] — forks vs native CLI/TUI
- [[verify-agent-fabricated-failures]] — main-session verification pattern

---

*Phase B6 Combo A Spec — Bidirectional Vault Sync — 2026-08-29*
