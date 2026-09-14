# Example: M1 — Wire loop-tick.sh to claude-flow daemon

Demonstrates how to register the loop tick as a scheduled job in the claude-flow daemon. Manual ticks work, but cron-driven ticks require daemon registration.

## What this example covers

After M0 Bootstrap is complete, register `loop-tick.sh` as a scheduled job:

```bash
bash .claude/helpers/daemon-manager.sh add \
  --name "loop-tick" \
  --interval "60m" \
  --command "bash .claude/loop/loop-tick.sh" \
  --cost-cap-usd "5"
```

Verify:

```bash
bash .claude/helpers/daemon-manager.sh list
# Expect: shows current schedules (audit, optimize, loop-tick, hill-climb)
```

## The cost cap pattern

The `--cost-cap-usd "5"` argument is CRITICAL — it prevents runaway spend if the orchestrator or worker agent gets stuck in a loop.

The pattern: `--cost-cap-usd X` where X = the budget per tick.

## How to run this example

```bash
cd examples/m1-cron-tick

# See the daemon-manager.sh script structure
ls .claude/helpers/
cat .claude/helpers/daemon-manager.sh | head -30
```

## Key takeaway

The cost cap is the only safety mechanism for autonomous loops. Without it, an infinite tick loop could rack up unbounded spend.
