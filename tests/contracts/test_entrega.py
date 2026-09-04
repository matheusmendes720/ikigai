"""Tests for Entrega contract."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.contracts.entrega import Entrega


def test_entrega_construction():
    e = Entrega(
        id="en:bot-mvp:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Bot MVP v1.0",
        tier="QUARTERLY",
        parent_ueid="pj:bot-builder:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        artifact_path="/vault/deliverables/bot-mvp-v1.zip",
        artifact_type="binary",
        is_public=False,
    )
    assert e.tier == "QUARTERLY"
    assert e.artifact_path == "/vault/deliverables/bot-mvp-v1.zip"
    assert e.artifact_type == "binary"
    assert e.is_public is False


def test_entrega_artifact_type_default():
    e = Entrega(
        id="en:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="pj:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    assert e.artifact_type == "document"


def test_entrega_is_public_default():
    e = Entrega(
        id="en:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="pj:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    assert e.is_public is False


def test_entrega_frozen_rejects_mutation():
    e = Entrega(
        id="en:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="pj:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    with pytest.raises(Exception):
        e.is_public = True
