from datetime import date
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

class Habit(BaseModel):
    """
    Entidade de Hábito: Ativo biológico/cognitivo que gera performance.
    """
    id: str = Field(pattern=r'^h_[a-z0-9_]+$')
    name: str = Field(min_length=3, max_length=100)
    entity_type: Literal["habit"] = "habit"
    category: Literal["biological", "cognitive", "productive", "ritual"]
    
    # Parâmetros Cibernéticos
    resistance: float = Field(ge=0.0, le=10.0, description="Dificuldade inicial de execução")
    lambda_learning: float = Field(ge=0.01, le=0.5, default=0.1, description="Taxa de aprendizado/automação")
    weight_in_qhe: float = Field(ge=0.0, le=1.0, default=0.1, description="Peso no Q_HE")
    
    status: Literal["active", "paused", "archived"] = "active"
    created_at: date
    
    # State tracking
    streak_current: int = 0
    streak_previous: int = 0
    
    @property
    def habit_level(self) -> float:
        """H(t) = 1 - e^(-lambda * streak)"""
        import math
        return 1 - math.exp(-self.lambda_learning * self.streak_current)

    @property
    def energy_required(self) -> float:
        """E_req = R * (1 - H(t))"""
        return self.resistance * (1 - self.habit_level)
