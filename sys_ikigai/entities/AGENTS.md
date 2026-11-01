# sys_ikigai/entities

Legacy entity model family (plan / profile / regime / skill / vector) plus the
`plan/` shims that alias the canonical contracts. Earns its file: distinct
domain (entity layer), complexity score 11, 27 importing files.

## OVERVIEW
`PlanEntity` and its subclasses are the pre-`src/contracts` models. `plan/*`
re-exports canonical `src.contracts` classes under legacy names.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Base plan model | `base.py` | `PlanEntity` |
| Identifier | `ueid.py` | delegates to `src.contracts.common._UEID_PATTERN` |
| Scored value + unit | `score_value.py` | `ScoreValue` / `ScoreUnit` |
| Persisted record | `ikigai_record.py` | `IKIGAiRecord` |
| Profile / regime / skill / vector | `profile.py`, `regime.py`, `skill.py`, `vector.py` | |
| Opportunity, corrections, drift, overrides, snapshots | `opportunity.py`, `correction_signal.py`, `drift_state.py`, `override.py`, `phase_snapshot.py`, `fractal_regime.py` | small single-purpose models |
| Canonical aliases | `plan/` | `Task` -> `Tarefa`, `Project` -> `Projeto` |

## CONVENTIONS
- `PlanEntity` deliberately differs from the canonical contracts: mutable,
  assignment-validated, `extra="allow"` for forward compatibility. Do not
  "fix" it to match the frozen models.
- `entities/ueid.py` imports the pattern from `src.contracts.common`
  (ADR-033, single source of truth) and still validates legacy 5-part IDs so
  old fixtures keep working.
- `plan/*.py` are one-line backward-compat shims marked `# noqa: F401`; each
  module docstring points at the canonical contract it aliases.
- The package `__init__.py` re-exports an explicit `__all__` — extend it when
  adding a public model.

## ANTI-PATTERNS
- New shared models go to `src/contracts/`, not here.
- `sys_ikigai/types.py` holds a LEGACY 5-part `UEID`; `PlanEntity` uses it
  while `IKIGAiRecord` uses the canonical 4-part one. Do not pass an ID
  between the two families without validating it.
- `plan/project.py` maps `Project` to `src.contracts.Projeto`, which is a
  different contract from `src.contracts.task.Project` — the two are
  deliberately distinct.
- `propagation/markdown_db.py::MarkdownDB.read` imports `DreamEntity`,
  `GoalEntity`, `ObjectiveEntity`, `ProjectEntity`, `TaskEntity` and
  `DeliverableEntity` from these `plan/` modules, but the shims export only
  the short names. The call raises `ImportError` today (verified). Use
  `PlanEntity`, or fix the names before relying on it.
- `entities/plan/` must not grow real models — it stays a shim layer.
- `sys_ikigai/entities/__init__.py` exports the short alias names
  (`Deliverable`, `Dream`, `Goal`, ...); the `*Entity` names exist nowhere.

## COMMANDS
```bash
python -m pytest src/ikigai/tests/test_ueid_validator.py src/ikigai/tests/test_score_value.py -v
```
