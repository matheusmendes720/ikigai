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

from src.bot.main import HEAD_FIELDS, WRITABLE, Bot, McpClient
from src.contracts.dom import (
    Artifact,
    ArtifactBundle,
    ArtifactKind,
    Relation,
    RelationType,
    SearchResult,
    make_uid,
)
from src.contracts.dom_kinds import KIND_MODELS

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
                        dst_uid=make_uid(ArtifactKind.KPI, "meta", "bbbbbbbb", "0123456789abcdef"),
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


# ---------------------------------------------------------------------------
# The cadence commands
#
# The pi harness runs the cadences, but the owner is the one holding the phone
# when the decision is taken. So the client writes the cadence kinds too, in
# the kinds the skills write — and the contract has the last word on what
# those payloads carry.
# ---------------------------------------------------------------------------

#: One case per command the owner may write: the message, and the kind the
#: command MUST write.
#:
#: The kind is written out here and not read from the bot. A test that read
#: the expectation from the thing it is testing moves the expectation with the
#: defect — a mapping pointing `/revisao` at the wrong kind passed every
#: assertion, because the assertion had moved with it.
#:
#: The two structured kinds need two lines: the head, and what the kind also
#: requires.
_CASES: dict[str, tuple[str, ArtifactKind]] = {
    "/nota": ("a nota de hoje", ArtifactKind.NOTA),
    "/sonho": ("o sonho de sempre", ArtifactKind.SONHO),
    "/revisao": ("a revisão da semana", ArtifactKind.REVISAO),
    "/plano": ("o plano do trimestre", ArtifactKind.PLANO),
    "/onda": ("a onda 3", ArtifactKind.ONDA),
    "/fase": ("a fase 2", ArtifactKind.FASE),
    "/desc": ("mudar o plano\nporque o mercado mudou", ArtifactKind.DESC),
    "/okr": ("reduzir o churn\npara 2%", ArtifactKind.OKR),
}


@pytest.mark.parametrize("command", sorted(_CASES))
async def test_every_writable_command_writes_its_kind(command: str) -> None:
    """Each command writes the kind it claims, and a payload the contract takes.

    The transport takes the TYPED model for the kind, so a payload the model
    would refuse is a payload the api refuses — after the owner typed it.
    The validation here is the same model the transport validates against.
    """
    message, kind = _CASES[command]
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch(command, message, "60")

    assert len(client.calls) == 1
    tool, arguments = client.calls[0]
    assert tool == "upsert_artifact"
    assert arguments["artifact"]["kind"] == kind.value
    assert arguments["artifact"]["body"] == message
    assert arguments["expected_revision"] is None
    assert arguments["idempotency_key"]
    assert arguments["client_id"] == "owner"
    assert arguments["artifact"]["uid"] in answer

    # The payload satisfies the kind's own model — and the model forbids
    # extra fields, so a head field that leaked into another kind fails here.
    KIND_MODELS[kind].model_validate(arguments["artifact"])


async def test_a_decision_takes_its_rationale_from_the_second_line() -> None:
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch("/desc", "mudar o plano\nporque o mercado mudou", "61")

    artifact = client.calls[0][1]["artifact"]
    assert artifact["kind"] == "desc"
    assert artifact["decision"] == "mudar o plano"
    assert artifact["rationale"] == "porque o mercado mudou"
    assert artifact["title"] == "mudar o plano"
    assert artifact["uid"] in answer


async def test_an_okr_takes_its_key_result_from_the_second_line() -> None:
    client = _ContractClient()
    bot = _bot(client)

    await bot._dispatch("/okr", "reduzir o churn\npara 2%", "62")

    artifact = client.calls[0][1]["artifact"]
    assert artifact["kind"] == "okr"
    assert artifact["objective"] == "reduzir o churn"
    assert artifact["key_result"] == "para 2%"


async def test_a_decision_without_its_rationale_is_asked_for() -> None:
    """A decision without a rationale is not a decision — so nothing is written.

    The monthly-review skill states it, and the bot holds the line at the
    boundary: it asks for the second line instead of writing the decision
    without the reason behind it.
    """
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch("/desc", "mudar o plano", "63")

    assert "porquê" in answer, f"the bot answered: {answer}"
    assert not client.calls, "the bot wrote a decision without a rationale"


async def test_an_okr_without_its_key_result_is_asked_for() -> None:
    client = _ContractClient()
    bot = _bot(client)

    answer = await bot._dispatch("/okr", "reduzir o churn", "64")

    assert "key result" in answer, f"the bot answered: {answer}"
    assert not client.calls, "the bot wrote an OKR without a key result"


async def test_the_help_lists_every_command_that_can_be_written() -> None:
    """The catalogue is built FROM the writable set, so it cannot drift.

    A command that can be written and is not listed would be a command the
    owner does not know exists; a command that is listed and cannot be
    written would be a lie. Both fail here.
    """
    bot = _bot(_ContractClient())

    answer = await bot._dispatch("/help", "", "65")

    for command in _CASES:
        assert command in answer, f"/help does not list {command}"


def test_the_catalogue_covers_exactly_the_writable_commands() -> None:
    """The catalogue and the writable set are the same set.

    A description without a command would describe something the owner cannot
    do; a command without a description would be a command the catalogue
    cannot render. The two are held together here.
    """
    from src.bot.main import _COMMANDS

    assert set(_COMMANDS) == set(WRITABLE)


async def test_a_payload_the_contract_would_refuse_never_leaves_the_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bot validates against the kind's own model BEFORE it writes.

    The api would refuse the payload anyway — but the refusal would arrive as
    a transport error, after the write was attempted. Validating here means
    the write never happens, and the failure names the field that is missing.
    """
    from pydantic import ValidationError

    import src.bot.main as bot_main
    from src.contracts.dom_kinds import DecisionArtifact

    class _Stricter(DecisionArtifact):
        outcome_is_required: str

    models = dict(bot_main.KIND_MODELS)
    models[ArtifactKind.DESC] = _Stricter
    monkeypatch.setattr(bot_main, "KIND_MODELS", models)

    client = _ContractClient()
    bot = _bot(client)

    with pytest.raises(ValidationError):
        await bot._dispatch("/desc", "mudar o plano\nporque o mercado mudou", "66")

    assert not client.calls, "the bot wrote a payload the contract would refuse"


async def test_the_writable_set_is_the_cadence_kinds() -> None:
    """The commands the bot may write are pinned.

    Opening a command is a decision about what a message from the phone can
    do to the canonical store. It is not a refactor, so the set is written
    out here and a change to it has to be a change to this test.
    """
    assert WRITABLE == {
        "/nota": ArtifactKind.NOTA,
        "/sonho": ArtifactKind.SONHO,
        "/revisao": ArtifactKind.REVISAO,
        "/plano": ArtifactKind.PLANO,
        "/onda": ArtifactKind.ONDA,
        "/fase": ArtifactKind.FASE,
        "/desc": ArtifactKind.DESC,
        "/okr": ArtifactKind.OKR,
    }


def test_every_writable_kind_gets_the_fields_its_contract_requires() -> None:
    """The bot fills every field the kind's model requires.

    The model is the contract, and the bot writes against it. If a kind grows
    a required field, this fails — otherwise the bot would keep sending a
    payload the api refuses, and the refusal would arrive as a transport error
    instead of as a missing field.
    """
    spine = set(Artifact.model_fields)
    for kind in WRITABLE.values():
        model = KIND_MODELS[kind]
        required = {
            name
            for name, field in model.model_fields.items()
            if field.is_required() and name not in spine
        }
        provided = set(HEAD_FIELDS.get(kind, ()))
        assert required <= provided, (
            f"{kind.value} requires {sorted(required - provided)} and the bot does not send them"
        )


def test_the_head_fields_are_fields_of_their_model() -> None:
    """The names the bot fills are the names the model has.

    A field renamed in the contract must not leave the bot filling a name
    that no longer exists: the model forbids extra fields, so the payload
    would be refused.
    """
    for kind, fields in HEAD_FIELDS.items():
        model_fields = KIND_MODELS[kind].model_fields
        for name in fields:
            assert name in model_fields, f"{kind.value} has no field {name!r}"
