"""The intent router: a sentence to a routine, without a model.

The bot has two doors and, until now, only one of them was open. A slash
command reaches a routine by name; anything else is prose, and prose becomes
a draft. So "fecha o dia" answered "Não há rascunho aberto", which is a true
sentence about a draft and a useless sentence about the owner's intent.

This module is the missing door — and it is deliberately the DUMB half:

- **It cannot invent a routine.** The harness refuses an id that is not in
  the published projection (`loadRoutines()` in `deploy/harness/server.mjs`),
  so a confident guess becomes a 400 in the owner's face.
- **It says nothing when it is not sure.** Two routines matching the same
  sentence is an abstention, not a coin flip. The caller asks instead.
- **It reads the caller's own table.** The ids come from the bot's `ROUTINES`,
  so a routine removed from the client cannot keep being routed by a list
  this module keeps in a second place.

A model MAY sit behind this table later. When it does, it answers with an id
from the same table — the table is the vocabulary, the model is only a second
way of reaching it.

The relative day is the one slot that matters now: "fecha o dia de ontem" and
"fecha o dia" are the same routine and different work.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field

__all__ = ["Route", "callback_data", "parse_callback", "route"]

#: The version of the inline-button token. It is in the payload because a
#: button outlives the bot that sent it: a message from last week is still
#: tappable after a deploy, and a payload without a version is a payload the
#: new process has to guess the shape of.
_CALLBACK_VERSION = "v1"

#: What a sentence says, longest phrase first.
#:
#: The phrases are matched as SUBSTRINGS of the folded sentence, so a short
#: marker is a trap: "semana" alone would claim "a semana foi longa", which is
#: a thought for the weekly review to read, not a command to run it. Every
#: entry below carries a verb or a possessive for that reason.
_PHRASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "daily-note",
        (
            "fecha o dia",
            "fechar o dia",
            "fecha o meu dia",
            "registar o dia",
            "registra o dia",
            "regista o dia",
            "nota do dia",
            "close the day",
            "daily note",
            "daily review",
        ),
    ),
    (
        "weekly-review",
        (
            "revisao da semana",
            "revisao semanal",
            "fecha a semana",
            "fechar a semana",
            "fecha a minha semana",
            "consolida a semana",
            "weekly review",
            "close the week",
        ),
    ),
    (
        "monthly-review",
        (
            "revisao do mes",
            "revisao mensal",
            "fecha o mes",
            "fechar o mes",
            "fecha o meu mes",
            "consolida o mes",
            "monthly review",
            "close the month",
        ),
    ),
    (
        "quarterly-plan",
        (
            "planeia o trimestre",
            "planeja o trimestre",
            "plano do trimestre",
            "planeamento do trimestre",
            "planejamento do trimestre",
            "fecha o trimestre",
            "quarterly plan",
            "plan the quarter",
        ),
    ),
)

#: The relative markers, folded. The VALUE is what the routine is told, in the
#: owner's words, because that string is the prompt's payload too.
_RELATIVE: tuple[tuple[str, str], ...] = (
    ("semana passada", "semana passada"),
    ("last week", "semana passada"),
    ("mes passado", "mes passado"),
    ("last month", "mes passado"),
    ("trimestre passado", "trimestre passado"),
    ("last quarter", "trimestre passado"),
    ("ontem", "ontem"),
    ("yesterday", "ontem"),
    ("anteontem", "anteontem"),
)


@dataclass(frozen=True)
class Route:
    """One sentence, read as one routine.

    `why` is the phrase that matched. It is not decoration: when the owner
    says "eu não pedi isso", the bot can say what it read, and the phrase is
    the thing to correct.
    """

    routine: str
    slots: dict[str, str] = field(default_factory=dict)
    why: str = ""


def _fold(text: str) -> str:
    """Lowercase, accent-folded, single-spaced.

    Folded rather than lowercased because the owner types "revisão" and
    "revisao" and means the same thing — and NFKD + ascii is the cheapest
    thing that makes those one string.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    folded = decomposed.encode("ascii", "ignore").decode("ascii")
    return " ".join(folded.lower().split())


def route(text: str, routines: Mapping[str, str]) -> Route | None:
    """Read `text` as one routine, or refuse.

    `routines` is the caller's table (id -> description). An id that is not in
    it is not routable, so the table stays the single source of what exists.

    Returns `None` when the sentence names no routine, and **also** when it
    names more than one: "fecha a semana e o mês" is a sentence with two jobs,
    and running one of them silently would be the bot picking a job it was not
    asked to pick.
    """
    folded = _fold(text)
    if not folded:
        return None

    hits: list[tuple[str, str]] = []
    for routine, phrases in _PHRASES:
        if routine not in routines:
            continue
        for phrase in phrases:
            if phrase in folded:
                hits.append((routine, phrase))
                break

    named = {routine for routine, _ in hits}
    if len(named) != 1:
        return None

    routine, phrase = hits[0]
    slots: dict[str, str] = {}
    for marker, value in _RELATIVE:
        if marker in folded:
            slots["when"] = value
            break
    return Route(routine=routine, slots=slots, why=phrase)


def callback_data(verb: str, arg: str = "") -> str:
    """The payload of one inline button.

    Telegram caps `callback_data` at 64 bytes and answers a longer one with a
    silent failure at send time, so the cap is applied here — at the place
    that builds it, not at the place that sends it.
    """
    token = f"{_CALLBACK_VERSION}:{verb}"
    if arg:
        token = f"{token}:{arg}"
    return token[:64]


def parse_callback(data: str) -> tuple[str, str] | None:
    """The verb and the argument of a button, or `None` for a stranger.

    A button from an older deploy, or one this bot did not send, is answered
    with "I do not know that button" rather than an exception in the poll
    loop — the loop is one `for` away from dying, and a dead poll loop is a
    silent bot.
    """
    parts = (data or "").split(":")
    if len(parts) < 2 or parts[0] != _CALLBACK_VERSION:
        return None
    verb = parts[1].strip()
    if not verb:
        return None
    return verb, ":".join(parts[2:])
