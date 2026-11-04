# AGENTS.md — `src/data/`

**Score 4 (3 modules, 100% code, ~640 LOC, 4 public names) — created: distinct domain (the store's only writer).** The Postgres layer: pooled connections, retries, and the artifact repository.

## OVERVIEW
Two modules and nothing else. `client.py` moves bytes and manages connections; `repository.py` maps the DOM onto SQL. Neither knows what an artifact *means* — that belongs to `src/services/`.

## WHERE TO LOOK
| Module | Role |
|---|---|
| `client.py` | `DataClient` — pool, retry, transaction helper, healthcheck. `StoreNotConfiguredError`, `StoreUnavailableError`. |
| `repository.py` | `ArtifactRepository` — every read and write the DOM allows against the store. |
| `__init__.py` | package docstring only; no re-exports. |

## CONVENTIONS
- **The DSN comes from the environment, never a file.** `STORE_DSN_ENV` (`IKIGAI_STORE_DSN`) is declared in `src/contracts/store.py`; `DataClient.__init__` raises `StoreNotConfiguredError` when it is unset, and the message says so.
- **`psycopg` and `psycopg-pool` are optional runtime dependencies.** Both imports sit behind `try/except ImportError`; the missing-driver path raises `StoreUnavailableError` carrying the install line.
- **`execute()` retries only transient failures** — 3 attempts, exponential backoff from 0.2 s. `_is_transient()` matches the exception *class name* against `OperationalError`, `InterfaceError`, `SerializationFailure`, `DeadlockDetected`, `ConnectionException`. A serialization failure is the database asking to retry, not an error to surface.
- **The optimistic write never falls back to an upsert.** `upsert()` claims `ikig.idempotency_keys` first; a replayed key returns `outcome="unchanged"` with the current revision and writes nothing. A stale `expected_revision` raises `ConflictError` and changes nothing.
- **Pagination is by cursor, never offset.** `_decode_cursor` unpacks the opaque `[updated_at, uid]` JSON pair and `_search_structured` compares `(updated_at, uid) < (%s::timestamptz, %s)` — the cast is required, Postgres will not compare a `timestamptz` column with a text parameter.
- **Deletes are soft.** `soft_delete()` sets `deleted_at` and bumps the revision under the same guard; the row and its history stay.
- **The revision history is append-only.** `_insert_revision` writes a JSONB snapshot of every write into `ikig.artifact_revisions` — never an update, never a delete.
- **Embeddings are rendered as a pgvector literal.** `_vector_literal()` builds `"[0.1,0.2]"` text and lets the column cast it, which keeps the `pgvector` Python package out of the dependency set; `set_embedding` casts with `%s::vector`.
- **The `Jsonb` adapter is optional** — `psycopg.types.json.Jsonb` is imported under `try/except ImportError` and falls back to a plain dict.

## ANTI-PATTERNS
- **Never write a query that bypasses the revision guard.** Every update filters on `uid = %s and revision = %s and deleted_at is null`; dropping the `revision` predicate turns optimistic concurrency into a last-write-wins race.
- **Never hard-delete an artifact row.** `soft_delete` is the sanctioned path — the history must outlive the artifact.
- **Never retry a non-transient failure.** The bare `raise` inside `_retry` is deliberate; retrying a validation error only delays the error.
- **Never hardcode a DSN, a schema name, or a table name here.** `DOMAIN` (`ikig`) and the kind→table map are the contract with the migrations, and they live in `src/contracts/store.py`.
- **Never widen `KIND_TABLES` from this module.** `_write_extension` branches on the *model type*, so a new kind needs a model, a table entry and a migration — three places, not one.

## NOTES
- The SQL issued here lives in `src/contracts/migrations/0001_init.sql` … `0003_rls.sql`. The schema is `ikig`; the tables are `ikig.artifacts`, `ikig.artifact_relations`, `ikig.artifact_revisions`, `ikig.idempotency_keys`, plus one extension table per typed kind.
- Row-level security filters on the `client_id` JWT claim, so another client's rows are invisible rather than an error. `ForbiddenError` means an explicit denial.
