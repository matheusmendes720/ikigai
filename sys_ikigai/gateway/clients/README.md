# Fork Client Connectivity

The IKIGAI gateway (`UnifiedMCPGateway`) reaches 4 fork systems via stdio JSON-RPC 2.0.

| Fork | Binary | Default location | Wrapper module |
|---|---|---|---|
| taskdog | `taskdog.exe` | `taskwarrior/taskdog/` (or PATH) | `clients/taskdog.py` |
| solverforge-calendar | `solverforge-calendar-cli.exe` | `solverforge_calendar/dist/` (or PATH) | `clients/solverforge_calendar.py` |
| tuiboard | `bun run tuiboard-mcp.ts` | `interfaces/tui/tuiboard/` | `clients/tuiboard.py` |
| native CLI | `python -m ikigai.cli` | repo-root `src/ikigai/src/` | `clients/cli.py` |

## StdioAdapter protocol

All clients implement the `StdioAdapter` protocol:
- `bufsize=0` for unbuffered subprocess pipes
- `read1` for stderr on Windows (binary mode fix; commit b93a1f3)
- Single-writer lock per subprocess
- Hard timeout per call (default 15s; solverforge-calendar sf_replan needs 60s)
- Subprocess killed on timeout

## Fallback behavior

When binary is missing, each tool wrapper returns a warning message instead of crashing `agent.invoke()`. Already wired for solverforge + tuiboard + taskdog. The native CLI fork has a `cli_native_fallback` tool (not in `IKIGAI_TOOLS`, drift-detector-safe).

## Testing

Run `python -m pytest src/ikigai/tests/test_v2_fork_connectivity.py -v` to verify all 4 fork clients are reachable. Tests skip gracefully when binary is not installed (Windows-friendly).
