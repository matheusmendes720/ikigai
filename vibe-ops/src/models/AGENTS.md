# src/models — entity contracts (42 public names)

## OVERVIEW
Vault-shaped entity contracts — deliberately lenient pydantic so user-authored frontmatter survives validation.

Pydantic v2 shapes mirrored from vault frontmatter: dreams, hypotheses, projects, studies,
habits, metrics, period reports, policies. Imported as `from models.X import Y`.

## WHERE TO LOOK
| Domain | Module | Entities |
|--------|--------|----------|
| Dreams | `dream_entities.py` | `Dream` (`dr_*` id pattern) |
| Hypotheses | `hypothesis_entities.py` | `FalsifiableHypothesis`, `HypothesisEvaluation` (`fh_*`) |
| Projects | `project_entities.py` | `Project`, `BacklogTask`, `RoadmapItem`, `ChangelogEntry`, `Skill` (`proj_*`) |
| Studies | `study_entities.py` | `StudyProject`, `StudyTopic`, `StudyMaterial`, `StudySession`, `StudyNoteIndex` (`sp_*`) |
| Period reports | `period_report.py` | `PeriodReport`, `PeriodReportParser`, `PeriodSyncStats` (ADR-006) |
| Policies | `policy_entities.py` | `PolicyDecision`, `DecisionRecord`, `ReviewEvent`, `TimeBlock` |
| Ops / health | `operational_entities.py`, `health_entities.py`, `metric_entities.py` | `OperationalMode`, `PolicyRule`, `DailyLog`, `DailyConsolidation`, `WeeklyAggregate`, `DailyMetrics`, `SleepRecord` |
| IKIGAI | `ikigai_entities.py` | `IKIGAiProfile`, `SkillNode`, `OpportunitySignal` |
| RAG | `rag_entities.py` | `RAGIndex` over `SQLIndex` / `VectorIndex` / `GraphIndex` |
| Docs / contracts | `doc_entities.py`, `contracts.py` | `DocBackend`, `DocFrontend`, `DataContract`, `StudyNoteContract` |

## CONVENTIONS
- **Deliberately lenient**: `dream_entities`, `hypothesis_entities`, `project_entities`,
  `study_entities` and `period_report` use `extra="allow"`; **no model in this package uses
  `extra="forbid"`**, and `PeriodReport` is explicitly `frozen=False`. Vault frontmatter
  carries user-authored keys that must survive validation (`period_report.py` docstring).
- **Id prefixes are regex-enforced** (`^dr_`, `^fh_`, `^proj_`, `^sp_`) — they are part of
  the vault contract; keep them when adding fields.
- **Absolute sibling imports** (`from models.x import Y`) and `from __future__ import annotations`.
- `__init__.py` re-exports 42 names through `__all__` — extend it when adding a public entity.

## ANTI-PATTERNS
- Do not tighten these models to `extra="forbid"` / `frozen=True` to match the repo-wide
  contract rule in `src/contracts/` — the divergence is intentional here.
- Do not rename entity ids or drop the `id` pattern; the sync layer keys on them.
- `policy_entities.PolicyDecision` duplicates `schemas.pydantic_v2.PolicyDecision` — use the
  `models/` one for vault-shaped payloads, the `schemas/` one for DB payloads, and never mix
  them in one signature.
- `PeriodSyncStats` is `frozen=True` while `PeriodReport` is not; do not assume the whole
  module shares one config.
