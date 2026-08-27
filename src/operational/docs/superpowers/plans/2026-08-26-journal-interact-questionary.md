# Journal Interact — Systematic Time Input via `questionary`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `pav journal interact` command (L2 — interactive `questionary` session) that systematically collects sleep times, time-block start/end pairs, pomodoro rounds, energy/focus/mood ratings, and free-form notes, then upserts the corresponding PAV entities (`SleepRecord`, `TimeBlock`, `PomodoroRound`, `JournalEntry`, `RoutineLog`) in one session.

**Architecture:** Thin Typer command in `cli/commands/journal_interact_cmd.py` using `questionary` for all prompts. All time validators are extracted to `operational/input_validation.py` (shared between CLI and TUI). Existing L1 `journal create` remains unchanged.

**Tech Stack:** `questionary>=2.0`, Python 3.11+, Pydantic v2, Typer, existing PAV entity factories.

---

## Global Constraints

- **Python floor:** `>=3.11`
- **Pydantic v2:** `frozen=True` / `extra="forbid"` on all immutable entities; `validate_assignment=True` on mutable ones
- **No business logic in controllers:** all logic in `core/` or `input_validation.py`
- **Zero LLM/NLP:** pure arithmetic only
- **Repository layout:** `life-ops/operational/` is the project root; `packages/core/src/operational/` is the core layer; `apps/cli/src/operational/cli/` is the controller layer
- **State:** 15 `_PersistentRepo` singletons in `cli/state.py`; repos: `journals`, `time_blocks`, `pomodoros`, `routine_logs`, `sleep_records`
- **Factories:** `meta/factories.py` — `make_journal_entry`, `make_time_block`, `make_sleep_record`, `make_routine`; new: `make_routine_log`
- **Period enum:** `Period.MANHA` / `Period.TARDE` / `Period.NOITE` with `.default_start_hour` / `.default_end_hour`
- **Existing entities exact signatures:**
  - `JournalEntry(entry_date: date, entry_text: str, energia_nivel: int|None, foco_nivel: int|None, humor_morning: int|None, humor_evening: int|None, pomodoros_completos: int)` — mutable, `validate_assignment=True`
  - `TimeBlock(label, start: datetime, end: datetime, period: Period, routine_id: UEID|None, energia_nivel|None, foco_nivel|None, notes)` — frozen
  - `SleepRecord(id, date, bedtime: time, wake_time: time, quality_score: int[1-10])` — frozen
  - `PomodoroRound(round_number, state: PomodoroState, started_at|None, completed_at|None)` — frozen
  - `RoutineLog(id, routine_id, date, period: Period, routine_type: RoutineType, text, energia_nivel|None, foco_nivel|None, humor|None)` — frozen

---

### Task 1: Extract time validators to `operational/input_validation.py`

**Files:**
- Create: `packages/core/src/operational/input_validation.py`
- Modify: `packages/core/src/operational/__init__.py` (add `from operational.input_validation import ...`)
- Test: `packages/core/tests/unit/test_input_validation.py`

**Interfaces:**
- Consumes: nothing (pure functions)
- Produces: `validate_HHMM`, `validate_period_label`, `validate_block_times`, `parse_HHMM`

---

- [ ] **Step 1: Write the failing test**

```python
# packages/core/tests/unit/test_input_validation.py
from datetime import time
import pytest
from operational.input_validation import validate_HHMM, parse_HHMM, validate_block_times

class TestValidateHHMM:
    def test_parses_valid_hhmm(self):
        assert validate_HHMM("05:00") == time(5, 0)
        assert validate_HHMM("23:59") == time(23, 59)
        assert validate_HHMM("00:00") == time(0, 0)

    def test_rejects_invalid_format(self):
        with pytest.raises(ValueError, match="HH:MM"):
            validate_HHMM("5:00")
        with pytest.raises(ValueError, match="HH:MM"):
            validate_HHMM("25:00")
        with pytest.raises(ValueError, match="HH:MM"):
            validate_HHMM("5-00")

    def test_rejects_non_string(self):
        with pytest.raises(TypeError):
            validate_HHMM(500)  # type: ignore


class TestValidateBlockTimes:
    def test_valid_block_ascending(self):
        start, end, dur = validate_block_times(time(5, 0), time(8, 30))
        assert start == time(5, 0)
        assert end == time(8, 30)
        assert dur == 210  # 3h30m

    def test_rejects_end_before_start(self):
        with pytest.raises(ValueError, match="end must be after start"):
            validate_block_times(time(8, 30), time(5, 0))
```

- [ ] **Step 2: Run test to verify it fails**

```
cd life-ops/operational && uv run pytest packages/core/tests/unit/test_input_validation.py -v
Expected: FAIL — ModuleNotFoundError: operational.input_validation
```

- [ ] **Step 3: Write minimal implementation**

```python
# packages/core/src/operational/input_validation.py
"""Time input validation helpers — shared between CLI (questionary) and TUI."""

from __future__ import annotations

from datetime import time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from operational.enums import Period

__all__ = ["validate_HHMM", "parse_HHMM", "validate_block_times"]


class HHMMValidationError(ValueError):
    """Raised when a HH:MM string is malformed or out of range."""


def parse_HHMM(value: str) -> tuple[int, int]:
    """Parse a 'HH:MM' string into (hour, minute) integers.

    Does NOT validate range. Raises HHMMValidationError on parse failure.

    Returns:
        (hour, minute) as ints.
    """
    if not isinstance(value, str):
        msg = f"expected string, got {type(value).__name__}"
        raise TypeError(msg)
    parts = value.split(":")
    if len(parts) != 2:
        msg = f"must be HH:MM, got {value!r}"
        raise HHMMValidationError(msg)
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        msg = f"must be HH:MM (numbers only), got {value!r}"
        raise HHMMValidationError(msg) from exc
    return hour, minute


def validate_HHMM(value: str) -> time:
    """Parse and validate a 'HH:MM' time string.

    Args:
        value: A string of the form 'HH:MM' (24-hour, zero-padded).

    Returns:
        datetime.time

    Raises:
        HHMMValidationError: If the string is not 'HH:MM' or hour/minute
            are out of range (hour 0-23, minute 0-59).
        TypeError: If value is not a string.
    """
    hour, minute = parse_HHMM(value)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        msg = f"HH:MM out of range: {value!r} (hour 0-23, minute 0-59)"
        raise HHMMValidationError(msg)
    return time(hour, minute)


def validate_block_times(start: time, end: time) -> tuple[time, time, int]:
    """Validate a time block's start < end and compute duration in minutes.

    Args:
        start: Block start time.
        end: Block end time.

    Returns:
        (start, end, duration_minutes).

    Raises:
        ValueError: If end is at or before start.
    """
    if end <= start:
        msg = f"end time ({end}) must be after start time ({start})"
        raise ValueError(msg)
    # Compute minutes difference (crossing midnight not allowed here)
    start_min = start.hour * 60 + start.minute
    end_min = end.hour * 60 + end.minute
    duration = end_min - start_min
    return start, end, duration
```

- [ ] **Step 4: Run test to verify it passes**

```
uv run pytest packages/core/tests/unit/test_input_validation.py -v
Expected: PASS (3 tests)
```

- [ ] **Step 5: Commit**

```bash
cd life-ops/operational
git add packages/core/src/operational/input_validation.py packages/core/tests/unit/test_input_validation.py
git commit -m "feat(core): add input_validation module with HHMM validators"
```

---

### Task 2: Add `questionary` dependency and `make_routine_log` factory

**Files:**
- Modify: `apps/cli/pyproject.toml` (add `questionary>=2.0`)
- Modify: `packages/core/pyproject.toml` (add `operational-core` workspace dep)
- Create: `packages/core/src/operational/meta/factories.py` additions (append `make_routine_log`)
- Test: `packages/core/tests/unit/test_factories.py`

**Interfaces:**
- Consumes: `RoutineLog` entity, `routine_cmd.py` REPO
- Produces: `make_routine_log` factory function

---

- [ ] **Step 1: Write the failing test for `make_routine_log`**

```python
# packages/core/tests/unit/test_factories.py (append)
from datetime import date
import pytest
from operational.meta.factories import make_routine_log
from operational.enums import Period, RoutineType

def test_make_routine_log_defaults():
    log = make_routine_log(
        routine_id="rou_test",
        date=date(2026, 8, 26),
        period=Period.MANHA,
        routine_type=RoutineType.CORE,
        text="Morning focus block completed.",
    )
    assert log.routine_id == "rou_test"
    assert log.date == date(2026, 8, 26)
    assert log.period == Period.MANHA
    assert log.routine_type == RoutineType.CORE
    assert log.text == "Morning focus block completed."
    assert log.id.startswith("rlog_")
```

- [ ] **Step 2: Run test to verify it fails**

```
uv run pytest packages/core/tests/unit/test_factories.py -v -k "test_make_routine_log"
Expected: FAIL — make_routine_log not defined
```

- [ ] **Step 3: Add `questionary` to `pyproject.toml`**

```toml
# apps/cli/pyproject.toml — add to dependencies array:
"questionary>=2.0",
```

- [ ] **Step 4: Add `make_routine_log` factory (append to `packages/core/src/operational/meta/factories.py`)**

```python
# Append after make_sleep_record (around line 185):

def make_routine_log(
    *,
    id: UEID | None = None,
    routine_id: UEID,
    date: date,
    period: Period,
    routine_type: RoutineType,
    text: str,
    block_id: UEID | None = None,
    energia_nivel: int | None = None,
    foco_nivel: int | None = None,
    humor: int | None = None,
    **overrides: Any,
) -> RoutineLog:
    """Build a RoutineLog with sensible defaults.

    Args:
        routine_id: UEID of the parent Routine.
        date: Date the routine was performed.
        period: Period of the routine.
        routine_type: Type of routine (ENTRY/CORE/TRANSITION/EXIT).
        text: NL description of the execution.

    Returns:
        RoutineLog
    """
    from uuid import uuid4
    from datetime import datetime, UTC

    _now = datetime.now(tz=UTC) if True else datetime.utcnow()
    base: dict[str, object] = {
        "id": id or f"rlog_{uuid4().hex[:12]}",
        "routine_id": routine_id,
        "block_id": block_id,
        "date": date,
        "period": period,
        "routine_type": routine_type,
        "text": text,
        "energia_nivel": energia_nivel,
        "foco_nivel": foco_nivel,
        "humor": humor,
        "created_at": _now,
    }
    base.update(overrides)
    return RoutineLog(**base)
```

- [ ] **Step 5: Run test to verify it passes**

```
uv run pytest packages/core/tests/unit/test_factories.py -v -k "test_make_routine_log"
Expected: PASS
```

- [ ] **Step 6: Commit**

```bash
git add apps/cli/pyproject.toml packages/core/src/operational/meta/factories.py packages/core/tests/unit/test_factories.py
git commit -m "feat: add questionary dependency + make_routine_log factory"
```

---

### Task 3: Create `journal_interact_cmd.py` — L2 interactive journal session

**Files:**
- Create: `apps/cli/src/operational/cli/commands/journal_interact_cmd.py`
- Modify: `apps/cli/src/operational/cli/app.py` (register the new command)
- Test: `tests/integration/test_journal_interact.py`

**Interfaces:**
- Consumes: `questionary`, `input_validation`, existing repos from `cli/state`, existing factories
- Produces: upserts `JournalEntry`, `SleepRecord`, `TimeBlock`, `RoutineLog`; new CLI command `journal interact`

---

- [ ] **Step 1: Write the command file**

```python
# apps/cli/src/operational/cli/commands/journal_interact_cmd.py
"""Journal interact — L2 systematic time-input session via questionary.

Architecture (per CLAUDE.md §Layer 3):
- Thin Typer controller ONLY; no business logic, no Rich construction.
- All time validation delegated to input_validation.py.
- All entity construction delegated to meta/factories.py.
- State writes via _PersistentRepo instances in cli/state.py.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, time, UTC
from typing import Annotated

import questionary
import typer
from questionary import ValidationError as QValidationError
from questionary import Validator

from operational.cli._compat import make_console
from operational.cli.state import (
    journals,
    routine_logs,
    sleep_records,
    time_blocks,
)
from operational.enums import Period, RoutineType
from operational.input_validation import validate_HHMM, validate_block_times, HHMMValidationError
from operational.meta.factories import (
    make_journal_entry,
    make_routine_log,
    make_sleep_record,
    make_time_block,
)
from operational.types import UEID

app = typer.Typer(help="Interactive journal session — systematic time input.")
console = make_console(width=120)


# ---------------------------------------------------------------------------
# Custom questionary validators
# ---------------------------------------------------------------------------

class HHMMValidator(Validator):
    def validate(self, document):
        text = document.text.strip()
        try:
            validate_HHMM(text)
        except (HHMMValidationError, TypeError):
            raise QValidationError(f"Must be HH:MM (e.g. 05:00, 23:59)")


class BlockTimesValidator(Validator):
    def validate(self, document):
        # Expects "HH:MM - HH:MM"
        text = document.text.strip()
        if " - " not in text:
            raise QValidationError('Use format "HH:MM - HH:MM" (e.g. 05:00 - 08:30)')
        try:
            start_str, end_str = text.split(" - ", 1)
            start = validate_HHMM(start_str.strip())
            end = validate_HHMM(end_str.strip())
            validate_block_times(start, end)
        except (HHMMValidationError, ValueError) as exc:
            raise QValidationError(str(exc))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ask_HHMM(prompt: str, default: str | None = None) -> time:
    while True:
        kwargs: dict[str, object] = {"message": prompt, "validator": HHMMValidator()}
        if default:
            kwargs["default"] = default
        raw = questionary.text(**kwargs).ask()
        if raw is None:
            raise KeyboardInterrupt("Cancelled")
        try:
            return validate_HHMM(raw.strip())
        except HHMMValidationError as exc:
            console.print(f"[red]Invalid:[/red] {exc}")


def _ask_block(prompt: str, default: str | None = None) -> tuple[time, time, int]:
    while True:
        kwargs: dict[str, object] = {
            "message": prompt,
            "validator": BlockTimesValidator(),
            "default": default or "HH:MM - HH:MM",
        }
        raw = questionary.text(**kwargs).ask()
        if raw is None:
            raise KeyboardInterrupt("Cancelled")
        try:
            start_str, end_str = raw.split(" - ", 1)
            start = validate_HHMM(start_str.strip())
            end = validate_HHMM(end_str.strip())
            _s, _e, dur = validate_block_times(start, end)
            return _s, _e, dur
        except (HHMMValidationError, ValueError) as exc:
            console.print(f"[red]Invalid:[/red] {exc}")


def _infer_period_from_time(t: time) -> Period:
    h = t.hour
    if 3 <= h < 8:
        return Period.MANHA
    if 8 <= h < 18:
        return Period.TARDE
    return Period.NOITE


def _now_naive() -> datetime:
    return datetime.now(tz=UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

@app.command(name="interact")
def interact(
    target_date: str | None = typer.Option(
        None, "--date", "-d", help="Date (YYYY-MM-DD, defaults to today)"
    ),
    json: bool = typer.Option(False, "--json", help="JSON output of created entries"),
) -> None:
    """Interactive journal session — systematic time input.

    Guides the user through recording:
    1. Wake time + sleep onset (optional SleepRecord)
    2. Morning / afternoon / evening time blocks (optional TimeBlocks)
    3. Pomodoro rounds completed (count only — timer is separate)
    4. Energy, focus, mood ratings
    5. Free-form narrative (optional, appended to JournalEntry.entry_text)

    All entities are upserted to the JSON flat-file store on completion.
    """
    console.print("\n[bold cyan]📓 PAV Daily Journal — Interactive Session[/bold cyan]\n")

    # Resolve target date
    if target_date:
        try:
            d = date.fromisoformat(target_date)
        except ValueError:
            console.print(f"[red]Invalid date format:[/red] {target_date!r} (use YYYY-MM-DD)")
            raise typer.Exit(1)
    else:
        d = date.today()

    # ---- 1. Sleep ----
    console.print("[bold]⏰ Sleep[/bold]")
    try:
        wake_str = questionary.text(
            "  Wake-up time (HH:MM)",
            default="06:00",
            validator=HHMMValidator(),
        ).ask()
        sleep_onset_str = questionary.text(
            "  Sleep onset time (HH:MM, previous night)",
            default="23:00",
            validator=HHMMValidator(),
        ).ask()
        quality_str = questionary.text(
            "  Sleep quality (1-10)",
            default="7",
        ).ask()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    try:
        wake_t = validate_HHMM(wake_str)
        sleep_t = validate_HHMM(sleep_onset_str)
        quality = int(quality_str)
        if not (1 <= quality <= 10):
            raise ValueError("quality 1-10")
    except (HHMMValidationError, ValueError):
        console.print("[red]Invalid sleep data — skipping sleep record.[/red]")
        wake_t = sleep_t = None
        quality = None

    # ---- 2. Time blocks ----
    blocks: list[tuple[time, time, int]] = []
    block_labels: list[str] = []
    console.print("\n[bold]🕐 Time Blocks[/bold]  (press Enter with empty to finish)")
    while True:
        try:
            label = questionary.text(
                "  Block label (e.g. Morning Focus, Lunch Pause)",
                default="",
            ).ask()
            if not label:
                break
            start, end, dur = _ask_block(
                f"  {label} — start and end (HH:MM - HH:MM)",
            )
            blocks.append((start, end, dur))
            block_labels.append(label)
            console.print(f"    [green]✓[/green] {start.strftime('%H:%M')} → {end.strftime('%H:%M')} ({dur} min)")
        except KeyboardInterrupt:
            break

    # ---- 3. Pomodoros ----
    console.print("\n[bold]🍅 Pomodoros[/bold]")
    try:
        rounds_str = questionary.text(
            "  Rounds completed today (integer, 0-12)",
            default="0",
        ).ask()
        pomodoros = int(rounds_str)
        if not (0 <= pomodoros <= 12):
            raise ValueError("0-12")
    except (ValueError, KeyboardInterrupt):
        pomodoros = 0

    # ---- 4. Energy / Focus / Mood ----
    console.print("\n[bold]⚡ Metrics[/bold]")
    try:
        energia_str = questionary.text("  Energy (1-10)", default="7").ask()
        foco_str = questionary.text("  Focus (1-10)", default="7").ask()
        humor_manhã_str = questionary.text("  Mood morning (1-5)", default="4").ask()
        humor_noite_str = questionary.text("  Mood evening (1-5)", default="3").ask()
    except KeyboardInterrupt:
        energia_str = foco_str = humor_manhã_str = humor_noite_str = ""

    def _try_int(s: str, lo: int, hi: int) -> int | None:
        try:
            v = int(s)
            return v if lo <= v <= hi else None
        except ValueError:
            return None

    energia = _try_int(energia_str, 1, 10)
    foco = _try_int(foco_str, 1, 10)
    humor_manhã = _try_int(humor_manhã_str, 1, 5)
    humor_noite = _try_int(humor_noite_str, 1, 5)

    # ---- 5. Free-form note ----
    console.print("\n[bold]📝 Notes[/bold]  (optional — press Enter to skip)")
    try:
        note = questionary.text("  Free-form narrative").ask() or ""
    except KeyboardInterrupt:
        note = ""

    # ---- Build and upsert entities ----
    console.print("\n[bold cyan]💾 Persisting...[/bold cyan]")

    # SleepRecord
    if wake_t and sleep_t and quality:
        slp = make_sleep_record(
            date=d,
            bedtime=sleep_t,
            wake_time=wake_t,
            quality_score=quality,
        )
        sleep_records.upsert(slp)

    # TimeBlocks
    now = _now_naive()
    for label, (start_t, end_t, _) in zip(block_labels, blocks):
        period = _infer_period_from_time(start_t)
        start_dt = datetime.combine(d, start_t)
        end_dt = datetime.combine(d, end_t)
        blk = make_time_block(
            label=label,
            start=start_dt,
            end=end_dt,
            period=period,
            energia_nivel=energia,
            foco_nivel=foco,
        )
        time_blocks.upsert(blk)

    # JournalEntry
    periods_covered = set[Period]()
    for start_t, _, _ in blocks:
        periods_covered.add(_infer_period_from_time(start_t))
    if wake_t:
        periods_covered.add(_infer_period_from_time(wake_t))

    journal = make_journal_entry(
        entry_date=d,
        entry_text=note,
        energia_nivel=energia,
        foco_nivel=foco,
        humor_morning=humor_manhã,
        humor_evening=humor_noite,
        pomodoros_completos=pomodoros,
        periods_covered=periods_covered,
    )
    journals.upsert(journal)

    # RoutineLog for each block (if it maps to a known routine — text-only for now)
    for label, (start_t, _, _) in zip(block_labels, blocks):
        period = _infer_period_from_time(start_t)
        rlog = make_routine_log(
            routine_id=UEID(f"rou_interact_{d.isoformat()}"),
            date=d,
            period=period,
            routine_type=RoutineType.CORE,
            text=label,
            energia_nivel=energia,
            foco_nivel=foco,
        )
        routine_logs.upsert(rlog)

    # ---- Summary ----
    console.print(f"\n[bold green]✓[/bold green] Journal for [bold]{d.isoformat()}[/bold] saved.")
    console.print(f"  SleepRecord: {'✓' if wake_t else '✗'}")
    console.print(f"  TimeBlocks: {len(blocks)} created")
    console.print(f"  Pomodoros: {pomodoros}")
    console.print(f"  JournalEntry: {journal.id}")

    if json:
        import json as _json
        typer.echo(
            _json.dumps(
                {
                    "date": d.isoformat(),
                    "sleep": {"bedtime": str(sleep_t), "wake": str(wake_t), "quality": quality} if sleep_t else None,
                    "blocks": [
                        {"label": lbl, "start": str(st), "end": str(en)}
                        for lbl, (st, en, _) in zip(block_labels, blocks)
                    ],
                    "pomodoros": pomodoros,
                    "energia": energia,
                    "foco": foco,
                    "humor_morning": humor_manhã,
                    "humor_evening": humor_noite,
                    "journal_id": journal.id,
                    "note_preview": (note[:60] + "…") if len(note) > 60 else note,
                },
                indent=2,
            )
        )
```

- [ ] **Step 2: Register in `app.py`**

Find the `journal_app` registration and add the interact subcommand. In `apps/cli/src/operational/cli/app.py`, after line 48 (where `journal_app` is added):

```python
# Add this import at the top of the file (around line 12):
# from operational.cli.commands import journal_interact_cmd

# In the app registration section, find where journal_app is added and add:
# app.add_typer(journal_interact_cmd.app, name="journal", help="Journal commands.")
# NOTE: journal_cmd and journal_interact_cmd are separate apps under the same "journal" name.
# To avoid conflict, rename journal_cmd's app to avoid double-registration:
# journal_cmd.app = typer.Typer(help="Journal entry commands (create/list).")
# journal_interact_cmd.app = typer.Typer(help="Interactive journal session.")
# Then both can be registered under the journal group.

# ACTUAL CHANGE (in app.py near line 38-48, the existing journal_app registration):
# The existing line:
#     app.add_typer(journal_cmd.app, name="journal", help="Manage journal entries.")
# Change to add BOTH subapps:
#     app.add_typer(journal_cmd.app, name="journal_create", help="Create/list journal entries.")
#     app.add_typer(journal_interact_cmd.app, name="journal", help="Journal: create or interact.")
# OR keep existing and add interact as a standalone command within journal_cmd.app.
# The simplest change: add journal_interact_cmd to the existing journal app.
# journal_cmd.app.add_typer(journal_interact_cmd.app, name="interact")
```

The actual minimal change: in `app.py`, add one line to import `journal_interact_cmd` and one line to register it. Since both `journal_cmd.app` and `journal_interact_cmd.app` are `typer.Typer()` instances, they can be combined:

```python
# In app.py — add import:
from operational.cli.commands import journal_cmd, journal_interact_cmd

# And change the existing journal registration to chain the interact subapp:
journal_app = typer.Typer(help="Journal commands.")
journal_app.add_typer(journal_cmd.app, name="create")  # journal create subcommand
journal_app.add_typer(journal_interact_cmd.app, name="interact")  # journal interact
app.add_typer(journal_app, name="journal")
```

This means the existing `journal create` and `journal list` commands become `journal create ...` and `journal interact` — no breaking change to L1.

- [ ] **Step 3: Run to verify it loads**

```bash
cd life-ops/operational && uv run pav journal interact --help
Expected: help output showing the interact command
```

- [ ] **Step 4: Commit**

```bash
git add apps/cli/src/operational/cli/commands/journal_interact_cmd.py apps/cli/src/operational/cli/app.py
git commit -m "feat(cli): add journal interact L2 command with questionary"
```

---

### Task 4: Integration tests for `journal interact`

**Files:**
- Create: `tests/integration/test_journal_interact.py`

---

- [ ] **Step 1: Write integration tests**

```python
# tests/integration/test_journal_interact_cmd.py
"""Integration tests for journal interact command.

Tests the full command by invoking it as a subprocess with mocked stdin,
verifying correct entities are upserted to the JSON store.
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest
from operational.cli.state import _state_dir

class TestJournalInteract:
    def test_creates_sleep_record_and_journal_entry(self, tmp_path, monkeypatch):
        """Given user enters sleep + energy data, entities are upserted."""
        # Set a temp state dir
        monkeypatch.setenv("TIME_TASKER_STATE_DIR", str(tmp_path))
        # Simulate: wake=05:00, sleep=23:00, quality=8,
        # no blocks, pomodoros=2, energy=7, focus=6, mood=4/3, no note
        inputs = (
            "05:00\n"      # wake
            "23:00\n"      # sleep onset
            "8\n"          # quality
            "\n"          # (blocks done)
            "2\n"          # pomodoros
            "7\n"          # energy
            "7\n"          # focus
            "4\n"          # mood morning
            "3\n"          # mood evening
            "\n"          # note (skip)
        )
        result = subprocess.run(
            [sys.executable, "-m", "operational.cli.app", "journal", "interact",
             "--date", "2026-08-26"],
            input=inputs,
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "TIME_TASKER_STATE_DIR": str(tmp_path)},
        )
        # Should not crash
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Check journal was written
        journal_file = tmp_path / "journals.json"
        assert journal_file.exists()
        entries = json.loads(journal_file.read_text())
        assert len(entries) == 1
        assert entries[0]["energia_nivel"] == 7
        assert entries[0]["pomodoros_completos"] == 2

    def test_json_flag_emits_json(self, tmp_path, monkeypatch):
        """--json flag produces valid JSON to stdout."""
        monkeypatch.setenv("TIME_TASKER_STATE_DIR", str(tmp_path))
        inputs = (
            "06:00\n23:00\n7\n\n0\n7\n7\n4\n3\n\n"
        )
        result = subprocess.run(
            [sys.executable, "-m", "operational.cli.app", "journal", "interact",
             "--date", "2026-08-26", "--json"],
            input=inputs,
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "TIME_TASKER_STATE_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "journal_id" in data
        assert data["pomodoros"] == 0
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/integration/test_journal_interact_cmd.py -v
Expected: PASS (or SKIP if stdin interaction is hard to test in CI — mark with @pytest.mark.skip)
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_journal_interact_cmd.py
git commit -m "test(integration): add journal interact command tests"
```

---

## Self-Review Checklist

- [ ] Spec coverage: sleep (SleepRecord), blocks (TimeBlock), pomodoros, energy/focus/mood, free-form note, JournalEntry — all 6 covered
- [ ] `questionary` added to `apps/cli/pyproject.toml` dependencies
- [ ] `input_validation.py` created with `validate_HHMM`, `parse_HHMM`, `validate_block_times`
- [ ] `make_routine_log` added to `factories.py`
- [ ] `journal interact` registered in `app.py` as `journal interact` (L1 `journal create` unchanged)
- [ ] No business logic in `journal_interact_cmd.py` — only orchestration
- [ ] Pydantic v2 frozen/extra=forbid respected throughout
- [ ] Tests: unit tests for validators, integration test for command
- [ ] No placeholder comments or TODOs

## Type Consistency Check

| Item | Defined in |
|---|---|
| `validate_HHMM(value: str) -> time` | Task 1 |
| `validate_block_times(start: time, end: time) -> tuple[time, time, int]` | Task 1 |
| `make_routine_log(...) -> RoutineLog` | Task 2 |
| `make_journal_entry(entry_date: date, entry_text: str, ...)` | Task 3 (existing factory) |
| `make_time_block(label, start: datetime, end: datetime, period: Period, ...)` | Task 3 (existing factory) |
| `make_sleep_record(date, bedtime: time, wake_time: time, quality_score: int)` | Task 3 (existing factory) |
| Repos: `journals`, `sleep_records`, `time_blocks`, `routine_logs` | `cli/state.py` (existing) |
