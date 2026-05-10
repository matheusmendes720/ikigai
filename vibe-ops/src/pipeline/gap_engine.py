from typing import List, Dict, Any
from .knowledge_tree import BinaryKnowledgeTree
from storage.data_mesh_adapter import DataMeshAdapter

class GapSearchEngine:
    """
    Engine para detecção de lacunas de execução e conhecimento.
    Analisa a diferença entre o Roadmap (alvo) e o Aprendizado Real (sensor).
    """
    def __init__(self, adapter: DataMeshAdapter):
        self.adapter = adapter
        self.tree = BinaryKnowledgeTree(adapter)

    def analyze_gaps(self, domain: str = "study") -> Dict[str, Any]:
        # 1. Lacunas Cognitivas
        tree_data = self.tree.build_tree(domain)
        cog_gaps = [
            {"cause": node["title"], "isolation_degree": node["isolation_degree"]}
            for node in tree_data["gaps"]
        ]

        # 2. Dívida de Execução (SQL Join)
        # Cruza RoadmapItems pendentes com o orçamento de tempo (mock por enquanto)
        query = "SELECT COUNT(*) as count FROM roadmap_items WHERE status = 'pending'"
        pending_count = self.adapter.query_sql(query)[0]["count"]
        
        # Simulação de cálculo de dívida (Hardwork Budget)
        hours_per_task = 4.0
        weekly_budget = 20.0 # Horas disponíveis por semana
        debt_hours = pending_count * hours_per_task
        
        return {
            "cognitive_gaps": cog_gaps,
            "execution_debt": {
                "hours_debt": debt_hours,
                "weekly_capacity": weekly_budget,
                "days_to_clear": (debt_hours / (weekly_budget/7)) if weekly_budget > 0 else 999
            }
        }
