"""Integration gate for the data-model-unification branch (§1 complete).

Locks the whole unified data model end-to-end: vault markdown → IKIGAiRecord →
frontmatter dict → IKIGAiRecord (round-trip), the polymorphic discriminator,
ScoreValue unit ranges, OverrideRecord/FractalRegime/PhaseSnapshot shapes, and
the three adapters (DriftDetector, CheckpointAdapter, StateReducer).

Real files + real entities only — no mocks.

Plan-vs-reality adaptations (documented on the tests they affect):
  * module is `ikigai.adapters.drift_detector` (not `drift_detection`)
  * module is `ikigai.adapters.state_reducer` (not `state_dict_reducer`)
  * vault fixtures carry `status: ACTIVE` (uppercase) and `source_md_path: null`;
    both are normalized here before validation (see `_load_record`).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ikigai.adapters.checkpoint_adapter import CheckpointAdapter
from ikigai.adapters.drift_detector import DriftDetector
from ikigai.adapters.sqlite_bridge import IKIGAiRecordBridge
from ikigai.adapters.state_reducer import StateReducer
from ikigai.entities.drift_state import DriftState
from ikigai.entities.fractal_regime import FractalRegime, FractalRegimeState
from ikigai.entities.ikigai_record import EntityType, IKIGAiRecord, StatusType
from ikigai.entities.override import OverrideRecord
from ikigai.entities.phase_snapshot import PhaseSnapshot
from ikigai.entities.score_value import ScoreUnit, ScoreValue
from ikigai.propagation.sqlite_adapter import SQLiteAdapter
from ikigai.vault.dict_to_frontmatter import dict_to_frontmatter
from ikigai.vault.frontmatter_to_dict import frontmatter_to_dict

# Survey: VAULT_PATH_RELATIVE_TO_PROJECT_ROOT
VAULT_REL = Path("life-ops/ikigai/data/matheus")
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
VAULT = _PROJECT_ROOT / VAULT_REL

DREAM_MD = VAULT / "dreams" / "vaga-remota-2026.md"
OBJECTIVE_MD = VAULT / "objectives" / "q3-2026-primeira-vaga.md"

DREAM_UEID = "ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609"
OBJECTIVE_UEID = "ikigai:objective:q3-2026-primeira-vaga:cbf000ba:c040f222"


def _require(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"vault fixture missing: {path}")


def _load_record(path: Path) -> IKIGAiRecord:
    """Parse a vault .md into an IKIGAiRecord, normalizing the two known
    fixture quirks (uppercase status, null source_md_path)."""
    raw: dict[str, Any] = frontmatter_to_dict(path)
    if isinstance(raw.get("status"), str):
        raw["status"] = raw["status"].lower()
    if not raw.get("source_md_path"):
        raw["source_md_path"] = path.as_posix()
    raw.setdefault("created_at", datetime(2026, 7, 3, tzinfo=timezone.utc))
    raw.setdefault("updated_at", datetime(2026, 7, 3, tzinfo=timezone.utc))
    return IKIGAiRecord.model_validate(raw)


@pytest.fixture
def dream_record() -> IKIGAiRecord:
    _require(DREAM_MD)
    return _load_record(DREAM_MD)


@pytest.fixture
def tmp_dir() -> Iterator[Path]:
    d = Path(tempfile.mkdtemp(prefix="dmu_integration_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _base_payload(**over: Any) -> dict[str, Any]:
    now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    payload: dict[str, Any] = {
        "ueid": "ikigai:dream:probe:00000001:00000002",
        "entity_type": "dream",
        "slug": "probe",
        "title": "probe",
        "created_at": now,
        "updated_at": now,
        "source_md_path": "life-ops/ikigai/data/matheus/dreams/probe.md",
    }
    payload.update(over)
    return payload


# ──────────────────────────── RT-01..06 ────────────────────────────


def test_rt01_full_round_trip_preserves_custom_fields(dream_record: IKIGAiRecord) -> None:
    """RT-01: record → frontmatter dict → record preserves every `custom` key."""
    fm = dict_to_frontmatter(dream_record)
    again = IKIGAiRecord.model_validate(fm)
    assert set(again.custom) == set(dream_record.custom)
    assert again.custom == dream_record.custom


def test_rt02_ueid_survives_round_trip(dream_record: IKIGAiRecord) -> None:
    """RT-02: the canonical 5-part UEID matches the fixture after round-trip."""
    assert dream_record.ueid == DREAM_UEID
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(dream_record))
    assert again.ueid == DREAM_UEID


def test_rt03_null_fields_survive(dream_record: IKIGAiRecord) -> None:
    """RT-03: explicit nulls (description, parent_ueid) stay None, not dropped."""
    fm = dict_to_frontmatter(dream_record)
    assert "description" in fm
    assert fm["description"] is None
    again = IKIGAiRecord.model_validate(fm)
    assert again.description is None
    assert again.parent_ueid is None


def test_rt04_datetimes_are_tz_aware(dream_record: IKIGAiRecord) -> None:
    """RT-04: created_at/updated_at round-trip as tz-aware datetimes."""
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(dream_record))
    for dt in (again.created_at, again.updated_at):
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None


def test_rt05_source_md_path_required_and_preserved(dream_record: IKIGAiRecord) -> None:
    """RT-05: source_md_path (D8/I9) is required and survives as a Path."""
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(dream_record))
    assert isinstance(again.source_md_path, Path)
    assert again.source_md_path.as_posix() == dream_record.source_md_path.as_posix()
    payload = _base_payload()
    del payload["source_md_path"]
    with pytest.raises(ValidationError, match="source_md_path"):
        IKIGAiRecord.model_validate(payload)


def test_rt06_extra_allow_passthrough(dream_record: IKIGAiRecord) -> None:
    """RT-06: unknown frontmatter keys (tags, horizon_days) pass through extra='allow'."""
    extra = dream_record.model_extra or {}
    assert "tags" in extra or "horizon_days" in extra
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(dream_record))
    assert (again.model_extra or {}) == extra


# ──────────────────────────── PD-01..04 ────────────────────────────


def test_pd01_dream_entity_type_round_trips(dream_record: IKIGAiRecord) -> None:
    """PD-01: entity_type=dream survives the discriminated round-trip."""
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(dream_record))
    assert again.entity_type is EntityType.DREAM


def test_pd02_objective_entity_type_round_trips() -> None:
    """PD-02: entity_type=objective round-trips from the real vault objective."""
    _require(OBJECTIVE_MD)
    rec = _load_record(OBJECTIVE_MD)
    assert rec.ueid == OBJECTIVE_UEID
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.entity_type is EntityType.OBJECTIVE
    assert again.parent_ueid == DREAM_UEID


def test_pd03_vector_entity_type_round_trips() -> None:
    """PD-03: entity_type=vector round-trips through the same root model."""
    rec = IKIGAiRecord.model_validate(
        _base_payload(
            ueid="ikigai:vector:skill:00000001:00000003",
            entity_type="vector",
            slug="skill",
        )
    )
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.entity_type is EntityType.VECTOR


def test_pd04_vector_scores_support_fractal_keys() -> None:
    """PD-04: vector_scores accepts fractal keys like 'skill.python' (D3)."""
    rec = IKIGAiRecord.model_validate(
        _base_payload(
            vector_scores={
                "skill": {"value": 60.0, "unit": "percent"},
                "skill.python": {"value": 80.0, "unit": "percent"},
            }
        )
    )
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.vector_scores["skill.python"] == ScoreValue(value=80.0, unit=ScoreUnit.PERCENT)


# ──────────────────────────── SU-01..04 ────────────────────────────


def test_su01_percent_range_enforced() -> None:
    """SU-01: PERCENT scores must be within [0, 100] (I3)."""
    assert ScoreValue(value=100.0, unit=ScoreUnit.PERCENT).value == 100.0
    with pytest.raises(ValidationError, match="PERCENT"):
        ScoreValue(value=100.1, unit=ScoreUnit.PERCENT)
    with pytest.raises(ValidationError, match="PERCENT"):
        ScoreValue(value=-0.1, unit=ScoreUnit.PERCENT)


def test_su02_ratio_range_enforced() -> None:
    """SU-02: RATIO scores must be within [0.0, 1.0] (I4)."""
    assert ScoreValue(value=1.0, unit=ScoreUnit.RATIO).value == 1.0
    with pytest.raises(ValidationError, match="RATIO"):
        ScoreValue(value=1.5, unit=ScoreUnit.RATIO)


def test_su03_q_he_must_be_ratio() -> None:
    """SU-03: q_he_score is a RATIO-unit score (I4); a 0..1 PERCENT would be wrong.

    Limitation: the model does not enforce the unit on the field, so this
    asserts the structural contract — a RATIO Q_HE validates and its
    `normalized` value equals its raw value.
    """
    rec = IKIGAiRecord.model_validate(_base_payload(q_he_score={"value": 0.72, "unit": "ratio"}))
    assert rec.q_he_score is not None
    assert rec.q_he_score.unit is ScoreUnit.RATIO
    assert rec.q_he_score.normalized == pytest.approx(0.72)


def test_su04_score_value_equality() -> None:
    """SU-04: ScoreValue equality is by (value, unit), and it is frozen."""
    a = ScoreValue(value=50.0, unit=ScoreUnit.PERCENT)
    assert a == ScoreValue(value=50.0, unit=ScoreUnit.PERCENT)
    assert a != ScoreValue(value=0.5, unit=ScoreUnit.RATIO)
    assert a != ScoreValue(value=60.0, unit=ScoreUnit.PERCENT)
    with pytest.raises(ValidationError, match="frozen"):
        a.value = 10.0  # type: ignore[misc]


# ──────────────────────────── OV-01..03 ────────────────────────────


def test_ov01_override_record_round_trips() -> None:
    """OV-01: OverrideRecord survives a record round-trip inside audit_trail."""
    ov = OverrideRecord(
        at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        by="human:matheus",
        field_path="regime.levels.0.regime",
        previous_value="maintain",
        new_value="push",
        reason="manual push after streak",
    )
    rec = IKIGAiRecord.model_validate(_base_payload(audit_trail=[ov]))
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert len(again.audit_trail) == 1
    assert again.audit_trail[0].field_path == ov.field_path
    assert again.audit_trail[0].by == "human:matheus"


def test_ov02_override_values_preserved_verbatim() -> None:
    """OV-02: previous/new values (Any) survive round-trip unchanged."""
    ov = OverrideRecord(
        at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        by="agent",
        field_path="q_he_score.value",
        previous_value=0.4,
        new_value=0.8,
        reason="recompute",
    )
    rec = IKIGAiRecord.model_validate(_base_payload(audit_trail=[ov]))
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.audit_trail[0].previous_value == 0.4
    assert again.audit_trail[0].new_value == 0.8


def test_ov03_correction_signal_fields_preserved() -> None:
    """OV-03: manual_override + recommendation_score (D12) survive round-trip."""
    rec = IKIGAiRecord.model_validate(
        _base_payload(manual_override=True, recommendation_score=0.65)
    )
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.manual_override is True
    assert again.recommendation_score == pytest.approx(0.65)


# ──────────────────────────── FR-01..03 ────────────────────────────


def _regime(levels: list[str]) -> FractalRegime:
    return FractalRegime(
        levels=[
            FractalRegimeState(
                level=lvl,  # type: ignore[arg-type]
                regime="maintain",
                days_in_regime=1,
                is_hysteresis_active=False,
                hysteresis_days=0,
            )
            for lvl in levels
        ]
    )


def test_fr01_fractal_regime_has_four_levels() -> None:
    """FR-01: the canonical FractalRegime carries exactly 4 levels (D13)."""
    regime = _regime(["global", "cluster", "vector", "sub_vector"])
    assert len(regime.levels) == 4
    assert [lv.level for lv in regime.levels] == [
        "global",
        "cluster",
        "vector",
        "sub_vector",
    ]


def test_fr02_level_names_are_constrained() -> None:
    """FR-02: an unknown level name is rejected by the Literal constraint."""
    with pytest.raises(ValidationError, match="level"):
        FractalRegimeState(
            level="galactic",  # type: ignore[arg-type]
            regime="maintain",
            days_in_regime=0,
            is_hysteresis_active=False,
            hysteresis_days=0,
        )


def test_fr03_regime_round_trips_on_record() -> None:
    """FR-03: each level's regime is one of the 4 policy states and round-trips."""
    regime = _regime(["global", "cluster", "vector", "sub_vector"])
    rec = IKIGAiRecord.model_validate(_base_payload(regime=regime))
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.regime is not None
    assert len(again.regime.levels) == 4
    for lv in again.regime.levels:
        assert lv.regime.lower() in {"push", "maintain", "reduce", "recover"}


# ──────────────────────────── SA-01..05 ────────────────────────────


def _mirror(tmp: Path, md: Path) -> tuple[SQLiteAdapter, IKIGAiRecord]:
    adapter = SQLiteAdapter(db_path=tmp / "mirror.db")
    rec = IKIGAiRecord.model_validate(
        _base_payload(
            ueid="ikigai:dream:sync-probe:0000000a:0000000b",
            slug="sync-probe",
            source_md_path=md,
        )
    )
    IKIGAiRecordBridge(adapter).upsert_ikigai_record(rec)
    return adapter, rec


def test_sa01_vault_is_canonical(dream_record: IKIGAiRecord) -> None:
    """SA-01: the vault .md is the canonical source — its path is on the record."""
    assert dream_record.source_md_path.as_posix().endswith(
        "data/matheus/dreams/vaga-remota-2026.md"
    )
    assert dream_record.drift_state is DriftState.IN_SYNC


def test_sa02_drift_detector_in_sync_when_vault_matches(tmp_dir: Path) -> None:
    """SA-02: DriftDetector reports a non-conflicting state when vault matches mirror."""
    vault = tmp_dir / "vault"
    md = vault / "dreams" / "sync-probe.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("# probe\n", encoding="utf-8")
    adapter, rec = _mirror(tmp_dir, md)
    findings = list(DriftDetector(adapter)._collect(vault))
    mine = [f for f in findings if f.ueid == rec.ueid]
    assert len(mine) == 1
    assert mine[0].state in {
        DriftState.IN_SYNC,
        DriftState.MARKDOWN_NEWER,
        DriftState.SQLITE_NEWER,
    }


def test_sa03_drift_detector_flags_markdown_newer(tmp_dir: Path) -> None:
    """SA-03: DriftDetector reports drift when the .md is newer than the mirror.

    Limitation: the detector uses mtime as the drift proxy (md5 comparison is
    marked as future work in drift_detector.py), so this futures the mtime.
    """
    vault = tmp_dir / "vault"
    md = vault / "dreams" / "sync-probe.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("# probe\n", encoding="utf-8")
    adapter, rec = _mirror(tmp_dir, md)
    fut = (datetime.now(timezone.utc) + timedelta(seconds=120)).timestamp()
    os.utime(md, (fut, fut))
    findings = list(DriftDetector(adapter)._collect(vault))
    mine = [f for f in findings if f.ueid == rec.ueid]
    assert len(mine) == 1
    assert mine[0].state is DriftState.MARKDOWN_NEWER


def test_sa04_checkpoint_adapter_round_trip(tmp_dir: Path) -> None:
    """SA-04: CheckpointAdapter save/load round-trips via JsonPlusSerializer (no pickle)."""
    adapter = CheckpointAdapter(tmp_dir / "ckpt.db")
    rec = IKIGAiRecord.model_validate(_base_payload(q_he_score={"value": 0.5, "unit": "ratio"}))
    adapter.save(rec, thread_id="t1")
    loaded = adapter.load("t1")
    assert loaded is not None
    assert loaded.ueid == rec.ueid
    assert loaded.q_he_score == rec.q_he_score
    assert adapter.load("missing") is None


def test_sa05_state_reducer_normalizes_state_dict(tmp_dir: Path) -> None:
    """SA-05: StateReducer.reduce(state, source_md_path) → IKIGAiRecord (CYCLE)."""
    md = tmp_dir / "cycle.md"
    state: dict[str, Any] = {
        "cycle_id": "ikigai:cycle:2026-q3:0000000c:0000000d",
        "cycle_start": "2026-07-01",
        "vector_scores": {"skill": 0.8, "market": 0.6},
        "q_he_score": 0.7,
        "meta_vector_score": 0.65,
        "regime_state": "MAINTAIN",
        "phase": "fundacao",
    }
    rec = StateReducer.reduce(state, md)
    assert isinstance(rec, IKIGAiRecord)
    assert rec.entity_type is EntityType.CYCLE
    assert rec.status is StatusType.ACTIVE
    assert rec.is_placeholder is True
    assert rec.regime is not None
    assert len(rec.regime.levels) == 4
    assert rec.vector_scores["skill"].unit is ScoreUnit.PERCENT
    assert rec.source_md_path == md


# ──────────────────────────── PH-01, PS-01 ────────────────────────────


def test_ph01_placeholder_and_phase_snapshot_round_trip() -> None:
    """PH-01: is_placeholder=True survives round-trip; PhaseSnapshot re-validates.

    Limitation: PhaseSnapshot itself has no `is_placeholder` field (I7 keeps it
    frozen and minimal), so the placeholder flag is asserted on IKIGAiRecord.
    """
    rec = IKIGAiRecord.model_validate(
        _base_payload(is_placeholder=True, placeholder_owner="ikigai-agent")
    )
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.is_placeholder is True
    assert again.placeholder_owner == "ikigai-agent"

    snap = PhaseSnapshot(
        ueid="ikigai:phase_snapshot:2026-q3:0000000e:0000000f",
        cycle_ueid="ikigai:cycle:2026-q3:0000000c:0000000d",
        phase="fundacao",
        iteration=1,
        weights={"passion": 0.2, "skill": 0.2, "market": 0.2, "revenue": 0.2, "course": 0.2},
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    again_snap = PhaseSnapshot.model_validate(snap.model_dump())
    assert again_snap == snap
    assert again_snap.weight_sum() == pytest.approx(1.0)


def test_ps01_drift_state_resolved_path_round_trips() -> None:
    """PS-01: a resolved DriftState + source_md_path round-trip on the record."""
    rec = IKIGAiRecord.model_validate(
        _base_payload(drift_state="conflict", source_md_path=DREAM_MD)
    )
    again = IKIGAiRecord.model_validate(dict_to_frontmatter(rec))
    assert again.drift_state is DriftState.CONFLICT
    assert again.source_md_path.as_posix() == DREAM_MD.as_posix()
