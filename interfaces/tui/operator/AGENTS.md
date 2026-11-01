# interfaces/tui/operator

Textual control-plane dashboard for the mesh. Earns its file: distinct domain
(terminal TUI, not the Typer CLI), complexity score 8.

## OVERVIEW
`OperatorApp` — a Textual `App` showing fork adapters, backend processes, the
pending review queue, live tasks, and kill-switch state.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| App shell, tabs, auto-refresh | `app.py` | 460 lines; reactive `active_tab` |
| Row loaders (filesystem-derived) | `data.py` | adapters / backend / queue / task rows |
| Kill switch tab + banner | `_kill_switch_tab.py` | 5th tab; shells out to the CLI |
| Stylesheet | `styles.tcss` | Textual CSS, one class per widget |
| Docs | `README.md` | stale — see ANTI-PATTERNS |
| Tests | `tests/` | patches the taskdog adapter to a temp SQLite path |

## CONVENTIONS
- Five tabs, switched by the `active_tab` reactive: `tasks`, `adapters`,
  `backend`, `queue`, `kill_switch`. Keys `1`-`5`, `r` refresh, `q` quit.
- Two refresh cadences: the Tasks tab polls `data/tasks.jsonl` every 2s by
  mtime; every other tab refreshes every 5s.
- Rows are derived from the filesystem and pidfiles, never from a live query —
  `data.py` is the only loader module.
- The adapter registry here is a deliberate copy of `interfaces.cli.server`'s
  `ADAPTER_REGISTRY`, not a shared import (acknowledged duplication).
- Entry point: `python -m interfaces.tui.operator`.

## ANTI-PATTERNS
- The "Read-only — never writes to vault/, data/, or anywhere" invariant in
  `README.md` is false: the Kill Switch tab spawns
  `python -m interfaces.cli kill-switch pause|resume` via `subprocess.Popen`.
  Treat that README line as documentation drift, not a safety guarantee.
- `README.md` lists 3 tabs and the `app.py` docstring says "four-tab"; the
  code implements 5. Trust `app.py`, not the prose.
- `README.md` says "auto-refresh every 5s"; the Tasks tab actually polls
  every 2s.
- Do not import `interfaces.cli.kill_switch` into the TUI — the tab shells out
  on purpose, keeping the CLI the single kill-switch surface.
- Subprocess launches are fire-and-forget `Popen` with failures swallowed; a
  failed pause/resume does not surface to the user.

## COMMANDS
```bash
python -m interfaces.tui.operator
python -m pytest interfaces/tui/operator/tests -v
```
