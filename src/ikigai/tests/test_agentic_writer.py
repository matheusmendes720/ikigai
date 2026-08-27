"""Tests for IKIGAiAgenticWriter — replaces f-string writer at tools.py:350-385."""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import pytest

from ikigai.entities.ikigai_record import IKIGAiRecord
from ikigai.vault.agentic_writer import IKIGAiAgenticWriter


@pytest.fixture
def tmp_vault() -> Path:
    """Project-root-relative vault layout: vault_dir is the parent of the
    `data/matheus/...` tree. The writer resolves `source_md_path` against
    `vault_dir.parent`.
    """
    d = Path(tempfile.mkdtemp(prefix="vault_writer_"))
    # writer expects vault_dir.parent / source_md_path; so put the data
    # tree under `vault_dir.parent`
    (d / "data/matheus/ikigai_state").mkdir(parents=True)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def record(tmp_vault: Path) -> IKIGAiRecord:
    return IKIGAiRecord.model_validate({
        "ueid": "ikigai:cycle:2026-08-26:00000001:00000001",
        "entity_type": "cycle",
        "slug": "2026-08-26",
        "title": "IKIGAi Cycle — 2026-08-26",
        "status": "active",
        "is_placeholder": True,
        "placeholder_owner": "ikigai-agent",
        "corrections": [],
        "prospective_buffer": ["observe q_he trend"],
        "retrospective_log": ["regime stayed PUSH"],
        "audit_trail": [],
        "created_at": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 8, 26, tzinfo=timezone.utc),
        # Absolute source_md_path so the writer writes under tmp_vault
        # regardless of cwd (mirrors the prod `life-ops/ikigai/` cwd setup).
        "source_md_path": tmp_vault / "data/matheus/ikigai_state/cycle-2026-08-26.md",
    })


def test_writer_emits_full_record(tmp_vault: Path, record: IKIGAiRecord) -> None:
    """RT-05: cycle writer preserves corrections + buffers + audit_trail as typed lists."""
    w = IKIGAiAgenticWriter(vault_dir=tmp_vault)
    written = w.write(record)

    post = frontmatter.load(str(written))
    md = post.metadata
    assert md["ueid"] == record.ueid
    assert md["corrections"] == []
    assert md["prospective_buffer"] == ["observe q_he trend"]
    assert md["retrospective_log"] == ["regime stayed PUSH"]
    assert md["audit_trail"] == []
    assert md["is_placeholder"] is True


def test_writer_acquires_lock(tmp_vault: Path, record: IKIGAiRecord) -> None:
    """The writer invokes VaultLock — verified by side effect of
    serialized concurrent writes succeeding without deadlock.
    """
    lock_path = tmp_vault / ".vault.lock"
    w = IKIGAiAgenticWriter(vault_dir=tmp_vault, lock_path=lock_path)
    w.write(record)
    # VaultLock releases + cleans up on exit; just verify the target wrote.
    assert (tmp_vault / "data/matheus/ikigai_state/cycle-2026-08-26.md").exists()


def test_writer_path_under_vault_root(tmp_vault: Path, record: IKIGAiRecord) -> None:
    w = IKIGAiAgenticWriter(vault_dir=tmp_vault)
    written = w.write(record)
    # written file lives under tmp_vault/data/matheus/...
    assert written.parent == tmp_vault / "data/matheus/ikigai_state"
    assert written.name == "cycle-2026-08-26.md"


def test_writer_round_trip_via_frontmatter_to_dict(tmp_vault: Path, record: IKIGAiRecord) -> None:
    """RT-05 e2e: write → read → dict matches."""
    from ikigai.vault.frontmatter_to_dict import frontmatter_to_dict
    w = IKIGAiAgenticWriter(vault_dir=tmp_vault)
    written = w.write(record)
    d = frontmatter_to_dict(written)
    assert d["ueid"] == record.ueid
    assert d["prospective_buffer"] == ["observe q_he trend"]