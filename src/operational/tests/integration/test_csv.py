"""Integration tests for the CSV loader + dataset selector."""
from __future__ import annotations

import csv
import os
import sys
import tempfile
from datetime import date, datetime, time
from pathlib import Path

import pytest

# Set TIME_TASKER_STATE_DIR to a tmp dir BEFORE any operational import.
# The conftest.py also does this, but we set it here as well so the test
# works even if run directly.
_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-csv-test-state"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.csv_loader import (  # noqa: E402
    ENTITY_TYPE_ORDER,
    MODEL_MAP,
    _from_jsonable,
    _to_jsonable,
    export_to_csv,
    import_from_csv,
    import_from_csv_as_entities,
)
from operational.cli.dataset_selector import (  # noqa: E402
    DatasetRef,
    list_datasets,
    resolve_dataset,
)
from operational.cli.state import (  # noqa: E402
    day_contexts,
    journals,
    routines,
    sleep_records,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def tmp_csv(tmp_path: Path) -> Path:
    return tmp_path / "test.csv"


@pytest.fixture
def sample_rows() -> list[tuple[str, str, dict]]:
    """Realistic entities from multiple types."""
    return [
        (
            "sleep_record",
            "sle_2026_06_07",
            {
                "id": "sle_2026_06_07",
                "date": date(2026, 6, 7),
                "bedtime": time(23, 0),
                "wake_time": time(7, 0),
                "quality_score": 8,
                "deep_sleep_pct": None,
                "rem_sleep_pct": None,
                "interruptions": 0,
                "notes": "",
                "source": "MANUAL",
                "created_at": datetime(2026, 6, 8, 0, 50, 17),
            },
        ),
        (
            "habit",
            "hab_water",
            {
                "id": "hab_water",
                "name": "Drink water",
                "category": "physiological",
                "resistance": 1.0,
                "lambda_learning": 0.093,
                "weight_in_qhe": 0.1,
                "frequency": "DAILY",
                "target_streak": None,
                "description": "",
                "created_at": datetime(2026, 6, 1, 0, 0),
                "archived": False,
            },
        ),
        (
            "day_context",
            "ctx_2026_06_07",
            {
                "id": "ctx_2026_06_07",
                "date": date(2026, 6, 7),
                "tipo_dia": "curso",  # TipoDia is a StrEnum with lowercase values
                "hardwork_orcado_min": 540,
                "hardwork_realizado_min": 480,
                "pomodoros_meta": 12,
                "pomodoros_realizados": 11,
                "tem_curso": True,
                "tem_deadline": False,
                "observacoes": "",
                "created_at": datetime(2026, 6, 7, 23, 0),
            },
        ),
    ]


# ===========================================================================
# _to_jsonable / _from_jsonable
# ===========================================================================


class TestToFromJsonable:
    def test_none(self) -> None:
        assert _to_jsonable(None) == ""
        assert _from_jsonable("") is None

    def test_datetime(self) -> None:
        dt = datetime(2026, 6, 7, 14, 30, 0)
        s = _to_jsonable(dt)
        assert s == "2026-06-07T14:30:00"
        assert _from_jsonable(s, datetime) == dt

    def test_date(self) -> None:
        d = date(2026, 6, 7)
        s = _to_jsonable(d)
        assert s == "2026-06-07"
        assert _from_jsonable(s, date) == d

    def test_time(self) -> None:
        t = time(14, 30, 45)
        s = _to_jsonable(t)
        assert s == "14:30:45"
        assert _from_jsonable(s, time) == t

    def test_enum(self) -> None:
        from operational.enums import TipoDia

        s = _to_jsonable(TipoDia.CURSO)
        # TipoDia is a StrEnum with lowercase values.
        assert s == "curso"

    def test_bool(self) -> None:
        assert _to_jsonable(True) == "true"
        assert _to_jsonable(False) == "false"
        assert _from_jsonable("true") is True
        assert _from_jsonable("false") is False

    def test_int(self) -> None:
        assert _to_jsonable(42) == "42"
        assert _from_jsonable("42") == 42

    def test_float(self) -> None:
        assert _to_jsonable(3.14) == "3.14"
        assert _from_jsonable("3.14") == 3.14

    def test_list_dict(self) -> None:
        s = _to_jsonable([1, 2, 3])
        assert s == "[1, 2, 3]"
        assert _from_jsonable(s) == [1, 2, 3]
        s = _to_jsonable({"a": 1})
        assert s == '{"a": 1}'

    def test_set(self) -> None:
        from operational.enums import Period

        s = _to_jsonable({Period.MANHA, Period.TARDE})
        assert "MANHA" in s
        assert "TARDE" in s


# ===========================================================================
# export_to_csv / import_from_csv
# ===========================================================================


class TestExportImport:
    def test_roundtrip(self, tmp_csv: Path, sample_rows: list) -> None:
        written = export_to_csv(sample_rows, tmp_csv)
        assert written == 3
        assert tmp_csv.exists()
        groups = import_from_csv(tmp_csv)
        assert "sleep_record" in groups
        assert "habit" in groups
        assert "day_context" in groups
        sleep = groups["sleep_record"][0]
        assert sleep["id"] == "sle_2026_06_07"
        # Date string (raw CSV cell)
        assert sleep["date"] == "2026-06-07"

    def test_validates_through_pydantic(self, tmp_csv: Path, sample_rows: list) -> None:
        export_to_csv(sample_rows, tmp_csv)
        groups = import_from_csv_as_entities(tmp_csv)
        sleep = groups["sleep_record"][0]
        from operational.entities.metric import SleepRecord

        assert isinstance(sleep, SleepRecord)
        assert sleep.quality_score == 8

    def test_utf8_bom_written(self, tmp_csv: Path, sample_rows: list) -> None:
        export_to_csv(sample_rows, tmp_csv)
        raw = tmp_csv.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"  # UTF-8 BOM

    def test_crlf_line_endings(self, tmp_csv: Path, sample_rows: list) -> None:
        export_to_csv(sample_rows, tmp_csv)
        raw = tmp_csv.read_bytes()
        assert b"\r\n" in raw

    def test_empty_rows(self, tmp_csv: Path) -> None:
        written = export_to_csv([], tmp_csv)
        assert written == 0
        assert tmp_csv.exists()

    def test_header_has_entity_type_and_id(
        self, tmp_csv: Path, sample_rows: list
    ) -> None:
        export_to_csv(sample_rows, tmp_csv)
        with open(tmp_csv, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader)
        assert header[0] == "entity_type"
        assert header[1] == "id"

    def test_missing_field_emits_empty_cell(self, tmp_csv: Path) -> None:
        rows = [("habit", "hab_x", {"id": "hab_x", "name": "Test"})]
        export_to_csv(rows, tmp_csv)
        with open(tmp_csv, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            row = next(reader)
        assert row.get("category", "") == ""

    def test_unknown_entity_type_raises(self, tmp_csv: Path) -> None:
        with open(tmp_csv, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\r\n")
            writer.writerow(["entity_type", "id", "name"])
            writer.writerow(["unknown_type", "u_1", "Test"])
        with pytest.raises(ValueError, match="unknown entity_type"):
            import_from_csv(tmp_csv)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            import_from_csv(tmp_path / "nonexistent.csv")

    def test_invalid_header_raises(self, tmp_csv: Path) -> None:
        with open(tmp_csv, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\r\n")
            writer.writerow(["wrong", "header"])
        with pytest.raises(ValueError, match="Invalid CSV header"):
            import_from_csv(tmp_csv)


# ===========================================================================
# Dataset selector
# ===========================================================================


class TestDatasetSelector:
    def test_resolve_synthetic(self) -> None:
        ref = resolve_dataset("synthetic")
        assert ref.name == "synthetic"
        assert ref.csv_path.name == "synthetic.csv"
        assert ref.is_builtin

    def test_resolve_golden(self) -> None:
        ref = resolve_dataset("golden")
        assert ref.name == "golden"
        assert ref.csv_path.name == "golden.csv"

    def test_resolve_production(self) -> None:
        ref = resolve_dataset("production")
        assert ref.name == "production"
        assert str(ref.csv_path) == "."  # empty Path

    def test_resolve_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown dataset"):
            resolve_dataset("nonexistent")

    def test_resolve_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TIME_TASKER_DATASET", "golden")
        ref = resolve_dataset()
        assert ref.name == "golden"

    def test_resolve_default_is_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TIME_TASKER_DATASET", raising=False)
        ref = resolve_dataset()
        assert ref.name == "production"

    def test_list_datasets(self) -> None:
        all_ds = list_datasets()
        names = {d.name for d in all_ds}
        assert "synthetic" in names
        assert "golden" in names
        assert "production" in names


# ===========================================================================
# Roundtrip via the actual repos
# ===========================================================================


class TestStateRoundtrip:
    def test_export_import_via_repos(self, tmp_path: Path) -> None:
        """Create real entities, export to CSV, clear, import back."""
        from operational.entities.metric import SleepRecord
        from operational.entities.v3 import DayContext

        # Create
        sleep = SleepRecord(
            id="sle_test_001",
            date=date(2026, 6, 7),
            bedtime=time(23, 0),
            wake_time=time(7, 0),
            quality_score=8,
            created_at=datetime(2026, 6, 8, 0, 0),
        )
        sleep_records.upsert(sleep)
        ctx = DayContext(
            id="ctx_test_001",
            date=date(2026, 6, 7),
            hardwork_orcado_min=540,
            hardwork_realizado_min=480,
            created_at=datetime(2026, 6, 7, 23, 0),
        )
        day_contexts.upsert(ctx)

        # Export
        csv_path = tmp_path / "export.csv"
        rows: list[tuple[str, str, dict]] = []
        for etype, repo in [
            ("sleep_record", sleep_records),
            ("day_context", day_contexts),
        ]:
            for ent in repo:
                data = ent.model_dump(mode="python")
                rows.append((etype, str(ent.id), data))
        written = export_to_csv(rows, csv_path)
        assert written == 2

        # Clear
        sleep_records.clear()
        day_contexts.clear()
        assert sleep_records.count() == 0
        assert day_contexts.count() == 0

        # Import
        groups = import_from_csv_as_entities(csv_path)
        for ent in groups.get("sleep_record", []):
            sleep_records.upsert(ent)
        for ent in groups.get("day_context", []):
            day_contexts.upsert(ent)

        # Verify
        assert sleep_records.count() == 1
        loaded = sleep_records.get("sle_test_001")
        assert loaded is not None
        assert loaded.quality_score == 8
        assert day_contexts.count() == 1
