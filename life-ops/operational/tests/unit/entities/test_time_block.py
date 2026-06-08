"""Unit tests for :mod:`operational.entities.time_block`.

Coverage:

* Construction happy paths for :class:`TimeBlock`.
* Validation guards (frozen, extra=forbid, time ordering, field bounds).
* Computed properties (``duration_minutes``, ``overlaps_period``,
  ``has_routine_link``).
* Canonical period-hour windows (PAV §3: 3-5 / 8-17 / 18-21).
* JSON roundtrip.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from operational.entities.time_block import TimeBlock
from operational.enums import Period

from tests.unit.entities._roundtrip import roundtrip

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TS: datetime = datetime(2026, 6, 7, 12, 0, 0)
"""A fixed timestamp used for ``created_at`` across the suite."""


def _make_block(**overrides: Any) -> TimeBlock:
    """Return a minimal but valid :class:`TimeBlock` with optional overrides."""
    base: dict[str, Any] = {
        "id": "blk_2026_06_07_1410",
        "label": "Deep work",
        "start": datetime(2026, 6, 7, 14, 10),
        "end": datetime(2026, 6, 7, 15, 0),
        "period": Period.TARDE,
        "created_at": TS,
    }
    base.update(overrides)
    return TimeBlock(**base)


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


class TestModuleSurface:
    """The ``time_block`` module exposes a stable public API."""

    def test_all_is_complete(self) -> None:
        import operational.entities.time_block as mod

        assert "TimeBlock" in mod.__all__

    def test_all_names_importable(self) -> None:
        import operational.entities.time_block as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestTimeBlockConstruction:
    """Happy-path construction of :class:`TimeBlock`."""

    def test_create_minimal_time_block(self) -> None:
        b = _make_block()
        assert b.id == "blk_2026_06_07_1410"
        assert b.label == "Deep work"
        assert b.start == datetime(2026, 6, 7, 14, 10)
        assert b.end == datetime(2026, 6, 7, 15, 0)
        assert b.period is Period.TARDE
        assert b.routine_id is None
        assert b.notes == ""
        assert b.created_at == TS

    def test_time_block_with_routine_link(self) -> None:
        b = _make_block(routine_id="rou_focus_block")
        assert b.routine_id == "rou_focus_block"

    def test_time_block_with_notes(self) -> None:
        b = _make_block(notes="Wrote the PRD for Sprint 2A")
        assert b.notes == "Wrote the PRD for Sprint 2A"

    def test_time_block_strips_whitespace_in_label(self) -> None:
        b = _make_block(label="  Spaced Label  ")
        assert b.label == "Spaced Label"

    @pytest.mark.parametrize("period", list(Period))
    def test_period_assignment(self, period: Period) -> None:
        b = _make_block(period=period)
        assert b.period is period

    def test_accepts_empty_label(self) -> None:
        b = _make_block(label="")
        assert b.label == ""

    def test_rejects_oversized_label(self) -> None:
        with pytest.raises(ValidationError):
            _make_block(label="x" * 101)

    def test_rejects_oversized_notes(self) -> None:
        with pytest.raises(ValidationError):
            _make_block(notes="x" * 501)


# ---------------------------------------------------------------------------
# Model_config guards
# ---------------------------------------------------------------------------


class TestTimeBlockModelConfig:
    """TimeBlock is frozen and rejects unknown fields."""

    def test_time_block_frozen(self) -> None:
        b = _make_block()
        with pytest.raises(ValidationError):
            b.label = "Mutated"  # type: ignore[misc]

    def test_time_block_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError) as exc:
            TimeBlock(
                id="blk_test",
                label="Test",
                start=datetime(2026, 6, 7, 14, 0),
                end=datetime(2026, 6, 7, 15, 0),
                period=Period.TARDE,
                created_at=TS,
                extra_field="nope",  # type: ignore[call-arg]
            )
        assert "extra_field" in str(exc.value)

    @pytest.mark.parametrize(
        "bad_id",
        ["ab_x", "toolong_x", "BLK_x", "blk_", "blk", "blk-X"],
    )
    def test_rejects_bad_ueid(self, bad_id: str) -> None:
        with pytest.raises(ValidationError):
            _make_block(id=bad_id)


# ---------------------------------------------------------------------------
# Time validators
# ---------------------------------------------------------------------------


class TestTimeBlockTimeValidation:
    """end must be strictly after start."""

    def test_time_block_validates_end_after_start(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _make_block(
                start=datetime(2026, 6, 7, 15, 0),
                end=datetime(2026, 6, 7, 14, 0),
            )
        assert "end" in str(exc.value)

    def test_time_block_rejects_equal_times(self) -> None:
        """Zero-duration blocks are forbidden."""
        with pytest.raises(ValidationError):
            _make_block(
                start=datetime(2026, 6, 7, 14, 0),
                end=datetime(2026, 6, 7, 14, 0),
            )

    def test_time_block_allows_overnight_block(self) -> None:
        """Overnight crossing is allowed (end is in absolute time after start)."""
        b = _make_block(
            start=datetime(2026, 6, 7, 23, 0),
            end=datetime(2026, 6, 8, 1, 0),
        )
        assert b.duration_minutes == 120

    def test_time_block_rejects_invalid_datetime_string(self) -> None:
        """Pydantic rejects malformed datetimes at construction time."""
        with pytest.raises(ValidationError):
            TimeBlock(
                id="blk_test",
                label="Test",
                start="not-a-datetime",  # type: ignore[arg-type]
                end=datetime(2026, 6, 7, 15, 0),
                period=Period.TARDE,
                created_at=TS,
            )


# ---------------------------------------------------------------------------
# Computed fields — duration
# ---------------------------------------------------------------------------


class TestTimeBlockDuration:
    """``duration_minutes`` is computed from start/end."""

    def test_time_block_computed_duration_minutes(self) -> None:
        b = _make_block(
            start=datetime(2026, 6, 7, 14, 0),
            end=datetime(2026, 6, 7, 15, 0),
        )
        assert b.duration_minutes == 60

    def test_duration_50_minute_focus_block(self) -> None:
        b = _make_block(
            start=datetime(2026, 6, 7, 14, 10),
            end=datetime(2026, 6, 7, 15, 0),
        )
        assert b.duration_minutes == 50

    def test_duration_handles_seconds(self) -> None:
        """Whole-minute truncation: 1h0m30s -> 60 minutes."""
        b = _make_block(
            start=datetime(2026, 6, 7, 14, 0, 0),
            end=datetime(2026, 6, 7, 15, 0, 30),
        )
        assert b.duration_minutes == 60

    def test_duration_appears_in_model_dump(self) -> None:
        b = _make_block()
        data = b.model_dump()
        assert data["duration_minutes"] == 50


# ---------------------------------------------------------------------------
# Computed fields — overlaps_period
# ---------------------------------------------------------------------------


class TestTimeBlockOverlapsPeriodManha:
    """MANHA canonical window is 3-5 (PAV §3)."""

    @pytest.mark.parametrize(
        ("start_h", "end_h", "expected"),
        [
            (3, 5, True),     # exact match
            (3, 4, True),     # within
            (4, 5, True),     # within
            (2, 4, False),    # starts before window
            (5, 6, False),    # starts at window end (exclusive)
            (4, 6, False),    # ends after window
            (6, 7, False),    # entirely outside
        ],
    )
    def test_overlaps_period_manha(
        self, start_h: int, end_h: int, expected: bool,
    ) -> None:
        b = _make_block(
            start=datetime(2026, 6, 7, start_h, 0),
            end=datetime(2026, 6, 7, end_h, 0),
            period=Period.MANHA,
        )
        assert b.overlaps_period is expected

    def test_overlaps_period_manha_block_at_4am(self) -> None:
        b = _make_block(
            start=datetime(2026, 6, 7, 4, 0),
            end=datetime(2026, 6, 7, 4, 30),
            period=Period.MANHA,
        )
        assert b.overlaps_period is True


class TestTimeBlockOverlapsPeriodTarde:
    """TARDE canonical window is 8-17 (PAV §3)."""

    @pytest.mark.parametrize(
        ("start_h", "end_h", "expected"),
        [
            (8, 17, True),    # exact match
            (9, 12, True),    # midday
            (14, 15, True),   # afternoon
            (8, 12, True),    # morning of tarde
            (12, 17, True),   # ending at boundary
            (7, 9, False),    # starts before window
            (16, 18, False),  # ends after window
            (18, 19, False),  # entirely outside
        ],
    )
    def test_overlaps_period_tarde(
        self, start_h: int, end_h: int, expected: bool,
    ) -> None:
        b = _make_block(
            start=datetime(2026, 6, 7, start_h, 0),
            end=datetime(2026, 6, 7, end_h, 0),
            period=Period.TARDE,
        )
        assert b.overlaps_period is expected

    def test_overlaps_period_tarde_50min_focus(self) -> None:
        """A 50-minute focus block at 14:10-15:00 overlaps TARDE."""
        b = _make_block(
            start=datetime(2026, 6, 7, 14, 10),
            end=datetime(2026, 6, 7, 15, 0),
            period=Period.TARDE,
        )
        assert b.overlaps_period is True


class TestTimeBlockOverlapsPeriodNoite:
    """NOITE canonical window is 18-21 (PAV §3)."""

    @pytest.mark.parametrize(
        ("start_h", "end_h", "expected"),
        [
            (18, 21, True),   # exact match
            (18, 19, True),   # start of window
            (19, 20, True),   # middle
            (20, 21, True),   # end at boundary
            (17, 19, False),  # starts before window
            (20, 22, False),  # ends after window
            (21, 22, False),  # starts at window end (exclusive)
        ],
    )
    def test_overlaps_period_noite(
        self, start_h: int, end_h: int, expected: bool,
    ) -> None:
        b = _make_block(
            start=datetime(2026, 6, 7, start_h, 0),
            end=datetime(2026, 6, 7, end_h, 0),
            period=Period.NOITE,
        )
        assert b.overlaps_period is expected

    def test_overlaps_period_noite_evening_routine(self) -> None:
        b = _make_block(
            start=datetime(2026, 6, 7, 19, 0),
            end=datetime(2026, 6, 7, 19, 30),
            period=Period.NOITE,
        )
        assert b.overlaps_period is True


# ---------------------------------------------------------------------------
# Routine link
# ---------------------------------------------------------------------------


class TestTimeBlockRoutineLink:
    """``routine_id`` is optional; ``has_routine_link`` reflects it."""

    def test_time_block_optional_routine_link(self) -> None:
        b = _make_block()
        assert b.routine_id is None
        assert b.has_routine_link is False

    def test_time_block_routine_link_set(self) -> None:
        b = _make_block(routine_id="rou_focus_block")
        assert b.has_routine_link is True

    def test_routine_link_rejects_bad_ueid(self) -> None:
        with pytest.raises(ValidationError):
            _make_block(routine_id="not-a-valid-ueid!")


# ---------------------------------------------------------------------------
# JSON roundtrip
# ---------------------------------------------------------------------------


class TestTimeBlockJsonRoundtrip:
    """JSON encode/decode preserves the entity."""

    def test_json_roundtrip(self) -> None:
        b = _make_block(
            routine_id="rou_focus_block",
            notes="Sprint 2A prep",
        )
        decoded: TimeBlock = roundtrip(b)
        assert decoded == b
        assert decoded.duration_minutes == b.duration_minutes
        assert decoded.overlaps_period == b.overlaps_period
        assert decoded.has_routine_link == b.has_routine_link

    def test_json_payload_shape(self) -> None:
        b = _make_block()
        payload = json.loads(b.model_dump_json())
        assert payload["label"] == "Deep work"
        assert payload["period"] == "TARDE"
        # computed fields are included
        assert "duration_minutes" in payload
        assert "overlaps_period" in payload
        assert "has_routine_link" in payload

    def test_json_roundtrip_preserves_period_membership(self) -> None:
        b = _make_block(period=Period.NOITE)
        decoded: TimeBlock = roundtrip(b)
        assert decoded.period is Period.NOITE
        assert decoded.overlaps_period == b.overlaps_period


# ---------------------------------------------------------------------------
# Deep copy / equality
# ---------------------------------------------------------------------------


class TestTimeBlockCopy:
    """Model copy semantics."""

    def test_deepcopy_preserves_data(self) -> None:
        b = _make_block()
        clone = deepcopy(b)
        assert clone == b
        assert clone.duration_minutes == b.duration_minutes

    def test_model_copy_preserves_data(self) -> None:
        b = _make_block()
        clone = b.model_copy()
        assert clone == b
