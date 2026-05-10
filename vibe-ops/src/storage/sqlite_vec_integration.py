from __future__ import annotations
import sqlite3
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

class SQLiteVecIntegration:
    """
    Integração de busca semântica (vetorial) no SQLite.
    
    Se a extensão 'sqlite-vec' estiver disponível no sistema, ela será usada.
    Caso contrário, implementa uma busca vetorial via Python + NumPy como fallback
    para garantir que a funcionalidade de 'Semantic Search' do Vibe-Ops funcione 
    em qualquer ambiente.
    """

    def __init__(self, db_path: str = "vibe_ops.db"):
        self.db_path = db_path
        self._has_native_vec = False
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        # Tenta carregar a extensão se existir em caminhos comuns (opcional)
        # Por enquanto, focamos na detecção de funções nativas
        try:
            res = conn.execute("SELECT name FROM pragma_function_list WHERE name = 'vec_version'").fetchone()
            if res:
                self._has_native_vec = True
        except Exception:
            pass
        return conn

    def _init_db(self):
        """Inicializa as tabelas necessárias para o índice semântico."""
        with self._get_connection() as conn:
            if self._has_native_vec:
                # Se tiver a extensão nativa, poderíamos usar tabelas virtuais vec0
                # Mas para manter compatibilidade total, usamos a estrutura comum
                # e apenas otimizamos as queries se possível.
                pass
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_index (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    content TEXT,
                    embedding BLOB,
                    metadata TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def upsert_vector(self, 
                      entity_id: str, 
                      entity_type: str, 
                      content: str, 
                      embedding: List[float], 
                      metadata: Optional[Dict[str, Any]] = None):
        """Insere ou atualiza um vetor no índice."""
        emb_array = np.array(embedding, dtype=np.float32)
        emb_blob = emb_array.tobytes()
        
        meta_json = json.dumps(metadata or {})
        
        sql = """
            INSERT OR REPLACE INTO semantic_index (id, entity_type, content, embedding, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        with self._get_connection() as conn:
            conn.execute(sql, (entity_id, entity_type, content, emb_blob, meta_json))
            conn.commit()

    def semantic_search(self, 
                        query_embedding: List[float], 
                        limit: int = 5, 
                        min_similarity: float = 0.0,
                        filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Realiza a busca semântica por similaridade de cosseno.
        """
        query_vec = np.array(query_embedding, dtype=np.float32)
        norm_query = np.linalg.norm(query_vec)
        
        if norm_query == 0:
            return []

        results = []
        sql = "SELECT id, entity_type, content, embedding, metadata FROM semantic_index"
        params = []
        
        if filter_type:
            sql += " WHERE entity_type = ?"
            params.append(filter_type)

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            for row in cursor:
                eid, etype, content, emb_blob, meta_raw = row
                
                # Converte BLOB de volta para array numpy
                vec = np.frombuffer(emb_blob, dtype=np.float32)
                norm_vec = np.linalg.norm(vec)
                
                if norm_vec == 0:
                    continue
                    
                # Similaridade de Cosseno: (A . B) / (||A|| * ||B||)
                similarity = np.dot(query_vec, vec) / (norm_query * norm_vec)
                
                if similarity >= min_similarity:
                    results.append({
                        "id": eid,
                        "entity_type": etype,
                        "content": content,
                        "similarity": round(float(similarity), 4),
                        "metadata": json.loads(meta_raw)
                    })

        # Ordena por similaridade (maior primeiro)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def delete_vector(self, entity_id: str):
        """Remove um item do índice."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM semantic_index WHERE id = ?", (entity_id,))
            conn.commit()
