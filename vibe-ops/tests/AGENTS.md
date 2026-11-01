# vibe-ops/tests — Engine Test Suite

## OVERVIEW
23 test modules + 4 sub-suites covering the vibe-ops engine; self-bootstrapping
`sys.path`, run with `uv run pytest` from `vibe-ops/`.

## WHERE TO LOOK
| Area | Files | Notes |
|------|-------|-------|
| Shared fixtures | `conftest.py` | `fixture_vault`, `temp_vault`, `temp_db`, `sync_engine`, `populated_sync_engine` |
| Vault ⇄ DB sync | `test_bidirectional_sync.py`, `test_sync_code_to_vault.py` | D3 conflict resolution; "sync writes field presence, never scores" |
| Period reports | `test_period_report.py` (37 tests) | ADR-006 validators |
| Migrations | `test_migrations.py` | runs each SQL file **twice** to assert idempotency |
| Pipeline units | `test_frontmatter_parser.py`, `test_mvl_orchestrator.py`, `test_hypothesis_evaluator.py`, `test_rice_exporter.py`, `test_knowledge_telemetry.py` | pins `MODEL_MAP` = 24 entity types |
| Entity models | `test_project_entities.py`, `test_study_entities.py`, `test_hypothesis_entities.py` | Pydantic contract tests |
| Integration | `integration/test_period_sync.py`, `integration/test_conflict_resolution.py` | `TestPeriodReportSync` is marked `integration`; conflict test is a 100-iteration property check |
| Property / e2e | `property/test_period_report_properties.py` (hypothesis), `e2e/test_period_reports_full_cycle.py`, `test_full_sync_cycle.py` | both e2e files carry `@pytest.mark.e2e` |
| Fixture vault | `fixtures/vault/{2_projeto,3_indice,4_leitura,5_atomicas}` | 7 notes, **one intentionally broken**; `fixtures/README.md` expects `ingested=6, errors=1` |

## CONVENTIONS
- **Self-bootstrapping.** Every test module inserts `vibe-ops/src` into `sys.path`
  before importing (`parents[1] / "src"`), so the suite runs from any CWD.
  Post-bootstrap imports carry `# noqa: E402`.
- **Class-per-behaviour**, not flat functions: `class TestModelMapRegistry`,
  `class TestComputeRiceScore`. Test methods are `test_*` inside the class.
- **Fixtures come from `conftest.py` only** — `temp_vault` copies the fixture
  vault to `tmp_path` for mutation-safe tests; `temp_db` bootstraps a minimal
  `planning_entities` table.
- **Assertion style**: `pytest.approx` for floats,
  `pytest.raises(ValidationError)` / `pytest.raises(ValueError, match=...)` for
  validation contracts.
- **Markers**: `e2e` (2 modules) and `integration` (1 class). Filter with
  `uv run pytest -m e2e` / `-m integration`.
- **Fixture vault layout** is numerically prefixed (`2_projeto`, `3_indice`,
  `4_leitura`, `5_atomicas`) and entity ids are prefixed
  (`proj_`, `dr_`, `atom_`, `moc_`, `lit_`, `tp_`, `sp_`, `rdm_`, `ja_`).
- **Do not mutate `fixtures/vault/` in place** — use `temp_vault`; the committed
  vault is the shared baseline for the "6 ingested, 1 broken" expectation.

## ANTI-PATTERNS (THIS PROJECT)
- **Never relax an existing assertion to make a suite green.** These tests pin
  contracts (24 entity types, RICE formula, D3 merge rules).
- **Never add a fixed sleep or poll** to wait for a sync — assert on the
  observable DB/frontmatter state.
- **Never make a test depend on the developer's CWD or on a live `vibe_ops.db`** —
  use `tmp_path` and `temp_db`.
- **Do not import from the repo root's `src/contracts/`** in vibe-ops tests; the
  two contract trees are deliberately separate.

## NOTES
- `test_period_report.py` is the largest module (387 lines, 37 tests).
- `integration/test_period_sync.py` documents a known limitation: a re-run is
  skipped by id, so a changed file with the same id is not re-ingested.
- `models/period_report.py` returns `None` for **any** parse error, so a malformed
  report is indistinguishable from "not a period_report" — tests encode this.
- `tests/property/` and `tests/e2e/` carry committed `.pyc` files for CPython
  3.11/3.12/3.13; they are build junk.
