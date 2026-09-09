# Loop Engineering Examples

Copy-pasteable tutorials for running each milestone of the life-oss loop
engineering system.

## Contents

| File | Milestone | What it covers |
|------|-----------|----------------|
| `M0-bootstrap.md` | M0 Bootstrap | First-run loop-tick, dry-run, verifying progress.md |
| `M1-loop-engineering.md` | M1 Loop Engineering | Cron schedule, daemon-manager, notification channel |
| `M5-ikigai-mcp.md` | M5 IKIGAI MCP | MCP server startup, JSON-RPC handshake, tool invocation |

## Quick start

```bash
# Verify prerequisites
python --version   # 3.10+
claude --version  # authenticated
uv --version      # available

# M0: first tick
bash .claude/loop/loop-tick.sh --dry-run

# M1: wire cron + daemon-manager
bash .claude/loop/loop-tick.sh --cost-cap 5 --max-runtime 30

# M5: start IKIGAI MCP server
ikigai.bat mcp
```

## Architecture overview

```
loop-tick.sh (heartbeat cron)
  └─> orchestrator prompt (claude --agent loop-orchestrator)
        ├─> loop-worker (implements task in worktree)
        ├─> loop-verifier (scores diff, runs gates)
        │     └─> risk-tier system (shallow/deep based on file risk)
        └─> MCP gateway (IKIGAI tools accessible to worker)
              ├─> ikigai_read_tasks / ikigai_write_tasks
              ├─> vault_read / vault_write
              └─> investigation_enqueue / status / complete
```

## Common commands

```bash
# Check daemon status
bash .claude/helpers/daemon-manager.sh status

# View latest tick log
tail -20 .claude/loop/logs/tick-$(date +%Y%m%d).log

# Check progress
tail -5 .claude/loop/progress.md

# Run a single tick with verbose output
bash .claude/loop/loop-tick.sh --cost-cap 5 --max-runtime 30 --dry-run

# Cost dashboard
bash scripts/cost-dashboard.sh

# Worktree cleanup (after task close)
bash scripts/worktree-helper.sh cleanup-all
```

## Drift net (regression guard)

The drift net runs automatically in CI. To run it manually:

```bash
uv run pytest \
  src/ikigai/tests/test_drift_invariants.py \
  src/ikigai/tests/test_canonical_scope.py \
  src/ikigai/tests/test_drift_extended_invariants.py \
  -q
```

Expected: 44 passed. Any failure = regression detected.

## See also

- [`.claude/loop/constitution.md`](.claude/loop/constitution.md) — governance rules
- [`.claude/loop/roadmap.md`](.claude/loop/roadmap.md) — milestone status
- [`specs/`](specs/) — detailed SPEC.md for each milestone
