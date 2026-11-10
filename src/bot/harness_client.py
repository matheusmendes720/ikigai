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
#:
#: It has to be at least as long as the harness's own margin
#: (`HARNESS_REQUEST_MARGIN_MS`, 60 s), or the bot's socket gives up BEFORE
#: the harness's — and the owner is told the routine failed while the agent
#: is still working on it.
TIMEOUT_MARGIN_S = 90.0

#: The default ceiling of a routine, in seconds. It is the harness's own
#: default (`HARNESS_TIMEOUT_MS`, 1800000 ms = the owner's question ceiling
#: plus the room the agent needs to write the artifact): the two agree on who
#: gives up first — the agent, not the socket.
DEFAULT_TIMEOUT_S = 1800.0

#: The ceiling of a STOP, in seconds. A stop that takes longer than the
#: owner's patience is a stop that did not happen: the gate is two seconds,
#: and this is the bot's half of that budget.
CANCEL_TIMEOUT_S = 5.0


class HarnessError(RuntimeError):
    """The harness refused the routine, or was not there at all.

    The message is what the owner reads when a routine dies, so it names the
    cause the harness gave — not "something went wrong".

    The STATUS is the other half, and it is what tells a REFUSAL from a
    FAILURE: a busy session answers 409 (a conflict with the state of the
    session), and the request is fine — it just has to wait for the turn that
    is running. "A rotina foi recusada" and "a rotina falhou" are different
    sentences, and the owner acts differently on each.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


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
        client: str | None = None,
        client_run_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a routine and wait for the agent's report.

        The session id is the agent's conversation: two chats are two
        conversations and cannot share one context. The harness sanitises it
        on arrival and on the way out, so the caller may send the raw key it
        has — a Telegram chat id, a composite — and still find what the
        agent remembered.

        `client` is the ROUTING key: the harness decides which agentic runtime
        answers it. It is the same key as the session, today — `tg:<chat_id>`
        — but it is sent separately because the two are different things: the
        session is the conversation, the client is the door.

        `client_run_id` NAMES this run. A chat is one session, so every
        routine the owner starts in it shares the session key — and a Stop
        from a preview that is already over would land on the NEXT routine of
        that chat and kill it. The name is what says which run a stop means.
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
        if client:
            payload["client"] = client
        if context:
            payload["context"] = context
        if client_run_id:
            payload["client_run_id"] = client_run_id
        return await self._post("/v1/routine", payload)

    async def cancel_routine(
        self,
        session_id: str,
        *,
        client_run_id: str | None = None,
        timeout_s: float = CANCEL_TIMEOUT_S,
    ) -> dict[str, Any]:
        """Stop a routine that is running.

        The bot's wait is NOT the work: the agent is a `pi` process with the
        store open, and it keeps working — and keeps writing — after the bot
        stops listening. So a stop has to reach the harness, or the owner
        cancels a routine that goes on to write the note they cancelled.

        `client_run_id` names the run to stop, and it is the same name the
        run was started with. Without it, a stop that arrives late would
        stop whatever this session happens to be running — which, in a chat
        that runs a routine every night, is the NEXT one.

        The answer says whether there WAS something to stop: a stop that
        arrives after the run is over cancels nothing, and the owner is told
        so rather than being given a stop that stopped nothing.
        """
        payload: dict[str, Any] = {"session_id": session_id}
        if client_run_id:
            payload["client_run_id"] = client_run_id
        return await self._post("/v1/routine/cancel", payload, timeout_s=timeout_s)

    async def route(self, client: str, timeout_s: float | None = None) -> dict[str, Any]:
        """Which runtime answers this client.

        The answer is a runtime and a reason: a client that was routed by a
        rule and a client that fell back to the default are both answers, and
        only one of them is a decision somebody made.
        """
        path = f"/v1/routing?client={quote(client)}"
        return await self._get(path, timeout_s=timeout_s)

    async def session(self, client: str, timeout_s: float | None = None) -> dict[str, Any]:
        """The session of a client: its id, its runtime, and what it owes.

        The pending questions are here, so a client that restarted can show
        the owner what is still waiting instead of a chat that went quiet.
        """
        path = f"/v1/session?client={quote(client)}"
        return await self._get(path, timeout_s=timeout_s)

    async def events(
        self,
        session: str,
        since: int = 0,
        limit: int = 200,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """The agent's event log, FORWARD, from a cursor.

        The same shape as the store's change feed (ADR-039): the client says
        what it has and gets what it does not, in order. The agent's side
        carries the questions it asked and the answers it got.
        """
        path = f"/v1/events?session={quote(session)}&since={int(since)}&limit={int(limit)}"
        return await self._get(path, timeout_s=timeout_s)

    async def question(self, question_id: str, timeout_s: float | None = None) -> dict[str, Any]:
        """The state of one question the agent asked.

        `pending`, `answered` or `expired`. It is how the client knows a
        question is still worth drawing: a question that was answered, or
        that ran out of time, must not be shown again.
        """
        path = f"/v1/owner/answer?question_id={quote(question_id)}"
        return await self._get(path, timeout_s=timeout_s)

    async def answer(
        self,
        question_id: str,
        value: str | None = None,
        option_index: int | None = None,
    ) -> dict[str, Any]:
        """The owner's answer, and the agent's turn continues.

        The answer travels as the TEXT the owner typed, or as the INDEX of
        the option the owner picked — a channel's button payload is capped at
        64 bytes, and the option's text belongs to the runtime anyway.
        """
        payload: dict[str, Any] = {"question_id": question_id}
        if option_index is not None:
            payload["option_index"] = int(option_index)
        else:
            payload["value"] = "" if value is None else value
        return await self._post("/v1/owner/answer", payload)

    async def routines(self, timeout_s: float | None = None) -> list[str]:
        """The routines the harness published — the projection it reads.

        `timeout_s` bounds THIS call: the handshake that greets the owner
        must not hang for the length of a routine when the agent is down.
        """
        body = await self._get("/v1/routines", timeout_s=timeout_s)
        items = body.get("routines") or []
        return [str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")]

    async def memory(
        self,
        session: str,
        limit: int = 20,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """What the agent remembers about a session.

        The session key is sanitised on both ends, so the caller sends the
        same raw key it sent when it ran the routine.
        """
        path = f"/v1/memory?session={quote(session)}&limit={limit}"
        return await self._get(path, timeout_s=timeout_s)

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._http.post(
                f"{self._base}{path}",
                json=payload,
                timeout=httpx.Timeout(timeout_s) if timeout_s is not None else None,
            )
        except httpx.HTTPError as exc:
            raise HarnessError(f"the harness did not answer: {exc}") from exc
        return self._body(response, path)

    async def _get(self, path: str, timeout_s: float | None = None) -> dict[str, Any]:
        try:
            response = await self._http.get(
                f"{self._base}{path}",
                timeout=httpx.Timeout(timeout_s) if timeout_s is not None else None,
            )
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
            raise HarnessError(
                f"{error} ({detail})" if detail else error,
                status=response.status_code,
            )
        return body
