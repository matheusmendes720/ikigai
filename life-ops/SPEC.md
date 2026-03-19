# `life-tatics` SPEC

## Purpose

The **life-tatics** submodule provides standalone CLI tooling and domain logic for personal time management. It is designed to manage time allocation, track developer screen time, and orchestrate daily routines/rituals.

Crucially, **life-tatics** is completely decoupled from the overarching Algorithmic Life OS orchestrator (`life/`) and the core `taskwarrior` implementation. While it will eventually connect to the `tw-api` for deep integration regarding "work vs. resting" metrics, it serves as an independent, modular time-allocation engine.

## Agent Contract / AI Rules

- AI agents must treat this submodule as an isolated project when operating within its directory bounds. 
- Use strict formatting and adhere to the `.cursor/rules/submodule-life-tatics.mdc`.
- Outputs must be structured (preferably JSON, using `--json` flags) to maintain interoperability with other orchestration tools if they choose to consume life-tatics data.

## CLI Surface (Planned)

The main entry point is the Typer CLI `life-tatics`.

- `life-tatics block start [name]`: Start a time allocation block.
- `life-tatics block stop`: Stop the current time allocation block.
- `life-tatics screentime log`: Log development vs resting screen time.
- `life-tatics routine [morning|evening]`: Run routine checklists.

## Data Model

All data defaults to being stored locally or interfacing with standard JSON/SQLite formats to ensure portability.
