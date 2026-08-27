# SPEC C4 — CheckpointAdapter: JsonPlusSerializer Envelope (NO raw pickle)

> **Status**: 🟢 Draft — pending merge of `feat/data-model-unification`
> **Date**: 2026-08-27 · **Severity**: 🔴 Critical — closes RCE gap
> **Commit**: `eb8be96` · **Branch**: `feat/data-model-unification`

---

## §0. Purpose

This spec removes **`pickle.loads` from the LangGraph checkpoint read path** and replaces
it with a **portable JSON envelope** that round-trips through LangGraph's first-party
`JsonPlusSerializer`. Every checkpoint state is now a self-describing JSON blob that:

1. **Cannot execute arbitrary code on load.** `pickle.loads` is the largest
   remote-code-execution vector in the IKIGAI stack; an attacker who can write a row
   to `state_blob` gets `__import__("os").system(...)` on next resume.
   `JsonPlusSerializer.loads_typed()` deserializes only registered JSON-safe types —
   no module lookup, no `__reduce__` protocol.
2. **Survives Python upgrades and refactors.** Pickle binds by class **FQN**; rename
   `IKIGAiStateDict` and every checkpoint is unreadable. Schema-registry tags
   (`"ikigai_record_v1"`) persist across Python versions and minor refactors.
3. **Human-readable.** Corrupted checkpoints debuggable via `sqlite3 ... "select
   state_blob from checkpoints"` and eyeballing JSON, instead of decoding
   `b'\x80\x04\x95...'` by hand.

**Non-goals.** Does not change checkpoint schema (fields in `IKIGAiStateDict`) or the
`IKIGAiRecord` polymorphic shape (SPEC C2). Only the **transport** changes.
---
## §1. Problem

### 1.1 Raw pickle on the read path

`life-ops/ikigai/src/mcp_server/server.py` calls `pickle.loads(...)` directly on three sites:

| Site | Behavior on hostile payload |
|------|------------------------------|
| `server.py:188-201` (`_read_checkpoint`) | Silently drops to fallback (see §1.3). |
| `server.py:419-421` (`_read_plan_entity_cycle`) | Silently falls back; runs on every score recompute. |
| `server.py:430-436` (`_restore_thread_state`) | Fail-loud `UnpicklingError`; breaks thread resume. |

Plus `agents/ikigai_maintainer/graph.py:149-152` constructs `SqliteSaver` with no
custom `serde=`, so LangGraph uses its default pickle-based serializer for internal
writes/reads. Same class of bug, different file.

**Threat model:**

```text
INSERT INTO checkpoints VALUES('victim', b'\x80\x04\x95...os.system...');
Next resume → pickle.loads(state_blob) → __import__('os').system('malicious')
```

The DB lives at `~/.ikigai/ikigai_checkpoints.db` (world-readable on Linux WSL2 by
default). Any local process — compromised MCP tool, malicious extension, shared
CLI — can poison the blob; the resume path happily executes whatever `__reduce__`
returns.

### 1.2 Python-version / refactor coupling

Pickle encodes class identity by FQN (`ikigai.adapters.state_reducer.IKIGAiStateDict`).
Three things brick every existing checkpoint: moving `IKIGAiStateDict` to
`ikigai.entities.ikigai_state`, renaming `state_dict_reducer.py` → `state_reducer.py`,
or upgrading `langgraph.checkpoint.serde.jsonplus` (0.3+ uses a different protocol).

`feat/data-model-unification` already does the rename (ADR-009), so **every existing
checkpoint on a developer's machine is unreadable** after merge. Users silently
fall through to fallback or fail-loud depending on which call site hits.

### 1.3 Fallback hides the bug

`server.py:419-421` swallows **any** exception during checkpoint read — including
`UnpicklingError`, `EOFError`, `sqlite3.DatabaseError` — and falls back to
`_read_entity("plan_entities")`. Deserialization corruption becomes **invisible**:
we cannot tell from the tool response whether a prior cycle was restored or an empty
result returned. Users keep acting on stale scores for cycles they believed were
restored.

### 1.4 Where this fits in the unification

- **C1** — Vault canonical writer (authoring/validation, not runtime state).
- **C2** — `IKIGAiRecord` polymorphic root + `upsert_ikigai_record` (the *shape* of persisted entities).
- **C3** — `StateReducer` mapping `IKIGAiStateDict` → `IKIGAiRecord` (the bridge).
- **C4 (this)** — `CheckpointAdapter` (the **transport** that carries the record to/from SQLite without pickle).

C4 is the last link: C2 shapes an `IKIGAiRecord`, C3 produces one, C4 stores/restores one safely.

---

## §2. Design

### 2.1 JsonPlusSerializer envelope

LangGraph ships `langgraph.checkpoint.serde.jsonplus.JsonPlusSerializer` —
msgpack-with-JSON-fallback for primitives, a **type registry** for user-defined classes,
and bytes for everything else. It deserializes only what the registry recognizes — no
module lookup, no `__reduce__`.

Our `CheckpointAdapter` wraps that serde in a two-key **JSON envelope** so the row is
literal text:

```
envelope = json.dumps({
    "type":  <serde.dumps_typed()[0]>,        # e.g. "ikigai_record_v1"
    "data":  base64.b64encode(msgpack_bytes), # ASCII text
})
```

Stored as the literal UTF-8 value of `state_blob TEXT`. `grep` finds it; `cat` shows
something a human can decode.

### 2.2 Why the JSON envelope (and not raw msgpack bytes)

We don't store `(type_string, blob)` as a sqlite BLOB tuple because:

1. **Schema is `state_blob TEXT NOT NULL`** — BLOB tuple would require a migration on
   5+ read sites.
2. **Debuggability** — TEXT = `grep "ikigai_record_v1"`; BLOB = `xxd | head` and pain.
3. **Cross-tool inspection** — `sqlitebrowser`, `datasette`, ad-hoc shells all show
   JSON envelopes without configuration.

Trade-off: ~33% bloat from base64 + JSON quoting. Acceptable — rows are small (~2-10 KB,
< 50 cycles retained).

### 2.3 msgpack payload + type registry

Inside the envelope, the actual IKIGAiRecord is msgpack-encoded via
`JsonPlusSerializer.dumps_typed()` natively handles primitives, `bytes` (base64),
`datetime`/`UUID`/`Decimal` (msgpack ext-types), and `Path` (fspath). `IKIGAiRecord`
must be in the SchemaRegistry (§2.4).

### 2.4 SchemaRegistry — type whitelist

Only types registered in `ikigai.contracts.registry.SchemaRegistry` survive the
round-trip:

```python
# src/ikigai/contracts/registry.py
from ikigai.entities.ikigai_record import IKIGAiRecord

SCHEMA_REGISTRY: dict[type, str] = {IKIGAiRecord: "ikigai_record_v1"}
```

`dumps_typed()` returns `(tag, bytes)`; `loads_typed((tag, bytes))` looks the tag up
in its own registry (populated via `JsonPlusSerializer.register(IKIGAiRecord)` at
construction). Anything outside falls back to `repr()` — **safe but lossy** — so we
raise `TypeError` at write time if an unregistered type sneaks through.

### 2.5 Storage layer

In `~/.ikigai/ikigai_checkpoints.db` (no schema migration; same file as `graph.py:108`):

```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id  TEXT PRIMARY KEY,
    state_blob TEXT NOT NULL,                       -- JSON envelope
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
```

One row per thread (`INSERT OR REPLACE`). No append-only history mirror — checkpoints
**are** the recovery point; `StateReducer` (§C3) handles diffing in memory.

---

## §3. Interface signatures

### 3.1 `CheckpointAdapter` (new — `life-ops/ikigai/src/ikigai/adapters/checkpoint_adapter.py`)

```python
from pathlib import Path
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from ikigai.entities.ikigai_record import IKIGAiRecord

class CheckpointAdapter:
    def __init__(self, db_path: Path) -> None:
        """Side effects: mkdir(parent), CREATE TABLE, register IKIGAiRecord
        with self.serde so loads_typed round-trips cleanly."""
    def save(self, record: IKIGAiRecord, thread_id: str) -> None:
        """Persist record. Raises TypeError if record contains a
        non-registered Python type (defense-in-depth)."""
    def load(self, thread_id: str) -> IKIGAiRecord | None:
        """Return the IKIGAiRecord, or None if no row. Raises ValueError
        on malformed JSON / unknown tag / msgpack failure; sqlite3.DatabaseError
        on connection failure."""
```

### 3.2 Graph factory change

`life-ops/ikigai/src/agents/ikigai_maintainer/graph.py:149-152` becomes:

```python
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from ikigai.adapters.checkpoint_adapter import CheckpointAdapter
from ikigai.contracts.registry import SCHEMA_REGISTRY

serde = JsonPlusSerializer()
for py_type, tag in SCHEMA_REGISTRY.items():
    serde.register(py_type, tag)

# SqliteSaver now uses serde= instead of the default pickle.
checkpointer = SqliteSaver(conn, serde=serde)
```

The `CheckpointAdapter` (separate API) and the LangGraph-internal `serde=serde` on
`SqliteSaver` use the **same** `JsonPlusSerializer` instance — both paths must agree
or resume-from-thread breaks.

### 3.3 MCP server — replace `pickle.loads` (3 sites)

Each of `server.py:188-201, 419-421, 430-436` becomes:

```python
from ikigai.adapters.checkpoint_adapter import CheckpointAdapter

_cp = CheckpointAdapter(db_path=IKIGAI_CHECKPOINT_DB)

def _load_record_or_none(thread_id: str) -> IKIGAiRecord | None:
    try:
        return _cp.load(thread_id=thread_id)
    except (ValueError, KeyError):
        return None  # unknown tag, malformed envelope → no fallback data
```

**Breaking change vs §1.3:** no more swallowed `UnpicklingError`, **explicit None** on
malformed rows instead of silent fallback to `_read_entity("plan_entities")`. Legacy
fallback preserved as a separate, opt-in code path.

---

## §4. Acceptance criteria

1. **AC-C4-01 — no raw pickle header.** After `save()`, `state_blob` starts with `{`
   or `[` (JSON envelope) and **never** with `b"\x80"` (pickle protocol 2/3/4/5).
   Mirrors `test_checkpoint_adapter.py::test_uses_json_plus_serializer_not_pickle`.

2. **AC-C4-02 — round-trip.** `save(record, "t1")` then `load("t1")` returns an
   `IKIGAiRecord` whose `ueid`, `entity_type`, `custom`, `ikigai_vectors`, and
   `phase_at_creation` match the input under `model_dump()` equality.

3. **AC-C4-03 — overwrite is idempotent.** Two `save()`s with the same `thread_id`
   produce exactly one row with the **later** state (`INSERT OR REPLACE`).

4. **AC-C4-04 — SchemaRegistry enforcement.** `save()` with a payload containing a
   non-registered Python type (bare `set`, custom unannotated class) raises `TypeError`
   at serialize time, **before** the row is written.

5. **AC-C4-05 — SA-04 (integration gate).** Integration test
   `test_integration_data_model.py::test_SA_04_checkpoint_round_trip_via_jsonplus`
   parses real vault `dreams/vaga-remota-2026.md` → `IKIGAiRecord` → save → load →
   `IKIGAiRecord`. Both ueids match, and the resulting `state_blob` row fails the
   pickle-header sniff from AC-C4-01.

---

## §5. Migration path

### 5.1 One-time code change (~3 files, ~150 lines added, 0 removed)

1. Add `src/ikigai/adapters/__init__.py` and `checkpoint_adapter.py` (already at
   `eb8be96`).
2. Add `src/ikigai/contracts/registry.py` with `SCHEMA_REGISTRY` containing
   `IKIGAiRecord` only (extend as new entities land).
3. Edit `agents/ikigai_maintainer/graph.py:149-152` to pass `serde=serde` to `SqliteSaver`.
4. Edit `mcp_server/server.py:188-201, 419-421, 430-436` to use `CheckpointAdapter`.
   Remove `pickle.loads` and `pickle.dumps` imports.

### 5.2 Re-snapshot all existing threads

Every existing row in `~/.ikigai/ikigai_checkpoints.db` is a pickle blob and is
**unreadable** post-deploy (different envelope format). Run once at deploy time:

```bash
python -m ikigai.tools.resnapshot_threads \
    --old-db ~/.ikigai/ikigai_checkpoints.db \
    --backup-suffix .pre-c4-$(date +%Y%m%d)
```

The script (the **only** code path that still uses pickle, gated by
`__name__ == "__main__"`): open old DB with `pickle.loads`, translate each
`IKIGAiStateDict` through `StateReducer` (SPEC C3) into an `IKIGAiRecord`, call
`CheckpointAdapter.save(record, thread_id)`, atomically rename the old DB to
`ikigai_checkpoints.db.pre-c4-<date>` once all rows are persisted. If `StateReducer`
cannot decode a row (schema too old), dump to `migration_drops/<thread_id>.json`
(stderr notification).

### 5.3 Rollback

If C4 regresses post-merge: `git revert eb8be96`, `cp ikigai_checkpoints.db.pre-c4-*
ikigai_checkpoints.db`, re-run the pickle-loading path. State is preserved. The
pickle path lives in the resnapshot script for **30 days after merge**, then is
deleted (TODO + `ExpireDate` comment in `checkpoint_adapter.py`).

---

## §6. Verification

```bash
cd life-ops/ikigai
pytest tests/test_checkpoint_adapter.py -v        # unit (~10 cases)
pytest tests/test_integration_data_model.py -k SA_04   # integration gate

# Static: no pickle imports in production paths
! grep -rn "^from pickle\|^import pickle" src/ikigai src/agents src/mcp_server \
    | grep -v "tools/resnapshot_threads"

# SQLite-level: every state_blob is JSON, never pickle
sqlite3 ~/.ikigai/ikigai_checkpoints.db \
  "SELECT thread_id, substr(state_blob,1,5) FROM checkpoints;" | head -20
# Expected: rows "<thread> | {"  (curly-brace opener)
# Reject:    rows "<thread> | \x80"  (pickle protocol header)
```

If AC-C4-01's sniff fails on any row, the suite aborts loudly with the offending
`thread_id` — no silent corruption.

---

## §7. Cross-references

| Reference | File | Why |
|-----------|------|-----|
| `IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` | `life-ops/ikigai/docs/` | §C4 lists the `_read_entity` collision this spec does **not** address (SPEC C5). |
| `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` | `code-docs/diagnostic/` | §1 lists `S-C4` CheckpointAdapter as one of the unified data-model acceptance gates. |
| `tests/test_checkpoint_adapter.py` | `life-ops/ikigai/tests/` | Unit tests (5 cases). |
| `tests/test_integration_data_model.py::SA-04` | `life-ops/ikigai/tests/` | End-to-end vault → DB → IKIGAiRecord round-trip. |
| SPEC C2 (polymorphic root) | `code-docs/specs/2026-08-27-spec-C2-ikigai-record-polymorphic.md` | Defines `IKIGAiRecord` shape passed through this envelope. |
| SPEC C3 (StateReducer) | `code-docs/specs/2026-08-27-spec-C3-state-reducer.md` | Bridges `IKIGAiStateDict` → `IKIGAiRecord` during resnapshot. |
| ADR-009 | `code-docs/adr/` | Pydantic strict-mode — opaque to this layer. |

---

## §8. Open questions

1. **Envelope self-versioning.** `{"type": tag, "data": base64}` may become unreadable
   on LangGraph 1.0 wire-format bump. Default: pin `langgraph<1.0`, re-spec on
   upgrade — punt on an envelope `v` field until 1.0 ships.
2. **Encryption at rest.** SQLite is plaintext, same YAGNI argument as vault
   markdown. Reopen if `IKIGAiRecord.custom` ever holds PII.
3. **Concurrent multi-process writers.** `check_same_thread=False` (graph.py:151);
   last-write-wins, tighter race window than pickle. Separate spec if real.
4. **`state_blob` TEXT vs BLOB.** Base64 + JSON loses ~33% density vs raw BLOB. With
   < 10 KB × ~50 cycles, cost is negligible. Revisit at 100× throughput.
5. **`IKIGAiRecord` versioning inside the envelope.** The `"ikigai_record_v1"` tag
   implies v1. First shape change → bump `_v2`, write a migrator, publish an ADR.
   Placeholder ADR needed before first bump.

---

*SPEC C4 — v1.0 — 2026-08-27 — draft, gated by `feat/data-model-unification` PR*
