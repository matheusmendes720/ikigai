# 02 — Persistence Layer

> Three backends, one Protocol, one `_PersistentRepo` overlay that
> makes the JSON files look like a regular repository. The boot path
> is a state machine driven by environment variables and CSV presence.

The persistence layer has three physical backends and one abstraction
(`Repository` Protocol + `RepositoryBase[T_Entity]` ABC). Only one
backend is **active at runtime**: the JSON-file overlay in
`cli/state.py`. The other two (InMemory and SQLite) are fully
implemented but used in different contexts.

---

## 1. The 3 backends

| Backend | Module | Backing store | Used in |
|---|---|---|---|
| **InMemory** | `persistence/memory.py:23` | `dict[str, dict]` (in-process) | Tests, REPL, the home menu's transient `InMemoryRepository` instances, `_PersistentRepo` base class |
| **JSON files** | `cli/state.py:39-86` (overlay on `InMemoryRepository`) | `~/.time-tasker/*.json` (UTF-8, indent=2) | **The live runtime state** — what every `operational` command reads and writes |
| **SQLite** | `persistence/sqlite.py:77` | One SQLite DB file (single `entities` table, JSON `data` column) | **Built but not wired.** `SqliteRepository` is fully implemented, plus `MigrationRunner` and `migrations/001_initial.sql`. The boot path never uses it. |

**Why JSON is the active store** is detailed in §11 below. The
short version: zero-friction iteration, atomic-enough via
"overwrite on every mutation" semantics, easy to grep / inspect /
copy. The migration to SQLite is a deliberate decision the project
has not yet made.

---

## 2. Repository Protocol (`operational.types.Repository`)

`types.py:134-204` declares the structural Protocol:

```python
@runtime_checkable
class Repository(Protocol, Generic[T_Entity]):
    def get(self, id: UEID) -> T_Entity | None: ...
    def list(self, filters: dict[str, Any] | None = None) -> list[T_Entity]: ...
    def upsert(self, entity: T_Entity) -> UEID: ...
    def delete(self, id: UEID) -> bool: ...
    def count(self, filters: dict[str, Any] | None = None) -> int: ...
```

Five methods. `T_Entity` is `TypeVar("T_Entity", bound=BaseModel)` —
every repo stores a single Pydantic model class. The Protocol is
`@runtime_checkable` so that `isinstance(repo, Repository)` works in
tests and adapters.

---

## 3. `RepositoryBase[T_Entity]`

`persistence/base.py:18-189` is the ABC that fulfills the Protocol
and leaves only five abstract methods to subclasses:

| Abstract method | Purpose |
|---|---|
| `_load_all() -> dict[str, dict[str, Any]]` | Return the full store as `{id: data_dict}` |
| `_persist_one(entity_id, data)` | Write or overwrite one entity |
| `_remove_one(entity_id)` | Delete one entity (no-op if absent) |
| `_serialize(entity) -> dict` | Entity → plain dict |
| `_deserialize(data) -> entity` | dict → entity (re-validates via Pydantic) |

The base class implements the public CRUD:

- `get(id) -> T | None`
- `list(filters=None) -> list[T]`
- `upsert(entity) -> UEID` (idempotent insert-or-replace)
- `delete(id) -> bool` (returns whether the id existed)
- `count(filters=None) -> int`
- `exists(id)`, `get_many(ids)`, `upsert_many(entities)`,
  `delete_many(ids)` — convenience helpers.

Filtering in `list()` / `count()` is attribute equality:
`getattr(ent, attr) == expected` for each key in `filters`.
Unknown attributes raise `AttributeError`.

---

## 4. `InMemoryRepository`

`persistence/memory.py:23-98`. The simplest backend.

- **Storage:** `dict[str, dict[str, Any]]` (id → already-serialized dict).
- **Performance:** O(1) for `get` / `upsert` / `delete`; O(n) for
  `list` / `count` (with optional attribute-equality filter).
- **Process-lifetime:** lost on restart. Not persistent.
- **Iteration helpers:** `__iter__` yields deserialized entities;
  `__len__` returns count; `__bool__` is `len > 0`; `clear()` empties
  the store.

`_serialize` uses `model_dump(mode="python", exclude=computed_fields)`
so dates/times/enums are preserved as Python objects (not JSON
strings) for roundtrip integrity. `_deserialize` uses
`model_validate` — full Pydantic validation runs on every read, which
catches corruption.

---

## 5. `_PersistentRepo` (the JSON-file overlay)

`cli/state.py:39-86`. The **active** persistence layer.

```python
class _PersistentRepo(InMemoryRepository):
    """In-memory repo that snapshots to a JSON file on every mutation."""

    def __init__(self, model_class: type, filename: str) -> None:
        super().__init__(model_class)
        self._path = _STATE_DIR / filename
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw: dict[str, dict[str, Any]] = json.loads(
                self._path.read_text("utf-8"))
            self._store.update(raw)
        except (json.JSONDecodeError, OSError):
            pass  # corrupt file → start fresh

    def _dump(self) -> None:
        serialized = {}
        for eid, data in self._store.items():
            serialized[eid] = self._model_class.model_validate(data).model_dump(
                mode="json",
                exclude={*self._model_class.model_computed_fields.keys()},
            )
        self._path.write_text(
            json.dumps(serialized, indent=2, ensure_ascii=False), "utf-8")

    def _persist_one(self, entity_id: str, data: dict[str, Any]) -> None:
        super()._persist_one(entity_id, data)
        self._dump()

    def _remove_one(self, entity_id: str) -> None:
        super()._remove_one(entity_id)
        self._dump()

    def clear(self) -> None:
        super().clear()
        if self._path.exists():
            self._path.unlink()
```

### 5.1 Key design choices

- **Subclasses `InMemoryRepository`** — inherits O(1) operations, only
  adds I/O hooks. This is why you see no `_load_all()` /
  `_serialize()` overrides.
- **Re-validates on dump** (`model_validate(data).model_dump(...)`) —
  this round-trip catches any drift between in-memory state and the
  on-disk Pydantic model. If a field is added to the entity and
  removed from the JSON, the dump rebuilds the entity and writes
  the canonical form back.
- **Excludes computed fields** so `duration_minutes`, `regime_predicted`,
  `habit_level`, etc. don't pollute the JSON.
- **Tolerates corruption** (`cli/state.py:59-60`) — a bad JSON file is
  treated as empty rather than raising. The next `_dump()` overwrites
  with the clean in-memory state.
- **`clear()` deletes the file**, not just the in-memory dict. This
  keeps "fresh start" semantics for the demo flow.

### 5.2 The 14 instances

Defined at `cli/state.py:91-106`:

```python
routines: _PersistentRepo            = _PersistentRepo(Routine, "routines.json")
routine_logs: _PersistentRepo        = _PersistentRepo(RoutineLog, "routine_logs.json")
time_blocks: _PersistentRepo         = _PersistentRepo(TimeBlock, "time_blocks.json")
journals: _PersistentRepo            = _PersistentRepo(JournalEntry, "journals.json")
habits: _PersistentRepo              = _PersistentRepo(Habit, "habits.json")
sleep_records: _PersistentRepo       = _PersistentRepo(SleepRecord, "sleep_records.json")
pomodoros: _PersistentRepo           = _PersistentRepo(PomodoroRound, "pomodoros.json")
policy_decisions: _PersistentRepo    = _PersistentRepo(PolicyDecision, "policy_decisions.json")
policy_setpoints: _PersistentRepo    = _PersistentRepo(PolicySetpoints, "policy_setpoints.json")
ajustes_finos: _PersistentRepo       = _PersistentRepo(AjusteFino, "ajustes_finos.json")
day_contexts: _PersistentRepo        = _PersistentRepo(DayContext, "day_contexts.json")
daily_reflections: _PersistentRepo   = _PersistentRepo(DailyReflection, "daily_reflections.json")
lunch_records: _PersistentRepo       = _PersistentRepo(LunchRecord, "lunch_records.json")
transicoes: _PersistentRepo          = _PersistentRepo(TransicaoRegistrada, "transicoes.json")
```

All 14 are created at module import time. They share the
`TIME_TASKER_STATE_DIR` (default `~/.time-tasker/`,
`cli/state.py:35-36`).

---

## 6. `SqliteRepository`

`persistence/sqlite.py:77-241`. **Built but not wired into the boot
path.**

### 6.1 Storage

A single `entities` table:

```sql
CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,                  -- UEID
    entity_type TEXT NOT NULL,                     -- e.g. "routine"
    data        TEXT NOT NULL,                     -- JSON blob
    created_at  TEXT NOT NULL,                     -- ISO-8601 UTC
    updated_at  TEXT NOT NULL                      -- ISO-8601 UTC
);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_created ON entities(created_at);
```

Plus a `_migrations` metadata table (created by `MigrationRunner`,
`persistence/runner.py:99-119`).

The `data` column is a JSON dump of the entity (via
`json.dumps(data, default=_serialize_value, ensure_ascii=False)`).
`created_at` is preserved across upserts by `COALESCE((SELECT ...))`
in the upsert query (`persistence/sqlite.py:142-148`).

### 6.2 Connection management

`get_connection(db_path)` (`persistence/sqlite.py:34-50`) opens a
connection with:

- `PRAGMA journal_mode=WAL` (write-ahead log → concurrent readers)
- `PRAGMA foreign_keys=ON`
- `PRAGMA busy_timeout=5000` (5s wait on locked DB)
- `row_factory = sqlite3.Row` (dict-like access)

### 6.3 `ensure_table()`

`persistence/sqlite.py:200-224` issues a `CREATE TABLE IF NOT EXISTS`
plus an index. Safe to call on every boot.

### 6.4 Why not wired?

Two reasons: (1) the JSON overlay is good enough for the single-user,
sub-thousand-entities use case; (2) wiring SQLite means picking a
schema-versioning story, a backup story, and a migration plan for
existing JSON users. The work is **deferred, not abandoned** — the
repository, the migration runner, and the SQL schema are all
production-quality and tested in isolation.

---

## 7. Migrations

`persistence/migrations/001_initial.sql` is the only migration file.
It creates the `entities` table and the `_migrations` metadata
table.

`MigrationRunner` (`persistence/runner.py:24-191`) is the engine:

| Method | Purpose |
|---|---|
| `apply_all() -> list[str]` | Apply all pending migrations in sorted order |
| `apply_one(name) -> bool` | Apply a single migration by name; returns whether it was already applied |
| `applied() -> list[str]` | List applied migration names |
| `pending() -> list[str]` | List unapplied migration names |
| `get_applied_migrations(conn)` | Helper: query `_migrations` table |

**Internals** (`persistence/runner.py:99-167`):

1. `_ensure_meta_table()` — creates `_migrations` on construction
2. `_discover_pending(applied)` — globs `*.sql`, filters out applied
3. `_apply_one(name, path)` — reads SQL, computes SHA-256 checksum,
   runs via `executescript()`, records success/failure in
   `_migrations`

Failures are recorded (`success=0`) so they can be inspected later.
The checksum is a hint for future "have you tampered with my
migrations?" detection.

---

## 8. State machine for `state.py` boot

When `cli/state.py` is imported (i.e. on every `operational`
invocation), it runs `_auto_load_dataset()` at module level
(`cli/state.py:156`). The decision tree:

```
                        ┌─────────────────────┐
                        │  import state.py    │
                        └──────────┬──────────┘
                                   │
                                   ▼
                ┌─────────────────────────────────┐
                │  TIME_TASKER_DATASET set?       │
                │  (env var, value != "production")│
                └──────────────┬──────────────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
              NO (unset /                YES
              "production")
                  │                         │
                  ▼                         ▼
            ┌──────────┐    ┌──────────────────────────┐
            │  return  │    │  Any *.json already in   │
            │  (no-op) │    │  TIME_TASKER_STATE_DIR?  │
            └──────────┘    └────────────┬────────────┘
                                        │
                            ┌───────────┴──────────┐
                            │                      │
                        YES (don't              NO
                        overwrite user          (state dir empty)
                        data)
                            │                      │
                            ▼                      ▼
                       ┌──────────┐    ┌────────────────────────┐
                       │  return  │    │  resolve_dataset(name) │
                       │  (no-op) │    │  → CSV path            │
                       └──────────┘    └────────────┬───────────┘
                                                   │
                                                   ▼
                                  ┌─────────────────────────────┐
                                  │  import_from_csv_as_entities│
                                  │  (cli/csv_loader.py:261)    │
                                  │  → dict[entity_type, list]  │
                                  └────────────┬────────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────────┐
                                  │  for each (etype, entities):│
                                  │    repo_map[etype].upsert() │
                                  │    → writes JSON file       │
                                  └─────────────────────────────┘
```

**Implementation**: `cli/state.py:112-153`. Errors are caught
broadly (`except Exception: pass`) and the user can always run
`operational demo import-csv` manually to retry.

The 14-entry `repo_map` is the bridge between CSV entity-type names
(`"routine"`, `"time_block"`, ...) and Python repo instances
(`routines`, `time_blocks`, ...). It lives at `cli/state.py:132-147`.

---

## 9. CSV layer

`cli/csv_loader.py:1-301`. The read-only source-of-truth for
datasets.

### 9.1 Encoding and format

- **UTF-8 with BOM** (`utf-8-sig` on read, `utf-8-sig` on write) —
  Excel-friendly.
- **CRLF line endings** (`lineterminator="\r\n"` in the writer) —
  Windows-friendly.
- **Header row:** `entity_type,id,<field1>,<field2>,...`
- **One row per entity**, discriminated by `entity_type`.

### 9.2 Field encoding

`cli/csv_loader.py:72-105` (`_to_jsonable`) and
`cli/csv_loader.py:123-159` (`_from_jsonable`) handle round-trip
encoding:

| Python type | CSV representation |
|---|---|
| `None` | empty string |
| `datetime` / `date` / `time` | ISO 8601 string |
| `Enum` | `.value` (str) |
| `set` / `frozenset` | sorted JSON list |
| `list` / `dict` / `tuple` | `json.dumps(...)` |
| `bool` | `"true"` / `"false"` |
| `int` / `float` / `str` | string repr |

The asymmetry (sets become JSON lists on write, but lists are also
JSON on write) is intentional: lists stay as JSON, sets become
JSON-encoded sorted lists. `_from_jsonable` uses best-effort type
inference (int → int, float-shaped → float, JSON-shaped → `json.loads`,
else raw string).

### 9.3 The two public functions

| Function | File:line | Purpose |
|---|---|---|
| `import_from_csv(path) -> dict[str, list[dict]]` | `cli/csv_loader.py:212-258` | Read CSV → grouped dict of raw dicts. Raises `FileNotFoundError` or `ValueError` on bad input. |
| `import_from_csv_as_entities(path) -> dict[str, list[Any]]` | `cli/csv_loader.py:261-292` | Read CSV → grouped dict of **Pydantic instances** (via `model_validate`). Raises `pydantic.ValidationError` on bad data. |
| `export_to_csv(rows, path) -> int` | `cli/csv_loader.py:162-209` | Write entities to CSV. Returns the number of data rows written. |

For the full CSV schema, see [../data/01-CSV-SCHEMA.md](../data/01-CSV-SCHEMA.md).

---

## 10. Dataset selector

`cli/dataset_selector.py:1-85`. Resolves the `TIME_TASKER_DATASET`
env var to a CSV path.

Three built-in datasets are registered at
`cli/dataset_selector.py:26-40`:

| Name | CSV | Description |
|---|---|---|
| `synthetic` | `docs/synthetic.csv` | 30+ days with edge cases PAV |
| `golden` | `docs/golden.csv` | 7 canonical PAV scenarios |
| `production` | (empty path) | No auto-load — empty state, real user data |

`resolve_dataset(name=None)` (`cli/dataset_selector.py:48-77`)
defaults to `os.environ.get("TIME_TASKER_DATASET", "production")`.
Unknown names raise `ValueError`. The `production` dataset returns
a `DatasetRef` with an empty `Path()` — the boot path checks for
empty paths and skips the import.

`list_datasets()` returns a `DatasetRef` for every built-in. The
project root is resolved as `Path(__file__).resolve().parents[3]`
(`cli/dataset_selector.py:43-45`) — that walks up from
`src/operational/cli/dataset_selector.py` to `life-ops/operational/`.

**How to add a new dataset:**

1. Drop `docs/my_dataset.csv` in the project root.
2. Add an entry to `_BUILTIN_DATASETS` in `cli/dataset_selector.py:26-40`.
3. Use it: `TIME_TASKER_DATASET=my_dataset operational report daily`.

The boot path does the rest. No Python registration is needed beyond
the dict entry.

---

## 11. Why JSON is the current store (and not SQLite)

The JSON overlay was chosen for six reasons:

1. **Zero install friction.** A new user can `git clone`, install the
   package, run a command, and immediately have working state — no
   DB file to create, no migration to apply, no `ensure_table` call.
2. **Inspectability.** `cat ~/.time-tasker/sleep_records.json` works
   in any editor. Diffing across commits is trivial.
3. **Atomic-enough semantics.** Writes are full-file overwrites on
   every mutation. For a single-user system with sub-millisecond
   per-write latency, this is fine. The "atomic-enough" risk is a
   crash mid-write leaving a corrupt file — handled by
   `cli/state.py:59-60` (corrupt JSON is treated as empty).
4. **No migration story needed yet.** When the schema changes,
   `_dump()` re-validates and writes the canonical form back. New
   fields are filled by their Pydantic defaults; removed fields are
   silently dropped.
5. **Schema validation happens in Python.** Every read goes through
   `model_validate`, so the JSON is always self-checking.
6. **Sub-second cold start.** The full state for 30 days of usage
   (≈ 1000 entities) loads in < 50 ms. SQLite is not faster than that
   for the same workload.

**When will SQLite take over?**

- Multi-user (not on the roadmap — single-user by design).
- State size > 100 MB (each entity as JSON in a 1 GB file would
  still be fine, but `list()` with filters would slow down).
- Need for transactions across entities (the JSON overlay's
  per-entity `_dump()` is not atomic across repos).
- Need for SQL queries (the home menu and reports would benefit
  from `SELECT ... WHERE date BETWEEN ...` for large windows).

The `SqliteRepository` is built, tested, and migration-ready. Wiring
it is a swap of `cli/state.py:39-86` for the SQLite-backed
`_PersistentRepo` overlay. That work is on the deferred backlog.

---

## 12. Cross-references

- [01-MVC-LAYERS.md](01-MVC-LAYERS.md) — where persistence sits in
  the layering
- [04-IMPORT-GRAPH.md](04-IMPORT-GRAPH.md) — who imports `persistence`
- [../data/01-CSV-SCHEMA.md](../data/01-CSV-SCHEMA.md) — the CSV format
  produced/consumed by the loader
- [../data/02-DATASETS.md](../data/02-DATASETS.md) — the two built-in
  datasets and when to use them
