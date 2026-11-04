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
import os
from collections.abc import Awaitable, Callable, Mapping
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
from src.contracts.dom_kinds import ArtifactPayload
from src.services.wiring import Services, build_services, prepare_runtime

__all__ = [
    "Services",
    "get_services",
    "mcp",
    "resolve_transport",
    "set_services",
    "transport_host",
    "transport_port",
]

TRANSPORT_HOST_ENV = "FASTMCP_HOST"
TRANSPORT_PORT_ENV = "FASTMCP_PORT"


def transport_host() -> str:
    """The address the transport binds.

    FastMCP takes the host as a CONSTRUCTOR argument and reads nothing from
    the environment: `mcp.run()` accepts only the transport, and the default
    host is the loopback. A deployment that sets FASTMCP_HOST and trusts the
    library to honour it ends up with a server no other container can reach —
    and a healthcheck that connects to itself reports it healthy anyway.
    """
    return (os.environ.get(TRANSPORT_HOST_ENV) or "127.0.0.1").strip()


def transport_port() -> int:
    """The port the transport binds."""
    raw = (os.environ.get(TRANSPORT_PORT_ENV) or "8000").strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{TRANSPORT_PORT_ENV} is not a port number: {raw!r}") from exc


mcp = FastMCP("ikigai-data", host=transport_host(), port=transport_port())
"""The server the harness connects to."""

_T = TypeVar("_T")


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
async def upsert_artifact(
    artifact: ArtifactPayload,
    idempotency_key: str,
    client_id: str,
    expected_revision: int | None = None,
    relations: tuple[Relation, ...] = (),
) -> WriteOutcome:
    """Escreve um artefato com versionamento otimista.

    Conflito de revisão retorna CONFLICT: releia o artefato e reaplique. Nunca
    sobrescreve o trabalho de outro cliente em silêncio.

    The artifact is the TYPED model for its kind, not the bare spine: a KPI
    carries its metric and its target, and the store keeps them in the
    extension table. `expected_revision` is null for a create and the
    revision you read for an update.

    `relations` are the edges the artifact STARTS, and they are written with
    it, in the same transaction: the graph is written with the node, or not at
    all. Each edge names the destination, which must already exist; the
    source is the artifact being written.
    """
    return await get_services().artifacts.upsert(
        WriteRequest(
            artifact=artifact,
            expected_revision=expected_revision,
            idempotency_key=idempotency_key,
            client_id=client_id,
            relations=relations,
        )
    )


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


_TRANSPORTS = {
    "stdio": "stdio",
    "http": "streamable-http",
    "streamable-http": "streamable-http",
    "sse": "sse",
}
"""IKIGAI_MCP_TRANSPORT value -> the transport name FastMCP understands (ADR-011)."""


def resolve_transport(env: Mapping[str, str] | None = None) -> str:
    """Pick the transport from IKIGAI_MCP_TRANSPORT (ADR-011).

    ``stdio`` keeps the local harness working; ``http`` is what a cloud
    deployment needs. Host and port come from FastMCP's own settings
    (``FASTMCP_HOST`` / ``FASTMCP_PORT``).
    """
    source = os.environ if env is None else env
    raw = (source.get("IKIGAI_MCP_TRANSPORT") or "stdio").strip().lower()
    if raw not in _TRANSPORTS:
        raise ValueError(
            f"unknown IKIGAI_MCP_TRANSPORT: {raw!r} (expected one of {sorted(_TRANSPORTS)})"
        )
    return _TRANSPORTS[raw]


def main() -> None:
    """Run the server. The harness decides how to reach it."""
    # Before mcp.run(): the policy has to be chosen before the loop exists.
    prepare_runtime()
    mcp.run(transport=resolve_transport())


if __name__ == "__main__":
    main()
