"""The MCP transport over the service layer.

Six tools, each expressing one domain intent. A tool that exposed a table would
be a database RPC with a nicer name; these expose what a client actually wants
to do. The transport holds no persistence logic and no queries of its own —
it translates intent into a service call and translates the service's typed
errors back into something the agent can act on.

The harness is external (ADR-037 D7): this module is the tool surface the pi
loads, not a framework around an agent.
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from mcp.server.fastmcp import FastMCP

from src.contracts.common import UEID
from src.contracts.dom import (
    ArtifactBundle,
    Relation,
    RelationType,
    SearchQuery,
    SearchResult,
    WriteOutcome,
    WriteRequest,
)
from src.contracts.errors import DataLayerError

from src.data.client import DataClient
from src.data.repository import ArtifactRepository
from src.services.artifacts import ArtifactService
from src.services.embeddings import EmbeddingService
from src.services.relations import RelationService

__all__ = ["Services", "get_services", "mcp", "set_services"]

mcp = FastMCP("ikigai-data")
"""The server the harness connects to."""

_T = TypeVar("_T")


@dataclass
class Services:
    """The service wiring the tools call into."""

    artifacts: ArtifactService
    relations: RelationService
    embeddings: EmbeddingService


def build_services() -> Services:
    """Wire the services against the configured store."""
    client = DataClient()
    repo = ArtifactRepository(client)
    return Services(
        artifacts=ArtifactService(repo),
        relations=RelationService(repo),
        embeddings=EmbeddingService(client),
    )


_services: Services | None = None


def get_services() -> Services:
    """The process-wide wiring, built on first use."""
    global _services
    if _services is None:
        _services = build_services()
    return _services


def set_services(services: Services | None) -> None:
    """Replace the wiring. Used by the tests and by a bootstrap that injects a client."""
    global _services
    _services = services


def _tool_error(exc: DataLayerError) -> Exception:
    """Turn a typed domain error into something the harness can read."""
    payload = exc.to_dict()
    message = f"{payload['code']}: {payload['message']}"
    if payload["detail"]:
        message = f"{message} ({payload['detail']})"
    return RuntimeError(message)


def _translate_errors(
    fn: Callable[..., Awaitable[_T]],
) -> Callable[..., Awaitable[_T]]:
    """Map the service's typed errors onto the tool boundary."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> _T:
        try:
            return await fn(*args, **kwargs)
        except DataLayerError as exc:
            raise _tool_error(exc) from exc

    return wrapper


@mcp.tool()
@_translate_errors
async def search_artifacts(query: SearchQuery) -> SearchResult:
    """Busca por índice estruturado, texto completo ou semântica.

    Use this to answer "what do we know about X" without reading the vault.
    """
    return await get_services().artifacts.search(query)


@mcp.tool()
@_translate_errors
async def get_artifact(uid: UEID, depth: int = 1) -> ArtifactBundle:
    """Lê um artefato e suas relações.

    depth=1 devolve o artefato e os vizinhos imediatos; depth=0 devolve só o
    artefato e as suas arestas.
    """
    return await get_services().artifacts.get(uid, depth=depth)


@mcp.tool()
@_translate_errors
async def upsert_artifact(req: WriteRequest) -> WriteOutcome:
    """Escreve um artefato com versionamento otimista.

    Conflito de revisão retorna CONFLICT: releia o artefato e reaplique. Nunca
    sobrescreve o trabalho de outro cliente em silêncio.
    """
    return await get_services().artifacts.upsert(req)


@mcp.tool()
@_translate_errors
async def delete_artifact(uid: UEID, expected_revision: int) -> WriteOutcome:
    """Remove logicamente um artefato.

    A linha e o histórico permanecem no store; só o campo deleted_at muda.
    """
    return await get_services().artifacts.delete(uid, expected_revision)


@mcp.tool()
@_translate_errors
async def list_relations(uid: UEID, rel: RelationType | None = None) -> list[Relation]:
    """Navega o grafo a partir de um artefato."""
    return await get_services().relations.neighbors(uid, rel)


@mcp.tool()
@_translate_errors
async def embed_text(text: str) -> list[float]:
    """Vetoriza um texto e devolve o embedding."""
    return await get_services().embeddings.embed(text)


def main() -> None:
    """Run the server. The harness decides how to reach it."""
    mcp.run()


if __name__ == "__main__":
    main()
