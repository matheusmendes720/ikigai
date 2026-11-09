"""The draft: the message that exists while the work is happening.

Telegram's streaming replies (Bot API 10.x) give a bot one more surface than
a message: a **draft** — a preview the owner watches while the answer is being
generated, with a **Stop** button if the bot asked for one. The stop arrives
as an update (`stopped_message_generation`) and the bot's job is to cancel
the work behind it.

Three rules the API states, and the reason each one is here:

- **The draft is a PREVIEW.** It is ephemeral and disappears after about
  thirty seconds; it is not the message. The finished answer is sent with
  `sendMessage`/`sendRichMessage`, and that message is what replaces the
  preview. A bot that only sends drafts has sent nothing.
- **`draft_id` must be non-zero, and the SAME for the updates of one draft.**
  That is what makes them animate into each other instead of replacing one
  another. A new run gets a new id, so a fresh preview starts empty.
- **`can_stop` is what shows the button.** Without it there is no Stop, and
  without a Stop the owner's only way to cancel is to close the app.

And the one that is easy to get wrong: the preview is a **30-second** thing.
A routine that runs for two minutes loses its Stop button halfway through,
unless the bot keeps the draft alive by refreshing it. `REFRESH_S` is that
tick.
"""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["DRAFT_PREVIEW_S", "REFRESH_S", "Draft", "Drafts"]

#: How long the API keeps a preview alive. It is a preview, not a message.
DRAFT_PREVIEW_S = 30

#: How often the draft is refreshed while the work runs. Below the preview's
#: window, so the Stop button never disappears from under the owner's thumb.
REFRESH_S = 20

#: The API's own limit for `text` in `sendMessageDraft`.
MAX_TEXT = 4096

#: How many previews are remembered. A late Stop has to find the preview it
#: belongs to — so it cannot be forgotten the instant the work ends — but a
#: bot that runs for months must not keep them forever. The finished ones go
#: first: they are the ones nobody will press again.
MAX_REMEMBERED = 64


@dataclass
class Draft:
    """One preview, and the work behind it.

    `draft_id` is the handle Telegram gives back: the Stop update carries it,
    and it is how a stop finds the run it belongs to.
    """

    chat_id: str
    draft_id: int
    text: str = ""
    #: The task running the work this preview stands for. `None` until the
    #: caller attaches it — the preview opens a moment before the task does.
    task: Any = None
    #: Whether the owner may stop this one. A preview that cannot be stopped
    #: is a preview that only takes space.
    can_stop: bool = True
    #: Whether the work behind it is already over. A stop that arrives after
    #: this has nothing to stop — and cancelling then would cut the report
    #: in half, which is worse than a stop that did nothing.
    finished: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class Drafts:
    """The previews this bot is showing, and the calls behind them.

    It owns two things the rest of the bot must not: the ids (Telegram wants
    a non-zero integer, and the same one for the updates of one draft) and
    the shape of the payload.

    The TRANSPORT is not its own: `post` is the bot's, so the draft goes out
    through the same HTTP client as every other message — and a client that
    is replaced (in a test, or when the bot reconnects) is replaced for the
    draft too.
    """

    def __init__(
        self,
        post: Callable[[dict[str, Any]], Awaitable[bool]],
        base_id: int | None = None,
    ) -> None:
        self._post = post
        # A random base so that an id is not reused after a restart: a stale
        # Stop button from a previous process would otherwise land on the
        # draft that took the same number, and cancel the wrong run.
        self._next_id = base_id if base_id is not None else random.randint(1, 2_000_000_000)
        self._by_id: dict[int, Draft] = {}

    # -- the ids ------------------------------------------------------------

    def _mint(self) -> int:
        self._next_id += 1
        return self._next_id

    # -- the Telegram calls -------------------------------------------------

    async def open(self, chat_id: str, text: str, *, can_stop: bool = True) -> Draft | None:
        """Open a preview. `None` when Telegram refused it.

        A refusal is not an error the owner sees: a chat that is not private
        cannot have a draft, and the bot's answer has to work in every chat.
        The caller falls back to a message.
        """
        draft = Draft(chat_id=chat_id, draft_id=self._mint(), text=text, can_stop=can_stop)
        if not await self._send(draft, can_stop=can_stop):
            return None
        self._by_id[draft.draft_id] = draft
        self._prune()
        return draft

    async def refresh(self, draft: Draft, text: str | None = None) -> bool:
        """Keep the preview alive, and its Stop button with it.

        The same `draft_id` is sent again: that is what makes Telegram
        animate the new text into the old one instead of replacing it.
        """
        if text is not None:
            draft.text = text
        return await self._send(draft, can_stop=draft.can_stop)

    def _payload(self, draft: Draft, *, can_stop: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": _chat_id(draft.chat_id),
            "draft_id": int(draft.draft_id),
            "text": draft.text[:MAX_TEXT],
            # The draft stays in the chat when the owner stops it: what was
            # produced so far is worth reading, and the bot says what it did.
            "keep_on_stop": True,
        }
        if can_stop:
            payload["can_stop"] = True
        return payload

    async def _send(self, draft: Draft, *, can_stop: bool) -> bool:
        return await self._post(self._payload(draft, can_stop=can_stop))

    # -- the bookkeeping ----------------------------------------------------

    def find(self, draft_id: int) -> Draft | None:
        """The preview with that id — the one a Stop belongs to."""
        return self._by_id.get(int(draft_id))

    def _prune(self) -> None:
        """Forget the oldest finished previews, when there are too many.

        The finished ones go first: their work is over, and the only Stop
        that can still arrive for one is the owner pressing it too late —
        which is exactly the Stop that deserves an answer.
        """
        excess = len(self._by_id) - MAX_REMEMBERED
        if excess <= 0:
            return
        for draft in [d for d in self._by_id.values() if d.finished][:excess]:
            self._by_id.pop(draft.draft_id, None)

    def close(self, draft: Draft | None) -> None:
        """Forget a preview.

        The draft itself disappears on its own: Telegram owns its lifetime.
        What the bot owns is the mapping — a Stop that arrives after the work
        is over must find nothing, or it would cancel a run that is already
        gone.
        """
        if draft is None:
            return
        self._by_id.pop(draft.draft_id, None)

    def __len__(self) -> int:
        return len(self._by_id)


def _chat_id(chat_id: str) -> str | int:
    """The chat id the API wants.

    `sendMessageDraft` documents `chat_id` as an Integer. A private chat id
    IS an integer, and Telegram accepts the string form for the other
    methods this bot already uses — but the draft is a new method, so the
    number is sent as a number.
    """
    text = str(chat_id).strip()
    return int(text) if text.isdigit() else text
