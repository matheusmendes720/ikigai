"""The cadence and the rich report.

The clock and the table are the two parts of this feature that can be wrong
without a socket: a next-run that is off by an hour, and a Markdown table that
the client renders as debris. Both are pure, so both are tested here.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, timezone
from typing import Any

import pytest

#: The module the cadence's constants live in — the tests shorten the wait,
#: and a test that waits fifteen minutes is a test nobody runs.
from src.bot import main as bot_main
from src.bot.cadence import Cadence, cadence_from_env, run_day
from src.bot.harness_client import HarnessError
from src.bot.main import Bot
from src.bot.rich import markdown_table, plain_table, report_markdown, rich_payload


def _utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)  # type: ignore[arg-type]


# ─── the clock ──────────────────────────────────────────────────────────────


def test_the_next_run_is_tonight_when_the_hour_has_not_come() -> None:
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")

    assert cadence.next_run(_utc(2026, 11, 9, 21, 0)) == _utc(2026, 11, 9, 22, 0)


def test_the_next_run_is_tomorrow_when_the_hour_has_passed() -> None:
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")

    assert cadence.next_run(_utc(2026, 11, 9, 22, 30)) == _utc(2026, 11, 10, 22, 0)


def test_the_next_run_is_STRICTLY_after() -> None:
    """Exactly at 22:00 asks for tomorrow.

    That single comparison is what makes a restart safe: a process that wakes
    a fraction of a second after the hour cannot deliver the same daily note
    a second time.
    """
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")

    assert cadence.next_run(_utc(2026, 11, 9, 22, 0)) == _utc(2026, 11, 10, 22, 0)


def test_the_offset_moves_the_hour_and_the_utc_day() -> None:
    """22:00 in -03:00 is 01:00 the NEXT day in UTC.

    A cadence that ignored the offset would fire at 19:00 local — three hours
    before the day it reports on has ended.
    """
    cadence = Cadence(
        at=time(22, 0), routine="daily-note", chat_id="42", offset=timedelta(hours=-3)
    )

    # 2026-11-10T00:30Z is 2026-11-09T21:30 in -03:00: tonight, still ahead.
    assert cadence.next_run(_utc(2026, 11, 10, 0, 30)) == _utc(2026, 11, 10, 1, 0)


def test_the_cadence_is_off_when_the_environment_names_no_time() -> None:
    assert cadence_from_env({}, {"42"}) is None


def test_a_word_can_turn_the_cadence_off() -> None:
    """The deployment ships with a time, so turning it off has to be a word.

    An empty value would be replaced by the compose default, and a typo would
    refuse to boot — `off` is the one spelling that means what it says.
    """
    assert cadence_from_env({"IKIGAI_CADENCE_AT": "off"}, {"42"}) is None
    assert cadence_from_env({"IKIGAI_CADENCE_AT": " OFF "}, {"42"}) is None


def test_a_malformed_time_raises_instead_of_switching_the_cadence_off() -> None:
    """A typo must not look like "never configured": both are silent."""
    with pytest.raises(ValueError):
        cadence_from_env({"IKIGAI_CADENCE_AT": "25:00"}, {"42"})
    with pytest.raises(ValueError):
        cadence_from_env({"IKIGAI_CADENCE_AT": "tonight"}, {"42"})


def test_the_chat_is_the_first_of_the_allowlist_when_none_is_named() -> None:
    """Sorted, so two processes on one configuration wake the same chat."""
    cadence = cadence_from_env(
        {"IKIGAI_CADENCE_AT": "22:00"}, {"913", "42", "7"}
    )

    assert cadence is not None
    assert cadence.chat_id == "42"


def test_an_explicit_chat_wins_over_the_allowlist() -> None:
    cadence = cadence_from_env(
        {"IKIGAI_CADENCE_AT": "22:00", "IKIGAI_CADENCE_CHAT_ID": "913"}, {"42"}
    )

    assert cadence is not None
    assert cadence.chat_id == "913"


def test_an_unresolvable_zone_falls_back_to_the_fixed_offset() -> None:
    """A slim container has no tz database; the cadence still fires."""
    cadence = cadence_from_env(
        {"IKIGAI_CADENCE_AT": "22:00", "IKIGAI_CADENCE_TZ": "Not/A_Zone"}, {"42"}
    )

    assert cadence is not None
    assert cadence.zone is None
    assert cadence.offset == timedelta(hours=-3)


# ─── the table ──────────────────────────────────────────────────────────────


def test_the_table_has_a_header_an_alignment_row_and_the_cells() -> None:
    table = markdown_table(
        ("Tipo", "Título", "Hora"),
        [("nota", "O dia", "22:00")],
        ("left", "left", "right"),
    )

    lines = table.splitlines()
    assert lines[0] == "| Tipo | Título | Hora |"
    assert lines[1] == "|:---|:---|---:|"
    assert lines[2] == "| nota | O dia | 22:00 |"


def test_a_pipe_in_a_cell_does_not_end_the_cell() -> None:
    """The caller's data is prose, and prose has pipes in it."""
    table = markdown_table(("Título",), [("a | b",)])

    assert table.splitlines()[2] == r"| a \| b |"


def test_a_newline_in_a_cell_becomes_a_space() -> None:
    table = markdown_table(("Título",), [(" duas\nlinhas ",)])

    assert table.splitlines()[2] == "| duas linhas |"


def test_an_empty_cell_is_a_dash_and_not_an_empty_column() -> None:
    table = markdown_table(("A", "B"), [("", "valor")])

    assert table.splitlines()[2] == "| — | valor |"


def test_a_short_row_is_padded_so_the_table_keeps_its_shape() -> None:
    table = markdown_table(("A", "B"), [("só uma",)])

    assert table.splitlines()[2] == "| só uma | — |"


def test_a_table_with_no_rows_is_still_a_table() -> None:
    """A quiet day renders as a heading and an empty table — not as nothing."""
    table = markdown_table(("A",), [])

    assert len(table.splitlines()) == 2


def test_the_plain_table_is_aligned() -> None:
    """The fallback is read in the same chat as the success; it cannot look
    like debris."""
    plain = plain_table(("Tipo", "Título"), [("nota", "O dia")])

    lines = plain.splitlines()
    assert lines[0].startswith("Tipo ")
    assert lines[1].startswith("----")
    assert lines[2].startswith("nota ")


def test_the_report_puts_the_heading_the_table_then_the_prose() -> None:
    markdown = report_markdown("# jÁ temos", "| A |\n|:---|", "o corpo", "2 artefatos")

    assert markdown.index("# jÁ temos") < markdown.index("| A |")
    assert markdown.index("| A |") < markdown.index("o corpo")
    assert markdown.rstrip().endswith("*2 artefatos*")


def test_the_payload_carries_exactly_one_content_field() -> None:
    """`rich_message` takes one of markdown, html or blocks; two is a
    rejection."""
    payload = rich_payload("42", "# Olá")

    assert payload["chat_id"] == "42"
    content = payload["rich_message"]
    assert list(content) == ["markdown"]
    assert content["markdown"] == "# Olá"


# ─── the whole run ──────────────────────────────────────────────────────────


class _Store:
    def __init__(self, artifacts: list[dict[str, Any]]) -> None:
        self._artifacts = artifacts
        self.calls: list[tuple[str, Any]] = []

    async def call(self, tool: str, arguments: Any) -> Any:
        self.calls.append((tool, arguments))
        return {"artifacts": self._artifacts}


class _Harness:
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
        return {"text": self._text, "duration_ms": 2500}


class _QuietBot(Bot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rich: list[tuple[str, str, str]] = []

    async def _send_rich(self, chat_id: str, markdown: str, fallback: str) -> None:
        self.rich.append((chat_id, markdown, fallback))


def _bot(store: Any, harness: Any, cadence: Cadence) -> _QuietBot:
    return _QuietBot(
        "token",
        store,
        {"42"},
        "owner",
        harness=harness,
        cadence=cadence,
    )


async def test_the_cadence_runs_the_routine_and_sends_a_rich_table() -> None:
    now = datetime.now(UTC)
    store = _Store(
        [
            {
                "kind": "nota",
                "title": "O dia de hoje",
                "updated_at": now.isoformat(),
            },
            {
                "kind": "nota",
                "title": "O dia de anteontem",
                "updated_at": (now - timedelta(days=2)).isoformat(),
            },
        ]
    )
    harness = _Harness("escrevi a nota do dia")
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")
    bot = _bot(store, harness, cadence)

    await bot._run_cadence(cadence)

    chat_id, markdown, fallback = bot.rich[0]

    assert chat_id == "42"
    assert "# daily-note — " in markdown
    assert "| Tipo | Título | Hora |" in markdown
    assert "O dia de hoje" in markdown
    assert "O dia de anteontem" not in markdown, "só o que foi escrito hoje entra"
    assert "escrevi a nota do dia" in markdown
    assert fallback.startswith("daily-note"), "o fallback repete o título"
    routine, session_id, chat_id, message, date = harness.calls[0]
    assert (routine, session_id, chat_id, message) == ("daily-note", "tg:42", "42", "")
    assert date == run_day(datetime.now(UTC)), (
        "a cadência não disse ao agente que dia é — a nota levaria o dia que o "
        "agente adivinhou"
    )


# ─── the day ─────────────────────────────────────────────────────────────────


def test_the_run_day_is_the_utc_day_of_the_run() -> None:
    """01:00Z on the 11th is 22:00 on the 10th, and the note names the 11th.

    Measured on the box, 2026-11-11: the cadence run of 01:00:00Z wrote
    `not:2026-11-11:74dfed05:d6ad7bd8023c5f59` — the note carries the run's own
    UTC day.
    """
    assert run_day(_utc(2026, 11, 11, 1, 0)) == "2026-11-11"


def test_the_run_day_advances_ONE_per_night() -> None:
    """The uid AND the idempotency key are derived from this day.

    A repeated key is swallowed by the store as `unchanged` BEFORE it looks at
    the body (`ikig.idempotency_keys`, `on conflict do nothing`), so a day
    that repeats would make the night's note vanish without a word. The rule
    that advances once per run is the contract, and this is what holds it.
    """
    nights = [
        run_day(_utc(2026, 11, 11, 1, 0)),
        run_day(_utc(2026, 11, 12, 1, 0)),
        run_day(_utc(2026, 11, 13, 1, 0)),
    ]

    assert nights == ["2026-11-11", "2026-11-12", "2026-11-13"]
    assert len(set(nights)) == len(nights), "um dia repetido é uma nota que não pode ser escrita"


def test_the_owners_day_is_ONE_BEHIND_the_run_day() -> None:
    """The report is titled with the owner's day; the note names the run's.

    This is the disagreement the owner has to settle (§11 of the tracker): the
    daily cycle fires at 22:00 in -03:00, which is 01:00Z of the NEXT day, so
    the two are one day apart BY CONSTRUCTION. The test states it, so that
    whoever moves one of them has to move this too.
    """
    now = _utc(2026, 11, 11, 1, 0)
    owner = timezone(timedelta(hours=-3))

    assert run_day(now) == "2026-11-11"
    assert now.astimezone(owner).strftime("%Y-%m-%d") == "2026-11-10"


# ─── the night is not lost ───────────────────────────────────────────────────


class _RefusingHarness:
    """A harness that REFUSES the first `refusals` runs, and answers after.

    The refusal is the harness's own: 409, the session is busy. It is what the
    cadence meets when the owner is in conversation with the bot.
    """

    def __init__(self, refusals: int, text: str = "escrevi a nota do dia") -> None:
        self._refusals = refusals
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
        if len(self.calls) <= self._refusals:
            raise HarnessError(
                "the session is busy: the routine did not start",
                status=bot_main.HARNESS_BUSY_STATUS,
            )
        return {"text": self._text, "duration_ms": 2500}


class _NightBot(_QuietBot):
    """A bot that remembers what it SENT — the owner's half of the night."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sent: list[str] = []

    async def _send(
        self,
        chat_id: str,
        text: str,
        buttons: Any = None,
        web_app: Any = None,
    ) -> None:
        self.sent.append(text)


def _night_bot(harness: Any, cadence: Cadence) -> _NightBot:
    return _NightBot(
        "token",
        _Store([]),
        {"42"},
        "owner",
        harness=harness,
        cadence=cadence,
    )


async def test_a_refused_night_is_tried_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """A busy session is not a lost night.

    Measured on the code (2026-11-11): the cadence runs in the OWNER's session
    (`session_id=f"tg:{cadence.chat_id}"`), so a night when the owner is in
    conversation with the bot is a night the harness REFUSES — and the loop
    used to go straight back to `next_run()`, which returns TOMORROW. The note
    of that night never existed, while the bot's own comment claimed the night
    was not lost.
    """
    monkeypatch.setattr(bot_main, "CADENCE_RETRY_S", 0)
    harness = _RefusingHarness(refusals=1)
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")
    bot = _night_bot(harness, cadence)

    await bot._run_the_night(cadence)

    assert len(harness.calls) == 2, (
        "a noite recusada não foi tentada outra vez — a nota do dia nunca chega a existir"
    )


async def test_the_retry_writes_the_note_of_the_NIGHT_and_not_of_the_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The day is the night's, not the attempt's.

    The note's uid AND its idempotency key derive from the day, and the store
    swallows a repeated key as `unchanged` BEFORE it looks at the body — so a
    retry that crossed midnight UTC would name tomorrow, and tomorrow's own
    run would be swallowed: tomorrow's note would vanish without a word.
    """
    monkeypatch.setattr(bot_main, "CADENCE_RETRY_S", 0)
    harness = _RefusingHarness(refusals=1)
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")
    bot = _night_bot(harness, cadence)

    await bot._run_the_night(cadence)

    days = {call[4] for call in harness.calls}
    assert len(days) == 1, (
        f"as tentativas escreveram dias diferentes: {days} — uma delas nomeia a nota de outra noite"
    )

    # And the day can be IMPOSED — that is what makes every attempt of the
    # same night write the same note, whatever day the retry lands on.
    await bot._run_cadence(cadence, day="2026-11-12")
    assert harness.calls[-1][4] == "2026-11-12", (
        "a rotina não aceitou o dia da noite — cada tentativa escreveria a nota "
        "do dia em que calhou"
    )


async def test_a_night_that_never_runs_is_declared_LOST(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ceiling is the truth: past it, the night IS lost — and it is said.

    A night that disappears without a word is the failure this path exists to
    prevent: the note of a day is the record of that day.
    """
    monkeypatch.setattr(bot_main, "CADENCE_RETRY_S", 0)
    monkeypatch.setattr(bot_main, "CADENCE_RETRY_MAX", 3)
    harness = _RefusingHarness(refusals=99)
    cadence = Cadence(at=time(22, 0), routine="daily-note", chat_id="42")
    bot = _night_bot(harness, cadence)

    await bot._run_the_night(cadence)

    assert len(harness.calls) == 4, (
        f"as tentativas não têm tecto: {len(harness.calls)} tentativas "
        f"(a primeira mais {bot_main.CADENCE_RETRY_MAX} re-tentativas)"
    )
    assert any("não existe" in text for text in bot.sent), (
        f"a noite perdida não foi dita ao dono: {bot.sent}"
    )


def test_the_refused_night_says_the_night_is_not_lost() -> None:
    """The message the owner reads when the NIGHT is refused.

    The manual refusal says "pede outra vez" — and that is right, because the
    owner asked. The night is not the owner's to ask again: the cadence asks
    again by itself.
    """
    night = bot_main._refused_night_message("daily-note")
    manual = bot_main._refused_message("daily-note")

    assert "não se perde" in night
    assert "não se perde" not in manual, (
        "a recusa manual não é a recusa da noite: o dono pediu, e o que se lhe "
        "diz é para pedir outra vez"
    )
