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
- **drafts** — the client's unfinished prose. It is a THIRD kind of frame and
  deliberately not a seventh tool: the tool surface is the six of ADR-037 D6,
  and a draft is not an operation on the DOM. It rides here because it is the
  only surface with a connection that outlives a request — the whole point of
  a draft is that it survives the client going away (ADR-040).

The rules the rest of the system depends on still hold here:

- **The transport holds no persistence logic and no queries.** It translates a
  frame into a service call and translates the service's typed errors back.
- **There is no second writer.** A write that arrives over the websocket goes
  through the same service layer, with the same revision guard and the same
  idempotency key, as a write that arrives over MCP.
- **The tool surface is the six.** Not seven: the websocket is another way to
  reach them, not another set. A draft is not a tool — it is state, and it is
  reached with its own frame type.

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
import hashlib
import json
import os
import secrets
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import is_dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError, validate_call
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.contracts.dom import ArtifactKind
from src.contracts.drafts import Draft
from src.contracts.errors import DataLayerError, InvalidPayloadError, NotFoundError
from src.contracts.store import STORE_DSN_ENV
from src.services.changes import ChangeEvent
from src.services.wiring import Services, build_services, prepare_runtime
from src.transport import mcp_server
from src.transport.healthcheck import probe

__all__ = ["Router", "build_app", "draft_frame", "main", "ws_host", "ws_port"]

WS_HOST_ENV = "IKIGAI_WS_HOST"
WS_PORT_ENV = "IKIGAI_WS_PORT"
WS_TOKEN_ENV = "IKIGAI_WS_TOKEN"
WS_ALLOW_ANONYMOUS_ENV = "IKIGAI_WS_ALLOW_ANONYMOUS"
CLIENT_ID_ENV = "IKIGAI_CLIENT_ID"

_DEFAULT_PORT = 8001

#: How many change events the log keeps. It is a bound for a log that only
#: grows, not a promise: a client that was away longer than this gets
#: `truncated` and rereads what it cares about.
EVENT_LOG_KEEP = 10000

#: The four things a client does with a draft. They are NOT tools: the tool
#: surface is the six of ADR-037 D6, and a draft is state, not an operation on
#: the DOM.
_DRAFT_OPS = ("save", "get", "list", "discard")


def default_client_id() -> str:
    """The identity a draft belongs to, when the frame names none.

    It is the same `IKIGAI_CLIENT_ID` the write envelope carries: one person
    with several devices. A draft scoped to a socket would be a draft that dies
    with it, which is the thing drafts exist to avoid.
    """
    return (os.environ.get(CLIENT_ID_ENV) or "owner").strip()


def _require_draft_id(frame: dict[str, Any]) -> str:
    draft_id = str(frame.get("draft_id") or "").strip()
    if not draft_id:
        raise InvalidPayloadError(
            "the frame names no draft_id",
            detail="a draft is addressed by (client_id, draft_id) and the id is required",
        )
    return draft_id


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _draft_key(client_id: str, draft_id: str, body: str, at: datetime) -> str:
    """The de-duplication key of one save.

    It carries the CONTENT and the moment: two saves of the same text are the
    same intent, so a client that retries after a dropped socket does not turn
    one save into two. Two saves of different text are two saves, even a
    second apart.
    """
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    return f"draft:{client_id}:{draft_id}:{digest}:{at.isoformat(timespec='seconds')}"


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
    """A result the wire can carry.

    A dataclass is here on purpose: `ChangeEvent` and `Replay` are the domain
    events, and they are plain frozen dataclasses rather than Pydantic models
    — the service layer holds meaning, and it does not need a validation
    framework for two fields. `json.dumps` does not know how to serialise one,
    so a conversion that skips this branch sends an object over a socket and
    fails on the client's side of the wire.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return {field: _jsonable(getattr(value, field)) for field in value.__dataclass_fields__}
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
    """The frame that carries a change to the clients.

    It carries the store's SEQUENCE, and that is what lets a client survive a
    dropped connection: it remembers the last one it saw, and asks for what
    came after it on the next connect (`resume`). Without the sequence the
    client would have to reread everything to find out what it missed.
    """
    data: dict[str, Any] = {"uid": event.uid, "op": event.op}
    if event.seq is not None:
        data["seq"] = event.seq
    return {"type": "event", "event": f"artifact.{event.op.lower()}", "data": data}


def hello_frame(tools: set[str], sequence: int) -> dict[str, Any]:
    """The first frame of a connection: who this is, and where the feed is.

    `sequence` is the store's tip AT THIS MOMENT. A client that reconnects
    compares it with the last sequence it saw: equal means nothing happened
    while it was away, and a difference is the gap it has to ask for.
    """
    return {
        "type": "hello",
        "server": "ikigai-ws",
        "tools": sorted(tools),
        # The drafts are not tools, and a client that only knows the tool list
        # would never try one. This is the frame that tells it they exist.
        "drafts": ["save", "get", "list", "discard"],
        # Where the change log stands right now.
        "sequence": sequence,
    }


def draft_frame(draft: Any) -> dict[str, Any]:
    """A draft on the wire.

    It carries the revision because that is what the client has to send back
    to save over it — a draft without its revision is a draft the client can
    only overwrite blindly.
    """
    return {"type": "draft", "draft": _jsonable(draft)}


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

    async def tip(self) -> int:
        """Where the change log stands, or 0 when it cannot be read.

        A store that cannot answer must not stop the connection from opening:
        the live feed still works, and a client that gets 0 simply has no gap
        to replay. Failing the handshake would turn a degraded replay into no
        client at all.
        """
        try:
            return await self.services.changes.tip()
        except Exception as exc:
            print(f"the change log tip is unreadable: {exc}", file=sys.stderr)
            return 0

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
        frame_type = frame.get("type")
        if frame_type == "draft":
            await self._handle_draft(websocket, request_id, frame)
            return
        if frame_type == "resume":
            await self._handle_resume(websocket, request_id, frame)
            return
        if frame_type != "call":
            await self._send(
                websocket,
                error_frame(request_id, "malformed", f"unknown frame type: {frame_type!r}"),
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

    async def _handle_resume(
        self, websocket: WebSocket, request_id: str, frame: dict[str, Any]
    ) -> None:
        """Replay the changes a client missed while it was away.

        The client sends the last sequence it saw — the `sequence` from its
        `hello`, or the `seq` of the last event it received — and gets what
        came after it, oldest first, with the store's tip and whether the gap
        was bigger than one page.

        This is the half a `NOTIFY` cannot give. The channel reaches whoever is
        listening at that instant and nobody else, so without this a client
        that was reconnecting when a write happened would never learn it
        happened, and the gap would be silent and permanent.
        """
        since = frame.get("since")
        if since is None or since == "":
            await self._send(
                websocket,
                error_frame(request_id, "validation", "the resume frame names no 'since'"),
            )
            return
        limit = int(frame.get("limit") or 500)
        try:
            replay = await self.services.changes.replay(int(since), limit)
        except Exception as exc:
            code, message, detail = _domain_error(exc)
            await self._send(websocket, error_frame(request_id, code, message, detail))
            return

        await self._send(
            websocket,
            result_frame(
                request_id,
                {
                    "events": [_jsonable(event) for event in replay.events],
                    "tip": replay.tip,
                    "truncated": replay.truncated,
                    # The oldest event still kept. `lost` is the difference
                    # between "you are up to date" and "I no longer have what
                    # you missed" — the same empty page answers both.
                    "floor": replay.floor,
                    "lost": replay.lost,
                    "last_seq": replay.last_seq,
                },
            ),
        )

    async def _handle_draft(
        self, websocket: WebSocket, request_id: str, frame: dict[str, Any]
    ) -> None:
        """Save, read, list or discard a draft.

        Four operations on one frame type. The client states the draft and the
        revision it expects; the service states the clock and the guard.

        A client that sends no `client_id` gets the one the deployment was
        configured with — the same identity the artifacts carry, because one
        person with several devices is the model here, and a draft scoped to a
        socket would be a draft that dies with it.
        """
        op = frame.get("op")
        if op not in _DRAFT_OPS:
            await self._send(
                websocket,
                error_frame(request_id, "malformed", f"unknown draft op: {op!r}"),
            )
            return

        client_id = str(frame.get("client_id") or default_client_id()).strip()
        if not client_id:
            await self._send(
                websocket,
                error_frame(request_id, "validation", "the frame names no client"),
            )
            return

        try:
            if op == "save":
                result = await self._draft_save(client_id, frame)
            elif op == "get":
                result = await self._draft_get(client_id, frame)
            elif op == "list":
                result = await self.services.drafts.open_drafts(
                    client_id, int(frame.get("limit") or 50)
                )
            else:
                result = await self.services.drafts.discard(
                    client_id,
                    _require_draft_id(frame),
                    expected_revision=_optional_int(frame.get("expected_revision")),
                )
        except Exception as exc:
            code, message, detail = _domain_error(exc)
            await self._send(websocket, error_frame(request_id, code, message, detail))
            return

        if isinstance(result, list):
            await self._send(
                websocket,
                result_frame(request_id, {"drafts": [_jsonable(item) for item in result]}),
            )
            return
        if isinstance(result, Draft):
            await self._send(websocket, result_frame(request_id, draft_frame(result)["draft"]))
            return
        await self._send(websocket, result_frame(request_id, _jsonable(result)))

    async def _draft_save(self, client_id: str, frame: dict[str, Any]) -> Any:
        """A save: the draft as the client stated it, plus the clock."""
        now = datetime.now(UTC)
        draft = Draft(
            client_id=client_id,
            draft_id=_require_draft_id(frame),
            kind=frame.get("kind") or ArtifactKind.NOTA,
            title=frame.get("title"),
            body=str(frame.get("body") or ""),
            parent_uid=frame.get("parent_uid") or None,
            created_at=now,
            updated_at=now,
        )
        return await self.services.drafts.save(
            draft,
            expected_revision=_optional_int(frame.get("expected_revision")),
            idempotency_key=_draft_key(client_id, draft.draft_id, draft.body, now),
        )

    async def _draft_get(self, client_id: str, frame: dict[str, Any]) -> Any:
        draft = await self.services.drafts.get(client_id, _require_draft_id(frame))
        if draft is None:
            raise NotFoundError(
                f"no draft {frame.get('draft_id')!r} for {client_id!r}",
                detail="a draft that was never saved cannot be read",
            )
        return draft

    @staticmethod
    async def _send(websocket: WebSocket, frame: dict[str, Any]) -> None:
        try:
            await websocket.send_json(frame)
        except Exception:  # the client is gone; there is nobody to tell
            return


async def _prune_once(router: Router) -> None:
    """Keep the change log bounded, once per start.

    An event is only interesting to a client that has not replayed it yet, so
    the log does not have to be forever — and a table that only grows is a
    table that eventually costs a backup. Pruning on startup, and not on a
    timer, keeps it off the request path and out of the scheduler.

    It NEVER fails the boot: an unreadable log is a log nobody replays, and a
    service that refuses to start over its own housekeeping is worse than a
    log that grew.
    """
    try:
        removed = await router.services.changes.prune(EVENT_LOG_KEEP)
        if removed:
            print(f"pruned {removed} old change events", file=sys.stderr)
    except Exception as exc:
        print(f"the change log was not pruned: {exc}", file=sys.stderr)


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
        await _prune_once(router)
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
            await websocket.send_json(hello_frame(router.tool_names, await router.tip()))
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
