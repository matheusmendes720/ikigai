# scripts

Operator tooling for the loop, the agent harnesses and the CI-adjacent probes.
Earns its file: score 12 (33 files, 98% code, 94 symbols, 293 referencing files)
— the largest flat command surface outside `src/`.

## OVERVIEW
Executables, not an importable package (no `__init__.py` anywhere below). Four
subdirectories: `backtest/` (orchestrator), `cron/` (scheduler), `smoke/`
(Phase 3 e2e), `td_shim_build/` (zipapp builder); the rest are flat files.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Full backtest pipeline | `backtest/run_backtest.sh` | 10 steps; needs `taskdog-server` on :8000, exits 2 if unreachable |
| Daily backtest cron | `cron/cron-backtest.sh`, `cron/setup-task-scheduler.ps1` | logs to `.life/logs/cron-backtest.log` |
| Phase 3 e2e | `smoke/phase3_v1.sh` / `.bat` | isolated temp dir, never touches `data/` |
| Mesh smokes | `smoke/mvp_marco.py`, `mvp_marco_cli.py`, `cli_dedup.py` | self-executing, `main() -> int` |
| `td` launcher | `td` | extension-less shim → `src.mesh.taskdog_cli:main` |
| MCP contract probe | `mcp_inspect.py` (+ `mcp-inspect.bat`) | asserts `IKIGAI_TOOLS == 12`; CI job `mcp-gateway-contract` |
| Live MCP handshake | `mcp_probe.py` | spawns the server, calls `tools/call` |
| LangGraph dev | `chat.py`, `chat_repl.py` | `chat.py` has `graphs/schema/run/chat/mcp/taskdog/e2e` subcommands |
| Paperclip | `paperclip-dashboard.py`, `paperclip_heartbeat_http.py`, `paperclip-spawner.sh` | FastAPI vs stdlib server — see ANTI-PATTERNS |
| Loop daemons | `auto-start-loop-tick.sh`, `cost-dashboard.sh`, `streak-tracker.sh`, `notify.sh`, `dispatch.sh`, `worktree-helper.sh` | pure bash + awk by spec |
| One-shot codemods | `m156_stub_pav.py`, `m158d_remove_m156_stubs.py`, `m158e_inject_anthropic_shim.py` | historical, edit files in place |

## CONVENTIONS
- Bash scripts: `set -euo pipefail`; `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"`,
  then `REPO_ROOT="$SCRIPT_DIR/.."`. **Exit code 2 means "needs human
  intervention"** — the notify channel branches on the code, never on file text.
- Every meaningful `.sh` has a `.bat` twin. The twins set `PYTHONPATH`
  explicitly (`mcp-inspect.bat` sets `%REPO_ROOT%;%REPO_ROOT%\src\ikigai\src`)
  because `make` is not on PATH under cmd/PowerShell.
- Scripts that import product code bootstrap `sys.path` first, so the late
  imports carry `# noqa: E402`.
- `from __future__ import annotations` is used in 9/10 Python scripts; the
  exception is `m156_stub_pav.py`.
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
- **Never ship a real token.** `paperclip_heartbeat_http.py` defaults
  `HEARTBEAT_TOKEN="dev-token-do-not-use-in-prod"`; prod must override. In
  `notify.sh` the ntfy topic name *is* the secret — use 16+ unguessable chars.
- **Never grow the notify state file by cleanup.** It is append-only and
  hash-deduplicated; periodic cleanup is explicitly out of scope.
- **Never assume a POSIX path on Windows.** `worktree-helper.sh` translates
  Cygwin `/c/Users/...` → `C:/Users/...` via `cygpath -m` before `git -C`.
- **Never run both Paperclip servers at once.** `paperclip-dashboard.py`
  (FastAPI) and `paperclip_heartbeat_http.py` (stdlib `http.server`) both
  default to port 8765 and collide.
- **Never re-run the one-shot codemods.** `m156_*`, `m158d_*`, `m158e_*` have
  no `--dry-run` and are not idempotent-guarded; they rewrite prompt files.
- **Never import a test fixture from production.** `chat_repl.py` imports
  `src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server`.
- `mcp_inspect.py` imports `from src.agents.tools import IKIGAI_TOOLS` — a
  *different* import root than `src.ikigai.src.agents`. That is deliberate
  (the drift assertion checks the other identity); do not "fix" it.
- `scripts/langgraph-dev.bat` and `scripts/ruvocal-start.bat` hardcode
  machine-specific absolute paths and break on any other machine.

## COMMANDS
```bash
bash scripts/backtest/run_backtest.sh [--skip-gen]
bash scripts/cron/cron-backtest.sh
bash scripts/smoke/phase3_v1.sh          # Windows: scripts\smoke\phase3_v1.bat
python scripts/smoke/mvp_marco.py
python scripts/mcp_inspect.py
bash scripts/cost-dashboard.sh [--dry-run]   # exit 2 on a >$10/day spike
bash scripts/streak-tracker.sh [--dry-run]   # exit 2 on a streak break
```
