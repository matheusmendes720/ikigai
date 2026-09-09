# LLM Activation

How to enable the IKIGAI v2 harness against a real LLM (not `IKIGAI_FAKE_LLM=1`).

## Quick start (MiniMax proxy)

```bash
cd "C:\Users\mathe\code_space\life-oss\life\.worktrees\loop-prod-ready"

# 1. Unset fake mode
unset IKIGAI_FAKE_LLM

# 2. Set MiniMax proxy inline (do NOT add to .env or commit)
export ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
export ANTHROPIC_API_KEY=<your-key-here>

# 3. Run any skill (uses cwd=src/ikigai/src so mcp_server package resolves)
.venv/Scripts/python.exe -m interfaces.cli v2 daily --json
.venv/Scripts/python.exe -m interfaces.cli v2 weekly --json
```

After running, **always unset the key**:

```bash
unset ANTHROPIC_API_KEY ANTHROPIC_BASE_URL
export IKIGAI_FAKE_LLM=1   # back to safe default
```

## Production prerequisites

1. **Python 3.12 venv** at `.venv/` with deps installed. Typer 0.12.x required
   (compat with `ikigai 0.1.0`).
2. **mcp<2** in the venv. The MCP server uses FastMCP v1 API; mcp 2.x renamed
   `FastMCP` → `MCPServer` and the server crashes on import.
   ```bash
   C:/Users/mathe/.local/bin/uv.exe pip install --python .venv/Scripts/python.exe "mcp<2"
   ```
3. **Cost guard rails** are wired in `src/ikigai/src/agents/v2/graph.py`:
   - Per-skill token caps: daily=1000, weekly=8000, monthly=32000, quarterly=96000
   - Rate limit: 10 calls/hour via token bucket in `interfaces/cli/_v2_skills.py`
4. **MCP server subprocess wiring**: `interfaces/cli/_v2_skills.py:ensure_mcp_server_bound`
   spawns `python -m mcp_server` with `cwd=src/ikigai/src` (the inner src — NOT
   `src/ikigai`, which would shadow `<repo>/src/contracts/`). PYTHONPATH carries
   three entries: REPO_ROOT, LIFE_SRC, IKIGAI_SRC.

## Verified

Phase 10.0 PROD Tier 5 — 2026-09-09 — smoke-tested end-to-end:

| Skill | Output | Latency | Calls |
|-------|--------|---------|-------|
| `v2 daily` | `(no suggestions — empty surface_intentions)` | 32.4s | 1 |
| `v2 weekly` | `Skill: ikigai-weekly, Regime: MAINTAIN` | 3.6s | 1+ |

Drift net preserved: 44/44 PASS.

## Security

- **Never** write the API key to a tracked file. Set it as a shell env var only.
- **Never** echo the API key in commit messages, logs, or reports.
- **Always** unset the key after smoke runs.
- `.env` ships with `IKIGAI_FAKE_LLM=1` (safe default) — never commit a real key.

## Cost

~$0.005–$0.05 per `v2 daily` (1 LLM call via MiniMax proxy).
~$0.05–$0.20 per `v2 weekly` (8 LLM calls).
Hard ceiling per guard rails: 1000 tokens for daily, 8000 for weekly.
