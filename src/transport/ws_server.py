"""The websocket transport: the bi-directional sync channel (ADR-039).

The MCP transport is a request/response surface: a client asks, the server
answers, and the connection carries nothing else. That is the right shape for
a harness that drives the store. It is the wrong shape for a CLIENT that has
to stay in sync with writers it cannot see — and there are three of those
here: the Telegram bot, the vault ingestion and the retrieval layer all live
in different containers, and each of them writes.

So the websocket carries two kinds of traffic on one socket:

- **calls** — the client asks for a tool, the server answers. The SAME six
  tools the MCP server exposes, reached through the SAME functions: the
  registry is built from the MCP server itself, so the two surfaces cannot
  drift apart, and a new tool does not have to be written twice.
- **events** — the server pushes what the store changed. The store announces
  it (the trigger is in the migrations), the service layer turns the
  announcement into a domain event, and this module forwards it to whoever is
  connected.

The rules the rest of the system depends on still hold here:

- **The transport holds no persistence logic and no queries.** It translates a
  frame into a service call and translates the service's typed errors back.
- **There is no second writer.** A write that arrives over the websocket goes
  through the same service layer, with the same revision guard and the same
  idempotency key, as a write that arrives over MCP.
- **The tool surface is the six.** Not seven: the websocket is another way to
  reach them, not another set.

Run::

    python -m src.transport.ws_server

Environment
-----------
``IKIGAI_WS_HOST`` / ``IKIGAI_WS_PORT``   the address it binds (127.0.0.1:8001)
``IKIGAI_WS_TOKEN``                      the shared secret a client must present
``IKIGAI_WS_ALLOW_ANONYMOUS``            set it to accept a client with no token
``IKIGAI_STORE_DSN``                     the store, read from the environment
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, ValidationError, validate_call
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.contracts.errors import DataLayerError
from src.contracts.store import STORE_DSN_ENV
from src.services.changes import ChangeEvent
from src.services.wiring import Services, build_services, prepare_runtime
from src.transport import mcp_server
from src.transport.healthcheck import probe

__all__ = ["Router", "build_app", "main", "ws_host", "ws_port"]

WS_HOST_ENV = "IKIGAI_WS_HOST"
WS_PORT_ENV = "IKIGAI_WS_PORT"
WS_TOKEN_ENV = "IKIGAI_WS_TOKEN"
WS_ALLOW_ANONYMOUS_ENV = "IKIGAI_WS_ALLOW_ANONYMOUS"

_DEFAULT_PORT = 8001

# The codes the service layer raises. A frame that carries one of them says
# what the caller should do next, and they have to stay distinguishable: a
# conflict means reread, a validation failure means fix the payload, a
# forbidden means stop, a missing artifact means check the uid.
_DOMAIN_CODES = ("conflict", "validation", "forbidden", "not_found")


def ws_host() -> str:
    """The address the websocket binds.

    The loopback is the default, for the same reason the MCP transport's
    default is the loopback: a service is not exposed by accident.
    """
    return (os.environ.get(WS_HOST_ENV) or "127.0.0.1").strip()


def ws_port() -> int:
    """The port the websocket binds."""
    raw = (os.environ.get(WS_PORT_ENV) or str(_DEFAULT_PORT)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{WS_PORT_ENV} is not a port number: {raw!r}") from exc


def _jsonable(value: Any) -> Any:
    """A result the wire can carry."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def result_frame(request_id: str, data: Any) -> dict[str, Any]:
    """The frame that answers a call that worked."""
    return {"type": "result", "id": request_id, "ok": True, "data": data}


def error_frame(
    request_id: str,
    code: str,
    message: str = "",
    detail: str = "",
) -> dict[str, Any]:
    """The frame that answers a call that did not.

    The shape is the same as a success — one kind of answer to a request —
    and the outcome is the `ok` flag. A client never has to guess which kind
    of frame it is looking at.
    """
    error: dict[str, Any] = {"code": code, "message": message}
    if detail:
        error["detail"] = detail
    return {"type": "result", "id": request_id, "ok": False, "error": error}


def event_frame(event: ChangeEvent) -> dict[str, Any]:
    """The frame that carries a change to the clients."""
    return {
        "type": "event",
        "event": f"artifact.{event.op.lower()}",
        "data": {"uid": event.uid, "op": event.op},
    }


def hello_frame(tools: set[str]) -> dict[str, Any]:
    """The first frame of a connection: who this is and what it can do."""
    return {"type": "hello", "server": "ikigai-ws", "tools": sorted(tools)}


def _domain_error(exc: Exception) -> tuple[str, str, str]:
    """The code, the message and the detail of a failed call.

    The transport's own wrapper renders a typed error as
    ``"<code>: <message> (<detail>)"``, so the code is read back from the
    message. A failure that carries no code is a plain error, and says so.
    """
    if isinstance(exc, DataLayerError):
        payload = exc.to_dict()
        return str(payload["code"]), str(payload["message"]), str(payload["detail"] or "")

    message = str(exc)
    code, separator, rest = message.partition(": ")
    if separator and code in _DOMAIN_CODES:
        detail = ""
        if rest.endswith(")") and " (" in rest:
            rest, _, detail = rest.rpartition(" (")
            detail = detail[:-1]
        return code, rest, detail
    return "error", message, ""


class Router:
    """The connected clients, the tool registry and the change feed."""

    def __init__(self, services: Services, *, token: str | None = None) -> None:
        self._services = services
        self._token = token
        self._tools: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._validators: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._clients: set[WebSocket] = set()

    @property
    def services(self) -> Services:
        return self._services

    @property
    def tool_names(self) -> set[str]:
        return set(self._tools)

    async def load_tools(self) -> None:
        """Build the registry FROM the MCP server.

        The websocket does not get its own list of tools: it asks the MCP
        server which ones exist and takes the functions from the same module
        the MCP server registers. The two surfaces therefore cannot drift —
        a tool added to one is in the other, and a tool that exists in the
        list but not in the module is a startup error, not a silent hole.
        """
        tools = await mcp_server.mcp.list_tools()
        registry: dict[str, Callable[..., Awaitable[Any]]] = {}
        validators: dict[str, Callable[..., Awaitable[Any]]] = {}
        for tool in tools:
            function = getattr(mcp_server, tool.name, None)
            if function is None or not callable(function):
                raise RuntimeError(
                    f"the MCP server exposes {tool.name!r} but the transport module does "
                    f"not define it — the websocket would have no way to call it"
                )
            registry[tool.name] = function
            validators[tool.name] = validate_call(function)
        self._tools = registry
        self._validators = validators

    def authorized(self, websocket: WebSocket) -> bool:
        """Whether this client may use the channel.

        The token is compared in constant time, and it is compared against the
        header OR the query string — a browser cannot set headers on a
        websocket handshake, and the clients here are not all browsers.
        """
        if self._token is None:
            return True
        header = websocket.headers.get("authorization", "")
        if header.startswith("Bearer ") and secrets.compare_digest(
            header[len("Bearer ") :].strip(), self._token
        ):
            return True
        query = websocket.query_params.get("token", "")
        return bool(query) and secrets.compare_digest(query, self._token)

    async def join(self, websocket: WebSocket) -> None:
        self._clients.add(websocket)

    async def leave(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def broadcast(self, event: ChangeEvent) -> None:
        """Push a change to everyone who is listening."""
        frame = event_frame(event)
        for client in list(self._clients):
            try:
                await client.send_json(frame)
            except Exception:  # a client that cannot be reached is gone
                self._clients.discard(client)

    async def handle(self, websocket: WebSocket, raw: str) -> None:
        """Answer one frame."""
        try:
            frame = json.loads(raw)
        except (TypeError, ValueError):
            await self._send(websocket, error_frame("", "malformed", "the frame is not JSON"))
            return
        if not isinstance(frame, dict):
            await self._send(websocket, error_frame("", "malformed", "the frame is not an object"))
            return

        request_id = str(frame.get("id") or "")
        if frame.get("type") != "call":
            await self._send(
                websocket,
                error_frame(request_id, "malformed", f"unknown frame type: {frame.get('type')!r}"),
            )
            return

        name = frame.get("tool")
        arguments = frame.get("arguments")
        if not isinstance(name, str) or not name:
            await self._send(
                websocket, error_frame(request_id, "malformed", "the frame names no tool")
            )
            return
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            await self._send(
                websocket,
                error_frame(request_id, "malformed", "the arguments are not an object"),
            )
            return

        validator = self._validators.get(name)
        if validator is None:
            await self._send(
                websocket, error_frame(request_id, "not_found", f"no tool named {name!r}")
            )
            return

        try:
            result = await validator(**arguments)
        except ValidationError as exc:
            await self._send(websocket, error_frame(request_id, "validation", str(exc)))
            return
        except Exception as exc:
            code, message, detail = _domain_error(exc)
            await self._send(websocket, error_frame(request_id, code, message, detail))
            return

        await self._send(websocket, result_frame(request_id, _jsonable(result)))

    @staticmethod
    async def _send(websocket: WebSocket, frame: dict[str, Any]) -> None:
        try:
            await websocket.send_json(frame)
        except Exception:  # the client is gone; there is nobody to tell
            return


async def _pump(router: Router) -> None:
    """Forward the store's changes to the connected clients.

    The feed is the store's own announcement, so a write made by the vault
    ingestion — in another container, by another process — reaches the
    clients without anybody polling for it.
    """
    try:
        async for event in router.services.changes.events():
            await router.broadcast(event)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(f"the change feed stopped: {exc}", file=sys.stderr)


def build_app(services: Services, *, token: str | None = None) -> Starlette:
    """The ASGI application: one websocket route and one health route.

    The wiring is installed into the MCP transport's own holder, so there is
    ONE wiring per process: the tools this module calls are the MCP server's
    functions, and they resolve the services from that holder. A second
    wiring would be a second pool against the same store, for no reason.
    """
    mcp_server.set_services(services)
    router = Router(services, token=token)

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        await router.load_tools()
        pump = asyncio.create_task(_pump(router))
        try:
            yield
        finally:
            pump.cancel()

    async def healthz(request: Request) -> Response:
        """The data plane, not the surface (contract C-2).

        The container must not report healthy while the store is unreachable.
        The probe writes a row and throws it away — the only query that
        proves the store can be written under the service's own role.
        """
        dsn = os.environ.get(STORE_DSN_ENV)
        if not dsn:
            return JSONResponse(
                {"status": "unhealthy", "detail": f"{STORE_DSN_ENV} is not set"},
                status_code=503,
            )
        try:
            await asyncio.to_thread(probe, dsn, ws_host(), ws_port())
        except Exception as exc:
            return JSONResponse({"status": "unhealthy", "detail": str(exc)}, status_code=503)
        return JSONResponse({"status": "healthy"})

    async def sync_route(websocket: WebSocket) -> None:
        if not router.authorized(websocket):
            await websocket.close(code=4401)
            return
        await websocket.accept()
        await router.join(websocket)
        try:
            await websocket.send_json(hello_frame(router.tool_names))
            while True:
                message = await websocket.receive_text()
                await router.handle(websocket, message)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            print(f"the websocket failed: {exc}", file=sys.stderr)
        finally:
            await router.leave(websocket)

    return Starlette(
        routes=[
            WebSocketRoute("/sync", sync_route),
            Route("/healthz", healthz),
        ],
        lifespan=lifespan,
    )


def main() -> None:
    """Run the websocket server."""
    # Before the loop exists: the store's driver refuses Windows' default
    # event loop, and the policy has to be chosen before the loop is created.
    prepare_runtime()

    token = (os.environ.get(WS_TOKEN_ENV) or "").strip() or None
    if token is None and not (os.environ.get(WS_ALLOW_ANONYMOUS_ENV) or "").strip():
        raise SystemExit(
            f"{WS_TOKEN_ENV} is not set — the websocket is a write channel, so it "
            f"refuses to start without a token. Set {WS_TOKEN_ENV}, or set "
            f"{WS_ALLOW_ANONYMOUS_ENV}=1 to accept a client with none."
        )

    import uvicorn

    services = build_services()
    app = build_app(services, token=token)
    uvicorn.run(app, host=ws_host(), port=ws_port(), log_level="info")


if __name__ == "__main__":
    main()
