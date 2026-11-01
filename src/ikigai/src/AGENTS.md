# AGENTS.md — `src/ikigai/src/`

**Score 2 (1 package, 2 tracked files) — canonical scope (ADR-037).**

## OVERVIEW
This directory used to hold the whole IKIGAI agent runtime (`agents/`, `chat/`,
`mcp_server/`, `plugins/`, `observability/`) — a LangGraph harness with its own
MCP servers and a tracing stack. That harness is **not published** anymore: the
serverless scope keeps the **data layer canonical** and exposes the agent
surface through `src/transport/mcp_server.py` (ADR-011), while the agent layer
stays planner-only (ADR-013).

What remains here is the **strategics loader** — the read-only bridge to the
PT-BR strategic prose (`strategics/*.md`).

## STRUCTURE
```
src/ikigai/src/
└── strategics/
    ├── __init__.py
    └── loader.py        # loads strategics/*.md — NEVER writes
```

## WHERE TO LOOK
| Task | Location |
|---|---|
| Load strategic prose | `strategics/loader.py` |
| Serve the agent surface over MCP | `src/transport/mcp_server.py` (canonical transport, ADR-011) |
| Planner layer (memory, reflection) | `src/agents/` (canonical, at `src/`, not here) |
| Kill-switch tuning constants | `sys_ikigai/security/algorithm_constants.json` (ADR-019 R1) |

## CONVENTIONS
- The Poetry project installs **top-level** package names from this directory
  (currently `strategics`) plus `sys_ikigai` from the repo root
  (`from = "../.."`). Runtime imports therefore read `from strategics.loader
  import ...` — there is no `ikigai.*` prefix.
- The loader is **read-only**: it never writes to `strategics/`, the vault, or
  any data file.
- The agent layer is planner-only per ADR-013 — no PAV math, no scoring or
  policy tools.

## ANTI-PATTERNS
- **Do not re-add an agent harness under this directory.** The canonical MCP
  surface is `src/transport/mcp_server.py`; the retired harness is gone.
- **Do not add tuning constants here.** The algorithm constants JSON is
  `sys_ikigai/security/algorithm_constants.json` (ADR-019 R1).
- Do not import this directory as `src.ikigai.src.*` from production code —
  the installed import identity is the bare top-level name.

## COMMANDS
```bash
python -m pytest src/ikigai/tests -q
```
