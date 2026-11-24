"""The weekly review: the second clock, and the daily one that did not move.

Two promises are tested here, and the second is the reason the file exists.

- **The weekly recurrence is right.** `next_run` with a `weekday` has to land
  on that weekday, on the OWNER's clock and not the container's, strictly after
  `now`, and exactly once a week. A review that fires on Wednesday, or twice on
  Sunday, or at the UTC hour, is a review nobody asked for.
- **The daily cadence is UNTOUCHED.** The daily cases below are the same
  comparisons `test_bot_cadence.py` already makes, run again against the class
  that now carries a `weekday` field: same constructor, same `next_run`, the
  weekday left at `None`. If adding weekly recurrence moved the nightly note by
  an hour or by a day, it fails here and not in the owner's chat at 22:00.

`test_bot_cadence.py` is append-only and was NOT edited. This file is the
second one the drift net grows, and it brings its own doubles on purpose: a
guard that imports another guard's fixtures inherits the day it stops passing.
"""

from __future__ import annotations

import asyncio
import itertools
from datetime import UTC, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from src.bot.cadence import Cadence, run_day, weekly_cadence_from_env
from src.bot.main import Bot

#: The owner's clock, the one the deployment ships (`DEFAULT_OFFSET`).
OWNER = timedelta(hours=-3)

#: `datetime.weekday()` numbering: 6 is Sunday, and Sunday is the default.
SUNDAY = 6


def _utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)  # type: ignore[arg-type]


def _weekly(**kwargs: Any) -> Cadence:
    """The review the deployment runs: Sunday 20:00, on the owner's clock."""
    cadence: dict[str, Any] = {
        "at": time(20, 0),
        "routine": "weekly-review",
        "chat_id": "42",
        "offset": OWNER,
        "weekday": SUNDAY,
    }
    cadence.update(kwargs)
    return Cadence(**cadence)


# ─── the weekly clock ───────────────────────────────────────────────────────


def test_the_weekly_run_lands_on_the_named_weekday() -> None:
    """Monday asks for the Sunday that is still ahead, and not for Tuesday."""
    cadence = _weekly()

    # 2026-11-23 is a Monday; 12:00Z is 09:00 on the owner's clock.
    assert cadence.next_run(_utc(2026, 11, 23, 12, 0)) == _utc(2026, 11, 29, 23, 0)


def test_the_weekly_run_is_strictly_after() -> None:
    """Exactly at the instant the review fires asks for NEXT Sunday.

    The daily cadence lives on this same comparison: it is what makes a
    restart safe. A weekly process that wakes at 20:00:00.4 and re-derives its
    target must not deliver the same review a second time, and the store would
    not stop it — the retry would simply write over the note it just made.
    """
    cadence = _weekly()

    assert cadence.next_run(_utc(2026, 11, 29, 23, 0)) == _utc(2026, 12, 6, 23, 0)


def test_the_weekday_is_read_on_the_owners_clock_and_not_the_containers() -> None:
    """02:00Z on a Sunday is still Saturday evening for the owner.

    A cadence that asked the UTC clock "is it Sunday yet" would fire at 20:00Z
    — seventeen hours before the week it reviews has ended, in the middle of
    the owner's Saturday.
    """
    cadence = _weekly()

    assert cadence.next_run(_utc(2026, 11, 29, 2, 0)) == _utc(2026, 11, 29, 23, 0)

    # And the same clock on a Wednesday: the answer is not "today at 20:00",
    # because a cadence that waits for a weekday is not a daily one.
    assert cadence.next_run(_utc(2026, 11, 25, 12, 0)) == _utc(2026, 11, 29, 23, 0)


def test_the_week_wraps_forward_and_never_backwards() -> None:
    """Monday (0) from a Sunday (6) is ONE day ahead, not six behind.

    This is the arithmetic the daily cadence never had to do: the target
    weekday number can be lower than today's, and `% 7` is what turns `-6`
    into `+1`. Get it wrong and the review fires six days early, every week.
    """
    cadence = _weekly(weekday=0)

    # 2026-11-29T02:00Z is Sunday 23:00 local; the next Monday 20:00 is 30/11.
    assert cadence.next_run(_utc(2026, 11, 29, 2, 0)) == _utc(2026, 11, 30, 23, 0)


def test_a_sunday_that_already_had_its_hour_waits_for_the_next_one() -> None:
    """The target day is today, the hour is past: a whole week, not a day."""
    cadence = _weekly()

    # 2026-11-30T00:00Z is Sunday 21:00 local — the review already happened.
    assert cadence.next_run(_utc(2026, 11, 30, 0, 0)) == _utc(2026, 12, 6, 23, 0)


def test_the_weekly_run_fires_once_a_week_and_never_on_another_day() -> None:
    """Six consecutive targets: all Sunday on the owner's clock, 7 days apart.

    The property, not the instance — a recurrence that drifted a day per fire
    would pass every single-step case above.
    """
    cadence = _weekly()
    local = timezone(OWNER)
    now = _utc(2026, 11, 23, 12, 0)

    fires = []
    for _ in range(6):
        now = cadence.next_run(now)
        fires.append(now)

    assert [f.astimezone(local).strftime("%A %H:%M") for f in fires] == ["Sunday 20:00"] * 6
    gaps = {b - a for a, b in itertools.pairwise(fires)}
    assert gaps == {timedelta(days=7)}, f"the review is not one week per fire: {gaps}"


def test_the_weekly_runs_never_share_a_run_day() -> None:
    """`run_day` is the idempotency key's day, and weekly runs must not collide.

    The note's uid AND its idempotency key are derived from `run_day`, and the
    store swallows a repeated key as `unchanged` BEFORE it looks at the body.
    The UTC day was written for a nightly cycle; a weekly one is seven UTC days
    apart, so the same rule holds — but only because `next_run` is strictly
    after. This is what pins it.
    """
    cadence = _weekly()
    now = _utc(2026, 11, 23, 12, 0)

    days = []
    for _ in range(5):
        now = cadence.next_run(now)
        days.append(run_day(now))

    assert days == ["2026-11-29", "2026-12-06", "2026-12-13", "2026-12-20", "2026-12-27"]
    assert len(set(days)) == len(days), "two weekly runs naming one day: one writes nothing"


# ─── the daily cadence did not move ─────────────────────────────────────────


def test_a_daily_cadence_still_has_no_weekday() -> None:
    """Constructed the old way, in the old order — and `weekday` is `None`.

    The new field is LAST and defaulted, so every existing positional
    `Cadence(at, routine, chat_id, offset, zone)` still means the daily thing.
    """
    cadence = Cadence(time(22, 0), "daily-note", "42", OWNER)

    assert cadence.weekday is None


def test_the_daily_next_run_is_unchanged_before_the_hour() -> None:
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")

    assert cadence.next_run(_utc(2026, 11, 23, 21, 0)) == _utc(2026, 11, 23, 22, 0)


def test_the_daily_next_run_is_unchanged_after_the_hour() -> None:
    """The hour passed, so the answer is tomorrow — a DAY, not next Sunday.

    Read together with the case above: the daily cadence fires on days that are
    not its weekday (2026-11-23 is a Monday, 2026-11-24 a Tuesday), which is
    exactly what a `weekday is None` branch has to keep doing.
    """
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")

    assert cadence.next_run(_utc(2026, 11, 23, 22, 30)) == _utc(2026, 11, 24, 22, 0)


# ─── the environment ────────────────────────────────────────────────────────


def test_the_weekly_clock_is_off_when_the_environment_names_no_time() -> None:
    assert weekly_cadence_from_env({}, {"42"}) is None


def test_a_word_can_turn_the_weekly_review_off() -> None:
    """The same spellings as the daily, because the same trap applies: the
    compose default would replace an empty value with a time again."""
    for word in ("off", " OFF ", "none", "no", "never"):
        assert weekly_cadence_from_env({"IKIGAI_WEEKLY_AT": word}, {"42"}) is None


def test_the_daily_time_does_not_start_the_weekly_clock() -> None:
    """Two variables, two clocks — a deployment with only the nightly note is a
    deployment that keeps only the nightly note."""
    env = {"IKIGAI_CADENCE_AT": "22:00"}

    assert weekly_cadence_from_env(env, {"42"}) is None


def test_the_weekly_defaults_are_sunday_and_the_weekly_review() -> None:
    cadence = weekly_cadence_from_env({"IKIGAI_WEEKLY_AT": "20:00"}, {"42"})

    assert cadence is not None
    assert cadence.weekday == 6
    assert cadence.routine == "weekly-review"
    assert cadence.at == time(20, 0)
    assert cadence.offset == OWNER, "it borrows the daily's owner clock"


def test_the_weekly_chat_is_the_first_of_the_allowlist_when_none_is_named() -> None:
    """Sorted, so the review and the nightly note wake the SAME chat."""
    cadence = weekly_cadence_from_env({"IKIGAI_WEEKLY_AT": "20:00"}, {"913", "42", "7"})

    assert cadence is not None
    assert cadence.chat_id == "42"


def test_an_explicit_weekly_chat_wins_over_the_allowlist() -> None:
    cadence = weekly_cadence_from_env(
        {"IKIGAI_WEEKLY_AT": "20:00", "IKIGAI_WEEKLY_CHAT_ID": "913"}, {"42"}
    )

    assert cadence is not None
    assert cadence.chat_id == "913"


def test_a_malformed_weekly_time_names_the_weekly_variable() -> None:
    """A typo must not look like "never configured", and must not blame the
    nightly note: the message names what it actually read."""
    with pytest.raises(ValueError, match="IKIGAI_WEEKLY_AT"):
        weekly_cadence_from_env({"IKIGAI_WEEKLY_AT": "25:00"}, {"42"})
    with pytest.raises(ValueError, match="IKIGAI_WEEKLY_AT"):
        weekly_cadence_from_env({"IKIGAI_WEEKLY_AT": "tonight"}, {"42"})


def test_a_malformed_weekday_refuses_to_boot() -> None:
    """A weekday nobody can read would move the review to a day nobody chose."""
    for spelling in ("fundo", "7", "8", "satu", "sday"):
        env = {"IKIGAI_WEEKLY_AT": "20:00", "IKIGAI_WEEKLY_WEEKDAY": spelling}
        with pytest.raises(ValueError, match="IKIGAI_WEEKLY_WEEKDAY"):
            weekly_cadence_from_env(env, {"42"})


def test_the_weekday_is_a_name_or_a_digit_in_any_case() -> None:
    """The deployment writes `sunday`; a person at a keyboard writes `Sun`."""
    for spelling, expected in (("saturday", 5), ("SAT", 5), (" sun ", 6), ("0", 0), ("wed", 2)):
        cadence = weekly_cadence_from_env(
            {"IKIGAI_WEEKLY_AT": "20:00", "IKIGAI_WEEKLY_WEEKDAY": spelling}, {"42"}
        )

        assert cadence is not None, spelling
        assert cadence.weekday == expected, spelling


def test_a_weekly_clock_with_nobody_to_wake_is_an_error() -> None:
    """The daily returns `None` for no chat; the weekly has already been asked
    for by a time that IS set, so silence would be a lost week."""
    with pytest.raises(ValueError, match="chat"):
        weekly_cadence_from_env({"IKIGAI_WEEKLY_AT": "20:00"}, set())


def test_the_named_zone_is_honoured_when_this_machine_knows_it() -> None:
    cadence = weekly_cadence_from_env(
        {"IKIGAI_WEEKLY_AT": "20:00", "IKIGAI_CADENCE_TZ": "America/Sao_Paulo"}, {"42"}
    )

    assert cadence is not None
    assert cadence.zone == ZoneInfo("America/Sao_Paulo")


def test_an_unresolvable_zone_leaves_the_weekly_on_the_fixed_offset() -> None:
    """A slim container has no tz database; the review still fires on Sunday."""
    cadence = weekly_cadence_from_env(
        {"IKIGAI_WEEKLY_AT": "20:00", "IKIGAI_CADENCE_TZ": "Not/A_Zone"}, {"42"}
    )

    assert cadence is not None
    assert cadence.zone is None
    assert cadence.offset == OWNER


# ─── the whole run ──────────────────────────────────────────────────────────


class _Harness:
    """The agent's door: what the cadence asked for, and the prose it answered."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[tuple[str, str, str, str, str | None]] = []

    async def run_routine(
        self,
        routine: str,
        *,
        session_id: str,
        chat_id: str,
        message: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append((routine, session_id, chat_id, message, date))
        return {"text": self._text, "duration_ms": 1200}


class _RecordingBot(Bot):
    """A bot that keeps what it would have sent, instead of sending it."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rich: list[tuple[str, str, str]] = []

    async def _send_rich(self, chat_id: str, markdown: str, fallback: str) -> None:
        self.rich.append((chat_id, markdown, fallback))


async def test_the_weekly_cadence_runs_the_weekly_routine_and_reports() -> None:
    """The review the owner reads, end to end through the real `_run_cadence`.

    Same path as the nightly note and the same rich delivery — which is the
    point: the weekly is a second Cadence, not a second mechanism. What has to
    be different is the ROUTINE the harness is asked for and the day it is
    handed, because the note's uid and idempotency key are made from that day.
    """
    harness = _Harness("a semana teve 4 tarefas e 1 sonho")
    bot = _RecordingBot(
        token="t",
        client=None,
        allowed={"42"},
        client_id="tg:42",
        harness=harness,
        weekly=_weekly(),
    )

    await bot._run_cadence(bot._weekly, day="2026-11-22")

    routine, session_id, chat_id, message, date = harness.calls[0]
    assert routine == "weekly-review", "a weekly clock that runs the daily routine is two dailies"
    assert session_id == "tg:42"
    assert chat_id == "42"
    assert message == ""
    assert date == "2026-11-22", "the run did not tell the agent which day to name"

    assert len(bot.rich) == 1, "a cadence run that reports nothing is a run nobody knows about"
    sent_chat, markdown, fallback = bot.rich[0]
    assert sent_chat == "42"
    assert "# weekly-review — " in markdown
    assert "a semana teve 4 tarefas e 1 sonho" in markdown
    assert "| Tipo | Título | Hora |" in markdown, "the report is a table, as the daily's is"
    assert fallback.startswith("weekly-review"), "o fallback repete o título"


async def test_the_weekly_loop_is_a_sibling_and_not_a_second_mechanism() -> None:
    """`_cadence_loop` takes the clock it carries.

    The weekly is the same coroutine handed the other `Cadence`, so every fix
    the nightly path ever got — the refused night, the retry that keeps the
    night's day, the lost night that is declared — is already the weekly's too.
    A second loop would have had to re-grow all three.
    """
    harness = _Harness("ok")
    bot = _RecordingBot(token="t", client=None, allowed={"42"}, client_id="tg:42", harness=harness)

    assert bot._cadence is None
    assert bot._weekly is None
    # A clock nobody set: the loop returns instead of sleeping forever.
    await asyncio.wait_for(bot._cadence_loop(None), 1)

    # And the same call with a real clock runs the night it belongs to.
    bot._weekly = _weekly()
    await bot._run_the_night(bot._weekly)

    assert harness.calls[0][0] == "weekly-review"
