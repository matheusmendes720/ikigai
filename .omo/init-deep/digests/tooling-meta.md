# DIGEST — subtree `tools/ scripts/ taskwarrior/ life/ plugins/ examples/ bin/ .github/`

Scope owner: writer node for the tooling-and-meta subtree. Inputs: chunk
reports `c19.md`, `c20.md` (c21 had no report — its scope was re-scanned
directly from `.omo/init-deep/scope/c21.json`), all spot-checked against the
real tree.

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `life/AGENTS.md` | 17 | The `life` meta-package hub: app wiring, config defaults, plugin discovery, stale log dir. 80 lines. |
| `.github/AGENTS.md` | 13 | CI (5 jobs), PR-review orchestrator, issue forms, labels, wiki; 3 scripts do not compile. 80 lines. |
| `scripts/AGENTS.md` | 12 | Operator tooling: loop daemons, Paperclip servers, MCP probes, smoke driver, one-shot codemods. 78 lines. |
| `life/cli/AGENTS.md` | 10 | Console entry point, `LifeConfig`, bootstrap, test runner, logging; stdout JSON leak. 69 lines. |
| `tools/AGENTS.md` | 9 | Offline analysis + vault-mutation CLIs (backtest pipeline, vault write path). 71 lines. |
| `tools/backtest/AGENTS.md` | 9 | Backtest/drift pipeline: scenario → harness → judge → report, 7 drift kinds, baseline chain. 69 lines. |
| `taskwarrior/AGENTS.md` | 9 | Full Taskwarrior workspace: config, scripts, help system, docs, PT-BR domain model. 77 lines. |
| `life/centrals/AGENTS.md` | 8 | Pillar hubs (`task`/`knowledge`/`research`) + `BaseCentral` dispatch; two live defects. 71 lines. |

### Scoring detail (matrix applied per directory, depth ≤ 3)

| Directory | Files | Sub | Code% | Cfg | Bnd | Sym | Exp | Refs | Total | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `life` | 21 | 6 | 100% | y | y | 78 | 54 | 231 | **17** | create |
| `.github` | 21 | 4 | 74% | y | n | 82 | 73 | 61 | **13** | create |
| `scripts` | 33 | 4 | 98% | n | n | 94 | 60 | 293 | **12** | create |
| `life/cli` | 6 | 0 | 100% | y | y | 21 | 22 | 33 | **10** | create |
| `tools` | 20 | 2 | 100% | n | n | 169 | 84 | 268 | **9** | create |
| `tools/backtest` | 14 | 0 | 100% | n | n | 140 | 71 | 29 | **9** | create |
| `taskwarrior` | 48 | 6 | 14% | y | n | 9 | 9 | 22 | **9** | create |
| `life/centrals` | 5 | 0 | 100% | n | y | 32 | 19 | 9 | **8** | create |
| `plugins` | 7 | 1 | 74% | n | y | 11 | 3 | 51 | 7 | skip |
| `taskwarrior/*` children | — | — | — | — | — | — | — | — | ≤3 | skip (`docs` 0, `help` 3, `scripts` 2, `config` 0, `pwsh` 2) |
| `tools/vault` | 6 | 0 | 100% | n | n | 29 | 13 | 4 | 4 | skip (parent covers) |
| `.github/scripts` | 10 | 0 | 100% | n | n | 79 | 70 | 4 | 6 | skip (parent covers) |
| `.github/workflows` | 2 | 0 | 0% | y | n | 0 | 0 | 49 | 3 | skip (parent covers) |
| `life/plugins` | 5 | 0 | 100% | n | y | 7 | 11 | 4 | 6 | skip (parent covers) |
| `life/handlers` | 3 | 0 | 100% | n | y | 4 | 2 | 2 | 4 | skip (parent covers) |
| `plugins/paperclipai` | 7 | 2 | 74% | y | y | 11 | 3 | 13 | 5 | skip |
| `scripts/smoke` | 5 | 0 | 100% | n | n | 6 | 3 | 6 | 2 | skip (parent covers) |
| `scripts/cron` | 3 | 0 | 62% | y | n | 0 | 0 | 5 | 0 | skip (parent covers) |
| `scripts/backtest` | 1 | 0 | 100% | n | n | 0 | 0 | 9 | 2 | skip (parent covers) |
| `scripts/td_shim_build` | 1 | 0 | 100% | n | n | 1 | 0 | 4 | 2 | skip (parent covers) |
| `bin` | 1 | 0 | 100% | n | n | 3 | 2 | 2 | 5 | skip |
| `examples` (+3 children) | 4 | 3 | 0% | n | n | 0 | 0 | 4 | 3 | skip |

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **The `life` console command is the repo's user-facing entry point**, but
   `life/AGENTS.md` + `life/cli/AGENTS.md` + `life/centrals/AGENTS.md` are
   three separate files — the root file should not re-describe the CLI.
2. **Live defect (verified by running the CLI): every `life` invocation leaks
   a JSON error block to stdout.** `interfaces.cli.taskdog_app.register_taskdog_app`
   calls `typer.echo(json.dumps(...))` and *then* raises `typer.Exit`;
   `life/cli/cli.py` catches the exit with `except typer.Exit: pass`. Result:
   `python -m life.cli …` prints `{"ok": false, "error": "failed to discover
   MCP tools: …"}` before the real output, so `--json` emits two documents.
   Reproduced on `--help`, `task ls`, `knowledge read`, `research search`,
   `plugins`.
3. **Live defect (verified): `life task today` raises `NameError`.**
   `life/centrals/task.py:263` uses `TASK_BIN`, which the module never
   defines (only `TASKDOG_BIN` exists). `_run_task` is the last Taskwarrior
   path in the task central.
4. **Live defect (verified): the knowledge and research centrals always fail.**
   `knowledge.py` dispatches to `leitura`/`notes`/`mindmaps` and `research.py`
   to `research`; none is in `DEFAULT_SUBMODULES`, so the commands return
   `Submodule … not found`. Adding them to `config/life.yaml` is the fix.
5. **Three of the ten `.github/scripts` modules do not compile** (verified with
   `py_compile`): `setup_hooks.py:81` (hyphen in a `def` name),
   `test_review.py:65,121` and `type_review.py:69` (duplicate `text=True`).
   The CI job `code-review-checks` only uses `code_review*.py`, so CI is
   green — the breakage is latent.
6. **Three of the four modules `code_review.py` imports are untracked.**
   `code_review_checks.py`, `code_review_model.py` and
   `code_review_topology.py` exist on disk but are absent from
   `git ls-files`; `code_review.py` itself is tracked. A fresh clone fails
   the `code-review-checks` CI job with `ModuleNotFoundError`.
7. **`.gitignore:513` swallows every 4-letter root directory.** The pattern
   `/[a-zA-Z][a-zA-Z][a-zA-Z][a-zA-Z]` matches `life`, `data`, `docs` and
   `logs`; git never descends into a matched directory, so new files there are
   silently untracked. Only `src/` has a negation (`!/src/`, line 522).
   `git add -f` is required for new files under `life/`.
8. **`tools/` and `scripts/` are namespace packages, not importable
   distributions.** Cross-module imports are absolute
   (`from tools.backtest.X import …`) and require the repo root on
   `sys.path`; `tools/backtest/`, `tools/vault/`, `scripts/` and
   `.github/scripts/` have no `__init__.py`.
9. **The drift pipeline is a CI gate.** `tools/backtest/drift_regression.py
   check` exits 1 on regression (any drift kind growing >10% relative, or a
   new kind appearing 0 → >0). It compares relative growth only — absolute
   counts grow with the corpus.
10. **The vault write path lives in `tools/backtest/vault_propagation.py`**,
    not in `sys_ikigai/vault/`. It is preview-gated (`preview` then `apply`),
    refuses on an inexact checkbox match, and appends to
    `vault/.vault_events.jsonl` with `INVARIANT_MARKER = "VAULT_WRITE_INVARIANT"`.
    `tools/vault/` is a thin CLI façade over it.
11. **Taskwarrior is no longer the task store.** `taskdog-server` on
    `http://127.0.0.1:8000` replaced it (M83/M112), but `taskwarrior/scripts`
    is still the `task_scripts` path that `life task daily-review`,
    `weekly-review` and `metrics` execute.
12. **Two local HTTP servers collide on port 8765** —
    `scripts/paperclip-dashboard.py` (FastAPI) and
    `scripts/paperclip_heartbeat_http.py` (stdlib). The PaperclipAI *bridge*
    uses 8741 (`LIFE_PAPERCLIP_PORT`).
13. **`plugins/` (repo root) is TypeScript, not a `life` plugin dir.** It
    holds `paperclipai/`, a PaperclipAI plugin (npm/bun, Node ≥ 20,
    `@paperclipai/plugin-sdk`). `life/plugins/loader.py` scans that directory
    too but finds nothing loadable — `life plugins` lists only `health_check`.
14. **`bin/seed-demo-tasks.py` writes to the real `data/tasks.jsonl`** via
    `CliAdapter.apply_change` with deterministic UEIDs, so it is idempotent.
    It is a manual bootstrap step, not a test fixture.
15. **`examples/` is documentation only** — three READMEs (M0 bootstrap, M1
    cron tick, M5 MCP integration) describing loop-engineering patterns under
    `.claude/`. No code.
16. **Stale artifacts to ignore**: `tools/backtest/__pycache__/` (3 CPython
    versions of the same 13 modules), `.github/scripts/__pycache__/` (4 `.pyc`),
    `life/.life/logs/life.log` (the live log dir is `<repo>/.life/logs`).
17. **Machine-locked paths**: `scripts/langgraph-dev.bat` and
    `scripts/ruvocal-start.bat` break on any other machine;
    `scripts/td_shim_build/__main__.py` hardcodes
    `C:\Users\mathe\code_space\life-oss\life`.

## VERIFICATION

- All 8 files exist on disk and are within the 30-80 line band
  (78 / 71 / 69 / 77 / 80 / 80 / 69 / 71).
- No file under this subtree had a pre-existing `AGENTS.md`; all 8 were
  created with `Write`.
- Nothing outside `tools/`, `scripts/`, `taskwarrior/`, `life/`, `plugins/`,
  `examples/`, `bin/`, `.github/` was written except this digest file.
- Every claim marked "verified" above was checked against the real tree
  (`py_compile`, `python -m life.cli …` runs, `git ls-files`,
  `git check-ignore -v`, module import scans).
