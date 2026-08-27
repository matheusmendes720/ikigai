"""Tests for CheckpointAdapter — SA-03 replaces raw pickle at server.py:188-201."""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ikigai.adapters.checkpoint_adapter import CheckpointAdapter
from ikigai.entities.ikigai_record import IKIGAiRecord


@pytest.fixture
def tmp_db_dir() -> Path:
    """Manual tmpdir — sqlite3 on Windows holds a file lock briefly after
    connection close, which makes `tempfile.TemporaryDirectory` cleanup
    flaky. mkdtemp + ignore_errors is robust."""
    d = Path(tempfile.mkdtemp(prefix="checkpoint_adapter_test_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def record() -> IKIGAiRecord:
    return IKIGAiRecord.model_validate({
        "ueid": "ikigai:cycle:2026-08-26:00000001:00000001",
        "entity_type": "cycle",
        "slug": "2026-08-26",
        "title": "Cycle 2026-08-26",
        "status": "active",
        "created_at": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "source_md_path": Path("data/matheus/ikigai_state/cycle-2026-08-26.md"),
    })


def test_save_and_load_round_trip(tmp_db_dir: Path, record: IKIGAiRecord) -> None:
    cp_path = tmp_db_dir / "checkpoints.db"
    adapter = CheckpointAdapter(db_path=cp_path)
    adapter.save(record, thread_id="t1")
    loaded = adapter.load(thread_id="t1")
    assert loaded is not None
    assert loaded.ueid == record.ueid


def test_load_missing_returns_none(tmp_db_dir: Path) -> None:
    cp_path = tmp_db_dir / "checkpoints.db"
    adapter = CheckpointAdapter(db_path=cp_path)
    assert adapter.load(thread_id="missing") is None


def test_uses_json_plus_serializer_not_pickle(tmp_db_dir: Path, record: IKIGAiRecord) -> None:
    """SA-03: serialized form must NOT be raw pickle (no b'\\x80' header)."""
    import sqlite3
    cp_path = tmp_db_dir / "checkpoints.db"
    adapter = CheckpointAdapter(db_path=cp_path)
    adapter.save(record, thread_id="t1")

    conn = sqlite3.connect(str(cp_path))
    row = conn.execute("SELECT state_blob FROM checkpoints WHERE thread_id='t1'").fetchone()
    conn.close()
    assert row is not None
    blob = row[0]
    # TEXT storage; never raw pickle bytes
    if isinstance(blob, bytes):
        assert not blob.startswith(b"\x80"), "raw pickle detected"
        assert blob.startswith(b"{") or blob.startswith(b"[")
    else:
        # JSON envelope we wrote: starts with `{`
        assert blob.startswith("{")


def test_save_overwrites_existing(tmp_db_dir: Path, record: IKIGAiRecord) -> None:
    cp_path = tmp_db_dir / "checkpoints.db"
    adapter = CheckpointAdapter(db_path=cp_path)
    adapter.save(record, thread_id="t1")
    adapter.save(record, thread_id="t1")  # second save
    loaded = adapter.load(thread_id="t1")
    assert loaded is not None