"""The harness has delivered `kinds` wrapped ({item:[..]} / [{item:str}]).

The transport is the boundary that faces the external harness (ADR-037 D7), so
it accepts a wrapped array and still refuses a kind that is not one of the ten.
Measured on the box: search_artifacts rejected {"kinds":[{"item":"nota"}]} with
query.kinds.0 got object, breaking the review routines. No database: the service
stub raises after capturing the validated query.
"""

from __future__ import annotations

import importlib.util
from typing import Any

import pytest

from src.contracts.dom import ArtifactKind, SearchQuery

_HAS_MCP = importlib.util.find_spec("mcp") is not None
pytestmark = pytest.mark.skipif(not _HAS_MCP, reason="the MCP SDK is required")


@pytest.fixture(scope="module")
def transport() -> Any:
    from src.transport import mcp_server

    return mcp_server


class _CapturingArtifacts:
    def __init__(self, sink: dict[str, SearchQuery]) -> None:
        self._sink = sink

    async def search(self, query: SearchQuery) -> Any:
        self._sink["query"] = query
        raise RuntimeError("stop here")


async def _run_search(transport: Any, raw: dict[str, Any]) -> SearchQuery:
    sink: dict[str, SearchQuery] = {}
    transport.set_services(
        transport.Services(
            artifacts=_CapturingArtifacts(sink),  # type: ignore[arg-type]
            relations=object(),  # type: ignore[arg-type]
            embeddings=object(),  # type: ignore[arg-type]
            changes=object(),  # type: ignore[arg-type]
            drafts=object(),  # type: ignore[arg-type]
        )
    )
    tool = transport.mcp._tool_manager.get_tool("search_artifacts")
    try:
        with pytest.raises(Exception, match="stop here"):
            await tool.run(raw)
    finally:
        transport.set_services(None)
    return sink["query"]


@pytest.mark.parametrize(
    "raw_kinds",
    [
        ["nota", "revisao"],
        {"item": ["nota", "revisao"]},
        [{"item": "nota"}, {"item": "revisao"}],
        [{"item": ["nota", "revisao"]}],
    ],
    ids=["plain", "array-wrapped", "element-wrapped", "wrapped-then-listed"],
)
async def test_wrapped_kinds_reach_the_service_as_names(transport: Any, raw_kinds: Any) -> None:
    query = await _run_search(transport, {"query": {"kinds": raw_kinds, "quarter": "Q4-2026"}})
    assert query.kinds == (ArtifactKind.NOTA, ArtifactKind.REVISAO)
    assert all(isinstance(k, ArtifactKind) for k in query.kinds)
    assert query.quarter == "Q4-2026"


async def test_an_unknown_kind_is_still_rejected(transport: Any) -> None:
    tool = transport.mcp._tool_manager.get_tool("search_artifacts")
    with pytest.raises(Exception, match="kinds"):
        await tool.run({"query": {"kinds": ["bogus"]}})


async def test_an_extra_field_is_still_rejected(transport: Any) -> None:
    tool = transport.mcp._tool_manager.get_tool("search_artifacts")
    with pytest.raises(Exception, match="nope"):
        await tool.run({"query": {"kinds": ["nota"], "nope": 1}})
