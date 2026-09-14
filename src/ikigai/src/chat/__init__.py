"""Chat file-system package — Phase 7 (decision #3).

Persistent thread-backed chat between user and agent. Entries live in:

    vault/ikigai/runtime/chat/{thread_id}/{entry_id}.md
    vault/ikigai/runtime/chat/{thread_id}/proposals/{proposal_id}.md

Architecture:
    schema  → Pydantic v2 strict models (Entry, Proposal)
    writer  → atomic write to vault/ikigai/runtime/chat/{thread_id}/
    reader  → read_thread(thread_id) → ordered list of entries

The chat package is intentionally filesystem-backed (no DB) so that:
  1. All conversation history is browsable from Obsidian
  2. The append-only invariant of vault/ carries over (no deletes)
  3. The Drift net can audit writer.py the same way it audits vault_write
"""

from __future__ import annotations

from .schema import (
    CHAT_RUNTIME_DIR,
    Entry,
    EntryRole,
    Proposal,
    ProposalStatus,
)
from .writer import write_entry, write_proposal
from .reader import read_thread

__all__ = [
    "CHAT_RUNTIME_DIR",
    "Entry",
    "EntryRole",
    "Proposal",
    "ProposalStatus",
    "read_thread",
    "write_entry",
    "write_proposal",
]