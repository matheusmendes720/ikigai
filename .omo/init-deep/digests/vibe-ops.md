# DIGEST — vibe-ops subtree

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `vibe-ops/AGENTS.md` | 15 | Subtree root — engine, storage, contracts, and operating conventions |
| `vibe-ops/planning/AGENTS.md` | 10 | Requirements board and live period-report templates |
| `vibe-ops/src/AGENTS.md` | 16 | Flat import root; model, storage, sync, and CLI facades |
| `vibe-ops/src/pipeline/AGENTS.md` | 14 | Ingest/validate/enrich/index kernel and policy adjuster |
| `vibe-ops/tests/AGENTS.md` | 12 | Self-bootstrapping pytest suite and fixture contracts |

Scores: Symbols/exports use Python AST plus fenced Python in contract docs; references are other tracked files containing the location path; code ratio counts source files.
`vibe-ops/` = 3 (232 files >20) + 2 (14 subdirs >5) + 1 (`pyproject.toml`/`uv.lock`) + 2 (`__init__.py`) + 2 (1,573 symbols) + 2 (327 exports) + 3 (211 references) = 15; code 120/232=51.7%, +0.
`vibe-ops/planning/` = 3 (28 files >20) + 2 (81 fenced symbols) + 2 (75 public fenced exports) + 3 (69 references) = 10; code 0/28, +0.
`vibe-ops/src/` = 3 (86 files >20) + 2 (13 subdirs >5) + 2 (81/86=94.2% code) + 2 (`__init__.py`) + 2 (353 symbols) + 2 (69 exports) + 3 (114 references) = 16.
`vibe-ops/src/pipeline/` = 3 (33 files >20) + 2 (32/33=97.0% code) + 2 (`__init__.py`) + 2 (137 symbols) + 2 (14 exports) + 3 (53 references) = 14.
`vibe-ops/tests/` = 3 (32 files >20) + 2 (23/32=71.9% code) + 2 (`__init__.py`) + 2 (350 symbols) + 3 (29 references) = 12; exports 0, +0.
The four 8-15 locations are distinct domains; `vibe-ops/src/` exceeds 15.

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `vibe-ops/specs/` | 7 | `vibe-ops/AGENTS.md` — contract/version entry points |
| `vibe-ops/scripts/` | 4 | `vibe-ops/AGENTS.md` — operator scripts and search entry point |
| `vibe-ops/contracts/` | 0 | `vibe-ops/AGENTS.md` — JSON Schema contract inventory |
| `vibe-ops/base/` | 7 | `vibe-ops/AGENTS.md` — canonical concept source |
| `vibe-ops/migrations/` | 4 | `vibe-ops/AGENTS.md` — migration and DB-DDL map |
| `vibe-ops/schema_registry/` | 0 | `vibe-ops/AGENTS.md` — registry ownership |
| `vibe-ops/artifacts/` | 0 | `vibe-ops/AGENTS.md` — knowledge artifacts map |
| `vibe-ops/doc/` | 0 | `vibe-ops/AGENTS.md` — strategy-document map |
| `vibe-ops/vectors/` | 0 | `vibe-ops/AGENTS.md` — IKIGAI-vector map |
| `vibe-ops/context/` | 4 | `vibe-ops/AGENTS.md` — research/MOC map |
| `vibe-ops/architecture/` | 3 | `vibe-ops/AGENTS.md` — ADR reading order |

Skipped arithmetic: `specs` 2+2+3=7; `architecture` 3; `base` 7; `context` 4; `migrations` 4; `scripts` 4; `artifacts`/`contracts`/`doc`/`schema_registry`/`vectors` 0.

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **Canonical tracked scope and engine anchor.** `git ls-files -- vibe-ops/vibeops-tui` returns zero: that path is absent from the canonical tracked tree. The sole tracked cybernetics module is `vibe-ops/src/cybernetics/engine.py`.
2. **The live loop is distributed, not a six-stage engine call chain.** `engine.py` defines `KnowledgeNode`, `BinaryKnowledgeTree`, `GapSearchEngine`, and `get_engine`; it contains no `TARGET`/`SENSOR`/`ADJUSTER`/`PERSIST`/`SYNC`/`INDEX` sequence. The live roles are split across `vibe-ops/src/pipeline/gap_engine.py` (sensor), `vibe-ops/src/pipeline/policy_engine.py` (adjuster), `vibe-ops/src/pipeline/mvl_orchestrator.py` (SQLite persist plus Chroma index), and `vibe-ops/src/middleware/bidirectional_sync.py` (vault sync). Thus `Target -> Sensor -> Adjuster -> Persist -> Sync -> Index` is architectural wording, not a callable sequence in `engine.py`.
3. **Policy adjuster has four operational states.** `PolicyEngine.POLICY_MAP` and `PolicyEngine.evaluate()` use `PUSH`, `MAINTAIN`, `REDUCE`, and `RECOVER`; escalation to `PUSH` requires `MAINTAIN` plus `days_in_policy >= 3`. `vibe-ops/src/schemas/pydantic_v2.py` also retains the legacy enum alias `RECOVERY`.
4. **Persistence and vector indexing use SQLite and Chroma.** `vibe-ops/src/storage/sqlite_adapter.py` initializes `vibe-ops/src/storage/schema.sql`; `vibe-ops/src/storage/chroma_adapter.py` uses `chromadb.PersistentClient`; `DataMeshAdapter.sync_entity()` writes SQLite and then upserts Chroma.
5. **Planning authority and current test scale.** The canonical temporal document is `src/life_tatics/time-lenghts_reviews.md` (1,583 lines; `rho=11/15`, `WAVE=15D=11W`, `CYCLE=45D=33W`, `PHASE=180D=132W`); `src/planner/time-lenghts_reviews.md` is the earlier 1,172-line variant. The live `vibe-ops` pytest suite collects 801 tests.

## VERIFICATION

- Measured at live HEAD `2ae8478dd49d03d145149e086439283e90e68b79`; the briefing's `8c983626` is not current HEAD.
- `git ls-files -- vibe-ops` returned 232 files; per-location counts were 232/28/20/86/33/32 for root/planning/specs/src/pipeline/tests.
- `git ls-files -- vibe-ops/vibeops-tui` returned no tracked files (canonical absence).
- Live reads of `engine.py`, `policy_engine.py`, `pydantic_v2.py`, both storage adapters, `mvl_orchestrator.py`, and `bidirectional_sync.py` verified the anchors above; `git grep` found no uppercase six-stage sequence in `engine.py`.
- `vibe-ops/.venv/Scripts/python.exe -m pytest --collect-only -q -p no:cacheprovider` exited 0: 801 tests collected.
- Every path named above was checked against the live tree.
