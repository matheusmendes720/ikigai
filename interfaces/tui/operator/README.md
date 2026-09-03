# Operator TUI

Backend control-plane dashboard for the IKIGAI mesh.

## What this is

Per the dual-layer architecture (`interfaces-architecture-2026-08-27`),
this directory hosts the **operator control plane** — NOT user-facing views.

User-facing views live in the **forks** (tuiboard / taskdog / solverforge-calendar).
This TUI is for inspecting the backend topology: fork adapters, backend
processes, and the review queue.

## Launch

```bash
# From repo root
python -m interfaces.tui.operator
```

## Tabs

| Key | Tab       | Shows                                              |
|-----|-----------|----------------------------------------------------|
| 1   | Adapters  | Fork adapters (cli / taskdog / solverforge_calendar / a2ui) + storage path liveness |
| 2   | Backend   | Backend process status (mcp_gateway / review_queue_worker) + PID |
| 3   | Queue     | Pending TaskChange events in data/review_queue/   |

## Keys

- `1` / `2` / `3` — switch tabs
- `r` — refresh now (auto-refresh every 5s)
- `q` — quit

## Architecture invariants

- **Read-only** — never writes to vault/, data/, or anywhere
- **Reuses canonical registry** from `interfaces.cli.server` (single source of truth)
- **Zero LLM** — pure Python data loaders

## Future

When LLM-driven validation lands (data mesh v1.2), add a 4th tab:
"Decisions" showing APPROVE/REJECT/CLARIFY outcomes from the agent_consumer.
