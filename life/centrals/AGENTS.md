# life/centrals

The three pillar hubs — `task`, `knowledge`, `research` — and the dispatch base
they share. Earns its own file: score 8 (5 files, 100% code, 32 symbols, 19
exports) — a distinct domain (submodule dispatch), and it is where two live
defects live.

## OVERVIEW
`BaseCentral.run_cli()` is the one dispatch path: it runs
`python -m <module> <args> --json` with the submodule's directory as cwd and
returns `{ok, stdout, stderr, data}`. `task.py` adds a second transport — HTTP
to `taskdog-server` — because the task store moved off Taskwarrior (M83/M112).

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Dispatch base | `base.py` | `BaseCentral(ABC)`, `run_cli(cwd, module, args, json_out, timeout)` |
| Task pillar | `task.py` | 12 KB; HTTP-first taskdog client + Taskwarrior-era leftovers |
| Knowledge pillar | `knowledge.py` | dispatches to `leitura`, `notes`, `mindmaps` |
| Research pillar | `research.py` | dispatches to `research` |
| Export surface | `__init__.py` | `BaseCentral`, `task_central`, `knowledge_central`, `research_central` |

## CONVENTIONS
- **Every central exports a module-level Typer app under a public alias**
  (`task_central = app`, `knowledge_central = app`, `research_central = app`);
  `cli.py` mounts those aliases.
- **Transport result shape is uniform**: `{ok, stdout, stderr, data?}` for the
  CLI path, `{ok, stdout, stderr, error?, transport}` for the HTTP path. The
  `transport` field is `"http"` or `"cli"` — the task central is the only one
  that reports it.
- **`_http_or_cli()` is HTTP-first with a CLI fallback** for the task pillar:
  it tries the HTTP call, and on `URLError` / `ConnectionError` / `OSError`
  falls back to the `taskdog` CLI subprocess. A non-network exception is
  returned as `http_failed: <msg>` with `transport: "http"` and is *not*
  retried.
- **The task central talks to `http://127.0.0.1:8000`** (`TASKDOG_HTTP_URL`),
  the same endpoint as the mesh. `ENABLE_HTTP` is the module-level kill
  switch.
- Submodule commands always pass `--json` and re-emit the parsed payload, so
  the caller sees one JSON document.

## ANTI-PATTERNS
- **`life task today` is broken.** `task.py:263` builds
  `cmd = [TASK_BIN] + args`, but `TASK_BIN` is never defined in the module
  (only `TASKDOG_BIN` is). Running it raises
  `NameError: name 'TASK_BIN' is not defined` — verified on
  `python -m life.cli task today`. `_run_task` is the only remaining
  Taskwarrior path; `add`/`start`/`done`/`ls` all use taskdog over HTTP.
- **Never assume a central's submodule is configured.** `knowledge.py`
  dispatches to `leitura`, `notes` and `mindmaps`, and `research.py` to
  `research` — none of those names is in `DEFAULT_SUBMODULES`. Every
  `life knowledge …` command therefore returns
  `{"ok": false, "error": "Submodule leitura not found"}` and every
  `life research …` returns `{"ok": false, "error": "research submodule not
  found"}` (both verified). Adding them to `config/life.yaml` is the fix.
- **Never mix the two task transports in one command.** `add`/`start`/`done`/
  `ls` are taskdog; `today`/`daily-review`/`weekly-review`/`metrics` are the
  Taskwarrior-era scripts under `taskwarrior/scripts`.
- **Never drop the `transport` key** from the task central's result — the
  caller needs to know whether the HTTP server or the CLI answered.
- `life task ls` exits 1 with `taskdog not found on PATH` when neither
  `taskdog-server` on :8000 nor the `taskdog` binary is available. That is the
  expected degraded path, not a crash.

## COMMANDS
```bash
python -m life.cli task ls [--json]
python -m life.cli task add "title" -p 5 --json
python -m life.cli knowledge read <path> [--json/--no-json]
python -m life.cli research map <url> --depth 2 [--json/--no-json]
```
