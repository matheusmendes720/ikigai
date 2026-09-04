"""Tests for Tarefa contract."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.contracts.tarefa import Tarefa


def test_tarefa_construction():
    t = Tarefa(
        id="tsk:build-bot:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="Build bot MVP",
        tier="QUARTERLY",
        parent_ueid="en:bot-mvp:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    assert t.tier == "QUARTERLY"
    assert t.title == "Build bot MVP"


def test_tarefa_inherits_base_fields():
    t = Tarefa(
        id="tsk:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="en:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        description="A test task",
        tags=["test", "bot"],
    )
    assert t.description == "A test task"
    assert t.tags == ["test", "bot"]


def test_tarefa_frozen_rejects_mutation():
    t = Tarefa(
        id="tsk:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        title="t",
        tier="QUARTERLY",
        parent_ueid="en:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    with pytest.raises(Exception):
        t.title = "New Title"
