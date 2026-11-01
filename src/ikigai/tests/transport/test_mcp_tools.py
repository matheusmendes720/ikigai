"""The MCP tool surface (SPEC-03 T3.5).

Two things are asserted here: the surface is exactly the six domain tools it
is supposed to be, and the transport contains no persistence logic of its own.
A tool that exposed SQL would be a database RPC with a nicer name, and the
surface would drift from the services the moment the schema changed.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest
from src.contracts.dom import SearchQuery
from src.contracts.errors import ConflictError, NotFoundError

_HAS_MCP = importlib.util.find_spec("mcp") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_MCP,
    reason="the MCP SDK is required for the transport tests",
)

EXPECTED_TOOLS = {
    "search_artifacts",
    "get_artifact",
    "upsert_artifact",
    "delete_artifact",
    "list_relations",
    "embed_text",
}

TRANSPORT_SOURCE = Path(__file__).resolve().parents[3] / "transport" / "mcp_server.py"


@pytest.fixture(scope="module")
def transport() -> Any:
    from src.transport import mcp_server

    return mcp_server


async def test_the_surface_has_exactly_six_tools(transport: Any) -> None:
    tools = await transport.mcp.list_tools()
    assert {tool.name for tool in tools} == EXPECTED_TOOLS


async def test_every_tool_is_documented(transport: Any) -> None:
    tools = await transport.mcp.list_tools()
    for tool in tools:
        assert tool.description, f"{tool.name} has no description"


def test_the_transport_exposes_no_sql() -> None:
    source = TRANSPORT_SOURCE.read_text(encoding="utf-8")
    matches = re.findall(r"\b(select|insert|update|delete)\s+", source, re.IGNORECASE)
    assert not matches, f"the transport contains SQL: {matches}"


async def test_a_conflict_reaches_the_caller_with_its_code(transport: Any) -> None:
    class FailingArtifacts:
        async def search(self, query: SearchQuery) -> Any:
            raise ConflictError("artefato alterado", detail="expected_revision obsoleto")

    class FailingRelations:
        pass

    class FailingEmbeddings:
        pass

    transport.set_services(
        transport.Services(
            artifacts=FailingArtifacts(),  # type: ignore[arg-type]
            relations=FailingRelations(),  # type: ignore[arg-type]
            embeddings=FailingEmbeddings(),  # type: ignore[arg-type]
        )
    )
    try:
        with pytest.raises(RuntimeError, match="conflict:"):
            await transport.search_artifacts(SearchQuery(text="qualquer"))
    finally:
        transport.set_services(None)


def test_the_transport_is_selected_by_env(transport: Any) -> None:
    """ADR-011: the same server serves stdio locally and http in the cloud."""
    assert transport.resolve_transport({}) == "stdio"
    assert transport.resolve_transport({"IKIGAI_MCP_TRANSPORT": "stdio"}) == "stdio"
    assert transport.resolve_transport({"IKIGAI_MCP_TRANSPORT": "http"}) == "streamable-http"
    assert (
        transport.resolve_transport({"IKIGAI_MCP_TRANSPORT": "streamable-http"})
        == "streamable-http"
    )
    assert transport.resolve_transport({"IKIGAI_MCP_TRANSPORT": "sse"}) == "sse"
    assert transport.resolve_transport({"IKIGAI_MCP_TRANSPORT": " HTTP "}) == "streamable-http"
    with pytest.raises(ValueError, match="unknown IKIGAI_MCP_TRANSPORT"):
        transport.resolve_transport({"IKIGAI_MCP_TRANSPORT": "carrier-pigeon"})


async def test_a_missing_artifact_reaches_the_caller_with_its_code(transport: Any) -> None:
    class FailingArtifacts:
        async def get(self, uid: Any, depth: int = 1) -> Any:
            raise NotFoundError("nenhum artefato com esse uid")

    transport.set_services(
        transport.Services(
            artifacts=FailingArtifacts(),  # type: ignore[arg-type]
            relations=object(),  # type: ignore[arg-type]
            embeddings=object(),  # type: ignore[arg-type]
        )
    )
    try:
        with pytest.raises(RuntimeError, match="not_found:"):
            await transport.get_artifact("kpi:qualquer:a1b2c3d4:0123456789abcdef")
    finally:
        transport.set_services(None)
