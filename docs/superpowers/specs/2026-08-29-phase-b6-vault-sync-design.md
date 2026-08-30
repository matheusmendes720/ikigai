# Phase B6 — Vault→taskdog Sync v1 — Design Spec

**Date:** 2026-08-29
**Phase:** B6 (LAST) of `2026-08-28-backend-audit-data-mesh` layering plan
**Layer:** 5 (Vault Sync Protocol)
**Status:** Design — pending spec self-review + user approval before writing-plans
**Inputs:**
- [[backend-phase-reordering-2026-08-28]] — B6 placed LAST
- [[master-branch-carro-chefe-2026-08-28]] — deep-agent ↔ forks↔ vault
- [[interfaces-architecture-2026-08-27]] — forks as user surfaces via MCP adapters
- [[vault-planning-false-gap-2026-08-28]] — vault is SOT for infra, append-only on `vault/`
- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — no math edits
- [[verify-agent-fabricated-failures]] — main-session verification
- `src/ikigai/src/ikigai/gateway/clients/taskdog.py` — TaskdogAdapter factory
- `src/ikigai/src/ikigai/vault/frontmatter_to_dict.py` — frontmatter parser
- `src/ikigai/src/ikigai/cli/app.py:33` — sync_app Typer sub-app
- `data/boulder.json` precedent — runtime state file in `data/` (gitignored)

---

## Context

Per [[master-branch-carro-chefe-2026-08-28]], master branch = deep-agent
bidirectionally syncing forks-prontas (tuiboard / taskdog / solverforge-calendar)
widgets ↔ vault local `.db.markdown`. The "forks" in this codebase are
**MCP adapters** (not separate repositories):
`src/ikigai/src/ikigai/gateway/clients/{taskdog,tuiboard,solverforge_calendar}.py`
— each constructs a `StdioAdapter` that talks to the fork's MCP server over
stdio. This is the integration shape B6 must respect.

Vault is git-tracked (147/163 files in `vault/`); `data/` is gitignored
(vibe_ops.db, vibe_mesh.db, boulder.json, chroma_db, review_queue/).
Multiple fragmented sync mechanisms exist today (`vault_taskdog_sync.py`,
`vibe-ops/src/middleware/sync_engine.py`, MCP `ikigai_sync_vault` tool,
direct writes from `deepagents_harness.py`). B6 does NOT consolidate them
— it adds one **deterministic, idempotent** sync path that operators can
trust for vault→taskdog propagation.

## Why now (per [[backend-phase-reordering-2026-08-28]] rev.3)

B6 sits LAST because all earlier layers stabilize the sync ends:
- B1 A2UI adapter ready (interfaces/cli's adapter layer is solid)
- B2 server-management CLI ready (operators can start/stop fork backends)
- B3 MCP gateway consolidado (auditable IPC contracts for forks)
- B4 review queue worker (minimal runtime for event consumption)
- B5 agent consumer + propagator (PAE validation wired end-to-end)

Doing sync before these = "empty handler" anti-pattern. Doing sync now =
real wire-up of the canonical deep-agent ↔ fork direction.

---

## Decisions (D1..D5, locked from brainstorming session 2026-08-29)

### D1. Unidirectional vault→forks (MVP scope)

v1 syncs **only one direction**: vault markdown → fork (taskdog). Reverse
direction (fork → vault) is deferred to v1.2. This avoids the conflict-
resolution design problem (3-way merge, last-write-wins vs operational
transform vs CRDT) which is a multi-week design surface of its own.

Rationale: vault is SOT per [[vault-planning-false-gap-2026-08-28]]. If
the operator disagrees with what's in a fork, the source of truth to
reconcile to is the vault — never the other way around in v1.

**Rejected alternatives:**
- **D1.B** — Bidirectional full sync in v1. Requires UEID as canonical
  join key + conflict policy + write-back semantics upfront. Scope
  explosion; blocks the simpler "make vault changes visible in taskdog"
  value-prop behind a much bigger design.
- **D1.C** — Agent-driven sync only (no CLI). Violates user's "on-demand
  CLI" choice (D2) and removes the operator's ability to verify sync
  state at will.

### D2. On-demand CLI trigger

Operator runs `ikigai sync vault-to-taskdog` (extending the existing
`sync_app` Typer sub-app at `src/ikigai/src/ikigai/cli/app.py:33`). No
daemon, no file-system watcher, no cron.

Rationale: smallest blast radius. The CLI invocation can later be wired
into the deep-agent's `ikigai_sync_vault` tool, a file-watcher, or a
schedule without changing the sync engine itself — the protocol is
trigger-agnostic.

**Rejected alternatives:**
- **D2.B** — Hook into `ikigai_sync_vault` MCP tool. Couples vault
  writes to fork writes; fork MCP failures would block vault commits.
- **D2.C** — `watchdog`-based file watcher daemon. Adds process lifecycle
  management + cross-platform edge cases + race conditions with agent
  writes. Defer to v1.3+ if real demand emerges.
- **D2.D** — Schedule-driven (cron). Introduces sync lag and infra
  orchestration overhead.

### D3. taskdog is the MVP fork

Sync targets `taskdog` only in v1. tuiboard is read-only rendering
(`tuiboard_render`, `tuiboard_snapshot`, `tuiboard_diff` — no write
semantics), so "vault→tuiboard" doesn't fit cleanly. solverforge-calendar
is a different domain (time-based events) with bigger design surface.
taskdog's task semantics (`taskdog_add`, `taskdog_done`, `taskdog_list`)
align naturally with vault frontmatter tasks.

Rationale: lowest design risk + highest semantic overlap with vault
content shape. Existing partial impl at
`src/ikigai/tools/vault_taskdog_sync.py:312` proves the path; B6
refactors/replaces it into the canonical sync engine.

**Rejected alternatives:**
- **D3.B** — All three forks at once. Couples the design to 3 different
  content shapes. Defeats the MVP philosophy.
- **D3.C** — tuiboard. Read-only by design; unidirectional vault→tuiboard
  means "invalidate cache + re-render", not CRUD.
- **D3.D** — solverforge-calendar. Time-domain differences make task
  frontmatter reuse awkward; bigger design work.

### D4. Frontmatter-tagged tasks as sync unit

Sync only markdown files where frontmatter declares the file as a task:
```yaml
---
ueid: ikigai:task:slug:<uuid>:<hash>
title: "..."
status: planned  # or in_progress | done
tags: [task]     # OR
type: task       # alternative discriminator
priority: high   # optional
due: 2026-09-15  # optional
---
```

Other markdown in `vault/` (drafts, evidence, MOCs, ADRs, retros,
strategics) is **never** synced. Content-driven — vault author decides
what's a task via frontmatter.

Rationale: scales naturally as vault grows; no path-pattern brittleness;
matches how operators already tag content.

**Rejected alternatives:**
- **D4.B** — Path-prefix (`vault/ikigai/**`). Pulls in non-task content;
  would need post-filtering anyway.
- **D4.C** — Hard-coded path list. Brittle — breaks if vault structure
  evolves. Couples sync code to current vault layout.
- **D4.D** — Configurable YAML. Adds config surface to design, test,
  document. Defer if real demand.

### D5. Approach B — `data/sync-state.json` incremental diff

Maintain `data/sync-state.json` (gitignored, alongside `boulder.json`):
```json
{
  "version": 1,
  "last_sync_at": "2026-08-29T18:42:11Z",
  "tasks": {
    "ikigai:task:slug:<uuid>:<hash>": {
      "last_synced_at": "2026-08-29T18:42:11Z",
      "last_status": "done",
      "taskdog_id": "12",
      "vault_path": "vault/ikigai/closing-2026/.../task-foo.md"
    }
  }
}
```

On sync: read vault → diff against state → push only NEW/CHANGED.
- `NEW` (UEID not in state) → call `taskdog_add(payload)`, capture returned taskdog id, store
- `CHANGED` (status differs from `last_status`) → if new status is `done` call `taskdog_done(ueid)`; else call `taskdog_add(payload)` for update
- `UNCHANGED` → skip

State written AFTER each successful push (atomic per-task write), so a
crash mid-batch leaves a recoverable state where the in-flight task will
be re-tried next sync.

Rationale: efficient (O(changes) not O(all)), idempotent, no vault
mutation. Follows the project convention that runtime state lives in
`data/` (precedent: `data/boulder.json`, `data/vibe_ops.db`).

**Rejected alternatives:**
- **D5.A** — Read-once + idempotent push (no state). Re-pushes everything
  every invocation; no status-transition detection.
- **D5.C** — Vault-frontmatter-driven (`synced_to.taskdog: <ts>`).
  Mutates vault content (breaks "vault = pure planning" convention);
  needs first-run migration for existing tasks.

---

## Architecture

```
   vault/**/*.md (frontmatter-tagged tasks only)
       │
       │ read + parse frontmatter
       ▼
   ┌──────────────────────────────────────────────────────────┐
   │ task_extractor.parse_vault_tasks(vault_root)             │
   │   → list of {ueid, status, title, priority, due, ...}    │
   └────────┬─────────────────────────────────────────────────┘
            │
            │ diff against
            ▼
   ┌──────────────────────────────────────────────────────────┐
   │ data/sync-state.json                                     │
   │   → per-UEID {last_status, taskdog_id, last_synced_at}   │
   └────────┬─────────────────────────────────────────────────┘
            │
            │ classify NEW | CHANGED | UNCHANGED
            ▼
   ┌──────────────────────────────────────────────────────────┐
   │ sync_engine.push(actions)                                │
   │   per action: try/except → log + continue                │
   │   on success: write state update (atomic per task)       │
   └────────┬─────────────────────────────────────────────────┘
            │
            │ MCP stdio (via StdioAdapter)
            ▼
   ┌──────────────────────────────────────────────────────────┐
   │ taskdog MCP server                                       │
   │   - taskdog_add(ueid, title, priority, due, ...)          │
   │   - taskdog_done(ueid)                                    │
   └──────────────────────────────────────────────────────────┘
```

---

## Components & Files

### NEW — `src/ikigai/src/ikigai/vault/sync.py`

Sync engine + task extractor + state manager. Three classes/functions:

```python
# Public API
def parse_vault_tasks(vault_root: Path) -> list[TaskRecord]: ...
def load_state(state_path: Path) -> SyncState: ...   # init if missing
def save_state(state_path: Path, state: SyncState) -> None: ...
def diff(tasks: list[TaskRecord], state: SyncState) -> list[SyncAction]: ...
def push(actions: list[SyncAction], adapter: StdioAdapter) -> SyncResult: ...
def run_sync(vault_root: Path, state_path: Path, adapter: StdioAdapter) -> SyncResult: ...
```

`TaskRecord` and `SyncState` are Pydantic v2 strict (`frozen=True`,
`extra="forbid"`) — matches project conventions.

### NEW — `data/sync-state.json` (gitignored)

Runtime state file. Already in `.gitignore` patterns (`data/*.json`).

### MODIFY — `src/ikigai/src/ikigai/cli/app.py`

Add a new subcommand under existing `sync_app` Typer group (line 33):

```python
@sync_app.command("vault-to-taskdog")
def sync_vault_to_taskdog(
    ctx: typer.Context,
    vault_root: Path = typer.Option(Path("vault"), "--vault"),
    state_path: Path = typer.Option(Path("data/sync-state.json"), "--state"),
) -> None:
    """Sync vault frontmatter tasks → taskdog via MCP. Incremental, idempotent."""
    from ikigai.gateway.clients.taskdog import TaskdogAdapter
    from ikigai.vault.sync import run_sync

    adapter = TaskdogAdapter()
    result = run_sync(vault_root=vault_root, state_path=state_path, adapter=adapter)
    _output(result.model_dump(mode="json"), ctx.obj.get("json_out", False))
```

### NO CHANGE — `src/ikigai/src/ikigai/gateway/clients/taskdog.py`

Reuse existing `TaskdogAdapter` factory. Adapter exposes
`adapter.call_tool(name, args)` via the StdioAdapter protocol — sync
engine calls `taskdog_add` and `taskdog_done` by name.

### NO CHANGE — `src/ikigai/src/ikigai/vault/frontmatter_to_dict.py`

Reuse existing parser. Sync engine calls `frontmatter_to_dict(path)` and
filters to records where `tags` includes `"task"` OR `type == "task"`.

---

## Data flow (per CLI invocation)

1. **Load state**: read `data/sync-state.json`; if missing, initialize empty
   `SyncState(version=1, tasks={})` and ensure `data/` dir exists
2. **Walk vault**: glob `vault/**/*.md`, parse frontmatter, keep tasks
   (D4 discriminator)
3. **Diff** per task:
   - UEID not in `state.tasks` → action `NEW` (call `taskdog_add`)
   - UEID in state but `current_status != state.last_status` → action
     `CHANGED` (call `taskdog_done` if status is `done`, else `taskdog_add`)
   - UEID in state and `current_status == state.last_status` → skip
4. **Push** with per-action try/except:
   - On success: update state with `{last_status: current, taskdog_id:
     <returned_id>, last_synced_at: now}` written atomically (write to
     `state_path.with_suffix(".tmp")` then rename)
   - On exception: log error with `{ueid, exception}`; count in summary;
     continue with next action
5. **Report**: CLI outputs JSON summary
   ```json
   {
     "scanned": 47,
     "added": 3,
     "updated": 1,
     "completed": 2,
     "skipped": 41,
     "errors": [
       {"ueid": "ikigai:task:...:...:...", "error": "MCP timeout"}
     ],
     "duration_s": 2.34
   }
   ```

---

## Error handling

- **Per-task failure isolation**: one task's MCP failure doesn't abort the
  batch (try/except in `push()` loop). Mirrors the per-adapter isolation
  pattern from B4/B5 review queue worker.
- **State integrity**: state written AFTER each successful push via
  atomic rename. Crash mid-batch → task re-tried next sync (state was
  not updated for the failed push).
- **MCP unreachable**: `StdioAdapter.call_tool()` raises
  `MCPTimeoutError` after `call_timeout_s=10.0`. Caught at the
  per-action level; counted in `errors[]`.
- **Frontmatter parse error**: caught at the `parse_vault_tasks` level;
  offending file logged and skipped; surface count in summary under
  `parse_errors`.
- **Missing `data/` dir**: `load_state` creates `state_path.parent` if
  missing.
- **Concurrent sync invocations**: not handled in v1 (out of scope).
  Operator runs sync serially.

---

## Testing

### Pre-flight baseline (must be green before B6 ships)

```bash
TMPDIR=/c/tmp TMP=/c/tmp PYTHONPATH=. \
  pytest tests/ikigai/ \
         interfaces/cli/tests/test_review_queue_worker.py \
         interfaces/cli/tests/test_review_queue_worker_e2e.py \
         src/ikigai/tests/test_vault_lock.py \
         src/ikigai/tests/test_drift_detector.py \
         src/ikigai/tests/test_frontmatter_to_dict.py \
         src/ikigai/tests/test_agentic_writer.py \
         src/ikigai/tests/test_cli.py -v
```

### New tests (Phase B6)

1. **Unit — `src/ikigai/tests/test_vault_sync.py`**:
   - `test_parse_vault_tasks_filters_non_tasks` — drafts/evidence/MOCs ignored
   - `test_parse_vault_tasks_extracts_ueid_status_priority_due` — full record extraction
   - `test_diff_new_unchanged_changed` — three-way classification
   - `test_push_per_task_isolation` — one failure doesn't abort batch
   - `test_save_state_atomic_rename` — verifies `.tmp` → final pattern
   - `test_load_state_initializes_when_missing` — first-run path
2. **Integration — `src/ikigai/tests/test_vault_sync_e2e.py`**:
   - Mock MCP server (in-process stdio) + tmp vault + tmp state →
     run `run_sync()` → verify taskdog received expected `taskdog_add`
     + `taskdog_done` calls in expected order; state file updated
3. **Smoke — `tests/smoke/test_sync_vault_to_taskdog.{sh,bat}`**:
   - End-to-end CLI invocation against an in-process mock taskdog
     server. Verifies exit code 0 on success; non-zero with error
     summary on failure.

### Verification

```bash
TMPDIR=/c/tmp TMP=/c/tmp PYTHONPATH=. \
  pytest src/ikigai/tests/test_vault_sync.py \
         src/ikigai/tests/test_vault_sync_e2e.py \
         src/ikigai/tests/test_cli.py -v
```

Expected: new tests + existing CLI tests + frontmatter tests all PASS.

---

## Out of scope (v1)

Per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] + YAGNI:

- **Reverse direction** (taskdog → vault) — deferred to v1.2
- **Other forks** (tuiboard, solverforge-calendar) — deferred; add via
  same sync engine pattern in v1.3
- **Update of fields beyond `done` status** (priority/due/etc.) — v1
  treats `taskdog_add` as full-payload overwrite; partial-field updates
  deferred until a real consumer requests them
- **Vault file deletion handling** — if a task is removed from vault,
  it stays in taskdog. v1.2 can add "list taskdog, diff vs vault,
  archive orphans" pass.
- **Conflict resolution / 3-way merge** — only matters if v1.2 adds
  reverse direction
- **Concurrent sync invocations** — file-locking not in v1; serial runs only
- **Algorithm-driven task fields** (vector scores, regime, Q_HE) —
  frozen per algorithm gate

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| TaskdogAdapter MCP server not actually installed/runnable in dev env | Medium | Use in-process mock for unit + integration tests; document `TASKDOG_MODULE` env override for real server in smoke test |
| Frontmatter diversity — existing vault files may not have `tags: [task]` yet | Medium | Spec includes 1 example template in spec; v1 ships with 0 vault files needing migration; document migration guide as separate Phase B6.5 task |
| State file grows unboundedly with completed tasks | Low | v1 doesn't auto-prune; document `data/sync-state.json` lifecycle; v1.2 can add "tasks not in vault → mark `archived` in state" |
| `taskdog_add` semantics — does it UPSERT on UEID or always create new? | Medium | Verify in smoke test before commit; if no UPSERT, prefix UEID into title for idempotency (degraded but functional); real fix is taskdog-side, out of B6 scope |
| Race: vault file changes between read and state write | Low | v1 is single-operator, serial; document "don't edit vault mid-sync" |
| `python-frontmatter` library drops `None`-valued keys (RT-03) | Low | Existing `frontmatter_to_dict` already preserves None (line 32-36); reuse without modification |

---

## Estimated Scope

| Sub-task | LoC changed | Effort |
|----------|-------------|--------|
| B6.1: `src/ikigai/src/ikigai/vault/sync.py` (NEW) | ~280 lines (parser + state + diff + push + run_sync) | 4 hours |
| B6.2: CLI subcommand in `app.py` | ~25 lines added | 30 min |
| B6.3: `tests/test_vault_sync.py` (NEW) | ~150 lines (6 unit tests) | 2 hours |
| B6.4: `tests/test_vault_sync_e2e.py` (NEW) | ~120 lines (mock MCP + tmp vault/state) | 2 hours |
| B6.5: `tests/smoke/test_sync_vault_to_taskdog.{sh,bat}` (NEW) | ~60 lines | 1 hour |
| B6.6: Verification + memory + CHANGELOG | trivial | 30 min |
| **Total** | **~635 lines** | **~10 hours** |

---

## Related

- [[backend-phase-reordering-2026-08-28]] — B6 placed LAST, after B0-B5
- [[master-branch-carro-chefe-2026-08-28]] — master = deep-agent↔forks↔vault
- [[interfaces-architecture-2026-08-27]] — forks are MCP adapters, not separate repos
- [[vault-planning-false-gap-2026-08-28]] — vault is SOT, append-only on `vault/`
- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — no math edits
- [[verify-agent-fabricated-failures]] — main-session test verification
- [[phase-b5-b-agent-wiring-shipped-2026-08-29]] — closest precedent for test patterns + per-adapter isolation

---

**SUPERSEDED 2026-08-30 (B7.5):** `src/ikigai/src/ikigai/vault/agentic_writer.py` and its test DELETED. Zero production callers; uses non-atomic `frontmatter.dump()` (regression vs `vault_write`). `IKIGAiRecord` survives via 3 other consumers (`sqlite_bridge`, `checkpoint_adapter`, `dict_to_frontmatter`). See Phase B7 spec §5.5.
- `docs/superpowers/specs/2026-08-29-phase-b5-b-agent-wiring-design.md` — format precedent for this spec
- `src/ikigai/tools/vault_taskdog_sync.py:312` — existing partial impl that B6 supersedes
- `vibe-ops/src/middleware/sync_engine.py` — unrelated (vault↔SQLite mirror)