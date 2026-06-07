# Session Changelog — 2026-06-07

> Decoupling `life` from `fin_ops`, restoring root `__init__.py`, fixing imports,
> and validating the `life-ops/operational/` standalone project.

---

## Commit: `4dc18c1`

```
feat(life): decouple fin_ops, fix global imports, restore root __init__

- centrals/finance.py: removed entirely (fin_ops submodule deleted)
- centrals/__init__.py: cleaned up finance_central references
- cli/cli.py: removed finance Typer mount, fixed old-style imports
- cli/config.py: removed fin_ops from DEFAULT_SUBMODULES, finance_store field
- cli/test_runner.py, plugins/*.py: fixed life.config -> life.cli.config imports
- handlers/daily.py, weekly.py: removed --skip-finance, finance logic
- __init__.py: restored root package (was deleted in checkpoint)

Also fixed plugin loader to skip loader.py/protocol.py as plugins
(since plugins/ dir is in DEFAULT_PLUGIN_DIRS, causing relative
import errors on self-loading).
```

---

## Detailed Changes

### 1. Finance Central Removed (`centrals/finance.py`)

**Deleted:**
- `centrals/finance.py` — entire file (106 lines), 4 commands: `track`, `report`, `simulate`, `derivatives`
- All dispatched to `fin_ops.cli` submodule which no longer exists

**Files updated:**
- `centrals/__init__.py` — removed `from .finance import finance_central` and `__all__` entry
- `cli/cli.py` — removed `app.add_typer(finance_central, name="finance", ...)`
- `cli/config.py` — removed `"fin_ops": ROOT / "fin_ops"` from `DEFAULT_SUBMODULES`, removed `finance_store: Optional[Path]` from `LifeConfig`, removed YAML config deserialization for `finance_store`
- `handlers/daily.py` — removed `--skip-finance`, `--finance-period` flags and the finance report subprocess call
- `handlers/weekly.py` — removed `--skip-finance` flag and the finance report subprocess call

### 2. Root `__init__.py` Restored

- Created `life/__init__.py` defining `__version__ = "0.1.0"`
- This was deleted in the checkpoint commit (`f1a6395`) which moved `__init__.py` → `cli/__init__.py`
- Required for `python -m life.cli` to work

### 3. Import Style Unification

Fixed old-style imports (`life.config` → `life.cli.config`, `life.log` → `life.cli.log`, `life.test_runner` → `life.cli.test_runner`) across these canonical source files:

| File | Old Import | New Import |
|------|-----------|------------|
| `cli/cli.py` | `life.config`, `life.test_runner` | `life.cli.config`, `life.cli.test_runner` |
| `cli/test_runner.py` | `life.config`, `life.log` | `life.cli.config`, `life.cli.log` |
| `plugins/loader.py` | `life.config`, `life.log` | `life.cli.config`, `life.cli.log` |
| `plugins/builtin/health_check.py` | `life.config` | `life.cli.config` |
| `handlers/weekly.py` | `life.config`, `life.log` | `life.cli.config`, `life.cli.log` |

### 4. Plugin Loader Self-Loading Fix

`plugins/loader.py` was being loaded as a plugin because `plugins/` is in `DEFAULT_PLUGIN_DIRS` and `loader.py` doesn't start with `_`. This caused a relative import error (`from .protocol import PluginProtocol`) because the module was loaded via `importlib.spec_from_file_location`, not as part of the `life.plugins` package.

**Fix:** Added `_SKIP = {"loader.py", "protocol.py", "__init__.py"}` to `load_plugins()` so these internal files are skipped during plugin discovery.

### 5. `life-ops/operational/` Project Validation

Full quality sweep of the standalone PAV cybernetic engine (untracked, Poetry-based):

| Metric | Before | After |
|--------|--------|-------|
| Tests | 2518 ✅ pass | 2518 ✅ pass |
| Mypy | ~21 errors | **0 errors** |
| Ruff `T201` (prints) | 39 | **0** (→ `typer.echo()`) |
| Ruff `EM102/EM101` | ~48 | **0** (→ `%` formatting) |
| Ruff total | 309 | 261 (cosmetic only) |
| CLI | Untested | ✅ 7 commands working |

**Mypy fixes applied to:**
- `persistence/base.py` — `typing.List` to avoid name collision with `list()` method
- `entities/policy.py` — replaced `from datetime import date` with `import datetime as _dt` to avoid `PolicyDecision.date` field name conflict
- `core/break_calculator.py` — added `Period` type annotations, fixed `custom_overrides` type
- `core/routine_logger.py` — full type annotations for `Period`, `RoutineType` params across all functions and `RoutineLogger` methods
- `persistence/memory.py`, `sqlite.py` — removed unused `# type: ignore[return-value]` comments

---

## Files Touched

### Staged & Committed (10 files)
```
__init__.py                 |   3 ++   (new)
centrals/__init__.py        |   4 +-
centrals/finance.py         | 106 ---   (deleted)
cli/cli.py                  |  11 +--
cli/config.py               |   6 +-
cli/test_runner.py          |   4 +-
handlers/daily.py           |  27 +---
handlers/weekly.py          |  29 +---
plugins/loader.py           |   7 +-
plugins/builtin/health_check.py | 2 +-
```

### Uncommitted (from previous session / unrelated)
- `CLAUDE.md` — 281-line update (pre-existing dirty)
- `life-ops/SPEC.md` — spec updates (pre-existing dirty)
- `vibe-ops/architecture/*.md`, `vibe-ops/planning/`, `vibe-ops/specs/` — pre-existing dirty docs
- `vibe-ops/base/*.txt`, `vibe-ops/base/*.json` — deleted in checkpoint
- `life-ops/planner/2026-01-11-study-plan.md` — deleted in checkpoint
- Various untracked files (see `git status`)

---

## Architecture State After Session

```
life CLI (python -m life.cli)
├── task central        → Taskwarrior binary + scripts
├── knowledge central   → leitura, mindmaps, notes (submodules)
├── research central    → research (submodule)
├── daily handler       → task today (no finance)
├── weekly handler      → weekly review + metrics (no finance)
├── plugins             → health_check builtin
├── test runner         → pytest discovery across submodules

life-ops/
├── life-tatics         → Standalone time-tracking CLI (Poetry)
└── operational/        → Standalone PAV cybernetic engine (Poetry)
    ├── 2518 tests ✅
    ├── 0 mypy errors ✅
    ├── CLI: routine, block, journal, habit, metric, policy, report
    └── Covers: habits (H(t), Q_HE), routines, policy FSM, pomodoro,
                metrics, sleep, journal, persistence (InMemory + SQLite)

vibe-ops/               → Active R&D (Target-Sensor-Adjuster loop)
    ├── Cybernetic Daily Loop
    ├── Hybrid RAG Indexer
    ├── Policy Engine (PUSH/MAINTAIN/REDUCE/RECOVER)
    └── Rust TUI dashboard
```
