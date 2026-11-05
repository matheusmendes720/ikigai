"""The bot, as a client of the transport (SPEC-02 F2.2-F2.4).

The bot is the first non-desktop client, and its acceptance is that a note
written from a chat lands in the store, that a search finds it, and that a uid
reads it back with its edges. None of that needs Telegram: the bot speaks MCP
to the api, so the client can be driven over the api's own protocol.

The doubles are built FROM THE CONTRACT — `SearchResult(...).model_dump()` —
so they cannot drift from what the transport publishes. That is the point of
this file: the bot's renderer looked for "items" and "results", names the
contract never had, and answered "Nada encontrado" for a search that had
results. The renderer was never exercised, so nothing noticed — and the
defect was in the one command whose acceptance criterion is "returns what was
written".
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from src.bot.main import Bot, McpClient
from src.contracts.dom import (
    Artifact,
    ArtifactBundle,
    ArtifactKind,
    Relation,
    RelationType,
    SearchResult,
    make_uid,
)

NOW = datetime.now(UTC)


def _artifact(title: str = "Nota do dia") -> Artifact:
    return Artifact(
        uid=make_uid(ArtifactKind.NOTA, "nota-do-dia", "a1b2c3d4", "0123456789abcdef"),
        kind=ArtifactKind.NOTA,
        title=title,
        body="o corpo da nota",
        revision=1,
        created_at=NOW,
        updated_at=NOW,
    )


class _ContractClient(McpClient):
    """A client double that answers with the contract's own models.

    It subclasses the real client so the bot takes it without a cast, and it
    answers with `model_dump()` — the same shape the transport publishes — so
    a change in the contract's field names shows up here as a failure rather
    than as a silent mismatch in the renderer.
    """

    def __init__(self) -> None:
        super().__init__("http://unused.invalid/mcp")
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        if tool == "search_artifacts":
            return SearchResult(artifacts=(_artifact(),)).model_dump()
        if tool == "get_artifact":
            return ArtifactBundle(
                artifact=_artifact(),
                relations=(
                    Relation(
                        src_uid=_artifact().uid,
                        dst_uid=make_uid(
                            ArtifactKind.KPI, "meta", "bbbbbbbb", "0123456789abcdef"
                        ),
                        rel=RelationType.EVIDENCES,
                    ),
                ),
            ).model_dump()
        return {"uid": _artifact().uid, "revision": 1, "outcome": "created"}


def _bot(client: McpClient, allowed: set[str] | None = None) -> Bot:
    return Bot("token", client, allowed if allowed is not None else {"42"}, "owner")


async def test_a_note_from_a_chat_lands_in_the_store() -> None:
    """F2.2: the write carries what the transport accepts."""
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch("/nota", "a nota de hoje", "42")

    assert len(client.calls) == 1
    tool, arguments = client.calls[0]
    assert tool == "upsert_artifact"
    assert arguments["artifact"]["kind"] == "nota"
    assert arguments["artifact"]["body"] == "a nota de hoje"
    assert arguments["expected_revision"] is None
    assert arguments["idempotency_key"]
    assert arguments["client_id"] == "owner"
    assert arguments["artifact"]["uid"] in answer


async def test_a_search_returns_what_the_store_holds() -> None:
    """F2.3: the search finds the artifact and the answer SAYS so.

    The renderer looked for "items" and "results" — names the contract has
    never had — so it answered "Nada encontrado" for a search that had
    results. The failure is silent and plausible: the bot looked like it had
    searched and found nothing.
    """
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch("/busca", "nota", "43")

    assert client.calls[0][0] == "search_artifacts"
    assert "Nada encontrado" not in answer, f"the search answered: {answer}"
    assert "Nota do dia" in answer, f"the search answered: {answer}"


async def test_a_search_with_no_results_says_so() -> None:
    class _Empty(_ContractClient):
        async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
            self.calls.append((tool, arguments))
            return SearchResult(artifacts=()).model_dump()

    bot = _bot(_Empty())

    answer = await bot._dispatch("/busca", "nada disso", "44")

    assert answer == "Nada encontrado."


async def test_a_uid_reads_back_with_its_edges() -> None:
    """F2.4: the artifact and its edges."""
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch("/uid", str(_artifact().uid), "45")

    assert client.calls[0][0] == "get_artifact"
    assert "Nota do dia" in answer
    assert "evidences" in answer


async def test_a_command_without_its_argument_asks_for_it() -> None:
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch("/nota", "", "46")

    assert "Diz o que é" in answer
    assert not client.calls


async def test_an_unknown_command_says_so() -> None:
    bot = _bot(_ContractClient())

    answer = await bot._dispatch("/nada", "x", "47")

    assert "Não conheço esse comando" in answer


async def test_the_help_lists_the_commands() -> None:
    bot = _bot(_ContractClient())

    answer = await bot._dispatch("/help", "", "48")

    for command in ("/nota", "/sonho", "/busca", "/uid"):
        assert command in answer


async def test_an_unlisted_chat_gets_no_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract C-4: the bot fails closed, and stays silent about it.

    An unlisted chat gets no reply and no trace of what the bot can do.
    """
    sent: list[dict[str, Any]] = []

    class _Http:
        async def post(self, url: str, json: dict[str, Any]) -> None:
            sent.append(json)

        async def get(self, url: str, params: dict[str, Any]) -> Any:
            raise AssertionError("the bot must not poll in this test")

    bot = _bot(_ContractClient(), allowed={"42"})
    monkeypatch.setattr(bot, "_http", _Http())

    await bot._handle({"chat": {"id": 999}, "text": "/nota algo", "message_id": 50})

    assert not sent, "an unlisted chat was answered"


def test_the_bot_refuses_to_start_without_an_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract C-4: no allowlist, no bot."""
    from src.bot.main import main

    monkeypatch.setenv("IKIGAI_BOT_TOKEN", "token")
    monkeypatch.setenv("IKIGAI_BOT_ALLOWED_CHAT_IDS", "")

    with pytest.raises(SystemExit):
        main()


def test_the_bot_refuses_to_start_without_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.bot.main import main

    monkeypatch.delenv("IKIGAI_BOT_TOKEN", raising=False)
    monkeypatch.setenv("IKIGAI_BOT_ALLOWED_CHAT_IDS", "42")

    with pytest.raises(SystemExit):
        main()
