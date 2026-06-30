import datetime as _dt
from datetime import date, datetime, time
from typing import Literal, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


def _today() -> date:
    return _dt.date.today()


class StudyProject(BaseModel):
    """
    StudyProject: Agrupador de alto nível para clusters de estudo.
    """
    model_config = ConfigDict(extra="allow")

    id: str = Field(pattern=r'^sp_[a-z0-9_]+$')
    title: str = Field(min_length=3, max_length=200)
    domain: Literal["professional", "personal"]
    ikigai_vector: Literal["passion", "skill", "market", "revenue"]
    revenue_priority: float = Field(ge=0.0, le=1.0, default=0.0)
    obsidian_index_note: str
    roadmap_id: Optional[str] = Field(None, pattern=r'^rm_[a-z0-9_]+$')
    taskwarrior_project_key: str
    anchor_wave: Optional[str] = Field(None, pattern=r'^W\d+_[A-Za-z]{3}_\d{4}$')
    anchor_cycle: Optional[str] = Field(None, pattern=r'^C\d+_[A-Za-z]{3}_\d{4}$')
    study_progress_pct: float = Field(ge=0.0, le=100.0, default=0.0)
    dev_progress_pct: float = Field(ge=0.0, le=100.0, default=0.0)
    sync_status: Literal["aligned", "study_ahead", "dev_ahead", "drift"] = "aligned"
    tags: List[str] = Field(default_factory=list)
    created: date = Field(default_factory=_today)
    updated: date = Field(default_factory=_today)

    xp_points: int = 0
    mastery_level: Literal["beginner", "intermediate", "advanced", "expert"] = "beginner"
    subject: Optional[str] = None
    learning_phase: Optional[Literal["metalearning", "direct_practice", "retrieval", "iteration"]] = None
    tech_stack: List[str] = Field(default_factory=list)
    milestone: Optional[date] = None
    deliverable: Optional[str] = None
    commercial_goal: Optional[str] = None
    vault_path: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class CognitiveDebt(BaseModel):
    level: Literal["low", "medium", "high", "critical"] = "low"
    reason: str = ""
    due_sprint: Optional[str] = None
    interest_rate: float = Field(ge=0.0, le=1.0, default=0.0)


class StudyTopic(BaseModel):
    """
    StudyTopic: Unidade atômica de conhecimento no mesh epistêmico.
    """
    id: str = Field(pattern=r'^tp_[a-z0-9_]+$')
    title: str = Field(min_length=3, max_length=200)
    parent_study_project: str = Field(pattern=r'^sp_[a-z0-9_]+$')
    prerequisites: List[str] = Field(default_factory=list)
    importance_level: Literal["primary", "secondary", "tertiary"] = "primary"
    depth_level: float = Field(ge=0.0, le=5.0, default=0.0)
    target_depth: int = Field(ge=1, le=5, default=3)
    cognitive_debt: CognitiveDebt = Field(default_factory=CognitiveDebt)
    status: Literal["active", "paused", "completed", "backlog", "in_progress", "review_concept", "deferred"] = "backlog"


class StudyMaterial(BaseModel):
    id: str = Field(pattern=r'^sm_[a-z0-9_]+$')
    title: str = Field(min_length=3, max_length=300)
    entity_type: Literal["study_material"] = "study_material"
    material_type: Literal["book", "course", "video", "article", "documentation", "project"]
    topic_id: str
    status: Literal["unread", "reading", "completed", "reference"] = "unread"
    completed_minutes: int = Field(ge=0, default=0)
    estimated_minutes: Optional[int] = None


class StudyNoteIndex(BaseModel):
    id: str = Field(pattern=r'^note_[a-z0-9_]+$')
    obsidian_path: str
    topic_id: Optional[str] = None
    abstraction_level: Literal["theoretical", "practical", "artifact"] = "practical"


class StudySession(BaseModel):
    id: str = Field(pattern=r'^ss_[a-z0-9_]+$')
    topic_id: str
    date: date
    start_time: time
    end_time: Optional[time] = None
    duration_minutes: Optional[int] = None

    @model_validator(mode='after')
    def compute_duration(self) -> 'StudySession':
        if self.end_time and self.start_time and not self.duration_minutes:
            start = datetime.combine(self.date, self.start_time)
            end = datetime.combine(self.date, self.end_time)
            self.duration_minutes = int((end - start).total_seconds() / 60)
        return self
