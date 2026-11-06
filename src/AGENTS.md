# AGENTS.md — `src/`

**Canonical scope (ADR-037).** This directory holds the canonical data layer:
one DOM, one store client, the domain rules, the MCP transport, and the
clients that project them.

The pre-ADR-037 runtime — the LangChain/LangGraph harness, the fork mesh,
the operator CLI, the cybernetic engine — is **unpublished**. The files stay
on the owner's disk and in the git history; they are simply not on this
branch. A drift test fails if any of them comes back.

## OVERVIEW

`src/` is a set of independent packages with different import identities and
different tooling. A file belongs to exactly one of them, and the root
`AGENTS.md` names the layers; this file records how they differ on disk.

## STRUCTURE

```text
src/
├── contracts/           # the DOM (Pydantic v2, frozen) + the vault contract family
│                       #   dom.py · dom_kinds.py · common.py · errors.py · store.py
│                       #   migrations/  the versioned SQL and its runner
├── data/                # the store client — pooled Postgres, retries, transactions
│                       #   client.py · repository.py
├── services/            # the domain rules — the ONLY writer of the store
│                       #   artifacts.py · relations.py · embeddings.py · sync.py
│                       #   wiring.py — the composition root
├── transport/           # MCP over the services (FastMCP) — ADR-011
│                       #   mcp_server.py · healthcheck.py
├── bot/                 # the Telegram client — a projection of the DOM
├── ikigai/              # Poetry project: the strategics loader + the canonical suite
├── life_tatics/         # time-block / screentime CLI (Typer)
├── planner/             # markdown-only planning notes, no code
└── ruff.toml            # the shared lint rules for the packages below
```

## WHERE TO LOOK

| Task | Location | Notes |
|---|---|---|
| The unified model | `src/contracts/dom.py` | one DOM, N projections; never re-define a field |
| Store constants | `src/contracts/store.py` | provider, schema, dimension, the DSN env var |
| Identity (`UEID`) | `src/contracts/common.py` | ADR-014, 4-part; ONE pattern, in ONE file |
| The vault contract family | `src/contracts/sonho.py`, `tarefa.py`, … | the Plan A contracts the vault prose is written against |
| The store client | `src/data/client.py` | pooled connection; **source**, not runtime state |
| Domain rules | `src/services/` | validation, versioning, idempotency, the conflict contract |
| The MCP tool surface | `src/transport/mcp_server.py` | exactly six tools, drift-guarded; transport via `IKIGAI_MCP_TRANSPORT` |
| The Telegram client | `src/bot/main.py` | speaks MCP to the transport; it never opens a database |
| Strategic prose loader | `src/ikigai/src/strategics/loader.py` | read-only |
| The canonical tests | `src/ikigai/tests/` | the drift net |

## CONVENTIONS

- **The layering is a pyramid: `transport → services → data`.** Only
  `src/data/` knows the driver; only `src/services/` writes; the transport
  translates intent and never carries SQL. The drift net enforces it.
- **`src/` is not a package.** No `src/__init__.py`. `import src.contracts.X`
  resolves because the *repository root* is on `sys.path`; `import
  strategics.X` resolves because `src/ikigai/src/` is on it. Both spellings
  are live — pick the one the surrounding package already uses.
- **One writer per store (ADR-037 D5).** Every write carries a `revision` and
  an `idempotency_key`; a stale revision is a **409**, never a silent
  overwrite.
- **The store wins (ADR-037 D4).** On a structured field Postgres is
  canonical and the markdown is the prose it came from.
- **One DOM, N projections (ADR-037 D2).** The model is shared; every client
  decides how to render it. No field of the interface belongs in the
  contract.
- **The agent is external (ADR-037 D7).** No published file imports an LLM
  SDK, a graph library or an orchestrator. The harness is `pi`, and it is not
  in this repository.
- **Ruff config is per-package, not inherited.** The real configs are
  `src/ruff.toml` (the packages without their own), `src/contracts/pyproject.toml`
  and `src/ikigai/pyproject.toml` — all `line-length = 100`,
  `target-version = "py311"`.
- **`from __future__ import annotations`** at the top of every module.

## ANTI-PATTERNS

- **Never re-introduce the retired runtime** (ADR-037): no `sys_ikigai/`, no
  `src/mesh/`, no `interfaces/`, no `vibe-ops/`, no `src/agents/`, no
  `src/tuiboard/`, no `src/solverforge_calendar/`, no
  `src/ikigai/src/{agents,chat,mcp_server,plugins}`.
- **Never let a transport tool contain SQL or policy.** The transport
  translates intent; the services decide.
- **Never import the store client from outside `src/services/`.** The
  transport asks the service layer for its wiring; it does not build it.
- **Never re-define `UEID`.** Extend the canonical pattern in
  `src/contracts/common.py` — and only there.
- **Never write to `vault/` from code.** The vault is prose; the store is
  canonical.
- **Never let a published guide describe a tree the branch does not publish.**
  The `src/planner/` notes are gone with the pre-ADR-037 scope: a guide that
  still lists them sends a cold agent looking for files that are not there.

## COMMANDS

```bash
cd src/ikigai && poetry run pytest -m "not e2e" -q
cd src/ikigai && poetry run ruff check src/ && poetry run ruff format --check src/
cd src/ikigai && poetry run mypy -p src.ikigai.src
```
