# AGENTS.md

Algorithmic Life OS — a personal, single-player agent system. One Postgres store
holds the vault as typed, versioned, queryable artifacts; one MCP transport over
HTTP serves them; one Telegram client projects them.

**This repository IS the deployment.** There is no separate service repo, no
"backend" to copy out, and no framework underneath. The agent that operates it is
external — the harness is `pi`.

**Canonical scope: ADR-037, renewed 2026-11-02.** The pre-ADR-037 system — the
LangChain/LangGraph harness, the fork mesh, the operator CLI and TUI, the
cybernetic engine, the root test suite — is **unpublished, not deleted**. The
files stay on the owner's disk and in the git history. A drift test fails if any
of them comes back.

Repo: github.com/matheusmendes720/ikigai · Board: github.com/users/matheusmendes720/projects/5

## The product

Four pieces, and nothing else. A change that does not serve one of them is
outside the product.

| Piece | What it is | Where it lives |
|---|---|---|
| **The store** | One Postgres + pgvector. The DOM lives in the `ikig` schema. The only state. | `src/contracts/migrations/` · `src/data/` |
| **The transport** | **Our own MCP**, six tools, over HTTP — and, beside it, the websocket that carries the changes the store announces. The only writer. | `src/transport/mcp_server.py` (ADR-011) · `src/transport/ws_server.py` (ADR-039) |
| **The client** | Telegram. A projection of the DOM, never a fork of it. | `src/bot/main.py` |
| **The agent** | **The `pi` harness — external.** It reads the project's MCP servers from `.pi/mcp.json` and its skills from `.pi/skills/`. Nothing in this repository imports it. | `specs/harness/` · `.pi/` |

**The skills are the workflow.** `specs/harness/skills/<id>/SKILL.md` is the
published projection of the routines — `daily-note`, `weekly-review`,
`monthly-review`, `quarterly-plan`, `store-read`, `store-write`, `vault-sync`.
`pi` loads them from `.pi/skills/`, and the copy is regenerated from the
projection. The projection is the source; the copy is runtime state. The
skills adapt the workflow **into the Telegram client**: a routine is a skill
the harness runs, not a subcommand a desktop CLI mounts.

**No LangGraph, no model SDK, no orchestrator in the published tree.** The
harness is `pi` and it is not in this repository (ADR-037 D7). A published file
that imports one is a drift, not a feature.

## The four rules

| # | Rule | Where it lives |
|---|---|---|
| 1 | **One writer per store.** Clients speak MCP; only `src/services/` writes. A stale revision is a **409**, never a silent overwrite. | ADR-037 D5 · `src/services/artifacts.py` |
| 2 | **One DOM, N projections.** The model is shared; every client decides how to render it. | ADR-037 D2, D8 |
| 3 | **The agent is external.** The harness is `pi`; this repository builds no framework, no graph, no orchestrator. | ADR-037 D7 |
| 4 | **The store wins.** On a structured field, Postgres is canonical and the markdown is the prose it came from. | ADR-037 D4 |

## Setup commands

- Install the package + the canonical suite: `cd src/ikigai && poetry install`
- Install the contracts package: `cd src/contracts && uv sync`
- Start the service: `cd deploy && docker compose up -d --build`
- Apply the migrations: `cd deploy && docker compose exec api python -m src.contracts.migrations.apply up`
- Healthcheck: `cd deploy && docker compose exec api python -m src.transport.healthcheck`
- `deploy/compose.yml` runs five roles off one image: `db`, `api`, `ws`, `sync`, `bot`
- Ingest the vault into the store: `cd deploy && docker compose exec sync python -m src.services.sync`
- Feed the vector index for rows written before it was fed:
  `cd deploy && docker compose exec api python -m src.services.embeddings backfill`
- Wire the harness to a running api: `mkdir -p .pi/skills && cp -r specs/harness/skills/* .pi/skills/`
- Prove the wiring answers: `pi mcp list` — the api is connected, with its six tools

## Testing instructions

- Unit + integration: `cd src/ikigai && poetry run pytest -m "not e2e"`
  (pytest · pytest-asyncio `asyncio_mode = "auto"` · hypothesis · testcontainers —
  the store tests reach a **real Postgres**, so they need Docker)
- **There is no e2e yet.** `-m "not e2e"` excludes nothing today: no published test
  file carries the `e2e` marker. The integrated path (Telegram → `/mcp` → Postgres →
  read back) has never been run — see `specs/production-readiness/ROADMAP.md` (G1–G5)
- The drift net lives in `src/ikigai/tests/` and is **append-only**: never delete or
  weaken a guard to make a suite green — add a new file instead
- Every new behavior gets a test; all tests pass before a PR
- A guard is only worth what its failure proves: re-introduce the violation and
  watch it fail before you trust a green run

## Lint & typecheck

- Lint: `cd src/ikigai && poetry run ruff check src/ && poetry run ruff format --check src/`
- Typecheck: `cd src/ikigai && poetry run mypy -p src.ikigai.src` — **never invoke mypy
  with a path**; it creates a second module identity for the same files and aborts
  with "Source file found twice under different module names"
- The other canonical packages are ruff-only in CI: `src/contracts`, `src/data`,
  `src/services`, `src/transport`
- The PR review (`.github/scripts/code_review.py`) runs each package's tools
  inside that package's own environment. The root bucket — the Python that
  belongs to no package (the CI tooling, the Telegram client) — runs in the
  ONE environment the branch publishes: the Ikigai package
- Pre-commit hooks: `.pre-commit-config.yaml`

## Project layout

- `src/contracts/` — the DOM (Pydantic v2, frozen) + the versioned SQL and its runner
- `src/data/` — the store client: pooled Postgres, retries, transactions
- `src/services/` — the domain rules; the ONLY writer of the store
- `src/transport/` — our MCP transport (FastMCP) over the services, the websocket sync channel, and the healthcheck
- `src/bot/` — the Telegram client; a projection of the DOM, over MCP or over the websocket
- `src/ikigai/` — the Poetry package: the strategics loader + the canonical suite
- `vault/` — the markdown prose: INPUT to the store, append-only
- `strategics/` — the PT-BR strategic prose (published; the fork beside it is not)
- `specs/harness/` — the harness contract: the router, the prompts, the skill specs
- `specs/harness/skills/` — the published projection of the runtime skills
- `specs/data-layer/` — the data-layer tech spec (ADR-037)
- `specs/production-readiness/` — the product state, the plan to close the gap, and the
  roadmap: `PRODUCT.md` · `TECH.md` · `ROADMAP.md`
- `deploy/` — the container: Dockerfile, compose.yml, the env contract
- `code-docs/adr/` — the decisions the contracts rest on (011, 013, 014, 033, 037, 039)
- `docs/` — the index, and the data-layer spec series under `docs/superpowers/specs/`
- `data/` — runtime state (gitignored); one tracked marker under `data/investigation_queue/`
- `.claude/skills/` — the published projection of the four cadence skills
- `.pi/` — the project's harness configuration: the MCP declaration (`mcp.json`); the
  skills copy is runtime state and is not published
- `.github/` — CI + the PR-review scripts

## Code style

- Python 3.11 (`.python-version`); `from __future__ import annotations` at the top of
  every module
- **The layering is a pyramid: `transport → services → data`.** Only `src/data/` knows
  the driver; only `src/services/` writes; the transport translates intent and never
  carries SQL. The drift net enforces it.
- Pydantic v2 strict — `frozen=True`, `extra="forbid"` on every model, `Literal`
  discriminators, `Decimal` for KPIs
- Ruff: `line-length = 100`, `target-version = "py311"`. The real configs are
  `src/ruff.toml`, `src/contracts/pyproject.toml`, `src/ikigai/pyproject.toml` —
  per-package, never inherited
- mypy `strict = true` in `src/ikigai/pyproject.toml`; the root `mypy.ini` governs
  only a bare `mypy` run from the repository root
- `src/` has **no `__init__.py`** — `from src.contracts.X` needs the repo root on
  `sys.path`; `from contracts.X` needs `src/` on it. Both spellings are live
- **One identity, one source** — `UEID` is defined once, in
  `src/contracts/common.py`. Never re-define it

## Where to look

| Task | Location | Notes |
|------|----------|-------|
| The unified model | `src/contracts/dom.py`, `dom_kinds.py` | one DOM, N projections (ADR-037 D2) |
| Store constants | `src/contracts/store.py` | provider, schema, dimension, the DSN env var |
| Identity | `src/contracts/common.py` | `UEID`, ADR-014 4-part — ONE pattern, ONE file |
| The store client | `src/data/client.py`, `repository.py` | **source**, not runtime state |
| The domain rules | `src/services/` | validation, versioning, idempotency, the conflict contract |
| The MCP tool surface | `src/transport/mcp_server.py` | exactly six tools; transport via `IKIGAI_MCP_TRANSPORT` (ADR-011) |
| The websocket sync channel | `src/transport/ws_server.py` | the SAME six tools, plus the store's changes (ADR-039) |
| The vault ingestion | `src/services/sync.py` | `python -m src.services.sync` — the prose into the store and the index |
| The change feed | `src/services/changes.py` | the store's own announcements, as domain events |
| The Telegram client | `src/bot/main.py` | speaks MCP or the websocket; never opens a database; fails closed |
| The healthcheck | `src/transport/healthcheck.py` | measures the DATA PLANE, not the surface (C-2) |
| The container | `deploy/Dockerfile`, `compose.yml` | one image, five roles |
| The harness contract | `specs/harness/router.md` | how an agent finds its prompt, its skill, its cadence |
| The skill projection | `specs/harness/skills/<id>/SKILL.md` | the source; `pi` loads the copy in `.pi/skills/` |
| The drift net | `src/ikigai/tests/` | the published surface, the layering, the versioning |

## Code map

| Symbol | Location | Role |
|--------|----------|------|
| `Artifact`, `WriteRequest`, `WriteOutcome` | `src/contracts/dom.py` | the spine and the write envelope |
| `KIND_MODELS` | `src/contracts/dom_kinds.py` | the ten kinds, one typed model each |
| `UEID` | `src/contracts/common.py` | the canonical 4-part join key (ADR-014) |
| `DataClient` | `src/data/client.py` | the pooled connection, the retries, the transactions |
| `ArtifactService` | `src/services/artifacts.py` | the only writer: versioning, idempotency, conflict |
| `VaultSync` | `src/services/sync.py` | reads the vault prose, upserts it, writes nothing back |
| `build_services` | `src/services/wiring.py` | the composition root — the service layer, not the transport |
| `mcp` | `src/transport/mcp_server.py` | the FastMCP server the harness connects to |
| `Router` | `src/transport/ws_server.py` | the websocket: the same tools, plus the events the store pushes |
| `Bot` | `src/bot/main.py` | the Telegram loop, owner-only |

## Anti-patterns (this project)

- **Never re-introduce the retired runtime** (ADR-037): no `sys_ikigai/`, no
  `src/mesh/`, no `interfaces/`, no `life/`, no `vibe-ops/`, no `src/agents/`, no
  `src/tuiboard/`, no `src/solverforge_calendar/`, no
  `src/ikigai/src/{agents,chat,mcp_server,plugins}`
- **Never let a transport tool contain SQL or policy.** The transport translates
  intent; the services decide
- **Never import the store client from outside `src/services/`.** The composition
  root lives in `src/services/wiring.py`; the transport asks the service layer for
  its wiring
- **Never write to `vault/` from code.** The vault is prose; the store is canonical
- **Never publish a file that imports a package the branch does not publish.**
  `life/cli/cli.py` imported `interfaces.cli.notify_cli` at module scope, and a
  fresh clone could not import the package at all
- **Never give the repository root a Python project.** The root has no
  `pyproject.toml` and no `uv.lock`, on purpose: the retired root project is
  what `uv run --frozen --extra dev` still pointed at, and it resolved on the
  owner's disk and in no clone. The one published environment is
  `src/ikigai/`
- **Append-only** — never delete or prune `vault/`, `strategics/`
- **Drift tests are append-only**: never delete or weaken one; add a new file under
  `src/ikigai/tests/` instead of editing an existing guard
- **No secret, token or connection string in a tracked file.** Every secret comes
  from the environment; `.env` is gitignored
- **No algorithmic layer** while the architecture is still moving (ADR-037 D1).
  No PAV kernel, no hysteresis FSM, no scoring in the published tree
- `strategics/planning-with-files/` is a vendored third-party fork with its own
  `.git/` — untracked here, never commit its contents
- The stray shell-redirect leftovers in the repo root are **gitignored by shape**
  (a root name that is a bare identifier, or one that carries a character no file
  may legitimately contain). Leave them alone

## PR & commit conventions

- Branch from `main`; never push to `main` directly
- Conventional commits: `feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`
- PR template: `.github/PULL_REQUEST_TEMPLATE.md`; CI green (the five-package matrix
  and the container job) before merge
- Open the PR with `gh pr create` once CI is green — **with `--repo
  matheusmendes720/ikigai`**. The owner's checkout carries a leftover `upstream`
  remote from the retired runtime (the taskdog bridge), and `gh` resolves the
  repository from it: the command then fails with "No commits between main and
  <branch>", which reads like a broken push and is not one. Either name the
  repository or remove the remote (`git remote remove upstream`).

## Security

- Never commit secrets — `.env` is gitignored; `.env.example` names every variable
  the published code reads
- `IKIGAI_STORE_DSN` above all — without it the service refuses to start
- **The client fails closed.** `IKIGAI_BOT_ALLOWED_CHAT_IDS` is required; an empty
  allowlist stops the bot at startup instead of turning it into a public write
  channel (C-4)
- **The healthcheck measures the data plane** (C-2): the store answers a query AND
  a client can reach the transport. A socket that returns bytes is not health —
  and neither is a socket that answers *itself* while every other container is
  refused: the check dials the address a client uses
- **The api binds the loopback.** The public surface is the Telegram client; the
  harness reaches the transport through an SSH tunnel, and the store is not
  reachable from outside at all

## Notes

- **The drift net** — CI fails if a load-bearing invariant is weakened:

| File | Purpose |
|---|---|
| `src/ikigai/tests/test_canonical_scope.py` | the retired runtime stays unpublished; the canonical surface AND the vault's prose stay published; no published file imports an unpublished tree; no LLM SDK; everything the image copies is published |
| `src/ikigai/tests/test_published_surface_integrity.py` | a published file imports only published packages; a junk-named root directory holds nothing |
| `src/ikigai/tests/test_drift_invariants.py` | the transport exposes exactly six tools; the layering holds; the UEID pattern has one source; every write carries a revision and an idempotency key |
| `src/ikigai/tests/test_gitignore_root_scope.py` | the repository root stays reachable, and no tracked file is ever ignored |
| `src/ikigai/tests/test_lint_target_is_not_vacuous.py` | every CI lint target resolves to the Python the branch publishes — a gate that checks no file is green forever |
| `src/ikigai/tests/test_code_review_gate_integrity.py` | the review runs in an environment the branch publishes (the root is not a package), and a failed check always says why |
| `src/ikigai/tests/contracts/test_dom_kinds_drift.py` | the ten kinds and `KIND_TABLES` stay in sync across the contract and the SQL ends |
| `src/ikigai/tests/store/test_store_schema.py` | the SQL and the contracts agree; every migration has a reverse script; the full-text configuration precedes the index that needs it |
| `src/ikigai/tests/transport/test_bind_address.py` | the transport binds the address a CLIENT uses, and the healthcheck dials that one — not the bind host (C-2) |
| `src/ikigai/tests/services/test_artifacts_service.py` | the write envelope, the conflict contract, the idempotency gate, and the vault sync — against an in-memory double |

- **The environment is the contract.** Nothing comes from a file; every secret comes
  from the environment.
- **UEID drift is real** — the shipped `_UEID_PATTERN` is a wider triple-pattern
  (4-part short | 4-part long-UUID | 5-part legacy), so it does **not** match the
  canonical literal `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`. The 5-part
  branch exists only to READ rows written before ADR-014; it is never written. Never
  re-define `UEID` — extend the canonical one.
- **Windows quirks:** `sys.stdin.readline()` hangs on Windows pipes — use
  `sys.stdin.buffer.readline()`; pytest-asyncio `PermissionError [WinError 5]` on
  stale temp dirs → `src/ikigai/tests/conftest.py` redirects `tempfile.tempdir` to
  `data/pytest-tmp/`.
- **Version pins that bite:** `mcp` is pinned `<2` (2.x dropped
  `mcp.server.fastmcp`); `ruff` is pinned `^0.17.3` in `src/ikigai/pyproject.toml`
  so the CI gate cannot drift.
- **Tooling split (do not mix):**

| Subpath | Build system | Notes |
|---|---|---|
| `src/ikigai/` | **Poetry** | own `poetry.lock`; the drift net lives in `src/ikigai/tests/` |
| `src/contracts/` | **Hatchling** | own `pyproject.toml`, `uv.lock` |
| `src/data/`, `src/services/`, `src/transport/`, `src/bot/` | none | imported as `src.<pkg>.*` with the repo root on `sys.path`; linted, not installed |

- **The deployment is the VPS.** The box runs the compose; the store is the owner's
  own Postgres there. The operator scripts under `scripts/` are **not published** —
  they live on the owner's disk and on the box. A fresh clone of the repository
  carries the service, not the way to operate it.
