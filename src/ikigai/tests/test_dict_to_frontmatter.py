"""Tests for dict_to_frontmatter — IKIGAiRecord → frontmatter dict (RT-01..06)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ikigai.entities.ikigai_record import IKIGAiRecord
from ikigai.vault.dict_to_frontmatter import dict_to_frontmatter


def _record() -> IKIGAiRecord:
    return IKIGAiRecord.model_validate({
        "ueid": "ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609",
        "entity_type": "dream",
        "slug": "vaga-remota-2026",
        "title": "Primeira vaga remota em Data/AI ate 2026-12-31",
        "description": None,
        "status": "active",
        "ikigai_vectors": ["passion", "skill", "market", "revenue", "course"],
        "vector_weights_snapshot": {"passion": 0.20, "skill": 0.20, "market": 0.20, "revenue": 0.20, "course": 0.20},
        "created_at": datetime(2026, 7, 3, 0, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 7, 3, 0, 0, 0, tzinfo=timezone.utc),
        "source_md_path": Path("data/matheus/dreams/vaga-remota-2026.md"),
        "custom": {"verticals": ["data-analytics", "ai-llm-tooling"]},
    })


def test_null_fields_preserved() -> None:
    """RT-03: description=null preserved; NOT dropped."""
    d = dict_to_frontmatter(_record())
    assert "description" in d
    assert d["description"] is None


def test_datetime_iso_preserved() -> None:
    d = dict_to_frontmatter(_record())
    assert d["created_at"] == "2026-07-03T00:00:00+00:00"


def test_extra_allow_field_passes_through() -> None:
    """RT-06: extra fields (entity-specific like DreamEntity.motivation) survive."""
    r = _record()
    # Set entity-specific extra field via model_extra (SPEC D6 allows extras)
    object.__setattr__(r, "__pydantic_extra__", {"motivation": "quer construir coisas legais"})
    d = dict_to_frontmatter(r)
    assert d["motivation"] == "quer construir coisas legais"


def test_custom_dict_preserved() -> None:
    d = dict_to_frontmatter(_record())
    assert d["custom"] == {"verticals": ["data-analytics", "ai-llm-tooling"]}


def test_path_stringified() -> None:
    d = dict_to_frontmatter(_record())
    assert d["source_md_path"] == "data/matheus/dreams/vaga-remota-2026.md"


def test_enum_value_serialized() -> None:
    """StatusType.ACTIVE → 'active', not 'StatusType.ACTIVE'."""
    d = dict_to_frontmatter(_record())
    assert d["status"] == "active"


def test_vector_weights_intact() -> None:
    d = dict_to_frontmatter(_record())
    assert d["vector_weights_snapshot"]["passion"] == 0.20