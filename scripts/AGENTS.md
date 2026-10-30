# scripts

## OVERVIEW
Operational entry points for local development and automation; score 12 because this is a distinct, highly referenced CLI/automation domain.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Inspect the live MCP gateway contract | `mcp_inspect.py` | Spawns the stdio gateway and checks tool/resource counts |
| Exercise a running LangGraph server | `chat.py` | HTTP/SSE client with `graphs`, `schema`, `run`, `chat`, `mcp`, and `e2e` commands |
| Run the local soul/profile REPL | `chat_repl.py` | Offline deterministic shell; persists through the canonical chat writer |
| Inspect or dispatch Paperclip agents | `paperclip-dashboard.py`, `paperclip_heartbeat_http.py`, `paperclip-spawner.sh` | Dashboard, heartbeat server, and cost/availability-aware spawner |
| Migrate Taskdog storage | `migrate_taskdog_schema_v2.py` | Backs up SQLite before idempotent v1-to-v2 changes; supports `--dry-run` |
| Run the canonical mesh smoke path | `smoke/phase3_v1.sh` or `.bat` | Uses an isolated temporary data tree |
| Run drift backtests | `backtest/run_backtest.sh` | Requires the local Taskdog service; supports `--skip-gen` |
| Build the local Taskdog launcher | `td_shim_build/__main__.py` | Machine-specific zipapp launcher, not a portable package |

## CONVENTIONS
- These are standalone programs, not a shared library; each owns its `main()` and CLI parsing.
- Python entry points that import repository packages bootstrap the required `src` paths before imports; preserve the `# noqa: E402` pattern.
- Shell entry points resolve the repository from `BASH_SOURCE` and use `cygpath` when passing paths to native Windows Python.
- Loop automation in `dispatch.sh`, `notify.sh`, `cost-dashboard.sh`, and `streak-tracker.sh` intentionally uses Bash plus standard tools; do not add dependencies.
- Exit status is protocol: loop monitors distinguish normal completion from a spike or failed regression.
- Smoke drivers redirect module-level paths to a temporary directory and clean it on exit; they must not touch the real `data/` tree.
- Schema-changing utilities provide dry-run behavior and preserve a backup before mutation.

## ANTI-PATTERNS
- NEVER run smoke or backtest drivers against real runtime data; use the isolated harness.
- NEVER introduce a real LLM call into `m156_stub_pav.py` or the M158 migration helpers; they exist to remove/restore stubs only.
- DO NOT revive the archived PAV kernel from these scripts; IKIGAI remains planner-only.
- DO NOT assume `scripts/td_shim_build/__main__.py` is portable; it deliberately hardcodes one Windows checkout.
- DO NOT swallow the exit-code distinction used by loop monitors; `2` is a meaningful spike/break signal.
- `chat.py` and `paperclip-dashboard.py` are known large hotspots; keep changes cohesive and preserve their documented CLI exit semantics.
