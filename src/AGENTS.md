# AGENTS.md — `src/`

**Score 15 — distinct domain: the published data layer, split into five packages with five toolchains.** The root `AGENTS.md` names the layers and the four rules; this file records how the packages differ on disk.

## OVERVIEW

`src/` holds five independent packages — `contracts`, `data`, `services`,
`transport`, `bot` — plus the Poetry project `ikigai` (the strategics loader
and the canonical suite). Each package has its own import identity, its own
lint config and its own entry points. A file belongs to exactly one of them.

## STRUCTURE

```text
src/
├── contracts/     # the DOM (Pydantic v2, frozen) + the store's SQL
│                   #   dom.py · dom_kinds.py · common.py · errors.py · store.py · drafts.py
│                   #   migrations/  numbered up/down SQL + the checksum-locked runner
├── data/          # the store client — pooled Postgres, retries, transactions
│                   #   client.py · repository.py · drafts.py
├── services/      # the domain rules — the ONLY writer of the store
│                   #   artifacts.py · relations.py · embeddings.py · sync.py · vault_write.py
│                   #   changes.py · drafts.py · wiring.py — the composition root
├── transport/     # the MCP surface (ADR-011) + the websocket (ADR-039)
│                   #   mcp_server.py · ws_server.py · healthcheck.py
├── bot/           # the Telegram client + the Mini App — a projection of the DOM
├── ikigai/        # Poetry project: the strategics loader + the canonical suite
└── ruff.toml      # the lint rules for the packages without their own
```

## WHERE TO LOOK

| Task | Location | Notes |
|---|---|---|
| The unified model | `src/contracts/dom.py` | one DOM, N projections; never re-define a field |
| Identity (`UEID`) | `src/contracts/common.py` | ADR-014; ONE pattern, in ONE file |
| Drafts (the one hard-deleted table) | `src/contracts/drafts.py` · `src/data/drafts.py` | `Draft` · `DraftSaveRequest` · `DraftOutcome` |
| The store's SQL and its runner | `src/contracts/migrations/` | numbered up/down pairs; the runner is checksum-locked |
| The store client | `src/data/client.py` | pooled connection; **source**, not runtime state |
| Domain rules | `src/services/` | validation, versioning, idempotency, the conflict contract |
| The MCP tool surface | `src/transport/mcp_server.py` | exactly six tools, drift-guarded; transport via `IKIGAI_MCP_TRANSPORT` |
| The websocket sync channel | `src/transport/ws_server.py` | the same six tools, plus the store's announcements |
| The vault ingestion | `src/services/sync.py` | `python -m src.services.sync` — the prose into the store |
| The Telegram client | `src/bot/main.py` | speaks MCP to the transport; it never opens a database |

## CONVENTIONS

- **`src/` is not a package.** No `src/__init__.py`. `from src.contracts.X` needs
  the *repository root* on `sys.path`; `from contracts.X` needs `src/` on it.
  Both spellings are live — follow the package you are in.
- **Ruff config is per-package, never inherited.** The real configs are
  `src/ruff.toml` (the packages without their own), `src/contracts/pyproject.toml`
  and `src/ikigai/pyproject.toml` — all `line-length = 100`,
  `target-version = "py311"`.
- **mypy is strict only in `src/ikigai`** — `mypy -p src.ikigai.src`, never with
  a path (a path creates a second module identity and aborts with "Source file
  found twice"). The other packages are ruff-only in CI.
- **`from __future__ import annotations`** at the top of every module; Pydantic v2
  strict — `frozen=True`, `extra="forbid"`, `Literal` discriminators, `Decimal`.
- **In `services/`, `transport/` and `bot/`, the module docstring is the
  design document** — it states the rule and the failure it prevents; comments
  carry the rationale and the measured history, never the what.

## ANTI-PATTERNS

- **Never let a guide describe a tree the branch does not publish.**
  `src/life_tatics/` and `src/planner/` are gone from the published tree; a
  guide that still lists them sends a cold agent after files that are not
  there. Each package's own guide holds its rules — do not restate them here.

## COMMANDS

```bash
cd src/ikigai && poetry run pytest -m "not e2e" -q
cd src/ikigai && poetry run ruff check src/ && poetry run ruff format --check src/
cd src/ikigai && poetry run mypy -p src.ikigai.src
ruff check src/contracts                                   # its own [tool.ruff]
ruff check src/data src/services src/transport src/bot     # src/ruff.toml
```
