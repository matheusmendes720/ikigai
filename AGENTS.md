# PROJECT KNOWLEDGE BASE

**Generated:** 2026-11-21
**Commit:** 09c7c81f
**Branch:** main

## OVERVIEW

Algorithmic Life OS — a personal, single-player agent system. One Postgres store
holds the vault as typed, versioned, queryable artifacts; one MCP transport over
HTTP serves them; one Telegram client projects them. **This repository IS the
deployment**: no separate service repo, no framework underneath, and the agent
that operates it is external — the harness is `pi` (ADR-037 D7).

## STRUCTURE

```
life/
├── src/            # the product: contracts, data, services, transport, bot, ikigai
├── vault/          # the owner's prose: INPUT to the store, append-only
├── strategics/     # PT-BR strategic prose (published; the vendored fork beside it is not)
├── specs/          # the harness contract + the plan of record
├── code-docs/adr/  # the decision record: ADR-011 … ADR-047
├── docs/           # the wiki + the dated spec series
├── deploy/         # the container: one image, seven roles
├── .github/        # CI + the PR-review scripts
└── .claude/skills/ # the published mirror of the four cadence skills
```

Child guides own their own subtree: `src/AGENTS.md`, `src/{contracts,data,
services,transport,bot}/AGENTS.md`, `src/ikigai/**/AGENTS.md`, `specs/{harness,
production-readiness}/AGENTS.md`, `code-docs/AGENTS.md`, `docs/AGENTS.md`,
`deploy/{,harness/}AGENTS.md`, `.github/{,scripts/}AGENTS.md`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| The unified model | `src/contracts/dom.py`, `dom_kinds.py` | one DOM, N projections (ADR-037 D2) |
| Identity | `src/contracts/common.py` | `UEID`, ADR-014 4-part — ONE pattern, ONE file |
| The store client | `src/data/client.py`, `repository.py` | source, not runtime state |
| The domain rules | `src/services/artifacts.py` | versioning, idempotency, the conflict contract (409) |
| The composition root | `src/services/wiring.py` | the service layer, not the transport |
| The MCP tool surface | `src/transport/mcp_server.py` | exactly six tools (ADR-011) |
| The websocket sync channel | `src/transport/ws_server.py` | the SAME six, plus the store's changes (ADR-039) |
| The Telegram client | `src/bot/main.py` | speaks MCP or the websocket; never opens a database |
| The vault ingestion | `src/services/sync.py` | prose into the store and the index |
| The harness contract | `specs/harness/router.md` | how an agent finds its prompt, skill, cadence |
| The skill projection | `specs/harness/skills/<id>/SKILL.md` | the source; `.pi/skills/` is the runtime copy |
| The decision record | `code-docs/adr/` | ADR-037 is the anchor; the next free number is ADR-048 |
| The plan of record | `specs/production-readiness/ROADMAP.md` | the gates G1 → G5 |
| The drift net | `src/ikigai/tests/` | append-only guards |

## CODE MAP

| Symbol | Location | Role |
|--------|----------|------|
| `Artifact`, `WriteRequest`, `WriteOutcome` | `src/contracts/dom.py` | the spine and the write envelope |
| `KIND_MODELS` | `src/contracts/dom_kinds.py` | the ten kinds, one typed model each |
| `UEID` | `src/contracts/common.py` | the canonical 4-part join key (ADR-014) |
| `DataClient` | `src/data/client.py` | pooled Postgres, retries, transactions |
| `ArtifactService` | `src/services/artifacts.py` | the only writer: versioning, idempotency, conflict |
| `VaultSync` | `src/services/sync.py` | reads the vault prose, upserts it |
| `build_services` | `src/services/wiring.py` | the composition root |
| `mcp` | `src/transport/mcp_server.py` | the FastMCP server the harness connects to |
| `Router` | `src/transport/ws_server.py` | the websocket: the same six tools, plus events |
| `Bot` | `src/bot/main.py` | the Telegram loop, owner-only |

## CONVENTIONS

- Python 3.11 (`.python-version`); `from __future__ import annotations` at the top of every module.
- **The layering is a pyramid: `transport → services → data → contracts`.** Only `src/data/` knows the driver; only `src/services/` writes; the transport translates intent and never carries SQL.
- Pydantic v2 strict — `frozen=True`, `extra="forbid"` on every model, `Literal` discriminators, `Decimal` for KPIs.
- **One identity, one source** — `UEID` is defined once, in `src/contracts/common.py`. Never re-define it.
- `src/` has **no `__init__.py`** — `from src.contracts.X` needs the repo root on `sys.path`; `from contracts.X` needs `src/` on it. Both spellings are live.
- Tooling is per package, never inherited: ruff at `src/ruff.toml`, `src/contracts/pyproject.toml`, `src/ikigai/pyproject.toml` (line-length 100, py311); mypy `strict` only in `src/ikigai`.
- The repository root has **no Python project**: a root `pyproject.toml` / `uv.lock` may sit on the owner's disk but is gitignored. The one published environment is `src/ikigai/`.
- `.gitignore` is shape-based and the **last matching rule wins**: a negation must come after the rule that excludes its contents.
- No model SDK, no LangGraph, no orchestrator in the published tree (ADR-037 D7).

## ANTI-PATTERNS (THIS PROJECT)

- **Never re-introduce the retired runtime** (ADR-037): no `sys_ikigai/`, `src/mesh/`, `interfaces/`, `life/`, `vibe-ops/`, `src/agents/`, `src/tuiboard/`, `src/solverforge_calendar/`, `src/ikigai/src/{agents,chat,mcp_server,plugins}`. It is unpublished, not deleted — a drift test fails if it comes back.
- **Never let a transport tool contain SQL or policy.** The transport translates intent; the services decide.
- **Never import the store client from outside `src/services/`** — the composition root is `src/services/wiring.py`.
- **Never write to `vault/` from code** (the sanctioned write-back, ADR-043, refuses the repo's own `vault/`); **never delete or prune** `vault/` or `strategics/` — append-only.
- **Never publish a file that imports a package the branch does not publish**, and never give the repository root a Python project.
- **The drift net is append-only**: never delete or weaken a guard to make a suite green — add a new file under `src/ikigai/tests/`.
- **No secret, token or connection string in a tracked file.** Everything comes from the environment; `.env` is gitignored.
- **No algorithmic layer yet** (ADR-037 D1): no PAV kernel, no hysteresis FSM, no scoring in the published tree.
- Never add a seventh MCP tool — the surface is exactly six: `search_artifacts`, `get_artifact`, `upsert_artifact`, `delete_artifact`, `list_relations`, `embed_text`.
- Never publish an ADR by dropping a file into `code-docs/adr/`: `.gitignore` excludes `code-docs/adr/*.md` and re-includes each ADR by name. The same rule hides any other file there.

## UNIQUE STYLES

- The prose is PT-BR (`vault/`, `strategics/`, ADR-040…047, `specs/production-readiness/`, `docs/`); the harness contract is English (`specs/harness/`, `specs/miniapp/`).
- Two ADR shapes coexist: bold-markdown frontmatter (011, 013, 014, 033, 037, 039, 040, 041, 043) and YAML frontmatter (042, 044, 045, 046, 047).
- The tree is documents plus code: `specs/` (plan), `code-docs/adr/` (decisions), `docs/` (wiki) are all markdown, no executable code.
- **The projection is the source; the copy is runtime state** — `specs/harness/skills/<id>/SKILL.md` → `.pi/skills/`, and `.claude/skills/ikigai-<cadence>/SKILL.md` mirrors the same projection under a directory name that differs from its skill id.
- The deployment is the VPS: the box runs the compose; the repository carries the service, not the way to operate it.

## COMMANDS

```bash
# The suite — the canonical entry (store tests need Docker: a real Postgres via testcontainers)
cd src/ikigai && poetry install && poetry run pytest -m "not e2e"

# Lint / format / typecheck — mypy with the package, never with a path
cd src/ikigai && poetry run ruff check src/ && poetry run ruff format --check src/
cd src/ikigai && poetry run mypy -p src.ikigai.src

# The service, as containers
cd deploy && docker compose up -d --build
docker compose exec api python -m src.contracts.migrations.apply up
docker compose exec api python -m src.transport.healthcheck
docker compose exec sync python -m src.services.sync

# Wire the harness to a running api, then prove the wiring answers
mkdir -p .pi/skills && cp -r specs/harness/skills/* .pi/skills/
pi mcp list
```

## NOTES

- **No e2e yet.** `-m "not e2e"` excludes nothing today; the integrated path (Telegram → `/mcp` → Postgres → read back) has never been run — see `specs/production-readiness/ROADMAP.md` (G1–G5).
- **A guard is only worth what its failure proves**: re-introduce the violation and watch it fail before trusting a green run.
- **The bot fails closed** (C-4): `IKIGAI_BOT_ALLOWED_CHAT_IDS` is required. The healthcheck measures the **data plane** (C-2), and the api binds the loopback.
- **Only `api`, `ws`, `sync`, `write` hold `IKIGAI_STORE_DSN`.** The bot and the harness reach the store through the api's MCP; a DSN fallback would be a second writer (ADR-037 D5).
- **UEID drift is real**: the shipped `_UEID_PATTERN` also accepts a 5-part legacy form, so it does not match the canonical 4-part literal. The legacy branch only READS pre-ADR-014 rows; never re-define `UEID` — extend the canonical one.
- **Windows quirks**: `sys.stdin.readline()` hangs on Windows pipes (use `sys.stdin.buffer.readline()`); `src/ikigai/tests/conftest.py` redirects `tempfile.tempdir` to `data/pytest-tmp/` to dodge `PermissionError [WinError 5]`.
- **Version pins that bite**: `mcp` is pinned `<2` (2.x dropped `mcp.server.fastmcp`); `ruff` is pinned `^0.17.3`.
- **`.claude/AGENTS.md` is a retired path** — a `.gitignore` rule and a `RETIRED_PATHS` entry both point at it; it must never come back. Everything under `.claude/` except the four published cadence skills is the owner's local runtime (gitignored), including a checkout of the retired runtime under `.claude/worktrees/`.
- **Stale facts on disk, not fixed here**: `deploy/README.md` lists six containers (the compose runs seven); `docs/README.md` says "as cinco decisões" (14 ADRs are published); `specs/harness/router.md` calls the 45-day cycle `onda` and the 180-day year `quarter`, while the owner's prose says `onda` = 15 days, `ciclo` = 45, 180 days = the year; `strategics/00-ÍNDICE-PROGRESSIVO.md` still says the tree holds six documents (nine are published).
