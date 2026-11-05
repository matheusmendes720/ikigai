# ikigai

**A personal life OS with one canonical store and one external agent.**

One Postgres (with pgvector) holds the vault as typed, versioned, queryable
artifacts. Our own MCP over HTTP is the only way in. The Telegram client is a
projection of that model. The agent that operates it is `pi` — external, and
deliberately not in this repository.

There is no framework underneath. No LangGraph, no model SDK, no orchestrator,
no second service to copy out. **This repository is the deployment.**

> The decision is recorded in
> [ADR-037 — Virada Canônica: camada de dados primeiro](code-docs/adr/ADR-037-data-layer-canonical-turn.md),
> renewed on 2026-11-02. The one-line version: *"stop building machine and
> build the data layer, on a harness that already exists."*

---

## The shape

```text
   owner ──Telegram──▶ ┌──────────────────────────────────────────┐
                       │  src/bot/        a projection of the DOM  │
                       └───────────────────┬──────────────────────┘
                                           │  MCP over HTTP — six tools
                       ┌───────────────────▼──────────────────────┐
                       │  src/transport/   the surface              │
                       └───────────────────┬──────────────────────┘
                                           │  in-process
                       ┌───────────────────▼──────────────────────┐
                       │  src/services/    the ONLY writer          │
                       └───────────────────┬──────────────────────┘
                                           │  SQL
                       ┌───────────────────▼──────────────────────┐
                       │  Postgres + pgvector — the canonical state│
                       └──────────────────────────────────────────┘

   agent ─────────────▶ ┌──────────────────────────────────────────┐
      (external: pi)    │  .pi/mcp.json + .pi/skills/               │
                        └──────────────────────────────────────────┘
```

The prose enters on the left and leaves as rows: `vault/` (markdown) is read
by `VaultSync`, which writes through the service layer into the store. The
store is canonical; the markdown is the prose it came from.

## What is in here

```text
src/contracts/     the DOM — one model, strongly typed (Pydantic v2, frozen)
                   dom.py · dom_kinds.py · common.py · errors.py · store.py
                   migrations/  the versioned SQL and its runner
src/data/          the store client — the pooled connection and the retries
                   client.py · repository.py
src/services/      the domain rules. ONE writer per store.
                   artifacts.py · relations.py · embeddings.py · sync.py
                   wiring.py — the composition root
src/transport/     the MCP transport over HTTP, and the healthcheck
                   mcp_server.py · healthcheck.py
src/bot/           the Telegram client — a projection of the DOM
src/ikigai/        the python package: the strategics loader, the suite, the lock
vault/             the prose source (markdown). INPUT to the store.
strategics/        the PT-BR strategic prose, published; the fork beside it is not.
deploy/            the container: Dockerfile + compose + the env contract
specs/harness/     the harness contract: router, prompts, the skill projection
code-docs/adr/     the decisions, with the reasoning that eliminated the rest
docs/              the wiki — the record, and the canonical map
```

## The four rules

| # | Rule | Where it lives |
|---|---|---|
| 1 | **One writer per store.** Clients speak MCP; only `src/services/` writes. A stale revision is a **409**, never a silent overwrite. | ADR-037 D5 · `src/services/artifacts.py` |
| 2 | **One DOM, N projections.** The model is shared; every client decides how to render it. | ADR-037 D2, D8 |
| 3 | **The agent is external.** The harness is `pi`; this repository builds no framework, no graph, no orchestrator. | ADR-037 D7 |
| 4 | **The store wins.** On a structured field, Postgres is canonical and the markdown is the prose it came from. | ADR-037 D4 |

## The stack

| Piece | What it is | Where it runs |
|---|---|---|
| **The store** | Postgres 16 + pgvector, schema `ikig`, migrations applied by the api at boot | one container |
| **The api** | our MCP over HTTP — six tools, no SQL, no policy | one container, bound to `127.0.0.1:8000` |
| **The bot** | the Telegram client — writes and reads through the api, never touches the database | one container |
| **The harness** | `pi`, external: it loads `.pi/mcp.json` and `.pi/skills/` | wherever the agent runs |

The api and the bot are the **same image**. The role is the command, not the
build — so the client and the transport cannot drift apart in the build.

## Running it

```bash
cd deploy
docker compose up -d --build          # db + api + bot
docker compose exec api python -m src.contracts.migrations.apply up
docker compose exec api python -m src.transport.healthcheck
```

The api applies the migrations itself before it serves, so the chain holds
without a manual step. The secrets are named in
[`deploy/README.md`](deploy/README.md); none of them belongs in a tracked
file. The bot **fails closed**: without `IKIGAI_BOT_ALLOWED_CHAT_IDS` there is
no bot.

The api binds the **loopback** on purpose. The public surface is the Telegram
bot, and the harness reaches the transport through an SSH tunnel:

```bash
ssh -L 8000:127.0.0.1:8000 <the box>     # then point the harness at http://127.0.0.1:8000/mcp
```

On the box, `bash scripts/deploy-vps.sh` does the whole thing: fetch,
checkout, `compose up -d --build`, migrations, healthcheck.

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

## The workflow — the skills

**The skills are the workflow.** A routine is a skill the harness runs, not a
subcommand a desktop CLI mounts. `specs/harness/skills/<id>/SKILL.md` is the
published projection; `.pi/skills/` is the copy `pi` loads.

| Routine | Skill | Produces | Cadence |
|---|---|---|---|
| Daily | `daily-note` | `nota` | every day |
| Weekly | `weekly-review` | `revisao` | five-day consolidation |
| Monthly | `monthly-review` | `desc` / `decisao` | three-week analysis |
| Quarterly | `quarterly-plan` | `plano` with `fase`, `okr`, `onda` | three-month planning |
| On demand | `store-read` | — | find, read, follow the graph |
| On demand | `store-write` | — | write under the conflict contract |
| On demand | `vault-sync` | — | when the prose changes |

The proportion behind it: five days of execution, three weeks of analysis,
three months of planning. The 45-day `onda` is the cycle; the 180-day
macro-phase is the quarter.

The harness contract — how an agent finds its prompt, its skill and its
cadence — is [`specs/harness/router.md`](specs/harness/router.md).

## The client

Telegram. `/nota` writes the day's note, `/sonho` writes a dream, `/busca`
queries the store, `/uid` reads an artifact and its edges. The bot is
owner-only and **fails closed**: no allowlist, no bot.

It is a **projection**, not a fork. The bot never opens a database
connection; it speaks MCP to the api, and every write carries a revision and
an idempotency key. One writer per store holds for the client too.

## The tests

```bash
cd src/ikigai
poetry run pytest -m "not e2e" -q
poetry run ruff check src/ && poetry run ruff format --check src/
poetry run mypy -p src.ikigai.src
```

The drift net is the specification. It is **append-only**: a guard is never
weakened to make a suite green, and a new invariant gets a new file.

| Guard | What it holds |
|---|---|
| `test_canonical_scope.py` | the retired runtime stays unpublished; the canonical surface and the vault's prose stay published; no LLM SDK in the tree |
| `test_published_surface_integrity.py` | a published file imports only published packages; every tracked file exists on disk |
| `test_drift_invariants.py` | six tools, the layering, the single UEID source, revision + idempotency key on every write |
| `test_gitignore_root_scope.py` | the repository root stays reachable, and no tracked file is ever ignored |
| `test_lint_target_is_not_vacuous.py` | every CI lint target resolves to the Python the branch publishes |
| `test_code_review_gate_integrity.py` | the review runs in an environment the branch publishes, and a failed check always says why |
| `test_ignore_rules_are_platform_invariant.py` | the ignore rules decide the same thing on every machine |

CI runs five package gates — `ikigai`, `src-contracts`, `src-data`,
`src-services`, `src-transport` — over ruff, mypy and pytest, plus a
pre-merge review of the changed files.

## The state of play

**Live.** The store, the transport, the client, the harness contract, the
skill projection, the container, the drift net.

**Deferred, on purpose** (ADR-037 D1): no PAV kernel, no hysteresis FSM, no
scoring in the published tree. They come last, and they need real data to be
worth anything.

**Unpublished, not deleted.** The pre-ADR-037 system — the langchain/langgraph
harness, the operator CLI, the fork mesh, the cybernetic engine, the
vault-markdown write path — is **not on this branch**. The files stay on the
owner's disk and in the git history. ADR-037 §"publicação independente" is
the clause that says so, and a drift test fails if any of it comes back.

**The document record is not the architecture.** `docs/` and `code-docs/`
keep the dated material that explains how the decisions were reached — a
decision that cites what it eliminated is history, not architecture. What is
current is what the drift net holds.

## The metric that decides this shape

One note written from a client without editing a file by hand · zero lost
updates with two clients active · a structured search under 100ms at p95.
Fourteen days of that decides whether this shape worked — and the intent is
the metric, not the feature count.

---

*ikigai — the algorithmic life OS. The store wins.*
