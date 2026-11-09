"""The websocket transport (ADR-039).

The websocket is a SECOND way to reach the same six tools, and a channel for
the changes the store announces. These tests hold both halves of that promise:

1. the tool surface over the websocket is EXACTLY the MCP surface — not a
   seventh tool, not a subset, not a copy that can drift;
2. the answers carry the same errors the MCP transport carries, with their
   codes — a conflict over the websocket means "reread", exactly as it does
   over MCP;
3. the transport holds no SQL of its own, anywhere in the package.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from src.contracts.dom import SearchResult
from src.contracts.errors import ConflictError
from src.transport import mcp_server, ws_server

TRANSPORT_PACKAGE = Path(__file__).resolve().parents[3] / "transport"


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


class FakeArtifacts:
    """The service the tools reach, in the shape the transport expects."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[Any] = []

    async def search(self, query: Any) -> SearchResult:
        self.calls.append(query)
        if self.error is not None:
            raise self.error
        return SearchResult(artifacts=())


def _services(error: Exception | None = None) -> Any:
    return mcp_server.Services(
        artifacts=FakeArtifacts(error),
        relations=object(),
        embeddings=object(),
        changes=object(),
        drafts=object(),
    )


@pytest.fixture
def router() -> Any:
    """A router with the tools loaded and the wiring installed."""
    mcp_server.set_services(_services())
    instance = ws_server.Router(mcp_server.get_services())
    return instance


async def _loaded_router(error: Exception | None = None) -> Any:
    mcp_server.set_services(_services(error))
    instance = ws_server.Router(mcp_server.get_services())
    await instance.load_tools()
    return instance


async def test_the_websocket_exposes_exactly_the_mcp_tools() -> None:
    """Not a seventh tool, and not a copy that can drift.

    The registry is built FROM the MCP server, so this holds by construction —
    and the test holds it anyway, because a construction that changes is a
    change nobody notices.
    """
    instance = await _loaded_router()
    mcp_tools = {tool.name for tool in await mcp_server.mcp.list_tools()}

    assert instance.tool_names == mcp_tools
    assert mcp_tools == {
        "search_artifacts",
        "get_artifact",
        "upsert_artifact",
        "delete_artifact",
        "list_relations",
        "embed_text",
    }


async def test_a_call_answers_with_the_tool_result() -> None:
    instance = await _loaded_router()
    socket = FakeSocket()

    await instance.handle(
        socket,  # type: ignore[arg-type]
        json.dumps(
            {
                "type": "call",
                "id": "abc",
                "tool": "search_artifacts",
                "arguments": {"query": {"text": "sono"}},
            }
        ),
    )

    assert len(socket.sent) == 1
    frame = socket.sent[0]
    assert frame["type"] == "result"
    assert frame["id"] == "abc"
    assert frame["ok"] is True
    assert frame["data"]["artifacts"] == []


async def test_a_call_without_an_id_is_still_answered() -> None:
    """The answer always comes back, so a client never waits forever."""
    instance = await _loaded_router()
    socket = FakeSocket()

    await instance.handle(
        socket,  # type: ignore[arg-type]
        json.dumps({"type": "call", "tool": "search_artifacts", "arguments": {}}),
    )

    assert socket.sent[0]["type"] == "result"


async def test_an_unknown_tool_is_refused() -> None:
    instance = await _loaded_router()
    socket = FakeSocket()

    await instance.handle(
        socket,  # type: ignore[arg-type]
        json.dumps({"type": "call", "id": "1", "tool": "drop_the_database", "arguments": {}}),
    )

    frame = socket.sent[0]
    assert frame["ok"] is False
    assert frame["error"]["code"] == "not_found"


async def test_a_malformed_frame_is_refused() -> None:
    instance = await _loaded_router()
    socket = FakeSocket()

    await instance.handle(socket, "not json at all")  # type: ignore[arg-type]

    frame = socket.sent[0]
    assert frame["ok"] is False
    assert frame["error"]["code"] == "malformed"


async def test_a_payload_that_breaks_the_contract_is_refused() -> None:
    """The websocket validates the arguments like the MCP transport does."""
    instance = await _loaded_router()
    socket = FakeSocket()

    await instance.handle(
        socket,  # type: ignore[arg-type]
        json.dumps(
            {
                "type": "call",
                "id": "1",
                "tool": "search_artifacts",
                "arguments": {"query": {"limit": 9999}},
            }
        ),
    )

    frame = socket.sent[0]
    assert frame["ok"] is False
    assert frame["error"]["code"] == "validation"


async def test_a_domain_error_keeps_its_code() -> None:
    """A conflict over the websocket means "reread", exactly as over MCP."""
    instance = await _loaded_router(ConflictError("artefato alterado", detail="obsoleto"))
    socket = FakeSocket()

    await instance.handle(
        socket,  # type: ignore[arg-type]
        json.dumps(
            {
                "type": "call",
                "id": "1",
                "tool": "search_artifacts",
                "arguments": {"query": {"text": "x"}},
            }
        ),
    )

    frame = socket.sent[0]
    assert frame["ok"] is False
    assert frame["error"]["code"] == "conflict"
    assert "artefato alterado" in frame["error"]["message"]


def test_the_tool_surfaces_contain_no_sql() -> None:
    """The modules that expose tools, not the whole package.

    The transport translates intent; the services decide. A query that
    reaches a tool is a query that bypasses the layer that owns the rules.

    `healthcheck.py` is excluded ON PURPOSE and not by accident: it is the
    probe, and the one write it is allowed to make is the row it inserts and
    rolls back to prove the store can be written. It exposes no tool, so it
    is not a surface.
    """
    surfaces = ("mcp_server.py", "ws_server.py")
    offenders: list[str] = []
    for name in surfaces:
        source = (TRANSPORT_PACKAGE / name).read_text(encoding="utf-8")
        matches = re.findall(r"\b(select|insert|update|delete)\s+", source, re.IGNORECASE)
        if matches:
            offenders.append(f"{name}: {matches}")
    assert not offenders, f"the transport contains SQL: {offenders}"


def test_the_bind_address_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IKIGAI_WS_HOST", "0.0.0.0")
    monkeypatch.setenv("IKIGAI_WS_PORT", "9002")

    assert ws_server.ws_host() == "0.0.0.0"
    assert ws_server.ws_port() == 9002


def test_the_default_bind_address_is_the_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IKIGAI_WS_HOST", raising=False)
    monkeypatch.delenv("IKIGAI_WS_PORT", raising=False)

    assert ws_server.ws_host() == "127.0.0.1"
    assert ws_server.ws_port() == 8001


def test_a_client_without_the_token_is_refused() -> None:
    """The channel is a write path, so the token is not optional in practice."""
    instance = ws_server.Router(mcp_server.get_services(), token="s3cret")

    assert instance.authorized(FakeSocket()) is False  # type: ignore[arg-type]

    with_token = FakeSocket()
    with_token.headers["authorization"] = "Bearer s3cret"
    assert instance.authorized(with_token) is True  # type: ignore[arg-type]

    with_query = FakeSocket()
    with_query.query_params["token"] = "s3cret"
    assert instance.authorized(with_query) is True  # type: ignore[arg-type]


def test_a_change_becomes_an_event_frame() -> None:
    from src.services.changes import ChangeEvent

    frame = ws_server.event_frame(ChangeEvent(uid="nota:abc:00000000:00000000", op="UPDATE"))

    assert frame["type"] == "event"
    assert frame["event"] == "artifact.update"
    assert frame["data"]["uid"] == "nota:abc:00000000:00000000"


def test_the_hello_frame_names_the_tools() -> None:
    frame = ws_server.hello_frame({"search_artifacts", "embed_text"}, sequence=0)

    assert frame["type"] == "hello"
    assert frame["tools"] == ["embed_text", "search_artifacts"]
