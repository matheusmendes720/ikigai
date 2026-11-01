# AGENTS.md — `src/contracts/`

**Score 9 (15 files, 99% code, own Hatchling config, 45 symbols, 38 exports, imported by 91 repo files) — created: distinct domain.** The only contract surface shared by every layer.

## OVERVIEW
Canonical Pydantic v2 models: identity, task tree, plan tree, metrics, mesh events, investigations. No logic beyond validation.

## WHERE TO LOOK
| Model | Module |
|---|---|
| `UEID`, `Period`, `Priority`, `EntityType`, `RegimeState`, `TimestampMixin` | `common.py` |
| `UEID` regex + `PaeCyclePhase` / `PlanTier` / `VectorKey` literals | `common.py` |
| `BasePlanContract` (base for the 6 plan entities) | `base.py` |
| `Sonho` `Objetivo` `Meta` `Projeto` `Entrega` `Tarefa` | `sonho.py` `objetivo.py` `meta.py` `projeto.py` `entrega.py` `tarefa.py` |
| `Task` `Subtask` `ChecklistItem` `Project` `Milestone` `Deliverable` | `task.py` |
| `TaskChange` `PropagationEvent` `TaskAction` `TaskStatus` | `task_change.py` |
| `PlanningCycle` `Wave` `Sprint` `VaultEvent` | `planning.py` |
| `Burndown` `ExecutionRate` `QHEScore` | `metrics.py` |
| `Investigation` `InvestigationStatus` | `investigation.py` |

## CONVENTIONS
- **`__all__` in `__init__.py` is grouped by domain, not alphabetical** (`common` → plan hierarchy → task → planning → metrics → investigation). The `RUF022` noqa on the assignment is deliberate — do not "fix" the ordering.
- **`TaskChange` / `TaskStatus` are deliberately NOT re-exported** from `__init__.py`; consumers import them from `src.contracts.task_change` directly to avoid a circular import surface.
- **`UEID` is a `str` subclass, not a `BaseModel`.** It carries a custom Pydantic core schema (`GetCoreSchemaHandler` / `core_schema`), so it validates as a plain string everywhere.
- **The 6 plan entities subclass `BasePlanContract`** and inherit its `frozen=True, extra="forbid"` config plus the `ikigai_vectors` non-empty validator. Each adds only its own fields.
- **`Investigation` uses `inq_id`, not a UEID** — a separate namespace, deliberately outside the plan hierarchy.
- **`TaskAction` is a `StrEnum`** with `create/update/delete/done` plus `tag_add/tag_remove/tag_clear`. `TAG_LIST` is intentionally absent (read-only, bypasses the queue).

## ANTI-PATTERNS
- **The UEID regex in `common.py` is a triple-pattern, not the 4-part form quoted in the root `AGENTS.md`.** It accepts 4-part short, 4-part long-UUID, and 5-part legacy, with namespace `{2,8}`:
  ```
  ^[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}$   (or long-uuid, or 5-part)
  ```
  Three other regexes exist elsewhere and are NOT kept in sync: `src/mesh/adapters/taskdog.py` (byte-identical copy of this one, inlined to dodge a circular import), `src/ikigai/contracts/proposal.py` (`{2,5}` 4-part), `src/ikigai/src/chat/schema.py` (`{2,10}` 4-part). Do not "unify" them — the drift tests assert each one separately.
- **`QHEScore.qhe` and `.regime_predicted` raise `NotImplementedError`** by design (ADR-013). Do not implement the formula here; the PAV kernel is archived.
- **Never re-define `UEID`, `Task`, or `TaskChange` outside this package.** `src/ikigai/contracts/proposal.py` and `src/ikigai/src/chat/schema.py` each define their own `Proposal` class with a *different* field set (`approval_state` vs `status`) — neither is the canonical `TaskChange`.
- **Never add business logic to a contract model.** `base.py` keeps `_check_vector_subset` as a *static helper* for the application layer precisely because the validator cannot reach the parent registry.

## COMMANDS
```bash
cd src/contracts && uv build        # Hatchling build
ruff check src/contracts             # uses src/contracts/pyproject.toml [tool.ruff]
```
