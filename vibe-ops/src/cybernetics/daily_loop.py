from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional
from pydantic import TypeAdapter
from schemas.pydantic_v2 import PolicyState, PolicyDecision, QHEMetrics
from pipeline.rag_indexer import HybridRAGIndexer
from middleware.sync_engine import SyncEngine
from pipeline.policy_engine import PolicyEngine
from pipeline.ikigai_scorer import IkigaiScorer
import sqlite3, json

class CyberneticDailyLoop:
    def __init__(self, db_path, tw_path, vault_path, tw_client=None):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.vault_path = vault_path
        self.sync = SyncEngine(vault_path, db_path, tw_path, tw_client=tw_client)
        self.indexer = HybridRAGIndexer(db_path=db_path)
        self.policy_engine = PolicyEngine()
        self.ikigai = IkigaiScorer(db_path=db_path)
        
    def execute_daily_cycle(self, target_date: date) -> PolicyDecision:
        """Executa o ciclo completo Target-Sensor-Adjuster"""
        
        # 1. TARGET: Definir meta do dia (usa Ikigai)
        target = self._compute_target(target_date)
        
        # 2. SENSOR: Capturar execução real
        metrics = self._read_sensor_data(target_date)
        
        # 3. ADJUSTER: Aplicar correção cibernética (usa PolicyEngine)
        prev_decision = self._get_previous_decision(target_date)
        decision = self.policy_engine.evaluate(metrics, prev_decision, target_date)
        
        # 4. PERSIST & SYNC
        self._persist_decision(decision)
        self.sync.sync_sqlite_to_taskwarrior(decision.policy.value)
        
        # 5. SEMANTIC INDEXING (Hybrid RAG)
        self.indexer.index_vault(self.vault_path)
        
        return decision

    def _get_previous_decision(self, target_date: date) -> Optional[PolicyDecision]:
        """Recupera a última decisão persistida."""
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM policy_decisions ORDER BY date DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None
        
        # Converter Row para dict e parsear listas JSON
        data = dict(row)
        data['recomendacoes'] = json.loads(data['recomendacoes'])
        data['alertas'] = json.loads(data['alertas'])
        data['date'] = date.fromisoformat(data['date'])
        data['computed_at'] = datetime.fromisoformat(data['computed_at'])
        
        return PolicyDecision(**data)

    def _compute_target(self, target_date: date) -> dict:
        """Calcula o setpoint ideal baseado no Ikigai e Roadmap."""
        ikigai_data = self.ikigai.compute_score()
        return {
            "qhe_target": 0.8,
            "c_comp_target": 0.9,
            "ikigai_global": ikigai_data.get("global", 0.5)
        }

    def _read_sensor_data(self, target_date: date) -> dict:
        """Lê métricas reais das últimas 24h"""
        cursor = self.db.cursor()
        
        # Estudo
        cursor.execute("""
            SELECT COALESCE(SUM(duration_minutes)/60.0, 0) as study_hours
            FROM study_sessions WHERE date = ?
        """, (target_date.isoformat(),))
        row = cursor.fetchone()
        actual_hours = row["study_hours"] if row else 0.0
        
        # Consistência
        cursor.execute("""
            SELECT AVG(CAST(executed AS INTEGER)) as consistency
            FROM habit_states WHERE date = ?
        """, (target_date.isoformat(),))
        row = cursor.fetchone()
        consistency = row["consistency"] if row and row["consistency"] is not None else 0.0
        
        # Infrações
        cursor.execute("""
            SELECT COUNT(*) as infractions
            FROM habit_states WHERE date = ? AND streak_broken = 1
        """, (target_date.isoformat(),))
        row = cursor.fetchone()
        infractions = row["infractions"] if row else 0
        
        return {
            "actual_hours": actual_hours,
            "consistency": consistency,
            "infractions": infractions,
            "hours_deviation": actual_hours - 2.5 # Simplificado
        }

    def _persist_decision(self, decision: PolicyDecision):
        """Grava decisão no banco de dados."""
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO policy_decisions (
                date, policy, qhe, c_comp, infrações_24h, tipo_dia,
                hardwork_budget_hours, pause_duration_minutes, sleep_target_hours,
                recomendacoes, alertas, days_in_current_policy, policy_prev, computed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.date.isoformat(), decision.policy.value, decision.qhe, decision.c_comp,
            decision.infrações_24h, decision.tipo_dia, decision.hardwork_budget_hours,
            decision.pause_duration_minutes, decision.sleep_target_hours,
            json.dumps(decision.recomendacoes), json.dumps(decision.alertas),
            decision.days_in_current_policy, decision.policy_prev.value if decision.policy_prev else None,
            decision.computed_at.isoformat()
        ))
        self.db.commit()
