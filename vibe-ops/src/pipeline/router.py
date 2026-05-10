from typing import Literal, Union
from pydantic import BaseModel
from models import (
    Project, Habit, Wave, Cycle, Phase, 
    StudyTopic, BacklogTask, RoadmapItem, StudyProject
)

class DataRouter:
    """
    Roteia entidades para os destinos corretos (SQL, Vector, ou Graph).
    """
    
    @staticmethod
    def get_destination(entity: BaseModel) -> Literal["sqlite", "chroma", "neo4j"]:
        if isinstance(entity, (Wave, Cycle, Phase, Habit)):
            return "sqlite"
        
        if isinstance(entity, (StudyProject, StudyTopic)):
            return "chroma"
            
        if isinstance(entity, (Project, RoadmapItem, BacklogTask)):
            return "sqlite"
            
        return "sqlite" 
