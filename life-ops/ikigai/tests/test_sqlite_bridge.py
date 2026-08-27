"""Tests for IKIGAiRecordBridge — IKIGAiRecord → SQLiteAdapter.upsert.

Task 11 of data-model-unification: bridges the new polymorphic root
into the existing append-only SQLite mirror without mutating
SQLiteAdapter itself.

The bridge maps the polymorphic `entity_type`, vector scores (dict of
ScoreValue), regime fractal levels, and source path. Existing rows
created by PlanEntity.insert() remain untouched — the bridge only
upgrades the *write* path for IKIGAiRecord.
"""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ikigai.adapters.sqlite_bridge import IKIGAiRecordBridge
from ikigai.entities.ikigai_record import IKIGAiRecord, EntityType, StatusType
from ikigai.entities.score_value import ScoreUnit, ScoreValue
from ikigai.propagation.sqlite_adapter import SQLiteAdapter


@pytest.fixture
def tmp_db() -> Path:
    d = Path(tempfile.mkdtemp(prefix="bridge_test_"))
    try:
        yield d / "mirror.db"
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def record() -> IKIGAiRecord:
    return IKIGAiRecord.model_validate({
        "ueid": "ikigai:dream:2026-q3:00000001:00000001",
        "entity_type": "dream",
        "slug": "2026-q3",
        "title": "Close first remote role by Q3 2026",
        "description": "Land a remote BI/data role paying ≥R$12k/mo",
        "status": "active",
        "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 7, 15, tzinfo=timezone.utc),
        "source_md_path": Path("data/matheus/dreams/2026-q3.md"),
        "ikigai_vectors": ["passion", "skill", "market", "revenue"],
        "vector_scores": {
            "passion": ScoreValue(value=85.0, unit=ScoreUnit.PERCENT),
            "skill":   ScoreValue(value=70.0, unit=ScoreUnit.PERCENT),
            "market":  ScoreValue(value=55.0, unit=ScoreUnit.PERCENT),
            "revenue": ScoreValue(value=40.0, unit=ScoreUnit.PERCENT),
        },
        "is_placeholder": False,
    })


def test_bridge_inserts_row(tmp_db: Path, record: IKIGAiRecord) -> None:
    adapter = SQLiteAdapter(db_path=tmp_db)
    bridge = IKIGAiRecordBridge(adapter)
    bridge.upsert_ikigai_record(record)

    row = adapter.get_by_ueid(record.ueid)
    assert row is not None
    assert row["entity_type"] == "dream"
    assert row["title"] == "Close first remote role by Q3 2026"
    assert row["status"] == "active"


def test_bridge_maps_vector_scores_to_json_dict(tmp_db: Path, record: IKIGAiRecord) -> None:
    """`ikigai_vectors` is stored as a JSON object of float scores (legacy
    schema shape), NOT the polymorphic ScoreValue object."""
    adapter = SQLiteAdapter(db_path=tmp_db)
    bridge = IKIGAiRecordBridge(adapter)
    bridge.upsert_ikigai_record(record)

    import json
    row = adapter.get_by_ueid(record.ueid)
    assert row is not None
    vectors = json.loads(row["ikigai_vectors"])
    # Vectors stored as dict[str, float] normalised to 0..1 (legacy
    # upsert schema stores ratios; bridge uses ScoreValue.normalized)
    assert vectors["passion"] == pytest.approx(0.85)
    assert vectors["skill"] == pytest.approx(0.70)


def test_bridge_is_idempotent(tmp_db: Path, record: IKIGAiRecord) -> None:
    """Writing the same record twice produces the same row state (append-
    only; upsert drops+reinserts)."""
    adapter = SQLiteAdapter(db_path=tmp_db)
    bridge = IKIGAiRecordBridge(adapter)
    bridge.upsert_ikigai_record(record)
    bridge.upsert_ikigai_record(record)
    assert adapter.get_by_ueid(record.ueid) is not None
    # History should record both writes
    hist = adapter.history_for(record.ueid)
    assert len(hist) >= 2


def test_bridge_maps_source_md_path(tmp_db: Path, record: IKIGAiRecord) -> None:
    adapter = SQLiteAdapter(db_path=tmp_db)
    bridge = IKIGAiRecordBridge(adapter)
    bridge.upsert_ikigai_record(record)
    row = adapter.get_by_ueid(record.ueid)
    # source_md_path is stored as POSIX string per vault convention
    assert row["source_md_path"] == record.source_md_path.as_posix()


def test_bridge_accepts_polymorphic_entity_type(tmp_db: Path) -> None:
    """Exercise entity_type='cycle' (CYCLE per SPEC D7) — should land in
    the mirror with entity_type column = 'cycle'."""
    rec = IKIGAiRecord.model_validate({
        "ueid": "ikigai:cycle:2026-08-26:00000001:00000002",
        "entity_type": "cycle",
        "slug": "2026-08-26",
        "title": "Cycle 2026-08-26",
        "status": "active",
        "is_placeholder": True,
        "created_at": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "source_md_path": Path("data/matheus/ikigai_state/cycle-2026-08-26.md"),
    })
    adapter = SQLiteAdapter(db_path=tmp_db)
    bridge = IKIGAiRecordBridge(adapter)
    bridge.upsert_ikigai_record(rec)
    row = adapter.get_by_ueid(rec.ueid)
    assert row is not None
    assert row["entity_type"] == "cycle"
    assert row["is_placeholder"] == 1


def test_bridge_serializes_status(tmp_db: Path, record: IKIGAiRecord) -> None:
    adapter = SQLiteAdapter(db_path=tmp_db)
    bridge = IKIGAiRecordBridge(adapter)
    bridge.upsert_ikigai_record(record)
    row = adapter.get_by_ueid(record.ueid)
    assert row["status"] == "active"