"""The channel: how a question the agent asked becomes buttons.

The decisions that go wrong quietly are here: a button whose payload is too
long for Telegram (64 bytes, and the failure is SILENT), an option's text
travelling as the answer (so a truncated option becomes a truncated answer),
and a question drawn twice.
"""

from __future__ import annotations

from src.bot.channel import (
    Question,
    answer_buttons,
    parse_question,
    question_keyboard,
    question_text,
)
from src.bot.router import callback_data, parse_callback


def _question(**kwargs) -> Question:
    base = {"id": "a1b2c3", "kind": "choice", "question": "Nota ou sonho?"}
    base.update(kwargs)
    return Question(**base)  # type: ignore[arg-type]


def test_a_choice_becomes_one_button_per_option() -> None:
    rows = question_keyboard(_question(options=("nota", "sonho")))
    labels = [label for row in rows for label, _, _ in row]
    assert labels == ["nota", "sonho"]


def test_two_options_share_a_row() -> None:
    """A phone fits two short labels side by side; a column of six is a menu
    the owner has to scroll."""
    rows = question_keyboard(_question(options=("a", "b", "c", "d")))
    assert [len(row) for row in rows] == [2, 2]


def test_a_confirmation_is_two_buttons() -> None:
    rows = question_keyboard(_question(kind="confirm", options=()))
    labels = [label for row in rows for label, _, _ in row]
    assert labels == ["Sim", "Não"]


def test_a_free_form_question_gets_one_button_that_arms_the_chat() -> None:
    """The answer is prose; the button cannot carry it. The button's only job
    is to say "I am ready to write"."""
    rows = question_keyboard(_question(kind="text"))
    assert len(rows) == 1
    assert len(rows[0]) == 1
    label, verb, argument = rows[0][0]
    assert label == "✍️ Responder"
    assert verb == "ask.type"
    assert argument == "a1b2c3"


def test_the_option_text_never_travels_in_the_button() -> None:
    """Telegram caps `callback_data` at 64 bytes and fails SILENTLY past it.
    The option's text is the runtime's, and the runtime resolves the index."""
    long_option = "uma opção que o agente escreveu e que é bastante comprida mesmo"
    rows = question_keyboard(_question(options=(long_option,)))
    _, verb, argument = rows[0][0]
    payload = callback_data(verb, argument)
    assert len(payload.encode("utf-8")) <= 64
    assert long_option not in payload
    # And what travels identifies the option by its POSITION.
    assert argument == "a1b2c3:0"


def test_a_button_survives_the_round_trip() -> None:
    """The payload is built in one place and read in another; a change in
    either that breaks the other is a button that does nothing."""
    rows = question_keyboard(_question(options=("nota", "sonho")))
    _, verb, argument = rows[0][0]
    parsed = parse_callback(callback_data(verb, argument))
    assert parsed is not None
    read_verb, read_argument = parsed
    assert answer_buttons(read_verb, read_argument) == ("a1b2c3", "#0")


def test_a_button_of_another_channel_is_refused() -> None:
    assert answer_buttons("draft.guardar", "a1b2c3") is None
    assert answer_buttons("ask.pick", "") is None
    assert answer_buttons("ask.pick", "a1b2c3:zero") is None


def test_the_typed_answer_is_recognised() -> None:
    assert answer_buttons("ask.type", "a1b2c3") == ("a1b2c3", "#type")


def test_a_question_without_an_id_cannot_be_drawn() -> None:
    """A button with no question behind it is a button that answers nothing."""
    assert parse_question({"id": "", "question": "x"}) is None
    assert parse_question({"id": "a1", "question": ""}) is None
    assert parse_question(None) is None


def test_the_question_is_read_from_the_runtime_event() -> None:
    question = parse_question(
        {
            "id": "a1b2c3",
            "kind": "choice",
            "question": "Nota ou sonho?",
            "options": ["nota", "sonho"],
        }
    )
    assert question is not None
    assert question.id == "a1b2c3"
    assert question.options == ("nota", "sonho")
    assert question.is_free_form is False


def test_the_message_says_the_question_is_the_agents() -> None:
    """The answer goes to the agent, so the question has to look like the
    agent's — not like the bot's."""
    text = question_text(_question())
    assert "Nota ou sonho?" in text
    assert "❓" in text
