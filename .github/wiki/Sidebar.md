# Getting Started

## Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_HANDLE/life.git
cd life

# Install the active app (operational — PAV kernel)
cd life-ops/operational
uv sync

# Run the CLI
pav --help

# Run the TUI
pav home
```

## Quick Commands

```bash
# Daily flow
pav daily run

# Track a habit
pav habit log --name sleep --streak 5

# Run tests
uv run pytest

# Quality gates
uv run ruff check packages/core/src/
uv run mypy packages/core/src/
```

## Project Structure

```
life/                       ← root CLI hub
life-ops/operational/       ← ACTIVE: PAV productivity kernel
  packages/core/            pure arithmetic logic (no I/O, no LLM)
  apps/cli/                 Typer CLI (pav, pav-os)
  apps/tui/                 Textual TUI (7 screens)
  tests/                    2518 tests
vibe-ops/                   R&D: cybernetic engine
taskwarrior/               TW binary + scripts
```

## Architecture Overview

The system has three layers:

1. **Root CLI hub** (`life/`) — Typer app that orchestrates domain "centrals" (task, knowledge, research) as subprocesses
2. **PAV Kernel** (`life-ops/operational/`) — Standalone productivity engine with pure arithmetic algorithms (habit model, policy FSM, pomodoro SM)
3. **Cybernetic Engine** (`vibe-ops/`) — Target-Sensor-Adjuster loop over Obsidian ↔ SQLite ↔ Taskwarrior

See [ARCHITECTURE_INDEX.md](../ARCHITECTURE_INDEX.md) for the full map.
