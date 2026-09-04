"""Entities package — polymorphic PlanEntity + specialized subclasses."""

from __future__ import annotations

from ikigai.entities.base import PlanEntity
from ikigai.entities.opportunity import OpportunitySignal, OpportunityStatus
from ikigai.entities.plan.deliverable import Deliverable
from ikigai.entities.plan.dream import Dream
from ikigai.entities.plan.goal import Goal
from ikigai.entities.plan.objective import Objective
from ikigai.entities.plan.project import Project
from ikigai.entities.plan.task import Task
from ikigai.entities.profile import IKIGAiProfile, ProfileSnapshot
from ikigai.entities.regime import RegimeGraph, RegimeOverride, RegimeOverrideAudit
from ikigai.entities.skill import SkillCategory, SkillLevel, SkillNode
from ikigai.entities.vector import (
    IKIGAiVectorEntity,
    VectorScorePoint,
    VectorTrend,
)

__all__ = [
    "Deliverable",
    "Dream",
    "Goal",
    "IKIGAiProfile",
    "IKIGAiVectorEntity",
    "Objective",
    "OpportunitySignal",
    "OpportunityStatus",
    "PlanEntity",
    "ProfileSnapshot",
    "Project",
    "RegimeGraph",
    "RegimeOverride",
    "RegimeOverrideAudit",
    "SkillCategory",
    "SkillLevel",
    "SkillNode",
    "Task",
    "VectorScorePoint",
    "VectorTrend",
]
