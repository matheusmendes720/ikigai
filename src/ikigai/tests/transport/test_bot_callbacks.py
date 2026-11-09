"""The dispatch of a button: the path the owner taps, and the one with no test.

Gate G6 of the chain (`specs/harness/CHAINED-ROUTINES.md` §11): **HITL
commits** — *Guardar* writes once; the same button twice writes once
(idempotency key); a stale revision is a 409.

The button path had no test. The token parser has one (`test_bot_router.py`)
and the draft flow has one (`test_bot_drafts.py`), but `_on_callback` — where
a token becomes an action — had none. An untested path is a path where a
broken button looks like a button that simply does not answer.

THE INVARIANT THIS FILE GUARDS: **every path answers the callback.**

An unanswered callback query spins on the owner's screen until Telegram's
timeout, and a spinner is the client telling the owner the bot is thinking
when it is not. The bot answers it even when it refuses the button, even
when it refuses the CHAT, and even when the write fails.
"""

from __future__ import annotations

from typing import Any

from src.bot.main import Bot
from src.bot.router import callback_data


class FakeHttp:
    """Telegram's HTTP surface: what was sent, and nothing else."""

    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []

    async def post(self, url: str, json: dict[str, Any]) -> Any:
        self.posts.append((url, json))
        return None

    async def get(self, url: str, params: dict[str, Any]) -> Any:
        raise AssertionError("the bot must not poll in this test")

    @property
    def answers(self) -> list[dict[str, Any]]:
        """The `answerCallbackQuery` calls, in order."""
        return [payload for url, payload in self.posts if "answerCallbackQuery" in url]


class FakeClient:
    """The transport: `upsert_artifact` and the drafts.

    The two failures the gate names are switchable, because both are real:
    a write that conflicts with what the store holds, and a draft that moved
    under the bot between the read and the close.
    """

    def __init__(self) -> None:
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.drafts: dict[str, dict[str, Any]] = {}
        self.writes: list[dict[str, Any]] = []
        self.conflict_on_write = False
        self.refuse_the_discard = False

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        if tool == "upsert_artifact":
            if self.conflict_on_write:
                raise RuntimeError("conflict: the artifact is taken — send expected_revision")
            artifact = arguments["artifact"]
            self.writes.append(arguments)
            self.artifacts[str(artifact["uid"])] = dict(artifact)
            return {"uid": artifact["uid"], "revision": 1, "outcome": "created"}
        raise AssertionError(f"unexpected tool {tool}")

    async def draft(self, op: str, **fields: Any) -> Any:
        if op == "get":
            found = self.drafts.get(fields.get("draft_id"))
            if found is None:
                raise RuntimeError("not_found: no draft for that id")
            return dict(found)
        if op == "discard":
            if self.refuse_the_discard:
                raise RuntimeError("conflict: the draft was changed by someone else")
            self.drafts.pop(fields.get("draft_id"), None)
            return {"draft_id": fields.get("draft_id"), "revision": 0, "outcome": "discarded"}
        raise AssertionError(f"unexpected draft op {op}")


class RecordingBot(Bot):
    """The real bot, with Telegram's send replaced by a recorder."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.outbox: list[str] = []
        self.keyboards: list[Any] = []
        self.http = FakeHttp()
        self._http = self.http

    async def _send(self, chat_id: str, text: str, buttons: Any = None) -> None:
        self.outbox.append(text)
        if buttons:
            self.keyboards.append(buttons)


def _bot(client: Any, allowed: set[str] | None = None) -> RecordingBot:
    return RecordingBot("token", client, allowed if allowed is not None else {"chat-1"}, "owner")


def _open_draft(client: FakeClient, body: str = "o parágrafo do rascunho") -> None:
    client.drafts["telegram-chat-1"] = {
        "draft_id": "telegram-chat-1",
        "kind": "nota",
        "title": "",
        "body": body,
        "revision": 1,
    }


async def _press(
    bot: RecordingBot,
    data: str,
    chat_id: str = "chat-1",
    message_id: str = "7",
    callback_id: str = "cb-1",
) -> None:
    """One button press, as Telegram delivers it."""
    await bot._on_callback(
        {
            "id": callback_id,
            "message": {"message_id": int(message_id), "chat": {"id": chat_id}},
            "data": data,
        }
    )


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------


async def test_a_button_that_is_not_ours_is_refused_and_answered() -> None:
    """A stranger's token gets an answer, and nothing else."""
    bot = _bot(FakeClient())

    await _press(bot, "isto-nao-e-um-botao")

    assert bot.outbox == [], "the bot answered a stranger in the chat"
    assert len(bot.http.answers) == 1
    assert "Não conheço esse botão." in bot.http.answers[0]["text"]


async def test_a_chat_outside_the_allowlist_hears_nothing() -> None:
    """Fail closed — but still stop the spinner.

    The chat learns nothing about what the button would have done. The owner
    of that chat learns only that the button was answered, which is the same
    thing every other refused button gets.
    """
    client = FakeClient()
    _open_draft(client)
    bot = _bot(client, allowed={"outro-chat"})

    await _press(bot, callback_data("draft.guardar"), chat_id="chat-1")

    assert bot.outbox == [], "an unlisted chat was answered"
    assert not client.writes, "an unlisted chat wrote to the store"
    assert len(bot.http.answers) == 1
    assert "text" not in bot.http.answers[0], "the refusal leaked what the button does"


# ---------------------------------------------------------------------------
# The commit — gate G6
# ---------------------------------------------------------------------------


async def test_the_guardar_button_saves_the_draft_once() -> None:
    """The button writes the artifact, closes the draft, and says the uid."""
    client = FakeClient()
    _open_draft(client)
    bot = _bot(client)

    await _press(bot, callback_data("draft.guardar"))

    assert len(client.writes) == 1, "the button did not write exactly once"
    written = client.writes[0]["artifact"]
    assert written["body"] == "o parágrafo do rascunho"
    assert written["kind"] == "nota"
    assert client.drafts == {}, "the draft was not closed"
    assert written["uid"] in bot.outbox[-1]
    assert "Guardado" in bot.outbox[-1]


async def test_the_same_button_twice_carries_the_same_key() -> None:
    """The key is a function of the message, so a retap cannot write twice.

    The scenario is the one that really happens: the write LANDS, and the
    closing of the draft is refused because the draft moved under the bot.
    The owner taps again, because the bot said it had failed. The second
    write must be the SAME write — same uid, same idempotency key — so the
    store says "unchanged" instead of creating a second artifact.
    """
    client = FakeClient()
    _open_draft(client)
    client.refuse_the_discard = True
    bot = _bot(client)

    await _press(bot, callback_data("draft.guardar"))
    await _press(bot, callback_data("draft.guardar"))

    assert len(client.writes) == 2, "the second press did not reach the write path"
    first, second = client.writes
    assert first["artifact"]["uid"] == second["artifact"]["uid"]
    assert first["idempotency_key"] == second["idempotency_key"], (
        "the second press carries a different key — the store cannot tell it is the same write"
    )
    assert len(client.artifacts) == 1, "the store holds two artifacts for one button"


async def test_a_write_that_conflicts_is_heard_and_nothing_is_saved() -> None:
    """A 409 is an answer, not a crash — and not a silent overwrite."""
    client = FakeClient()
    _open_draft(client)
    client.conflict_on_write = True
    bot = _bot(client)

    await _press(bot, callback_data("draft.guardar"))

    assert not client.artifacts, "the conflicting write landed anyway"
    assert bot.outbox, "the owner was told nothing"
    assert len(bot.http.answers) == 1, "the callback was left spinning"


async def test_a_draft_that_moved_under_the_bot_does_not_hide_the_write() -> None:
    """The write landed. Saying it failed would be a lie about the store.

    The close of the draft is guarded by its revision, and the guard is right:
    discarding a draft another session just edited would throw that edit
    away. But the artifact is already in the store, so the answer has to say
    that — and to say that the draft is still open, because it is.
    """
    client = FakeClient()
    _open_draft(client)
    client.refuse_the_discard = True
    bot = _bot(client)

    await _press(bot, callback_data("draft.guardar"))

    assert len(client.artifacts) == 1, "the write did not land"
    assert "Guardado" in bot.outbox[-1], f"the bot answered: {bot.outbox[-1]}"
    assert client.drafts, "the draft was closed even though the close was refused"


# ---------------------------------------------------------------------------
# The other verbs — the dispatch, not the handlers
# ---------------------------------------------------------------------------


async def test_the_run_button_starts_a_routine() -> None:
    """The button reaches the routine path — here, the refusal of a bot with
    no agent behind it, which is the only answer this bot can give."""
    bot = _bot(FakeClient())

    await _press(bot, callback_data("run", "daily-note"))

    assert bot.outbox, "the routine button said nothing"
    assert "agente não está configurado" in bot.outbox[-1]
    assert len(bot.http.answers) == 1


async def test_a_button_that_is_not_a_verb_of_this_bot_is_refused() -> None:
    """`v1:` with a verb nobody implements is still OUR token — and still a
    refusal, not an exception."""
    bot = _bot(FakeClient())

    await _press(bot, callback_data("inventado"))

    assert "Não conheço esse botão." in bot.outbox[-1]
    assert len(bot.http.answers) == 1


async def test_every_path_answers_the_callback_exactly_once() -> None:
    """The invariant, over every path the dispatch can take.

    One spinner that never stops is worse than a refusal: the owner cannot
    tell a slow bot from a dead one, and taps again.
    """
    client = FakeClient()
    _open_draft(client)
    bot = _bot(client)

    await _press(bot, "isto-nao-e-um-botao", callback_id="cb-1")
    await _press(bot, callback_data("draft.descartar"), callback_id="cb-2")
    await _press(bot, callback_data("inventado"), callback_id="cb-3")
    await _press(bot, callback_data("run", "daily-note"), callback_id="cb-4")

    answered = [payload["callback_query_id"] for payload in bot.http.answers]
    assert answered == ["cb-1", "cb-2", "cb-3", "cb-4"]
