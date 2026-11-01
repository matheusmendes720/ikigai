# vibe-ops/planning — Requirements Board

## OVERVIEW
The PRD board of the vibe-ops engine: seven cluster PRDs, the Cluster-PLAN
drilldowns, and the period-report templates that the code actually validates.

## WHERE TO LOOK
| Area | Files | Notes |
|------|-------|-------|
| Cluster PRDs | `PRD-01-temporal-engine.md` … `PRD-07-ikigai-vectors.md` | each carries entities, state machines, KPIs, anti-patterns |
| Cluster-PLAN drilldowns | `CLUSTER_PLAN_BRD.md`, `CLUSTER_PLAN_DATA_MODEL.md`, `CLUSTER_PLAN_CLI_SPEC.md`, `CLUSTER_PLAN_ROADMAP.md`, `CLUSTER_PLAN_USER_STORIES.md` | the canonical CLI and schema for the PLAN cluster |
| Templates | `TEMPLATE-micro-ciclo.md`, `TEMPLATE-weekly-review.md`, `TEMPLATE-epic-sprint.md` | cognitive debt + MVK, cybernetic sensor/adjuster, epic → sprint |
| Period templates | `_templates_periodos_v2/00…08` + `RELEASE-NOTES.md` | **source of truth** for the period-report schema |
| Agent reading order | `README.md` | BRD → DATA_MODEL → CLI_SPEC → implement Sprint 1 |
| Workspace snapshot | `CHECKPOINT-2026-06-07-pre-development.md` | dated, see NOTES |

## CONVENTIONS
- **Agent reading order is explicit** in `README.md`: implement Cluster PLAN →
  read `CLUSTER_PLAN_BRD.md` → `CLUSTER_PLAN_DATA_MODEL.md` →
  `CLUSTER_PLAN_CLI_SPEC.md`; architect → `architecture/ADR-001` + `ADR-002` +
  `ADR-005`.
- **The period-report templates are the live contract.** `_templates_periodos_v2/`
  frontmatter (`type: period_report`, `entity_type: period_report`, `period`,
  `template_version`, `ikigai_cluster`, `date_start`, `date_end`, `sonho_id`,
  `ikigai_vector`, `xp_gained`, `mastery_delta`, `verdict`, `verdict_score`,
  `policy_recommendation`, `parent_period`, `status`, `tags`) is exactly what
  `../src/models/period_report.py` validates and what
  `../src/middleware/period_sync.py` syncs into the `period_reports` table.
- **Verdict enums are per-period**, from ADR-006: daily / weekly / quarterly →
  `PASS|PARTIAL|FAIL`; onda → `CONTINUE_WAVE|CORRECT_TRAJECTORY|KILL_WAVE`;
  sonho → `ACTIVE|VALIDATED|FALSIFIED|PIVOTED|ABANDONED`.
- **The templates folder is the source of truth**; the vault mirror
  (`notas_estudo/_templates_periodos/`) is a copy, synced bidirectionally —
  vault edits require a re-sync.
- **CLI conventions** (`CLUSTER_PLAN_CLI_SPEC.md` §2): every command accepts
  `--json`; ISO-8601 dates; `HH:MM` 24h; durations in integer minutes; colour
  legend 🟢 3–5h / 🟡 5–6h / 🔴 6h+; idempotency enforced by UNIQUE
  constraints, so a re-run **updates** instead of duplicating.
- **Append-only**: new discoveries are appended, nothing is rewritten
  (PRD-01…03 carry an explicit "Regra Append-Only").
- **Docs are Brazilian Portuguese; identifiers and keywords are English.**

## ANTI-PATTERNS (THIS PROJECT)
- **Never hand-write a wave/cycle reference** — `W[N]_Mmm_YYYY` / `Q[1-4]_YYYY`
  are foreign keys, not free text.
- **Never log a streak without the matching daily log** (artificial inflation);
  `habit_level` must come from H(t), never hardcoded, and `weight_in_qhe` must
  not sum above 1.0 across habits.
- **Never let a cycle exist without a valid parent phase**, and never move an
  entity to `completed` without a completed `WAVE_END` ReviewEvent.
- **Never use naive regex to parse frontmatter** — use a real YAML/AST parser
  (`doc/01.5-data-contracts-and-pipelines.md`).
- **No LLM, no embeddings, no interactive charts** in the cluster-plan pipelines.

## NOTES
- **`CHECKPOINT-2026-06-07-pre-development.md` is stale**: it claims the repo root
  lacks `pyproject.toml`/`pytest.ini` (both exist) and points at
  `vibe-ops/src/models/pav_entities.py` and `tests/unit/test_pav_*.py`, which do
  not exist. Read it as history, not as truth.
- The `prd-*.md` files in `../specs/` are ~1.4 KB mirrors of the PRDs here, with
  no sync mechanism — edit the canonical copy in this directory.
- Several cross-links point outside the repo (`../../ARCHITECTURE_INDEX.md`,
  `../../CLUSTER_PLAN.md`, `../../life-ops/planner/…`) and are broken.
