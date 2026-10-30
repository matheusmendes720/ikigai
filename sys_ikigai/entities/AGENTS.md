# AGENTS.md — `sys_ikigai/entities`

> Earned its file: score 11/20 — distinct domain (the Pydantic model layer of the kernel).
> Parent: `sys_ikigai/AGENTS.md`. Scope: this directory only.

## OVERVIEW

Pydantic v2 models for the whole kernel: two polymorphic roots plus specialised records for
regime, vector, skill, profile, opportunity, overrides and drift state. 15 modules, ~1.1k LOC.

## WHERE TO LOOK

| File | Role |
|------|------|
| `base.py` | `PlanEntity` — polymorphic base for Dream→Deliverable. Discriminator `entity_type`; `extra="allow"`, `frozen=False`, plus a forward-compat `custom` dict. |
| `ikigai_record.py` | `IKIGAiRecord` — canonical single root (SPEC D6). Discriminated union on `entity_type`; also defines `EntityType` and `StatusType`. |
| `ueid.py` | UEID validator; re-exports `_UEID_PATTERN` from `src/contracts/common.py` (ADR-033 — single source of truth). Accepts the 4-part canonical form **and** legacy 5-part. |
| `score_value.py` | `ScoreValue` + `ScoreUnit` (`PERCENT` ∈ [0,100], `RATIO` ∈ [0,1]) so 0-100 / 0-1 / RICE scales cannot be confused. |
| `vector.py` | `IKIGAiVectorEntity`, `VectorScorePoint`, `VectorTrend`. |
| `regime.py` | Fractal regime hierarchy (Global → Cluster → Vector → SubVector): `RegimeGraph`, `RegimeOverride`, `RegimeOverrideAudit`. |
| `profile.py` | `IKIGAiProfile`, `ProfileSnapshot`. |
| `skill.py` | `SkillNode`, `SkillCategory`, `SkillLevel`. |
| `opportunity.py` | `OpportunitySignal`, `OpportunityStatus`. |
| `override.py`, `phase_snapshot.py`, `drift_state.py`, `fractal_regime.py`, `correction_signal.py` | Override records, phase snapshots, drift state, fractal regime state, correction signals. |
| `plan/` | **Deprecated.** 6 one-line shims re-exporting `src.contracts` (`Task` → `Tarefa`). |

## CONVENTIONS (deviations from parent)

- **Two config modes.** The two polymorphic roots use `extra="allow"`, `frozen=False` for forward
  compatibility; every other model here uses `frozen=True, extra="forbid"`.
- `entities/__init__.py` is a re-export façade with 21 public names.
- Enums live in the package `enums.py` when shared across domains, and next to their model when
  domain-local (`EntityType`/`StatusType` in `ikigai_record.py`, `ScoreUnit` in `score_value.py`).

## ANTI-PATTERNS

- **Never extend `entities/plan/*`.** Those are backward-compat shims over `src.contracts`;
  new code imports `src.contracts` directly.
- **Do not redefine `UEID` here.** `entities/ueid.py` only re-exports the canonical pattern; the
  4-part format is owned by `src/contracts/common.py` (ADR-014 / ADR-033).
- **Do not add `extra="allow"` to a new model** — only the two polymorphic roots may carry
  unknown fields.
- Never introduce scoring/PAV math in this layer — the agent is planner-only (ADR-013).

## COMMANDS

```bash
python -c "from sys_ikigai.entities import PlanEntity, IKIGAiRecord; print(PlanEntity.model_config)"
```
