import pytest
from datetime import datetime
from pydantic import ValidationError
from src.contracts.sonho import Sonho


def test_sonho_construction_minimum_fields():
    s = Sonho(
        id="sn:life-os-v1:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Ship Algorithmic Life OS v1",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill", "market", "revenue"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="Ship a planning system that actually plans for me, not against me.",
        success_metric="A (operational hard) + B (adoption soft)",
        core_values=["craft", "truth", "leverage"],
    )
    assert s.tier == "SONHO"
    assert s.pae_tier == "SONHO"
    assert s.motivation.startswith("Ship a planning")
    assert s.success_metric == "A (operational hard) + B (adoption soft)"
    assert s.core_values == ["craft", "truth", "leverage"]


def test_sonho_requires_motivation():
    with pytest.raises(ValidationError, match="motivation"):
        Sonho(
            id="sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
            title="Test",
            tier="SONHO",
            parent_ueid=None,
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="SONHO",
            created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
            # motivation missing
            success_metric="X",
        )


def test_sonho_frozen_rejects_title_mutation():
    s = Sonho(
        id="sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Test",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m",
        success_metric="s",
    )
    with pytest.raises(Exception):
        s.title = "New Title"
