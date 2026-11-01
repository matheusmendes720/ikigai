# AGENTS.md — `src/contracts/`

**Score 15 (20 Python modules + 6 SQL migrations, own Hatchling config, 59 exports, imported by 91 repo files) — updated: distinct domain.** The only contract surface shared by every layer — and, since ADR-037, also the contract surface of the store.

## OVERVIEW
Two families live here and they do not overlap:
- **The DOM** (`dom.py`, `dom_kinds.py`, `store.py`, `errors.py`) — the unified data model: ten artifact kinds, the typed error surface, and the store's constants.
- **The planning tree** (`common.py`, `base.py`, `sonho.py`, `objetivo.py`, `projeto.py`, `entrega.py`, `tarefa.py`, `meta.py`, `task.py`, `task_change.py`, `planning.py`, `metrics.py`, `investigation.py`) — identity, the task/plan tree, metrics, mesh events, investigations.

No logic beyond validation. `migrations/` holds the store's physical SQL.

## WHERE TO LOOK
| Model | Module |
|---|---|
| `Artifact` spine, `ArtifactKind` (10), `Relation` / `RelationType`, `WriteRequest` / `WriteOutcome`, `SearchQuery` / `SearchResult`, `make_uid` | `dom.py` |
| `KIND_MODELS` + the 10 typed kinds (`SonhoArtifact` … `TarefaArtifact`) | `dom_kinds.py` |
| `DOMAIN="ikig"`, `EMBEDDING_DIM=1536`, `KIND_TABLES`, `PROVIDER="supabase"`, `RLS_CLIENT_CLAIM`, `STORE_DSN_ENV` | `store.py` |
| `DataLayerError` + `ConflictError` / `InvalidPayloadError` / `ForbiddenError` / `NotFoundError` | `errors.py` |
| `UEID`, `Period`, `Priority`, `EntityType`, `RegimeState`, `TimestampMixin` | `common.py` |
| `UEID` regex + `PaeCyclePhase` / `PlanTier` / `VectorKey` literals | `common.py` |
| `BasePlanContract` (base for the 6 plan entities) | `base.py` |
| `Sonho` `Objetivo` `Meta` `Projeto` `Entrega` `Tarefa` | `sonho.py` `objetivo.py` `meta.py` `projeto.py` `entrega.py` `tarefa.py` |
| `Task` `Subtask` `ChecklistItem` `Project` `Milestone` `Deliverable` | `task.py` |
| `TaskChange` `PropagationEvent` `TaskAction` `TaskStatus` | `task_change.py` |
| `PlanningCycle` `Wave` `Sprint` `VaultEvent` | `planning.py` |
| `Burndown` `ExecutionRate` `QHEScore` | `metrics.py` |
| `Investigation` `InvestigationStatus` | `investigation.py` |
| The store's SQL: schema `ikig`, indexes, RLS policies | `migrations/` |

## CONVENTIONS
- **`__all__` in `__init__.py` is grouped by domain, not alphabetical** (`common` → plan hierarchy → task → **dom → dom errors** → metrics → investigation). The `RUF022` noqa on the assignment is deliberate — do not "fix" the ordering.
- **The DOM spine holds only what every kind shares.** Kind-specific fields live in `dom_kinds.py` as typed subclasses that narrow `kind` with a `Literal` discriminator, so no client can invent a field and no kind degrades into a free-shape JSON blob.
- **Prose kinds require a body; KPI, OKR and decisions carry typed fields instead.** That split is exactly what `KIND_TABLES` mirrors on the SQL side.
- **A kind with typed fields has an extension table, and a kind with a table has typed fields.** `KIND_TABLES` in `store.py` is the contract between the two ends, and a drift test holds both ends to it.
- **`make_uid` validates through the `UEID` constructor, not string concatenation**, so a malformed slug or hash is rejected at the boundary instead of failing a SQL CHECK constraint later.
- **`TaskChange` / `TaskStatus` are deliberately NOT re-exported** from `__init__.py`; consumers import them from `src.contracts.task_change` directly to avoid a circular import surface.
- **`UEID` is a `str` subclass, not a `BaseModel`.** It carries a custom Pydantic core schema (`GetCoreSchemaHandler` / `core_schema`), so it validates as a plain string everywhere.
- **The 6 plan entities subclass `BasePlanContract`** and inherit its `frozen=True, extra="forbid"` config plus the `ikigai_vectors` non-empty validator. Each adds only its own fields.
- **`Investigation` uses `inq_id`, not a UEID** — a separate namespace, deliberately outside the plan hierarchy.
- **`TaskAction` is a `StrEnum`** with `create/update/delete/done` plus `tag_add/tag_remove/tag_clear`. `TAG_LIST` is intentionally absent (read-only, bypasses the queue).

## ANTI-PATTERNS
- **The UEID regex in `common.py` is a triple-pattern, not the 4-part form quoted in the root `AGENTS.md`.** It accepts 4-part short, 4-part long-UUID, and 5-part legacy, with namespace `{2,8}`:
  ```
  ^[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}$   (or long-uuid, or 5-part)
  ```
  The SQL `artifacts_uid_format` CHECK in `migrations/0001_init.sql` copies this pattern **verbatim** — keep it that way.
  Three other regexes exist elsewhere and are NOT kept in sync: `src/mesh/adapters/taskdog.py` (byte-identical copy of this one, inlined to dodge a circular import), `src/ikigai/contracts/proposal.py` (`{2,5}` 4-part), `src/ikigai/src/chat/schema.py` (`{2,10}` 4-part). Do not "unify" them — the drift tests assert each one separately.
- **`QHEScore.qhe` and `.regime_predicted` raise `NotImplementedError`** by design (ADR-013). Do not implement the formula here; the PAV kernel is archived.
- **Never re-define `UEID`, `Task`, or `TaskChange` outside this package.** `src/ikigai/contracts/proposal.py` and `src/ikigai/src/chat/schema.py` each define their own `Proposal` class with a *different* field set (`approval_state` vs `status`) — neither is the canonical `TaskChange`.
- **Never add business logic to a contract model.** `base.py` keeps `_check_vector_subset` as a *static helper* for the application layer precisely because the validator cannot reach the parent registry.
- **Never change an applied migration.** The runner checksums each file and raises if it changed after being applied; roll back with `down` first, then edit.
- **Never change `EMBEDDING_DIM` in Python alone.** The HNSW index in `0002_indexes.sql` is built for exactly one dimension — a mismatch is a migration, not a config edit.

## COMMANDS
```bash
cd src/contracts && uv build && uv sync && uv run pytest
ruff check src/contracts             # uses src/contracts/pyproject.toml [tool.ruff]
python -m src.contracts.migrations.apply up          # apply pending (checksum-locked)
python -m src.contracts.migrations.apply status
python -m src.contracts.migrations.apply down --yes  # roll back the last one
```
