"""Tests for Projeto contract."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.contracts.projeto import Projeto


def test_projeto_construction():
    p = Projeto(
        id="pj:bot-builder:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Bot Builder Platform",
        tier="QUARTERLY",
        parent_ueid="mt:q4-revenue:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill", "market"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        tech_stack=["python", "fastapi", "postgres"],
        repo_url="https://github.com/matheusmendes720/bot-builder",
        target_revenue_brl=50000.0,
        actual_revenue_brl=0.0,
    )
    assert p.tier == "QUARTERLY"
    assert p.tech_stack == ["python", "fastapi", "postgres"]
    assert p.repo_url == "https://github.com/matheusmendes720/bot-builder"
    assert p.target_revenue_brl == 50000.0
    assert p.actual_revenue_brl == 0.0


def test_projeto_optional_repo_url():
    p = Projeto(
        id="pj:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Test Project",
        tier="QUARTERLY",
        parent_ueid="mt:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        tech_stack=["python"],
    )
    assert p.repo_url is None


def test_projeto_revenue_defaults():
    p = Projeto(
        id="pj:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="mt:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    assert p.target_revenue_brl == 0.0
    assert p.actual_revenue_brl == 0.0


def test_projeto_frozen_rejects_mutation():
    p = Projeto(
        id="pj:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="mt:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    with pytest.raises(Exception):
        p.tech_stack = ["rust"]
