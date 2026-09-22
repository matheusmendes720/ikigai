# M123 — Daily backtest cron

## Purpose
Runs the full backtest pipeline (`bash scripts/backtest/run_backtest.sh --skip-gen`)
once per day. The first run of the day is the "daily snapshot" used by the
weekly trend table (M118).

## Files
- `cron-backtest.sh` — bash driver (POSIX + Windows git-bash compatible)
- `setup-task-scheduler.ps1` — Windows Task Scheduler one-time setup
- `.life/logs/cron-backtest.log` — output log (auto-created on first run)

## Setup

### Windows (Task Scheduler)
```powershell
.\scripts\cron\setup-task-scheduler.ps1
```
Default: daily at 06:00 local time, 30-minute execution limit.

To unregister:
```powershell
.\scripts\cron\setup-task-scheduler.ps1 -Unregister
```

To change the time:
```powershell
.\scripts\cron\setup-task-scheduler.ps1 -Time "22:00"
```

### Linux / macOS (crontab)
```bash
# Edit crontab:
crontab -e
# Add this line (replace /path/to/repo):
0 6 * * * /path/to/repo/scripts/cron/cron-backtest.sh
```

### Manual run (any time)
```bash
bash scripts/cron/cron-backtest.sh
```

## Behavior

- **Idempotent** — running twice in one day is safe. `baseline_archive` is
  first-wins same-day (M118), so the second run no-ops on the archive.
- **Python detection** — prefers repo venv, falls back to PATH python.
- **Logs to file** — output goes to `.life/logs/cron-backtest.log`. Cron
  failures exit non-zero so the scheduler knows.
- **Skip-gen** — `--skip-gen` is passed because scenario generation is
  stable (only changes when M114 chain is updated).

## What this delivers

- Daily `reports/baselines/<YYYY-MM-DD>.json` snapshot
- Daily `reports/baselines/<YYYY-MM-DD>.llm.json` snapshot (M119)
- Updated `reports/backtest-trend.md` with new week's data
- Daily `reports/backtest-drift.md` (current vs previous baseline)
- Daily `reports/backtest-Q1.md` (latest run summary)

## Honest scope

- ⚠️ **No notification on failure** — user opted out of Telegram/Discord.
  Cron failures are visible in `.life/logs/cron-backtest.log` and via the
  exit code in Task Scheduler's history.
- ⚠️ **No cross-host sync** — each machine has its own baselines. CI would
  need a shared store (S3 / git-LFS).
- ⚠️ **First-wins same-day means** manual runs after a cron run still
  produce reports, but they don't get a second archive snapshot.
