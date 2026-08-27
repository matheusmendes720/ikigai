# SPEC C3 — StateReducer: `IKIGAiStateDict` → `IKIGAiRecord`

> **Status**: 🟢 **Draft** — implementation shipped (commit `770881e`); SA-05
> integration test pending merge
> **Date**: 2026-08-27
> **Author**: Architecture (sub-agent, session 44aa707a)
> **Branch**: `feat/data-model-unification`
> **Source**: `life-ops/ikigai/src/ikigai/adapters/state_reducer.py` (130 lines)
> **Tests**: `life-ops/ikigai/tests/test_state_reducer.py` (108 lines, 8 tests)
> **Severity target**: 🟠 High — closes the LangGraph → SQLite bridge that
> keeps the 11-col writer drift alive

---

## §0. Purpose

`StateReducer` is **Layer 2 of the unified data model** (§2 of
`feat/data-model-unification`): the single, pure bridge that collapses
the **ephemeral LangGraph state** held inside the IKIGAi-Maintainer
graph into the **canonical, persistent `IKIGAiRecord`** polymorphic root.

The maintainer graph uses a `TypedDict` (`IKIGAiStateDict`) optimized
for in-memory mutation, list-append accumulators (`operator.add`), and
LangGraph reducer semantics — none of which round-trip through Pydantic,
SQLite, or vault markdown without an explicit translation step. **Three
properties this spec enforces:**

1. **Pure function** — `reduce()` is stateless; same input dict produces
   the same `IKIGAiRecord`. No filesystem, no logger side-effects.
2. **Score unit coherence** — every numeric score is wrapped in a
   `ScoreValue` with the correct `ScoreUnit` (RATIO for `q_he_score`,
   PERCENT for `vector_scores`) so downstream consumers never see a
   bare `float`.
3. **Lossless typed reduction** — the 17 typed `IKIGAiStateDict` fields
   plus the three accumulator channels map 1-to-1 onto `IKIGAiRecord`
   fields, with no silent drops.

This is the load-bearing adapter that lets the LangGraph runtime talk to
the SQLite mirror (spec C2) and the vault canonical writer (spec C1)
without either side knowing about the other's data model.

---

## §1. Problem

### 1.1 IKIGAiStateDict is TypedDict, not Pydantic

`src/agents/ikigai_maintainer/state.py:107-168` defines the canonical
state shape for every node in the IKIGAi-Maintainer LangGraph. Its 17
typed fields plus three annotated accumulators carry three structural
defects: bare floats (no range validation), unvalidated `Literal`s
(typos pass unchecked), and `total=False` (partial state may `KeyError`
mid-graph). Five key fields:

| Field | State type | Issue |
|-------|-----------|-------|
| `q_he_score: float` | bare float ∈ [0,1] | No range validation; drift detector compares apples to oranges |
| `vector_scores: dict[str, float]` | bare dict of ratios | Scores silently mix units (ratio vs percent) in same dict |
| `regime_state: Literal[...]` | unvalidated Literal | `"push"` or `"PUSHED"` passes unchecked; regime classifies wrongly |
| `balancer_verdict: Literal[...]` | unvalidated Literal | Typo silently corrupts the channel; commit edge guard runs on garbage |
| `phase_weights: dict[str, float]` | lives here | Removed from `IKIGAiRecord` (SPEC I7) — permanent divergence |

### 1.2 The drift lives here

The 11-col runtime writer in `commit.py:58-118` reads from a *different*
shape (`PlanEntity` dataclass) that has never agreed with either
`IKIGAiStateDict` or `IKIGAiRecord`. The StateReducer is the only place
where these three shapes can be unified — without it, every cycle emits
one more row of drift, `SQLiteAdapter.upsert_ikigai_record()` (spec C2)
has nothing to consume, the drift detector cannot compute vector deltas,
and vault markdown for cycles is written by hand via f-strings (spec C1)
that propagate every silent drop in §1.1 to disk.

---

## §2. Design

### 2.1 Layer 2 of the unified data model

```
┌────────────────────────────────────────────────────────────────┐
│ Layer 1 — Canonical root    IKIGAiRecord  (Pydantic, D6)       │
│                              ▲                                 │
│ Layer 2 — Bridge adapter    StateReducer.reduce(state, path)   │
│                              ▲                                 │
│ Layer 3 — LangGraph state   IKIGAiStateDict (TypedDict)        │
└────────────────────────────────────────────────────────────────┘
```

The reducer is **the only Layer 3 → Layer 1 path**. Other adapters
(vault serializer, JsonPlusSerializer checkpoint) consume
`IKIGAiRecord`, not `IKIGAiStateDict`. This prevents layer-skipping
bypasses.

### 2.2 ScoreValue coercion (the load-bearing decision)

The state dict stores `q_he_score`, `meta_vector_score`, and
`vector_scores` as raw ratios (0..1). The canonical root expects:
`q_he_score` and `meta_vector_score` as `ScoreValue(unit=RATIO)`;
`vector_scores` as `dict[VectorKey, ScoreValue(unit=PERCENT)]` per SPEC
I3. **The unit divergence is intentional** — state computation stays in
ratio space (so `compute_meta_vector` does not need to know about
percent), but `IKIGAiRecord` storage uses PERCENT for vectors and RATIO
for Q_HE so the discriminator survives `SQLiteAdapter.upsert_ikigai_record`
serialization. Coercion rule (`_map_vector_scores`):

```python
{k: ScoreValue(value=float(v) * 100.0, unit=ScoreUnit.PERCENT) for k, v in scores.items()}
```

This is the only place in the system where `ratio → percent` scaling
lives. The reverse (`normalized` property on `ScoreValue`) is the single
source for ratio reads downstream.

### 2.3 Regime → FractalRegime lifting

`IKIGAiStateDict.regime_state` is a single `Literal` (one value for the
whole graph). `IKIGAiRecord.regime` is a 4-level `FractalRegime` per
SPEC D13 (global → cluster → vector → sub_vector). `_map_regime` lifts
the single state value to the global level and **fills the lower three
with `MAINTAIN` placeholders** — deliberately lossy at lower levels
because the in-memory state has no knowledge of cluster / vector /
sub-vector regime. Placeholder levels carry `days_in_regime=0` and
`is_hysteresis_active=False` so a future heuristic cannot mistake them
for real signal. The 4-level invariant (D13, FR-01) is preserved because
we never collapse below 4 entries.

### 2.4 Placeholder + decoupling

CYCLE is a **derived log entry** — emitted by the graph at cycle-end,
not authored in the vault by hand. SPEC D7 mandates
`is_placeholder=True, placeholder_owner="ikigai-agent"`, signalling to
`DriftDetector` and `IKIGAiAgenticWriter` (spec C1) that the cycle row
is a mirror artifact, not a primary authored entity. The CYCLE `ueid`
is the LangGraph `cycle_id` (5-part format) — no synthesis, no remap.
The reducer does not validate Literal membership at reduction time
(trusts the upstream node); validation happens later in
`FractalRegimeState.regime`, the drift detector, or a future heuristic.
This keeps the reducer decoupled from the operational core's enum
definitions (see `_map_balancer_verdict` pass-through).

---

## §3. Interface signatures

### 3.1 `StateReducer.reduce(state, source_md_path)`

```python
class StateReducer:
    """Pure function from state dict to IKIGAiRecord. Stateless."""

    @staticmethod
    def reduce(state: dict[str, Any], source_md_path: Path) -> IKIGAiRecord:
        """Collapse `state` into an IKIGAiRecord.

        Cycle record is always EntityType.CYCLE, is_placeholder=True (D7).
        Required: cycle_id in state; source_md_path REQUIRED (D8/I9) and
        must point inside data/matheus/ikigai_state/.

        Raises KeyError if cycle_id missing; pydantic.ValidationError if
        any coerced value violates IKIGAiRecord constraints (UEID regex,
        ScoreValue range, phase_iteration ∈ [0,5], etc.).
        """
```

Mappers: `_map_vector_scores` (`dict[float]` → `dict[ScoreValue(unit=PERCENT, v*100)]`);
`_map_regime` (Literal → 4-level `FractalRegime`, global only — lower
levels = `MAINTAIN` placeholder); `_map_balancer_verdict` (pass-through
str; decouples from operational core).

### 3.2 Caller pattern

```python
from pathlib import Path
from ikigai.adapters.state_reducer import StateReducer
from ikigai.propagation.sqlite_adapter import SQLiteAdapter

# At cycle-end (commit node in the LangGraph):
record = StateReducer.reduce(
    state=graph_state_dict,
    source_md_path=Path("data/matheus/ikigai_state/cycle-2026-08-27.md"),
)
adapter = SQLiteAdapter(Path.home() / ".ikigai" / "plan_entities.db")
adapter.upsert_ikigai_record(record)
```

**Out of scope:** no filesystem writes, no SQLite upsert, no Literal
validation (Pydantic fires on `IKIGAiRecord(...)` construction), no drift
detection (separate adapter, commit `912a7c0`).

---

## §4. Acceptance criteria

The five testable bullets below mirror the SA-01..05 group in
`tests/test_integration_data_model.py` (spec C2 §4.3).

- **AC-1** — `reduce()` produces an `IKIGAiRecord` whose
  `entity_type == EntityType.CYCLE` and `is_placeholder is True`. Test:
  `test_reduce_emits_cycle_entity`. ✅
- **AC-2** — Every entry in `vector_scores` becomes
  `ScoreValue(value*100, unit="percent")`. Test:
  `test_reduce_maps_vector_scores`. ✅
- **AC-3** — `regime` is always a 4-level `FractalRegime` when
  `regime_state` is present, with exactly the levels `[global, cluster,
  vector, sub_vector]` in that order. Test:
  `test_reduce_maps_regime_into_fractal_regime`. ✅
- **AC-4** — Buffers (`prospective_buffer`, `retrospective_log`) and
  corrections pass through verbatim. Test:
  `test_reduce_preserves_corrections_buffer_and_retrospective`. ✅
- **AC-5 (SA-05)** — End-to-end pipeline: maintainer runs a cycle →
  `reduce()` called at the commit node → `IKIGAiRecord.model_validate()`
  passes → `SQLiteAdapter.upsert_ikigai_record()` writes a 24-col row →
  drift detector round-trips back without divergence. Test:
  `test_sa05_state_reducer_e2e_pipeline` (planned addition to SA-01..05
  group).

---

## §5. Migration path

The StateReducer is **already implemented** on
`feat/data-model-unification` (commit `770881e`) and unit-tested. The
migration here is about **wiring it into the LangGraph commit node**
without breaking the existing cycle-write path.

**Sprint 1 — side-by-side phase:** (1) Add reducer call at the commit
node in `src/agents/ikigai_maintainer/nodes/commit.py` (where the cycle
markdown is currently f-string'd). Reducer runs **before** the existing
f-string write; its output is logged to a debug channel but not
persisted. (2) Compare the reducer's output against the existing
f-string template fields (9 keys: `ueid, cycle_id, date, regime, q_he,
meta_vector, phase, corrections_count, vector_scores`). Any field
present in the reducer's `IKIGAiRecord` but absent from the f-string
template is a candidate for adding (per spec C1 §2.3 — writer must be
lossless). (3) Snapshot diff — for 5 consecutive cycles, log both the
reducer's `IKIGAiRecord.model_dump_json()` and the f-string output.
Verify the reducer's JSON is a strict superset.

**Sprint 2 — flip phase:** (1) Replace the f-string write with
`IKIGAiAgenticWriter.write_cycle(record)` (spec C1). (2) Pass the
reducer's `IKIGAiRecord` to `SQLiteAdapter.upsert_ikigai_record()`
(spec C2) immediately after the vault write — single transaction. (3)
Delete the f-string template (`commit.py:write_cycle_md`) and its tests.
(4) Promote `StateReducer.reduce` to the **sole entry point** for any
`IKIGAiStateDict → IKIGAiRecord` translation. Add a mypy custom rule
banning direct `IKIGAiRecord(**state)` calls in non-reducer modules.

**Rollback:** If the flip surfaces a divergence (e.g. a node that wrote
a value the reducer rejects under stricter Pydantic validation), the
reducer's `KeyError` / `ValidationError` is logged with the full state
dict and offending field; the cycle retries with a `force=True` flag on
the reducer that drops the offending field (gated on explicit operator
action — see §8 OQ-3); a spec amendment is filed before resuming the
flip. The `dict → IKIGAiRecord` direction is the only path the reducer
covers; the reverse is owned by `CheckpointAdapter` (separate spec).

---

## §6. Verification

```bash
# Static checks
poetry run mypy src/ikigai/adapters/state_reducer.py    # zero errors
poetry run ruff check src/ikigai/adapters/state_reducer.py  # zero errors

# Unit — 8 tests cover entity_type, is_placeholder, 4-level regime,
# vector score coercion, UEID preservation, source path, tz-aware
# timestamps, balancer verdict pass-through, lossless buffer passthrough
poetry run pytest tests/test_state_reducer.py -v

# Integration — SA-05 exercises the full pipeline:
# IKIGAiStateDict → reducer → IKIGAiRecord → SQLiteAdapter →
# round-trip read → maintainer diff
poetry run pytest tests/test_integration_data_model.py::TestStateReducerIntegration -v

# Score unit invariant — ratios in [0,1], percents in [0,100]
poetry run pytest -k "score_unit" -v

# Verify no ad-hoc IKIGAiRecord(**state) calls outside the reducer
grep -rn "IKIGAiRecord(\*\*state" src/ikigai/ | grep -v state_reducer
# Expected: no output

# Side-by-side snapshot (during migration)
poetry run python -c "
from pathlib import Path
from ikigai.adapters.state_reducer import StateReducer
import json
state = {...}  # load from a real LangGraph checkpoint
rec = StateReducer.reduce(state, source_md_path=Path('data/matheus/ikigai_state/cycle-test.md'))
print(json.dumps(rec.model_dump(mode='json'), indent=2, default=str))
"
# Expected: Valid JSON with all 17 fields present (or null where optional + absent)
# and entity_type: 'cycle'
```

---

## §7. Cross-references

- **Source / tests:** `life-ops/ikigai/src/ikigai/adapters/state_reducer.py`
  (130 lines, commit `770881e`); `tests/test_state_reducer.py` (108 lines,
  8 tests).
- **Adjacent entities:** `IKIGAiStateDict` (input, `state.py:107-168`),
  `IKIGAiRecord` (output, commit `4839a74`), `ScoreValue` (PERCENT/RATIO),
  `FractalRegime` (4-level D13 invariant).
- **Diagnostics:** `IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` §C3;
  `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §1
  (S-C1 split-brain origin).
- **Specs:** D6, D7, D13, I3, I4, I7; sibling
  `2026-08-27-spec-C1-vault-canonical-writer.md` (consumer),
  `2026-08-27-spec-C2-ikigai-record-polymorphic.md` (sibling).
- **ADRs / tests / branch:** ADR-009 (Pydantic strict mode —
  `extra="allow"` allows the reducer to forward unmapped fields via
  `custom`); `tests/test_integration_data_model.py` SA-01..05 (SA-05 is
  the StateReducer pipeline gate); `feat/data-model-unification`
  (commits `4839a74`, `770881e`, `4b6bc62`, `eeac3aa`, `ca4e65c`,
  `d9285be`).

---

## §8. Open questions

1. **Tighten `FractalRegimeState.regime` to a Literal?** Currently free
   `str`. Tightening would catch node typos but forces the reducer to
   know about enum membership (contradicts §2.4). Defer; drift detector
   surfaces divergence.
2. **`meta_vector_score` storage unit.** Currently RATIO (raw 0..1);
   some dashboards expect PERCENT. Swap is one-liner via
   `ScoreValue.normalized` when needed.
3. **`force=True` retry flag in §5.3** — caller owns it (commit node
   catches `ValidationError`, logs, emits `kill_switch_triggered=True`).
4. **`phase_weights` passthrough.** State dict still carries it
   (`state.py:134`); `IKIGAiRecord` does not (SPEC I7 → `PhaseSnapshot`).
   Reducer drops silently. Keep dropped; upstream should write to
   `PhaseSnapshot` via `PhaseAdapter` (not yet implemented).
5. **Multi-cycle reducer** — two cycles back-to-back = two records with
   different UEIDs. Persist both; `SQLiteAdapter` keys on UEID.
6. **Async signature** — `reduce()` is sync; if the commit node becomes
   async, no reducer change needed (pure). Caller wraps with
   `asyncio.to_thread`.
7. **Strict-mode invariant reconciliation** — ADR-009 chose
   `frozen=True, extra="forbid"`; `IKIGAiRecord` violates with
   `frozen=False, extra="allow"`. If the invariant is re-tightened, the
   reducer's `custom` passthrough breaks. See ADR-009 §3.

---

*SPEC C3 — StateReducer: `IKIGAiStateDict` → `IKIGAiRecord` — v1.0 — 2026-08-27*
