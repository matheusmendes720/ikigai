"""Journal interact — L2 interactive journal session via questionary.

Architecture (per CLAUDE.md §Layer 3):
- Thin Typer controller ONLY; no business logic, no Rich construction.
- All time validation delegated to input_validation.py.
- All entity construction delegated to meta/factories.py.
- State writes via _PersistentRepo instances in cli/state.py.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, UTC

import questionary
import typer

from operational.cli._compat import make_console
from operational.cli.state import journals, routine_logs, sleep_records, time_blocks
from operational.enums import Period, RoutineType
from operational.input_validation import (
    HHMMValidationError,
    validate_block_times,
    validate_HHMM,
)
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
# Helpers — manual validation (avoids questionary/prompt_toolkit CliRunner incompatibility)
# ---------------------------------------------------------------------------

_CANCELLED_MSG = "Cancelled"


def _ask_hhmm(prompt: str, default: str | None = None) -> time:
    """Ask for a HH:MM time, retrying on invalid input until valid or cancelled."""
    while True:
        raw = questionary.text(message=prompt, default=default).ask()
        if raw is None:
            raise KeyboardInterrupt(_CANCELLED_MSG)
        try:
            return validate_HHMM(raw.strip())
        except HHMMValidationError as exc:
            console.print(f"[red]Invalid:[/red] {exc}")


_BLOCK_FORMAT_MSG = "Use format 'HH:MM - HH:MM' (e.g. 05:00 - 08:30)"


def _ask_block(prompt: str, default: str | None = None) -> tuple[time, time, int]:
    """Ask for a block time range 'HH:MM - HH:MM', retrying on invalid input."""
    while True:
        raw = questionary.text(
            message=prompt,
            default=default or "HH:MM - HH:MM",
        ).ask()
        if raw is None:
            raise KeyboardInterrupt(_CANCELLED_MSG)
        if " - " not in raw:
            console.print(f"[red]Invalid:[/red] {_BLOCK_FORMAT_MSG}")
            continue
        start_str, end_str = raw.split(" - ", 1)
        try:
            start = validate_HHMM(start_str.strip())
            end = validate_HHMM(end_str.strip())
        except (HHMMValidationError, ValueError) as exc:
            console.print(f"[red]Invalid:[/red] {exc}")
            continue
        try:
            _s, _e, dur = validate_block_times(start, end)
        except ValueError as exc:
            console.print(f"[red]Invalid:[/red] {exc}")
            continue
        return _s, _e, dur


def _infer_period_from_time(t: time) -> Period:
    """Infer Period from hour of day."""
    h = t.hour
    if 3 <= h < 8:
        return Period.MANHA
    if 8 <= h < 18:
        return Period.TARDE
    return Period.NOITE


def _now_naive() -> datetime:
    """Return current UTC time as naive datetime (no tzinfo)."""
    return datetime.now(tz=UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

_INVALID_DATE_MSG = "Invalid date format: {target_date!r} (use YYYY-MM-DD)"
_SLEEP_QUALITY_ERR = "quality 1-10"
_POMODORO_ERR = "rounds must be 0-12"


@app.command(name="interact")
def interact(
    target_date: str | None = typer.Option(
        None, "--date", "-d", help="Date (YYYY-MM-DD, defaults to today)"
    ),
    json_output: bool = typer.Option(False, "--json", help="JSON output of created entries"),
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
            raise typer.Exit(1) from None
    else:
        d = date.today()

    # ---- 1. Sleep ----
    console.print("[bold]⏰ Sleep[/bold]")
    try:
        wake_t = _ask_hhmm("  Wake-up time (HH:MM)", default="06:00")
        sleep_t = _ask_hhmm("  Sleep onset time (HH:MM, previous night)", default="23:00")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0) from None
    else:
        quality_str = questionary.text(
            message="  Sleep quality (1-10)",
            default="7",
        ).ask()
        try:
            quality = int(quality_str or "0")
        except ValueError:
            quality = -1
        if not (1 <= quality <= 10):
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
                message="  Block label (e.g. Morning Focus, Lunch Pause)",
                default="",
            ).ask()
            if not label:
                break
            start, end, dur = _ask_block(f"  {label} — start and end (HH:MM - HH:MM)")
            blocks.append((start, end, dur))
            block_labels.append(label)
            console.print(
                f"    [green]✓[/green] {start.strftime('%H:%M')} → {end.strftime('%H:%M')} ({dur} min)"
            )
        except KeyboardInterrupt:
            break

    # ---- 3. Pomodoros ----
    console.print("\n[bold]🍅 Pomodoros[/bold]")
    try:
        rounds_str = questionary.text(
            message="  Rounds completed today (integer, 0-12)",
            default="0",
        ).ask()
        pomodoros = int(rounds_str or "0")
    except ValueError:
        pomodoros = 0
    except KeyboardInterrupt:
        pomodoros = 0
    else:
        if not (0 <= pomodoros <= 12):
            pomodoros = 0

    # ---- 4. Energy / Focus / Mood ----
    console.print("\n[bold]⚡ Metrics[/bold]")
    try:
        energia_str = questionary.text(message="  Energy (1-10)", default="7").ask() or ""
        foco_str = questionary.text(message="  Focus (1-10)", default="7").ask() or ""
        humor_am_str = questionary.text(message="  Mood morning (1-5)", default="4").ask() or ""
        humor_pm_str = questionary.text(message="  Mood evening (1-5)", default="3").ask() or ""
    except KeyboardInterrupt:
        energia_str = foco_str = humor_am_str = humor_pm_str = ""

    def _try_int(s: str, lo: int, hi: int) -> int | None:
        try:
            v = int(s)
        except ValueError:
            return None
        else:
            if lo <= v <= hi:
                return v
            return None

    energia = _try_int(energia_str, 1, 10)
    foco = _try_int(foco_str, 1, 10)
    humor_am = _try_int(humor_am_str, 1, 5)
    humor_pm = _try_int(humor_pm_str, 1, 5)

    # ---- 5. Free-form note ----
    console.print("\n[bold]📝 Notes[/bold]  (optional — press Enter to skip)")
    try:
        note = questionary.text(message="  Free-form narrative").ask() or ""
    except KeyboardInterrupt:
        note = ""

    # ---- Build and upsert entities ----
    console.print("\n[bold cyan]💾 Persisting...[/bold cyan]")

    # SleepRecord
    if wake_t and sleep_t and quality is not None:
        slp = make_sleep_record(
            record_date=d,
            bedtime=sleep_t,
            wake_time=wake_t,
            quality_score=quality,
        )
        sleep_records.upsert(slp)

    # TimeBlocks
    for label, (start_t, end_t, _) in zip(block_labels, blocks, strict=True):
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
    periods_covered: set[Period] = set()
    for start_t, _, _ in blocks:
        periods_covered.add(_infer_period_from_time(start_t))
    if wake_t:
        periods_covered.add(_infer_period_from_time(wake_t))

    journal = make_journal_entry(
        entry_date=d,
        entry_text=note,
        energia_nivel=energia,
        foco_nivel=foco,
        humor_morning=humor_am,
        humor_evening=humor_pm,
        pomodoros_completos=pomodoros,
        periods_covered=periods_covered,
    )
    journals.upsert(journal)

    # RoutineLog for each block
    for label, (start_t, _, _) in zip(block_labels, blocks, strict=True):
        period = _infer_period_from_time(start_t)
        rlog = make_routine_log(
            routine_id=UEID(f"rou_interact_{d.strftime('%Y_%m_%d')}"),
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

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "date": d.isoformat(),
                    "sleep": {
                        "bedtime": str(sleep_t),
                        "wake": str(wake_t),
                        "quality": quality,
                    }
                    if sleep_t
                    else None,
                    "blocks": [
                        {"label": lbl, "start": str(st), "end": str(en)}
                        for lbl, (st, en, _) in zip(block_labels, blocks, strict=True)
                    ],
                    "pomodoros": pomodoros,
                    "energia": energia,
                    "foco": foco,
                    "humor_morning": humor_am,
                    "humor_evening": humor_pm,
                    "journal_id": journal.id,
                    "note_preview": (note[:60] + "…") if len(note) > 60 else note,
                },
                indent=2,
            )
        )
