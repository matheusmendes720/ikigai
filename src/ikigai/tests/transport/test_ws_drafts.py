"""The drafts over the websocket: a third frame type, and not a seventh tool.

The tool surface is the six of ADR-037 D6, so a draft cannot be a tool — and
it must not become one by accident. It rides on the socket because the socket
is the only surface whose CONNECTION outlives a request, and the whole point of
a draft is that it survives the client going away.

Four things these tests hold:

1. the tool surface is still exactly six — the drafts did not sneak in;
2. a draft frame reaches the draft service, with the client the frame named;
3. a frame that names no draft is a validation error, not a crash;
4. the hello frame says the drafts exist, because a client that only knows the
   tool list would never try one.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.contracts.drafts import Draft, DraftOutcome
from src.contracts.errors import ConflictError
from src.transport import mcp_server, ws_server


class FakeSocket:
    """A socket that keeps what was sent to it."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.headers: dict[str, str] = {}
        self.query_params: dict[str, str] = {}

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)

    async def close(self, code: int = 1000) -> None:
        return


class FakeDrafts:
    """The draft service, in the shape the transport expects."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.saved: list[Any] = []
        self.discarded: list[tuple[str, str, int | None]] = []
        self.listed: list[str] = []
        self.read: list[tuple[str, str]] = []

    async def save(self, draft: Draft, *, expected_revision: Any = None) -> Any:
        if self.error is not None:
            raise self.error
        self.saved.append((draft, expected_revision))
        return DraftOutcome(
            client_id=draft.client_id,
            draft_id=draft.draft_id,
            revision=1,
            outcome="created",
        )

    async def get(self, client_id: str, draft_id: str) -> Any:
        self.read.append((client_id, draft_id))
        return None

    async def open_drafts(self, client_id: str, limit: int = 50) -> list[Any]:
        self.listed.append(client_id)
        return []

    async def discard(
        self, client_id: str, draft_id: str, *, expected_revision: Any = None
    ) -> Any:
        self.discarded.append((client_id, draft_id, expected_revision))
        return DraftOutcome(
            client_id=client_id,
            draft_id=draft_id,
            revision=1,
            outcome="discarded",
        )


class FakeArtifacts:
    async def search(self, query: Any) -> Any:
        from src.contracts.dom import SearchResult

        return SearchResult(artifacts=())


def _router(drafts: Any) -> Any:
    services = mcp_server.Services(
        artifacts=FakeArtifacts(),  # type: ignore[arg-type]
        relations=object(),  # type: ignore[arg-type]
        embeddings=object(),  # type: ignore[arg-type]
        changes=object(),  # type: ignore[arg-type]
        drafts=drafts,  # type: ignore[arg-type]
    )
    mcp_server.set_services(services)
    return ws_server.Router(services)


async def _handle(drafts: Any, frame: dict[str, Any]) -> dict[str, Any]:
    router = _router(drafts)
    await router.load_tools()
    socket = FakeSocket()
    await router.handle(socket, json.dumps(frame))  # type: ignore[arg-type]
    assert socket.sent, "the client got no answer and would wait forever"
    return socket.sent[0]


async def test_the_tool_surface_is_still_the_six() -> None:
    """A draft is state, not an operation on the DOM."""
    router = _router(FakeDrafts())
    await router.load_tools()

    tools = {tool.name for tool in await mcp_server.mcp.list_tools()}

    assert tools == {
        "search_artifacts",
        "get_artifact",
        "upsert_artifact",
        "delete_artifact",
        "list_relations",
        "embed_text",
    }
    assert "save_draft" not in router.tool_names
    assert not any("draft" in name for name in router.tool_names)


async def test_a_draft_save_reaches_the_draft_service() -> None:
    drafts = FakeDrafts()

    frame = await _handle(
        drafts,
        {
            "type": "draft",
            "id": "d1",
            "op": "save",
            "draft_id": "nota-1",
            "kind": "nota",
            "title": "Uma nota",
            "body": "primeiro paragrafo",
        },
    )

    assert frame["type"] == "result"
    assert frame["ok"] is True
    assert len(drafts.saved) == 1
    saved, expected = drafts.saved[0]
    assert saved.draft_id == "nota-1"
    assert str(saved.kind) == "nota"
    assert expected is None, "a first save expects no revision"


async def test_the_frame_names_the_client_and_the_service_does_not() -> None:
    """Two devices are two drafts, and the frame is what says which one."""
    drafts = FakeDrafts()

    await _handle(
        drafts,
        {
            "type": "draft",
            "id": "d2",
            "op": "save",
            "draft_id": "n1",
            "client_id": "outra-maquina",
            "body": "x",
        },
    )

    assert drafts.saved[-1][0].client_id == "outra-maquina"


async def test_a_list_is_scoped_to_the_client_the_frame_names() -> None:
    drafts = FakeDrafts()

    frame = await _handle(
        drafts,
        {"type": "draft", "id": "d3", "op": "list", "client_id": "maquina-b"},
    )

    assert drafts.listed == ["maquina-b"]
    assert frame["data"]["drafts"] == []


async def test_a_discard_carries_the_revision_it_expects() -> None:
    drafts = FakeDrafts()

    await _handle(
        drafts,
        {
            "type": "draft",
            "id": "d4",
            "op": "discard",
            "draft_id": "nota-1",
            "expected_revision": 3,
        },
    )

    assert drafts.discarded[-1][1] == "nota-1"
    assert drafts.discarded[-1][2] == 3


async def test_a_frame_that_names_no_draft_is_a_validation_error() -> None:
    frame = await _handle(FakeDrafts(), {"type": "draft", "id": "d5", "op": "save", "body": "x"})

    assert frame["ok"] is False
    assert frame["error"]["code"] == "validation"


async def test_an_unknown_draft_op_is_refused() -> None:
    frame = await _handle(FakeDrafts(), {"type": "draft", "id": "d6", "op": "commit"})

    assert frame["ok"] is False
    assert frame["error"]["code"] == "malformed"


async def test_a_conflict_over_the_socket_keeps_its_code() -> None:
    """A conflict means reread and reapply, exactly as it does over MCP."""
    drafts = FakeDrafts(error=ConflictError("draft n1 was changed", detail="stale"))

    frame = await _handle(
        drafts,
        {"type": "draft", "id": "d7", "op": "save", "draft_id": "n1", "body": "x"},
    )

    assert frame["ok"] is False
    assert frame["error"]["code"] == "conflict"


async def test_a_read_of_something_absent_is_a_not_found() -> None:
    frame = await _handle(
        FakeDrafts(), {"type": "draft", "id": "d8", "op": "get", "draft_id": "nao-existe"}
    )

    assert frame["ok"] is False
    assert frame["error"]["code"] == "not_found"


async def test_the_hello_frame_advertises_the_drafts() -> None:
    """A client that only knows the tool list would never try a draft."""
    frame = ws_server.hello_frame({"search_artifacts"}, sequence=7)

    assert frame["tools"] == ["search_artifacts"]
    assert frame["drafts"] == ["save", "get", "list", "discard"]
    assert frame["sequence"] == 7, "the client needs the tip to know its gap"


def test_the_client_defaults_to_the_deployment_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IKIGAI_CLIENT_ID", "owner-no-vps")
    assert ws_server.default_client_id() == "owner-no-vps"

    monkeypatch.delenv("IKIGAI_CLIENT_ID")
    assert ws_server.default_client_id() == "owner"
