# ikigai

The Poetry package of the canonical service (ADR-037, renewed 2026-11-02).

It holds two things, and only two things:

1. **`strategics/`** — the read-only loader that reads the PT-BR strategic
   prose (`strategics/*.md`) into typed documents for an agent. It never
   writes.
2. **`tests/`** — the drift net: the canonical test suite, including the
   guards that hold the published surface, the layering and the versioning
   in place.

The service itself is not a distribution. `src/contracts/`, `src/data/`,
`src/services/`, `src/transport/` and `src/bot/` are imported as
`src.<package>.*` with the repository root on `sys.path` — the container sets
that explicitly (`deploy/Dockerfile`). This package is the one that has a
lockfile, so it is the one the CI installs.

## Install and test

```bash
poetry install
poetry run pytest -m "not e2e" -q
poetry run ruff check src/ && poetry run ruff format --check src/
poetry run mypy -p src.ikigai.src      # never invoke mypy with a path
```

The store tests (`tests/store/`) reach a real Postgres through
testcontainers, so the driver and the container runtime have to be in the same
environment that runs pytest:

```bash
poetry run pip install "psycopg[binary]" psycopg-pool "testcontainers[postgres]"
```

## The drift net

| File | Holds |
|---|---|
| `tests/test_canonical_scope.py` | the retired runtime stays unpublished; the canonical surface stays published; no published file imports an unpublished tree; no LLM SDK in the published tree |
| `tests/test_drift_invariants.py` | the transport exposes exactly six tools; the layering `transport → services → data` holds; the UEID pattern has one source; every write carries a revision and an idempotency key |
| `tests/test_gitignore_root_scope.py` | the repository root stays reachable by git, and no tracked file is ever ignored |
| `tests/contracts/test_dom_kinds_drift.py` | the ten artifact kinds and `KIND_TABLES` stay in sync across the contract and the SQL ends |

These grow with the system and are never weakened to make a suite green.

## What is not here

The pre-ADR-037 runtime — the LangChain/LangGraph harness, the local chat
REPL, the stdio MCP fork servers, the operator CLI and the tracing stack — is
**unpublished**. The files stay on the owner's disk and in the git history;
they are not on the branch. ADR-037 §"publicação independente" is the clause
that says so.

The algorithm layer is deferred (ADR-037 D1): no PAV kernel, no hysteresis
FSM, no scoring in the published tree. They come last, and they need real
data to be worth anything.
