import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime
from pydantic import TypeAdapter, ValidationError
from contracts.roadmap_sync_v1 import RoadmapSyncPayload

class RoadmapSyncIngest:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.adapter = TypeAdapter(RoadmapSyncPayload)
        # Carrega versão do contrato para validação futura
        self.contract_version = "1.0.0"
    
    def __del__(self):
        if hasattr(self, 'db') and self.db:
            self.db.close()
            
    def apply_migration(self, sql_path: Path):
        """Aplica o schema do roadmap_sync caso não exista."""
        if sql_path.exists():
            self.db.executescript(sql_path.read_text())
            self.db.commit()

    def upsert(self, payload_dict: dict) -> dict:
        """Ingestão idempotente com validação de contrato."""
        try:
            # 1. Validar contra Pydantic v2
            payload = self.adapter.validate_python(payload_dict)
            
            # 2. Gerar upstream_id se não fornecido
            if not payload.upstream_id:
                hash_input = json.dumps(payload.model_dump(), sort_keys=True, default=str)
                payload.upstream_id = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            
            # 3. Upsert no SQLite
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO roadmap_sync (
                    task_uuid, description, project_key, status,
                    knowledge_prerequisites, cognitive_debt,
                    time_tracked_minutes, pomodoros_completed, energy_avg,
                    contract_version, upstream_id, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_uuid) DO UPDATE SET
                    description = excluded.description,
                    status = excluded.status,
                    knowledge_prerequisites = excluded.knowledge_prerequisites,
                    cognitive_debt = excluded.cognitive_debt,
                    time_tracked_minutes = excluded.time_tracked_minutes,
                    pomodoros_completed = excluded.pomodoros_completed,
                    energy_avg = excluded.energy_avg,
                    contract_version = excluded.contract_version,
                    upstream_id = excluded.upstream_id,
                    synced_at = CURRENT_TIMESTAMP
                WHERE excluded.upstream_id != roadmap_sync.upstream_id
            """, (
                payload.task_uuid, payload.description, payload.project_key, payload.status,
                json.dumps([kp.model_dump() for kp in payload.knowledge_prerequisites]),
                json.dumps(payload.cognitive_debt.model_dump()) if payload.cognitive_debt else None,
                payload.time_tracked_minutes, payload.pomodoros_completed, payload.energy_avg,
                self.contract_version, payload.upstream_id, datetime.utcnow()
            ))
            self.db.commit()
            
            return {"status": "success", "task_uuid": payload.task_uuid, "action": "inserted" if cursor.rowcount else "updated"}
            
        except ValidationError as e:
            return {"status": "contract_violation", "errors": e.errors()}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
