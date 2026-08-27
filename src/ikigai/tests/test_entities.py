"""Tests for ikigai.entities — PlanEntity hierarchy."""

from __future__ import annotations

import pytest
from datetime import date, timedelta
from ikigai.entities import (
    PlanEntity,
    DreamEntity,
    GoalEntity,
    ObjectiveEntity,
    ProjectEntity,
    TaskEntity,
    TaskPriority,
    DeliverableEntity,
)
from ikigai.enums import EntityType, StatusType
from ikigai.types import UEID


def _ueid(suffix):
    return UEID.generate("study", "goal", suffix)


class TestPlanEntityBasics:

    def test_extra_allowed_by_default(self):
        """extra="allow" means arbitrary fields become model attributes directly."""
        data = {
            "entity_type": "goal",
            "slug": "test-goal",
            "title": "Test Goal",
            "status": "active",
            "ueid": str(_ueid("test-goal")),
            "horizon_days": 365,
            "ikigai_vectors": ["skill"],
            "custom_arbitrary_field": 42,
        }
        entity = PlanEntity.from_frontmatter_dict(data)
        assert entity.slug == "test-goal"
        # extra="allow" routes unknown fields as direct model attributes
        assert hasattr(entity, "custom_arbitrary_field")
        assert entity.custom_arbitrary_field == 42

    def test_discriminator_entity_type(self):
        goal = GoalEntity(
            ueid=_ueid("disc-test"),
            slug="disc-test",
            title="Disc Test",
            horizon_days=365,
        )
        assert goal.entity_type == EntityType.GOAL

    def test_parent_ueid_optional(self):
        goal = GoalEntity(
            ueid=_ueid("orphan-goal"),
            slug="orphan-goal",
            title="Orphan Goal",
            horizon_days=365,
        )
        assert goal.parent_ueid is None

    def test_parent_ueid_set(self):
        parent = UEID.generate("study", "dream", "test-dream")
        child = UEID.generate("study", "goal", "child-goal")
        goal = GoalEntity(
            ueid=child,
            slug="child-goal",
            title="Child Goal",
            horizon_days=365,
            parent_ueid=parent,
        )
        assert goal.parent_ueid == parent

    def test_related_ueids_empty_list(self):
        goal = GoalEntity(
            ueid=_ueid("no-related"),
            slug="no-related",
            title="No Related",
            horizon_days=365,
        )
        assert goal.related_ueids == []

    def test_related_ueids_multiple(self):
        u1 = UEID.generate("study", "goal", "goal-a")
        u2 = UEID.generate("study", "goal", "goal-b")
        goal = GoalEntity(
            ueid=_ueid("multi-related"),
            slug="multi-related",
            title="Multi Related",
            horizon_days=365,
            related_ueids=[u1, u2],
        )
        assert len(goal.related_ueids) == 2


class TestDreamEntity:

    def test_horizon_days_1825(self):
        d = DreamEntity(
            ueid=UEID.generate("study", "dream", "short-dream"),
            slug="short-dream",
            title="Short",
            horizon_days=1825,
            status=StatusType.SEED,
        )
        assert d.horizon_days == 1825

    def test_horizon_days_3650(self):
        d = DreamEntity(
            ueid=UEID.generate("study", "dream", "long-dream"),
            slug="long-dream",
            title="Long",
            horizon_days=3650,
            status=StatusType.ACTIVE,
        )
        assert d.horizon_days == 3650

    def test_horizon_days_too_short_fails(self):
        with pytest.raises(ValueError):
            DreamEntity(
                ueid=UEID.generate("study", "dream", "fail-dream"),
                slug="fail-dream",
                title="Fail",
                horizon_days=1000,
                status=StatusType.SEED,
            )

    def test_horizon_days_too_long_fails(self):
        with pytest.raises(ValueError):
            DreamEntity(
                ueid=UEID.generate("study", "dream", "fail-dream2"),
                slug="fail-dream2",
                title="Fail",
                horizon_days=4000,
                status=StatusType.SEED,
            )

    def test_motivation_optional(self):
        d = DreamEntity(
            ueid=UEID.generate("study", "dream", "no-motivation"),
            slug="no-motivation",
            title="No Motivation",
            horizon_days=1825,
            status=StatusType.SEED,
        )
        assert d.motivation is None

    def test_core_values_default_empty(self):
        d = DreamEntity(
            ueid=UEID.generate("study", "dream", "cv-test"),
            slug="cv-test",
            title="CV Test",
            horizon_days=1825,
            status=StatusType.SEED,
        )
        assert d.core_values == []


class TestGoalEntity:

    def test_horizon_days_valid_365(self):
        g = GoalEntity(
            ueid=UEID.generate("study", "goal", "valid-goal"),
            slug="valid-goal",
            title="Valid",
            horizon_days=365,
        )
        assert g.horizon_days == 365

    def test_horizon_days_valid_730(self):
        g = GoalEntity(
            ueid=UEID.generate("study", "goal", "valid-goal-730"),
            slug="valid-goal-730",
            title="Valid 730",
            horizon_days=730,
        )
        assert g.horizon_days == 730

    def test_horizon_days_invalid_fails(self):
        with pytest.raises(ValueError):
            GoalEntity(
                ueid=UEID.generate("study", "goal", "fail-goal"),
                slug="fail-goal",
                title="Fail",
                horizon_days=500,
            )

    def test_description_optional(self):
        g = GoalEntity(
            ueid=UEID.generate("study", "goal", "no-desc"),
            slug="no-desc",
            title="No Desc",
            horizon_days=365,
        )
        assert g.description is None

    def test_success_metrics_default_empty(self):
        g = GoalEntity(
            ueid=UEID.generate("study", "goal", "sm-test"),
            slug="sm-test",
            title="SM Test",
            horizon_days=365,
        )
        assert g.success_metrics == []


class TestObjectiveEntity:

    def test_horizon_days_range(self):
        o = ObjectiveEntity(
            ueid=UEID.generate("study", "objective", "valid-obj"),
            slug="valid-obj",
            title="Valid",
            horizon_days=90,
        )
        assert o.horizon_days == 90

    def test_horizon_days_too_short_fails(self):
        with pytest.raises(ValueError):
            ObjectiveEntity(
                ueid=UEID.generate("study", "objective", "fail-obj"),
                slug="fail-obj",
                title="Fail",
                horizon_days=30,
            )

    def test_key_results_empty_by_default(self):
        o = ObjectiveEntity(
            ueid=UEID.generate("study", "objective", "no-kr"),
            slug="no-kr",
            title="No KR",
            horizon_days=180,
        )
        assert o.key_results == []

    def test_progress_pct_defaults_zero(self):
        o = ObjectiveEntity(
            ueid=UEID.generate("study", "objective", "no-progress"),
            slug="no-progress",
            title="No Progress",
            horizon_days=180,
        )
        assert o.progress_pct == 0.0


class TestProjectEntity:

    def test_tech_stack_empty_by_default(self):
        p = ProjectEntity(
            ueid=UEID.generate("work", "project", "proj"),
            slug="proj",
            title="Proj",
            horizon_days=30,
            status=StatusType.ACTIVE,
        )
        assert p.tech_stack == []

    def test_actual_revenue_defaults_zero(self):
        p = ProjectEntity(
            ueid=UEID.generate("work", "project", "proj2"),
            slug="proj2",
            title="Proj2",
            horizon_days=30,
            status=StatusType.ACTIVE,
        )
        assert p.actual_revenue_brl == 0.0


class TestTaskEntity:

    def test_rice_fields_default(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "task"),
            slug="task",
            title="Task",
            horizon_days=7,
            status=StatusType.DRAFT,
        )
        assert t.rice_reach == 1.0
        assert t.rice_impact == 0.5
        assert t.rice_confidence == 0.8
        assert t.rice_effort_h == 1.0

    def test_rice_score_effort_guard(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "task2"),
            slug="task2",
            title="Task2",
            horizon_days=7,
            status=StatusType.DRAFT,
            rice_reach=8.0,
            rice_impact=0.5,
            rice_confidence=0.8,
            rice_effort_h=0.0,
        )
        # max(effort, 0.5) = 0.5; score = (8 * 0.5 * 0.8) / 0.5 = 6.4
        assert t.rice_score == 6.4

    def test_rice_score_computed(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "task3"),
            slug="task3",
            title="Task3",
            horizon_days=7,
            status=StatusType.DRAFT,
            rice_reach=8.0,
            rice_impact=0.5,
            rice_confidence=0.8,
            rice_effort_h=4.0,
        )
        expected = (8.0 * 0.5 * 0.8) / 4.0
        assert t.rice_score == expected

    def test_rice_score_returns_float(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "task4"),
            slug="task4",
            title="Task4",
            horizon_days=7,
            status=StatusType.DRAFT,
        )
        assert isinstance(t.rice_score, float)

    def test_due_date_optional(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "task5"),
            slug="task5",
            title="Task5",
            horizon_days=7,
            status=StatusType.DRAFT,
        )
        assert t.due_date is None

    def test_task_priority_defaults_medium(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "task6"),
            slug="task6",
            title="Task6",
            horizon_days=7,
            status=StatusType.DRAFT,
        )
        assert t.priority == TaskPriority.MEDIUM


class TestDeliverableEntity:

    def test_artifact_path_optional(self):
        d = DeliverableEntity(
            ueid=UEID.generate("work", "deliverable", "del"),
            slug="del",
            title="Del",
            horizon_days=1,
            status=StatusType.DRAFT,
        )
        assert d.artifact_path is None


class TestEntityFrontmatterRoundtrip:

    def _roundtrip(self, entity):
        d = entity.to_frontmatter_dict()
        return type(entity).from_frontmatter_dict(d)

    def test_goal_roundtrip(self):
        g = GoalEntity(
            ueid=UEID.generate("study", "goal", "roundtrip-goal"),
            slug="roundtrip-goal",
            title="Roundtrip Goal",
            horizon_days=365,
        )
        restored = self._roundtrip(g)
        assert restored.slug == g.slug
        assert restored.title == g.title
        assert restored.horizon_days == g.horizon_days

    def test_objective_roundtrip(self):
        o = ObjectiveEntity(
            ueid=UEID.generate("study", "objective", "roundtrip-obj"),
            slug="roundtrip-obj",
            title="Roundtrip Obj",
            horizon_days=180,
            key_results=["KR1", "KR2"],
            progress_pct=33.0,
        )
        restored = self._roundtrip(o)
        assert restored.slug == o.slug
        assert restored.key_results == o.key_results

    def test_task_roundtrip(self):
        t = TaskEntity(
            ueid=UEID.generate("work", "task", "roundtrip-task"),
            slug="roundtrip-task",
            title="Roundtrip Task",
            horizon_days=7,
            status=StatusType.DRAFT,
            rice_reach=5.0,
            rice_impact=1.0,
            rice_confidence=0.9,
            rice_effort_h=2.0,
            priority=TaskPriority.HIGH,
        )
        restored = self._roundtrip(t)
        assert restored.slug == t.slug
        assert restored.priority == t.priority
        assert restored.rice_reach == t.rice_reach
