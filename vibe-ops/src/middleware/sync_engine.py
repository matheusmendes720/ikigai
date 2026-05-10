import sqlite3, json, hashlib
from pathlib import Path
from datetime import datetime
from tasklib import TaskWarrior
import frontmatter
from pydantic import TypeAdapter

from contracts.sync_contract_v1 import SyncContractV1
from schemas.pydantic_v2 import TaskPayload, StudyPlanEntity

class SyncEngine:
    def __init__(self, vault_path: Path, db_path: Path, tw_path: Path, tw_client=None):
        self.contract = SyncContractV1()
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.tw = tw_client if tw_client is not None else TaskWarrior(str(tw_path))
        self.vault = vault_path
        self.adapter_payload = TypeAdapter(TaskPayload)
        self.adapter_study = TypeAdapter(StudyPlanEntity)

    def compute_upstream_id(self, payload: dict) -> str:
        """Gera hash idempotente truncado (12 chars)"""
        normalized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]

    def sync_obsidian_to_sqlite(self, folder: str = "2_projeto") -> dict:
        """Ingestão idempotente de Frontmatter → SQLite"""
        stats = {"ingested": 0, "skipped": 0, "triaged": 0}
        
        for md_file in (self.vault / folder).rglob("*.md"):
            post = frontmatter.load(md_file)
            if "entity_type" not in post.metadata:
                continue
                
            payload = post.metadata
            upstream_id = self.compute_upstream_id(payload)
            
            # Verificar idempotência
            cursor = self.db.cursor()
            cursor.execute("SELECT upstream_id FROM planning_entities WHERE id = ? AND entity_type = ?", 
                          (payload.get("id"), payload.get("entity_type")))
            existing = cursor.fetchone()
            if existing and existing["upstream_id"] == upstream_id:
                stats["skipped"] += 1
                continue
                
            # Upsert com resolução de FK
            cursor.execute("""
                INSERT INTO planning_entities (id, entity_type, payload_json, upstream_id, synced_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id, entity_type) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    upstream_id = excluded.upstream_id,
                    synced_at = CURRENT_TIMESTAMP
                WHERE excluded.upstream_id != planning_entities.upstream_id
            """, (payload["id"], payload["entity_type"], json.dumps(payload), upstream_id, datetime.utcnow()))
            
            stats["ingested"] += 1
            
        self.db.commit()
        return stats

    def sync_sqlite_to_taskwarrior(self, policy_state: str = "MAINTAIN") -> dict:
        """Injeção segura no TW respeitando orçamento cognitivo"""
        stats = {"created": 0, "updated": 0, "throttled": 0}
        
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT pe.payload_json, rs.id as sync_id FROM planning_entities pe
            JOIN roadmap_sync rs ON pe.id = rs.study_plan_fk
            WHERE pe.entity_type = 'study_plan' AND rs.status = 'pending'
        """)
        
        for row in cursor.fetchall():
            plan = json.loads(row[0])
            sync_id = row[1]
            adapter = TypeAdapter(StudyPlanEntity)
            study_plan = adapter.validate_python(plan)
            
            # Throttle baseado em PolicyState
            if policy_state == "RECOVERY" and study_plan.daily_target_minutes > 60:
                stats["throttled"] += 1
                continue
                
            # Gerar payload TW
            tw_payload = TaskPayload(
                description=f"[Estudo] {study_plan.title}",
                project=study_plan.tw_project_key,  # S1.O2.study_backend_01
                tags=["study", f"policy:{policy_state.lower()}"],
                upstream_id=self.compute_upstream_id(plan),
                study_plan_id=study_plan.id
            )
            
            # Injetar no TW
            existing = self.tw.tasks.filter(upstream_id=tw_payload.upstream_id)
            if existing:
                task = existing[0]
                cursor.execute("UPDATE roadmap_sync SET tw_uuid = ?, last_synced = CURRENT_TIMESTAMP WHERE id = ?", (task['uuid'], sync_id))
                stats["updated"] += 1
            else:
                task = self.tw.tasks.add(
                    description=tw_payload.description,
                    project=tw_payload.project,
                    tags=tw_payload.tags
                )
                task["upstream_id"] = tw_payload.upstream_id
                task["study_plan_id"] = tw_payload.study_plan_id
                task.save()
                cursor.execute("UPDATE roadmap_sync SET tw_uuid = ?, last_synced = CURRENT_TIMESTAMP WHERE id = ?", (task['uuid'], sync_id))
                stats["created"] += 1
                
        self.db.commit()
        return stats

    def sync_taskwarrior_to_sqlite(self) -> dict:
        """Syncs completed tasks from Taskwarrior back to SQLite"""
        stats = {"completed": 0, "errors": 0}
        
        cursor = self.db.cursor()
        # Find tasks in SQLite that are pending
        cursor.execute("SELECT id, tw_uuid FROM roadmap_sync WHERE status = 'pending' AND tw_uuid IS NOT NULL")
        pending_records = cursor.fetchall()
        
        for record in pending_records:
            try:
                task = self.tw.tasks.get(uuid=record['tw_uuid'])
                if task['status'] == 'completed':
                    cursor.execute(
                        "UPDATE roadmap_sync SET status = 'completed', last_synced = CURRENT_TIMESTAMP WHERE id = ?",
                        (record['id'],)
                    )
                    stats["completed"] += 1
            except Exception as e:
                # Task not found or other error
                stats["errors"] += 1
                
        self.db.commit()
        return stats
