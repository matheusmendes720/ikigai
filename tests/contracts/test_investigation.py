"""Tests for Investigation contract — Plan C Task 1."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.contracts.investigation import Investigation, InvestigationStatus


def _now() -> datetime:
    return datetime.fromisoformat("2026-09-05T00:00:00+00:00")


def test_investigation_minimum_fields():
    """Minimum required fields: inq_id, source, payload, created_at."""
    inv = Investigation(
        inq_id="inq-20260905-001",
        source="agent",
        payload="Raw CSV observation from research log — needs DECISION on canonicalization.",
        created_at=_now(),
    )
    assert inv.inq_id == "inq-20260905-001"
    assert inv.status == "open"
    assert inv.source == "agent"
    assert inv.inq_ueid is None
    assert inv.tags == ()


def test_investigation_status_literal_type():
    """InvestigationStatus is a Literal — only 4 values allowed."""
    assert InvestigationStatus.__args__ == ("open", "in_progress", "resolved", "archived")


def test_investigation_extra_forbid():
    """Pydantic v2 strict — extra fields rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Investigation(
            inq_id="inq-20260905-001",
            source="agent",
            payload="x",
            created_at=_now(),
            extra_field="not allowed",  # type: ignore[call-arg]
        )
    assert "extra_field" in str(exc_info.value)


def test_investigation_frozen():
    """frozen=True — cannot mutate after creation."""
    inv = Investigation(
        inq_id="inq-20260905-001",
        source="agent",
        payload="x",
        created_at=_now(),
    )
    with pytest.raises(ValidationError):
        inv.status = "in_progress"  # type: ignore[misc]


def test_investigation_full_lifecycle():
    """Full lifecycle: open → in_progress → resolved (terminal)."""
    inv = Investigation(
        inq_id="inq-20260905-001",
        source="agent",
        payload="x",
        created_at=_now(),
        tags=("research", "ambiguous"),
    )
    assert inv.status == "open"
    # Terminal states (resolved/archived) are valid initial statuses too
    inv2 = Investigation(
        inq_id="inq-20260905-002",
        source="user",
        payload="y",
        created_at=_now(),
        status="resolved",
    )
    assert inv2.status == "resolved"


def test_investigation_with_ueid():
    """Once crystallized into hierarchy, inq_ueid is set."""
    inv = Investigation(
        inq_id="inq-20260905-001",
        source="agent",
        payload="x",
        created_at=_now(),
        inq_ueid="abc:def:0123:4567",
    )
    assert inv.inq_ueid == "abc:def:0123:4567"


def test_investigation_source_literal():
    """source is Literal['agent', 'user', 'external']."""
    for valid in ("agent", "user", "external"):
        inv = Investigation(
            inq_id=f"inq-{valid}",
            source=valid,  # type: ignore[arg-type]
            payload="x",
            created_at=_now(),
        )
        assert inv.source == valid
    with pytest.raises(ValidationError):
        Investigation(
            inq_id="bad",
            source="robot",  # type: ignore[arg-type]
            payload="x",
            created_at=_now(),
        )


def test_investigation_actor_field():
    """actor defaults to 'agent' but can be overridden."""
    inv_default = Investigation(
        inq_id="x", source="agent", payload="p", created_at=_now()
    )
    assert inv_default.actor == "agent"

    inv_user = Investigation(
        inq_id="y", source="agent", payload="p", created_at=_now(), actor="user:mathe"
    )
    assert inv_user.actor == "user:mathe"
