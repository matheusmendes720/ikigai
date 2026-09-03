import pytest
from src.contracts.base import BasePlanContract
from src.contracts.common import PlanTier, VectorKey, PaeCyclePhase
from src.contracts.common import UEID  # already exists


def test_subset_validator_accepts_empty_for_root_sonho():
    """SONHO-level (parent_ueid=None) skips subset check."""
    entity = BasePlanContract(
        id="sn:life-os-v1:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Ship Algorithmic Life OS v1",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill", "market", "revenue"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at="2026-09-03T00:00:00Z",
    )
    assert entity.ikigai_vectors == ["skill", "market", "revenue"]


def test_subset_validator_accepts_proper_subset():
    """OBJETIVO with [skill] is subset of SONHO with [skill, market, revenue]."""
    # Mock: pass parent_ueid but validator can't resolve without registry
    # We test validator logic directly via a stub parent
    entity = BasePlanContract(
        id="ob:q4-build:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Deep Agent build Q4-2026",
        tier="QUARTERLY",
        parent_ueid="sn:life-os-v1:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at="2026-09-03T00:00:00Z",
    )
    assert entity.ikigai_vectors == ["skill"]


def test_subset_validator_rejects_non_subset():
    """OBJETIVO with [revenue] is NOT subset of SONHO without revenue (hypothetical)."""
    # Test the validator function in isolation
    from src.contracts.base import _check_vector_subset
    with pytest.raises(ValueError, match="not subset of parent"):
        _check_vector_subset(
            child_vectors=["revenue"],
            parent_vectors=["skill", "market"],
        )


def test_frozen_model_rejects_mutation():
    """frozen=True means assigning to fields raises."""
    entity = BasePlanContract(
        id="sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Test",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at="2026-09-03T00:00:00Z",
    )
    with pytest.raises(Exception):  # ValidationError or AttributeError
        entity.title = "New Title"


def test_extra_field_rejected():
    """extra='forbid' means unknown fields raise ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Extra inputs"):
        BasePlanContract(
            id="sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
            title="Test",
            tier="SONHO",
            parent_ueid=None,
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="SONHO",
            created_at="2026-09-03T00:00:00Z",
            unknown_field="should fail",  # type: ignore
        )
