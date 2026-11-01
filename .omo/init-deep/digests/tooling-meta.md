# DIGEST — tooling-meta subtree (.github/, life/, scripts/, taskwarrior/, tools/)

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `.github/AGENTS.md` | 13 | CI + PR-review automation: 5-job workflow, 8-package quality-gates matrix, 10-module review orchestrator |
| `life/AGENTS.md` | 11 | The `life` console-command hub (Typer): centrals, handlers, plugins, config, logging |
| `life/centrals/AGENTS.md` | 11 | Pillar dispatch — `BaseCentral.run_cli` plus task/knowledge/research; taskdog HTTP transport |
| `life/cli/AGENTS.md` | 11 | The Typer app, config dataclass, console bootstrap and test runner behind `python -m life.cli` |
| `taskwarrior/AGENTS.md` | 13 | Full Taskwarrior workspace: taskrc template, 54 shell aliases, help system, PT-BR docs |
| `scripts/AGENTS.md` | 9 | Operator executables (not a package): loop daemons, backtest orchestrator, cron driver, smoke drivers |
| `tools/AGENTS.md` | 9 | Operator CLIs: the backtest/drift pipeline plus the vault write façade |
| `tools/backtest/AGENTS.md` | 9 | Deterministic scenario → harness → judge → report pipeline behind the drift-regression gate |

Scores: files = `git ls-files <dir>` minus subtree AGENTS.md; own config = a config file at the dir root or a `config/` subtree; symbols = AST module-level defs/classes/assignments + shell/PowerShell function definitions; exports = public module-level names + `__init__` re-exports; refs = distinct tracked files outside the dir matching its module paths/entry points (`git grep -l`).
`.github/` = files 21 (>20, +3) + subdirs 4 (+0) + code 16/21 = 76% (>70, +2) + own config `labels.yml` (+1) + no `__init__.py` (+0) + symbols 98 (>30, +2) + exports 71 (>10, +2) + refs 47 (>20, +3) = **13**.
`life/` = files 20 (+0) + subdirs 5 (+0) + code 20/20 = 100% (+2) + no own config (+0) + `life/__init__.py` (+2) + symbols 90 (+2) + exports 49 (+2) + refs 63 (+3) = **11**.
`life/centrals/` = files 5 (+0) + subdirs 0 (+0) + code 100% (+2) + no own config (+0) + `__init__.py` (+2) + symbols 36 (+2) + exports 21 (+2) + refs 23 (+3) = **11**.
`life/cli/` = files 6 (+0) + subdirs 0 (+0) + code 100% (+2) + no own config (+0) + `__init__.py` (+2) + symbols 31 (+2) + exports 22 (+2) + refs 69 (+3) = **11**.
`scripts/` = files 20 (+0) + subdirs 4 (+0) + code 19/20 = 95% (+2) + no own config (+0) + no `__init__.py` (+0) + symbols 36 (+2) + exports 12 (+2) + refs 42 (+3) = **9**.
`taskwarrior/` = files 48 (>20, +3) + subdirs 11 (>5, +2) + code 15/48 = 31% (+0) + own config `config/taskrc.template` (+1) + no `__init__.py` (+0) + symbols 166 (+2) + exports 38 (+2) + refs 24 (+3) = **13**.
`tools/` = files 20 (+0) + subdirs 2 (+0) + code 20/20 = 100% (+2) + no own config (+0) + no `__init__.py` (+0) + symbols 226 (+2) + exports 99 (+2) + refs 54 (+3) = **9**.
`tools/backtest/` = files 14 (+0) + subdirs 0 (+0) + code 14/14 = 100% (+2) + no own config (+0) + no `__init__.py` (+0) + symbols 190 (+2) + exports 89 (+2) + refs 38 (+3) = **9**.
All eight sit in the 8-15 band and are distinct domains.

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `tools/vault/` | 9 | `tools/AGENTS.md` WHERE TO LOOK + ANTI-PATTERNS — 6 CLI modules over the vault write path; create band, root file may promote |
| `life/plugins/` | 4 | `life/AGENTS.md` — `PluginProtocol`, loader, `builtin/health_check.py` |
| `life/handlers/` | 4 | `life/AGENTS.md` — daily/weekly flows |
| `.codex/` | 3 | root AGENTS.md — `config.toml` + `hooks.json` |
| `scripts/smoke/` | 2 | `scripts/AGENTS.md` — `phase3_v1.sh`/`.bat` + `cli_dedup.py` |
| `scripts/backtest/` | 2 | `scripts/AGENTS.md` — `run_backtest.sh` |
| `scripts/td_shim_build/` | 2 | `scripts/AGENTS.md` — zipapp builder for `td.exe` |
| `bin/` | 2 | root AGENTS.md — `seed-demo-tasks.py` seeder |
| `examples/` | 0 | root AGENTS.md — 4 read-only READMEs |
| `scripts/cron/` | 0 | `scripts/AGENTS.md` — `cron-backtest.sh` + `setup-task-scheduler.ps1` + `README.md` |

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **CI has 5 jobs, the quality-gates matrix has 8 packages, the review orchestrator knows 5.** `.github/workflows/ci.yml` (353 lines) declares `code-review-checks`, `quality-gates`, `review-queue-worker-contract`, `backtest-pipeline`, `drift-regression`; the matrix lists ikigai, vibe-ops, interfaces-cli, src-contracts, src-mesh, src-data, src-services, src-transport. `.github/scripts/code_review_topology.py::PACKAGES` holds only the first five — `src-data`, `src-services`, `src-transport` get no review bucket.
2. **Two `life` console scripts and one `td` script are declared across two pyprojects.** Root `pyproject.toml` → `life = "life.cli:_main_console"`, `td = "src.mesh.taskdog_cli:main"`; `interfaces/cli/pyproject.toml` → `life = "interfaces.cli.read_tasks:app"`. `python -m life.cli` reaches the same Typer app via `life/cli/__main__.py`.
3. **`scripts/` holds 21 tracked files (20 excluding its own AGENTS.md) and no `__init__.py` below the root.** 4 subdirs (`backtest/`, `cron/`, `smoke/`, `td_shim_build/`) plus 10 `.sh`, 5 `.py`, 2 `.bat`, 1 `.ps1`, the extension-less `td` launcher, `cron/README.md`. `scripts/cron/` = `cron-backtest.sh` (daily driver → `reports/backtest-Q1.md`, log `.life/logs/cron-backtest.log`), `setup-task-scheduler.ps1` (Task Scheduler, daily 06:00), `README.md`. Only `scripts/td` and `scripts/td_shim_build/__main__.py` resolve `src.mesh.*`. **ABSENCE:** the PC-only harness surface (local REPL, stdio MCP probe scripts, `langgraph-dev.bat`) is not in `scripts/`.
4. **`tools/backtest/llm_judge.py` falls back to the deterministic stub on four conditions.** `judge_scenario_llm` returns `_stub_score` when `use_llm` is false, when `IKIGAI_FAKE_LLM=1` (line 194), when `langchain_anthropic` is not importable (`_LANGCHAIN_AVAILABLE`, line 196), or when `_is_real_llm_available()` is false — which needs `ANTHROPIC_API_KEY` **or** `CLAUDE_API_KEY` (lines 219-222). `tools/AGENTS.md` names only `ANTHROPIC_API_KEY`.
5. **`tools/` is imported by 26 tracked tests, not by one ignored CLI shim.** `git grep -l -E "^from tools\." -- tests` returns 26 files (e.g. `tests/test_vault_propagation.py`); CI and `scripts/backtest/run_backtest.sh` drive the pipeline. `interfaces/cli/v2.py` — named by `tools/AGENTS.md` as the only external consumer — is gitignored (`.gitignore:651`), so it is not in the canonical tree.

## VERIFICATION

- `git ls-files` per dir (counts include each subtree's AGENTS.md): `.github` 22, `life` 23, `life/centrals` 6, `life/cli` 7, `scripts` 21, `taskwarrior` 49, `tools` 22, `tools/backtest` 15; skipped dirs: `tools/vault` 6, `life/plugins` 5, `life/handlers` 3, `scripts/cron` 3, `scripts/smoke` 3, `bin` 1, `examples` 4, `.codex` 2.
- `git ls-files` on purged paths returns 0: `interfaces/tui`, `src/tuiboard`, `vibe-ops/vibeops-tui`, `src/ikigai/src/mcp_server`, `src/ikigai/src/agents`, `langgraph.json`, `plugins`, `.claude-flow`, `archive/legacy-pav`; `src/transport/mcp_server.py` exists.
- AST pass over tracked `.py` files (symbols/exports) + `git grep -l` (reference centrality) + `python -m py_compile` over the 10 `.github/scripts/*.py` → exit 0.
- `ci.yml` read directly: 5 job keys, 8 matrix `package:` entries; `code_review_topology.py::PACKAGES` = 5. `pyproject.toml` `[project.scripts]` read for root + `interfaces/cli/`. `llm_judge.py` read at lines 188-223.
- `git status --porcelain`: ` M tests/AGENTS.md`, ` M tests/conftest.py` (another group's in-flight edits; `.omo/` is gitignored). This digest is the only file this group wrote.
- Every path named above was checked against the live tree at HEAD `2ae8478` (== `origin/main` == `origin/master`, branch `fix/ci-gates-green`).
