# AGENTS.md — `src/ikigai/src/`

**Canonical scope (ADR-037).**

## OVERVIEW

This directory used to hold the whole IKIGAI agent runtime (`agents/`,
`chat/`, `mcp_server/`, `plugins/`, `observability/`) — a LangGraph harness
with its own MCP servers and a tracing stack. That harness is **not
published** any more: the serverless scope keeps the **data layer
canonical** and exposes the agent surface through
`src/transport/mcp_server.py` (ADR-011), while the agent layer stays
planner-only (ADR-013).

What remains here is the **strategics loader** — the read-only bridge to the
PT-BR strategic prose (`strategics/*.md`).

## STRUCTURE

```text
src/ikigai/src/
└── strategics/
    ├── __init__.py
    ├── frontmatter_compat.py   # the YAML frontmatter shim (self-contained)
    └── loader.py               # loads strategics/*.md — NEVER writes
```

## WHERE TO LOOK

| Task | Location |
|---|---|
| Load strategic prose | `strategics/loader.py` |
| Serve the agent surface over MCP | `src/transport/mcp_server.py` (canonical transport, ADR-011) |
| The unified model | `src/contracts/dom.py` |
| The domain rules | `src/services/` |

## CONVENTIONS

- The Poetry project installs a **top-level** package name from this
  directory (currently `strategics`). Runtime imports therefore read
  `from strategics.loader import ...` — there is no `ikigai.*` prefix.
- The loader is **read-only**: it never writes to `strategics/`, the vault, or
  any data file.
- The agent layer is planner-only per ADR-013 — no PAV math, no scoring or
  policy tools.
- The frontmatter shim is **self-contained** on purpose: it imports nothing
  from the repository but PyYAML. The tree it used to live in
  (`sys_ikigai/vault/`) is unpublished, so a shim that imported from there
  would break the published package.

## ANTI-PATTERNS

- **Do not re-add an agent harness under this directory.** The canonical MCP
  surface is `src/transport/mcp_server.py`; the retired harness is gone.
- **Do not import from an unpublished tree.** Nothing under this directory
  may import `sys_ikigai` or `src.mesh` — a fresh clone does not have them.
- Do not import this directory as `src.ikigai.src.*` from production code —
  the installed import identity is the bare top-level name.

## COMMANDS

```bash
cd src/ikigai && poetry run pytest -m "not e2e" -q
```
