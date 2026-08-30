# Interface TUI — Consumer Applications

TUI apps here are **pure consumers** of `data/tasks.jsonl`.
They read structured tasks and write user feedback to `data/feedback.jsonl`.
They **never write to vault/** — only the Deep Agent does.

## Architecture

```
vault/ (markdown — source of truth)
  → Deep Agent (interprets, applies PAE/strategics)
    → data/tasks.jsonl (structured tasks)
      → TUI apps (render, let user mark done)
        → data/feedback.jsonl (done/priority changes)
          → Deep Agent (reads feedback, updates planning)
```

## Planned TUIs

| App | Focus | Tech |
|-----|-------|------|
| `daily-view` | Today's tasks + regime + Q_HE | Textual |
| `kanban` | Gantt / board view by horizon | Textual |
| `calendar` | Wave/sprint calendar | Textual |

## Contracts

All TUIs import task schemas from `src/contracts/`:

```python
from contracts import Task, Period, Priority
```

## Feedback Protocol

When a user marks a task done in any TUI:

```json
{"id": "abc12345", "action": "done", "date": "2026-08-27", "source": "tui_daily"}
```

Lines appended to `data/feedback.jsonl` — Deep Agent reads this to update planning.

---

> **SUPERSEDED — 2026-08-30**
>
> This README describes interfaces/tui/ as user-facing consumer apps (daily/kanban/calendar). That framing is **stale** per the canonical dual-layer architecture ([[interfaces-architecture-2026-08-27]]):
>
> - **User-facing views** live in the **forks** (tuiboard / taskdog / solverforge-calendar), not in `interfaces/tui/`.
> - **`interfaces/tui/`** is **native backend control plane ONLY** (operator tools: server ls/inspect/status, gateway health, queue worker status).
>
> The forked kanban/calendar/daily apps (user views) are installed separately and are NOT built under this directory. Until the operator-control TUI is actually built (current phase B2 scaffold only), this folder is empty by design. See `docs/diagnostics/2026-08-30-backend-topology-diagnosis/README.md` §2 for the layer-4 status matrix.
>
> Append-only invariant preserved (no delete).
