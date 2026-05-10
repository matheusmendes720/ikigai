import json
import hashlib
from typing import Dict, Any, List
from models import StudyProject, Project

class FKResolver:
    """
    Registry em memória para auditoria de órfãs e chaves hierárquicas.
    """
    FK_SCHEMA = {
        "study_topic": "parent_study_project",
        "dev_backlog": "roadmap_fk",
        "dev_roadmap": "study_project_fk"
    }

    def validate(self, entity_type: str, payload: Dict[str, Any]) -> bool:
        return True

def compute_upstream_id(entity_type: str, entity_id: str, title: str = "") -> str:
    seed = f"{entity_type}:{entity_id}:{title}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:12]
