# src/contracts/ — Canonical Pydantic v2 Contracts

**Score:** 14 (15 files, 99% code, 222 symbols, 40 exports, 91 import sites)
**Role:** the single source of truth for every cross-layer model in the OS.

## OVERVIEW

The only models shared between vault, agent, mesh and interface layers. Pure
data containers with invariants — no business logic. Every model is
`frozen=True, extra="forbid"`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Identity + time | `common.py` | `UEID`, `Period`, `Priority`, `EntityType`, `RegimeState`, `TimestampMixin` |
| UEID validation | `common.py` | `UEID.__new__` raises on a non-matching id; `from_legacy` converts `type_slug` |
| 6-level plan hierarchy | `base.py` | `BasePlanContract` + `sonho/objetivo/meta/projeto/entrega/tarefa.py` |
| Mesh event models | `task_change.py` | `TaskChange`, `PropagationEvent`, `TaskAction`, `TaskStatus` |
| Task tree | `task.py` | `Task`, `Subtask`, `ChecklistItem`, `Project`, `Milestone`, `Deliverable` |
| Planning cycles | `planning.py` | `PlanningCycle`, `Wave`, `Sprint`, `VaultEvent` |
| Feedback metrics | `metrics.py` | `Burndown`, `ExecutionRate`, `QHEScore` |
| Investigation queue | `investigation.py` | `inq_id` is a separate namespace from `UEID` |

## CONVENTIONS

- `UEID` is a `str` subclass with a custom Pydantic core schema, so it validates
  at the field boundary instead of at construction.
- `BasePlanContract` enforces `ikigai_vectors` non-empty. The parent-subset rule
  is checked by `_check_vector_subset` at the application layer, not by the
  validator — the validator cannot resolve the parent without a registry.
- `__all__` in `__init__.py` is grouped by domain, not alphabetical; the
  `RUF022` suppression is intentional and documented in-file.
- `TaskChange` and `TaskStatus` are deliberately **not** re-exported from
  `__init__.py` — importing them from there creates a circular import surface.
- `TimestampMixin` uses `extra="forbid"` but not `frozen=True`; it is the one
  model in the package that is mutable.
- `investigation.py` and `planning.py` use naive local `datetime.now()` for
  defaults; the rest of the package uses UTC.

## ANTI-PATTERNS

- Never redefine `UEID`, `Task`, `TaskChange` or any other shared model locally.
  A local duplicate is a drift bug — import from here instead.
- Never relax `frozen=True` / `extra="forbid"`. ADR-009 makes strict mode an
  invariant, not a style preference.
- Do not import `TaskChange` from `src.contracts` (the package root); import it
  from `src.contracts.task_change` directly.
- Do not add business logic to a contract. Invariants only.
- Do not assume the 5-part UEID format is canonical. ADR-014 (ACCEPTED
  2026-09-04) reversed the 5-part decision: **4-part is canonical**, and the
  regex in this file wins. The `_UEID_PATTERN` here is a widened triple-pattern
  (4-part short | 4-part long-UUID | 5-part legacy) — the extra branches exist
  for production fixtures, not as a promotion of the 5-part form.
  `src/ikigai/tests/test_canonical_scope.py::test_ueid_canonical_regex_enforced`
  guards this.
- `__init__.py`'s docstring still lists `src/operational/` as a consumer. That
  tree was archived to `archive/legacy-pav/src-operational/` — the reference is
  stale.
