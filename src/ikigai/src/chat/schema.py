"""Pydantic v2 strict schemas for the chat file system (Phase 7 / decision #3).

All models follow the project-wide convention:
    model_config = ConfigDict(frozen=True, extra="forbid")

`Proposal.target_ueid` validates the canonical 4-part UEID format
(`^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`) via a `field_validator`
because the chat layer cannot import `src.contracts.common.UEID` without
creating a new dependency edge into the planning contracts (chat is a
lower layer than planning).

The 4-part regex mirrors `src/contracts/common.py::_UEID_PATTERN` and is
the canonical post-ADR-014 format.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Repo root lives 4 levels up: src/ikigai/src/chat/schema.py → ../../../
_REPO_ROOT = Path(__file__).resolve().parents[3]

CHAT_RUNTIME_DIR: Path = _REPO_ROOT / "vault" / "ikigai" / "runtime" / "chat"
"""Canonical chat thread directory. Created on demand by writer.py."""

UEID_PATTERN = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")
"""4-part UEID format (post-ADR-014).

Mirrors `src/contracts/common.py::_UEID_PATTERN`. The chat package cannot
import `contracts.common.UEID` directly because that creates a dependency
edge into the planning contracts; chat is a strictly lower layer.
"""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EntryRole(StrEnum):
    """Speaker role for a chat entry."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProposalStatus(StrEnum):
    """Lifecycle state of an agent-authored proposal."""

    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Timezone-aware UTC now — used as default for all timestamps."""
    return datetime.now(timezone.utc)


class Entry(BaseModel):
    """A single chat message in a thread.

    Entries are append-only: once written to disk, the on-disk markdown
    file is never mutated. New replies become new files. Ordering is by
    `created_at` then `id` (lexicographic for ties).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(min_length=1, max_length=128)]
    """Unique within the thread. Convention: `{thread_id}-{seq:04d}`."""

    thread_id: Annotated[str, Field(min_length=1, max_length=128)]
    """Thread this entry belongs to. Maps 1:1 to a directory under CHAT_RUNTIME_DIR."""

    role: EntryRole
    """Speaker. `system` entries are agent-internal notes (not shown to user)."""

    content: Annotated[str, Field(min_length=1, max_length=100_000)]
    """Message body. Plain text or markdown."""

    created_at: datetime = Field(default_factory=_utcnow)
    """UTC timestamp. Timezone-aware (no naive datetimes)."""

    entity_type: Literal["entry"] = "entry"
    """Discriminator for deserialization."""


class Proposal(BaseModel):
    """An agent-authored proposal attached to a chat thread.

    Proposals are the agent's *output* — concrete suggestions for changes
    to the user's planning context (create a task, modify a project, etc.).
    `target_ueid` identifies the planning entity the proposal applies to
    (or will create, when the proposal is a `create` action).

    The 4-part UEID format is enforced via `field_validator` so a malformed
    UEID fails at validation time, not at write time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(min_length=1, max_length=128)]
    """Unique across all proposals. Convention: `{thread_id}-prop-{seq:04d}`."""

    thread_id: Annotated[str, Field(min_length=1, max_length=128)]
    """Thread that produced this proposal."""

    action: Annotated[str, Field(min_length=1, max_length=64)]
    """Verb describing the proposal. E.g. `create_task`, `update_project`, `archive_goal`."""

    target_ueid: Annotated[str, Field(min_length=1, max_length=256)]
    """UEID of the target planning entity. MUST match UEID_PATTERN (4-part canonical)."""

    rationale: Annotated[str, Field(max_length=10_000)] = ""
    """Plain-text reasoning the agent gives the user for this proposal."""

    status: ProposalStatus = ProposalStatus.OPEN
    """Lifecycle. New proposals start OPEN; user may ACCEPT/REJECT via TUI/CLI."""

    created_at: datetime = Field(default_factory=_utcnow)
    """UTC timestamp."""

    entity_type: Literal["proposal"] = "proposal"
    """Discriminator for deserialization."""

    @field_validator("target_ueid")
    @classmethod
    def _validate_target_ueid(cls, v: str) -> str:
        """Enforce 4-part canonical UEID format.

        This is the load-bearing validation the task brief calls out —
        drift-detection depends on every `target_ueid` matching the same
        regex as `src/contracts/common.py::_UEID_PATTERN`.
        """
        if not UEID_PATTERN.match(v):
            raise ValueError(
                f"Invalid target_ueid '{v}'. Must match {UEID_PATTERN.pattern!r}. "
                "Format: type:slug:uuid:hash (4 parts, all lowercase)."
            )
        return v


__all__ = [
    "CHAT_RUNTIME_DIR",
    "Entry",
    "EntryRole",
    "Proposal",
    "ProposalStatus",
    "UEID_PATTERN",
]