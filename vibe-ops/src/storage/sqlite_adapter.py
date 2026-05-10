import sqlite3
import json
from pathlib import Path
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

class SQLiteAdapter:
    """
    Adaptador SQLite para persistência do Data Mesh.
    Garante a integridade referencial e o UEID (Unified Entity ID).
    """

    def __init__(self, db_path: str = "vibe_ops.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Inicializa o banco de dados usando o schema.sql."""
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            return
            
        with open(schema_path, "r") as f:
            schema_script = f.read()
            
        with self._get_connection() as conn:
            conn.executescript(schema_script)

    def save_entity(self, entity: BaseModel):
        """
        Salva genericamente qualquer entidade baseada nos modelos Pydantic.
        """
        entity_type = getattr(entity, "entity_type", None)
        if not entity_type:
            entity_type = entity.__class__.__name__.lower()

        table_map = {
            "wave": "temporal_waves",
            "cycle": "temporal_cycles",
            "phase": "temporal_phases",
            "study_project": "study_projects",
            "study_topic": "study_topics",
            "study_material": "study_materials",
            "study_session": "study_sessions",
            "project": "dev_projects",
            "roadmap_item": "dev_roadmaps",
            "backlog_task": "dev_backlogs",
            "changelog_entry": "dev_changelogs",
            "habit": "habits",
            "daily_metrics": "metrics_daily"
        }

        table_name = table_map.get(entity_type)
        if not table_name:
            return

        data = entity.model_dump()
        
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                data[key] = json.dumps(value)
            elif isinstance(value, (date, datetime)):
                data[key] = value.isoformat()

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        with self._get_connection() as conn:
            conn.execute(sql, list(data.values()))

    def get_entity(self, table: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Busca uma entidade pelo ID."""
        sql = f"SELECT * FROM {table} WHERE id = ?"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(sql, (entity_id,)).fetchone()
            if row:
                return dict(row)
        return None
