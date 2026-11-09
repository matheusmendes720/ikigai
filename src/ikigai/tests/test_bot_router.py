"""The router, and the token an inline button carries.

Both are pure functions on purpose. The parts of the bot that talk to Telegram
cannot be tested without a socket; the decision — "what does this sentence
mean", "what did this button mean" — can, and it is the decision that goes
wrong quietly.
"""

from __future__ import annotations

import pytest

from src.bot.router import Route, callback_data, parse_callback, route

ROUTINES = {
    "daily-note": "the day",
    "weekly-review": "the week",
    "monthly-review": "the month",
    "quarterly-plan": "the quarter",
}


def test_a_sentence_names_a_routine() -> None:
    assert route("fecha o dia", ROUTINES) == Route(
        routine="daily-note", slots={}, why="fecha o dia"
    )


def test_the_relative_day_is_carried_as_a_slot() -> None:
    """Yesterday and today are the same routine and different work."""
    routed = route("Fecha o dia de ontem.", ROUTINES)
    assert routed is not None
    assert routed.routine == "daily-note"
    assert routed.slots == {"when": "ontem"}


def test_accents_and_case_do_not_change_the_reading() -> None:
    """The owner types `revisão` and `revisao` and means one thing."""
    accented = route("Revisão da semana", ROUTINES)
    plain = route("REVISAO DA SEMANA", ROUTINES)
    assert accented is not None
    assert accented == plain
    assert accented.routine == "weekly-review"


@pytest.mark.parametrize(
    "text",
    [
        "heloo",
        "bom dia",
        "a semana foi longa",
        "obrigado",
        "",
        "   ",
    ],
)
def test_a_sentence_that_names_no_routine_is_refused(text: str) -> None:
    """A marker must carry a verb. "a semana foi longa" is prose about a week,
    not an instruction to review it — and it belongs to the draft."""
    assert route(text, ROUTINES) is None


def test_two_routines_in_one_sentence_is_an_abstention() -> None:
    """Two VERBS is two jobs, and running one of them silently is the bot
    picking a job it was not asked to pick."""
    assert route("fecha o dia e depois fecha a semana", ROUTINES) is None


def test_a_bare_noun_after_a_verb_is_prose_and_not_a_second_job() -> None:
    """ "fecha a semana e o mês" is one command with two nouns, not two
    commands.

    The verbs are what bind: the table matches "fecha a semana", and the
    month rides along as prose for the weekly review to read. The alternative
    — matching a bare "o mês" — would claim "o mês foi difícil", which is a
    sentence the owner meant as a thought.
    """
    routed = route("fecha a semana e o mês", ROUTINES)
    assert routed is not None
    assert routed.routine == "weekly-review"


def test_a_routine_the_caller_does_not_have_is_not_routable() -> None:
    """The caller's table is the vocabulary; a list kept here would be a
    second source of what exists."""
    without_daily = {k: v for k, v in ROUTINES.items() if k != "daily-note"}
    assert route("fecha o dia", without_daily) is None


def test_a_button_token_round_trips() -> None:
    token = callback_data("draft.guardar")
    assert parse_callback(token) == ("draft.guardar", "")


def test_a_button_token_carries_its_argument() -> None:
    token = callback_data("run", "weekly-review")
    assert parse_callback(token) == ("run", "weekly-review")


def test_the_token_respects_the_telegram_cap() -> None:
    """64 bytes, and Telegram does not say so — it fails at send time."""
    assert len(callback_data("run", "x" * 200)) == 64


@pytest.mark.parametrize("data", ["", "v2:draft.guardar", "draft.guardar", "v1:", "v1: :"])
def test_a_token_this_bot_did_not_send_is_refused(data: str) -> None:
    """A button from last week's deploy is still tappable. Refusing it is how
    the poll loop survives the tap."""
    assert parse_callback(data) is None
