# M8 — Notification Channel

> **Created:** 2026-09-07
> **Owner:** loop-orchestrator
> **Status:** IN-PROGRESS

## Goal

Wire a single HTTP-webhook notification channel that fires when the loop needs
human intervention: `FAIL` / `NEEDS_FIX` / `BLOCKED` tick verdicts OR M7's
spike alarm (cost > $10/day, exit 2). Only alerts when intervention is needed —
HITL fatigue mitigation (the user's stated constraint for M8).

## Why

- M7 ships `cost-dashboard.sh` which exits 2 on a spike. That signal exists
  but nothing listens to it. M8 closes the loop: spike → notify.
- Loop runs 24/7 unattended (M9 target). Without notifications, the operator
  only finds out something broke when they manually check progress.md.
- One channel is enough for v1. Adding Telegram/Feishu/email is a future
  scope expansion gated on user demand.

## Channel Choice — Why ntfy (HTTP webhook)

Three options considered:

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **ntfy.sh** (HTTP POST webhook) | Zero auth (topic = URL secret), curl-only, no SDK, idempotent retry safe | Needs internet, public topic unless self-hosted | **CHOSEN** |
| Telegram Bot API | Native mobile push, rich formatting | Bot token + chat_id config, requires `jq`/curl with custom JSON, more moving parts | Deferred |
| Email (SMTP) | Universal, no app install | SMTP creds, async delivery, hard to test in sandbox | Deferred |

ntfy.sh wins on simplicity: a single curl POST to `https://ntfy.sh/<topic>`
publishes a message to anyone subscribed to that topic URL. The topic name IS
the secret. Pure bash + curl — matches M7 cost-dashboard.sh architecture note
("Pure bash + awk; no Python"). The notification channel is therefore a
~60-line bash script.

If the user prefers Telegram/Feishu later, the script's `send()` function is
the single integration point to swap.

## Acceptance Criteria

### 1. Channel configuration

- [ ] Reads `LOOP_NOTIFY_TOPIC` env var (default: empty → notify is disabled,
      exit 0 silently)
- [ ] Reads `LOOP_NOTIFY_SERVER` env var (default: `https://ntfy.sh`) — lets
      users self-host
- [ ] Reads `LOOP_NOTIFY_PRIORITY` env var (default: `default`; one of `min`,
      `low`, `default`, `high`, `urgent` per ntfy spec)
- [ ] No secrets committed to repo. Topic name lives in `.env.local` (gitignored)
      or shell rc.

### 2. Trigger interface

```bash
bash scripts/notify.sh \
    --reason "spike_alarm" \
    --message "M7 cost-dashboard: ticks_day=15 usd_total=$12.40 spike_alarm=SPIKE" \
    [--priority high] [--dry-run]
```

- `--reason` is a short machine-readable tag (`spike_alarm` | `tick_fail` |
  `needs_fix` | `blocked` | `test`) — included in message title for filtering
- `--message` is the human-readable body (multi-line allowed; passed through
  unchanged)
- `--priority` overrides `LOOP_NOTIFY_PRIORITY`
- `--dry-run` prints the curl command that WOULD run, does not POST

Exit codes:
- 0: notification sent (or skipped because disabled / dry-run)
- 1: fatal (missing dependency `curl`, network unreachable, malformed args)
- 2: ntfy returned HTTP 4xx/5xx (message NOT delivered — caller should retry)

### 3. Idempotency / deduplication

- Reads `.claude/loop/logs/notify-state.json` (gitignored, auto-created)
- Stores `{reason, message_sha256, last_sent_at}` keyed by `<reason>:<sha256>`
- If the same `<reason>+<message>` was sent within `LOOP_NOTIFY_COOLDOWN_SEC`
  (default 600s = 10min), suppress the duplicate (exit 0, log to stderr)
- This prevents storm conditions: a spike that lasts 1 hour does NOT fire 6
  identical notifications (one per cost-dashboard run)

### 4. Script interface (wire-in points)

The notify channel plugs into existing scripts at three exit paths:

```bash
# Wire #1 — M7 spike alarm (cost-dashboard.sh exit 2)
bash scripts/cost-dashboard.sh
if [ $? -eq 2 ]; then
    bash scripts/notify.sh --reason spike_alarm \
        --message "$(grep -E '^- \*\*' .claude/loop/logs/cost-report.md | head -10)"
fi

# Wire #2 — loop-tick.sh FAIL/NEEDS_FIX/BLOCKED (added in T-8.3)
# See scripts/loop-tick.sh EXIT trap additions

# Wire #3 — manual: `bash scripts/notify.sh --reason test --message "ping"`
```

### 5. Tests

`tests/test_notify.sh` covers (mirroring M7's 3-group layout):

1. **Disabled mode**: unset `LOOP_NOTIFY_TOPIC`, run, assert exit 0, no HTTP
   call made (assert by stubbing `curl` with a counter script)
2. **Idempotent duplicate suppression**: send same reason+message twice within
   cooldown, assert only ONE HTTP POST attempted (counter increments by 1)
3. **Dry-run mode**: `--dry-run`, assert prints curl command to stdout, does
   NOT POST (counter stays at 0)
4. **Spike alarm wire**: run cost-dashboard with seeded >$10 progress, assert
   notify fires with `reason=spike_alarm`

All tests use a stub `curl` (PATH override) that counts invocations and
returns configurable HTTP codes — no real network calls during tests.

### 6. Dependencies

- M7 (cost dashboard, exit code 2 spike signal) — DONE
- `curl` available in PATH (always true in Git Bash + Linux; macOS ships with
  it too; Windows cmd needs manual install — out of scope)

## Files Created

| Path | Purpose | Approx lines |
|------|---------|--------------|
| `scripts/notify.sh` | HTTP webhook sender + idempotency | ~80 |
| `tests/test_notify.sh` | 4 test groups + curl stub | ~100 |
| `scripts/loop-tick.sh` (EDIT) | Add notify wire to EXIT trap (Wire #2) | +15 |
| `.gitignore` (EDIT) | Add `.claude/loop/logs/notify-state.json` | +1 |

## Out of Scope (Future)

- Telegram / Feishu / email channels (v1.1, gated on user demand)
- Per-reason priority overrides (currently single `LOOP_NOTIFY_PRIORITY`)
- Web UI to view notification history (the notify-state.json file IS the
  history; v1 readers can `cat` it)
- Self-hosted ntfy server bootstrap (user installs; we just respect
  `LOOP_NOTIFY_SERVER` env var)
- HMAC signing of payloads (ntfy doesn't require it; topic IS the auth)

## Architecture Notes

- Pure bash + curl (no Python — matches M6/M7 architecture)
- Idempotency via SHA-256 of message body, persisted in JSON state file
- Cooldown window is configurable but defaults to 10min — long enough that
  the loop won't spam during a sustained anomaly, short enough that the
  operator is alerted within a reasonable window if the anomaly persists
- ntfy.sh is a public service but the topic name acts as a shared secret —
  operators subscribe to `https://ntfy.sh/<topic>` to receive alerts. The
  topic must be unguessable (default user picks their own 16+ char random
  string; documented in the SPEC's "Quickstart" subsection)

## Quickstart (operator)

```bash
# 1. Pick a topic name (16+ random chars). Treat it like a password.
export LOOP_NOTIFY_TOPIC="life-loop-$(openssl rand -hex 12)"

# 2. Subscribe on phone: open https://ntfy.sh/$LOOP_NOTIFY_TOPIC in ntfy
#    Android/iOS app, or `curl` to test

# 3. Test:
bash scripts/notify.sh --reason test --message "loop online"

# 4. Wire into loop-tick.sh (T-8.3 ships the wiring; once T-8.3 lands, the
#    loop will alert automatically on FAIL/NEEDS_FIX/spike)
```
