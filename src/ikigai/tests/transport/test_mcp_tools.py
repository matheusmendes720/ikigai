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
from src.contracts.dom import Relation, RelationType, SearchQuery
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
            changes=object(),  # type: ignore[arg-type]
            drafts=object(),  # type: ignore[arg-type]
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
            changes=object(),  # type: ignore[arg-type]
            drafts=object(),  # type: ignore[arg-type]
        )
    )
    try:
        with pytest.raises(RuntimeError, match="not_found:"):
            await transport.get_artifact("kpi:qualquer:a1b2c3d4:0123456789abcdef")
    finally:
        transport.set_services(None)


async def test_the_bot_sends_what_the_transport_accepts(transport: Any) -> None:
    """A client and the transport must agree on the tool's ARGUMENT NAMES.

    They disagreed once: the transport took the write as a nested `req`
    envelope and the bot sent the four fields flat, so every write from
    Telegram failed with a validation error — and nothing in the suite
    noticed, because nothing compared the two.

    The comparison is against the SCHEMA the server publishes, because that is
    what a client actually sees.
    """
    from src.bot.main import _write_arguments
    from src.contracts.dom import ArtifactKind

    tools = {tool.name: tool for tool in await transport.mcp.list_tools()}
    schema = tools["upsert_artifact"].inputSchema
    properties = set(schema.get("properties", {}))
    required = set(schema.get("required", []))

    sent = _write_arguments(ArtifactKind.NOTA, "nota do dia", "corpo", "abcd1234", "owner")

    assert required <= set(sent), (
        f"the tool requires arguments the bot never sends: {sorted(required - set(sent))}"
    )
    assert set(sent) <= properties, (
        f"the bot sends arguments the tool does not accept: {sorted(set(sent) - properties)}"
    )


async def test_the_write_tool_carries_the_edges(transport: Any) -> None:
    """The harness has to be able to create an edge.

    The skill specs need `EVIDENCES`, `PARENT_OF`, `REFERENCES` and
    `DERIVES_FROM`, and the six tools are bound by ADR-037 D6 — there is no
    seventh tool to create an edge with. So the edges ride with the artifact,
    and the tool has to publish them: a schema that does not mention them
    leaves the agent with a graph it can read and never write.
    """
    tools = {tool.name: tool for tool in await transport.mcp.list_tools()}
    properties = tools["upsert_artifact"].inputSchema.get("properties", {})

    assert "relations" in properties, (
        "the write tool does not publish the edges — the agent can read the "
        "graph and never write it"
    )


async def test_the_edges_reach_the_service(transport: Any) -> None:
    from src.contracts.dom import ArtifactKind, make_uid
    from src.contracts.dom_kinds import KPIArtifact

    seen: dict[str, Any] = {}

    class CapturingArtifacts:
        async def upsert(self, req: Any) -> Any:
            seen["relations"] = req.relations
            raise RuntimeError("stop here")

    transport.set_services(
        transport.Services(
            artifacts=CapturingArtifacts(),  # type: ignore[arg-type]
            relations=object(),  # type: ignore[arg-type]
            embeddings=object(),  # type: ignore[arg-type]
            changes=object(),  # type: ignore[arg-type]
            drafts=object(),  # type: ignore[arg-type]
        )
    )
    try:
        kpi = KPIArtifact(
            uid=make_uid(ArtifactKind.KPI, "sono", "aaaaaaaa", "0123456789abcdef"),
            title="Sono",
            metric="horas de sono",
            period="2026-11",
            created_at="2026-11-04T00:00:00+00:00",
            updated_at="2026-11-04T00:00:00+00:00",
        )
        edge = Relation(
            src_uid=kpi.uid,
            dst_uid=make_uid(ArtifactKind.KPI, "meta", "bbbbbbbb", "0123456789abcdef"),
            rel=RelationType.EVIDENCES,
        )
        with pytest.raises(RuntimeError, match="stop here"):
            await transport.upsert_artifact(
                artifact=kpi,
                idempotency_key="k",
                client_id="owner",
                relations=(edge,),
            )
    finally:
        transport.set_services(None)

    assert seen.get("relations") == (edge,), (
        f"the edges did not reach the service: {seen.get('relations')}"
    )


async def test_the_tool_keeps_the_typed_kind(transport: Any) -> None:
    """A KPI's own fields must survive the transport.

    The repository writes the extension tables by `isinstance`, so an artifact
    that arrives as the bare spine loses its typed fields in silence — and the
    spine forbids extra fields, so the tool has to take the TYPED model.
    """
    from src.contracts.dom import ArtifactKind, make_uid
    from src.contracts.dom_kinds import KPIArtifact

    seen: dict[str, Any] = {}

    class CapturingArtifacts:
        async def upsert(self, req: Any) -> Any:
            seen["type"] = type(req.artifact)
            seen["metric"] = getattr(req.artifact, "metric", None)
            raise RuntimeError("stop here")

    transport.set_services(
        transport.Services(
            artifacts=CapturingArtifacts(),  # type: ignore[arg-type]
            relations=object(),  # type: ignore[arg-type]
            embeddings=object(),  # type: ignore[arg-type]
            changes=object(),  # type: ignore[arg-type]
            drafts=object(),  # type: ignore[arg-type]
        )
    )
    try:
        kpi = KPIArtifact(
            uid=make_uid(ArtifactKind.KPI, "sono", "aaaaaaaa", "0123456789abcdef"),
            title="Sono",
            metric="horas de sono",
            period="2026-11",
            created_at="2026-11-04T00:00:00+00:00",
            updated_at="2026-11-04T00:00:00+00:00",
        )
        with pytest.raises(RuntimeError, match="stop here"):
            await transport.upsert_artifact(
                artifact=kpi,
                idempotency_key="k",
                client_id="owner",
            )
    finally:
        transport.set_services(None)

    assert seen.get("type") is KPIArtifact, (
        f"the artifact arrived as {seen.get('type')} — the typed fields are lost"
    )
    assert seen.get("metric") == "horas de sono"
