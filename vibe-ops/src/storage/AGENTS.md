# src/storage — persistence layer

## OVERVIEW
Where engine state lives — ORM tables, vector-store adapters and a local 3-part `UEID`.

SQLAlchemy ORM, SQLite/Chroma adapters and the mesh catalog. Relative imports inside the
package (`from .orm import Base`).

## WHERE TO LOOK
| File | Contents |
|------|----------|
| `orm.py` | `Base` (DeclarativeBase), `StudyProjectORM`, `StudyTopicORM`, `RoadmapItemORM` |
| `metadata_orm.py` | `MetadataCatalogORM`, `StateMachineORM` (mesh catalog + lifecycle log) |
| `data_mesh_adapter.py` | `DataMeshAdapter` — orchestrates SQLite + Chroma writes |
| `sqlite_adapter.py` | `SQLiteAdapter` — sqlite3 CRUD over `planning_entities` |
| `chroma_adapter.py` | `ChromaAdapter` — vector upsert/query |
| `sqlite_vec_integration.py` | `SQLiteVecIntegration` — sqlite-vec when available, NumPy fallback |
| `ueid.py` | `UEID` — local 3-part id helper |
| `schema.sql` | raw DDL for the SQLite schema |
| `vector_store.py` | **empty placeholder** |

## CONVENTIONS
- **Relative imports** are the norm here (`from .orm import Base`) — the only package in the
  tree that uses them exclusively.
- **`Base` is the single declarative base** — ORM classes must inherit it so metadata stays
  in one registry.
- **`UEID` here is 3-part** (`<CLUSTER>:<ENTITY_TYPE>:<ID>`) and `UEID.parse` raises unless
  it has exactly 3 parts. The canonical UEID in `src/contracts/common.py` is 4-part
  (`<type>:<slug>:<uuid>:<hash>`, ADR-014 + ADR-026 R4) — do not mix the two forms; use the
  shared contract type for anything crossing into `src/contracts/` or `src/mesh/`.
- `DataMeshAdapter.sync_entity` writes to SQLite and, when `content` is given, to Chroma
  under the UEID — only scalar metadata is forwarded to the vector store.
- `numpy` is imported at module level by `sqlite_vec_integration.py` and `knowledge_tree.py`
  but is not declared in `pyproject.toml`.

## ANTI-PATTERNS
- Never use this package's `UEID` as a canonical UEID in `data/review_queue/` or in mesh
  payloads — the formats differ (3-part vs 4-part).
- Never introduce a second declarative base; extend `Base`.
- `vector_store.py` is a 0-byte placeholder and `scripts/search_mesh.py` imports
  `VectorStore` from it — that import cannot work until the module is implemented.
- Do not delete rows through the adapters — sync writes are append-only by contract.
