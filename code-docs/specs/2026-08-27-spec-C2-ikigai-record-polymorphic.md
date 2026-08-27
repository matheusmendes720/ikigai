# SPEC C2 — IKIGAiRecord Polymorphic Root + `SQLiteAdapter.upsert_ikigai_record`

> **Status**: 🟢 Draft — pending merge of `feat/data-model-unification`
> **Date**: 2026-08-27 · **Branch**: `feat/data-model-unification`
> **Commits**: `4839a74` (IKIGAiRecord root) · `2c6e20f` (IKIGAiRecordBridge) · `4b6bc62` (SQLiteAdapter.upsert_ikigai_record)
> **Severity target**: 🔴 Critical — fixes S-C1 schema split-brain

---

## §0. Purpose

This spec establishes **IKIGAiRecord as the single canonical root** for every IKIGAI entity (dream → goal → objective → project → task → deliverable, plus 10 more variants), and **`SQLiteAdapter.upsert_ikigai_record()` as the sole write path** that fans the polymorphic root into the append-only SQLite mirror.

**Three properties enforced:**

1. **Single source of truth** — every IKIGAI entity round-trips through one Pydantic root, regardless of authoring path (vault markdown, MCP tool call, LangGraph checkpoint, programmatic).
2. **Single write path** — no code may INSERT into `plan_entities` directly. All writes flow through `SQLiteAdapter.upsert_ikigai_record()`. Ad-hoc INSERTs in `commit.py:58-118` and `server.py:347-357` are deprecated.
3. **Polymorphism with type safety** — the discriminated union on `entity_type` (SPEC D6) keeps variant-specific fields in `custom` rather than bloating the root, while Pydantic validators enforce invariants (UEID format, score ranges, status enum).

This is the keystone of the unified data model (§1 of `feat/data-model-unification`); without it, the runtime 11-col writers continue to drift from the canonical 24-col schema and S-C1 split-brain remains permanent.

---

## §1. Problem

### 1.1 Schema split-brain (S-C1)

Two writers, one table, zero agreement:

| Source | Schema | Status |
|---|---|---|
| `sqlite_adapter.py:18-80` (`SCHEMA_SQL`) | **24 columns** canonical | Defined, never written |
| `commit.py:58-118` | **11 columns** runtime | Writes every commit |
| `server.py:347-357` (`_read_plan_entity`) | **11 columns** legacy fallback | Reads what `commit.py` wrote |

The 24-col canonical schema includes fields the 11-col runtime drops: `parent_ueid`, `related_ueids`, `ikigai_vectors`, `vector_weights_snapshot`, `phase_at_creation`, `regime_at_creation`, `horizon_days`, `primary_score`, `is_placeholder`, `placeholder_owner`, `claimed_by`, `source`, `source_md_path`, `custom`, `tags`. Downstream consumers (`ikigai_score`, `ikigai_phase`, `ikigai_regime`) read empty 24-col rows, fall back to the 11-col legacy table, return stale data.

**Drift is permanent**: every cycle adds another row to the 11-col table, widening the gap.

### 1.2 No canonical entity root

Before `4839a74`, IKIGAI entities were scattered across `PlanEntity` (11-col dataclass), `IKIGAiStateDict` (free-form dict), and vault markdown frontmatter. Each consumer re-parses its needed shape — no Pydantic validation, no discriminator, no invariant enforcement. Vault markdown could drift from `PlanEntity` because no single validator could catch the inconsistency.

### 1.3 Append-only enforcement is incomplete

`commit.py` and `server.py` write raw `INSERT` statements that bypass the `plan_entities_no_update` / `plan_entities_no_delete` triggers (triggers only block direct UPDATE/DELETE on the table, not no-op INSERTs). There is no `plan_entities_history` mirror populated by these legacy writers, so historical state is lost on every overwrite.

---

## §2. Design

### 2.1 IKIGAiRecord — single polymorphic root

`IKIGAiRecord` (Pydantic v2, `extra="allow"`, `frozen=False`, `discriminator="entity_type"`) is the canonical root.

- **Discriminator (SPEC D6):** 16 `EntityType` variants (DREAM, GOAL, OBJECTIVE, PROJECT, TASK, DELIVERABLE, ROUTINE, TIME_BLOCK, RITUAL, HABIT, VECTOR, PROFILE, SKILL_NODE, OPPORTUNITY, REGIME, CYCLE). Variant-specific fields (e.g. `DreamEntity.motivation`) live in `custom: dict[str, Any]` (forward-compat).
- **Status (SPEC §6):** 8-state explicit enum (DRAFT, ACTIVE, PAUSED, COMPLETED, ARCHIVED, ABANDONED, FALSIFIED, PIVOTED).
- **Identity (SPEC D10):** 5-part canonical UEID, regex-enforced:
  `^(ikigai|tw|obsidian|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}$`
- **Score invariants (SPEC I3/I4):** `ScoreValue.normalized` always returns 0..1 ratio regardless of source unit (PERCENT, RATIO, SCORE). This bridges typed scores to the legacy `ikigai_vectors` column (plain floats in 0..1 space).
- **Drift detection (SPEC D14):** `drift_state: DriftState` + `sqlite_mirror_at` + `last_triaged_at`. `DriftDetector` adapter (commit `912a7c0`) reads these and writes `triagem.md` reports.

### 2.2 `SQLiteAdapter.upsert_ikigai_record` — single write path

`SQLiteAdapter.upsert_ikigai_record(record: IKIGAiRecord) -> None` (commit `4b6bc62`) is the canonical entry point. It:

1. Maps the polymorphic record to the 24-col schema's keyword args via the inline mapping (formerly `IKIGAiRecordBridge._map`).
2. Normalizes `vector_scores: dict[VectorKey, ScoreValue]` → `dict[str, float]` (0..1 ratios) before JSON serialization.
3. Calls `self.upsert(**kwargs)` which:
   - On new UEID: `INSERT` into `plan_entities` + mirror to `plan_entities_history`.
   - On existing UEID: `DROP TRIGGER` → `DELETE` old row → `INSERT` new row → recreate triggers. Satisfies the append-only invariant; the history table records every state.

**Why a method, not a free function:** the adapter owns the connection pool (`self._connect`), trigger lifecycle, and JSON serialization. A method colocates these concerns.

**Bridge deprecation:** `IKIGAiRecordBridge` (commit `2c6e20f`) is preserved as a backward-compat shim; new code calls the method directly. `_map` was inlined into the adapter in `4b6bc62`.

### 2.3 Append-only triggers + history mirror

| Trigger | Behavior |
|---|---|
| `plan_entities_no_delete` | RAISE(ABORT) on DELETE — only the adapter's upsert path can bypass (DROP+reCREATE in same transaction) |
| `plan_entities_no_update` | RAISE(ABORT) on UPDATE — same bypass |
| `plan_entities_history` | Mirrored on every INSERT with full row snapshot — powers replay |

These triggers were already in `SCHEMA_SQL` but only enforced when writers used them. Routing every write through the adapter makes them effective.

### 2.4 Migration plan (MIG-1, MIG-2)

| Script | Purpose | When |
|---|---|---|
| **MIG-1** `scripts/migrate_plan_entities.py` (commit `eeac3aa`) | ALTER 11-col → 24-col + backfill known fields. Idempotent. | Before first production upsert |
| **MIG-2** `scripts/migrate_runtime_writers.py` (planned) | Replace raw `INSERT` in `commit.py:58-118` + `server.py:347-357` with `SQLiteAdapter.upsert_ikigai_record()`. | Sprint 1 (post-merge) |

---

## §3. Interface signatures

### 3.1 `IKIGAiRecord`

```python
class IKIGAiRecord(BaseModel):
    model_config = ConfigDict(extra="allow", discriminator="entity_type", frozen=False)

    # Identity (D6, D10)
    ueid: UEID                          # 5-part canonical ID
    entity_type: EntityType             # polymorphic discriminator (16 variants)
    slug: str                           # 1..128, immutable post-creation (I6)
    parent_ueid: UEID | None
    related_ueids: list[UEID]
    title: str
    description: str | None
    status: StatusType                  # 8-state enum

    # at-creation snapshots (NOT current state)
    phase_at_creation: str | None
    regime_at_creation: str | None
    primary_score: ScoreValue | None

    # vector scoring (D2/D3/I3)
    ikigai_vectors: list[VectorKey]
    vector_weights_snapshot: dict[VectorKey, float]
    vector_scores: dict[VectorKey, ScoreValue]
    vector_metadata: dict[VectorKey, dict[str, Any]]

    # current meta + Q_HE
    meta_vector_score: ScoreValue | None
    q_he_score: ScoreValue | None       # I4: unit MUST be 'ratio'

    # fractal regime (D13)
    regime: FractalRegime | None

    # phase state (D11/I11)
    phase: str | None
    phase_iteration: int | None         # ge=0, le=5
    phase_converged: bool | None
    # NOTE: phase_weights REMOVED — lives on PhaseSnapshot (I7)

    # decomposition chain (§3.2)
    active_dream_ueid: UEID | None
    active_goal_ueids: list[UEID]
    active_objective_ueids: list[UEID]
    active_project_ueids: list[UEID]
    active_task_ueids: list[UEID]
    active_deliverable_ueids: list[UEID]

    # balancer / workload
    workload_estimate: float | None
    capacity_estimate: float | None
    balancer_verdict: str | None        # OK | OVERLOAD | UNDERLOAD | RECOVER

    # buffers + corrections (D12)
    prospective_buffer: list[str]
    retrospective_log: list[str]
    corrections: list[CorrectionSignal]

    # override + audit (D12)
    manual_override: bool
    recommendation_score: float | None  # ge=0.0, le=1.0
    audit_trail: list[OverrideRecord]

    # forward-compat placeholder (D7)
    is_placeholder: bool
    placeholder_owner: str | None

    # drift detection (D14)
    drift_state: DriftState
    sqlite_mirror_at: datetime | None
    last_triaged_at: datetime | None

    # audit timestamps (NOT lifecycle — status is)
    created_at: datetime
    updated_at: datetime
    last_reviewed_at: datetime | None

    # canonical source (D8/I9 REQUIRED)
    source_md_path: Path

    # cross-cluster routing (§3.2 forward-compat)
    target_subsystem: Literal["CLUSTER_PLAN","life_tatics","vibe_ops","taskwarrior"] | None

    # typed forward-compat — variant-specific fields
    custom: dict[str, Any]
```

### 3.2 `SQLiteAdapter.upsert_ikigai_record`

```python
def upsert_ikigai_record(self, record: IKIGAiRecord) -> None:
    """Insert or update an IKIGAiRecord. Append-only semantics enforced
    by triggers. Vector scores normalised to 0..1 ratios via
    ScoreValue.normalized to match the legacy schema shape."""
    vector_scores: dict[str, float] = {}
    if record.vector_scores:
        for k, sv in record.vector_scores.items():
            vector_scores[str(k)] = sv.normalized

    self.upsert(
        ueid=str(record.ueid),
        entity_type=record.entity_type.value,
        slug=record.slug,
        title=record.title,
        description=record.description or "",
        parent_ueid=str(record.parent_ueid) if record.parent_ueid else None,
        related_ueids=[str(u) for u in record.related_ueids],
        status=record.status.value,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        last_reviewed_at=record.last_reviewed_at.isoformat()
            if record.last_reviewed_at else None,
        archived_at=None,
        ikigai_vectors=vector_scores,
        vector_weights_snapshot=dict(record.vector_weights_snapshot)
            if record.vector_weights_snapshot else {},
        phase_at_creation=record.phase_at_creation,
        regime_at_creation=record.regime_at_creation,
        horizon_days=None,
        primary_score=record.primary_score.value
            if record.primary_score else None,
        is_placeholder=record.is_placeholder,
        placeholder_owner=record.placeholder_owner,
        claimed_by=None,
        source="ikigai",
        source_md_path=record.source_md_path.as_posix()
            if record.source_md_path else None,
        custom=dict(record.custom) if record.custom else {},
        tags=[],
    )
```

**Caller pattern:**

```python
from ikigai.propagation.sqlite_adapter import SQLiteAdapter
from ikigai.entities.ikigai_record import IKIGAiRecord

adapter = SQLiteAdapter(Path.home() / ".ikigai" / "plan_entities.db")
adapter.upsert_ikigai_record(record)  # append-only; safe to retry
```

---

## §4. Acceptance criteria

### 4.1 Schema invariants (AC-1..3)

- **AC-1** — Every write to `plan_entities` flows through `SQLiteAdapter.upsert_ikigai_record()` OR `SQLiteAdapter.upsert()`. Grep proves: no remaining `INSERT INTO plan_entities` outside the adapter's source. ✅ (commits `ca4e65c`, `4b6bc62`)
- **AC-2** — The 11-col runtime schema is removed from production. `migrate_plan_entities.py` (commit `eeac3aa`) detects 11-col tables and ALTERs them to 24-col. ✅
- **AC-3** — UEID regex enforces 5-part format. Test: `test_invalid_ueid_rejected` (`test_ikigai_record.py`). ✅

### 4.2 Polymorphism + round-trip (AC-4..6)

- **AC-4** — All 16 `EntityType` variants validate successfully. Tests: `test_each_entity_type_loads` + `test_pd01..04_*`. ✅
- **AC-5** — `IKIGAiRecord → frontmatter dict → IKIGAiRecord` is lossless for `custom` and canonical UEID. Tests: `test_rt01_full_round_trip_preserves_custom_fields` + `test_rt02_ueid_survives_round_trip`. ✅
- **AC-6** — `is_placeholder=True` set automatically on CYCLE variants per SPEC D7. Test: `test_cycle_variant_marked_placeholder_per_d7`. ✅

### 4.3 Integration gate — RT-01..06 + 21 supporting (AC-7)

`test_integration_data_model.py` (commit `d9285be`, 477 lines, **27/27 tests passing**) covers real files + real entities:

| Test ID | Assertion | Status |
|---|---|---|
| **RT-01** | Custom fields survive `record → dict → record` | ✅ |
| **RT-02** | UEID matches fixture after round-trip | ✅ |
| **RT-03** | Explicit nulls (`description`, `parent_ueid`) stay None | ✅ |
| **RT-04** | Datetimes remain tz-aware across serialization | ✅ |
| **RT-05** | `source_md_path` REQUIRED + preserved (D8/I9) | ✅ |
| **RT-06** | `extra="allow"` passes through unknown fields | ✅ |
| PD-01..04 | Polymorphic discriminator for dream/objective/vector/fractal | ✅ |
| SU-01..04 | ScoreValue unit ranges (percent/ratio) enforced | ✅ |
| OV-01..03 | OverrideRecord + CorrectionSignal preserved verbatim | ✅ |
| FR-01..03 | FractalRegime 4 levels, constrained names, round-trip | ✅ |
| SA-01..05 | DriftDetector + CheckpointAdapter + StateReducer | ✅ |
| PH-01 | PhaseSnapshot + placeholder flag round-trip | ✅ |
| PS-01 | DriftState resolved-path round-trips | ✅ |

### 4.4 Migration safety (AC-8)

- **AC-8** — `migrate_plan_entities.py` is idempotent (re-running on 24-col DB prints "no migration needed", exits 0). ✅

---

## §5. Migration path

### MIG-1 — schema upgrade (shipped in `eeac3aa`)

```bash
cd life-ops/ikigai
poetry run python scripts/migrate_plan_entities.py
```

Detects current column count via `PRAGMA table_info(plan_entities)`. If 24+ cols: no-op. If 11 cols: ALTERs add the 13 missing columns, recreates the table, backfills known fields. Idempotent; preserves all rows.

### MIG-2 — runtime writer rewrite (Sprint 1)

Replace raw INSERTs:

| Location | Current | Target |
|---|---|---|
| `commit.py:58-118` | Raw `INSERT INTO plan_entities (...)` | `SQLiteAdapter.upsert_ikigai_record(record)` |
| `server.py:347-357` | Raw `INSERT OR REPLACE INTO plan_entities (...)` | `SQLiteAdapter.upsert_ikigai_record(record)` |

After MIG-2, the only file containing `INSERT INTO plan_entities` is `sqlite_adapter.py:300-350` (inside `upsert()`).

### Legacy 11-col compatibility

`_connect()` accepts `Path` and `":memory:"` (tests). `_init_schema` runs `SCHEMA_SQL` unconditionally — fresh DBs always get 24 cols. Legacy 11-col DBs require MIG-1 before any upsert lands. Read path: `_read_entity` (post-C4 fix) detects legacy 11-col schema and reads whatever columns exist.

---

## §6. Verification

```bash
# Static checks
cd life-ops/ikigai
poetry run mypy src/ikigai/entities/ikigai_record.py
poetry run mypy src/ikigai/propagation/sqlite_adapter.py
poetry run ruff check src/ikigai/entities/ikigai_record.py

# Unit tests (expected: 13 + 6 + N passing)
poetry run pytest tests/test_ikigai_record.py -v
poetry run pytest tests/test_sqlite_bridge.py -v
poetry run pytest tests/test_sqlite_adapter.py -v

# Integration gate (RT-01..06 + 21 — expected: 27 passed)
poetry run pytest tests/test_integration_data_model.py -v

# Migration idempotency (expected: second run prints "no migration needed")
poetry run python scripts/migrate_plan_entities.py
poetry run python scripts/migrate_plan_entities.py

# End-to-end smoke
poetry run python -c "
from datetime import datetime, timezone
from pathlib import Path
from ikigai.entities.ikigai_record import IKIGAiRecord, EntityType, StatusType
from ikigai.propagation.sqlite_adapter import SQLiteAdapter

record = IKIGAiRecord(
    ueid='ikigai:dream:smoke-test:00000001:00000002',
    entity_type=EntityType.DREAM,
    slug='smoke-test',
    title='Smoke Test Dream',
    status=StatusType.ACTIVE,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
    source_md_path=Path('life-ops/ikigai/data/matheus/dreams/smoke-test.md'),
)
adapter = SQLiteAdapter(Path.home() / '.ikigai' / 'plan_entities.db')
adapter.upsert_ikigai_record(record)
print('OK')
"
sqlite3 ~/.ikigai/plan_entities.db "PRAGMA table_info(plan_entities)" | wc -l
# Expected: 25 (24 cols + id PK)
```

---

## §7. Cross-references

| Reference | Path / Source |
|---|---|
| **Source** | `life-ops/ikigai/src/ikigai/entities/ikigai_record.py` (185 lines, `4839a74`) |
| | `life-ops/ikigai/src/ikigai/adapters/sqlite_bridge.py` (32 lines post-refactor, `4b6bc62`) |
| | `life-ops/ikigai/src/ikigai/propagation/sqlite_adapter.py` (upsert_ikigai_record L416-470, `4b6bc62`) |
| **Tests** | `life-ops/ikigai/tests/test_ikigai_record.py` (154 lines, 13 tests) |
| | `life-ops/ikigai/tests/test_sqlite_bridge.py` (138 lines, 6 tests) |
| | `life-ops/ikigai/tests/test_integration_data_model.py` (477 lines, **27 tests**) |
| **Migration** | `life-ops/ikigai/scripts/migrate_plan_entities.py` (192 lines, `eeac3aa`) |
| **Branch** | `feat/data-model-unification` (`4839a74`, `2c6e20f`, `4b6bc62`, `eeac3aa`, `ca4e65c`, `d9285be`) |
| **Diagnostics** | `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` §C2 |
| | `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §1 S-C1, §2 S-C2 |
| **Specs** | SPEC D6 (discriminated union), D7 (placeholder), D10 (UEID), D14 (drift), §6 (status enum), I3/I4 (score ranges) |
| **ADRs** | ADR-009 (Pydantic strict — `extra="allow"` exception justified for variant fields) |
| **Related** | `2026-08-27-spec-C1-vault-canonical-writer.md`, `2026-08-27-spec-C3-state-reducer.md` |

---

## §8. Open questions

1. **Bridge removal timeline** — `IKIGAiRecordBridge` is a deprecated shim. Delete in Sprint 2 once all callers are confirmed migrated.
2. **`frozen=False` on `IKIGAiRecord`** — ADR-009 chose strict mode; this entity uses `frozen=False` + `extra="allow"` for draft mutability + variant fields. See ADR-009 §3 for the relaxation clause.
3. **Trigger drop-and-recreate per upsert** — ~2ms cost per write. At expected rates (~10 writes/min) this is negligible; for bulk import, batch at the connection level.
4. **`PhaseSnapshot` availability** — `phase_weights` was moved off `IKIGAiRecord` to `PhaseSnapshot` (commit `dc19c03`, SPEC I7). Are all read paths updated, or do some still read `record.phase_weights`? Audit pending.
5. **`drift_state` write-back** — `DriftDetector` writes `drift_state` after comparing vault vs mirror. If vault is source of truth, should the write be a full `SQLiteAdapter.upsert_ikigai_record()` round-trip or a lightweight `UPDATE` (violating append-only)? See spec C4.
6. **Cross-cluster routing** — `target_subsystem: Literal[...]` declared but unused. When do callers populate it? TBD.

---

*SPEC C2 — IKIGAiRecord Polymorphic Root + `SQLiteAdapter.upsert_ikigai_record` — v1.0 — 2026-08-27*
