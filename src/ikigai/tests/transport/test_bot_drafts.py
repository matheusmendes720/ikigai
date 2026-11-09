"""The bot's draft flow, in a conversation, in the suite.

The end-to-end run (real bot, real server, live store) is what found the bug
this flow used to have — a de-duplication key that made two saves of the same
text inside one second the same save, so `/rascunho` "reopened" a draft it had
not touched. That run needs a container and a store, so it is not in here; what
is in here is the conversation's SHAPE, which is what a regression would break.

The fake stands in for the transport and answers the way the server does: a
draft map, a conflict on a stale revision, and `not_found` for a draft that
does not exist. The bot is the real one.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.bot.main import Bot, _catalogue


class FakeClient:
    """The transport: the six tools, and the draft frames."""

    def __init__(self) -> None:
        self.drafts: dict[str, dict[str, Any]] = {}
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.conflict_on_first_save = False
        self._saved = 0

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        if tool == "upsert_artifact":
            artifact = arguments["artifact"]
            self.artifacts[str(artifact["uid"])] = dict(artifact)
            return {"uid": artifact["uid"], "revision": 1, "outcome": "created"}
        if tool == "get_artifact":
            uid = arguments["uid"]
            return {"artifact": self.artifacts.get(uid, {}), "relations": []}
        if tool == "search_artifacts":
            return {"artifacts": []}
        raise AssertionError(f"unexpected tool {tool}")

    async def draft(self, op: str, **fields: Any) -> Any:
        self.calls.append((f"draft.{op}", fields))
        draft_id = fields.get("draft_id")
        if op == "get":
            found = self.drafts.get(draft_id)
            if found is None:
                raise RuntimeError("not_found: no draft for that id")
            return dict(found)
        if op == "list":
            return {"drafts": [dict(value) for value in self.drafts.values()]}
        if op == "save":
            self._saved += 1
            if self.conflict_on_first_save and self._saved == 1:
                raise RuntimeError("conflict: the draft is taken — send expected_revision")
            current = self.drafts.get(draft_id)
            expected = fields.get("expected_revision")
            if current is None and expected is not None:
                raise RuntimeError("conflict: no draft to update")
            if current is not None and expected is None:
                raise RuntimeError("conflict: the draft is taken")
            if current is not None and expected != current["revision"]:
                raise RuntimeError("conflict: draft was changed by someone else")
            revision = 1 if current is None else int(current["revision"]) + 1
            self.drafts[draft_id] = {
                "draft_id": draft_id,
                "kind": fields.get("kind"),
                "title": fields.get("title"),
                "body": fields.get("body") or "",
                "revision": revision,
            }
            return {"draft_id": draft_id, "revision": revision, "outcome": "created"}
        if op == "discard":
            current = self.drafts.get(draft_id)
            if current is None:
                raise RuntimeError("not_found: no draft for that id")
            if fields.get("expected_revision") not in (None, current["revision"]):
                raise RuntimeError("conflict: stale")
            del self.drafts[draft_id]
            return {"draft_id": draft_id, "revision": 0, "outcome": "discarded"}
        raise AssertionError(f"unexpected draft op {op}")


class MuteBot(Bot):
    """The real bot, with Telegram's send replaced by a recorder."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.outbox: list[str] = []
        #: The buttons offered with a message, when there were any. A decision
        #: is part of the answer, and a recorder that drops it tests less than
        #: the bot does.
        self.keyboards: list[Any] = []

    async def _send(self, chat_id: str, text: str, buttons: Any = None) -> None:
        self.outbox.append(text)
        if buttons:
            self.keyboards.append(buttons)

    async def say(self, text: str, message_id: str = "1") -> str:
        await self._handle({"chat": {"id": "chat-1"}, "text": text, "message_id": message_id})
        return self.outbox[-1]


def _bot(client: Any) -> MuteBot:
    return MuteBot("token", client, {"chat-1"}, "owner")


async def test_a_rascunho_opens_and_a_paragraph_grows_it() -> None:
    client = FakeClient()
    bot = _bot(client)

    assert "aberto" in await bot.say("/rascunho nota")
    assert "1 linha" in await bot.say("primeira linha do rascunho")
    answer = await bot.say("segunda linha")

    assert "2 linha" in answer
    assert client.drafts["telegram-chat-1"]["body"] == "primeira linha do rascunho\nsegunda linha"


async def test_the_first_word_of_a_paragraph_is_not_eaten() -> None:
    """The command path splits on the first space; a paragraph must not."""
    client = FakeClient()
    bot = _bot(client)
    await bot.say("/rascunho nota")

    await bot.say("primeira linha")

    assert client.drafts["telegram-chat-1"]["body"] == "primeira linha"


async def test_a_rascunho_with_no_argument_shows_what_is_there() -> None:
    client = FakeClient()
    bot = _bot(client)
    await bot.say("/rascunho nota")
    await bot.say("o texto")

    answer = await bot.say("/rascunho")

    assert "o texto" in answer and "nota" in answer


async def test_a_new_bot_finds_the_draft_in_the_store() -> None:
    """The restart is the whole reason a draft is not a dictionary."""
    client = FakeClient()
    await _bot(client).say("/rascunho nota")
    await _bot(client).say("o que ficou a meio")

    fresh = _bot(client)
    answer = await fresh.say("/rascunhos")

    assert "Rascunhos abertos" in answer
    assert "o que ficou a meio" in answer


async def test_resuming_an_open_draft_is_not_a_failure() -> None:
    """After a restart the bot has no revision, so the save comes back conflicted.

    A conflict is the CORRECT answer — it means "there is already a draft
    here" — and the bot rereads and resumes instead of reporting an error.
    """
    client = FakeClient()
    first = _bot(client)
    await first.say("/rascunho nota")
    await first.say("o parágrafo")

    fresh = _bot(client)
    answer = await fresh.say("/rascunho nota")

    assert "retomei-o" in answer
    assert client.drafts["telegram-chat-1"]["body"] == "o parágrafo", "resuming wiped the prose"


async def test_guardar_commits_through_the_artifact_tool_and_discards() -> None:
    """The draft never commits itself: it is state, and the write has its own envelope."""
    client = FakeClient()
    bot = _bot(client)
    await bot.say("/rascunho nota")
    await bot.say("primeira linha")
    await bot.say("segunda linha")

    answer = await bot.say("/guardar")

    assert "Guardado (nota)" in answer
    tools = [name for name, _ in client.calls]
    assert "upsert_artifact" in tools, "the commit did not go through the write path"
    uid = answer.splitlines()[-1]
    assert client.artifacts[uid]["body"] == "primeira linha\nsegunda linha"
    assert client.drafts == {}, "the committed draft was not discarded"


async def test_the_kinds_rule_still_applies_to_a_committed_draft() -> None:
    """A DESC still needs its rationale — the draft does not bypass the model."""
    client = FakeClient()
    bot = _bot(client)
    await bot.say("/rascunho desc")
    await bot.say("a decisão sem o porquê")

    answer = await bot.say("/guardar")

    assert "porquê" in answer or "racional" in answer
    assert "upsert_artifact" not in [name for name, _ in client.calls]


async def test_a_paragraph_with_no_draft_open_says_so() -> None:
    client = FakeClient()

    answer = await _bot(client).say("texto solto")

    assert "Não há rascunho aberto" in answer


async def test_descartar_throws_it_away() -> None:
    client = FakeClient()
    bot = _bot(client)
    await bot.say("/rascunho nota")
    await bot.say("para deitar fora")

    assert "Descartado" in await bot.say("/descartar")
    assert client.drafts == {}
    assert "Não há rascunho aberto" in await bot.say("outro texto")


async def test_a_sentence_that_names_a_routine_reaches_the_agent() -> None:
    """Without a slash, a routine is still reachable.

    The router is deterministic and the bot has no harness in this test, so
    the proof that the sentence was ROUTED is the answer that only the
    routine path can produce — "o agente não está configurado". Before the
    router, this sentence answered "não há rascunho aberto".
    """
    client = FakeClient()

    answer = await _bot(client).say("fecha o dia")

    assert "agente não está configurado" in answer


async def test_the_draft_confirmation_offers_the_decision() -> None:
    """The chat is a UI: agreeing with what you just read is a button, not a
    command you have to remember."""
    bot = _bot(FakeClient())

    await bot.say("/rascunho nota")

    assert bot.keyboards, "the confirmation carried no buttons"
    labels = [label for row in bot.keyboards[0] for label, _, _ in row]
    assert labels == ["Guardar", "Descartar"]


async def test_a_bot_on_the_mcp_transport_admits_it_has_no_drafts() -> None:
    """A capability that is not there must say so, not fail with a stack trace."""

    class McpOnly:
        async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
            return {}

    answer = await _bot(McpOnly()).say("/rascunho nota")

    assert "Sem rascunhos neste transporte" in answer


async def test_the_catalogue_lists_the_draft_commands() -> None:
    catalogue = _catalogue()

    for command in ("/rascunho", "/guardar", "/descartar", "/rascunhos"):
        assert command in catalogue, f"{command} is not in the help"


@pytest.mark.parametrize("kind", ["nota", "sonho", "plano", "onda", "fase", "revisao", "desc", "okr"])
async def test_every_writable_kind_can_be_drafted(kind: str) -> None:
    """A kind the bot can write is a kind it can compose first."""
    client = FakeClient()

    answer = await _bot(client).say(f"/rascunho {kind}")

    assert "aberto" in answer
