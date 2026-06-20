from datetime import date
from typing import Literal, List, Optional
from pydantic import BaseModel, Field, model_validator

class DailyKnowledgeReport(BaseModel):
    """
    DailyKnowledgeReport: Correlates abstract learning with execution telemetry.
    Acts as a daily roll-up of mental models applied in real-world engineering.
    """
    id: str = Field(pattern=r'^kr_\d{8}$')  # ex: kr_20260518
    date: date
    entity_type: Literal["knowledge_report"] = "knowledge_report"
    
    # Study Inputs
    study_hours: float = Field(ge=0.0, default=0.0)
    mental_models_studied: List[str] = Field(default_factory=list)
    
    # Execution Outputs (Telemetry)
    mental_models_applied: List[str] = Field(default_factory=list)
    code_execution_links: List[str] = Field(default_factory=list, description="Links to PRs/Commits")
    
    # KPIs
    consolidation_kpi: float = Field(ge=0.0, le=1.0, default=0.0)
    
    @model_validator(mode='after')
    def compute_consolidation_kpi(self) -> 'DailyKnowledgeReport':
        """
        Calculates how well study translates into execution.
        Basic heuristic: ratio of applied models vs studied models, capped at 1.0.
        Plus a bonus if code execution links exist.
        """
        score = 0.0
        
        # Calculate ratio of applied vs studied (if any were studied)
        if self.mental_models_studied:
            studied_set = set(self.mental_models_studied)
            applied_set = set(self.mental_models_applied)
            
            # Intersection (models studied AND applied today)
            direct_applications = len(studied_set.intersection(applied_set))
            
            ratio = direct_applications / len(studied_set)
            score += ratio * 0.7  # 70% of score comes from direct application
            
        # 30% of score comes from just executing code linked to ANY mental model
        if self.code_execution_links and self.mental_models_applied:
            score += 0.3
            
        # If no models were studied today, but models were applied, they are pulling from past knowledge
        if not self.mental_models_studied and self.mental_models_applied:
             score = 1.0 # Excellent consolidation of past knowledge
             
        self.consolidation_kpi = min(1.0, max(0.0, score))
        return self
