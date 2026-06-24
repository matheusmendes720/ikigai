# Data Architecture

> **Status:** 🟢 Authoritative. Synced with `packages/core/src/operational/entities/`, `persistence/`, and `apps/cli/state.py` at time of writing.
> **Related:** `00-DATA-MODEL.md`, `01-CSV-SCHEMA.md`, `02-DATASETS.md`, `03-CONTRACTS.md`, `02-PERSISTENCE-LAYER.md`.

This document describes the data side of `operational`: the entity graph, the canonical JSON contracts, the three persistence backends, the CSV/dataset formats, and the migration story.

---

## 1. Entity Graph

```
            ┌────────────┐
            │  Routine   │ ◀────── 1 user-defined shape: MANHA/TARDE/NOITE + CORE/FLEX
            └─────┬──────┘
                  │ 1..n
                  ▼
            ┌────────────┐   per-day instance
            │ RoutineLog │ ◀── start/stop events (id, routine_id, day, start_ts, stop_ts)
            └────────────┘

            ┌────────────┐
            │ TimeBlock  │ ◀────── gross entry/exit per day (ADR 2026-06-07)
            └────────────┘

            ┌────────────┐                  ┌──────────────────┐
            │  Habit     │ ◀─────────────▶  │  HabitEvent      │ (streak, day)
            └────────────┘                  └──────────────────┘

            ┌────────────┐                  ┌──────────────────┐
            │  Metric    │ ◀─────────────▶  │  SleepRecord     │
            └────────────┘                  └──────────────────┘

            ┌────────────────┐               ┌──────────────────┐
            │ PomodoroRound  │ (optional,    │  PomodoroPhase   │
            └────────────────┘  plug-in)     └──────────────────┘

            ┌──────────────────┐              ┌────────────────────┐
            │ PolicyDecision   │ ◀─────────── │ PolicySetpoints    │
            └──────────────────┘              └────────────────────┘

            ┌────────────────────┐
            │ DayContext         │ ◀──── per-day rolled-up state (computed by consolidator)
            ├────────────────────┤
            │ DailyReflection    │
            ├────────────────────┤
            │ LunchRecord        │
            ├────────────────────┤
            │ TransicaoRegistrada│
            └────────────────────┘

            ┌────────────┐
            │ AjusteFino │ ◀──── fine-tuning adjustments (per-day overrides)
            └────────────┘

            ┌────────────┐
            │ V3Snapshot │ ◀──── forward-compat schema (one row per major version)
            └────────────┘
```

### Cardinality

- **Routine ↔ RoutineLog:** 1..n per day. A routine has many `RoutineLog` rows, one per day it ran.
- **Habit ↔ HabitEvent:** 1..n. Each event is a per-day observation that drives `compute_H(streak, λ)`.
- **TimeBlock** and **RoutineLog** are siblings of the same day — they capture different slices of the day.
- **DayContext** is **derived state** — the consolidator computes it nightly from the other entities.

### Pydantic v2 conventions

Every entity follows the same recipe:

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import ClassVar

class Routine(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    name: str
    period: Period
    type: RoutineType
    created_at: datetime
    version: ClassVar[int] = 1  # bumped on schema break
```

Three properties of every entity:
1. **Frozen** — instances are immutable; mutations create new instances.
2. **`extra="forbid"`** — unknown fields are rejected at deserialisation, so silent schema drift is impossible.
3. **`version: ClassVar[int]`** — schema version is declared on the entity itself.

---

## 2. JSON Contracts (canonical wire format)

Every entity serialises to JSON with the same shape (Pydantic's default). Examples:

```json
{
  "id": "routine-2026-06-01-morning-run",
  "name": "Morning run",
  "period": "MANHA",
  "type": "CORE",
  "created_at": "2026-06-01T07:00:00Z",
  "version": 1
}
```

```json
{
  "id": "rlog-2026-06-22-morning-run",
  "routine_id": "routine-2026-06-01-morning-run",
  "day": "2026-06-22",
  "start_ts": "2026-06-22T06:58:00Z",
  "stop_ts":  "2026-06-22T07:32:00Z",
  "version": 1
}
```

```json
{
  "id": "day-2026-06-22",
  "date": "2026-06-22",
  "regime": "MAINTAIN",
  "q_he": 0.81,
  "policy_state": "MAINTAIN",
  "routines": 4,
  "habits_done": 3,
  "habits_total": 5,
  "sleep_hours": 7.5,
  "version": 1
}
```

Every CLI subcommand supports `--json` and emits these same shapes so the data model is identical across interfaces.

---

## 3. Persistence Backends

Three storage strategies, all behind the `Repository[T]` Protocol:

```
                ┌─────────────────────────────────┐
                │   Repository[T]   (Protocol)    │
                └────┬───────────────┬────────┬───┘
                     │               │        │
              ┌──────▼─────┐  ┌──────▼────┐  ┌▼──────────────┐
              │ InMemory   │  │ SQLite    │  │ JSON-Flat     │
              │ (tests)    │  │ (default) │  │ (CLI state)   │
              └────────────┘  └───────────┘  └───────────────┘
```

### 3.1 InMemory (`persistence/memory.py`)

- `dict[EntityId, T]` under the hood.
- Used by tests and ephemeral runs (`pav demo`).
- Thread-safe via a single `RLock`.

### 3.2 SQLite (`persistence/sqlite.py`)

- One file per repo: `~/.time-tasker/<entity>.db` or a single `pav.db` (configurable).
- Schema per entity — versioned via `MigrationRunner`.
- Connection pool: `sqlite3.Connection` wrapped in a tiny custom pool (no ORM).

### 3.3 JSON-Flat (`apps/cli/state.py`)

- Used by the CLI's "state" subcommands — `pav state show`, `pav state reset`, etc.
- One JSON file per entity, flat at `~/.time-tasker/<entity>.json`.
- Best for hand-inspection and version control.

### 3.4 Migration story

`persistence/runner.py` runs forward-only migrations on startup:

```
0001_init.sql            creates v3 schema baseline
0002_add_policy_setpoints.sql
0003_add_ajuste_fino.sql
...
```

Migrations are idempotent (each records its name in a `schema_migrations` table) and forward-only. Rollback is intentionally not supported — the SQLite file is copied to `<file>.bak-<timestamp>` before each migration runs.

---

## 4. CSV / Dataset formats

Two canonical datasets ship in `apps/cli/datasets/`:

### 4.1 `golden.csv` (curated regression dataset)

- 90 days × 14 entities → ~12,600 rows
- Hand-verified by the author; used for visual regression tests
- Schema declared in `docs/data/01-CSV-SCHEMA.md`

### 4.2 `synthetic.csv` (algorithmically generated)

- 180 days × 14 entities
- Seeded with a deterministic PRNG so re-runs match
- Used for property-based tests + load tests

Both are loaded by `apps/cli/csv_loader.py` into the InMemory repository, then asserted against the SQLite round-trip via `verify_sprint.py`.

---

## 5. Contracts (CLI ↔ entities ↔ storage)

Every CLI subcommand follows the same data contract:

```
                    ┌─────────────┐
   user input ───▶ │ Typer cmd   │
                    └──────┬──────┘
                           │ builds raw dict
                           ▼
                    ┌─────────────┐
                    │ factories.py│  validates + constructs Pydantic entity
                    └──────┬──────┘
                           │ Entity
                           ▼
                    ┌─────────────┐
                    │ Repository  │  stores
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ output      │  --json or table
                    └─────────────┘
```

Key invariants enforced at every layer:

- **No entity is constructed outside `factories/`** — the CLI/TUI never call Pydantic directly.
- **No repository returns a raw dict** — always a Pydantic instance.
- **No command emits non-JSON output unless `--json` is absent** — the same command produces the same data shape in either format.

---

## 6. Index / search

There is no central search service; each repository is queried by primary key (entity `id`) or by indexed columns (`day`, `routine_id`, `habit_id`). Aggregation queries (e.g. "all routines in MANHA") live in `core/consolidator.py` and `core/weekly_aggregator.py` — pure functions that take a repository snapshot and return derived entities.
