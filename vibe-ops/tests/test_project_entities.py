"""Unit tests for Project entity vault enrichment fields.

Source: .omo/plans/vault-enrichment-fields.md
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from models.project_entities import Project  # noqa: E402


def _base_kwargs(**overrides):
    base = dict(
        id="proj_vault_test",
        title="Vault Enrichment Test Project",
        status="active",
        revenue_impact="HIGH",
    )
    base.update(overrides)
    return base


class TestVaultFieldDefaults:
    """All 9 new fields must have the documented defaults."""

    def test_xp_points_default_zero(self):
        p = Project(**_base_kwargs())
        assert p.xp_points == 0

    def test_mastery_level_default_beginner(self):
        p = Project(**_base_kwargs())
        assert p.mastery_level == "beginner"

    def test_subject_default_none(self):
        p = Project(**_base_kwargs())
        assert p.subject is None

    def test_learning_phase_default_none(self):
        p = Project(**_base_kwargs())
        assert p.learning_phase is None

    def test_tech_stack_default_empty_list(self):
        p = Project(**_base_kwargs())
        assert p.tech_stack == []

    def test_milestone_default_none(self):
        p = Project(**_base_kwargs())
        assert p.milestone is None

    def test_deliverable_default_none(self):
        p = Project(**_base_kwargs())
        assert p.deliverable is None

    def test_commercial_goal_default_none(self):
        p = Project(**_base_kwargs())
        assert p.commercial_goal is None

    def test_vault_path_default_none(self):
        p = Project(**_base_kwargs())
        assert p.vault_path is None

    def test_last_synced_at_default_none(self):
        p = Project(**_base_kwargs())
        assert p.last_synced_at is None


class TestVaultFieldAssignment:
    """All 9 new fields accept valid typed values."""

    def test_xp_points_positive_int(self):
        p = Project(**_base_kwargs(xp_points=1500))
        assert p.xp_points == 1500

    def test_mastery_level_advanced(self):
        p = Project(**_base_kwargs(mastery_level="advanced"))
        assert p.mastery_level == "advanced"

    def test_subject_assigned(self):
        p = Project(**_base_kwargs(subject="Algebra"))
        assert p.subject == "Algebra"

    def test_learning_phase_retrieval(self):
        p = Project(**_base_kwargs(learning_phase="retrieval"))
        assert p.learning_phase == "retrieval"

    def test_tech_stack_assigned(self):
        p = Project(**_base_kwargs(tech_stack=["Python", "FastAPI", "PostgreSQL"]))
        assert p.tech_stack == ["Python", "FastAPI", "PostgreSQL"]

    def test_milestone_date(self):
        milestone = date(2026, 9, 30)
        p = Project(**_base_kwargs(milestone=milestone))
        assert p.milestone == milestone

    def test_deliverable_assigned(self):
        p = Project(**_base_kwargs(deliverable="MVP demo"))
        assert p.deliverable == "MVP demo"

    def test_commercial_goal_assigned(self):
        p = Project(**_base_kwargs(commercial_goal="R$10k MRR"))
        assert p.commercial_goal == "R$10k MRR"

    def test_vault_path_assigned(self):
        p = Project(**_base_kwargs(vault_path="/vault/projects/proj_vault_test.md"))
        assert p.vault_path == "/vault/projects/proj_vault_test.md"

    def test_last_synced_at_datetime(self):
        synced = datetime(2026, 6, 30, 12, 0, 0)
        p = Project(**_base_kwargs(last_synced_at=synced))
        assert p.last_synced_at == synced


class TestValidation:
    """Invalid values must raise ValidationError."""

    def test_invalid_mastery_level_raises(self):
        with pytest.raises(ValidationError):
            Project(**_base_kwargs(mastery_level="godlike"))

    def test_invalid_learning_phase_raises(self):
        with pytest.raises(ValidationError):
            Project(**_base_kwargs(learning_phase="random_phase"))

    def test_invalid_xp_points_type_raises(self):
        with pytest.raises(ValidationError):
            Project(**_base_kwargs(xp_points="not_a_number"))


class TestExtraAllow:
    """Unknown extra fields must be accepted (extra='allow')."""

    def test_unknown_field_accepted(self):
        p = Project(
            **_base_kwargs(custom_field_from_obsidian="value-42", another_extra=123)
        )
        assert p.custom_field_from_obsidian == "value-42"
        assert p.another_extra == 123

    def test_dict_payload_extra_fields(self):
        payload = _base_kwargs()
        payload["vault_extra_xp"] = 9999
        payload["nested_metadata"] = {"key": "value"}
        p = Project(**payload)
        assert p.vault_extra_xp == 9999
        assert p.nested_metadata == {"key": "value"}


class TestMutability:
    """Project must remain mutable (no frozen=True) so the sync layer can update fields."""

    def test_xp_points_can_be_mutated(self):
        p = Project(**_base_kwargs())
        p.xp_points = 500
        assert p.xp_points == 500

    def test_vault_path_can_be_mutated(self):
        p = Project(**_base_kwargs())
        p.vault_path = "/new/path.md"
        assert p.vault_path == "/new/path.md"

    def test_last_synced_at_can_be_mutated(self):
        p = Project(**_base_kwargs())
        new_ts = datetime(2026, 6, 30, 18, 30, 0)
        p.last_synced_at = new_ts
        assert p.last_synced_at == new_ts


class TestExistingFieldsPreserved:
    """Adding the 9 vault fields must NOT remove or change existing fields."""

    def test_existing_id_field_intact(self):
        p = Project(**_base_kwargs())
        assert p.id == "proj_vault_test"

    def test_existing_title_field_intact(self):
        p = Project(**_base_kwargs())
        assert p.title == "Vault Enrichment Test Project"

    def test_existing_status_default_backlog(self):
        p = Project(id="proj_x", title="Minimal Project Required Title")
        assert p.status == "backlog"

    def test_existing_revenue_impact_default_medium(self):
        p = Project(id="proj_x", title="Minimal Project Required Title")
        assert p.revenue_impact == "MEDIUM"