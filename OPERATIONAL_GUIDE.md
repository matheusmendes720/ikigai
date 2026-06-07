# Operational Guide — Algorithmic Life OS

> Complete command reference and walkthrough for both the root `life` CLI
> and the standalone `operational` cybernetic engine.

---

## Table of Contents

1. [Prerequisites & Setup](#1-prerequisites--setup)
2. [Root `life` CLI](#2-root-life-cli)
   - [Config & Info](#21-config--info)
   - [Task Central](#22-task-central)
   - [Knowledge Central](#23-knowledge-central)
   - [Research Central](#24-research-central)
   - [Daily Handler](#25-daily-handler)
   - [Weekly Handler](#26-weekly-handler)
   - [Plugins & Tests](#27-plugins--tests)
3. [Operational Cybernetic CLI](#3-operational-cybernetic-cli)
   - [Routines](#31-routines)
   - [Time Blocks](#32-time-blocks)
   - [Journal](#33-journal)
   - [Habits](#34-habits)
   - [Metrics](#35-metrics)
   - [Policy](#36-policy)
   - [Reports](#37-reports)
4. [End-to-End Walkthrough](#4-end-to-end-walkthrough)
5. [Testing & Verification](#5-testing--verification)

---

## 1. Prerequisites & Setup

### Root `life` CLI

```bash
# From repo root — requires parent dir on PYTHONPATH
cd C:\Users\mathe\code_space\life-oss\life
set PYTHONPATH=C:\Users\mathe\code_space\life-oss
python -m life.cli.cli --help
```

> **Note:** If `python -m life.cli` fails, use `python -m life.cli.cli` instead
> (the `cli/` directory is a package without `__main__.py`).

### `operational` CLI (standalone)

```bash
cd C:\Users\mathe\code_space\life-oss\life\life-ops\operational
set PYTHONPATH=src
python -c "from operational.cli.app import app; app()" --help
```

> **Tip:** Create aliases for convenience:
> ```batch
> doskey life=set PYTHONPATH=C:\Users\mathe\code_space\life-oss ^& python -m life.cli.cli $*
> doskey ops=set PYTHONPATH=src ^& python -c "from operational.cli.app import app; app()" $*
> ```

---

## 2. Root `life` CLI

### 2.1 Config & Info

```bash
# Show current configuration
python -m life.cli.cli config-show
python -m life.cli.cli config-show --json
python -m life.cli.cli config-show --path       # show config file path

# Show version
python -m life.cli.cli version                   # → 0.1.0

# List submodules with paths and git refs
python -m life.cli.cli submodules
python -m life.cli.cli submodules --json

# Show features from a submodule's SPEC.md
python -m life.cli.cli features leitura
python -m life.cli.cli features research --json

# Configure logging
python -m life.cli.cli log                        # show current log config
python -m life.cli.cli log --level DEBUG
python -m life.cli.cli log --path                 # show log file location
```

### 2.2 Task Central

Requires [Taskwarrior](https://taskwarrior.org) binary installed.

```bash
# Show today's tasks
python -m life.cli.cli task today
python -m life.cli.cli task today --json          # JSON export

# Daily review (runs taskwarrior/scripts/daily_review.sh)
python -m life.cli.cli task daily-review
python -m life.cli.cli task daily-review --json

# Weekly review
python -m life.cli.cli task weekly-review
python -m life.cli.cli task weekly-review --json

# Task metrics
python -m life.cli.cli task metrics
python -m life.cli.cli task metrics --json
```

### 2.3 Knowledge Central

Requires submodule directories (`leitura`, `notes`, `mindmaps`) to exist:

```bash
# Read a file (delegates to leitura)
python -m life.cli.cli knowledge read path/to/file
python -m life.cli.cli knowledge read path/to/file --format markdown

# List sections of a document
python -m life.cli.cli knowledge list-sections path/to/file

# Notes
python -m life.cli.cli knowledge note-add "My note content" --title "Note Title"
python -m life.cli.cli knowledge note-add "Content" --tags "important,quick"
python -m life.cli.cli knowledge note-list
python -m life.cli.cli knowledge note-list --tags "important"

# Mindmaps
python -m life.cli.cli knowledge mindmap-phase0 path/to/source --output mindmap.json
python -m life.cli.cli knowledge mindmap-phase1 path/to/index --output mindmap.json
```

### 2.4 Research Central

Requires the `research` submodule to exist:

```bash
# Map URLs for crawling
python -m life.cli.cli research map https://example.com
python -m life.cli.cli research map https://example.com --depth 3

# Crawl from sitemap or URL
python -m life.cli.cli research crawl https://example.com/sitemap.xml

# Search research backend
python -m life.cli.cli research search "query text"
python -m life.cli.cli research search "query" --backend vector
```

### 2.5 Daily Handler

```bash
# Full daily flow: task today
python -m life.cli.cli daily run
python -m life.cli.cli daily run --json

# Skip task
python -m life.cli.cli daily run --skip-task
```

> **Note:** The `--skip-finance` and `--finance-period` flags were removed
> in commit `4dc18c1` with the finance central decoupling.

### 2.6 Weekly Handler

```bash
# Full weekly flow: weekly review + metrics
python -m life.cli.cli weekly run
python -m life.cli.cli weekly run --json

# Skip components
python -m life.cli.cli weekly run --skip-review
python -m life.cli.cli weekly run --skip-metrics
```

> **Note:** The `--skip-finance` flag was removed in commit `4dc18c1`.

### 2.7 Plugins & Tests

```bash
# List loaded plugins
python -m life.cli.cli plugins
python -m life.cli.cli plugins --json

# Health check (from builtin plugin)
python -m life.cli.cli health

# Run tests across all submodules with tests/
python -m life.cli.cli test
python -m life.cli.cli test --list              # list test directories
python -m life.cli.cli test -s research         # run only research tests
python -m life.cli.cli test --verbose --json
```

---

## 3. Operational Cybernetic CLI

The standalone operational CLI (`life-ops/operational/`) manages the
cybernetic loop: routines → time blocks → habits → metrics → policy.

Run it:

```bash
cd C:\Users\mathe\code_space\life-oss\life\life-ops\operational
set PYTHONPATH=src
python -c "from operational.cli.app import app; app()" --help
```

All commands support `--json` for machine-readable output.

### 3.1 Routines

Routines are structured periods (morning/afternoon/evening) with start/end times.

```bash
# Create a morning routine
python -c "from operational.cli.app import app; app()" routine create "Wake up" MANHA CORE
python -c "from operational.cli.app import app; app()" routine create "Wake up" MANHA CORE --json

# Create with custom times
python -c "from operational.cli.app import app; app()" routine create "Deep Work" TARDE CORE -sh 8 -sm 0 -eh 12 -em 0

# List routines
python -c "from operational.cli.app import app; app()" routine list
python -c "from operational.cli.app import app; app()" routine list --period MANHA
```

**Parameters:**
| Argument | Values | Description |
|----------|--------|-------------|
| `name` | string | Routine name (required) |
| `period` | `MANHA`, `TARDE`, `NOITE` | Time period |
| `routine_type` | `ENTRY`, `CORE`, `TRANSITION`, `EXIT` | Type |
| `--start-hour` | 0-23 | Default: 6 |
| `--start-minute` | 0-59 | Default: 0 |
| `--end-hour` | 0-23 | Default: 6 |
| `--end-minute` | 0-59 | Default: 50 |

### 3.2 Time Blocks

Time blocks are work/pomodoro sessions within periods.

```bash
# Create a time block
python -c "from operational.cli.app import app; app()" block create MANHA
python -c "from operational.cli.app import app; app()" block create TARDE --label "Deep work" --json

# With routine reference
python -c "from operational.cli.app import app; app()" block create MANHA --routine "rt_xxxx"

# List time blocks
python -c "from operational.cli.app import app; app()" block list
python -c "from operational.cli.app import app; app()" block list --period TARDE --json
```

**Parameters:**
| Argument | Values | Description |
|----------|--------|-------------|
| `period` | `MANHA`, `TARDE`, `NOITE` | Time period (required) |
| `--label` | string | Block label |
| `--routine` | UEID | Reference to a routine |

### 3.3 Journal

Journal entries with date and free-text content.

```bash
# Create a journal entry
python -c "from operational.cli.app import app; app()" journal create --text "Great day, finished project X"
python -c "from operational.cli.app import app; app()" journal create --date 2026-06-07 --text "Day review" --json

# List entries
python -c "from operational.cli.app import app; app()" journal list
python -c "from operational.cli.app import app; app()" journal list --json
```

**Parameters:**
| Option | Format | Description |
|--------|--------|-------------|
| `--date`, `-d` | YYYY-MM-DD | Date (default: today) |
| `--text`, `-t` | string | Entry text |

### 3.4 Habits

Habits with Q_HE (Quality Habit Effectiveness) parameters.

```bash
# Create a habit
python -c "from operational.cli.app import app; app()" habit create "Drink water" physiological
python -c "from operational.cli.app import app; app()" habit create "Read 30min" cognitive --resistance 3 --weight 0.5 --json

# List habits
python -c "from operational.cli.app import app; app()" habit list
python -c "from operational.cli.app import app; app()" habit list --category physiological
```

**Parameters:**
| Parameter | Values | Description |
|-----------|--------|-------------|
| `name` | string | Habit name (required) |
| `category` | `physiological`, `cognitive`, `social`, `creative`, `ritual` | Category |
| `--resistance`, `-r` | 0.0–10.0 | Resistance level (default: 5.0) |
| `--weight`, `-w` | 0.0–1.0 | Q_HE weight (default: 0.25) |

### 3.5 Metrics

Track sleep and other quantitative metrics.

```bash
# Record a sleep entry
python -c "from operational.cli.app import app; app()" metric sleep --quality 8
python -c "from operational.cli.app import app; app()" metric sleep --date 2026-06-07 --quality 9 --bed-hour 22 --wake-hour 6 -json

# Change quality
python -c "from operational.cli.app import app; app()" metric sleep --quality 10 --bed-hour 21 --wake-hour 5
```

**Parameters:**
| Option | Range | Description |
|--------|-------|-------------|
| `--date`, `-d` | YYYY-MM-DD | Date (default: today) |
| `--quality`, `-q` | 1–10 | Sleep quality (default: 8) |
| `--bed-hour`, `-bh` | 0–23 | Bedtime hour (default: 23) |
| `--bed-minute`, `-bm` | 0–59 | Bedtime minute (default: 0) |
| `--wake-hour`, `-wh` | 0–23 | Wake hour (default: 7) |
| `--wake-minute`, `-wm` | 0–59 | Wake minute (default: 0) |

### 3.6 Policy

View the cybernetic policy setpoints and decisions (currently placeholder).

```bash
# View policy setpoints (PUSH / MAINTAIN / REDUCE / RECOVER)
python -c "from operational.cli.app import app; app()" policy setpoints
python -c "from operational.cli.app import app; app()" policy setpoints --json

# View decisions
python -c "from operational.cli.app import app; app()" policy decisions
python -c "from operational.cli.app import app; app()" policy decisions --json
```

### 3.7 Reports

Generate daily and weekly narrative reports.

```bash
# Daily summary
python -c "from operational.cli.app import app; app()" report daily
python -c "from operational.cli.app import app; app()" report daily --date 2026-06-07
python -c "from operational.cli.app import app; app()" report daily --date 2026-06-07 --json

# Weekly report
python -c "from operational.cli.app import app; app()" report weekly
python -c "from operational.cli.app import app; app()" report weekly --start 2026-06-01 --end 2026-06-07 --json
```

---

## 4. End-to-End Walkthrough

### Full Daily Loop

```bash
:: -- Root CLI --
cd C:\Users\mathe\code_space\life-oss\life
set PYTHONPATH=C:\Users\mathe\code_space\life-oss

:: 1. Check version and config
python -m life.cli.cli version
python -m life.cli.cli config-show

:: 2. Run daily flow
python -m life.cli.cli daily run

:: 3. Check health
python -m life.cli.cli health

:: 4. List plugins
python -m life.cli.cli plugins

:: -- Operational CLI --
cd life-ops\operational
set PYTHONPATH=src

:: 5. Log sleep
python -c "from operational.cli.app import app; app()" metric sleep -q 8 -bh 22 -wh 6

:: 6. Create a morning routine
python -c "from operational.cli.app import app; app()" routine create "Wake&Shine" MANHA CORE -sh 5 -eh 6

:: 7. Create a time block
python -c "from operational.cli.app import app; app()" block create MANHA -l "Morning deep work"

:: 8. Create a habit
python -c "from operational.cli.app import app; app()" habit create "Meditate" ritual -r 3 -w 0.4

:: 9. Journal
python -c "from operational.cli.app import app; app()" journal create -t "Started using Life OS. Routines are helping."

:: 10. Generate daily report
python -c "from operational.cli.app import app; app()" report daily --json
```

### Cybernetic Loop (Conceptual)

```
                    ┌─────────────┐
                    │   TARGET    │  ← IkigaiScorer (qhe_target, c_comp_target)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   SENSOR    │  ← Study hours, habit consistency, infractions
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  ADJUSTER   │  ← PolicyEngine (PUSH/MAINTAIN/REDUCE/RECOVER)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼────┐ ┌─────▼────┐
        │ PERSIST  │ │  SYNC   │ │  INDEX   │
        │ SQLite   │ │ Obsidian │ │ Vector   │
        │          │ │  ↔  TW  │ │ Store    │
        └──────────┘ └─────────┘ └──────────┘
```

---

## 5. Testing & Verification

### Run Operational Tests (2518 total)

```bash
cd C:\Users\mathe\code_space\life-oss\life\life-ops\operational
set PYTHONPATH=src

:: All tests
python -m pytest -q

:: By category
python -m pytest tests/unit -q                    # unit tests only
python -m pytest tests/integration -q             # integration tests
python -m pytest tests/e2e -q                     # end-to-end tests

:: By marker
python -m pytest -m unit -q
python -m pytest -m integration -q
python -m pytest -m e2e -q

:: With coverage
python -m pytest --cov=src/operational --cov-report=term-missing

:: Fast (no cov, no slow markers)
python -m pytest -x --tb=short -q --no-cov -m "not slow"
```

### Run Life CLI Tests

```bash
cd C:\Users\mathe\code_space\life-oss\life
set PYTHONPATH=C:\Users\mathe\code_space\life-oss

:: Discover and run all submodule tests
python -m life.cli.cli test

:: List test directories
python -m life.cli.cli test --list

:: Run specific submodule
python -m life.cli.cli test -s research
```

---

## Quick Command Cheat Sheet

| Goal | Command |
|------|---------|
| Life CLI help | `python -m life.cli.cli --help` |
| Operational CLI help | `python -c "from operational.cli.app import app; app()" --help` |
| Check config | `python -m life.cli.cli config-show --json` |
| Daily flow | `python -m life.cli.cli daily run` |
| Weekly flow | `python -m life.cli.cli weekly run` |
| Health check | `python -m life.cli.cli health` |
| Log sleep | `ops metric sleep -q 8 -bh 22 -wh 6` |
| Create routine | `ops routine create "Name" MANHA CORE` |
| Create block | `ops block create MANHA -l "Deep work"` |
| Create habit | `ops habit create "Name" PHYSIOLOGICAL -r 3` |
| Journal entry | `ops journal create -t "Entry text"` |
| Daily report | `ops report daily` |
| Run tests | `python -m pytest -q` |
| JSON output | Any command + `--json` |

> **Legend:** `ops` = `set PYTHONPATH=src && python -c "from operational.cli.app import app; app()"`
