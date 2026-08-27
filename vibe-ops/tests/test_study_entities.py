"""Unit tests for StudyProject entity vault enrichment fields.

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

from models.study_entities import StudyProject  # noqa: E402


def _base_kwargs(**overrides):
    base = dict(
        id="sp_vault_test",
        title="Vault Enrichment Study Project",
        domain="professional",
        ikigai_vector="skill",
        obsidian_index_note="/vault/notes/sp_vault_test.md",
        taskwarrior_project_key="vault_test",
    )
    base.update(overrides)
    return base


class TestVaultFieldDefaults:
    """All 9 new fields must have the documented defaults."""

    def test_xp_points_default_zero(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.xp_points == 0

    def test_mastery_level_default_beginner(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.mastery_level == "beginner"

    def test_subject_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.subject is None

    def test_learning_phase_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.learning_phase is None

    def test_tech_stack_default_empty_list(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.tech_stack == []

    def test_milestone_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.milestone is None

    def test_deliverable_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.deliverable is None

    def test_commercial_goal_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.commercial_goal is None

    def test_vault_path_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.vault_path is None

    def test_last_synced_at_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.last_synced_at is None


class TestVaultFieldAssignment:
    """All 9 new fields accept valid typed values."""

    def test_xp_points_positive_int(self):
        sp = StudyProject(**_base_kwargs(xp_points=2750))
        assert sp.xp_points == 2750

    def test_mastery_level_expert(self):
        sp = StudyProject(**_base_kwargs(mastery_level="expert"))
        assert sp.mastery_level == "expert"

    def test_subject_assigned(self):
        sp = StudyProject(**_base_kwargs(subject="Linear Algebra"))
        assert sp.subject == "Linear Algebra"

    def test_learning_phase_metalearning(self):
        sp = StudyProject(**_base_kwargs(learning_phase="metalearning"))
        assert sp.learning_phase == "metalearning"

    def test_learning_phase_direct_practice(self):
        sp = StudyProject(**_base_kwargs(learning_phase="direct_practice"))
        assert sp.learning_phase == "direct_practice"

    def test_learning_phase_iteration(self):
        sp = StudyProject(**_base_kwargs(learning_phase="iteration"))
        assert sp.learning_phase == "iteration"

    def test_tech_stack_assigned(self):
        sp = StudyProject(**_base_kwargs(tech_stack=["Rust", "Tokio", "SQLx"]))
        assert sp.tech_stack == ["Rust", "Tokio", "SQLx"]

    def test_milestone_date(self):
        milestone = date(2026, 12, 15)
        sp = StudyProject(**_base_kwargs(milestone=milestone))
        assert sp.milestone == milestone

    def test_deliverable_assigned(self):
        sp = StudyProject(**_base_kwargs(deliverable="Published paper"))
        assert sp.deliverable == "Published paper"

    def test_commercial_goal_assigned(self):
        sp = StudyProject(**_base_kwargs(commercial_goal="Course launch"))
        assert sp.commercial_goal == "Course launch"

    def test_vault_path_assigned(self):
        sp = StudyProject(
            **_base_kwargs(vault_path="/vault/study/sp_vault_test.md")
        )
        assert sp.vault_path == "/vault/study/sp_vault_test.md"

    def test_last_synced_at_datetime(self):
        synced = datetime(2026, 6, 30, 9, 0, 0)
        sp = StudyProject(**_base_kwargs(last_synced_at=synced))
        assert sp.last_synced_at == synced


class TestValidation:
    """Invalid values must raise ValidationError."""

    def test_invalid_mastery_level_raises(self):
        with pytest.raises(ValidationError):
            StudyProject(**_base_kwargs(mastery_level="master"))

    def test_invalid_learning_phase_raises(self):
        with pytest.raises(ValidationError):
            StudyProject(**_base_kwargs(learning_phase="drilling"))

    def test_invalid_xp_points_type_raises(self):
        with pytest.raises(ValidationError):
            StudyProject(**_base_kwargs(xp_points=[1, 2, 3]))


class TestExtraAllow:
    """Unknown extra fields must be accepted (extra='allow')."""

    def test_unknown_field_accepted(self):
        sp = StudyProject(
            **_base_kwargs(custom_obsidian_field="note-text", extra_score=42)
        )
        assert sp.custom_obsidian_field == "note-text"
        assert sp.extra_score == 42

    def test_dict_payload_extra_fields(self):
        payload = _base_kwargs()
        payload["vault_meta_xp"] = 7777
        payload["nested_links"] = {"primary": "tp_python_basics"}
        sp = StudyProject(**payload)
        assert sp.vault_meta_xp == 7777
        assert sp.nested_links == {"primary": "tp_python_basics"}


class TestMutability:
    """StudyProject must remain mutable (no frozen=True) so the sync layer can update fields."""

    def test_xp_points_can_be_mutated(self):
        sp = StudyProject(**_base_kwargs())
        sp.xp_points = 999
        assert sp.xp_points == 999

    def test_vault_path_can_be_mutated(self):
        sp = StudyProject(**_base_kwargs())
        sp.vault_path = "/new/study.md"
        assert sp.vault_path == "/new/study.md"

    def test_last_synced_at_can_be_mutated(self):
        sp = StudyProject(**_base_kwargs())
        new_ts = datetime(2026, 7, 1, 8, 15, 0)
        sp.last_synced_at = new_ts
        assert sp.last_synced_at == new_ts


class TestExistingFieldsPreserved:
    """Adding the 9 vault fields must NOT remove or change existing StudyProject fields."""

    def test_existing_id_field_intact(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.id == "sp_vault_test"

    def test_existing_title_field_intact(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.title == "Vault Enrichment Study Project"

    def test_existing_domain_field_intact(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.domain == "professional"

    def test_existing_ikigai_vector_field_intact(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.ikigai_vector == "skill"

    def test_existing_revenue_priority_default_zero(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.revenue_priority == 0.0

    def test_existing_obsidian_index_note_intact(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.obsidian_index_note == "/vault/notes/sp_vault_test.md"

    def test_existing_roadmap_id_default_none(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.roadmap_id is None

    def test_existing_taskwarrior_project_key_intact(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.taskwarrior_project_key == "vault_test"

    def test_existing_study_progress_pct_default_zero(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.study_progress_pct == 0.0

    def test_existing_dev_progress_pct_default_zero(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.dev_progress_pct == 0.0

    def test_existing_sync_status_default_aligned(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.sync_status == "aligned"

    def test_existing_tags_default_empty_list(self):
        sp = StudyProject(**_base_kwargs())
        assert sp.tags == []