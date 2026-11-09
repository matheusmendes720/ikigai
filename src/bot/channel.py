"""The channel: a question the agent asked, rendered the way Telegram renders.

The runtime asks; the owner answers; the agent continues. This module is the
middle of that sentence — the part that turns a question into BUTTONS.

It is deliberately small and deliberately dumb, like ``router.py`` next to it:

- it knows FOUR shapes of question (choice, confirm, text, editor) and what
  each one looks like on a phone;
- it never decides anything — the option the owner picks is sent to the
  runtime, and the RUNTIME resolves it against the question it asked;
- it never keeps the answer. The question lives in the runtime (so a restart
  does not lose it), and this module only knows how to DRAW it.

WHY THE OPTION IS CARRIED AS AN INDEX AND NOT AS TEXT: Telegram caps
``callback_data`` at 64 bytes, and an option the agent proposed can be a
sentence. The index is small, and the runtime still holds the real text — so
a truncated option can never become a truncated ANSWER.

WHY A FREE-FORM ANSWER GETS A BUTTON AND NOT A KEYBOARD: the answer is prose
the owner types. The button does not carry the answer; it ARMS the chat, and
the next message the owner writes IS the answer. That is the only way a
paragraph can travel through a channel made of buttons.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "Question",
    "answer_buttons",
    "parse_question",
    "question_keyboard",
    "question_text",
]

#: The verb of a button that PICKS an option: the argument is the index of
#: the option in the question the runtime asked.
VERB_PICK = "ask.pick"

#: The verb of a button that ARMS the chat for a typed answer: the argument
#: is the question's id, and the answer arrives as the next message.
VERB_TYPE = "ask.type"


@dataclass(frozen=True)
class Question:
    """One question, as the channel needs to draw it."""

    id: str
    kind: str
    question: str
    options: tuple[str, ...] = ()

    @property
    def is_free_form(self) -> bool:
        """Does the owner have to WRITE this one?"""
        return self.kind in ("text", "editor")


def parse_question(payload: dict[str, Any] | None) -> Question | None:
    """Read a question out of the runtime's event payload.

    The payload is the runtime's, not ours, so it is read defensively: a
    question without an id cannot be answered, and one without a question
    cannot be shown. Both are refused here rather than drawn as an empty
    button.
    """
    if not isinstance(payload, dict):
        return None
    identifier = str(payload.get("id") or "").strip()
    text = str(payload.get("question") or "").strip()
    if not identifier or not text:
        return None
    options = payload.get("options")
    return Question(
        id=identifier,
        kind=str(payload.get("kind") or "text"),
        question=text,
        options=tuple(str(option) for option in options) if isinstance(options, list) else (),
    )


def question_text(question: Question) -> str:
    """The message the owner reads.

    It says WHO is asking — the agent, not the bot — because the answer
    goes to the agent, and a question that arrives from "the bot" invites
    the owner to answer the wrong thing.
    """
    if question.kind == "confirm":
        return f"❓ {question.question}"
    return f"❓ {question.question}"


def question_keyboard(question: Question) -> list[list[tuple[str, str, str]]]:
    """The buttons under the question.

    A choice is one button per option, two to a row — a phone screen fits
    two short labels side by side, and a column of six buttons is a menu the
    owner has to scroll. A confirmation is two buttons. A free-form question
    gets ONE button, whose only job is to say "I am ready to write".
    """
    rows: list[list[tuple[str, str, str]]] = []
    if question.is_free_form:
        label = "✍️ Responder" if question.kind == "text" else "📝 Editar"
        return [[(label, VERB_TYPE, question.id)]]

    options = list(question.options)
    if question.kind == "confirm" and not options:
        options = ["Sim", "Não"]
    for start in range(0, len(options), 2):
        row = [
            # The argument carries the question AND the option's index: the
            # question id says which question, the index says which option.
            # The option's TEXT never travels in the button — it is the
            # runtime's, and the runtime is what resolves it.
            (option, VERB_PICK, f"{question.id}:{index}")
            for index, option in enumerate(options[start : start + 2], start=start)
        ]
        rows.append(row)
    return rows


def answer_buttons(verb: str, argument: str) -> tuple[str, str] | None:
    """Read a button of this channel back into (question id, what it means).

    Returns ``None`` for a button that is not ours — the caller answers it
    with "I do not know that button", the same way it answers a stranger.
    """
    if verb == VERB_PICK:
        question_id, _, index = argument.partition(":")
        if not question_id or not index.isdigit():
            return None
        return question_id, f"#{index}"
    if verb == VERB_TYPE:
        question_id, _, _ = argument.partition(":")
        if not question_id:
            return None
        return question_id, "#type"
    return None
