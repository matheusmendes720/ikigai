# M0 — Bootstrap

> How to run the loop tick for the first time.

## What this milestone does

M0 establishes the minimal loop infrastructure: the `loop-tick.sh` heartbeat,
`daemon-manager.sh` process supervisor, and the `constitution.md` governance
contract. It does NOT run an orchestrator prompt — it just proves the shell
scripts execute cleanly.

## Prerequisites

- Git Bash / MINGW64 / MSYS2 (Windows) or any POSIX shell (Linux/macOS)
- Python 3.10+ on PATH as `python`
- `claude` CLI installed and authenticated (`claude --version` works)
- `uv` installed (`uv --version` works)
- Bash scripts executable: `chmod +x .claude/loop/loop-tick.sh`

## Run

```bash
# 1. Verify scripts are executable
ls -la .claude/loop/loop-tick.sh
ls -la .claude/helpers/daemon-manager.sh

# 2. Dry-run the tick (no cost, no agent spawn)
bash .claude/loop/loop-tick.sh --dry-run

# 3. Check progress.md exists (created on first tick)
cat .claude/loop/progress.md  # should exist after first tick

# 4. Run a real tick (costs USD from your Claude budget)
#    Leave --cost-cap and --max-runtime at defaults for first run.
bash .claude/loop/loop-tick.sh --cost-cap 1 --max-runtime 10

# 5. Verify progress.md was appended
tail -10 .claude/loop/progress.md
```

## Expected output

```
[2026-09-09T...] Loop tick starting (id=..., cost_cap=$1, max_runtime=10min)
[2026-09-09T...] DRY RUN — would invoke orchestrator with: ...
[2026-09-09T...] Tick done (exit=0)
```

After a real tick, `progress.md` will have a new `##` entry with verdict,
cost, duration, and model used.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `timeout: not found` | Install GNU coreutils; on Windows Git Bash `timeout` is included |
| `claude: command not found` | `pip install claude` or download from claude.ai |
| `set -euo pipefail` aborts | Some older bash lacks `pipefail`; `loop-tick.sh` guards `$()` subshells with `|| true` |
| Python subprocess fails on Windows | `loop-tick.sh` honors `$PYTHON` env var; set `PYTHON=python.exe` if needed |

## What to check after M0

- [ ] `progress.md` has at least one `##` entry
- [ ] `daemon-manager.sh status` shows loop-tick as managed
- [ ] No ERROR or FAIL lines in `progress.md`
