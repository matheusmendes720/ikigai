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
