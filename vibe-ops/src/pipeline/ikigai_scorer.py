import sqlite3
from typing import Dict, Any

class IkigaiScorer:
    """
    Calcula o Ikigai Vector (Estudo, Trabalho, Saúde, Vontade).
    Fornece o alinhamento de longo prazo.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def compute_score(self) -> Dict[str, float]:
        """
        Calcula o score multidimensional.
        Retorna: {study, dev, health, alignment, global}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Study Momentum (Completions in last 7 days)
            cursor.execute("SELECT COUNT(*) FROM study_progress WHERE date >= date('now', '-7 days')")
            study_count = cursor.fetchone()[0]
            study_score = min(study_count / 14, 1.0) # Target: 2 study events per day

            # 2. Dev Velocity (Commits/Tasks in last 7 days)
            # Placeholder: no development_progress table yet, using generic metric
            dev_score = 0.5 

            # 3. Health Consistency (QHE Average)
            cursor.execute("SELECT AVG(qhe) FROM metrics WHERE date >= date('now', '-7 days')")
            qhe_avg = cursor.fetchone()[0] or 0.0
            health_score = qhe_avg

            # 4. Global Alignment
            global_score = (study_score * 0.4) + (dev_score * 0.4) + (health_score * 0.2)

            return {
                "study": round(study_score, 2),
                "dev": round(dev_score, 2),
                "health": round(health_score, 2),
                "global": round(global_score, 2)
            }
        finally:
            conn.close()
