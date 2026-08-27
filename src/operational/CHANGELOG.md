# Changelog

All notable changes to `operational` (PAV Productivity Kernel) are documented here.

## [Unreleased]

## [0.1.0] — 2026-06-20

### Added

- **uv workspace** — project restructured into a 3-package uv workspace:
  - `packages/core/` — `operational-core`: pure domain logic, entities, persistence, parsers, reports, meta
  - `apps/cli/` — `operational-cli`: Typer/Rich CLI, state management, UI components
  - `apps/tui/` — `operational-tui`: Textual TUI with 7 screens (Dashboard, Daily Flow, Habits, Journal, Metrics, Pomodoro Timer, Policy)
- `uv.toml` — uv workspace configuration with `packages/*` and `apps/*` members
- `pyproject.toml` — workspace root with `[tool.uv.workspace]`, shared `[tool.coverage]`
- `packages/core/pyproject.toml` — `operational-core` package with pydantic, python-frontmatter, pyyaml
- `apps/cli/pyproject.toml` — `operational-cli` package with entry points `pav`, `pav-os`, `operational`
- `apps/tui/pyproject.toml` — `operational-tui` package with textual, plotext
- `.env.example` — environment variable documentation (TIME_TASKER_STATE_DIR, TIME_TASKER_DATASET, PAV_THEME, etc.)
- `CLAUDE.md` updated with workspace-run commands (`uv run pav`, `uv run pytest`, etc.)

### Changed

- **File move** — all source moved from flat `src/operational/` to workspace packages:
  - `src/operational/core/` → `packages/core/src/operational/core/`
  - `src/operational/entities/` → `packages/core/src/operational/entities/`
  - `src/operational/persistence/` → `packages/core/src/operational/persistence/`
  - `src/operational/parsers/` → `packages/core/src/operational/parsers/`
  - `src/operational/reports/` → `packages/core/src/operational/reports/`
  - `src/operational/meta/` → `packages/core/src/operational/meta/`
  - `src/operational/cli/` → `apps/cli/src/operational/cli/`
  - `src/operational/ui/` → `apps/cli/src/operational/ui/`
  - `src/operational/tui/` → `apps/tui/src/operational/tui/`
- `services.py` moved from `core/` to `cli/` (breaks circular dependency)
- `apps/cli/src/operational/__init__.py` uses `pkgutil.extend_path` to bridge namespace across packages

### Fixed

- `test_state_show_json_with_mocked_sleep` — use `date.today()` instead of hardcoded date so the mocked sleep record is found at runtime

### Documentation

- `docs/ROADMAP.md` — Module Map updated to reflect uv workspace structure (`packages/core/`, `apps/cli/`, `apps/tui/`)

### Technology

- **Build**: hatchling (via `[build-system] requires = ["hatchling"]`)
- **Workspace**: uv with `[tool.uv.workspace] members = ["packages/core", "apps/cli", "apps/tui"]`
- **Python**: 3.11+
- **CLI**: Typer 0.12+ / Rich 13.7+
- **TUI**: Textual 0.8+ / plotext 4.2+
- **Domain**: Pydantic 2.10+, python-frontmatter, PyYAML
