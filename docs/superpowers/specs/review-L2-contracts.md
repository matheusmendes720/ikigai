# IKIGAI System Review — Layer 2 (src/contracts/) Diagnostic

**Date:** 2026-09-12
**Task:** T-11.3 (M11 system top-down review)
**Scope:** Canonical Pydantic contracts layer (`src/contracts/`)
**Method:** Read-only inspection (no code changes)
**Drift net reference:** `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py`
**Source spec:** `docs/superpowers/specs/2026-09-10-system-review-design.md` §2 Layer 2

---

## §0 — Goal

Verify the canonical Pydantic contracts layer honours three load-bearing
invariants:

1. **UEID canonical regex** — 4-part format per ADR-014
   (`^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`).
2. **Pydantic v2 strict** — every `BaseModel` carries both
   `frozen=True` and `extra="forbid"` (per project memory).
3. **PAV-archived math** — no algorithm constants (`DEFAULT_HABIT_LAMBDA`,
   `DEFAULT_ENERGY`, `DEFAULT_QHE`, `REGIME_*`, `POMODORO_*` thresholds)
   survive in the layer per ADR-013 (PAV kernel archived 2026-08-31).

---

## §1 — File Inventory

14 Python files in `src/contracts/` (1 package init + 13 modules). Non-py
artifacts (`.venv/`, `.mypy_cache/`, `.pytest_cache/`, `__pycache__/`,
`pyproject.toml`, `uv.lock`) excluded.

| File                          | Lines | Purpose                                                      |
|-------------------------------|------:|--------------------------------------------------------------|
| `__init__.py`                 |    97 | Re-exports + `__all__` (grouped by domain, RUF022 suppressed) |
| `base.py`                     |    86 | `BasePlanContract` — 6-level plan hierarchy root, enforces `frozen=True, extra="forbid"` + `ikigai_vectors` non-empty |
| `common.py`                   |   250 | `UEID` (4-part regex), `Period`, `Priority`, `EntityType`, `RegimeState`, `TimestampMixin`, `PaeCyclePhase`, `PlanTier`, `VectorKey` literals |
| `entrega.py`                  |    17 | `Entrega` (deliverable) — extends `BasePlanContract` |
| `investigation.py`            |    68 | `Investigation` (Plan C pre-form queue, separate `inq_id` namespace, NOT a UEID) |
| `meta.py`                     |    15 | `Meta` (measurable goal with `review_frequency_days`) |
| `metrics.py`                  |   195 | `Burndown`, `ExecutionRate`, `QHEScore` — feedback signals; `QHEScore.qhe` / `.regime_predicted` raise `NotImplementedError` per ADR-013 |
| `objetivo.py`                 |    15 | `Objetivo` (quarterly/onda objective with `key_results`) |
| `planning.py`                 |   221 | `Wave`, `Sprint`, `PlanningCycle`, `VaultEvent` — temporal hierarchy; cycle/wave/sprint ID patterns (`C\d+_MMM_YYYY`, etc.) |
| `projeto.py`                  |    18 | `Projeto` (project with `tech_stack`, `target_revenue_brl`) |
| `sonho.py`                    |    16 | `Sonho` (root of hierarchy, `tier="SONHO"`, `parent_ueid=None`) |
| `tarefa.py`                   |    10 | `Tarefa` (leaf, no extra fields) |
| `task.py`                     |   212 | `Task`, `Subtask`, `ChecklistItem`, `Project`, `Milestone`, `Deliverable` + `ProjectStatus` enum |
| `task_change.py`              |    58 | `TaskChange`, `PropagationEvent` (review-queue models) + `TaskAction` enum |
| **TOTAL**                     | **1278** | |

---

## §2 — UEID Canonical Regex Verification

**Definition site:** `src/contracts/common.py:34`

```python
_UEID_PATTERN = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")
```

**Format:** 4 parts separated by colons (`type:slug:uuid:hash`)

| Segment | Constraint      | Example                                       |
|---------|-----------------|-----------------------------------------------|
| type    | `[a-z]{2,5}`    | `tsk`, `proj`, `hab`, `wave`, `sprint`, `cyc` |
| slug    | `[a-z0-9-]+`    | `byd-case-review`, `morning-water`            |
| uuid    | `[a-f0-9-]+`    | `abc12345-1234-5678-9abc-def012345678`        |
| hash    | `[a-f0-9-]+`    | `0123456789abcdef`                            |

**Verdict:** MATCH — exact 4-part regex matches ADR-014
(`code-docs/adr/ADR-014-ueid-canonical-format.md`).

**Comment in source (`common.py:35-43`)** calls out the 5-part canonical
that historically lived at `src/ikigai/src/ikigai/types.py` — that
reference was renamed to `sys_ikigai/` per commit `685dec5` and is now
non-authoritative for the contracts layer. The contracts layer stays
on the 4-part format and acts as the consumer-facing alias.

**Legacy compatibility:** `UEID.from_legacy()` (lines 87-128) accepts
the 2-part underscore format (`tsk_morning_water`) and pads uuid/hash
with zeros. This is by design for vault reads — never written.

**Example cross-checks** (from `common.py:55-58`):

- `tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef` → 4 parts, valid
- `hab:sleep-8h:11111111-2222-3333-4444-555555555555:ffffffffffffffff` → 4 parts, valid
- `proj:vaga-remota-2026:00000000-0000-0000-0000-000000000000:0000000000000000` → 4 parts, valid

---

## §3 — Pydantic Strict Coverage

**Target invariant:** `frozen=True` AND `extra="forbid"` on every
`BaseModel` subclass.

**Enforcement source:** `BasePlanContract` (`base.py:52`) sets both via
`ConfigDict(frozen=True, extra="forbid")`. All 6 plan-hierarchy classes
(Sonho, Objetivo, Meta, Projeto, Entrega, Tarefa) inherit and inherit
both invariants for free.

### 3.1 Direct BaseModel subclasses — 18 classes

| File             | Class                  | `frozen=True` | `extra="forbid"` |
|------------------|------------------------|:-------------:|:----------------:|
| `base.py`        | `BasePlanContract`     | ✓             | ✓                |
| `task.py`        | `Task`                 | ✓             | ✓                |
| `task.py`        | `Subtask`              | ✓             | ✓                |
| `task.py`        | `ChecklistItem`        | ✓             | ✓                |
| `task.py`        | `Project`              | ✓             | ✓                |
| `task.py`        | `Milestone`            | ✓             | ✓                |
| `task.py`        | `Deliverable`          | ✓             | ✓                |
| `planning.py`    | `Wave`                 | ✓             | ✓                |
| `planning.py`    | `Sprint`               | ✓             | ✓                |
| `planning.py`    | `PlanningCycle`        | ✓             | ✓                |
| `planning.py`    | `VaultEvent`           | ✓             | ✓                |
| `metrics.py`     | `Burndown`             | ✓             | ✓                |
| `metrics.py`     | `ExecutionRate`        | ✓             | ✓                |
| `metrics.py`     | `QHEScore`             | ✓             | ✓                |
| `task_change.py` | `TaskChange`           | ✓             | ✓                |
| `task_change.py` | `PropagationEvent`     | ✓             | ✓                |
| `investigation.py` | `Investigation`      | ✓             | ✓                |

**Strict coverage: 17/17 (100%)** of hand-written `BaseModel` classes
in `src/contracts/`.

### 3.2 Plan hierarchy via inheritance — 6 classes

All 6 plan-hierarchy entities inherit `frozen=True, extra="forbid"`
from `BasePlanContract`:

- `Sonho` (`sonho.py:11`)
- `Objetivo` (`objetivo.py:11`)
- `Meta` (`meta.py:11`)
- `Projeto` (`projeto.py:12`)
- `Entrega` (`entrega.py:12`)
- `Tarefa` (`tarefa.py:9`)

Combined coverage: **23/23 (100%)** BaseModel-derived classes.

### 3.3 Exceptions (not BaseModel)

- `TimestampMixin` (`common.py:233`) sets ONLY `extra="forbid"` — not
  `frozen=True`. This is by design: it is a `BaseModel` mixin that
  subclasses must compose with their own `model_config`. **Gap §A.1**
  below.
- `UEID` (`common.py:46`) is a `str` subclass with custom validator
  (`__new__` + `__get_pydantic_core_schema__`). Frozen semantics do not
  apply to `str` subclasses in Pydantic v2.
- 5 `StrEnum` classes (`Period`, `Priority`, `EntityType`, `RegimeState`,
  `ProjectStatus`, `WaveStatus`, `SprintStatus`, `PlanningCycleStatus`)
  are immutable by enum definition and need no `ConfigDict`.
- 1 `str, Enum` (`TaskAction`) — same, immutable.

---

## §4 — PAV Algorithm Constant Audit

**Search patterns** (per task brief):

```
DEFAULT_HABIT_LAMBDA | DEFAULT_ENERGY | DEFAULT_QHE |
REGIME_*             | POMODORO_*
```

**Results from `src/contracts/`:**

| Pattern               | Matches | Notes                                                  |
|-----------------------|--------:|--------------------------------------------------------|
| `DEFAULT_HABIT_LAMBDA`|       0 |                                                        |
| `DEFAULT_ENERGY`      |       0 |                                                        |
| `DEFAULT_QHE`         |       0 |                                                        |
| `REGIME_*`            |       0 | `RegimeState` enum exists but contains NO `REGIME_*` constants |
| `POMODORO_*`          |       3 | All in `common.py:193-195` — `EntityType` enum labels (`POMODORO_CONFIG`, `POMODORO_ROUND`, `POMODORO_SESSION`). NOT algorithm constants — just entity-type identifiers for the data layer |

**Top-level `^DEFAULT_*` regex:** 0 matches across `src/contracts/`.

**Verdict:** 0 PAV algorithm constants in `src/contracts/`. The layer
is clean per ADR-013 (PAV kernel archived 2026-08-31).

**Bonus verification** — `QHEScore` (`metrics.py:128-195`) explicitly
out-of-scopes the algorithmic surface via two `NotImplementedError`
properties:

- `.qhe` (line 168) → formula deleted 2026-08-31 with
  `src/ikigai/core/scoring/`
- `.regime_predicted` (line 183) → FSM deleted 2026-08-31 with
  `src/ikigai/core/heuristics/`

Both reference ADR-013 in their docstrings — a positive signal that the
scope discipline is enforced at the contracts level, not only in the
drift net.

---

## §5 — Provisional Gaps Table

| ID    | Severity | File                  | Line(s) | Description                                                                                  |
|-------|----------|-----------------------|---------|----------------------------------------------------------------------------------------------|
| A.1   | LOW      | `common.py`           | 236     | `TimestampMixin.model_config = {"extra": "forbid"}` — missing `frozen=True`. By design (mixin), but drifts from the project-wide invariant. Document the exception or fold into `BasePlanContract` so all composed classes inherit `frozen=True` via MRO. |
| A.2   | LOW      | `common.py`           | 193-195 | `EntityType` enum still carries `POMODORO_*` member names. Not algorithm constants — pure type labels — but feed the vocabulary leak flagged in `2026-09-10-system-review-design.md` §0. Consider renaming or marking as `@deprecated` since the PAV/pomodoro kernel is archived. |
| A.3   | INFO     | `common.py`           | 35-43   | Docstring at `_UEID_PATTERN` still references the 5-part canonical that lives (now post-rename) at `sys_ikigai/types.py`. Path reference is stale relative to commit `685dec5`. Cosmetic; does not affect runtime regex. |
| A.4   | INFO     | `task.py`             | 68, 76  | `datetime.utcnow()` calls flagged by Ruff `DTZ003` (noqa applied). Consistent with project-wide naive-UTC convention. Not a contracts bug; flag for documentation rather than fix. |
| A.5   | INFO     | `metrics.py`          | 168-195 | `QHEScore.qhe` and `.regime_predicted` raise `NotImplementedError`. Correct per ADR-013, but callers in `sys_ikigai/` and `src/ikigai/` should be audited to ensure none of them depend on these properties. Drift net does not currently cover this consumer-side check. |

**Total provisional gaps: 5** (1 LOW, 0 MEDIUM, 0 HIGH, 0 CRITICAL,
4 INFO/L-doc).

---

## §6 — Compliance Summary

| Invariant                                | Status   | Evidence                                                |
|------------------------------------------|----------|---------------------------------------------------------|
| UEID 4-part regex (ADR-014)              | PASS     | `common.py:34` matches exactly                          |
| Pydantic v2 strict on BaseModel | 17/17 (100%)   | All direct subclasses carry `frozen=True, extra="forbid"` |
| Plan-hierarchy inheritance               | 6/6 (100%)     | All inherit `BasePlanContract.model_config`             |
| Zero PAV algorithm constants             | PASS     | 0 matches for `DEFAULT_*`, `REGIME_*`, `DEFAULT_HABIT_LAMBDA`, `DEFAULT_ENERGY`, `DEFAULT_QHE` |
| Out-of-scope markers on algorithmic API  | PASS     | `QHEScore.qhe` + `.regime_predicted` raise `NotImplementedError` per ADR-013 |

---

## §7 — Recommended Actions (for the M11 remediation plan)

| Priority | Action                                                                                                                |
|----------|-----------------------------------------------------------------------------------------------------------------------|
| LOW      | Resolve A.1 — either drop `frozen=True` from the project-wide invariant (allow mixins to compose differently) OR refactor `TimestampMixin` into a non-`BaseModel` helper that contributes fields via `Annotated`/`Field`. |
| LOW      | Resolve A.2 — rename `POMODORO_*` enum members to `TIMER_*` or document them as legacy entity-type identifiers. Reduces vocabulary leak surface (see system-review-design §0 root-cause hypothesis). |
| INFO     | Refresh A.3 docstring path reference post `sys_ikigai/` rename. Cosmetic. |
| INFO     | A.4/A.5 — no code change. Surface as audit notes for the Layer 4 (MCP gateway) and Layer 5 (v2 graph) reviews. |

**No code changes recommended for the contracts layer itself** in this
review. The layer is canonical and clean. All remediation candidates
are vocabulary or docstring refinements, not correctness fixes.

---

*Review complete. No code modified. Atomic commit of this doc pending.*