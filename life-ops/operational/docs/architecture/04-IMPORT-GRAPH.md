# 04 — Import Graph

> Who imports whom across the `operational` package. The graph is
> the source of truth for layering, for circular-import risk, and
> for the forbidden-import rules.

This is the same picture as in [01-MVC-LAYERS.md §5](01-MVC-LAYERS.md#5-import-graph),
but with finer-grained node labels and explicit
**`[CIRCULAR-RISK]`** markers where the import graph has
known-acceptable cycles and **forbidden imports** that the layering
rules forbid.

---

## 1. Top-level module graph

```
                            ┌─────────────────────────────────────┐
                            │  operational.cli.app                │
                            │  (Typer root, controller            │
                            │   registrations, `home` command)    │
                            └─────────────────┬───────────────────┘
                                              │
            ┌─────────────────────────────────┼──────────────────────────────────┐
            │                                 │                                  │
            ▼                                 ▼                                  ▼
  ┌────────────────────┐         ┌──────────────────────────┐       ┌──────────────────────┐
  │ operational.cli.   │         │ operational.cli.home     │       │ operational.cli.     │
  │ commands.<X>_cmd   │         │ (interactive menu,       │       │ dataset_selector,    │
  │ (12 sub-typers)    │         │  in-process Typer calls) │       │ csv_loader, seed     │
  └─────────┬──────────┘         └──────────┬───────────────┘       └──────────┬───────────┘
            │                                │                                  │
            ├────────────────────────────────┴──────────────────────────────────┤
            │                                                                   │
            ▼                                                                   ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                                                                                    │
  │   operational.cli.state                  ◄───── auto-loads via ──────             │
  │   (14 _PersistentRepo instances,            operational.cli.csv_loader            │
  │    import of every wired entity)            operational.cli.dataset_selector      │
  │                                                                                    │
  └─────────────┬──────────────────────────────────────────────────────────────────────┘
                │
                │  bases on InMemoryRepository
                ▼
  ┌────────────────────────────────────┐
  │  operational.persistence.memory    │
  │  (InMemoryRepository)              │
  └────────────────┬───────────────────┘
                   │  subclasses
                   │  RepositoryBase
                   ▼
  ┌────────────────────────────────────┐
  │  operational.persistence.base      │
  │  (RepositoryBase[T_Entity] ABC)    │
  └────────────────┬───────────────────┘
                   │  fulfils
                   │  Protocol
                   ▼
  ┌────────────────────────────────────┐
  │  operational.types                 │
  │  (Repository, Clock, Logger        │
  │   Protocols; UEID alias)           │
  └────────────────────────────────────┘
                   ▲
                   │  imported by every layer that needs typing
                   │
  ┌────────────────┴──────────────────────────────────────────────────────────────┐
  │                                                                                  │
  │   operational.entities.*           operational.core.*          operational.ui.* │
  │   (14 Pydantic leaves)             (pure business logic)       (Rich factories)  │
  │                                                                                  │
  └──────────────────────────────────────────────────────────────────────────────────┘
                                              ▲
                                              │  imports
                                              │
                            ┌─────────────────┴────────────────────┐
                            │  Leaves (zero operational imports)   │
                            │  • operational.enums                  │
                            │  • operational.constants              │
                            │  • operational.types                  │
                            │  • operational.exceptions             │
                            └───────────────────────────────────────┘
```

---

## 2. Detailed controller sub-tree

The 12 sub-typer files in `cli/commands/` all have the same shape.
Expanding one (`report_cmd.py`) as a representative:

```
operational.cli.commands.report_cmd
├── operational.cli.console                        [via shim → operational.ui.console]
│       └── operational.ui                          (CONSOLE_WIDTH, console, is_captured, strip_ansi)
├── operational.cli.state
│       ├── operational.persistence.memory          (InMemoryRepository via _PersistentRepo)
│       ├── operational.persistence.base            (RepositoryBase)
│       ├── operational.persistence.exceptions      (in some flows)
│       ├── operational.entities.ajuste_fino        (AjusteFino)
│       ├── operational.entities.habit              (Habit)
│       ├── operational.entities.journal            (JournalEntry)
│       ├── operational.entities.metric             (SleepRecord)
│       ├── operational.entities.policy             (PolicyDecision, PolicySetpoints)
│       ├── operational.entities.pomodoro           (PomodoroRound)
│       ├── operational.entities.routine            (Routine, RoutineLog)
│       ├── operational.entities.time_block         (TimeBlock)
│       └── operational.entities.v3                (DayContext, DailyReflection,
│                                                   LunchRecord, TransicaoRegistrada)
├── operational.cli.formatters                     (format_as_json, format_as_table, format_as_markdown)
│       └── (json + Pydantic stdlib only)
├── operational.core.budget                        (classify_quadrant, productivity_pct)
│       ├── operational.core.exceptions
│       ├── operational.enums                      (TipoDia)
│       └── operational.constants
├── operational.core.services                      (DaySnapshot, get_day_snapshot, compute_day_quadrant)
│       ├── operational.cli.state                  [CIRCULAR-RISK — see §5]
│       │       └── ... (recursive into entities.*)
│       ├── operational.core.budget
│       ├── operational.core.exceptions
│       ├── operational.enums
│       └── operational.constants
├── operational.ui.daily_report                    (render_daily_report)
│       ├── operational.core.services              (DaySnapshot, compute_day_quadrant)
│       ├── operational.enums                      (TipoDia)
│       └── operational.ui.components
│               ├── operational.cli.console        (shim)
│               ├── operational.enums              (Period, TipoDia)
│               ├── operational.constants          (DEFAULT)
│               └── (rich.*, stdlib)
├── typer                                          (third-party)
└── rich.console / rich.table / rich.text           (third-party — only for local helpers like _kpi/_panel)
```

The other 11 subcommand files follow the same shape. The only
substantial variation is which repos and which `ui.*` factories they
import:

| Subcommand | Reads from `state` | UI factories | Core services used |
|---|---|---|---|
| `routine_cmd` | `routines` | `ui.components` (colors) | `meta.factories.make_routine` |
| `block_cmd` | `time_blocks` | `ui.components` | `meta.factories.make_time_block` |
| `journal_cmd` | `journals` | `ui.components` | `meta.factories.make_journal_entry` |
| `habit_cmd` | `habits` | `ui.components` | `meta.factories.make_habit` |
| `metric_cmd` | `sleep_records` | `ui.components` | `core.services.validate_pomodoro_count`, `core.sleep_calculator` |
| `policy_cmd` | `policy_decisions`, `policy_setpoints` | `ui.components` | `core.policy_engine` |
| `report_cmd` | (6 repos) | `ui.daily_report`, `ui.components` | `core.services.get_day_snapshot`, `core.budget.classify_quadrant` |
| `state_cmd` | (7 repos) | `ui.components` (kpi_card, metric_table) | `core.services.get_day_snapshot` |
| `reflect_cmd` | `daily_reflections` | `ui.components` | (no core) |
| `lunch_cmd` | `lunch_records` | `ui.components` | (no core) |
| `demo_cmd` | (all 14 repos) | `ui.components` | `cli.seed.build_seed_*` |
| `doctor_cmd` | (no repos) | `ui.components` | (env checks only) |

---

## 3. UI sub-tree

```
operational.ui
├── operational.cli.console                        [backward-compat shim]
│       └── operational.ui                         (console, CONSOLE_WIDTH)
├── operational.core.services                      (DaySnapshot, compute_day_quadrant)
│       ├── operational.cli.state                  [CIRCULAR-RISK]
│       └── ... (see controller sub-tree above)
├── operational.enums                              (Period, TipoDia, ...)
├── operational.constants                          (DEFAULT for severity thresholds)
└── rich                                          (Panel, Table, Text, Group, ...)
```

**`ui/` never imports from `cli/commands/`** — confirmed by the
absence of any such import in `ui/components.py`,
`ui/daily_report.py`, and `ui/__init__.py`.

---

## 4. Entities sub-tree

```
operational.entities.<X>    for X in {routine, time_block, journal, habit,
                                       metric, pomodoro, policy, ajuste_fino,
                                       consolidation, v3}
├── operational.enums                              (Period, RoutineType, ...)
├── operational.types                              (UEID)
├── operational.constants                          (DEFAULT.LAMBDA_LEARNING_DEFAULT, etc.)
└── pydantic                                       (BaseModel, ConfigDict, Field)

Exception — one cross-entity import:
operational.entities.journal
└── operational.entities.ajuste_fino               (inline embedded list field)
```

This is the **"leaves"** rule. **No entity imports another entity
except `JournalEntry → AjusteFino` for the inline list field.**

---

## 5. `[CIRCULAR-RISK]` markers

The package is **not** 100% acyclic, by deliberate design. There are
two known-acceptable cycles:

### 5.1 `core.services ↔ cli.state`  (intentional)

`core/services.py:27-39` imports from `cli/state.py`. `cli/state.py`
imports entity classes (transitively, via the `_PersistentRepo`
constructor calls at `cli/state.py:91-106`). The entities do not
import `core` or `cli.state`, so the cycle is broken at the leaves
and Python's import machinery resolves it fine.

```
core.services ──→ cli.state ──→ entities.* ──→ (no return path)
     ▲                                                │
     │                                                │
     └────────── (services are imported by ──────────┘
                  ui/, controllers, but those don't
                  import core.services back into
                  the chain that created cli.state)
```

**Mitigation:** the cycle is broken at import time because Python
imports `cli/state.py` **first** (it has no dependencies on `core`),
and `core/services.py` is only imported **later** (by controllers
and `ui/`) — by which time `cli.state` is fully initialised. The
`_PersistentRepo` instances in `cli/state.py` are bound to entity
classes by the time `core/services.py` runs.

### 5.2 `cli.app ↔ cli.home`  (intentional)

`cli/app.py:55` does a deferred import:
```python
@app.command()
def home() -> None:
    from operational.cli.home import run as run_home
    run_home()
```

The deferred import (inside the function body) prevents the cycle
that would arise from `cli/home.py:24` (`from operational.cli.app
import app as typer_app`). The function body runs only when the user
invokes `operational home`, by which time `cli/app.py` is fully
loaded.

---

## 6. Forbidden imports

These imports would break the layering. The current codebase is
clean of all of them.

| Forbidden | Why | Enforced by |
|---|---|---|
| `operational.core.*` → `rich.*` | Core must be I/O-free and free of presentation concerns. Core is the only layer that can be unit-tested without spinning up a TTY. | Grep test in CI / pre-commit |
| `operational.core.*` → `typer.*` | Same as above. | Grep test |
| `operational.core.*` → `operational.cli.*` (except `cli.state`) | Same as above. The single exception is `core.services` (documented at [01-MVC-LAYERS.md §2.2](01-MVC-LAYERS.md#22-the-single-hard-compromise)). | Grep test (the exception is whitelisted) |
| `operational.ui.*` → `typer.*` | UI is a set of factory functions. They must work outside a Typer context (e.g. from a Jupyter notebook, a unit test, or a future TUI). | Code review |
| `operational.ui.*` → `operational.persistence.*` | UI consumes frozen dataclasses from `core.services`. It must not know there is a repo underneath — that knowledge belongs in `core.services.get_day_snapshot(d)`. | Grep test |
| `operational.entities.*` → `operational.entities.<other>` | Entities are leaves. The one allowed exception is `entities.journal` → `entities.ajuste_fino` (inline embedded list field, not a back-reference). | Grep test (with the inline-embedding exception whitelisted) |
| `operational.entities.*` → `operational.core.*` | Entities are pure data containers. No business logic, no calculations. | Grep test |
| `operational.enums` → anything from `operational.*` | Enums are leaves — they should never need to know about Pydantic, entities, or anything else. | Self-evident from the size of `enums.py` (915 lines) |
| `operational.constants` → anything from `operational.*` | `constants.py` is 329 lines of frozen dataclass. The single import is `from dataclasses import dataclass`. | Self-evident |
| `operational.types` → anything from `operational.*` | Same as above. `types.py` imports only from `pydantic` and stdlib. | Self-evident |
| `operational.exceptions` → anything from `operational.*` (other than the leaf modules) | Same as above. The package's top-level `__init__.py` re-exports the public surface, so the chain `operational.exceptions → operational.entities` would be a layering bug. | Code review |

---

## 7. Sanity grep commands

Run these from the project root to verify the layering rules. They
should return **zero matches** (with the documented exceptions).

```bash
# 1. Core must not import Rich or Typer
grep -rn "from rich"        src/operational/core/   # → 0
grep -rn "import typer"     src/operational/core/   # → 0

# 2. UI must not import Typer or persistence
grep -rn "import typer"                src/operational/ui/   # → 0
grep -rn "from operational.persistence" src/operational/ui/   # → 0

# 3. Entities must not import core (one documented exception for journal→ajuste_fino)
grep -rn "from operational.core" src/operational/entities/   # → 0
grep -rn "from operational.entities" src/operational/entities/   # → 1 (journal → ajuste_fino)
```

The third command has exactly one match: `entities/journal.py:44`
(`from operational.entities.ajuste_fino import AjusteFino`). That
match is the **inline-embedding exception** and is correct.

---

## 8. Where to read next

- [01-MVC-LAYERS.md](01-MVC-LAYERS.md) — the layering rules this graph enforces
- [02-PERSISTENCE-LAYER.md §5.2](02-PERSISTENCE-LAYER.md#52-the-14-instances) — the 14 `_PersistentRepo` instances
- [05-DATA-FLOW.md](05-DATA-FLOW.md) — the call chain across these layers for one command
