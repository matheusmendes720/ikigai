"""The Mini App: the page's identity, and the door it opens.

`initData` is the only reason the page may read anything. Two things can go
wrong with it, and both are silent in production: a FORGED signature (somebody
replaying a captured payload) and a STALE one (a payload captured last week is
still a valid signature forever). So both are checked here, against the
method Telegram documents.

The tests build the hash the way Telegram does — HMAC-SHA256 with the secret
key derived from the bot token — so they test the CHECK, not a copy of it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

import pytest
from starlette.testclient import TestClient

from src.bot.miniapp import MiniAppError, create_app, validate_init_data

TOKEN = "123456:TEST-TOKEN"


def _sign(fields: dict[str, str], token: str = TOKEN, with_signature: bool = False) -> str:
    """The hash Telegram would send, for these fields.

    `with_signature` builds the OTHER reading of the check string — the one
    that keeps the `signature` field — because Telegram's documentation
    describes both and the bot must accept whichever one Telegram sent.
    """
    secret = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    parts = dict(fields)
    if with_signature:
        parts["signature"] = fields.get("signature", "")
    check_string = "\n".join(f"{key}={parts[key]}" for key in sorted(parts))
    return hmac.new(secret, check_string.encode("utf-8"), hashlib.sha256).hexdigest()


def _init_data(
    user_id: str = "9138296750",
    auth_date: int | None = None,
    token: str = TOKEN,
    extra: dict[str, str] | None = None,
) -> str:
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps({"id": user_id, "first_name": "Matheus"}),
    }
    if extra:
        fields.update(extra)
    fields["hash"] = _sign(fields, token)
    return urlencode(fields)


def test_a_correct_signature_is_accepted() -> None:
    fields = validate_init_data(_init_data(), TOKEN)
    assert json.loads(fields["user"])["id"] == "9138296750"


def test_a_forged_signature_is_refused() -> None:
    """Somebody replaying a captured payload: the hash is not ours."""
    data = _init_data()
    tampered = data.replace("9138296750", "9999999999")
    with pytest.raises(MiniAppError):
        validate_init_data(tampered, TOKEN)


def test_a_hash_of_another_bot_is_refused() -> None:
    """The same payload, signed with a different bot's token."""
    data = _init_data(token="999:OTHER")
    with pytest.raises(MiniAppError):
        validate_init_data(data, TOKEN)


def test_a_stale_payload_is_refused() -> None:
    """Telegram's signature does not expire on its own. The window is ours."""
    old = int(time.time()) - 48 * 60 * 60
    with pytest.raises(MiniAppError):
        validate_init_data(_init_data(auth_date=old), TOKEN)


def test_a_payload_without_a_hash_is_refused() -> None:
    with pytest.raises(MiniAppError):
        validate_init_data("auth_date=1&user=%7B%7D", TOKEN)


def test_the_third_party_signature_field_is_ignored() -> None:
    """The Ed25519 field belongs to a validation method this bot does not use.
    It must not break the HMAC one — and the check string is accepted with
    AND without it, because Telegram's documentation describes both."""
    fields = {"auth_date": "1", "user": json.dumps({"id": "1"}), "signature": "not-ours"}
    without = _sign(fields)
    with_it = _sign(fields, with_signature=True)
    for payload_hash in (without, with_it):
        data = urlencode({**fields, "hash": payload_hash})
        assert validate_init_data(data, TOKEN, now=1.0)["auth_date"] == "1"


class _FakeHarness:
    def __init__(self) -> None:
        self.answered: list[tuple[str, Any]] = []

    async def session(self, client: str) -> dict[str, Any]:
        return {
            "session_id": "tg-9138296750",
            "runtime": {"id": "owner", "label": "Owner", "provider": "harness"},
            "questions": [
                {
                    "id": "a1b2c3",
                    "kind": "choice",
                    "question": "Nota ou sonho?",
                    "options": ["nota", "sonho"],
                    "state": "pending",
                }
            ],
        }

    async def events(self, session: str, since: int = 0, limit: int = 200) -> dict[str, Any]:
        return {"events": [], "tip": 0, "floor": 0}

    async def answer(
        self,
        question_id: str,
        value: str | None = None,
        option_index: int | None = None,
    ) -> dict[str, Any]:
        self.answered.append((question_id, option_index if option_index is not None else value))
        return {"ok": True, "question": {"id": question_id, "state": "answered"}}


class _FakeStore:
    async def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"artifacts": [{"uid": "ikigai.nota.abc", "kind": "NOTA", "title": "Hoje"}]}


class _FakeBot:
    def __init__(self) -> None:
        self._token = TOKEN
        self._allowed = {"9138296750"}
        self._harness = _FakeHarness()
        self._client = _FakeStore()


def test_the_page_is_served() -> None:
    client = TestClient(create_app(_FakeBot()))
    response = client.get("/")
    assert response.status_code == 200
    assert "<html" in response.text.lower()


def test_the_session_is_read_through_the_doors_that_exist() -> None:
    client = TestClient(create_app(_FakeBot()))
    response = client.post("/api/session", json={"init_data": _init_data()})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["session"]["id"] == "tg-9138296750"
    assert body["questions"][0]["question"] == "Nota ou sonho?"
    assert body["artifacts"][0]["uid"] == "ikigai.nota.abc"


def test_a_forged_page_reads_nothing() -> None:
    bot = _FakeBot()
    client = TestClient(create_app(bot))
    response = client.post("/api/session", json={"init_data": "auth_date=1&hash=nope"})
    assert response.status_code == 401
    assert response.json()["ok"] is False


def test_an_account_outside_the_allowlist_reads_nothing() -> None:
    """Fail closed, like every other door of this bot."""
    client = TestClient(create_app(_FakeBot()))
    response = client.post("/api/session", json={"init_data": _init_data(user_id="999")})
    assert response.status_code == 401


def test_answering_from_the_panel_reaches_the_runtime() -> None:
    bot = _FakeBot()
    client = TestClient(create_app(bot))
    response = client.post(
        "/api/answer",
        json={"init_data": _init_data(), "question_id": "a1b2c3", "option_index": 1},
    )
    assert response.status_code == 200
    assert bot._harness.answered == [("a1b2c3", 1)]


def test_a_typed_answer_reaches_the_runtime() -> None:
    bot = _FakeBot()
    client = TestClient(create_app(bot))
    response = client.post(
        "/api/answer",
        json={"init_data": _init_data(), "question_id": "a1b2c3", "value": "sonho"},
    )
    assert response.status_code == 200
    assert bot._harness.answered == [("a1b2c3", "sonho")]
