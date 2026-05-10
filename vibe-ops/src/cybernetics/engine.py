import sqlite3
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import date

@dataclass
class KnowledgeNode:
    topic: str
    depth: int
    completion: float  # 0.0 to 1.0
    dependencies: List[str]

class BinaryKnowledgeTree:
    """
    Algoritmo de representação de árvore de conhecimento para busca de gaps.
    Permite visualizar o que falta aprender/executar para atingir um objetivo.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_cognitive_gaps(self) -> List[Dict[str, Any]]:
        """
        Busca tópicos que possuem dependências resolvidas mas baixa completude.
        Utiliza uma lógica de travessia para encontrar a 'fronteira' do conhecimento.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Busca tópicos com progresso abaixo do ideal
        cursor.execute("""
            SELECT topic_id, name, progress_score, dependency_ids
            FROM study_topics
            WHERE progress_score < 0.8
        """)
        
        gaps = []
        rows = cursor.fetchall()
        for row in rows:
            topic_id = row['topic_id']
            name = row['name']
            progress = row['progress_score']
            deps_json = row['dependency_ids']
            
            deps = json.loads(deps_json) if deps_json else []
            
            # Verificar se as dependências (nós pais na árvore) estão concluídas (>90%)
            ready = True
            for dep_id in deps:
                cursor.execute("SELECT progress_score FROM study_topics WHERE topic_id = ?", (dep_id,))
                dep_row = cursor.fetchone()
                if dep_row and dep_row['progress_score'] < 0.9:
                    ready = False
                    break
            
            if ready:
                gaps.append({
                    "id": topic_id,
                    "topic": name,
                    "current_progress": progress,
                    "status": "READY_FOR_PUSH",
                    "reason": "Dependências concluídas. Este é o seu próximo gargalo cognitivo."
                })
        
        conn.close()
        return gaps

class GapSearchEngine:
    """
    Engine para análise de desvios cibernéticos (Execution Gaps).
    Compara o 'Setpoint' da política vs 'Sensor' da realidade.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path

    def analyze_execution_debt(self) -> Dict[str, Any]:
        """
        Calcula o débito de execução baseado na velocidade das últimas 72h.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Pegar a meta da última política
        cursor.execute("SELECT hardwork_budget_hours FROM policy_decisions ORDER BY date DESC LIMIT 1")
        row = cursor.fetchone()
        target_hours = row['hardwork_budget_hours'] if row else 2.5
        
        # 2. Pegar a execução real (média 3 dias)
        cursor.execute("""
            SELECT AVG(duration_minutes) / 60.0 as avg_hours
            FROM study_sessions 
            WHERE date >= date('now', '-3 days')
        """)
        actual_row = cursor.fetchone()
        actual_hours = actual_row['avg_hours'] if actual_row and actual_row['avg_hours'] else 0.0
        
        gap = target_hours - actual_hours
        
        conn.close()
        
        return {
            "target": target_hours,
            "actual_3d_avg": actual_hours,
            "gap_hours": gap,
            "debt_percentage": (gap / target_hours) * 100 if target_hours > 0 else 0
        }

def get_engine(db_path: str):
    return GapSearchEngine(db_path)
