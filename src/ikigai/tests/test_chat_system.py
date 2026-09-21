"""Tests for the chat file system (Phase 7 / decision #3).

Covers:
  1. Entry schema construction + frozen-forbid enforcement
  2. Proposal schema + UEID 4-part validation (the load-bearing validator)
  3. write_entry + write_proposal round-trip via read_thread
  4. read_thread returns [] for missing threads (no error)
  5. Atomic write integrity — no .tmp files left behind after success
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from src.ikigai.src.chat import (
    Entry,
    EntryRole,
    Proposal,
    ProposalStatus,
    read_thread,
    write_entry,
    write_proposal,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chat_root(tmp_path: Path) -> Path:
    """Isolated chat runtime dir per test.

    We pass this as `base_dir=` to writer/reader so no test touches the
    real `vault/ikigai/runtime/chat/`.
    """
    root = tmp_path / "chat"
    root.mkdir(parents=True, exist_ok=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _sample_ueid() -> str:
    """Return a canonical 4-part UEID matching UEID_PATTERN."""
    return "tsk:demo-task:11111111-2222-3333-4444-555555555555:abcdef0123456789"


# ---------------------------------------------------------------------------
# 1. Entry schema
# ---------------------------------------------------------------------------


def test_entry_schema_construction_and_frozen() -> None:
    """Entry builds from kwargs, rejects extra fields, and is frozen."""
    entry = Entry(
        id="thr-0001",
        thread_id="thr",
        role=EntryRole.USER,
        content="hello agent",
    )
    assert entry.role is EntryRole.USER
    assert entry.entity_type == "entry"
    assert entry.created_at.tzinfo is not None  # UTC-aware default
    assert entry.thread_id == "thr"

    # Frozen: assignment must raise.
    with pytest.raises((AttributeError, TypeError, ValueError)):
        entry.content = "tampered"  # type: ignore[misc]

    # extra="forbid": unknown field must raise at construction.
    with pytest.raises(ValueError, match="not_a_real_field"):
        Entry(
            id="thr-0002",
            thread_id="thr",
            role=EntryRole.USER,
            content="x",
            not_a_real_field=42,  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# 2. Proposal schema + UEID 4-part validation
# ---------------------------------------------------------------------------


def test_proposal_rejects_malformed_ueid() -> None:
    """Proposal's target_ueid field_validator rejects non-4-part UEIDs.

    This is the load-bearing test: drift detection relies on every
    `target_ueid` matching UEID_PATTERN, so a malformed value must
    fail at construction (not at write time).
    """
    # Wrong number of parts
    with pytest.raises(ValueError, match="Invalid target_ueid"):
        Proposal(
            id="thr-prop-0001",
            thread_id="thr",
            action="create_task",
            target_ueid="tsk:only:three",  # 3 parts
            rationale="bad",
        )

    # Uppercase type (regex requires [a-z]{2,5})
    with pytest.raises(ValueError, match="Invalid target_ueid"):
        Proposal(
            id="thr-prop-0002",
            thread_id="thr",
            action="create_task",
            target_ueid="TSK:foo:00000000-0000-0000-0000-000000000000:0000000000000000",
            rationale="bad",
        )

    # 5-part (legacy canonical) — must be rejected post-ADR-014
    with pytest.raises(ValueError, match="Invalid target_ueid"):
        Proposal(
            id="thr-prop-0003",
            thread_id="thr",
            action="create_task",
            target_ueid="ns:tsk:foo:00000000-0000-0000-0000-000000000000:0000000000000000",
            rationale="bad",
        )

    # Canonical 4-part passes
    p = Proposal(
        id="thr-prop-OK",
        thread_id="thr",
        action="create_task",
        target_ueid=_sample_ueid(),
        rationale="ok",
        status=ProposalStatus.OPEN,
    )
    assert p.status is ProposalStatus.OPEN
    assert p.target_ueid == _sample_ueid()


# ---------------------------------------------------------------------------
# 3. write_entry + write_proposal round-trip
# ---------------------------------------------------------------------------


def test_writer_reader_round_trip(chat_root: Path) -> None:
    """write_entry/write_proposal then read_thread → same data back."""
    thread_id = "thr-roundtrip"

    e1 = Entry(
        id=f"{thread_id}-0001",
        thread_id=thread_id,
        role=EntryRole.USER,
        content="first user message",
    )
    e2 = Entry(
        id=f"{thread_id}-0002",
        thread_id=thread_id,
        role=EntryRole.ASSISTANT,
        content="first assistant reply",
    )
    p1 = Proposal(
        id=f"{thread_id}-prop-0001",
        thread_id=thread_id,
        action="create_task",
        target_ueid=_sample_ueid(),
        rationale="because the user asked",
    )

    p1_path = write_proposal(p1, base_dir=chat_root)
    e1_path = write_entry(e1, base_dir=chat_root)
    e2_path = write_entry(e2, base_dir=chat_root)

    # Layout check
    assert p1_path == chat_root / thread_id / "proposals" / f"{thread_id}-prop-0001.md"
    assert e1_path == chat_root / thread_id / f"{thread_id}-0001.md"
    assert e2_path == chat_root / thread_id / f"{thread_id}-0002.md"
    assert p1_path.exists()
    assert e1_path.exists()
    assert e2_path.exists()

    entries, proposals = read_thread(thread_id, base_dir=chat_root)

    assert len(entries) == 2
    assert [e.id for e in entries] == [e1.id, e2.id]
    assert entries[0].role is EntryRole.USER
    assert entries[0].content == "first user message"
    assert entries[1].role is EntryRole.ASSISTANT
    assert entries[1].content == "first assistant reply"

    assert len(proposals) == 1
    assert proposals[0].id == p1.id
    assert proposals[0].action == "create_task"
    assert proposals[0].target_ueid == _sample_ueid()
    assert proposals[0].status is ProposalStatus.OPEN
    assert proposals[0].rationale == "because the user asked"


# ---------------------------------------------------------------------------
# 4. read_thread on missing thread
# ---------------------------------------------------------------------------


def test_read_thread_missing_returns_empty(chat_root: Path) -> None:
    """read_thread on a non-existent thread_id returns ([], []) — no error.

    The TUI/CLI consumer decides how to render an empty thread; the reader
    itself must not raise on a missing directory.
    """
    entries, proposals = read_thread("thr-that-was-never-written", base_dir=chat_root)
    assert entries == []
    assert proposals == []


# ---------------------------------------------------------------------------
# 5. Atomic write integrity
# ---------------------------------------------------------------------------


def test_atomic_write_leaves_no_tmp_files(chat_root: Path) -> None:
    """Successful writes never leave .tmp files behind.

    The writer uses `tempfile.mkstemp` + `os.replace`. If `os.replace`
    succeeds (which it must for the test to pass), the tmp file has been
    renamed — so a subsequent glob for `*.tmp` must be empty.
    """
    thread_id = "thr-atomic"
    write_entry(
        Entry(
            id=f"{thread_id}-0001",
            thread_id=thread_id,
            role=EntryRole.USER,
            content="x",
        ),
        base_dir=chat_root,
    )
    write_proposal(
        Proposal(
            id=f"{thread_id}-prop-0001",
            thread_id=thread_id,
            action="create_task",
            target_ueid=_sample_ueid(),
            rationale="atomic",
        ),
        base_dir=chat_root,
    )

    thread_dir = chat_root / thread_id
    proposals_dir = thread_dir / "proposals"

    # Walk every leaf under the thread dir; none should match *.tmp
    leftovers = list(thread_dir.rglob("*.tmp"))
    leftovers += list(proposals_dir.rglob("*.tmp")) if proposals_dir.exists() else []
    assert leftovers == [], f"atomic write left tmp files: {leftovers}"

    # Sanity: the real files are present
    assert (thread_dir / f"{thread_id}-0001.md").exists()
    assert (proposals_dir / f"{thread_id}-prop-0001.md").exists()
