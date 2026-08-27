# IKIGAI Data Model Unification — Design Spec

> **Goal:** Replace 4 ad-hoc data surfaces (vault markdown, plan_entities.db, LangGraph checkpoints, in-memory `IKIGAiStateDict`) with **one canonical `IKIGAiRecord`** root class that round-trips losslessly across all surfaces, written first by an agentic writer into the in-repo vault at `data/matheus/`, mirrored to SQLite downstream, and surfaced through a Unified MCP Gateway to three downstream MCP servers (tuiboard, taskdog-mcp, solverforge-calendar).

**Date:** 2026-08-26
**Author:** brainstorm + 3-lens adversarial review (SPEC invariant, entity collision, round-trip drift)
**Status:** §1 schema + §2 architecture + §3 round-trip contracts approved by user

---

## Context

The IKIGAI deep-agent harness currently has **four data surfaces** with no shared schema:

1. **Vault markdown** — `data/matheus/{dreams,objectives,...}/*.md` with hand-built frontmatter; the cycle writer (`src/agents/tools.py:350-385`) emits a hand-rolled f-string that drops the typed `corrections` list (writes `corrections_count: 0`), the `prospective_buffer`, `retrospective_log`, and `audit_trail` — so round-trip through cycle files loses 4 of the record's mutable surfaces.
2. **LangGraph checkpoint SQLite** — `~/.ikigai/ikigai_checkpoints.db` with raw `pickle.loads` bypassing `JsonPlusSerializer` (per findings: `server.py:188-201, 419-421, 430-436`).
3. **`plan_entities.db`** — `~/.ikigai/plan_entities.db`. **Already partially fixed in commits `ca4e65c` + `0ff111d` + `eeac3aa` on `gitbutler/workspace`** — `SQLiteAdapter.upsert()` provides the 24-col schema with append-only triggers + `plan_entities_history` table, and writes from `commit.py` + `server.py` now route through it. **The remaining gap**: `SQLiteAdapter` still consumes the legacy `PlanEntity` (from `ikigai.entities.base`), NOT the new `IKIGAiRecord`. New `IKIGAiRecord` fields absent from the 24-col schema: `vector_scores`, `meta_vector_score`, `q_he_score`, `regime` (FractalRegime), `phase_iteration`, `phase_converged`, `workload_estimate`, `capacity_estimate`, `balancer_verdict`, `prospective_buffer`, `retrospective_log`, `corrections`, `manual_override`, `recommendation_score`, `audit_trail`, `drift_state`, `sqlite_mirror_at`, `last_triaged_at`, `target_subsystem`, `active_*_ueids`. These need to land in the mirror via `custom` JSON blob (since `extra="allow"` per SPEC D6) — see `Open Questions #5`.
4. **In-memory `IKIGAiStateDict`** — TypedDict in `src/agents/ikigai_maintainer/state.py:107-167` with 17 fields that overlap with the proposed schema but use bare `float` instead of `ScoreValue` and `Literal` instead of `Enum`.

A 3-lens adversarial review workflow (`ikigai-record-schema-review`) returned **70 findings**: 22 Critical, 22 Important, 26 Minor — including **11 verbatim SPEC.md lock-in violations** in the original §1 draft. The user chose **Option B — single root, polymorphic** to reconcile the conflict between their "single schema" intent and SPEC D6's locked polymorphic discriminated-union requirement.

---

## §1 — `IKIGAiRecord` schema (single root, polymorphic per SPEC D6)

### Honor roll of locked SPEC decisions

| Decision | What it mandates | Where it shows up in `IKIGAiRecord` |
|---|---|---|
| **D6** | Polymorphic + `extra="allow"` + `frozen=False` | `model_config = ConfigDict(extra="allow", discriminator="entity_type", frozen=False)` |
| **D7** | `is_placeholder` + `placeholder_owner` | Both fields present |
| **D10 / §3.1** | UEID 5-part format `namespace:entity_type:slug:uuid_short:content_hash_short` | `UEID = Annotated[str, StringConstraints(pattern=...)]` |
| **D3 / D13** | Fractal sub-vectors (`skill.python`, `market.freelance`) | `VectorKey` allows fractal strings; `FractalRegime` carries 4 levels |
| **D12** | `manual_override` + `recommendation_score` + typed audit trail | `OverrideRecord` TypedDict, `audit_trail: list[OverrideRecord]` |
| **D13** | Fractal regime: Global → Cluster → Vector → SubVector | `FractalRegime.levels: list[FractalRegimeState]` (exactly 4) |
| **I3** | Vector scores ∈ [0, 100] | `ScoreValue.unit="percent"` carries the constraint |
| **I4** | Q_HE ∈ [0, 1] | `ScoreValue.unit="ratio"` carries the constraint |
| **I5** | Status transitions via StateMachine | Documented; direct assignment discouraged; enforced at `state_machines/` layer |
| **I6** | Slug immutable post-creation | Per-field `model_validator` on slug + DB trigger (NOT global frozen) |
| **I7** | Phase weights in separate table | `phase_weights` REMOVED from record; `PhaseSnapshot` entity |
| **I8** | Score unit consistency | Closed `ScoreUnit` Literal + per-unit validator |
| **I10** | Hysteresis respected | `hysteresis_days` lives on `FractalRegimeState` per-level + PAV_NS constants |
| **I11 / D11** | `phase_iteration ∈ [0, 5]` | `Field(ge=0, le=5)` |
| **D2** | Course vector `is_external=True` | `vector_metadata[VectorKey, dict]` carries per-vector metadata |
| **D8 / I9** | Markdown = canonical | `source_md_path: Path` REQUIRED (not Optional) |
| **D14 / §8.2** | Drift detection + triagem.md | `drift_state`, `sqlite_mirror_at`, `last_triaged_at` |

### The root class

```python
"""IKIGAiRecord — canonical single root, polymorphic per SPEC D6."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# ──────── Primitive value types ────────

UEID = Annotated[
    str,
    StringConstraints(
        pattern=r"^(ikigai|tw|obsidian|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}$",
    ),
]

VectorKey = Annotated[str, StringConstraints(min_length=1, max_length=128)]

class ScoreUnit(str, Enum):
    PERCENT = "percent"   # I3: vector scores ∈ [0, 100]
    RATIO = "ratio"       # I4: Q_HE ∈ [0, 1]

class ScoreValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    value: float
    unit: ScoreUnit

    @property
    def normalized(self) -> float:
        return self.value / 100.0 if self.unit == ScoreUnit.PERCENT else self.value

# ──────── Discriminators (polymorphism per D6) ────────

class EntityType(str, Enum):
    DREAM = "dream"
    GOAL = "goal"
    OBJECTIVE = "objective"
    PROJECT = "project"
    TASK = "task"
    DELIVERABLE = "deliverable"
    ROUTINE = "routine"
    TIME_BLOCK = "time_block"
    RITUAL = "ritual"
    HABIT = "habit"
    VECTOR = "vector"
    PROFILE = "profile"
    SKILL_NODE = "skill_node"
    OPPORTUNITY = "opportunity"
    REGIME = "regime"
    CYCLE = "cycle"     # derived log entry, is_placeholder=True

class StatusType(str, Enum):  # §6 — 8 explicit state machines
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ABANDONED = "abandoned"
    FALSIFIED = "falsified"
    PIVOTED = "pivot"

# ──────── Fractal structures (D3, D13) ────────

class FractalRegimeState(BaseModel):
    """D13: per-level regime state with its own hysteresis window."""
    model_config = ConfigDict(extra="forbid")
    level: Literal["global", "cluster", "vector", "sub_vector"]
    regime: str  # push | maintain | reduce | recover
    days_in_regime: int = Field(ge=0)
    is_hysteresis_active: bool
    hysteresis_days: int = Field(ge=0)  # per §8.3

class FractalRegime(BaseModel):
    """D13: 4-level fractal regime — Global → Cluster → Vector → SubVector."""
    model_config = ConfigDict(extra="forbid")
    levels: list[FractalRegimeState]  # exactly 4 entries

# ──────── Override + audit (D12) ────────

class OverrideRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at: datetime
    by: str                          # agent | human:<name>
    field_path: str                  # dotted path
    previous_value: Any
    new_value: Any
    reason: str

class CorrectionSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heuristic: str
    signal_type: Literal[
        "drift", "overload", "underload", "recover", "kill",
        "abandon", "pivot", "falsify",
    ]
    description: str
    target_ueid: Optional[UEID]
    urgency: Literal["low", "medium", "high", "critical"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

# ──────── Drift detection (§8.2, D14) ────────

class DriftState(str, Enum):
    IN_SYNC = "in_sync"
    MARKDOWN_NEWER = "markdown_newer"
    SQLITE_NEWER = "sqlite_newer"
    CONFLICT = "conflict"

# ──────── THE ROOT ────────

class IKIGAiRecord(BaseModel):
    """Canonical IKIGAi state — single root, polymorphic per SPEC D6."""
    model_config = ConfigDict(
        extra="allow",
        discriminator="entity_type",
        frozen=False,
    )

    # Identity (D6, D10, §3.1, §3.2)
    ueid: UEID
    entity_type: EntityType
    slug: str = Field(min_length=1, max_length=128)
    parent_ueid: Optional[UEID] = None
    related_ueids: list[UEID] = Field(default_factory=list)
    title: str
    description: Optional[str] = None
    status: StatusType = StatusType.DRAFT

    # §3.2 at-creation snapshots (NOT current)
    phase_at_creation: Optional[str] = None
    regime_at_creation: Optional[str] = None
    primary_score: Optional[ScoreValue] = None

    # Vector scoring (D2, D3, I3)
    ikigai_vectors: list[VectorKey] = Field(default_factory=list)
    vector_weights_snapshot: dict[VectorKey, float] = Field(default_factory=dict)
    vector_scores: dict[VectorKey, ScoreValue] = Field(default_factory=dict)
    vector_metadata: dict[VectorKey, dict[str, Any]] = Field(default_factory=dict)

    # Current meta-vector + Q_HE
    meta_vector_score: Optional[ScoreValue] = None
    q_he_score: Optional[ScoreValue] = None         # I4: unit MUST be 'ratio'

    # Fractal regime (D13) — replaces single regime_state field
    regime: Optional[FractalRegime] = None

    # Phase state (D11, I11, §3.2)
    phase: Optional[str] = None
    phase_iteration: Optional[int] = Field(default=None, ge=0, le=5)
    phase_converged: Optional[bool] = None
    # phase_weights REMOVED — lives on separate PhaseSnapshot (I7)

    # Decomposition chain (§3.2)
    active_dream_ueid: Optional[UEID] = None
    active_goal_ueids: list[UEID] = Field(default_factory=list)
    active_objective_ueids: list[UEID] = Field(default_factory=list)
    active_project_ueids: list[UEID] = Field(default_factory=list)
    active_task_ueids: list[UEID] = Field(default_factory=list)
    active_deliverable_ueids: list[UEID] = Field(default_factory=list)

    # Balancer / workload (IKIGAiStateDict-shaped)
    workload_estimate: Optional[float] = None
    capacity_estimate: Optional[float] = None
    balancer_verdict: Optional[str] = None       # OK | OVERLOAD | UNDERLOAD | RECOVER

    # Buffers + corrections (D12, typed)
    prospective_buffer: list[str] = Field(default_factory=list)
    retrospective_log: list[str] = Field(default_factory=list)
    corrections: list[CorrectionSignal] = Field(default_factory=list)

    # Override + audit (D12)
    manual_override: bool = False
    recommendation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    audit_trail: list[OverrideRecord] = Field(default_factory=list)

    # Forward-compat placeholder (D7)
    is_placeholder: bool = False
    placeholder_owner: Optional[str] = None

    # Drift detection (§8.2, D14, D8/I9)
    drift_state: DriftState = DriftState.IN_SYNC
    sqlite_mirror_at: Optional[datetime] = None
    last_triaged_at: Optional[datetime] = None

    # Audit timestamps (NOT lifecycle; lifecycle lives on StatusType)
    created_at: datetime
    updated_at: datetime
    last_reviewed_at: Optional[datetime] = None

    # Canonical source (D8/I9: REQUIRED)
    source_md_path: Path

    # Cross-cluster routing (§3.2 forward-compat)
    target_subsystem: Optional[Literal[
        "CLUSTER_PLAN", "life_tatics", "vibe_ops", "taskwarrior",
    ]] = None

    # Typed forward-compat (entity-specific fields live here)
    custom: dict[str, Any] = Field(default_factory=dict)
```

### What lives OUTSIDE `IKIGAiRecord`

| Entity | Reason | Own UEID format |
|---|---|---|
| **`PhaseSnapshot`** (I7) | Frozen phase weights — historical, append-only | `ikigai:phase_snapshot:{cycle_id}:{iter}:{hash}` |
| **`TimeSlice`** | Time-bucket queries over the union | query layer, no stored rows |
| **`StateMachine` config** (I10) | `hysteresis_days` live in PAV_NS constants | not an entity |
| Subtype models (§3.2) | `DreamEntity.motivation`, `GoalEntity.success_metrics`, `ObjectiveEntity.key_results`, `ProjectEntity.tech_stack`, `TaskEntity.{priority, assignee}`, `DeliverableEntity.artifact_path` — all live in `custom` / `extra="allow"` | inherits `ueid` |

---

## §2 — Architecture: Unified MCP Gateway + agentic-writer-first

### Layer 1 — Canonical vault (in-repo, agentic-writer-first)

- **Sole writer**: `IKIGAiAgenticWriter` — a tool exposed to the LangChain Deep Agent.
- **Path**: `data/matheus/{dreams,goals,objectives,projects,cycles,deliverables,ikigai_state,...}/*.md` (project-root relative; absolute path on the user's host is `life-ops/ikigai/data/matheus/...` per the user's `data first comes from vault in @life-ops\ikigai\data\matheus`)
- **Serializer**: rebuilt `dict_to_frontmatter(IKIGAiRecord.model_dump())` — NOT the lossy f-string writer at `tools.py:359-388`.
- **Deserializer**: rebuilt `frontmatter_to_dict` — preserves `null` keys, datetime tz, dict key types.
- **Concurrency**: file-level lock (`fcntl`/`msvcrt`); markdown writes serialize.

### Layer 2 — Mirror (SQLite, derived)

| Store | Path | Adapter | Status |
|---|---|---|---|
| Polimorphic mirror | `~/.ikigai/plan_entities.db` | `SQLiteAdapter` (existing in `src/ikigai/propagation/sqlite_adapter.py`) — keyed by `ueid`; 24-col schema + append-only triggers + `plan_entities_history` | **EXISTING** — currently consumes `PlanEntity`; must be extended to consume `IKIGAiRecord` (see Open Questions #5) |
| LangGraph checkpoints | `~/.ikigai/ikigai_checkpoints.db` | `CheckpointAdapter` — wraps LangGraph `JsonPlusSerializer` (NO raw pickle) | NEW (replaces existing raw-pickle path at `server.py:188-201, 419-421, 430-436`) |
| Ephemeral state | in-memory `IKIGAiStateDict` | `StateReducer` — dumps to `IKIGAiRecord` + vault at cycle commit | NEW (additive on existing TypedDict) |

**Invariant**: markdown wins on drift (§8.2). Drift = `markdown_mtime != sqlite_mtime > 5min` → write `triagem.md` (D14).

### Layer 3 — Unified MCP Gateway

```
LangChain Deep Agent ──HTTP+SSE──► Unified MCP Gateway ──┐
Claude Code CLI       ──stdio────►                       │
                                                          ▼
                                          ┌──────────────────────────┐
                                          │  IKIGAiRecord validation │
                                          │  at every request/resp   │
                                          └──────────────────────────┘
                                                          │
                          ┌───────────────────────────────┼──────────────────────────────┐
                          ▼                               ▼                              ▼
                  tuiboard MCP                     taskdog-mcp MCP             solverforge-calendar MCP
                  (kanban, stdio↔HTTP)            (Taskwarrior wrap, stdio↔HTTP)   (time-block planner, stdio↔HTTP)
```

- **HTTP+SSE** for the agent side; **stdio↔HTTP** for the three downstream MCP servers.
- **Gateway responsibilities**: auth + transport, schema validation (`IKIGAiRecord.model_validate()` at the boundary), cross-server transactions, observability (`@observed_tool` on every handler — already wired from prior observability work).

### Layer 4 — CLI/Widget object models (derived, read-only)

- CLIs and TUI widgets read from downstream MCP servers or from the mirror SQLite.
- **They never write to the canonical store directly.** Gateway rebuilds widget-friendly projections on each refresh (`KanbanColumn` from `active_project_ueids`, `WeekGrid` from solverforge calendar).
- Per data-first methodology (ADR-007 Option C, 2026-07-03): algorithmic fields (`corrections`/`balancer_verdict`/`workload_estimate`) stay `None` until an actual agent cycle produces them. No synthetic population.

### Write-path flow

```
1. LangChain Deep Agent decides to mutate → calls ikigai.<tool> via MCP
2. Unified MCP Gateway validates request as IKIGAiRecord (Pydantic, extra='allow')
3. Gateway acquires vault file lock
4. Agentic writer: dict_to_frontmatter(record) → write markdown
5. Mirror writer: plan_entities.db UPSERT keyed by ueid (after markdown commit)
6. LangGraph commit: JsonPlusSerializer.dumps(record) → checkpoints.db
7. Cross-server fan-out: tuiboard/taskdog/solverforge receive update notifications
8. Lock released; gateway returns IKIGAiRecord to agent
```

### Read-path flow

```
1. Agent/Gateway/CLI issues GET /entity/<ueid>
2. Gateway reads vault markdown FIRST (canonical)
3. Markdown present → IKIGAiRecord.model_validate(frontmatter_dict)
4. Markdown absent → fall back to plan_entities.db mirror
5. Mirror absent → reconstruct from IKIGAiStateDict at last commit
6. Surface any drift via DriftState field (NOT silent fallback)
```

---

## §3 — Round-trip contract tests (the data-first load-bearing invariant)

§1 + §2 are worthless if `writer(record) → read() → record'` doesn't round-trip. These 23 tests are the **contract** that gates "§1 complete". Fixtures are the existing vault files in `data/matheus/`.

### §3.1 — Vault markdown round-trip

| ID | Test | Fixture | Asserts |
|---|---|---|---|
| RT-01 | `test_round_trip_dream_entity` | `data/matheus/dreams/vaga-remota-2026.md` | All 30+ fields preserved, including `custom.verticals`, `custom.non_negotiables`, `vector_weights_snapshot` |
| RT-02 | `test_round_trip_objective_with_key_results` | `data/matheus/objectives/q3-2026-primeira-vaga.md` | `key_results: list[str]`, `progress_pct: float` preserved |
| RT-03 | `test_null_fields_survive_round_trip` | `vaga-remota-2026.md` line 8 `description: null` | `description=None` preserved; NOT dropped by serializer filter |
| RT-04 | `test_datetime_tz_aware_round_trip` | `vaga-remota-2026.md` line 18 `2026-07-03T00:00:00Z` | Re-parsed `datetime` carries tzinfo |
| RT-05 | `test_cycle_writer_emits_all_ikigai_record_fields` | `data/matheus/ikigai_state/cycle-2026-08-26.md` | Cycle log preserves `corrections` (full list), `prospective_buffer`, `retrospective_log`, `audit_trail` |
| RT-06 | `test_extra_allow_field_pass_through` | inject `custom_field: foo` | Unknown keys survive; current `extra="forbid"` schema rejects |

### §3.2 — Polymorphic discriminator

| ID | Test | Asserts |
|---|---|---|
| PD-01 | `test_discriminator_dream_loads_as_dream` | `entity_type=dream` + `extra={"motivation": ...}` loads; missing `motivation` OK with empty `extra` |
| PD-02 | `test_discriminator_goal_loads_as_goal` | `entity_type=goal` + `extra={"success_metrics": [...]}` round-trip |
| PD-03 | `test_discriminator_unknown_type_rejected` | `entity_type=cycle` → loaded with `is_placeholder=True` per D7 |
| PD-04 | `test_fractal_vector_keys_round_trip` | `vector_scores={"skill": ..., "skill.python": ...}` round-trips both keys |

### §3.3 — Score unit + range (I3, I4, I8)

| ID | Test | Asserts |
|---|---|---|
| SU-01 | `test_vector_score_in_range` | `ScoreValue(85, "percent")` valid; `150` raises |
| SU-02 | `test_q_he_score_unit_must_be_ratio` | `ScoreValue(0.85, "ratio")` valid; `unit="percent"` rejected for Q_HE |
| SU-03 | `test_meta_vector_computation_rejects_mixed_units` | `compute_meta_vector(scores)` raises if any input has unit ≠ "percent" |
| SU-04 | `test_normalized_property_unit_agnostic` | `ScoreValue(85, "percent").normalized == ScoreValue(0.85, "ratio").normalized == 0.85` |

### §3.4 — Override + audit (D12)

| ID | Test | Asserts |
|---|---|---|
| OV-01 | `test_manual_override_field_present` | `manual_override=True` persists; agent writes typed `OverrideRecord` to `audit_trail` |
| OV-02 | `test_recommendation_score_in_unit_interval` | `recommendation_score=0.5` valid; `1.5` rejected |
| OV-03 | `test_audit_trail_typed_not_free_form` | `audit_trail: list[OverrideRecord]` rejects raw strings |

### §3.5 — Fractal regime (D13)

| ID | Test | Asserts |
|---|---|---|
| FR-01 | `test_fractal_regime_has_four_levels` | `FractalRegime.levels` requires exactly 4 entries |
| FR-02 | `test_per_level_hysteresis_days` | Each `FractalRegimeState` carries its own `hysteresis_days` per §8.3 |
| FR-03 | `test_regime_state_field_replaces_single_regime_field` | No flat `regime_state: RegimeType`; reads go through `regime.levels[0].regime` |

### §3.6 — Surface adapters

| ID | Test | Asserts |
|---|---|---|
| SA-01 | `test_vault_canonical_overrides_mirror` | Vault modified, mirror stale → read returns vault; `drift_state=MARKDOWN_NEWER` |
| SA-02 | `test_sqlite_adapter_consumes_ikigai_record` | `SQLiteAdapter.upsert(IKIGAiRecord(...))` writes one row keyed by `ueid`; 24-col schema fields populated from the record; remaining `IKIGAiRecord` fields land in `custom` JSON blob (lossless round-trip via `model_validate(custom_json)`); append-only trigger still fires on UPDATE |
| SA-03 | `test_checkpoint_uses_json_plus_serializer` | `JsonPlusSerializer.dumps(record.model_dump())` round-trips through `checkpoints.db`; raw pickle removed |
| SA-04 | `test_state_dict_normalizes_to_record_at_commit` | `IKIGAiStateDict` → at cycle commit, dumped to `IKIGAiRecord` + vault |
| SA-05 | `test_drift_detection_writes_triagem_md` | `markdown_mtime - sqlite_mirror_at > 5min` → writes `triagem.md` entry |

### §3.7 — Placeholder + phase-snapshot (D7, I7)

| ID | Test | Asserts |
|---|---|---|
| PH-01 | `test_is_placeholder_round_trips` | `is_placeholder=True, placeholder_owner="matheus"` persists |
| PS-01 | `test_phase_weights_lives_on_phase_snapshot_not_record` | `record.phase_weights` raises AttributeError; `PhaseSnapshot` entity holds them |

**§1 complete** = all 23 tests pass on existing vault fixtures without test-time mutation.

---

## Global Constraints (load-bearing invariants the implementation MUST honor)

| Rule | Source | What it forbids |
|------|--------|-----------------|
| **Standalone** | `life/CLAUDE.md` §Global Conventions | `life-ops/operational/` imports from root `life/` or `vibe-ops/` |
| **Pydantic v2 strict** | `life/CLAUDE.md` §Global Conventions | `extra="forbid"`, `frozen=True` on canonical schemas — `IKIGAiRecord` deviates by SPEC D6 mandate (`extra="allow"`, `frozen=False`) |
| **Append-only** | SPEC I1 | DB-level triggers prevent UPDATE/DELETE on plan tables |
| **Fully local** | `life/CLAUDE.md` §Global Conventions | Cloud deps, API keys — except opt-in observability (already shipped) |
| **PT-BR ↔ EN split** | `life/CLAUDE.md` §Global Conventions | Strategic prose in Portuguese; code, file names, AI specs in English |
| **No new code without empirical logs** | ADR-007 data-first methodology (2026-07-03) | Algorithmic fields (`corrections`/`balancer_verdict`/`workload_estimate`) stay `None` until cycles produce them |
| **`--json` everywhere** | `life/CLAUDE.md` §Global Conventions | Any new CLI without machine-readable output |
| **Idempotent pipelines** | SPEC I1 | Non-deterministic writes; UEID-keyed writes only |

---

## Out of Scope

- Replacing `IKIGAiStateDict` TypedDict during a cycle's in-flight supersteps (kept for reducer perf; only normalized to record at commit).
- Migrating existing vault files in `data/matheus/` (they ARE the fixtures — see RT-01..06). **Note**: `cycle-2026-08-26.md` currently writes only `corrections_count: 0`; RT-05 mandates the rebuild produces `corrections: []` (typed list) for full round-trip — the cycle file is migrated as part of implementing RT-05, not as a separate task.
- New state-machine implementations (we wire status transitions through the existing 8 state machines at `src/ikigai/state_machines/`).
- LangSmith/Langfuse observability changes (already shipped in prior work).
- Migration of `plan_entities.db` historical rows (drift detection handles them — `DriftState.MARKDOWN_NEWER` until they're reconciled).
- Sub-vector score aggregation (D3 fractal math) — that's a separate spec.

---

## Open Questions (decide before / during implementation)

1. **Vault lock granularity** — file-level vs directory-level. File-level is simpler but means concurrent cycles on different dreams can't write simultaneously. Recommend file-level + cycle batching.
2. **`source_md_path` for derived entities** — cycle logs have `is_placeholder=True`, but where does their `source_md_path` point? Recommend: `data/matheus/ikigai_state/cycle-{cycle_id}.md` with `is_placeholder=True` so the schema invariant still holds.
3. **Cross-cluster routing** — `target_subsystem` is `Optional`. Should we require it for `ROUTINE`/`HABIT` entities? Recommend: not for v1; the field is forward-compat.
4. **`recommendation_score` provenance** — who populates it (agent, human, both)? Recommend: agent only; humans override via `manual_override=True` + `OverrideRecord` to `audit_trail`.
5. **`SQLiteAdapter` migration to `IKIGAiRecord`** (NEW — surfaced after spec approval) — existing `SQLiteAdapter` consumes `PlanEntity` from `ikigai.entities.base` (commit `ca4e65c`). `IKIGAiRecord` adds 19+ fields absent from the 24-col schema. Three options:
   - **(A) Extend `PlanEntity` to absorb all `IKIGAiRecord` fields** — smallest diff, but conflates two type hierarchies. Rejected per SPEC D6 polymorphic requirement.
   - **(B) Make `IKIGAiRecord` a strict superset** — `SQLiteAdapter.upsert()` accepts `IKIGAiRecord`; 24-col fields mapped directly; `custom` JSON blob carries the rest. Round-trip via `model_validate({**db_row, **json.loads(custom_blob)})`. **RECOMMENDED** — preserves existing triggers, additive change to adapter.
   - **(C) Migrate SQLite schema to N>24 columns** — requires trigger re-creation + on-disk migration. Defer until v2.
   
   Plan executes (B): `SQLiteAdapter.upsert()` is extended to accept `IKIGAiRecord`; 24-col INSERT statement unchanged; `custom` column absorbs the ~19 additional fields as JSON. Test SA-02 asserts round-trip through `model_validate`.

## Shipped Before Spec Approval (must not duplicate)

The following commits already exist on `gitbutler/workspace` (the spec was written before they landed). Tasks that touch them must treat them as EXISTING-and-must-extend, NOT as CREATE:

| Commit | What it ships | Plan implication |
|---|---|---|
| `ca4e65c` | `SQLiteAdapter.upsert()` + 24-col schema + append-only triggers + `plan_entities_history` | SA-02 tests against this; do NOT recreate the adapter |
| `0ff111d` | `commit.py` + `server.py` route plan entity writes through `SQLiteAdapter` | Task only needs to extend the call site to pass `IKIGAiRecord` instead of `PlanEntity`; do NOT re-route from raw INSERTs |
| `eeac3aa` | `scripts/migrate_plan_entities.py` for legacy 11-col DBs | Tests that exercise legacy migration must call this script, NOT a new one |

---

## Risks

- **Vault frontmatter YAML style drift** — current files use inline flow mappings; the rebuilt serializer must match. Risk: cosmetic diffs on first write. Mitigation: SA-01 + RT-01..06 validate byte-level preservation.
- **`pickle.loads` removal breaks checkpoints.db reads** — any historical checkpoint row written via raw pickle will fail to decode through `JsonPlusSerializer`. Risk: data loss for in-flight cycles. Mitigation: detect format on read, gracefully fall back to pickle with a deprecation warning.
- **3 downstream MCP server contract churn** — tuiboard / taskdog-mcp / solverforge-calendar have their own version cycles. Risk: gateway must translate between record versions. Mitigation: gateway keeps a versioned adapter per server; breaks surface loudly at the boundary.

---

## Files Created / Modified

| File | Action | Notes |
|---|---|---|
| `life-ops/ikigai/src/ikigai/entities/ikigai_record.py` | CREATE | Root class (§1) — `IKIGAiRecord`, `EntityType`, `StatusType`, `FractalRegime`, `FractalRegimeState`, `OverrideRecord`, `CorrectionSignal`, `DriftState`, `ScoreUnit`, `ScoreValue`, `UEID`, `VectorKey` |
| `life-ops/ikigai/src/ikigai/entities/phase_snapshot.py` | CREATE | Separate entity (I7) — frozen phase weights live here |
| `life-ops/ikigai/src/ikigai/vault/dict_to_frontmatter.py` | CREATE | Rebuilt serializer — replaces f-string writer at `tools.py:350-385` |
| `life-ops/ikigai/src/ikigai/vault/frontmatter_to_dict.py` | CREATE | Rebuilt deserializer |
| `life-ops/ikigai/src/ikigai/vault/lock.py` | CREATE | File-level `fcntl`/`msvcrt` lock helper |
| `life-ops/ikigai/src/ikigai/adapters/checkpoint_adapter.py` | CREATE | JsonPlusSerializer wrapper — replaces raw `pickle.loads` at `server.py:188-201, 419-421, 430-436` |
| `life-ops/ikigai/src/ikigai/stateReducer.py` | CREATE | Normalizes `IKIGAiStateDict` → `IKIGAiRecord` at cycle commit |
| `life-ops/ikigai/src/ikigai/mcp_gateway/server.py` | CREATE | Unified MCP Gateway |
| `life-ops/ikigai/src/ikigai/mcp_gateway/clients/{tuiboard,taskdog,solverforge}.py` | CREATE | 3 downstream client adapters (stdio↔HTTP) |
| `life-ops/ikigai/tests/unit/ikigai_record/test_round_trip.py` | CREATE | RT-01..06 |
| `life-ops/ikigai/tests/unit/ikigai_record/test_discriminator.py` | CREATE | PD-01..04 |
| `life-ops/ikigai/tests/unit/ikigai_record/test_score_value.py` | CREATE | SU-01..04 |
| `life-ops/ikigai/tests/unit/ikigai_record/test_override.py` | CREATE | OV-01..03 |
| `life-ops/ikigai/tests/unit/ikigai_record/test_fractal_regime.py` | CREATE | FR-01..03 |
| `life-ops/ikigai/tests/unit/ikigai_record/test_placeholder.py` | CREATE | PH-01, PS-01 |
| `life-ops/ikigai/tests/unit/adapters/test_sqlite_adapter_ikigai_record.py` | CREATE | SA-02 (extends existing SQLiteAdapter, see Open Question #5/B) |
| `life-ops/ikigai/tests/unit/adapters/test_checkpoint_adapter.py` | CREATE | SA-03 |
| `life-ops/ikigai/tests/unit/adapters/test_state_dict_reducer.py` | CREATE | SA-04 |
| `life-ops/ikigai/tests/unit/adapters/test_drift_detection.py` | CREATE | SA-01, SA-05 |
| `life-ops/ikigai/tests/unit/vault/test_dict_to_frontmatter.py` | CREATE | Dict → YAML round-trip unit tests |
| `life-ops/ikigai/tests/unit/vault/test_frontmatter_to_dict.py` | CREATE | YAML → dict round-trip unit tests |
| **EXISTING — DO NOT RECREATE** | | |
| `life-ops/ikigai/src/ikigai/propagation/sqlite_adapter.py` | EXISTING + MODIFY | `SQLiteAdapter.upsert()` already exists (commit `ca4e65c`). Task extends it to accept `IKIGAiRecord`; 24-col INSERT unchanged; `custom` column absorbs remaining fields as JSON |
| `life-ops/ikigai/scripts/migrate_plan_entities.py` | EXISTING | Legacy 11-col → 24-col DB migration (commit `eeac3aa`). Tests must call this script |
| `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/commit.py` | EXISTING + MODIFY | Already routes through `SQLiteAdapter` (commit `0ff111d`). Task only updates the call site to pass `IKIGAiRecord` |
| `life-ops/ikigai/src/mcp_server/server.py` | EXISTING + MODIFY | Already routes through `SQLiteAdapter` (commit `0ff111d`). Task replaces raw-pickle path at L188-201, L419-421, L430-436 with `CheckpointAdapter` |
| `life-ops/ikigai/src/agents/tools.py` | MODIFY | Replace f-string cycle writer at L350-385 with `IKIGAiAgenticWriter` (new function in `src/ikigai/vault/`) |
| `life-ops/ikigai/src/agents/deepagents_harness.py` | MODIFY | Wire Unified MCP Gateway as the agent's MCP surface |

---

*Spec complete. Ready for `superpowers:writing-plans` to generate the implementation plan.*
