import numpy as np
from typing import List, Dict, Any
from storage.data_mesh_adapter import DataMeshAdapter

class BinaryKnowledgeTree:
    """
    Representação em árvore dos clusters de conhecimento.
    Usada para detectar 'isolated leaves' (lacunas de conexão).
    """
    def __init__(self, adapter: DataMeshAdapter):
        self.adapter = adapter

    def build_tree(self, domain: str = "study") -> Dict[str, Any]:
        # Busca tópicos via SQL
        query = "SELECT id, title, parent_study_project FROM study_topics"
        topics = self.adapter.query_sql(query)
        
        # Simula detecção de isolamento via similaridade semântica
        # Se um tópico não tem links de saída e similaridade baixa com outros, é uma lacuna.
        isolated_nodes = []
        for topic in topics:
            # Busca vizinhos semânticos no Chroma
            neighbors = self.adapter.chroma.query_collection(
                query_texts=[topic["title"]],
                n_results=5
            )
            
            # Se a distância média for muito alta (> 1.5), o tópico está 'perdido'
            if neighbors["distances"] and np.mean(neighbors["distances"][0]) > 1.5:
                isolated_nodes.append({
                    "id": topic["id"],
                    "title": topic["title"],
                    "isolation_degree": np.mean(neighbors["distances"][0])
                })
        
        return {"nodes": topics, "gaps": isolated_nodes}
