"""Tests for Objetivo contract."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.contracts.objetivo import Objetivo


def test_objetivo_construction():
    o = Objetivo(
        id="ob:q4-build:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Deep Agent build Q4-2026",
        tier="QUARTERLY",
        parent_ueid="sn:life-os-v1:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        key_results=["B0 hygiene complete", "B4 queue worker complete"],
        progress_pct=0.0,
    )
    assert o.tier == "QUARTERLY"
    assert o.progress_pct == 0.0
    assert o.key_results == ["B0 hygiene complete", "B4 queue worker complete"]


def test_objetivo_progress_pct_validates_range():
    with pytest.raises(ValidationError):
        Objetivo(
            id="ob:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
            title="t",
            tier="QUARTERLY",
            parent_ueid="sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="QUARTERLY",
            created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
            progress_pct=150.0,  # > 100
        )


def test_objetivo_progress_pct_rejects_negative():
    with pytest.raises(ValidationError):
        Objetivo(
            id="ob:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
            title="t",
            tier="QUARTERLY",
            parent_ueid="sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="QUARTERLY",
            created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
            progress_pct=-10.0,  # < 0
        )


def test_objetivo_frozen_rejects_mutation():
    o = Objetivo(
        id="ob:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        key_results=["KR1"],
        progress_pct=50.0,
    )
    with pytest.raises(Exception):
        o.progress_pct = 75.0
