# scripts

Operator tooling for the loop, the scheduler and the CI-adjacent probes.
Twenty tracked files, all of them executables — this directory is not an
importable package (no `__init__.py` below the root).

**Serverless scope (ADR-037, 2026-11-01):** the PC-only harness tooling is
not published. There is no `chat.py` / `chat_repl.py` REPL, no
`mcp_inspect.py` / `mcp_probe.py` probe, no Paperclip dashboard or heartbeat
server and no `langgraph-dev.bat`. What remains is the loop tooling, the
backtest pipeline, the smoke drivers and the taskdog launchers.

## OVERVIEW
Four subdirectories: `backtest/` (orchestrator), `cron/` (scheduler), `smoke/`
(Phase 3 e2e), `td_shim_build/` (zipapp builder); the rest are flat files.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Full backtest pipeline | `backtest/run_backtest.sh` | needs `taskdog-server` on :8000, exits 2 if unreachable |
| Daily backtest cron | `cron/cron-backtest.sh`, `cron/setup-task-scheduler.ps1` | logs to `.life/logs/cron-backtest.log` |
| Phase 3 e2e | `smoke/phase3_v1.sh` / `.bat` | isolated temp dir, never touches `data/` |
| CLI adapter dedup smoke | `smoke/cli_dedup.py` | asserts `CliAdapter.apply_change` writes one CREATE event per UEID |
| `td` launcher | `td` | extension-less shim → `src.mesh.taskdog_cli:main` |
| `td` shim build | `td_shim_build/__main__.py` | zipapp builder; hardcodes the author's repo path |
| Loop task dispatch | `dispatch.sh` | reads `.claude/loop/tasks.md`, runs worker → verifier → commit → push |
| Session-start hook | `auto-start-loop-tick.sh` | idempotent; wired into the `SessionStart` hook chain |
| Loop daemons | `cost-dashboard.sh`, `streak-tracker.sh`, `notify.sh`, `worktree-helper.sh` | pure bash + awk by spec |
| Paperclip auto-spawner | `paperclip-spawner.sh` | polls `.claude/loop/inbox/`, dispatches one run per spec |
| taskdog schema migration | `migrate_taskdog_schema_v2.py` | M163: `tasks.db` v1 → v2 (tags, deps, audit_log, …) |
| One-shot codemods | `m156_stub_pav.py`, `m158d_remove_m156_stubs.py` | historical, edit files in place; the harness prompt files they patched are not published anymore, so both are inert |
| Ruvocal launcher | `ruvocal-start.bat` | machine-locked absolute paths |

## CONVENTIONS
- Bash scripts: `set -euo pipefail`; `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"`,
  then `REPO_ROOT="$SCRIPT_DIR/.."`. **Exit code 2 means "needs human
  intervention"** — the notify channel branches on the code, never on file text.
- Every meaningful `.sh` has a `.bat` twin where Windows needs one.
- Scripts that import product code bootstrap `sys.path` first, so the late
  imports carry `# noqa: E402`.
- `from __future__ import annotations` is used in every Python script here.
- Reruns are byte-identical except a `generated_at` line.
- `scripts/td` and `scripts/td_shim_build/__main__.py` are the only two entry
  points that resolve `src.mesh.*` — keep the dotted-prefix form.

## ANTI-PATTERNS
- **Never let a loop script fail the session.** `auto-start-loop-tick.sh` must
  always exit 0; a missing `daemon-manager.sh` is a silent no-op.
  `paperclip-spawner.sh` treats unknown args as warnings, not errors.
- **Never write Python into the loop bash scripts.** `cost-dashboard.sh`,
  `notify.sh`, `streak-tracker.sh`, `worktree-helper.sh` are bash + awk/curl
  only, by M6/M7/M8 spec.
- **Never ship a real token.** In `notify.sh` the ntfy topic name *is* the
  secret — use 16+ unguessable chars.
- **Never grow the notify state file by cleanup.** It is append-only and
  hash-deduplicated; periodic cleanup is explicitly out of scope.
- **Never assume a POSIX path on Windows.** `worktree-helper.sh` translates
  Cygwin `/c/Users/...` → `C:/Users/...` via `cygpath -m` before `git -C`.
- **Never re-run the one-shot codemods.** `m156_*` and `m158d_*` have no
  `--dry-run` and are not idempotent-guarded; they rewrite prompt files in
  place.
- **Never re-introduce a harness script here** (ADR-037): no REPL, no MCP
  probe, no local gateway launcher. The published client surface is
  `src/transport/mcp_server.py`.
- `scripts/ruvocal-start.bat` and `scripts/td_shim_build/__main__.py` hardcode
  machine-specific absolute paths and break on any other machine.

## COMMANDS
```bash
bash scripts/backtest/run_backtest.sh [--skip-gen]
bash scripts/cron/cron-backtest.sh
bash scripts/smoke/phase3_v1.sh          # Windows: scripts\smoke\phase3_v1.bat
python scripts/smoke/cli_dedup.py
python scripts/migrate_taskdog_schema_v2.py --db data/tasks.db
bash scripts/cost-dashboard.sh [--dry-run]   # exit 2 on a >$10/day spike
bash scripts/streak-tracker.sh [--dry-run]   # exit 2 on a streak break
```
