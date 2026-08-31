"""Entities package — polymorphic PlanEntity + specialized subclasses."""

from __future__ import annotations

from ikigai.entities.base import PlanEntity
from ikigai.entities.opportunity import OpportunitySignal, OpportunityStatus
from ikigai.entities.plan.deliverable import DeliverableEntity
from ikigai.entities.plan.dream import DreamEntity
from ikigai.entities.plan.goal import GoalEntity
from ikigai.entities.plan.objective import ObjectiveEntity
from ikigai.entities.plan.project import ProjectEntity
from ikigai.entities.plan.task import TaskEntity, TaskPriority, TaskStatus
from ikigai.entities.profile import IKIGAiProfile, ProfileSnapshot
from ikigai.entities.regime import RegimeGraph, RegimeOverride, RegimeOverrideAudit
from ikigai.entities.skill import SkillCategory, SkillLevel, SkillNode
from ikigai.entities.vector import (
    IKIGAiVectorEntity,
    VectorScorePoint,
    VectorTrend,
)

__all__ = [
    "DeliverableEntity",
    "DreamEntity",
    "GoalEntity",
    "IKIGAiProfile",
    "IKIGAiVectorEntity",
    "ObjectiveEntity",
    "OpportunitySignal",
    "OpportunityStatus",
    "PlanEntity",
    "ProfileSnapshot",
    "ProjectEntity",
    "RegimeGraph",
    "RegimeOverride",
    "RegimeOverrideAudit",
    "SkillCategory",
    "SkillLevel",
    "SkillNode",
    "TaskEntity",
    "TaskPriority",
    "TaskStatus",
    "VectorScorePoint",
    "VectorTrend",
]
