from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class PolicyState(str, Enum):  # noqa: UP042 - keep (str, Enum) member repr for DB payloads
    PUSH = "PUSH"
    MAINTAIN = "MAINTAIN"
    REDUCE = "REDUCE"
    RECOVER = "RECOVER"
    RECOVERY = "RECOVERY"  # alias legado


class PolicyDecision(BaseModel):
    date: date
    policy: PolicyState
    qhe: float
    c_comp: float
    infrações_24h: int
    tipo_dia: str
    hardwork_budget_hours: float
    pause_duration_minutes: int
    sleep_target_hours: float
    recomendacoes: list[str]
    alertas: list[str]
    days_in_current_policy: int
    policy_prev: PolicyState | None = None
    computed_at: datetime


class QHEMetrics(BaseModel):
    # Standard metrics payload if used elsewhere
    qhe: float
    c_comp: float
    date: date


class TaskPayload(BaseModel):
    description: str
    project: str
    tags: list[str]
    upstream_id: str
    study_plan_id: str


class StudyPlanEntity(BaseModel):
    id: str
    title: str
    tw_project_key: str
    daily_target_minutes: int
    work_ratio: float | None = None
    target_clr: float | None = None
