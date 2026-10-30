# vibe-ops/tests — pytest suite

## OVERVIEW
Standalone pytest suite for the cybernetic engine — fixture vault, sync cycles, period reports.

16 top-level modules plus `e2e/`, `integration/`, `property/`. Imports resolve by
inserting `vibe-ops/src` into `sys.path`; this package has no pytest ini options.

## WHERE TO LOOK
| Need | Fixture / file |
|------|----------------|
| Canonical 7-file test vault | `tests/fixtures/vault/` (`2_projeto`, `3_indice`, `4_leitura`, `5_atomicas`) |
| Mutable vault copy | `temp_vault` — copies the fixture vault into `tmp_path` |
| Bootstrapped SQLite | `temp_db` — creates the `planning_entities` table |
| Sync engine under test | `sync_engine`, `populated_sync_engine` |
| Vault↔code cycle | `test_full_sync_cycle.py`, `test_sync_code_to_vault.py`, `test_bidirectional_sync.py` |
| Period reports | `test_period_report.py`, `integration/test_period_sync.py`, `e2e/test_period_reports_full_cycle.py` |
| Conflicts | `integration/test_conflict_resolution.py` |
| Property-based | `property/test_period_report_properties.py` (hypothesis) |
| Schema application | `test_migrations.py` |

## CONVENTIONS
- **Fixtures live in `tests/conftest.py`** — add new ones there, not in a module-local copy.
- **The `sys.path` insert is repeated per module**: 16 test modules repeat the same idiom —
  `VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"` then
  `sys.path.insert(0, str(VIBE_OPS_SRC))` — before importing `models.*` / `middleware.*`
  (`conftest.py` does the same). Those imports sit below the insert, hence the `# noqa: E402`
  markers.
- **One exception**: `test_mvl_orchestrator.py` imports `from src.pipeline...` /
  `from src.storage...`, a style no other test uses — don't copy it.
- Tests operate on `tmp_path` copies; the committed fixture vault is read-only input.
- The suite runs with `uv run pytest` from `vibe-ops/`; `hypothesis` comes from the dev
  dependency group.

## ANTI-PATTERNS
- Never write to the real vault or to `data/` from a test — use `temp_vault` / `temp_db`.
- Never silence a failure with `warnings.simplefilter("always")` the way
  `test_period_report.py` does — assert the behaviour instead.
- Do not add fixtures that depend on the repo-root `pytest.ini`; this suite is standalone.
- Do not commit `*.db` artifacts from a local run into `vibe-ops/` — the tree already carries
  `test_vibe.db` / `vibe_ops_test.db`, keep new ones out.
