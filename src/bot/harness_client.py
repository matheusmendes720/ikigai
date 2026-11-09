"""The bot's door to the harness — the agent, over HTTP.

The bot is a CLIENT of the api (ADR-037 D6): it speaks MCP and never opens a
database. The agent is a client too, but of a different kind — it is an
external process (`pi`, ADR-037 D7) that the harness facade puts behind an
HTTP door, and the facade lives in `deploy/`, outside the published tree.

So the bot has TWO doors, and they are not interchangeable:

* the api's MCP — the DOM: what the store holds, and the only way to write it;
* the harness's HTTP — the AGENT: a routine that reads the DOM, decides, and
  writes back through the api.

Reaching the second door does not make the bot an orchestrator. It asks for a
routine, it waits, and it reports what the agent said. The routine itself is
the agent's work, and the agent writes through the api like every other
client — so there is still ONE writer per store (ADR-037 D5).

WHY NOT A TOOL ON THE API: the api's surface is exactly six tools, it is
drift-guarded, and a seventh is a CONTRACT CHANGE (ADR-011), not a
convenience. It would also make the canonical service depend on the agent's
availability and on the agent's vocabulary — which is what "the agent is
external" forbids. The agent is reached from the CLIENT, and the client is
where the owner's intent lives.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

#: The margin between the run's ceiling and the socket's patience. The
#: harness bounds the run; this waits a little longer, so a run that hits its
#: ceiling comes back as the harness's answer and not as a timeout here.
TIMEOUT_MARGIN_S = 30.0

#: The default ceiling of a routine, in seconds. It is the harness's own
#: default (`HARNESS_TIMEOUT_MS`, 600000 ms): the two agree on who gives up
#: first — the agent, not the socket.
DEFAULT_TIMEOUT_S = 600.0


class HarnessError(RuntimeError):
    """The harness refused the routine, or was not there at all.

    The message is what the owner reads when a routine dies, so it names the
    cause the harness gave — not "something went wrong".
    """


class HarnessClient:
    """A thin client over the harness facade.

    It speaks HTTP, not MCP: the harness is not the api and does not speak
    the api's protocol. The one thing the two share is the shape of a
    routine — a name, a session, the owner's own words — and the answer is
    the agent's report.
    """

    def __init__(self, base_url: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self._base = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_s + TIMEOUT_MARGIN_S),
        )

    async def run_routine(
        self,
        routine: str,
        *,
        session_id: str,
        chat_id: str,
        message: str = "",
        context: dict[str, Any] | None = None,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Run a routine and wait for the agent's report.

        The session id is the agent's conversation: two chats are two
        conversations and cannot share one context. The harness sanitises it
        on arrival and on the way out, so the caller may send the raw key it
        has — a Telegram chat id, a composite — and still find what the
        agent remembered.
        """
        payload: dict[str, Any] = {
            "routine": routine,
            "session_id": session_id,
            "chat_id": chat_id,
            "message": message,
            # The harness bounds the run with the same ceiling this client
            # waits for. The run is the agent's to end, not the socket's.
            "timeout_ms": int(self._timeout_s * 1000),
        }
        if date:
            payload["date"] = date
        if context:
            payload["context"] = context
        return await self._post("/v1/routine", payload)

    async def routines(self) -> list[str]:
        """The routines the harness published — the projection it reads."""
        body = await self._get("/v1/routines")
        items = body.get("routines") or []
        return [str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")]

    async def memory(self, session: str, limit: int = 20) -> dict[str, Any]:
        """What the agent remembers about a session.

        The session key is sanitised on both ends, so the caller sends the
        same raw key it sent when it ran the routine.
        """
        path = f"/v1/memory?session={quote(session)}&limit={limit}"
        return await self._get(path)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._http.post(f"{self._base}{path}", json=payload)
        except httpx.HTTPError as exc:
            raise HarnessError(f"the harness did not answer: {exc}") from exc
        return self._body(response, path)

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            response = await self._http.get(f"{self._base}{path}")
        except httpx.HTTPError as exc:
            raise HarnessError(f"the harness did not answer: {exc}") from exc
        return self._body(response, path)

    def _body(self, response: httpx.Response, path: str) -> dict[str, Any]:
        """The harness's answer, or the reason it refused.

        A refusal is a body too: the harness answers an unknown routine with
        the list of the ones it knows, and a failed run with the reason it
        failed. Both are more useful to the owner than a status code.
        """
        try:
            body = response.json()
        except ValueError as exc:
            raise HarnessError(
                f"the harness answered {path} with something that is not JSON"
            ) from exc
        if not isinstance(body, dict):
            raise HarnessError(f"the harness answered {path} with something that is not an object")
        if response.status_code >= 400:
            error = str(body.get("error") or f"HTTP {response.status_code}")
            detail = str(body.get("detail") or "").strip()
            raise HarnessError(f"{error} ({detail})" if detail else error)
        return body
