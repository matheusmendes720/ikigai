"""Pydantic v2 strict models for chat thread (decision #3)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_UEID_RE = re.compile(r"^[a-z]{2,10}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")


class _ProposalStatusEnum(StrEnum):
    """StrEnum so callers can use `ProposalStatus.OPEN`.

    Pydantic v2 happily coerces StrEnum values into Literal string fields via
    the enum's `.value`. The legacy Literal lives on below for serialization
    helpers if needed.
    """

    DRAFT = "draft"
    OPEN = "OPEN"
    SEMI = "semi"
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    CLOSED = "CLOSED"


ProposalStatus = _ProposalStatusEnum
"""Public ProposalStatus alias — StrEnum, so `ProposalStatus.OPEN` works
and `is ProposalStatus.OPEN` survives across module reloads.
"""


_PROPOSAL_STATUS_LITERAL = Literal[
    "draft", "open", "semi", "ready", "approved", "rejected", "archived", "OPEN", "CLOSED"
]


# ---------------------------------------------------------------------------
# M58 (chat regression): Entry + EntryRole removed in a5b1146c but referenced
# by tests/test_chat_system.py. Re-introduced minimal here with same invariants
# as the rest of the chat package (frozen=True, extra='forbid', entity_type).
# ---------------------------------------------------------------------------


class EntryRole(StrEnum):
    """Speaker role for a chat entry (StrEnum so `is` survives)."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Entry(BaseModel):
    """A single chat entry: one message in a thread.

    `created_at` defaults to UTC now so tests/observability can rely on
    timezone-aware timestamps (tzinfo not None).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    thread_id: str
    role: EntryRole = EntryRole.USER
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entity_type: str = "entry"  # marker for tests asserted in M58


class Proposal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    thread_id: str
    action: str = "create_task"
    target_ueid: str = ""
    rationale: str = ""
    status: _ProposalStatusEnum = _ProposalStatusEnum.OPEN

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, v):
        # Accept StrEnum members, strings (case-sensitive), or plain str literals.
        # Coerce "open" -> _ProposalStatusEnum.OPEN, "OPEN" -> .OPEN, etc.
        from .schema import _ProposalStatusEnum as _PSE

        if hasattr(v, "value"):  # any StrEnum
            v = v.value
        if isinstance(v, str):
            for member in _PSE:
                if member.value == v:
                    return member
            # lowercased canonical
            return _PSE(v.lower())
        return v

    @field_validator("target_ueid")
    @classmethod
    def _validate_target_ueid(cls, v: str) -> str:
        if not v or _UEID_RE.match(v):
            return v
        raise ValueError(f"Invalid target_ueid: {v!r} must match 4-part UEID pattern")

    # Legacy alias — tests/100bdb0a-era code referenced proposal_id; keep both.
    @property
    def proposal_id(self) -> str:
        return self.id


class ChatThread(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    thread_id: str
    created_at: datetime
    profile_active: str = "ikigai-planner"
    soul_path: str = "src/ikigai/souls/ikigai-planner.md"
    title: str = ""
