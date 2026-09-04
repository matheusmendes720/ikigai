"""Tests for Meta contract."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.contracts.meta import Meta


def test_meta_construction():
    m = Meta(
        id="mt:q4-revenue:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Grow revenue 30% Q4",
        tier="QUARTERLY",
        parent_ueid="ob:q4-build:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["revenue"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        success_metrics=["MRR > R$30k", "Churn < 5%"],
        review_frequency_days=14,
    )
    assert m.tier == "QUARTERLY"
    assert m.review_frequency_days == 14
    assert m.success_metrics == ["MRR > R$30k", "Churn < 5%"]


def test_meta_default_review_frequency():
    m = Meta(
        id="mt:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="ob:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["revenue"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    assert m.review_frequency_days == 7


def test_meta_frozen_rejects_mutation():
    m = Meta(
        id="mt:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="ob:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["revenue"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    with pytest.raises(Exception):
        m.review_frequency_days = 30
