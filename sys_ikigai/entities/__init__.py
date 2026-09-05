"""Entities package — polymorphic PlanEntity + specialized subclasses."""

from __future__ import annotations

from sys_ikigai.entities.base import PlanEntity
from sys_ikigai.entities.opportunity import OpportunitySignal, OpportunityStatus
from sys_ikigai.entities.plan.deliverable import Deliverable
from sys_ikigai.entities.plan.dream import Dream
from sys_ikigai.entities.plan.goal import Goal
from sys_ikigai.entities.plan.objective import Objective
from sys_ikigai.entities.plan.project import Project
from sys_ikigai.entities.plan.task import Task
from sys_ikigai.entities.profile import IKIGAiProfile, ProfileSnapshot
from sys_ikigai.entities.regime import RegimeGraph, RegimeOverride, RegimeOverrideAudit
from sys_ikigai.entities.skill import SkillCategory, SkillLevel, SkillNode
from sys_ikigai.entities.vector import (
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
