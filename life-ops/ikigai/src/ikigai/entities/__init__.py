"""Entities package — polymorphic PlanEntity + specialized subclasses."""

from __future__ import annotations

from ikigai.entities.base import PlanEntity
from ikigai.entities.profile import IKIGAiProfile, ProfileSnapshot
from ikigai.entities.skill import SkillNode, SkillLevel, SkillCategory
from ikigai.entities.opportunity import OpportunitySignal, OpportunityStatus
from ikigai.entities.regime import RegimeGraph, RegimeOverride, RegimeOverrideAudit
from ikigai.entities.vector import (
    IKIGAiVectorEntity,
    VectorScorePoint,
    VectorTrend,
)
from ikigai.entities.plan.dream import DreamEntity
from ikigai.entities.plan.goal import GoalEntity
from ikigai.entities.plan.objective import ObjectiveEntity
from ikigai.entities.plan.project import ProjectEntity
from ikigai.entities.plan.task import TaskEntity, TaskPriority, TaskStatus
from ikigai.entities.plan.deliverable import DeliverableEntity

__all__ = [
    "PlanEntity",
    "IKIGAiProfile",
    "ProfileSnapshot",
    "SkillNode",
    "SkillLevel",
    "SkillCategory",
    "OpportunitySignal",
    "OpportunityStatus",
    "RegimeGraph",
    "RegimeOverride",
    "RegimeOverrideAudit",
    "IKIGAiVectorEntity",
    "VectorScorePoint",
    "VectorTrend",
    "DreamEntity",
    "GoalEntity",
    "ObjectiveEntity",
    "ProjectEntity",
    "TaskEntity",
    "TaskPriority",
    "TaskStatus",
    "DeliverableEntity",
]
