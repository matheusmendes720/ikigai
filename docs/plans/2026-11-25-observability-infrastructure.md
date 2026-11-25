# Observability Infrastructure — Design Plan

**Date:** 2026-11-25
**Status:** draft — unreviewed
**Anchors:** ADR-037 D4 ("the store wins") · ADR-037 D5 ("one writer per store") · Issue #22 provenance gap

## 1. Schema change

### What already exists

`ikig.artifacts` (`0001_init.sql:15-31`) already has `client_id text not null`.
The repository writes it on every `INSERT` (`repository.py:210, 224`) and
`_update` sets it too. The column is populated — it just isn't readable through
the Pydantic layer.

`ArtifactSummary` (`dom.py:108-131`) and `Artifact` (`dom.py:134-142`) do NOT
expose `client_id`. That is the only gap between the SQL truth and the Python
object the VaultSync receives from `repo.get(uid)`.

### What to add

**`client_id` to `ArtifactSummary`** — add `client_id: str | None = None` to
`ArtifactSummary` (`dom.py`, after `vault_path`). Nullable because artifacts
written before the model exposed it will return `None` from the SELECT. The
column itself is `not null` in SQL, so rows written after the model change will
always carry the value.

**`correlation_id` to `ikig.artifacts`** — a new nullable `text` column
(`0001_init.sql` predates this concept). Populated by the repository from
`WriteRequest` on every write.

**`correlation_id` to `ikig.artifact_revisions`** — same column, same
semantics: each revision snapshot carries the trace id of the write that
produced it.

### Migration `0010_correlation_id`

```sql
-- 0010_correlation_id.sql
alter table ikig.artifacts
    add column if not exists correlation_id text;

alter table ikig.artifact_revisions
    add column if not exists correlation_id text;

comment on column ikig.artifacts.correlation_id is
    'trace identifier that flows from WriteRequest through the write pipeline';
```

```sql
-- 0010_correlation_id.down.sql
alter table ikig.artifacts drop column if exists correlation_id;
alter table ikig.artifact_revisions drop column if exists correlation_id;
```

The `if not exists` / `if exists` guards make re-application and rollback safe:
a migration that runs twice is a no-op, not an error.

### Pydantic change

`dom.py` — `ArtifactSummary` gains one field:

```python
client_id: str | None = None   # the client who wrote the current revision
```

`dom.py` — `WriteRequest` already has `client_id` (`dom.py:167-183`). Add:

```python
correlation_id: str | None = None
```

`store.py` — `SCHEMA_VERSION` stays at `1` (backwards-compatible addition,
no breaking shape change).

---

## 2. Provenance guard — the sync's decision tree

The guard lives in `sync.py._ingest_file`, after the existing read (line 488)
and before the upsert (line 591). It is ONE condition:

```python
# After line 488: existing = await self._repo.get(uid)
# After line 552: the unchanged check (existing.body_hash + _same_mapping)

if (
    existing is not None
    and existing.client_id is not None
    and existing.client_id != self._client_id       # "vault-sync"
    and existing.body_hash != body_hash              # store diverged from vault
):
    report.skipped.append(
        f"{relative}: store was advanced by '{existing.client_id}' "
        f"(revision {existing.revision}); vault not overwritten"
    )
    return
```

**Why three conditions:**

1. `existing.client_id is not None` — backfill guard for rows written before the model exposed the column
2. `existing.client_id != self._client_id` — someone else wrote the current revision
3. `existing.body_hash != body_hash` — the store's body differs from the vault file (actual divergence, not just mapping drift)

**What happens when it fires:** The sync logs a WARNING (stderr, visible in
container logs) and skips the file. The store keeps the client's correction.
The vault file remains out of sync with the store — and that is correct: the
owner edits the vault next, and the edit produces a new body_hash that the sync
CAN write.

**What happens when the owner edits the vault file directly:** The new
body_hash differs from both the stored ALPHA and the client's BETA —
`expected_revision` points to the client's revision, the upsert succeeds, and
the store advances. Normal flow, no guard fires.

**The edge case this intentionally does NOT handle:** The sync writes A, the
client writes A (same body), the vault stays A. `body_hash` matches → the
unchanged check at line 549 fires → `unchanged += 1` → no write. That's
correct: the content didn't change, and the revision doesn't need to advance.

---

## 3. Correlation ID — where it's born and how it flows

**Birth:** The caller constructs it before the write. Three callers exist:

| Caller | Where |
|---|---|
| MCP `upsert_artifact` tool | `mcp_server.py:141` — the agent already passes `idempotency_key`; `correlation_id` joins it |
| VaultSync | `sync.py:577` — generated per-write: `f"vault-sync:{datetime.now(UTC).isoformat()}"` |
| Bot (Telegram) | `src/bot/main.py:197` — generated per-message: `f"tg:{chat_id}:{message_id}"` |

**Flow:** `WriteRequest.correlation_id` → `repository.upsert()` → written into
BOTH `ikig.artifacts.correlation_id` (current revision) AND
`ikig.artifact_revisions.correlation_id` (snapshot). The NOTIFY payload
(`artifact_events`) also includes it.

The repository already has the mechanism — it writes `client_id` from the
request into the artifacts row (`repository.py:210, 224`). Adding
`correlation_id` follows the same pattern:

```python
# In repository._create / _update:
"insert into ikig.artifacts (..., client_id, correlation_id, ...) "
"values (..., %s, %s, ...)"
#                                req.client_id    req.correlation_id
```

**Why not UUID4:** A structured identifier (`vault-sync:2026-11-25T14:30:00Z`,
`tg:12345:678`) is traceable back to its source without a lookup. A UUID4
forces a join that may not exist in logs.

---

## 4. Wiring VaultSync into Services

### Current state (violates ADR-037 D5)

`sync.py:706-708` — standalone script opens its own `DataClient`:

```python
client = DataClient()
repo = ArtifactRepository(client)
sync = VaultSync(repo, embeddings=EmbeddingService(client))
```

### Target state (one write path)

`wiring.py` gains one field and one factory:

```python
@dataclass
class Services:
    artifacts: ArtifactService
    relations: RelationService
    embeddings: EmbeddingService
    changes: ChangeFeed
    drafts: DraftService
    vault_sync: VaultSync | None = None   # NEW — None when no vault is mounted


def build_services(vault_roots: list[VaultSource] | None = None) -> Services:
    client = DataClient()
    repo = ArtifactRepository(client)
    embeddings = EmbeddingService(client)
    vault_sync = None
    if vault_roots:
        vault_sync = VaultSync(repo, sources=vault_roots, embeddings=embeddings)
    return Services(
        artifacts=ArtifactService(repo, embeddings),
        relations=RelationService(repo),
        embeddings=embeddings,
        changes=ChangeFeed(repo),
        drafts=DraftService(DraftRepository(client)),
        vault_sync=vault_sync,
    )
```

The sync loop (`sync.py:_run`) becomes a method on `Services`:

```python
# In wiring.py or a new src/services/sync_runner.py:
async def run_vault_sync(services: Services, interval: int) -> None:
    if services.vault_sync is None:
        return
    while True:
        report = await services.vault_sync.ingest()
        # ... logging
        if interval <= 0:
            return
        await asyncio.sleep(interval)
```

The standalone `sync.py:main` stays as a thin entry point that calls
`build_services(vault_roots=...)` and passes the result to `run_vault_sync`.

**What this fixes:** The sync no longer opens its own `DataClient`. There is
ONE pool, ONE repository instance, ONE write path. Tools and sync share the
same connection pool, and the pool's connection limit (5) governs both.

---

## 5. Observability surface

### What gets logged

| Event | Level | Channel | Payload |
|---|---|---|---|
| Provenance guard fires (sync skips file) | WARNING | stderr | file path, store's client_id, store's revision |
| Write with correlation_id | DEBUG | stdout | uid, revision, correlation_id, outcome |
| Transaction rollback (crash-recovery) | INFO | stderr | correlation_id, exception class |

### What the NOTIFY payload includes

`ikig.artifact_events` already carries `seq, uid, op, created_at`
(`repository.py:714-720`). Add `correlation_id` and `client_id` to the
payload so the bot and the websocket subscribers can trace a write back to
its origin without querying `artifact_revisions`.

### What the healthcheck gains

The healthcheck already inserts and rollback a row (`healthcheck.py:65-86`).
After this change, that row carries `client_id="healthcheck"` and
`correlation_id=f"healthcheck:{timestamp}"` — the correlation_id proves the
write pipeline carried the trace id from request to table.

### What the drift test covers

The existing `test_drift_invariants.py` guards that the canonical tool set
matches. Add one guard:

- `test_artifact_summary_exposes_client_id` — `ArtifactSummary.model_fields`
  includes `"client_id"` → the provenance guard CAN check it
- `test_artifact_table_has_correlation_id` — the column exists in `ikig.artifacts`

---

## 6. Migration path

| Step | What | Rollback |
|---|---|---|
| 1 | `0010_correlation_id.sql` applied | `down.sql` drops columns |
| 2 | `ArtifactSummary` gains `client_id` field | remove field → guard skips (null check) |
| 3 | `WriteRequest` gains `correlation_id` field | remove field → column stays NULL |
| 4 | Repository writes `correlation_id` | remove write → column stays NULL |
| 5 | VaultSync provenance guard added | remove guard → same behavior as today |
| 6 | VaultSync wired into `Services` | revert `sync.py` to standalone client |
| 7 | `ArtifactSummary`'s `client_id` backfilled for rows with NULL | backfill is additive; no rollback needed |

**Backfill (step 7):** Rows written before the model exposed `client_id` have
the column in SQL but `ArtifactSummary` returned `None`. After step 2, a
one-shot query copies the value from `ikig.artifact_revisions`:

```sql
update ikig.artifacts a set client_id = r.client_id
from ikig.artifact_revisions r
where a.uid = r.uid and a.revision = r.revision and a.client_id is null;
```

This is OPTIONAL — the provenance guard's null check already handles the gap
— but it closes the window permanently.

---

## 7. Falsifiable PASS

**The test:** Write artifact via `upsert_artifact` (simulating Telegram client,
`client_id="telegram-bot"`), then run VaultSync against a vault file with OLDER
bytes. Assert the store still holds the client's body, NOT the vault's.

```python
async def test_vault_sync_does_not_overwrite_client_edit(
    store_dsn: str, tmp_path: Path
) -> None:
    # 1. Vault sync writes alpha → store rev 1, client_id="vault-sync"
    # 2. Client writes beta via upsert_artifact → store rev 2, client_id="telegram-bot"
    # 3. Vault file STILL says alpha
    # 4. Vault sync runs again
    # 5. Guard fires → file is SKIPPED
    # 6. Store still holds beta (body_hash == sha256(beta))
    # 7. SyncReport.skipped includes the file path
```

**Falsification:** Remove the `existing.client_id != self._client_id` condition
from the guard → the sync overwrites beta with alpha → the test FAILS because
`stored.body_hash != sha256(beta)`.

**This test is the Q1 fix proven.** It is the counterpart of
`test_a_file_reverted_to_earlier_content_reaches_the_row` — that test proves
A→B→A reaches the row (idempotency key fix, issue #22). This test proves
client-edit→vault-sync does NOT overwrite (provenance guard, Q1).

---

## 8. What this plan does NOT touch

- **RLS, authentication, multi-user** — TECH.md §10 D1 keeps these deferred
- **`vault_write` (writing back to vault files)** — separate concern, gated on
  this guard being proven first
- **Hysteresis FSM** — ADR-037 D1 defers algorithms; this guard is a simple
  condition, not a state machine
- **`embed_text` / semantic search** — TECH.md D2 already removes it from v1
- **The kinds serialization fix (Q2)** — separate plan, separate migration