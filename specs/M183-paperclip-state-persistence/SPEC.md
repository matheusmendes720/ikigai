---
name: M183-paperclip-state-persistence
description: Paperclip run-state persistence — JSON snapshots to data/paperclip/runs/ for post-mortem debug + spawner history.
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

# M183 — Paperclip run-state persistence

**Status:** 🟢 DONE
**Date:** 2026-10-12
**Author:** matheus-mendes (with Claude Code assist)

---

## TL;DR

Add **structured state persistence** to Paperclip: every graph run
(success OR failure) dumps its final state to
`data/paperclip/runs/<ISO-TS>_<task_id>.json` so:

1. **Crashes can be debugged post-mortem** — the JSON snapshot is the
   authoritative last-known-good state, even if the SqliteSaver
   checkpointer is binary-only and the dashboard's in-memory ring buffer
   is lost on restart.
2. **The M174 auto-spawner can read past run history** — `list_recent_runs`
   gives the spawner a durable view of what shipped and what failed,
   without depending on a long-running dashboard process.

---

## What changed

```
src/ikigai/src/agents/paperclip/
├── persistence.py                       # NEW (~240 LOC) — RunRecord +
│                                       # persist_run + list_recent_runs +
│                                       # load_run + GC
├── cli.py                               # MODIFIED — `paperclip run` calls
│                                       # persist_run after every invocation;
│                                       # new `paperclip runs` subcommand
└── tests/
    └── test_persistence.py              # NEW — 5 focused unit tests

src/ikigai/tests/
└── test_paperclip_drift.py              # +1 invariant (test_paperclip_persistence_module_exists)

specs/M183-paperclip-state-persistence/SPEC.md   # NEW — this file
.claude/loop/roadmap.md                  # +1 entry (M183)
```

**Drift total:** 74 → 75.

---

## File format

```
<runs_dir>/<YYYY-MM-DDTHH-MM-SSZ>_<task_id>.json
```

The ISO 8601 timestamp prefix sorts lexically — older files are deleted
first by GC. The `<task_id>` is sanitised (path separators → `_`) so the
filename is always safe on Windows + POSIX.

Each file:

```json
{
  "run_id": "uuid-hex-12",
  "task_id": "hello-world",
  "started_at": "2026-10-12T01:42:17Z",
  "finished_at": "2026-10-12T01:42:42Z",
  "duration_s": 25.0,
  "adapter": "pi",
  "status": "ok" | "error" | "spec_ambiguous" | "blocked_by_gate" | "running",
  "gates_consulted": [
    {"gate": "CostGate", "allowed": true, "reason": "..."},
    {"gate": "WallClockGate", "allowed": true, "reason": "..."},
    {"gate": "RiskGate", "allowed": true, "reason": "..."}
  ],
  "steps": [
    {"node": "read_spec", "ts": "...", "error_type": null},
    ...
  ],
  "final_state": {
    "commit_sha": "...",
    "worktree_path": "...",
    "branch_name": "...",
    "tests_ok": true,
    "implement_iteration": 1
  },
  "error": null
}
```

---

## API

```python
from src.ikigai.src.agents.paperclip.persistence import (
    RunRecord,
    persist_run,
    list_recent_runs,
    load_run,
    build_record_from_state,
)

# 1. Build a record
record = RunRecord(
    task_id="hello-world",
    started_at="2026-10-12T01:42:17Z",
    adapter="pi",
    status="ok",
    ...
)

# 2. Persist (atomic write + GC)
path = persist_run(record)  # returns Path

# 3. List recent (newest first)
recent = list_recent_runs(limit=20)

# 4. Load one back
data = load_run(path)  # dict
```

---

## CLI surface

```bash
# Run (existing) — now persists a snapshot at the end:
paperclip run --spec "Add hello()" --dry-run --task-id m183-smoke

# NEW subcommand: list recent runs
paperclip runs --limit 5
# TASK            STARTED                STATUS  ADAPTER  STEPS  PATH
# m183-smoke      2026-10-12 01:42:17    ok      dry-run     3   data/paperclip/runs/...

# JSON output for piping:
paperclip runs --json
```

---

## Design decisions

### Atomic write (`.tmp` + `os.replace`)

Writes go through `tmp_path = path.with_suffix(".tmp")` first, then
`os.replace(tmp_path, path)` for atomic rename. A crashed process never
leaves a half-written JSON file in the runs directory.

### Best-effort GC

GC is non-fatal: if `unlink()` raises (Windows transient lock), the file
is logged and skipped. The next `persist_run()` call will retry.

### Persist on BOTH success AND failure

The CLI wraps `persist_run` in a try/except that's separate from the
graph's error handling — a broken persistence layer never masks the real
graph outcome. The user always sees the test failure, not the JSON-write
error.

### Failures with empty final_state still get persisted

Even when the graph raises before any node updates state, the CLI calls
`persist_run` with `final_state={}` and `error="<ExceptionType>: <msg>"`.
Post-mortem debugging is most valuable when things go wrong.

### `MAX_RUNS = 100` (configurable)

GC removes oldest files when the directory exceeds this. 100 snapshots
@ ~5 KB each = ~500 KB — negligible disk footprint, ~6 months of typical
usage at 1 run/day.

---

## Tests

### `tests/test_persistence.py` (NEW — 5 tests)

1. `test_persist_run_creates_file` — `persist_run(record)` writes the
   record to `runs_dir` and the file exists with valid JSON.
2. `test_persist_run_filename_format` — filename matches
   `<ISO-TS>_<task_id>.json` so lexical sort matches chronological
   order.
3. `test_persist_run_gc_when_over_limit` — writing `MAX_RUNS+5` records
   removes the oldest 5 (verified via task_id inspection).
4. `test_list_recent_runs_newest_first` — returns paths in
   reverse-chronological order.
5. `test_load_run_roundtrip` — every field of the original `RunRecord`
   survives the persist → load cycle.

### `tests/test_paperclip_drift.py` (+1 invariant)

* `test_paperclip_persistence_module_exists` — `persist_run`,
  `list_recent_runs`, `RunRecord`, `MAX_RUNS`, `DEFAULT_RUNS_DIR` all
  importable. Locks the M183 surface against silent removal.

---

## What stays out of scope (deferred)

* **Streaming per-node snapshots** — currently we persist only the
  *final* state. Per-node streaming would be useful for long-running
  agent invocations but adds ~50 LOC + a write-per-node. Not needed for
  the MVP.
* **Compression** — JSON is already small (~5 KB / run). gzip would save
  ~70% but adds a dependency. Defer.
* **Cross-process locking** — `persist_run` is process-safe (atomic
  write), but two concurrent `paperclip run` invocations could GC each
  other's files. Not a concern in practice (one run at a time per
  machine).
* **`paperclip runs --follow` (live tail)** — dashboard already exposes
  the in-memory ring buffer; cross-referencing with on-disk JSON is
  dashboard v2 work.