# Matheus Mendes — IKIGAi Persona Vault

> **Production-bound dataset.** This is the real Matheus Mendes persona. The `src/ikigai/`
> Pydantic code reads this folder on the `--vault` flag once data-first methodology unblocks
> (5+ SONHO logs — currently at 1/5).
>
> **NOT to be confused with** `.omo/ikigai/mock-datasets/` (Marina Souza), which is a
> **meta-model** for template exploration only — Marina is structurally decoupled from
> production reads.

---

## Persona

- **Name**: Matheus Mendes
- **Location**: Salvador, Bahia, Brasil (UTC-3)
- **Target**: 100% remote Data / AI / BI / Analytics / ML / Dev-Tools roles
- **Stack**: Python, Polars, SQL
- **Salary floor**: "tanto faz para primeira vaga" — floor only activates after first role
- **Weekly budget**: 40+ h/semana (defined per-week in SEMANA entities)
- **Mode**: hybrid Salvador fallback only

## Runtime layer

The `.runtime/` sibling directory holds **derived, throwaway state** rebuilt from
the markdown vault by the planning agent. Currently it contains:

- `solverforge/calendar.db` — solverforge-calendar SQLite (rendered time slots)
- WAL files (`calendar.db-wal`, `calendar.db-shm`)

The DB location is set via `SOLVERFORGE_DATA_DIR` (consumed by the Rust binary,
the `solverforge` CLI wrapper, and the `solverforge-calendar` MCP server). All
DBs (`*.db`) are gitignored at the `life/` root — see `life/.gitignore` line 38.
This folder has its own `.gitignore` so it remains self-documenting when the
parent exclusion is reorganised.

## Purpose

- Source of truth for SONHO / TRIMESTRE / ONDA / SEMANA / DIA entities tied to Matheus
- Lives in git, versioned + auditable
- The handoff file at `.omo/ikigai/meta/session-handoff-2026-07-03.md` is the bootstrap log
- The continuation file at `life-ops/ikigai/2026-07-05-024447-*.txt` captures session-by-session
  decisions and Open-Socratic questions

## Conventions

- **Flat layout** matches `MarkdownDB._dir_for()` (no nested `dreams/2026/Q3/*.md`).
- **YAML frontmatter** must round-trip through `PlanEntity.from_frontmatter_dict()` —
  Pydantic v2 strict (`frozen=True`, `extra="forbid"`).
- **UEID format**: `ikigai:<entity_type>:<slug>:<8-hex uuid>:<8-hex content_hash>`.
  Placeholders regenerate when `MarkdownDB.write()` lands (post-5+ SONHO).
- **Vector weights**: equal (P=S=M=R=C=0.20) per Option C deferral until 5+ SONHO logs.
  See `.omo/ikigai/meta/perspective-log-2026-07-03.md` for the 3 options + migration paths.
- **`_intent_vector`**: informal annotation in `custom:` field, NOT schema — tracks which
  vector dominates the SONHO (revenue for this persona).

## Hierarchy & Resolution

```
DREAM (5-10y, 1825-3650d, now also 547d for SONHO real)
  └── OBJECTIVE / TRIMESTRE (3-12m, 90-365d)
        └── PROJECT / ONDA (1-6m, 30-180d)
              └── DELIVERABLE (1-30d)
                    └── TASK (1-7d)
```

The central SONHO "vaga-remota-2026" is a DREAM with horizon_days=547 (≈18 months)
deliberately bucketed at the lower end of the DREAM range to reflect the persona's
"primeira vaga até Dez/2026" intent without inflating to a 5-year horizon.

## Data-first methodology

No new code in `src/ikigai/` until 5+ SONHO logs are captured by hand. This persona is
log #1. Reference: `.omo/ikigai/meta/data-first-methodology.md`.

## Files in this vault

| File | Entity | Horizon | Status |
|------|--------|---------|--------|
| `dreams/vaga-remota-2026.md` | DREAM / SONHO | 547d | seed |
| `objectives/q3-2026-primeira-vaga.md` | OBJECTIVE / TRIMESTRE | 90d | planned |
| `projects/onda-q3-1-pipeline-bi-cold-outreach.md` | PROJECT / ONDA | 30d (15wd bucket) | **active** |
| `deliverables/byd-process-tracker.md` | DELIVERABLE / D4 | 7d | in_progress |
| `deliverables/byd-d1-outputs/byd-stack-fit-matrix.md` | DELIVERABLE / D1 | done |
| `deliverables/byd-d2-outputs/byd-econometric-vulnerability.ipynb` | DELIVERABLE / D2 | done |
| `deliverables/byd-d3-outputs/byd-cold-outreach-assets.md` | DELIVERABLE / D3 | done |
| `ikigai_state/profile-2026-07-03.json` | profile snapshot | 547d | active |

## Meta-model

For structural template exploration without touching production data, see
`.omo/ikigai/mock-datasets/` (Marina Souza). Do not commit Matheus persona data there —
Marina is a meta-model only.

---

*Bootstrap date: 2026-07-03 · Owner: Matheus Mendes · Code review: post-5+ SONHO logs*