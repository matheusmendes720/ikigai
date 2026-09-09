# M1 — Loop Engineering

> How to configure, tune, and operate the loop heartbeat.

## What this milestone does

M1 wires the loop-tick heartbeat into a cron schedule, configures the
daemon-manager as the canonical process supervisor, and sets up the
notification channel for FAIL/BLOCKED/OVERRUN alerts.

## Prerequisites

- M0 bootstrap complete (loop-tick.sh runs cleanly)
- `crontab` or task scheduler access
- `ntfy.sh` installed or a webhook endpoint for notifications
  (optional — loop runs fine without notifications, just won't alert on failure)

## Configure cron schedule

```bash
# Add loop-tick to crontab (every 60 minutes, $5 cost cap)
(crontab -l 2>/dev/null; echo "0 * * * * cd $(pwd) && bash .claude/loop/loop-tick.sh --cost-cap 5 --max-runtime 30 >> .claude/loop/logs/cron.log 2>&1") | crontab -

# Verify
crontab -l
```

On Windows Task Scheduler, create a Basic Task that runs:
```
powershell.exe -Command "bash .claude/loop/loop-tick.sh --cost-cap 5 --max-runtime 30"
```
Trigger: Daily at a convenient hour, or on a time interval of 60 minutes.

## Set up daemon-manager (canonical supervisor)

```bash
# Start loop-tick under daemon-manager
bash .claude/helpers/daemon-manager.sh start loop-tick -- bash .claude/loop/loop-tick.sh --cost-cap 5

# Check status
bash .claude/helpers/daemon-manager.sh status loop-tick

# View logs
tail -f .claude/loop/logs/tick-$(date +%Y%m%d).log
```

## Notification channel (M8 wiring)

```bash
# Set notify endpoint (uses ntfy.sh by default)
export LOOP_NOTIFY_COOLDOWN_SEC=600   # 10 min between repeated alerts
export LOOP_NOTIFY_URL=https://ntfy.sh/your-topic  # or any HTTP webhook

# Test notification
bash scripts/notify.sh --reason tick_pass --message "M1 notification test"
```

## Risk tier configuration (T-2 item)

The verifier applies different review depths based on what files changed.
For low-risk changes (tests/docs), it runs shallow review.
For high-risk changes (mcp_server, vault_write, agents), it runs deep review
with AST validation and dual-module identity checks.

This is automatic — no config needed. To override for a specific tick:

```bash
bash .claude/loop/loop-tick.sh --dry-run  # always runs verifier at shallow depth
```

## Verify M1 is operational

```bash
# 1. Daemon manager shows loop-tick as running
bash .claude/helpers/daemon-manager.sh status

# 2. Cron is registered
crontab -l | grep loop-tick

# 3. Run one tick end-to-end
bash .claude/loop/loop-tick.sh --cost-cap 1 --max-runtime 10

# 4. Check progress.md has the new entry
tail -5 .claude/loop/progress.md
```

## What to check after M1

- [ ] `daemon-manager.sh status` shows loop-tick running
- [ ] Crontab entry present
- [ ] `progress.md` has consecutive entries with PASS verdicts
- [ ] Cost stays within budget ($5/tick default)
