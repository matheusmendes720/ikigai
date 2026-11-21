# AGENTS.md — `src/contracts/`

**Score 15 — distinct domain: the DOM, the identity, and the store's SQL.** The only contract surface shared by every layer — and, since ADR-037, also the contract surface of the store.

## OVERVIEW
TWO families live here, and they are the DOM (ADR-037 D2):
- **The DOM** (`dom.py`, `dom_kinds.py`, `store.py`, `errors.py`, `drafts.py`) — the unified data model: ten artifact kinds, the typed error surface, the draft envelope, and the store's constants.
- **The identity** (`common.py`) — the UEID and the two axes the kinds share.

No logic beyond validation. `migrations/` holds the store's physical SQL and the runner that applies it.

## WHERE TO LOOK
| Model | Module |
|---|---|
| `Artifact` spine, `ArtifactKind` (10), `Relation` / `RelationType`, `WriteRequest` / `WriteOutcome`, `SearchQuery` / `SearchResult`, `make_uid` | `dom.py` |
| `KIND_MODELS` + the 10 typed kinds (`SonhoArtifact` … `TarefaArtifact`) | `dom_kinds.py` |
| `DOMAIN="ikig"`, `EMBEDDING_DIM=1536`, `KIND_TABLES`, `PROVIDER="postgres"`, `RLS_CLIENT_CLAIM`, `STORE_DSN_ENV` | `store.py` |
| `DataLayerError` + `ConflictError` / `InvalidPayloadError` / `ForbiddenError` / `NotFoundError` | `errors.py` |
| `UEID` | `common.py` |
| `Priority` enum + `PlanTier` / `VectorKey` literals | `common.py` |
| `Draft` · `DraftSaveRequest` · `DraftOutcome` — the draft envelope | `drafts.py` |
| The store's SQL: schema `ikig`, indexes, RLS policies | `migrations/` |
| The migration runner — advisory lock, SHA-256 ledger, `up` / `status` / `down --yes` | `migrations/apply.py` |
| The full-text configuration the index needs | `migrations/0001_text_search.sql` — Postgres ships only `english` and `simple`; this creates `portuguese` BEFORE `0002_indexes.sql` builds the GIN index over it |

## CONVENTIONS
- **`__all__` in `__init__.py` is grouped by domain, not alphabetical** (`common` → **dom → dom errors**). The `RUF022` noqa on the assignment is deliberate — do not "fix" the ordering.
- **The DOM spine holds only what every kind shares.** Kind-specific fields live in `dom_kinds.py` as typed subclasses that narrow `kind` with a `Literal` discriminator, so no client can invent a field and no kind degrades into a free-shape JSON blob.
- **Prose kinds require a body; KPI, OKR and decisions carry typed fields instead.** That split is exactly what `KIND_TABLES` mirrors on the SQL side.
- **A kind with typed fields has an extension table, and a kind with a table has typed fields.** `KIND_TABLES` in `store.py` is the contract between the two ends, and a drift test holds both ends to it.
- **`make_uid` validates through the `UEID` constructor, not string concatenation**, so a malformed slug or hash is rejected at the boundary instead of failing a SQL CHECK constraint later.
- **`UEID` is a `str` subclass, not a `BaseModel`.** It carries a custom Pydantic core schema (`GetCoreSchemaHandler` / `core_schema`), so it validates as a plain string everywhere.
- **The first segment of a UEID is the kind's namespace** (`KIND_NAMESPACE` in `dom.py`): `snh` sonho, `pln` plano, `ond` onda, `fse` fase, `rev` revisao, `not` nota, `kpi`, `dec` decisao, `okr`, `tsk` tarefa.
- **Migrations are numbered pairs**: `<NNNN>_<name>.sql` up and `<NNNN>_<name>.down.sql` down, applied in filename order. `0001_text_search.sql` sorts before `0002_indexes.sql` — the ordering is the dependency, so a file is never renamed to "tidy" it.
- **The runner is checksum-locked.** One `pg_advisory_lock` (`ikig_schema_migrations`), one ledger (`ikig.schema_migrations`) holding a SHA-256 per file; each migration runs in its own transaction; `down` requires `--yes`.
- **A draft carries no idempotency key.** The revision guard IS the de-duplication — `ikig.draft_keys` was deliberately dropped in migration `0008`; draft identity is `(client_id, draft_id)`, never a UEID.

## ANTI-PATTERNS
- **The UEID regex in `common.py` is a triple-pattern, not the 4-part form quoted in the root `AGENTS.md`.** It accepts 4-part short, 4-part long-UUID, and 5-part legacy, with namespace `{2,8}`:
  ```
  ^[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}$   (or long-uuid, or 5-part)
  ```
  The SQL `artifacts_uid_format` CHECK in `migrations/0001_init.sql` copies this pattern **verbatim** — keep it that way. The published surface has exactly one source, and `test_drift_invariants.py` holds it to that.
- **Never add business logic to a contract model.** A model is a data container with invariants; the rules live in `src/services/`.
- **Never change an applied migration.** The runner checksums each file and raises if it changed after being applied; roll back with `down` first, then edit.
- **Never rename a migration to reorder it.** The filename order IS the dependency order (`0001_text_search` before `0002_indexes`); a rename silently changes the schema's history.
- **Never change `EMBEDDING_DIM` in Python alone.** The HNSW index in `0002_indexes.sql` is built for exactly one dimension — a mismatch is a migration, not a config edit.
- **Do not re-introduce the planning tree.** The task/plan hierarchy, the PAV metrics (`QHEScore`, `Burndown`, `ExecutionRate`), the mesh events and the investigations were the pre-ADR-037 model's modules. Nothing imported them, and they left the published tree with the scope they belonged to (ADR-037 §"publicação independente"). A drift test names them.

## COMMANDS
```bash
cd src/contracts && uv build && uv sync && uv run pytest
ruff check src/contracts             # uses src/contracts/pyproject.toml [tool.ruff]
python -m src.contracts.migrations.apply up          # apply pending (checksum-locked)
python -m src.contracts.migrations.apply status
python -m src.contracts.migrations.apply down --yes  # roll back the last one
```
