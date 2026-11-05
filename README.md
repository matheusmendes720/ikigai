# ikigai

**The service.** A personal, single-player agent system: one Postgres store
that holds the vault as typed, versioned, queryable artifacts; one MCP
transport over HTTP; one Telegram client that writes and reads through it.

This repository IS the deployment. There is no separate service repo, no
"backend" folder to copy out, and no framework underneath.

> The decision is recorded in
> [ADR-037 — Virada Canônica: camada de dados primeiro](code-docs/adr/ADR-037-data-layer-canonical-turn.md)
> and the renewed scope of 2026-11-02. The one-line version: *"stop building
> machine and build the data layer, on a harness that already exists."*

---

## What is in here

```text
src/contracts/     the DOM — one model, strongly typed (Pydantic v2, frozen)
                   dom.py · dom_kinds.py · common.py · errors.py · store.py
                   migrations/  the versioned SQL and its runner
src/data/          the store client — the pooled connection and the retries
                   client.py · repository.py
src/services/      the domain rules. ONE writer per store.
                   artifacts.py · relations.py · embeddings.py · sync.py
src/transport/     the MCP transport over HTTP, and the healthcheck
                   mcp_server.py · healthcheck.py
src/bot/           the Telegram client — a projection of the DOM
src/ikigai/        the python package: contracts surface, tests, packaging
vault/             the prose source (markdown). INPUT to the store.
strategics/        the PT-BR strategic prose. Published; the fork beside it is not.
deploy/            the container: Dockerfile + compose + the env contract
specs/             the harness specs and the data-layer series
code-docs/adr/     the decisions, with the reasoning that eliminated the rest
docs/              the wiki — including the diagnosis that produced this shape
```

## The four rules

| # | Rule | Where it lives |
|---|---|---|
| 1 | **One writer per store.** Clients speak MCP; only `src/services/` writes. A stale revision is a **409**, never a silent overwrite. | ADR-037 D5 · `src/services/artifacts.py` |
| 2 | **One DOM, N projections.** The model is shared; every client decides how to render it. | ADR-037 D2, D8 |
| 3 | **The agent is external.** The harness is `pi`; this repository builds no framework, no graph, no orchestrator. | ADR-037 D7 |
| 4 | **The store wins.** On a structured field, Postgres is canonical and the markdown is the prose it came from. | ADR-037 D4 |

## Running it

```bash
cd deploy
docker compose up -d --build
docker compose exec api python -m src.contracts.migrations.apply up
docker compose exec api python -m src.transport.healthcheck
```

The secrets are named in [`deploy/README.md`](deploy/README.md). None of them
belongs in a tracked file.

## The API

Six tools, and the transport is the contract:

| Tool | What it does |
|---|---|
| `search_artifacts` | query by index, full text or semantics; cursor pagination, never offset |
| `get_artifact` | read one artifact with its edges and, optionally, its neighbours |
| `upsert_artifact` | write under optimistic concurrency (`revision` + `idempotency_key`) |
| `delete_artifact` | soft delete — the row and its history stay |
| `list_relations` | walk the typed edges out of one node |
| `embed_text` | the vector for a string |

## The tests

```bash
cd src/ikigai
poetry run pytest -m "not e2e" -q
poetry run ruff check src/ && poetry run ruff format --check src/
poetry run mypy -p src.ikigai.src
```

The drift net is the guard: `test_canonical_scope.py` holds the published
surface, `test_drift_invariants.py` holds the writing and layering rules, and
`test_gitignore_root_scope.py` holds the repository root reachable. They grow
with the system and are never weakened to make a suite green.

The PT-BR strategic prose is published too, at `strategics/` — the grounding
`vault/_strategics_excerpt.md` names as the full foundation. The loader that
reads it ships as a library under `src/ikigai/src/`. The vendored
`planning-with-files/` fork beside it is a third-party repository, and it is
not published.

## What is NOT here, and why

The pre-ADR-037 system — the langchain/langgraph harness, the operator CLI,
the fork mesh, the cybernetic engine, the vault-markdown write path — is
**unpublished, not deleted**. The files stay on the owner's disk and in the
git history; they are simply not on this branch. ADR-037 §"publicação
independente" is the clause that says so.

The algorithms are **deferred** (ADR-037 D1): no PAV kernel, no hysteresis
FSM, no scoring in the published tree. They come last, and they need real
data to be worth anything.

## The client

Telegram. `/nota` writes the day's note, `/sonho` writes a dream, `/busca`
queries the store, `/uid` reads an artifact and its edges. The bot is
owner-only and **fails closed**: no allowlist, no bot.

The intent is the metric: one note written from a client without editing a
file by hand, zero lost updates with two clients active, and a structured
search under 100ms at p95. Fourteen days of that decides whether this shape
worked.
