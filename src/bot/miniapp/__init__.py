"""The Mini App: the owner's panel on the agent's session.

A Telegram Web App is a web page that Telegram opens INSIDE the chat. It
arrives authenticated: the `initData` query string carries a signature the
server can check, and that signature is the only reason the page may read
anything at all.

WHY THE BOT SERVES IT, AND NOT THE HARNESS: the validation key is derived
from the BOT TOKEN (`HMAC_SHA256(bot_token, "WebAppData")`). The bot is the
only component that holds the token — the harness holds a model key and the
store's door, and giving it the bot token would make it able to speak as the
owner. So the bot validates, and the harness is asked for the DATA.

WHY THE PAGE NEVER TALKS TO THE STORE: the Mini App is a projection
(ADR-037 D8). It reads through the same six tools every other client uses,
and it writes through none of them. A browser that opened a database would
be a second writer with a screen.

WHAT IT SHOWS: the session the agent is in, the questions it is waiting on
(answered from here, with the same buttons the chat has), the log of what
the agent did, and the artefacts the store holds. One panel for the things
that are too big or too structured for a chat message — and NOT a second
place where the truth lives.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

__all__ = ["MiniAppError", "create_app", "validate_init_data"]

#: The page. It ships with the image (`src/` is copied), so the Mini App is
#: never a deployment that depends on a file somebody forgot to upload.
PAGE = Path(__file__).with_name("index.html")

#: How old an `initData` may be. Telegram's signature does not expire on its
#: own: a captured one would be valid forever, so the window is enforced
#: here. A day is long enough for a panel opened in the morning and long
#: enough to be useless to a thief.
MAX_AGE_S = 24 * 60 * 60


class MiniAppError(Exception):
    """The Mini App did not prove who it is."""


def validate_init_data(
    init_data: str,
    token: str,
    max_age_s: int = MAX_AGE_S,
    now: float | None = None,
) -> dict[str, str]:
    """Check the `initData` Telegram handed the page.

    The method is Telegram's own: the secret key is
    `HMAC_SHA256(bot_token, "WebAppData")`, the data-check string is every
    received field sorted by name and joined with newlines, and the check is
    its HMAC-SHA256.

    The `hash` field is always excluded — it IS the check. The `signature`
    field (the third-party Ed25519 path) is excluded too, and BOTH readings
    are accepted: Telegram's documentation describes the check string with
    and without it, and a check that rejects a payload Telegram actually
    sent is a bot that cannot open its own panel. Accepting both is not a
    hole: the hash can only be produced with the bot's token, so every
    accepted payload was signed by this bot either way.

    The freshness window is ours, and it is not optional: without it the
    signature is a bearer token with no expiry.
    """
    fields = dict(parse_qsl(init_data or "", keep_blank_values=True))
    received = fields.pop("hash", "")
    signature = fields.pop("signature", None)
    if not received:
        raise MiniAppError("the initData carries no hash")
    if not token:
        raise MiniAppError("this bot has no token to validate with")

    secret = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()

    def _check(parts: dict[str, str]) -> str:
        check_string = "\n".join(f"{key}={parts[key]}" for key in sorted(parts))
        return hmac.new(secret, check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    expected = _check(fields)
    if signature is not None:
        expected_with = _check({**fields, "signature": signature})
    else:
        expected_with = None
    if not (
        hmac.compare_digest(expected, received)
        or (expected_with is not None and hmac.compare_digest(expected_with, received))
    ):
        raise MiniAppError("the initData does not match this bot")

    try:
        auth_date = int(fields.get("auth_date", "0"))
    except ValueError as exc:
        raise MiniAppError("the initData has no usable auth_date") from exc
    moment = now if now is not None else time.time()
    if auth_date <= 0:
        raise MiniAppError("the initData has no auth_date")
    if moment - auth_date > max_age_s:
        raise MiniAppError("the initData is older than the window this bot accepts")

    return fields


def _client_key(user_id: str) -> str:
    """The routing key of the owner who opened the page.

    It is the SAME key the chat uses — `tg:<chat_id>` — because it is the
    same person: a Telegram account is one user, in one private chat with
    this bot.
    """
    return f"tg:{user_id}"


async def _body(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:
        raise MiniAppError("the body is not JSON") from exc
    if not isinstance(payload, dict):
        raise MiniAppError("the body is not an object")
    return payload


async def _session_view(bot: Any, client: str) -> dict[str, Any]:
    """What the panel shows: the session, the questions, the log, the store.

    Every part is read through a door that already exists: the harness for
    the agent's side, the api's MCP for the store's. The panel adds no new
    capability — it shows, in one place, what the chat shows in pieces.
    """
    harness = getattr(bot, "_harness", None)
    if harness is None:
        raise MiniAppError("this bot has no agent configured")

    session = await harness.session(client)
    page = await harness.events(client, since=0, limit=50)

    artifacts: list[dict[str, Any]] = []
    try:
        found = await bot._client.call("search_artifacts", {"query": {"limit": 12}})
        for item in (found or {}).get("artifacts") or []:
            artifacts.append(
                {
                    "uid": str(item.get("uid") or ""),
                    "kind": str(item.get("kind") or ""),
                    "title": str(item.get("title") or ""),
                }
            )
    except Exception:
        # The store being unreachable must not empty the panel: the agent's
        # side is still worth showing.
        artifacts = []

    return {
        "ok": True,
        "session": {
            "id": str(session.get("session_id") or ""),
            "client": client,
            "runtime": session.get("runtime") or {},
        },
        "questions": session.get("questions") or [],
        "events": page.get("events") or [],
        "artifacts": artifacts,
    }


def create_app(bot: Any) -> Starlette:
    """The Mini App's HTTP surface.

    It is mounted INSIDE the bot's process, on its own port: the bot is the
    only holder of the token, and the token is what the page's identity is
    made of.
    """

    async def page(request: Request) -> HTMLResponse:
        try:
            html = PAGE.read_text(encoding="utf-8")
        except OSError:
            return HTMLResponse("<h1>o painel não está instalado</h1>", status_code=500)
        return HTMLResponse(html)

    async def session(request: Request) -> JSONResponse:
        try:
            payload = await _body(request)
            fields = validate_init_data(str(payload.get("init_data") or ""), bot._token)
            user = fields.get("user") or ""
            # The `user` field is a JSON string; the id is what routes.
            user_id = str(_user_id(user))
            if not user_id:
                raise MiniAppError("the initData carries no user")
            if user_id not in bot._allowed:
                # Fail closed, like every other door of this bot: an unlisted
                # account learns nothing about what is there.
                raise MiniAppError("this account is not allowed here")
            view = await _session_view(bot, _client_key(user_id))
        except MiniAppError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=401)
        except Exception as exc:  # a panel that breaks is not a crash
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
        return JSONResponse(view)

    async def answer(request: Request) -> JSONResponse:
        try:
            payload = await _body(request)
            fields = validate_init_data(str(payload.get("init_data") or ""), bot._token)
            user_id = str(_user_id(fields.get("user") or ""))
            if not user_id or user_id not in bot._allowed:
                raise MiniAppError("this account is not allowed here")
            harness = getattr(bot, "_harness", None)
            if harness is None:
                raise MiniAppError("this bot has no agent configured")
            question_id = str(payload.get("question_id") or "")
            if not question_id:
                raise MiniAppError("no question to answer")
            if payload.get("option_index") is not None:
                out = await harness.answer(question_id, option_index=int(payload["option_index"]))
            else:
                out = await harness.answer(question_id, value=str(payload.get("value") or ""))
        except MiniAppError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=401)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
        return JSONResponse({"ok": True, "question": out.get("question") or {}})

    return Starlette(
        routes=[
            Route("/", page, methods=["GET"]),
            Route("/api/session", session, methods=["POST"]),
            Route("/api/answer", answer, methods=["POST"]),
        ]
    )


def _user_id(raw: str) -> str:
    """The id inside the `user` field of the initData.

    Telegram sends it as a JSON string. A field that is not JSON, or that
    has no id, is an empty id — and an empty id is refused by the caller.
    """
    import json

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return ""
    if not isinstance(parsed, dict):
        return ""
    return str(parsed.get("id") or "")
