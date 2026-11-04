# PROJECT KNOWLEDGE BASE

**Canonical scope (ADR-037, renewed 2026-11-02).** The repository **is** the
service: one Postgres store, one MCP transport over HTTP, one Telegram client
that writes through it.

**Generated:** 2026-11-02 — the ADR-037 cut.

## OVERVIEW

Algorithmic Life OS — a personal, single-player agent system. One DOM holds
the vault as typed, versioned, queryable artifacts. One transport serves them.
One client projects them.

The pre-ADR-037 system — the LangChain/LangGraph harness, the fork mesh, the
operator CLI and TUI, the cybernetic engine, the root test suite — is
**unpublished**. The files stay on the owner's disk and in the git history;
they are not on this branch. A drift test fails if any of them comes back.

Repo: github.com/matheusmendes720/ikigai — Board: github.com/users/matheusmendes720/projects/5

## STRUCTURE

```text
{root}/
├── src/            # the canonical data layer
│   ├── contracts/  #   the DOM (Pydantic v2, frozen) + the plan hierarchy
│   ├── data/       #   the store client: pooled Postgres, retries, transactions
│   ├── services/   #   the domain rules — the ONLY writer of the store
│   ├── transport/  #   MCP over the services (FastMCP) + the healthcheck
│   ├── bot/        #   the Telegram client — a projection of the DOM
│   ├── ikigai/     #   the Poetry package: the strategics loader + the suite
│   ├── life_tatics/ #  time-block / screentime CLI
│   └── planner/    #   markdown-only planning notes
├── vault/          # markdown prose — INPUT to the store, append-only
├── strategics/     # the PT-BR strategic prose — published; the fork beside it is not
├── deploy/         # the container: Dockerfile + compose + the env contract
├── specs/          # the harness specs and the data-layer series
├── code-docs/      # adr / brd / design / diagnostic / prd
├── docs/           # the wiki — the record, including the diagnosis
├── data/           # runtime state — gitignored
├── .claude/        # the agent harness: prompts, skills, slash commands
└── .github/        # CI + the PR-review scripts
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| The unified model | `src/contracts/dom.py`, `dom_kinds.py` | one DOM, N projections (ADR-037 D2) |
| Store constants | `src/contracts/store.py` | provider, schema, dimension, the DSN env var |
| Identity | `src/contracts/common.py` | `UEID`, ADR-014 4-part — ONE pattern, ONE file |
| The store client | `src/data/client.py`, `repository.py` | **source**, not runtime state |
| The domain rules | `src/services/` | validation, versioning, idempotency, the conflict contract |
| The MCP tool surface | `src/transport/mcp_server.py` | exactly six tools; transport via `IKIGAI_MCP_TRANSPORT` (ADR-011) |
| The Telegram client | `src/bot/main.py` | speaks MCP; never opens a database; fails closed |
| The healthcheck | `src/transport/healthcheck.py` | measures the DATA PLANE, not the surface (C-2) |
| The container | `deploy/Dockerfile`, `compose.yml` | one image, three roles |
| The drift net | `src/ikigai/tests/` | the published surface, the layering, the versioning |
| The harness specs | `specs/harness/router.md` | how an agent finds its prompt, its skill, its cadence |

## CODE MAP

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
| `Bot` | `src/bot/main.py` | the Telegram loop, owner-only |

## CONVENTIONS

- Python 3.11+, `from __future__ import annotations` at the top of every module.
- **The layering is a pyramid: `transport → services → data`.** Only
  `src/data/` knows the driver; only `src/services/` writes; the transport
  translates intent and never carries SQL. The drift net enforces it.
- **One writer per store** (ADR-037 D5). Every write carries a `revision` and
  an `idempotency_key`; a stale revision is a **409**, never a silent
  overwrite.
- **The store wins** (ADR-037 D4). On a structured field Postgres is
  canonical and the markdown is the prose it came from.
- **Contracts are Pydantic v2 strict** — `frozen=True`, `extra="forbid"` —
  imported from `src/contracts/` only. Never re-define `UEID`.
- `src/` has **no `__init__.py`**: `from src.contracts.X` needs the repo root
  on `sys.path`; `from contracts.X` needs `src/` on it. Both spellings are
  live.
- **The agent is external** (ADR-037 D7). No published file imports an LLM
  SDK, a graph library or an orchestrator. The harness is `pi`, and it is not
  in this repository.

Tooling split (do not mix):

| Subpath | Build system | Notes |
|---|---|---|
| `src/ikigai/` | **Poetry** | own `poetry.lock`; the drift net lives in `src/ikigai/tests/` |
| `src/contracts/` | **Hatchling** | own `pyproject.toml`, `uv.lock` |
| `src/data/`, `src/services/`, `src/transport/`, `src/bot/` | none | imported as `src.<pkg>.*` with the repo root on `sys.path`; linted, not installed |

Ruff: line-length 100, target py311 — `src/ruff.toml`, `src/contracts/pyproject.toml`,
`src/ikigai/pyproject.toml`.

## ANTI-PATTERNS (THIS PROJECT)

- **Never re-introduce the retired runtime** (ADR-037): no `sys_ikigai/`, no
  `src/mesh/`, no `interfaces/`, no `vibe-ops/`, no `src/agents/`, no
  `src/tuiboard/`, no `src/solverforge_calendar/`, no
  `src/ikigai/src/{agents,chat,mcp_server,plugins}`.
- **Never let a transport tool contain SQL or policy.** The transport
  translates intent; the services decide.
- **Never import the store client from outside `src/services/`.**
- **Append-only** — never delete or prune `vault/`, `strategics/`.
- **Drift tests are append-only**: never delete or weaken one; add a new file
  under `src/ikigai/tests/` instead of editing an existing guard.
- **No secret, token or connection string in a tracked file.** Every secret
  comes from the environment; `.env` is gitignored.
- **No algorithmic layer** while the architecture is still moving (ADR-037 D1).
  No PAV kernel, no hysteresis FSM, no scoring in the published tree.
- `strategics/planning-with-files/` is a vendored third-party fork with its
  own `.git/` — untracked here, never commit its contents.
- The stray shell-redirect leftovers in the repo root are **gitignored by
  shape** (a root name that is a bare identifier, or one that carries a
  character no file may legitimately contain). Leave them alone.

## COMMANDS

```bash
cd src/ikigai && poetry install && poetry run pytest -m "not e2e"   # the suite
cd src/ikigai && poetry run ruff check src/ && poetry run ruff format --check src/
cd src/ikigai && poetry run mypy -p src.ikigai.src                  # never with a path
cd deploy && docker compose up -d --build                             # the service
```

## NOTES

- **The drift net** — CI fails if a load-bearing invariant is weakened:

| File | Purpose |
|---|---|
| `src/ikigai/tests/test_canonical_scope.py` | the retired runtime stays unpublished; the canonical surface AND the vault's prose stay published; no published file imports an unpublished tree; no LLM SDK; everything the image copies is published |
| `src/ikigai/tests/test_drift_invariants.py` | the transport exposes exactly six tools; the layering holds; the UEID pattern has one source; every write carries a revision and an idempotency key |
| `src/ikigai/tests/test_gitignore_root_scope.py` | the repository root stays reachable, and no tracked file is ever ignored |
| `src/ikigai/tests/contracts/test_dom_kinds_drift.py` | the ten kinds and `KIND_TABLES` stay in sync across the contract and the SQL ends |
| `src/ikigai/tests/store/test_store_schema.py` | the SQL and the contracts agree; every migration has a reverse script; the full-text configuration precedes the index that needs it |
| `src/ikigai/tests/transport/test_bind_address.py` | the transport binds the address a CLIENT uses, and the healthcheck dials that one — not the bind host (C-2) |
| `src/ikigai/tests/services/test_artifacts_service.py` | the write envelope, the conflict contract, the idempotency gate, and the vault sync — against an in-memory double |

- **The client fails closed.** `IKIGAI_BOT_ALLOWED_CHAT_IDS` is required; an
  empty allowlist stops the bot at startup instead of turning it into a public
  write channel (C-4).
- **The healthcheck measures the data plane** (C-2): the store answers a
  query AND a client can reach the transport. A socket that returns bytes is
  not health — and neither is a socket that answers *itself* while every
  other container is refused: the check dials the address a client uses.
- **The environment is the contract.** `.env.example` names every variable
  the published code reads — `IKIGAI_STORE_DSN` above all, without which the
  service refuses to start. Nothing comes from a file.
- **UEID drift is real** — the shipped `_UEID_PATTERN` is a wider
  triple-pattern (4-part short | 4-part long-UUID | 5-part legacy), so it
  does **not** match the canonical literal
  `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`. The 5-part branch exists
  only to READ rows written before ADR-014; it is never written. Never
  re-define `UEID` — extend the canonical one.
- **Windows quirks:** `sys.stdin.readline()` hangs on Windows pipes — use
  `sys.stdin.buffer.readline()`; pytest-asyncio `PermissionError
  [WinError 5]` on stale temp dirs → `src/ikigai/tests/conftest.py`
  redirects `tempfile.tempdir` to `data/pytest-tmp/`.
- **Version pins that bite:** `mcp` is pinned `<2` (2.x dropped
  `mcp.server.fastmcp`).
- **Commit conventions:** branch from `main`, never push to `main`;
  conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`,
  `test:`). No secrets in the repo.
