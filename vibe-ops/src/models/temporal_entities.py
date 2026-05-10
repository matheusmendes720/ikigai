from datetime import date, timedelta
from typing import Literal, List, Optional
from pydantic import BaseModel, Field, model_validator

class Wave(BaseModel):
    """
    Nível 3.1 da hierarquia: Onda (Wave).
    Horizonte: Quinzenal (15 dias).
    Foco: Consolidação de hábitos e sprints técnicos.
    """
    id: str = Field(pattern=r'^W\d+_[A-Za-z]{3}_\d{4}$') # ex: W1_May_2026
    title: str = Field(min_length=5, max_length=100)
    entity_type: Literal["wave"] = "wave"
    status: Literal["active", "completed", "pending"] = "pending"
    start_date: date
    duration_days: int = Field(default=15, frozen=True)
    wave_number: int = Field(ge=1, le=3) # Onda 1, 2 ou 3 do Ciclo
    parent_cycle: str = Field(pattern=r'^C\d+_[A-Za-z]{3}_\d{4}$')
    parent_objective: Optional[str] = None # FK -> Objective
    
    # Métricas calculadas (Scorecards)
    c_comp: float = Field(default=0.0, ge=0.0, le=1.0) # Consistency score
    ic: float = Field(default=0.0, ge=0.0, le=1.0) # Index of consistency
    
    tags: List[str] = Field(default_factory=list)

    @property
    def expected_end(self) -> date:
        return self.start_date + timedelta(days=self.duration_days)

class Cycle(BaseModel):
    """
    Nível 3 da hierarquia: Ciclo (Cycle).
    Horizonte: 45 dias (3 ondas).
    """
    id: str = Field(pattern=r'^C\d+_[A-Za-z]{3}_\d{4}$')
    title: str = Field(min_length=5, max_length=100)
    entity_type: Literal["cycle"] = "cycle"
    status: Literal["active", "completed", "pending"] = "pending"
    start_date: date
    cycle_number: int = Field(ge=1, le=4)
    parent_phase: str = Field(pattern=r'^PH\d+_\d{4}$')
    parent_objective: Optional[str] = None
    aligned_half_quarter: Literal["HQ1", "HQ2"]
    
    tags: List[str] = Field(default_factory=list)

class Phase(BaseModel):
    """
    Nível 2 da hierarquia: Fase (Phase).
    Horizonte: 180 dias (2 quarters / 4 ciclos).
    """
    id: str = Field(pattern=r'^PH\d+_\d{4}$')
    title: str = Field(min_length=5, max_length=100)
    entity_type: Literal["phase"] = "phase"
    status: Literal["active", "completed", "pending"] = "pending"
    start_date: date
    phase_number: int = Field(ge=1, le=2)
    parent_dream: str = Field(pattern=r'^S\d+$') # FK -> Dream (S1, S2...)
    aligned_quarter_start: Literal["Q1", "Q2", "Q3", "Q4"]
    aligned_quarter_end: Literal["Q1", "Q2", "Q3", "Q4"]
    
    tags: List[str] = Field(default_factory=list)
