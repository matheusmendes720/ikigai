import subprocess
import json
from typing import List, Dict, Any
from models import Project, Skill

class TaskwarriorSyncAdapter:
    """
    Facade para sincronização entre o Data Mesh e o Taskwarrior.
    """
    def __init__(self):
        pass

    def full_pull(self) -> List[Dict[str, Any]]:
        return []

    def full_push(self, entities: List[Any]):
        pass
