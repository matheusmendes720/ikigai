# vibe-ops/specs — Specs-First Contracts

## OVERVIEW
The declarative contract layer: model schemas, frontmatter contracts and
cluster-plan pipeline specs, written **before** the code that implements them.

## WHERE TO LOOK
| Contract | File | Status |
|---|---|---|
| Pydantic models (canonical) | `schema-pydantic-models-v2.md` | 🟢 current — 15 models + 6 enums |
| Pydantic models (v1) | `schema-pydantic-models.md` | ⚪ deprecated |
| Frontmatter contract (canonical) | `schema-frontmatter-contract-v2.md` | 🟢 current |
| Frontmatter contract (v1) | `schema-frontmatter-contract.md` | ⚪ deprecated |
| Planner extension (living spec) | `schema-planner-extension.md` | 🟢 1904 lines — the largest artifact here |
| Cluster-plan pipeline spec | `spec-cluster-plan-pipelines.md` | 🟢 |
| Cluster-plan inputs / reports | `spec-cluster-plan-inputs.md`, `spec-cluster-plan-reports.md` | 🟢 |
| Epistemic mesh | `SPEC-05-cybernetic-epistemic-mesh.md` | 🟢 Hybrid RAG architecture |
| PRD mirrors | `prd-*.md` (7 files, ~1.4 KB each) | 🟢 short pointers to `../planning/PRD-0N-*.md` |

## CONVENTIONS
- **Specs-First is mandatory** (`README.md`): write the spec → mirror the
  requirement into `../planning/PRD-*.md` → mirror the contract into
  `../contracts/*.yaml` → implement code that references the spec → add tests
  that validate the spec. Specs precede code.
- **The version suffix is a lifecycle marker, not decoration**: `-v1` = deprecated
  (kept on disk, flagged in `README.md`), `-v2` = current, then SemVer
  (`-v2.1`, `-v3`). Deprecation is declared in the README table only — the v1
  files themselves carry no notice.
- **Append-only inside the documents.** `schema-planner-extension.md` is a living
  spec updated in place and reflected in `CHANGELOG.md`; the v2 schemas declare
  themselves an "append-only extension of v1".
- **Frontmatter is a hard contract**: `entity_type`, `id` and `status` are always
  mandatory; `status: active` = processed, `archived` = ignored. A note without
  frontmatter is ignored by the pipeline.
- **Computed fields are never hand-written** — `tw_project_key`, `c_comp`, `ic`,
  `total_target_hours`, `wave_count`, `completion_pct`, `streak_current` are
  pipeline-generated.
- **Pydantic v2 idioms only**: `field_validator`, `Field(ge=, le=, pattern=)`,
  `class X(str, Enum)`.
- **Docs are Brazilian Portuguese; identifiers and keywords are English.**
- **Naming split by role**: hyphen-lowercase for specs (`spec-*`, `prd-*`,
  `schema-*`), UPPER_SNAKE for planning artefacts (`CLUSTER_PLAN_*`, `PRD-0N-*`).
- **Specs are contracts, not imports** — the models inside the fenced code blocks
  are declarations; the running code lives in `../src/models/`.

## ANTI-PATTERNS (THIS PROJECT)
- **Never implement from a deprecated `-v1` spec.** Use the `-v2` file.
- **Never hand-edit a pipeline-computed field** in an example frontmatter block.
- **Never use a free-text wave/cycle reference** (`wave: "semana 3 de fev"`) —
  waves and cycles are foreign keys (`W3_Jul_2026`).
- **Never let two entities of the same type be `active` simultaneously**, and
  never skip a `ReviewEvent` without marking it `skipped`.
- **No LLM, no embeddings, no NLP in the cluster-plan pipelines** — arithmetic
  and SQLite queries only.

## NOTES
- **Two conflicting UEID definitions live here.** `SPEC-05-cybernetic-epistemic-mesh.md`
  §4 declares a **3-part** `<CLUSTER>:<ENTITY>:<ID>` id, matching
  `../src/storage/ueid.py`; the repo canonical UEID (ADR-014) is **4-part**.
- **Four entity models are declared twice** with near-disjoint fields —
  `WaveEntity`, `CycleEntity`, `PhaseEntity`, `HabitEntity` appear in both
  `schema-pydantic-models-v2.md` and `schema-planner-extension.md`, with different
  field names (`started`/`expected_end` vs `start_date`/`end_date`). Resolve
  before implementing either.
- ~27 % of the intra-doc markdown links are broken, mostly the `../../life-ops/…`
  tree and `../../ARCHITECTURE_INDEX.md`; from `specs/`, `../PRD-02-…` should be
  `../planning/PRD-02-…`.
- `.$concept_sys-archy.drawio.bkp` is a stale draw.io editor backup beside the
  live `concept_sys-archy.drawio` — dead weight, not a source.
