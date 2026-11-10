"""A recusa não é uma falha — e o bot tem de dizer as duas coisas diferente.

O harness recusa uma segunda rotina numa sessão ocupada com **409**: o
pedido não correu, porque a sessão já tinha um turno em curso. Medido no box
(2026-11-10, 11:44:41Z–11:45:27Z) e decidido pelo dono no mesmo dia:
recusar, mas **declarado** — o harness recusa antes de chamar o `pi`, com a
frase do produto.

Duas coisas têm de ser verdade ao mesmo tempo, e é a segunda que costuma
escapar:

* o dono recebe **"a rotina foi recusada"** — não "falhou", que é uma
  mentira sobre uma rotina que nunca começou;
* o **status** chega ao bot, porque sem ele "recusada" e "falhou" são a
  mesma frase.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.bot.harness_client import HarnessClient, HarnessError
from src.bot.main import Bot

BUSY_BODY = {
    "ok": False,
    "error": "the session is busy: the routine did not start",
    "detail": 'another routine is running in this session; wait for it to finish and send "daily-note" again',
}


class _Store:
    async def call(self, tool: str, arguments: Any) -> Any:
        return {}


class _BusyHarness:
    """A harness that refuses the way the real one does: 409."""

    def __init__(self) -> None:
        self.calls = 0

    async def run_routine(
        self, routine: str, *, session_id: str, chat_id: str, message: str, **kwargs: Any
    ) -> dict[str, Any]:
        self.calls += 1
        raise HarnessError(
            f"{BUSY_BODY['error']} ({BUSY_BODY['detail']})",
            status=409,
        )


class _QuietBot(Bot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sent: list[tuple[str, str]] = []

    async def _send(
        self,
        chat_id: str,
        text: str,
        buttons: Any | None = None,
        web_app: tuple[str, str] | None = None,
    ) -> None:
        self.sent.append((chat_id, text))


def _bot(harness: Any) -> _QuietBot:
    return _QuietBot("token", _Store(), {"42"}, "owner", harness=harness)


async def test_a_refused_routine_is_not_told_it_failed() -> None:
    """A recusa tem uma frase própria — "falhou" seria mentira."""
    bot = _bot(_BusyHarness())

    await bot._run_routine("42", "daily-note", "", None)

    assert bot.sent, "the owner was told nothing at all"
    text = bot.sent[-1][1]
    assert "recusada" in text
    assert "falhou" not in text


async def test_the_refusal_tells_the_owner_what_to_do() -> None:
    """Uma recusa que não diz o que fazer é uma recusa que gasta uma ida e volta."""
    bot = _bot(_BusyHarness())

    await bot._run_routine("42", "daily-note", "", None)

    text = bot.sent[-1][1].lower()
    assert "sessão" in text or "sessao" in text
    assert "pede outra vez" in text or "pede de novo" in text


async def test_the_refusal_names_the_routine() -> None:
    bot = _bot(_BusyHarness())

    await bot._run_routine("42", "monthly-review", "", None)

    assert "monthly-review" in bot.sent[-1][1]


def test_the_status_travels_with_the_refusal() -> None:
    """Sem o status, o bot não distingue "recusada" de "falhou"."""
    client = HarnessClient("http://harness.invalid:8002")

    class _Response:
        status_code = 409

        @staticmethod
        def json() -> dict[str, Any]:
            return BUSY_BODY

    with pytest.raises(HarnessError) as caught:
        client._body(_Response(), "/v1/routine")  # type: ignore[arg-type]

    assert caught.value.status == 409
    assert "session is busy" in str(caught.value)


def test_a_failure_without_a_status_is_not_a_refusal() -> None:
    """O 502 de uma rotina que morreu continua a ser uma falha."""
    error = HarnessError("the routine failed: Timeout collecting events", status=502)

    assert error.status == 502
