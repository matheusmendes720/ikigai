# AGENTS.md — `src/ikigai/tests/`

**Earned its file:** score 12 — 60 tracked files, 5 sub-packages, ~14.5k LOC, the canonical
drift net. Distinct domain: guard tests (surface invariants) + layer tests (behaviour).

## OVERVIEW

The canonical suite for ADR-037: top-level guards that decide *what the branch publishes*, plus
four area packages that exercise each published layer's behaviour.

## STRUCTURE

```text
tests/
├── conftest.py                 # load-bearing: sys.path, event loop, asyncio mode, collect_ignore
├── test_*.py (17)              # guards: published surface, canonical scope, drift invariants
├── transport/ (18 files)       # bot / ws / mcp surface behaviour
├── store/ (14 files)           # real Postgres via testcontainers
├── services/ (6 files)         # domain rules against in-memory doubles
├── contracts/ (4 files)        # Pydantic DOM contract + kind drift
└── skills/                     # package marker only — its docstring still names the retired M161 skills
```

## WHERE TO LOOK

| Task | Location |
|---|---|
| Which trees the branch publishes | `tests/test_canonical_scope.py` (649 LOC) |
| Six-tool surface, layering, one UEID, revision/idempotency | `tests/test_drift_invariants.py` |
| Compose / image / workflow shape | `tests/test_deployment_surface.py` (1171 LOC) |
| Import-root closure over every tracked file | `tests/test_published_surface_integrity.py` |
| Write envelope, conflict, idempotency | `tests/services/test_artifacts_service.py` |
| Vault write-back properties (ADR-043) | `tests/services/test_vault_write_back.py` |
| Revision guard, FTS ordering, `.down.sql` per migration | `tests/store/test_store_schema.py` |
| Transport carries no SQL/policy | `tests/transport/test_mcp_tools.py` |

## CONVENTIONS

- **Guards read the TRACKED file set** (`git ls-files`, `git grep`), never the filesystem — the
  retired runtime stays on the owner's disk, so a filesystem check passes locally and fails in a
  clone.
- **Two import spellings are live**: `from src.contracts.dom import ...` (repo root on the path)
  and `from strategics.loader import ...` (`src/ikigai/src/` on it). `conftest.py` guarantees both.
- **Test names are prose sentences** (`test_the_retired_runtime_is_neither_published_nor_deleted`),
  not `test_<thing>_<case>`; file names carry the area (`test_<area>_<subject>.py`).
- **Docstrings name the SPEC/ADR the test enforces** (`SPEC-01 T1.5`, `ADR-011`, `ADR-043`) and say
  why the test exists, not what it does.
- **A real server over a double when the wire is the contract** (`transport/test_bot_harness.py`,
  `transport/test_ws_wire.py`); doubles are local classes implementing the service interface,
  injected via `transport.set_services(...)` and reset in `finally`.
- **A real Postgres over a double for the store** — `PostgresContainer("pgvector/pgvector:pg16")`;
  a double would only prove the double behaves as written. Docker is required.
- **Async tests carry no `@pytest.mark.asyncio`** — `asyncio_mode = "auto"`.
- **Guards are append-only**: retire an invariant by translating it to the new surface, never by
  weakening the test; add a new file instead.

## ANTI-PATTERNS

- **Never weaken or delete a drift test to make a suite green.** The net is append-only.
- **Never parse prose as the contract.** A test that parses a markdown spec breaks when the spec is
  edited, and the spec is not the contract.
- **Never copy a pattern into the test** — a copied pattern passes forever. Derive it from the
  contract (e.g. kind models are discovered by introspection of `dom_kinds`).
- **Never import a retired tree** (`sys_ikigai`, `src.mesh`, `interfaces`, `life`, `vibe-ops`) —
  a fresh clone does not have them.
- **Never let a transport tool contain SQL or policy**, and never let the draft layer reach the
  writer — both are asserted by grep over the real source.
- **Never hardcode a list the contract can derive.**
- **`conftest.py` is not a scratchpad**: it decides `sys.path`, the event-loop policy and
  `asyncio_mode` for the whole suite; `LEGACY_TEST_MODULES` excludes retired modules from
  collection, it never deletes them.

## COMMANDS

```bash
cd src/ikigai && poetry run pytest -m "not e2e" -q
cd src/ikigai && poetry run pytest tests/store -q          # needs Docker (testcontainers)
cd src/ikigai && poetry run pytest tests/test_drift_invariants.py -v
```
