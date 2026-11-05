# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Repo Is

**The service.** A personal, single-player agent system: one Postgres store that
holds the vault as typed, versioned, queryable artifacts; one MCP transport
over HTTP; one Telegram client that writes and reads through it.

**This repository IS the deployment.** There is no separate service repo, no
"backend" folder to copy out, and no framework underneath. The agent that
operates it is external — the harness is `pi`.

**Repo:** github.com/matheusmendes720/ikigai
**Project Board:** github.com/users/matheusmendes720/projects/5

---

## The product

Four pieces, and nothing else. A change that does not serve one of them is
outside the product.

| Piece | What it is | Where it lives |
|---|---|---|
| **The store** | One Postgres + pgvector. The DOM lives in the `ikig` schema. The only state. | `src/contracts/migrations/` · `src/data/` |
| **The transport** | **Our own MCP**, six tools, over HTTP. The only writer. | `src/transport/mcp_server.py` (ADR-011) |
| **The client** | Telegram. A projection of the DOM, never a fork of it. | `src/bot/main.py` |
| **The agent** | **The `pi` harness — external.** It reads the project's MCP servers from `.pi/mcp.json` and its skills from `.pi/skills/`. Nothing in this repository imports it. | `specs/harness/` · `.pi/` |

**The skills are the workflow.** `specs/harness/skills/<id>/SKILL.md` is the
published projection of the routines — `daily-note`, `weekly-review`,
`monthly-review`, `quarterly-plan`, `store-read`, `store-write`, `vault-sync`.
`pi` loads them from `.pi/skills/`, and the copy is regenerated from the
projection. The skills adapt the workflow **into the Telegram client**: a
routine is a skill the harness runs, not a subcommand a desktop CLI mounts.

**No LangGraph, no model SDK, no orchestrator in the published tree.** The
harness is `pi` and it is not in this repository (ADR-037 D7). A published file
that imports one is a drift, not a feature.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  AGENT — external, the `pi` harness                        │
│  specs/harness/skills/  ->  .pi/skills/  ->  the routines   │
│  No model SDK, no graph, no orchestrator in this tree.      │
└────────────────────────────┬────────────────────────────────┘
                             │ MCP over HTTP (our own, six tools)
┌────────────────────────────▼────────────────────────────────┐
│  CLIENTS — projections of the DOM                            │
│  Telegram (the bot) · later: TUI, web                      │
└────────────────────────────┬────────────────────────────────┘
                             │ MCP over HTTP
┌────────────────────────────▼────────────────────────────────┐
│  TRANSPORT — src/transport/                                 │
│  Six tools. Translates intent; carries no SQL, no policy.   │
└────────────────────────────┬────────────────────────────────┘
                             │ contracts (Pydantic v2 strict)
┌────────────────────────────▼────────────────────────────────┐
│  SERVICES — src/services/                                   │
│  The domain rules. The ONLY writer of the store.            │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  DATA — src/data/ + src/contracts/ + src/bot/               │
│  The DOM, the pooled Postgres client, the vault prose.       │
└─────────────────────────────────────────────────────────────┘
```

**Canonical flow:** `vault/` (prose) → `VaultSync` → the store → the transport
→ the client. The client writes back through the transport; nothing else
writes.

---

## The four rules

| # | Rule | Where it lives |
|---|---|---|
| 1 | **One writer per store.** Clients speak MCP; only `src/services/` writes. A stale revision is a **409**, never a silent overwrite. | ADR-037 D5 · `src/services/artifacts.py` |
| 2 | **One DOM, N projections.** The model is shared; every client decides how to render it. | ADR-037 D2, D8 |
| 3 | **The agent is external.** The harness is `pi`; this repository builds no framework, no graph, no orchestrator. | ADR-037 D7 |
| 4 | **The store wins.** On a structured field, Postgres is canonical and the markdown is the prose it came from. | ADR-037 D4 |

---

## Global conventions

| Rule | What it forbids |
|------|-----------------|
| **The layering is a pyramid** | `transport → services → data`. Only `src/data/` knows the driver; only `src/services/` writes; the transport never carries SQL. |
| **One writer per store** | A write without a `revision` and a non-empty `idempotency_key`. A conflict is never resolved by forcing. |
| **Pydantic v2 strict** | `frozen=True`, `extra="forbid"` on every model; `Decimal` for KPIs; `Literal` discriminators. |
| **One identity, one source** | `UEID` is defined once, in `src/contracts/common.py`. Never re-define it. |
| **No secret in the repo** | Every secret comes from the environment. `.env` is gitignored. |
| **Append-only** | Never delete or prune `vault/`, `strategics/`. |
| **Drift tests are append-only** | Never weaken a guard to make a suite green; add a new one instead. |

---

## Build / Run / Test

```bash
# The suite — the canonical entry
cd src/ikigai && poetry install && poetry run pytest -m "not e2e"

# Lint / format / typecheck
cd src/ikigai && poetry run ruff check src/ && poetry run ruff format --check src/
cd src/ikigai && poetry run mypy -p src.ikigai.src    # never invoke mypy with a path

# The service, as containers
cd deploy && docker compose up -d --build
docker compose exec api python -m src.contracts.migrations.apply up
docker compose exec api python -m src.transport.healthcheck
```

`src/ikigai/tests/conftest.py` is the single source of truth for test imports:
it puts the repository root and `src/ikigai/src/` on `sys.path`, and it
redirects `tempfile.tempdir` to `data/pytest-tmp/` to dodge the Windows
`PermissionError [WinError 5]` on stale temp dirs.

CI (`.github/workflows/ci.yml`) runs a five-package matrix — `ikigai`,
`src-contracts`, `src-data`, `src-services`, `src-transport` — over ruff,
ruff-format, mypy and pytest.

---

## Where to start

| Task | Start here |
|------|-----------|
| Understanding the system | [`README.md`](README.md) → [`AGENTS.md`](AGENTS.md) → [`code-docs/adr/ADR-037-data-layer-canonical-turn.md`](code-docs/adr/ADR-037-data-layer-canonical-turn.md) |
| Working in `src/` | [`src/AGENTS.md`](src/AGENTS.md) |
| Building a client | `src/bot/main.py` — it speaks MCP and never opens a database |
| Changing the model | `src/contracts/dom.py` + `src/contracts/dom_kinds.py` — and the drift test with it |
| Deploying | [`deploy/README.md`](deploy/README.md) |
| Driving the agent | [`specs/harness/router.md`](specs/harness/router.md) |
| Drift net | `src/ikigai/tests/test_canonical_scope.py` · `test_drift_invariants.py` · `test_gitignore_root_scope.py` |

---

## Pitfalls

- **Don't re-introduce the retired runtime.** `sys_ikigai/`, `src/mesh/`,
  `interfaces/`, `vibe-ops/`, `src/agents/`, `src/tuiboard/`,
  `src/solverforge_calendar/` and `src/ikigai/src/{agents,chat,mcp_server,plugins}`
  are unpublished. A drift test fails if any of them is tracked again.
- **Don't import the store client from outside `src/services/`.** The
  composition root lives in `src/services/wiring.py`; the transport asks the
  service layer for its wiring.
- **Don't put SQL in a transport tool.** The transport translates intent; the
  services decide.
- **Don't write algorithms yet.** ADR-037 D1 defers them: no PAV kernel, no
  hysteresis FSM, no scoring in the published tree. They come last, and they
  need real data to be worth anything.
- **Don't write to `vault/` from code.** The vault is prose; the store is
  canonical. `VaultSync` reads it and never writes back.
- **The bot fails closed.** No `IKIGAI_BOT_ALLOWED_CHAT_IDS`, no bot.
- **The healthcheck measures the data plane.** A socket that returns bytes is
  not health (contract C-2).

---

## Refactor protocol

If touching `vault/` or `strategics/`: **stop** → propose an Action Plan →
wait for explicit "go" → verify every pre-existing string survives.

---

*Algorithmic Life OS — CLAUDE.md — canonical turn (ADR-037), renewed 2026-11-02*
