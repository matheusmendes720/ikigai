from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class PolicyState(str, Enum):
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
    recomendacoes: List[str]
    alertas: List[str]
    days_in_current_policy: int
    policy_prev: Optional[PolicyState] = None
    computed_at: datetime

class QHEMetrics(BaseModel):
    # Standard metrics payload if used elsewhere
    qhe: float
    c_comp: float
    date: date

class TaskPayload(BaseModel):
    description: str
    project: str
    tags: List[str]
    upstream_id: str
    study_plan_id: str

class StudyPlanEntity(BaseModel):
    id: str
    title: str
    tw_project_key: str
    daily_target_minutes: int
    work_ratio: Optional[float] = None
    target_clr: Optional[float] = None
