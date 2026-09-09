# M5 — IKIGAI MCP Integration

> How to invoke IKIGAI Deep Agent tools from inside the loop.

## What this milestone does

M5 wires the IKIGAI MCP server (15 tools + 6 resources) into the loop
orchestrator, so the loop can delegate research, knowledge management, and
task operations to the Deep Agent layer via MCP.

## Prerequisites

- M4 LangGraph integration complete (orchestrator prompt has graph surface)
- `src/ikigai/src/mcp_server/server.py` runs cleanly
- `ikigai.bat mcp` starts the MCP server on stdio (or `cd src/ikigai && uv run ikigai mcp` on POSIX)

## Start the MCP server

```bash
# Terminal 1 — start the MCP server (runs in background)
# On Windows:
ikigai.bat mcp

# On POSIX:
cd src/ikigai && uv run ikigai mcp

# Server listens on stdio JSON-RPC. Keep this terminal open.
```

## Test MCP handshake (no loop involvement)

```bash
# Test 1: health check (read-only, no cost)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ikigai_health"}}' \
  | ikigai.bat mcp 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); print(d['result']['content'][0]['text'])"

# Test 2: read tasks (read-only, no cost)
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"ikigai_read_tasks","arguments":{}}}' \
  | ikigai.bat mcp 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); print(d['result']['content'][0]['text'])"
```

Expected: JSON response with status OK or task list.

## Invoke from orchestrator prompt (inside loop-tick.sh)

The orchestrator prompt (`.claude/agents/loop/orchestrator.md`) now includes
the IKIGAI tool surface section (added in M5 acceptance criterion #1).
A worker can ask the orchestrator to delegate:

```
ikigai_read_tasks project_id="ikigai" limit=5
```

This spawns the MCP server subprocess, sends the JSON-RPC request, and
returns the result to the worker.

## Available IKIGAI tools (15 total)

| Tool | Purpose | Cost |
|------|---------|------|
| `ikigai_decompose` | Break a dream/goal into sub-UEIDs | LLM |
| `ikigai_write_tasks` | Write structured tasks to data/ | Free |
| `ikigai_read_tasks` | Read tasks from data/tasks.jsonl | Free |
| `ikigai_mesh_show` | Cross-fork UEID join (CLI/taskdog/UPI) | Free |
| `ikigai_task_create` | Create a task via TaskChange queue | Free |
| `vault_read` | Read a vault markdown file | Free |
| `vault_write` | Write to vault (sole writer per ADR-012) | Free |
| `investigation_enqueue` | Add to investigation queue | Free |
| `investigation_status` | Check investigation status | Free |
| `investigation_complete` | Mark investigation resolved | Free |
| `taskdog_read` | Read from taskdog SQLite | Free |
| `taskdog_list` | List taskdog tasks | Free |
| `taskdog_supports_field` | Check UPI field support | Free |

## Test the integration end-to-end

```bash
# From repo root, run the M5 smoke test
cd src/ikigai
uv run pytest tests/test_m5_ikigai_mcp_integration.py -v

# Expected: 1 test, PASS
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| MCP server hangs on stdin | Use `sys.stdin.buffer.readline()` — NOT `sys.stdin.readline()` on Windows (commit b93a1f3) |
| `ikigai: command not found` | Run from `src/ikigai/` directory or use `python -m ikigai` |
| JSON-RPC parse error | Ensure newline-delimited JSON (NDJSON) on stdio; no pretty-print |
| Connection refused | MCP server takes ~2s to start; add sleep before first call |

## What to check after M5

- [ ] `ikigai_health` returns `{"status": "ok"}`
- [ ] `ikigai_read_tasks` returns task list
- [ ] Orchestrator prompt has "IKIGAI MCP Tool Surface (M5)" section
- [ ] `test_m5_ikigai_mcp_integration.py` PASS
