# AGENTS.md — `src/mesh/`

**Score 15 (29 files, 100% code, 169 symbols, 44 exports, imported by 89 repo files) — updated: distinct domain.** The Phase 3 cross-fork mesh: fork adapters + append-only review queue.

## OVERVIEW
Read path joins slices from the 2 published fork adapters by UEID; write path routes every mutation through `data/review_queue/` as a `TaskChange`. The calendar fork was retired with the serverless pivot (ADR-037, 2026-11-01).

## STRUCTURE
```
src/mesh/
├── queue.py                # enqueue / consume_pending / ack / replay_after_restart
├── agent_consumer.py       # validate(event) -> Decision (approve|reject|clarify)
├── agent_propagator.py     # propagate(event) -> PropagationResult per fork
├── review_queue_worker.py  # run_once / start_worker / stop_worker / worker_status
├── investigation_queue.py  # separate append-only lifecycle queue
├── taskdog_cli.py          # 1035 LOC — the main `td` CLI
├── cli/                    # td_advanced (961), td_gantt, td_tag — sub-parser modules
├── adapters/               # CliAdapter, TaskdogAdapter + a2ui_schema (calendar fork retired)
├── dep_subsystem.py        # dependency graph CRUD (separate audited subsystem)
├── gantt_engine.py / gantt_renderers.py   # pure scheduling, no I/O
├── optimizer.py / optimizer_strategies.py  # FIFO / priority-weighted / critical-path
└── taskdog_chat.py, td_dep.py, cli_cli.py, mesh_cli.py, review_queue_cli.py
```

## WHERE TO LOOK
| Task | Location |
|---|---|
| Write path | `queue.py` → `agent_consumer.validate` → `agent_propagator.propagate` → `ack` |
| Fork adapters | `adapters/` (`ForkAdapter` Protocol in `base.py`) |
| Ops CLI (`td`) | `taskdog_cli.py`; advanced verbs in `cli/td_advanced.py` |
| Cross-fork read | `mesh_cli.py show <ueid>`, `cli_cli.py`, `interfaces/cli/read_tasks.py` |

## CONVENTIONS
- **CLIs use `argparse`, not Typer** — this deviates from the repo-wide Typer rule; `--json` is still honored everywhere.
- **Output mode precedence: `--json` > `--human` > TTY default.** The resolver `_wants_human()` is duplicated in **8** modules — `taskdog_cli.py`, `cli_cli.py`, `mesh_cli.py`, `review_queue_cli.py`, `td_dep.py` and `cli/td_{advanced,gantt,tag}.py` — keep all eight in sync.
- **`cli/td_*.py` modules are sub-parser plugins**, not standalone CLIs. Each exposes `register_<x>_subparser(sub)` + `run_<x>_command(args)`; only `taskdog_cli.py` calls them, and only `cli/td_advanced.py` has its own `main()`.
- **Module-level DB globals are mutated to redirect reads.** `_apply_db_override()` rewrites `TASKDOG_DB` in place when `--db-path` is passed. Monkeypatch the module attribute, not a parameter.
- **Queue files are written atomically** (temp file + `os.replace`) with fsync and retry/backoff on transient `OSError`.
- **Almost every import here is dotted.** All 15 `contracts` imports use `from src.contracts.…` and 45 use `from src.mesh.…`. The only two exceptions are bare `from mesh.…` in `review_queue_cli.py` and `review_queue_worker.py`; those resolve only when `src/` is on `sys.path`, so a bare import is a trap outside the pytest environment.
- **`Gantt` and the optimizer are pure functions** — no I/O, no DB, no adapter access. Optimizer strategies treat dependencies as hard constraints and never mutate their inputs.

## ANTI-PATTERNS
- **`data/review_queue/` is append-only.** Never delete, rewrite, truncate, or `rmtree` it; malformed files are logged and skipped, not "repaired".
- **Adapters must not write to SQLite directly from an MCP tool.** Write tools route through `mesh.queue.enqueue()`; the drift detector permits only the queue worker a narrow acknowledgment exception.
- **Investigation records are never deleted.** `resolved` and `archived` are terminal — no outgoing transitions. Notes are append-only; there is no update/delete note verb.
- **`td chat` must never auto-execute.** It always emits a proposal and waits for `--approve`.
- **Adapter failures must not crash propagation, and missing fork data is "not present", not an exception.**
- **Never re-introduce the calendar fork.** `SolverforgeCalendarAdapter` was retired with the serverless pivot (ADR-037): `adapters/solverforge_calendar.py` is deleted and the adapter is out of `adapters.__all__`. A drift test fails if that stem reappears under `src/mesh/adapters/`.

## COMMANDS
```bash
python -m src.mesh.taskdog_cli list|status|show|timeline|add|done|update|propagate|dep|tag|gantt|optimize|tui|chat
python -m src.mesh.taskdog_cli rm <ueid> | restore <ueid> | audit | db backup | db restore <path> --yes | export json|csv|md | stats
python -m src.mesh.review_queue_worker run-once|start|stop
python -m src.mesh.td_dep add|remove|list|blocked
ruff check src/mesh          # uses src/mesh/ruff.toml
```

**Gotcha:** `rm` is a **soft** delete (`status='deleted'`, audit log preserved) and `restore` is its inverse; `db restore` is destructive and exits `2` without `--yes`.
