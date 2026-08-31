"""CyberneticDailyLoop — DB I/O helpers preserved; execute_daily_cycle archived per attribution §3.

Per attribution §3, the orchestrator layer (vibe-ops/cybernetics) must NOT
execute algo math (policy evaluation, vector scoring). The full Target →
Sensor → Adjuster → Persist → Sync → Index pipeline that was previously
/// in ``execute_daily_cycle`` raises NotImplementedError; callers should
/// invoke the canonical algorithm modules directly.

The class structure, DB connection, and DB-only helpers
(``_get_previous_decision``, ``_read_sensor_data``, ``_persist_decision``)
remain available for callers that want to keep the wiring alive without
the algo composition.
"""
from datetime import date, datetime
from typing import Optional
from schemas.pydantic_v2 import PolicyDecision
from pipeline.rag_indexer import HybridRAGIndexer
from middleware.sync_engine import SyncEngine
# Per attribution §3, PolicyEngine + IkigaiScorer imports are removed; class
# attributes (loop.ikigai / loop.policy_engine) are kept as None placeholders
# for any callers that still reference them. Archived entry points raise.
import sqlite3
import json

class CyberneticDailyLoop:
    def __init__(self, db_path, tw_path, vault_path, tw_client=None):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.vault_path = vault_path
        self.sync = SyncEngine(vault_path, db_path, tw_path, tw_client=tw_client)
        self.indexer = HybridRAGIndexer(db_path=db_path)
        # Lazy attributes (set on first access to archived entry points) —
        # keeps importable surface stable while preventing accidental
        # algo execution at construction time.
        self.policy_engine = None  # type: ignore[assignment]
        self.ikigai = None  # type: ignore[assignment]

    def execute_daily_cycle(self, target_date: date) -> PolicyDecision:
        """Executa o ciclo completo Target-Sensor-Adjuster — ARCHIVED per attribution §3.

        Per attribution §3, the policy/IKigai composition path
        (Target → Adjuster using PolicyEngine.evaluate) is the algorithm
        layer's responsibility, not the orchestrator layer's. Callers
        should invoke the canonical modules directly:

            from operational.core.policy_engine import PolicyEngine
            policy_engine.evaluate(metrics, prev_decision, target_date)
        """
        raise NotImplementedError(
            "CyberneticDailyLoop.execute_daily_cycle archived per attribution §3 — "
            "the Target-Sensor-Adjuster orchestration (PolicyEngine.evaluate) "
            "is algo math, not orchestrator wiring. See "
            "operational.core.policy_engine for the canonical implementation."
        )

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
