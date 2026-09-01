"""Unit tests for :mod:`operational.entities.ajuste_fino`."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from operational.entities.ajuste_fino import AjusteFino
from operational.enums import Period


def _make_ajuste(
    *,
    ajuste_id: str = "aju_test_001",
    date_: date = date(2026, 6, 7),
    period: Period = Period.MANHA,
    minutos: int = 5,
    reason: str = "Extended break due to fatigue",
    block_id_before: str | None = None,
    block_id_after: str | None = None,
) -> AjusteFino:
    return AjusteFino(
        id=ajuste_id,
        date=date_,
        period=period,
        minutos=minutos,
        reason=reason,
        block_id_before=block_id_before,
        block_id_after=block_id_after,
        created_at=datetime(2026, 6, 7, 5, 30),
    )


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestAjusteFinoCreation:
    """Tests for creating AjusteFino entities."""

    def test_minimal_creation(self) -> None:
        ajuste = _make_ajuste()
        assert ajuste.id == "aju_test_001"
        assert ajuste.date == date(2026, 6, 7)
        assert ajuste.period == Period.MANHA
        assert ajuste.minutos == 5
        assert ajuste.reason == "Extended break due to fatigue"
        assert ajuste.block_id_before is None
        assert ajuste.block_id_after is None

    def test_negative_minutos_allowed(self) -> None:
        """Negative minutos are valid (shortened block, skipped ritual)."""
        ajuste = _make_ajuste(minutos=-30)
        assert ajuste.minutos == -30

    def test_zero_minutos_allowed(self) -> None:
        ajuste = _make_ajuste(minutos=0)
        assert ajuste.minutos == 0

    def test_max_positive_minutos(self) -> None:
        ajuste = _make_ajuste(minutos=1440)  # 24h
        assert ajuste.minutos == 1440

    def test_max_negative_minutos(self) -> None:
        ajuste = _make_ajuste(minutos=-1440)
        assert ajuste.minutos == -1440

    def test_with_block_references(self) -> None:
        ajuste = _make_ajuste(
            block_id_before="tbl_focus_1",
            block_id_after="tbl_focus_2",
        )
        assert ajuste.block_id_before == "tbl_focus_1"
        assert ajuste.block_id_after == "tbl_focus_2"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestAjusteFinoValidation:
    """Tests for AjusteFino validation rules."""

    def test_out_of_range_minutos_too_high(self) -> None:
        with pytest.raises(ValidationError, match="minutos"):
            _make_ajuste(minutos=2000)  # > 1440

    def test_out_of_range_minutos_too_low(self) -> None:
        with pytest.raises(ValidationError, match="minutos"):
            _make_ajuste(minutos=-2000)  # < -1440

    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            _make_ajuste(reason="")

    def test_whitespace_only_reason_rejected(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            _make_ajuste(reason="   \t\n   ")

    def test_long_reason_rejected(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            _make_ajuste(reason="x" * 501)  # > 500

    def test_max_reason_accepted(self) -> None:
        reason = "x" * 500
        ajuste = _make_ajuste(reason=reason)
        assert len(ajuste.reason) == 500

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            AjusteFino(
                id="aju_x",
                date=date(2026, 6, 7),
                period=Period.MANHA,
                minutos=5,
                reason="test",
                created_at=datetime.now(),
                invalid_field="should fail",
            )  # type: ignore[call-arg]

    def test_invalid_ueid_pattern(self) -> None:
        with pytest.raises(ValidationError, match="id"):
            _make_ajuste(ajuste_id="invalid_id")  # no underscore

    def test_invalid_period_rejected(self) -> None:
        with pytest.raises(ValidationError, match="period"):
            AjusteFino(
                id="aju_x",
                date=date(2026, 6, 7),
                period="NOT_A_PERIOD",  # type: ignore[arg-type]
                minutos=5,
                reason="test",
                created_at=datetime.now(),
            )


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestAjusteFinoImmutability:
    """Tests for frozen model behavior."""

    def test_cannot_mutate_minutos(self) -> None:
        ajuste = _make_ajuste()
        with pytest.raises((ValidationError, AttributeError)):
            ajuste.minutos = 999  # type: ignore[misc]

    def test_cannot_mutate_reason(self) -> None:
        ajuste = _make_ajuste()
        with pytest.raises((ValidationError, AttributeError)):
            ajuste.reason = "new reason"  # type: ignore[misc]

    def test_equality_is_structural(self) -> None:
        a = _make_ajuste(ajuste_id="aju_x", date_=date(2026, 6, 7), minutos=10, reason="x")
        b = _make_ajuste(ajuste_id="aju_x", date_=date(2026, 6, 7), minutos=10, reason="x")
        c = _make_ajuste(ajuste_id="aju_y", date_=date(2026, 6, 7), minutos=10, reason="x")
        assert a == b
        assert a != c


# ---------------------------------------------------------------------------
# JSON roundtrip
# ---------------------------------------------------------------------------


class TestAjusteFinoJsonRoundtrip:
    """Tests for JSON serialization."""

    def test_json_roundtrip(self) -> None:
        original = _make_ajuste(
            ajuste_id="aju_rt_001",
            minutos=-15,
            reason="Reduced S3 to 2 rounds",
            block_id_before="tbl_focus_s2",
            block_id_after="tbl_focus_s3",
        )
        json_str = original.model_dump_json()
        restored = AjusteFino.model_validate_json(json_str)
        assert restored == original
        assert restored.minutos == -15

    def test_model_dump_includes_all_fields(self) -> None:
        ajuste = _make_ajuste()
        data: dict[str, Any] = ajuste.model_dump()
        assert "id" in data
        assert "date" in data
        assert "period" in data
        assert "minutos" in data
        assert "reason" in data
        assert "created_at" in data
