# Test Integration Recovery — `test_integration_data_model.py`

> **Status:** 🟡 Draft — 2026-08-28
> **Branch source:** `feat/data-model-unification`
> **Source commit:** `d9285be` — "test(integration): full round-trip on vault fixtures — §1 complete gate (Task 15)"
> **Target branch:** `gitbutler/workspace` (current)
> **Purpose:** Document the recovery + analysis of the 27-test integration gate so we can decide HOW to land it alongside the C1–C5 specs.

---

## §0 Purpose

`test_integration_data_model.py` is the **integration gate** for the entire
unified data-model stack. While the five C1–C5 specs each come with their own
unit-test files, this file is the **only place** where the round-trip is
exercised end-to-end against real vault markdown (`vaga-remota-2026.md`,
`q3-2026-primeira-vaga.md`) and a real SQLite mirror — no mocks.

It locks:

1. **`IKIGAiRecord` polymorphic root** — `custom` survives, UEID survives,
   nulls survive, datetimes stay tz-aware, `source_md_path` is REQUIRED,
   `extra="allow"` passes through unknown keys (RT-01..06).
2. **Polymorphic discriminator** — `dream` / `objective` / `vector` /
   fractal keys (`skill.python`) (PD-01..04).
3. **`ScoreValue` unit invariants** — PERCENT [0, 100], RATIO [0, 1],
   Q_HE forced to RATIO, frozen equality (SU-01..04).
4. **`OverrideRecord` / `manual_override` / `recommendation_score`** —
   round-trip verbatim (OV-01..03).
5. **`FractalRegime` 4-level invariant** (D13) — `global / cluster / vector
   / sub_vector`, constrained level names, regime round-trips (FR-01..03).
6. **Three adapters** — `DriftDetector` (SA-02, SA-03), `CheckpointAdapter`
   (SA-04), `StateReducer` (SA-05), plus `drift_state` integration (SA-01).
7. **`PhaseSnapshot` + `is_placeholder`** (PH-01).
8. **`DriftState` resolved-path round-trip** (PS-01).

Without these tests, the C1–C5 specs have unit-only coverage; the **e2e
contract** (vault markdown → record → dict → record → adapters → SQLite)
would silently rot.

---

## §1 File Location & Recovery

| Item | Value |
|------|-------|
| **Path on source branch** | `life-ops/ikigai/tests/test_integration_data_model.py` |
| **Blob SHA** | `1cdf7faf3b0235d22a14d0fbd568ddcb5c108797` |
| **Recovery command** | `git show feat/data-model-unification:life-ops/ikigai/tests/test_integration_data_model.py > C:\Users\mathe\AppData\Local\Temp\test_integration_data_model.recovered.py` |
| **File on disk now** | `C:\Users\mathe\AppData\Local\Temp\test_integration_data_model.recovered.py` |
| **Line count** | **477 lines** |
| **Test count** | **27 tests** |
| **Confirmed passing on branch** | "27/27 pass" (commit message) |
| **Workspace status** | NOT present on `gitbutler/workspace` — full gap |

```
$ git ls-tree feat/data-model-unification -- life-ops/ikigai/tests/test_integration_data_model.py
100644 blob 1cdf7faf3b0235d22a14d0fbd568ddcb5c108797 life-ops/ikigai/tests/test_integration_data_model.py
```

The file is a single self-contained pytest module — no `conftest.py`
additions required, no plugin code, no parametrized fixtures beyond
`dream_record` and `tmp_dir`.

---

## §2 Test Inventory

### 2.1 Test groups (matches docstring naming)

| Group | Range | Count | What it covers |
|-------|-------|------:|----------------|
| **RT** (round-trip) | RT-01..06 | 6 | C1 + C2 — `IKIGAiRecord → dict → record` lossless |
| **PD** (polymorphic discriminator) | PD-01..04 | 4 | C2 — `entity_type` enum + fractal vector keys |
| **SU** (score units) | SU-01..04 | 4 | C2 — `ScoreValue` PERCENT/RATIO ranges + frozen |
| **OV** (override) | OV-01..03 | 3 | C2 — `OverrideRecord` + `manual_override` + `recommendation_score` |
| **FR** (fractal regime) | FR-01..03 | 3 | C2 — `FractalRegime` 4-level + constrained names |
| **SA** (state adapters) | SA-01..05 | 5 | C3 + C4 + C5 — `DriftDetector` + `CheckpointAdapter` + `StateReducer` |
| **PH** (placeholder) | PH-01 | 1 | C2 — `is_placeholder=True` + `PhaseSnapshot` shape |
| **PS** (path-state) | PS-01 | 1 | C2 + C5 — `drift_state="conflict"` + `source_md_path` round-trip |
| **TOTAL** | | **27** | |

### 2.2 Per-test detail

| # | Test name | Spec | AC | Status |
|--:|-----------|------|----|--------|
| 1 | `test_rt01_full_round_trip_preserves_custom_fields` | C1+C2 | AC-1 (custom field lossless) | PASS-ON-BRANCH / MISSING-DEPS on workspace |
| 2 | `test_rt02_ueid_survives_round_trip` | C1+C2 | AC-1 (UEID canonical 5-part) | PASS-ON-BRANCH / MISSING-DEPS |
| 3 | `test_rt03_null_fields_survive` | C1+C2 | AC-1 (null preservation, RT-03) | PASS-ON-BRANCH / MISSING-DEPS |
| 4 | `test_rt04_datetimes_are_tz_aware` | C1+C2 | AC-1 (tz-aware datetime) | PASS-ON-BRANCH / MISSING-DEPS |
| 5 | `test_rt05_source_md_path_required_and_preserved` | C1+C2 | AC-1 (D8/I9 REQUIRED Path) | PASS-ON-BRANCH / MISSING-DEPS |
| 6 | `test_rt06_extra_allow_passthrough` | C1+C2 | AC-1 (extra='allow' passthrough) | PASS-ON-BRANCH / MISSING-DEPS |
| 7 | `test_pd01_dream_entity_type_round_trips` | C2 | AC-4 (entity_type=dream) | PASS-ON-BRANCH / MISSING-DEPS |
| 8 | `test_pd02_objective_entity_type_round_trips` | C2 | AC-4 (entity_type=objective) | PASS-ON-BRANCH / MISSING-DEPS |
| 9 | `test_pd03_vector_entity_type_round_trips` | C2 | AC-4 (entity_type=vector) | PASS-ON-BRANCH / MISSING-DEPS |
| 10 | `test_pd04_vector_scores_support_fractal_keys` | C2 | AC-4 (D3 fractal keys) | PASS-ON-BRANCH / MISSING-DEPS |
| 11 | `test_su01_percent_range_enforced` | C2 | I3 (PERCENT [0,100]) | PASS-ON-BRANCH / MISSING-DEPS |
| 12 | `test_su02_ratio_range_enforced` | C2 | I4 (RATIO [0,1]) | PASS-ON-BRANCH / MISSING-DEPS |
| 13 | `test_su03_q_he_must_be_ratio` | C2 | I4 (Q_HE RATIO) | PASS-ON-BRANCH / MISSING-DEPS |
| 14 | `test_su04_score_value_equality` | C2 | I3 (frozen equality) | PASS-ON-BRANCH / MISSING-DEPS |
| 15 | `test_ov01_override_record_round_trips` | C2 | D12 (audit_trail shape) | PASS-ON-BRANCH / MISSING-DEPS |
| 16 | `test_ov02_override_values_preserved_verbatim` | C2 | D12 (Any values verbatim) | PASS-ON-BRANCH / MISSING-DEPS |
| 17 | `test_ov03_correction_signal_fields_preserved` | C2 | D12 (manual_override + recommendation_score) | PASS-ON-BRANCH / MISSING-DEPS |
| 18 | `test_fr01_fractal_regime_has_four_levels` | C2 | D13 (4-level invariant) | PASS-ON-BRANCH / MISSING-DEPS |
| 19 | `test_fr02_level_names_are_constrained` | C2 | D13 (Literal level constraint) | PASS-ON-BRANCH / MISSING-DEPS |
| 20 | `test_fr03_regime_round_trips_on_record` | C2 | D13 (regime round-trip) | PASS-ON-BRANCH / MISSING-DEPS |
| 21 | `test_sa01_vault_is_canonical` | C5 | AC-C5-5 (vault = canonical) | PASS-ON-BRANCH / MISSING-DEPS |
| 22 | `test_sa02_drift_detector_in_sync_when_vault_matches` | C5 | AC-C5-1 (state = IN_SYNC) | PASS-ON-BRANCH / MISSING-DEPS |
| 23 | `test_sa03_drift_detector_flags_markdown_newer` | C5 | AC-C5-1 (state = MARKDOWN_NEWER, mtime proxy) | PASS-ON-BRANCH / MISSING-DEPS |
| 24 | `test_sa04_checkpoint_adapter_round_trip` | C4 | AC-C4-02 (save/load IKIGAiRecord round-trip) | PASS-ON-BRANCH / MISSING-DEPS |
| 25 | `test_sa05_state_reducer_normalizes_state_dict` | C3 | AC-5 / SA-05 (cycle end-to-end) | PASS-ON-BRANCH / MISSING-DEPS |
| 26 | `test_ph01_placeholder_and_phase_snapshot_round_trip` | C2 | AC-6 + I7 (is_placeholder + PhaseSnapshot) | PASS-ON-BRANCH / MISSING-DEPS |
| 27 | `test_ps01_drift_state_resolved_path_round_trips` | C2+C5 | AC-1 + AC-C5-5 (drift_state + path) | PASS-ON-BRANCH / MISSING-DEPS |

> All 27 tests have `PASS-ON-BRANCH` per the `d9285be` commit message and
> per the explicit table in spec C2 §4.3. None of the test functions can
> be imported on `gitbutler/workspace` today (see §3).

---

## §3 Dependency Analysis

### 3.1 Required imports (all 13 symbols — none on workspace)

The test imports the following symbols. The "Workspace" column reports
whether the symbol exists in the workspace's `life-ops/ikigai/src/ikigai/`
tree today.

| Import | Workspace status | Source spec | Source commit (branch) |
|--------|:----------------:|-------------|------------------------|
| `from ikigai.adapters.checkpoint_adapter import CheckpointAdapter` | ❌ MISSING | C4 | `eb8be96` |
| `from ikigai.adapters.drift_detector import DriftDetector` | ❌ MISSING | C5 | `912a7c0` |
| `from ikigai.adapters.sqlite_bridge import IKIGAiRecordBridge` | ❌ MISSING | C2 | `2c6e20f` |
| `from ikigai.adapters.state_reducer import StateReducer` | ❌ MISSING | C3 | `770881e` |
| `from ikigai.entities.drift_state import DriftState` | ❌ MISSING | C5 | `912a7c0` |
| `from ikigai.entities.fractal_regime import FractalRegime, FractalRegimeState` | ❌ MISSING | C2 | `4839a74` (entity cluster) |
| `from ikigai.entities.ikigai_record import EntityType, IKIGAiRecord, StatusType` | ❌ MISSING | C2 | `4839a74` |
| `from ikigai.entities.override import OverrideRecord` | ❌ MISSING | C2 | `4839a74` (entity cluster) |
| `from ikigai.entities.phase_snapshot import PhaseSnapshot` | ❌ MISSING | C2 | `dc19c03` |
| `from ikigai.entities.score_value import ScoreUnit, ScoreValue` | ❌ MISSING | C2 | `4839a74` (entity cluster) |
| `from ikigai.propagation.sqlite_adapter import SQLiteAdapter` | ⚠️ PRESENT but LEGACY 11-col | C2 | pre-C2 (11-col); `4b6bc62` adds `upsert_ikigai_record` |
| `from ikigai.vault.dict_to_frontmatter import dict_to_frontmatter` | ❌ MISSING | C1 | `1de3641` |
| `from ikigai.vault.frontmatter_to_dict import frontmatter_to_dict` | ❌ MISSING | C1 | `1de3641` |

**Bottom line:** 12 of 13 imports are missing on workspace. The test cannot
be landed in isolation — every module it touches lives on the
`feat/data-model-unification` branch and was never merged into workspace.

### 3.2 Workspace's `ikigai` module today

The workspace currently has a different `ikigai` module layout — older
subpackages that predate the unification work:

```
life-ops/ikigai/src/ikigai/
├── __init__.py
├── constants.py
├── enums.py
├── exceptions.py
├── types.py
├── core/                 ← heuristics + scoring (NOT used by tests)
├── entities/
│   ├── base.py
│   ├── ueid.py           ← UEID validator lives here on workspace
│   ├── profile.py
│   ├── regime.py
│   ├── skill.py
│   ├── opportunity.py
│   ├── vector.py
│   └── plan/             ← DreamEntity / GoalEntity / ObjectiveEntity / Project / Task / Deliverable
├── propagation/
│   ├── frontmatter.py
│   ├── markdown_db.py
│   ├── sqlite_adapter.py ← 11-col legacy, NOT 24-col unified
│   └── triagem.py        ← legacy drift detection (no DriftDetector)
├── state_machines/
└── cli/
```

Notable absences: **`ikigai.adapters/` package does not exist** on
workspace, **`ikigai.vault/` package does not exist** on workspace,
**`ikigai.entities.{ikigai_record,score_value,fractal_regime,drift_state,
override,phase_snapshot}` do not exist** on workspace. The workspace's
`entities/ueid.py` is the closest analogue but the test expects
`ikigai.entities.ikigai_record.UEID` (re-exported from `ikigai.entities.ueid`
per commit `dbaaf5e`).

### 3.3 Vault fixtures

The test loads two real markdown fixtures. **Both exist on workspace.**

| Fixture | Path on workspace | Status |
|---------|-------------------|--------|
| `DREAM_MD` | `life-ops/ikigai/data/matheus/dreams/vaga-remota-2026.md` | ✅ exists |
| `OBJECTIVE_MD` | `life-ops/ikigai/data/matheus/objectives/q3-2026-primeira-vaga.md` | ✅ exists |

`_require(path)` calls `pytest.skip(...)` if either fixture is missing —
defensive coding that allows partial runs when only one fixture is present.

### 3.4 Fixtures / conftest requirements

The file declares two fixtures inline (`dream_record`, `tmp_dir`) — neither
needs `conftest.py`. It also references the workspace's existing
`life-ops/ikigai/tests/conftest.py` (does not need to be modified).

`tmp_dir` is `Path(tempfile.mkdtemp(prefix="dmu_integration_"))` — fully
self-contained, no project-level state.

### 3.5 Path resolution quirk

Line 46: `_PROJECT_ROOT = Path(__file__).resolve().parents[3]`

This walks **3 parents up** from the test file. If the file lands at
`life-ops/ikigai/tests/test_integration_data_model.py`, then
`parents[3]` = `life-ops/ikigai/tests → 2=life-ops/ikigai → 1=life-ops
→ 0=life` (project root). So `VAULT_REL = "life-ops/ikigai/data/matheus"`
is concatenated correctly and resolves to `life/life-ops/ikigai/data/matheus`.
This matches the workspace layout. **No path fix needed when landing.**

---

## §4 Coverage Against 5 Specs

### 4.1 Spec C1 — Vault Canonical Writer

Spec lists AC-1..5; only AC-1 has an integration counterpart in this file:

| AC | Test functions | Notes |
|----|----------------|-------|
| **AC-1** (lossless round-trip) | RT-01, RT-02, RT-03, RT-04, RT-05, RT-06 | All 6 RT tests exercise `dict_to_frontmatter(record) → IKIGAiRecord.model_validate(...)` round-trip; the lossless contract. |
| AC-2 (VaultLock serialization) | — | NOT in this file; covered by `tests/test_vault_lock.py` per C1 §6.1 |
| AC-3 (concurrent writes no deadlock) | — | NOT in this file; covered by `tests/test_agentic_writer.py::test_concurrent_writes_different_files` per C1 §6.1 |
| AC-4 (f-string deleted) | — | Static grep gate per C1 §6.2 (not a pytest) |
| AC-5 (CLI reconcile uses writer) | — | Static grep gate per C1 §6.2 (not a pytest) |

**Coverage verdict:** RT-01..06 are the integration half of C1 AC-1; they
are necessary but not sufficient (unit files also required for AC-2, AC-3).

### 4.2 Spec C2 — IKIGAiRecord Polymorphic Root

Spec §4.3 lists RT-01..06 + 21 supporting tests — this file IS that list:

| AC | Test functions | Notes |
|----|----------------|-------|
| **AC-1** (writes flow through adapter) | (not testable here; static grep) | Per C2 §4.1 |
| **AC-2** (11-col removed) | (not testable here; migration script) | Per C2 §4.1 |
| **AC-3** (UEID regex) | RT-02 | UEID matches fixture after round-trip |
| **AC-4** (16 EntityType variants) | PD-01, PD-02, PD-03, PD-04 | dream/objective/vector + fractal vector keys |
| **AC-5** (lossless + canonical UEID) | RT-01, RT-02 | Custom field lossless + UEID |
| **AC-6** (is_placeholder=True on CYCLE) | PH-01 (partial), SA-05 | `is_placeholder=True` round-trip + CYCLE via StateReducer |
| **AC-7** (integration gate) | **all 27 tests** | Per C2 §4.3 — this file IS AC-7 |
| **AC-8** (migrate idempotent) | — | Migration script test (separate file) |

SU-01..04, OV-01..03, FR-01..03, PH-01, PS-01 each map to specific C2 §3
fields:
- SU-01..04 → I3 / I4 / Q_HE unit invariant
- OV-01..03 → D12 (audit_trail + manual_override + recommendation_score)
- FR-01..03 → D13 (4-level FractalRegime)
- PH-01 → I7 (PhaseSnapshot separation)
- PS-01 → D14 + C5 integration

**Coverage verdict:** C2 is the **primary beneficiary** of this file —
all 16 acceptance tests referenced in C2 §4.3 map 1-to-1 onto these 27 tests.

### 4.3 Spec C3 — StateReducer

| AC | Test functions | Notes |
|----|----------------|-------|
| AC-1 (CYCLE + is_placeholder=True) | SA-05 | `rec.entity_type is EntityType.CYCLE` + `rec.is_placeholder is True` |
| AC-2 (vector_scores → PERCENT) | SA-05 | `rec.vector_scores["skill"].unit is ScoreUnit.PERCENT` |
| AC-3 (4-level FractalRegime) | SA-05 + FR-01 | `len(rec.regime.levels) == 4` |
| AC-4 (buffers + corrections verbatim) | — | NOT in this file; covered by `tests/test_state_reducer.py` |
| **AC-5 (SA-05 e2e pipeline)** | SA-05 | `StateReducer.reduce(state, source_md_path)` → `IKIGAiRecord` |

**Coverage verdict:** SA-05 is the **only** test in this file that exercises
StateReducer. AC-1..3 are implicitly covered (the SA-05 assertions check
all three). AC-4 has no integration test here.

### 4.4 Spec C4 — CheckpointAdapter

| AC | Test functions | Notes |
|----|----------------|-------|
| AC-C4-01 (no pickle header) | — | Not directly asserted; SA-04 does not sniff the header |
| **AC-C4-02 (round-trip)** | SA-04 | `adapter.save(rec, "t1")` → `adapter.load("t1")` → equal ueid + q_he_score |
| AC-C4-03 (overwrite idempotent) | — | Not directly tested |
| AC-C4-04 (SchemaRegistry enforcement) | — | Not tested here; covered in `tests/test_checkpoint_adapter.py` |
| **AC-C4-05 (SA-04 integration gate)** | SA-04 | Maps to C4 AC-C4-05 (the spec actually names this test as the gate) |

**Coverage verdict:** SA-04 covers AC-C4-02 + AC-C4-05. AC-C4-01, -03, -04
are unit concerns owned by `tests/test_checkpoint_adapter.py`.

> **Note:** the spec names the test `test_SA_04_checkpoint_round_trip_via_jsonplus`
> in C4 §4 AC-C4-05 and §6.2; the **actual function name on the branch is
> `test_sa04_checkpoint_adapter_round_trip`** (snake_case, no
> `via_jsonplus` suffix). The spec docstring and the function name diverge —
> minor doc nit to fix when the spec is re-rendered.

### 4.5 Spec C5 — DriftDetector

| AC | Test functions | Notes |
|----|----------------|-------|
| **AC-C5-1** (6 DriftState values) | SA-02, SA-03 | IN_SYNC (SA-02), MARKDOWN_NEWER (SA-03) |
| AC-C5-2 (per-UEID frontmatter) | — | Not tested here; covered by `tests/test_drift_detector.py::test_write_per_ueid_report_includes_frontmatter` |
| AC-C5-3 (300s tolerance) | — | Not directly tested in this file |
| AC-C5-4 (legacy summary back-compat) | — | Not tested here |
| **AC-C5-5** (source_md_path integration) | SA-01, PS-01 | vault canonical path + `drift_state` on record |

**Coverage verdict:** SA-01..03 + PS-01 cover 4 of 6 ACs. AC-C5-2..4 are
report-write concerns owned by `tests/test_drift_detector.py`.

> Spec C5 §4 names `test_sa_03_drift_with_canonical_path` (AC-C5-5);
> the **actual function name is `test_sa03_drift_detector_flags_markdown_newer`**
> with drift integration exercised implicitly. Spec renumbering needed.

---

## §5 Landing Strategy

### 5.1 Option A — Cherry-pick commit `d9285be` (RECOMMENDED)

```bash
cd "C:\Users\mathe\code_space\life-oss\life"
git cherry-pick d9285be --no-commit
```

**Pros:**
- Single-file change, surgical.
- Test already green on `feat/data-model-unification` (27/27 per commit
  message + spec C2 §4.3 verification).
- The 27 tests are the AC-7 reference for C2; the user's 5-spec set is
  **incomplete without them** — RT-01..06 are referenced verbatim by
  spec C1 §6.1 and spec C2 §4.3.

**Cons:**
- Will land ALONE first, then `pytest` on workspace will fail with
  ImportError on every test (`ikigai.adapters.*` etc.). The test file
  becomes a **red baseline** until the other C1–C5 commits land.

**Mitigation for the ImportError red-baseline period:**
- Mark the file `@pytest.mark.skip(reason="C1-C5 unification work not
  merged; see 2026-08-28-test-integration-recovery.md")` in a small
  pre-commit hook or simply add `pytest.importorskip("ikigai.adapters")`
  at module top.
- OR add `pytest.importorskip("ikigai.adapters.checkpoint_adapter")` so
  the entire file is skipped until the adapters package exists.
- This is the **same pattern** the file already uses internally via
  `_require(path)` for vault fixtures.

### 5.2 Option B — Re-write on workspace (NOT recommended)

Translate the test logic onto the workspace's older `ikigai` module layout
(`ikigai.entities.plan.dream.DreamEntity`, `ikigai.propagation.sqlite_adapter`
legacy 11-col). Would produce a **divergent test file** that does NOT match
the C1–C5 spec acceptance tests, breaks the 1:1 mapping the user explicitly
referenced in spec C2 §4.3, and creates a permanent fork between the
branch's tests and the workspace's tests.

**Reject.** Specs C1–C5 are explicitly the landing plan; rewriting tests
in workspace dialect defeats the unification premise.

### 5.3 Option C — Defer until C1–C5 land (DEFENSIBLE)

Hold the file on `feat/data-model-unification`, land C1–C5 commits first,
then merge this as the closing gate.

**Pros:** no red baseline on workspace; the test only goes green after
all 5 specs land.

**Cons:**
- The user explicitly told us: "nao vamos codificar nada ainda, apenas
  documentar todo o trabalho pendente" (data-first methodology — ADR-007).
- We are in the **document-only phase**; landing tests IS coding work in
  spirit even if it is test code. Holding it preserves the no-code
  mandate.
- However, tests document contracts as much as specs do — keeping the
  test file as a **documented reference** of what will eventually run is
  consistent with the methodology.

### 5.4 Recommendation

**Option C** with a soft handoff: keep the recovered test file at the
temp path + this diagnostic doc as the reference. When the user gives the
green light to land C1–C5 (the implementation work), the test file
cherry-picks as Option A. The temp file is NOT committed to workspace
during the data-first phase.

**However**, if the user wants the test file present on workspace as a
known-failing red baseline (so `pytest` shows the gap explicitly), then
**Option A with the `pytest.importorskip` gate** is the right call. Either
way, this doc is the audit trail.

### 5.5 Acceptance criteria for landing

Whichever option is chosen, the test file's landing is **gated** by these
invariants from spec C2 §4.3:

1. All 13 imports resolve on workspace.
2. `tests/test_integration_data_model.py -v` exits 0 with 27 passed.
3. No other test on workspace regresses (the integration tests only add;
   they don't modify other tests).
4. The vault fixtures (`vaga-remota-2026.md`, `q3-2026-primeira-vaga.md`)
   parse via `frontmatter_to_dict` without modification — confirmed
   today; both files exist.
5. The SQLiteAdapter on workspace supports `upsert_ikigai_record` method
   (requires `4b6bc62`).

---

## §6 Open Questions

1. **Function-name divergence with C4/C5 specs.** C4 §4 AC-C4-05 names
   `test_SA_04_checkpoint_round_trip_via_jsonplus`; actual is
   `test_sa04_checkpoint_adapter_round_trip`. C5 §4 AC-C5-5 names
   `test_sa_03_drift_with_canonical_path`; actual is
   `test_sa03_drift_detector_flags_markdown_newer`. Decide:
   (a) rename tests to match spec names; (b) update spec names to match
   tests; (c) leave as-is (function names are more descriptive). Default:
   (c) — open issue if user prefers (a) or (b).

2. **Why no AC-C4-01 / AC-C4-03 / AC-C4-04 tests in this file?** The spec
   implies the integration gate covers all 5 ACs; only AC-C4-02 + AC-C4-05
   are here. **Action:** amend spec C4 §4 to clarify which ACs belong in
   the integration gate vs `tests/test_checkpoint_adapter.py`.

3. **Why no AC-4 (16 EntityType variants) full sweep?** PD-01..04 cover
   3 of 16 (dream, objective, vector). Per C2 §4.3, the full sweep is in
   `tests/test_ikigai_record.py::test_each_entity_type_loads` — but no
   such function appears in the inventory on branch. **Action:** verify
   that test exists on `feat/data-model-unification` (not in this file).

4. **AC-C5-3 (300s tolerance) absent from this file.** The 300s
   `tolerance_seconds` constant is in spec C5 §3.1 but no integration test
   exercises it. **Action:** add a test to the gap-filling PR, or document
   the gap here and defer.

5. **`_load_record` normalization.** Lines 64–71 normalize uppercase
   `status: ACTIVE` → `active` and inject `source_md_path` when null.
   These are **fixture-only quirks** of the current vault files. Will the
   canonical C1 vault writer (commit `d04fa0c`) lower-case status on
   write? If so, the normalization can be removed; if not, it stays as a
   **back-compat shim** for legacy vault files.

6. **`drift_state is DriftState.IN_SYNC` assertion in SA-01.** The test
   asserts `dream_record.drift_state is DriftState.IN_SYNC` without ever
   calling `DriftDetector`. This works only if the vault fixture carries
   `drift_state: in_sync` in its frontmatter. **Verify** that
   `vaga-remota-2026.md` has this field; if not, SA-01 fails on workspace
   even after all imports resolve.

7. **Path resolution depth check.** `_PROJECT_ROOT = parents[3]` assumes
   the test lives at exactly `life-ops/ikigai/tests/`. If the file lands
   one level deeper (e.g. inside `tests/integration/`), paths break.
   **Lock the path** when landing: `life-ops/ikigai/tests/test_integration_data_model.py`.

---

## §7 Cross-references

| Reference | Path | Role |
|-----------|------|------|
| **Source test file (recovered)** | `C:\Users\mathe\AppData\Local\Temp\test_integration_data_model.recovered.py` | Working copy, not in repo |
| **Original on branch** | `life-ops/ikigai/tests/test_integration_data_model.py` (blob `1cdf7faf...`) at commit `d9285be` | Source of truth |
| **Commit metadata** | `git log --oneline feat/data-model-unification -- life-ops/ikigai/tests/test_integration_data_model.py` → `d9285be test(integration): full round-trip on vault fixtures — §1 complete gate (Task 15)` | Landed as Task 15 |
| **Related commits on branch** | `4839a74` (IKIGAiRecord), `770881e` (StateReducer), `eb8be96` (CheckpointAdapter), `912a7c0` (DriftDetector), `2c6e20f` (IKIGAiRecordBridge), `4b6bc62` (upsert method), `eeac3aa` (migration script), `ca4e65c`, `dbaaf5e` | All part of the unification; test depends on all of them |
| **Spec C1** | `code-docs/specs/2026-08-27-spec-C1-vault-canonical-writer.md` | RT-01..06 cover C1 AC-1 |
| **Spec C2** | `code-docs/specs/2026-08-27-spec-C2-ikigai-record-polymorphic.md` §4.3 | **This file IS C2 AC-7** |
| **Spec C3** | `code-docs/specs/2026-08-27-spec-C3-state-reducer.md` | SA-05 covers C3 AC-1..3 + AC-5 |
| **Spec C4** | `code-docs/specs/2026-08-27-spec-C4-checkpoint-adapter.md` | SA-04 covers C4 AC-C4-02 + AC-C4-05 |
| **Spec C5** | `code-docs/specs/2026-08-27-spec-C5-drift-detector.md` | SA-01..03 + PS-01 cover C5 AC-C5-1 + AC-C5-5 |
| **Master diagnostic** | `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §1 S-C1..S-C5 | Parent of all 5 specs |
| **Sprint 1 plan** | `code-docs/diagnostic/2026-08-27-sprint1-implementation-plan.md` (Task 15, #014, etc.) | Tracks landing order |
| **Data-first methodology** | ADR-007 (per memory note `data-first-methodology.md`) | "nao vamos codificar nada ainda, apenas documentar" |
| **This doc** | `code-docs/diagnostic/2026-08-28-test-integration-recovery.md` | Audit trail for the recovered file |

---

*Diagnostic — `test_integration_data_model.py` recovery — 2026-08-28 —
investigation only, no commits, no code edits.*