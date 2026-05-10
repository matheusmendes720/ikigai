from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import List, Optional, Literal

class KnowledgePrerequisite(BaseModel):
    study_topic_fk: str = Field(pattern=r'^tp_[a-z0-9_]+$')
    depth_required: int = Field(ge=0, le=5)
    depth_current: int = Field(ge=0, le=5)
    status: Literal['satisfied', 'deficit', 'ignored']
    evidence_ref: Optional[str] = None  # Ex: "cl_20260710_001" ou "note_abc"

class CognitiveDebt(BaseModel):
    level: Literal['none', 'low', 'medium', 'high', 'critical']
    interest_rate: float = Field(ge=0.0, le=1.0, description="Custo de adiar o estudo (0-1)")
    due_sprint: Optional[str] = Field(pattern=r'^S\d+_\d{4}$')
    reason: str = Field(min_length=10)

class RoadmapSyncPayload(BaseModel):
    """Payload validado para sync entre Obsidian StudyCluster ↔ TW Backlog"""
    task_uuid: str = Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    description: str = Field(min_length=5, max_length=500)
    project_key: str = Field(pattern=r'^S\d+\.O\d+\.[M\w.]+$')
    status: Literal['pending', 'waiting', 'completed', 'deleted']
    
    # Conexão com conhecimento
    knowledge_prerequisites: List[KnowledgePrerequisite] = Field(default_factory=list)
    cognitive_debt: Optional[CognitiveDebt] = None
    
    # Métricas de execução
    time_tracked_minutes: int = Field(ge=0, default=0)
    pomodoros_completed: int = Field(ge=0, default=0)
    energy_avg: float = Field(ge=0.0, le=10.0, default=7.0)
    
    # Controle de versão
    contract_version: str = Field(default="1.0.0")
    upstream_id: str = Field(min_length=12, max_length=12)  # SHA-256 truncated
    synced_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('knowledge_prerequisites')
    @classmethod
    def validate_depth_consistency(cls, v):
        for kp in v:
            if kp.depth_current > kp.depth_required:
                raise ValueError(f"depth_current ({kp.depth_current}) não pode exceder depth_required ({kp.depth_required})")
        return v
