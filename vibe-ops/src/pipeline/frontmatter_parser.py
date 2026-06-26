import yaml
import re
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, ValidationError
from models import (
    Wave, Cycle, Phase, Habit, StudyMaterial, StudyTopic,
    StudySession, Project, Skill, RoadmapItem,
    BacklogTask, ChangelogEntry, SleepRecord, HealthMetrics,
    DailyMetrics, ReviewEvent, PolicyDecision, DecisionRecord, TimeBlock,
    StudyProject, StudyNoteIndex, DocBackend, DocFrontend, PriorityMatrix, CyberneticFeedback,
    PeriodReport,
)

class FrontmatterParser:
    """
    Parser para extrair e validar metadados YAML de arquivos Markdown.
    """
    
    MODEL_MAP: Dict[str, Type[BaseModel]] = {
        "wave": Wave,
        "cycle": Cycle,
        "phase": Phase,
        "habit": Habit,
        "study_material": StudyMaterial,
        "study_topic": StudyTopic,
        "study_session": StudySession,
        "study_project": StudyProject,
        "project": Project,
        "skill": Skill,
        "roadmap_item": RoadmapItem,
        "backlog_task": BacklogTask,
        "changelog_entry": ChangelogEntry,
        "sleep_record": SleepRecord,
        "health_metrics": HealthMetrics,
        "daily_metrics": DailyMetrics,
        "review_event": ReviewEvent,
        "policy_decision": PolicyDecision,
        "decision_record": DecisionRecord,
        "time_block": TimeBlock,
        "period_report": PeriodReport,
    }

    FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

    @classmethod
    def parse_file(cls, file_path: str) -> Optional[BaseModel]:
        """
        Lê um arquivo .md, extrai o frontmatter e valida contra o modelo Pydantic.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        match = cls.FRONTMATTER_PATTERN.match(content)
        if not match:
            return None
            
        try:
            raw_data = yaml.safe_load(match.group(1))
            if not isinstance(raw_data, dict):
                return None
                
            entity_type = raw_data.get("entity_type")
            if not entity_type or entity_type not in cls.MODEL_MAP:
                return None
                
            model_cls = cls.MODEL_MAP[entity_type]
            return model_cls(**raw_data)
            
        except (yaml.YAMLError, ValidationError) as e:
            print(f"Erro ao processar {file_path}: {e}")
            return None
            
    @classmethod
    def extract_raw(cls, content: str) -> Optional[Dict[str, Any]]:
        """Apenas extrai o dicionário YAML sem validar."""
        match = cls.FRONTMATTER_PATTERN.match(content)
        if match:
            return yaml.safe_load(match.group(1))
        return None
