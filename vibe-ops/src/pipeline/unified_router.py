from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from storage.metadata_orm import MetadataCatalogORM, StateMachineORM
from storage.sqlite_adapter import SQLiteAdapter
from storage.chroma_adapter import ChromaAdapter

class UnifiedQueryRouter:
    """
    Roteador de Query Unificada do Data Mesh (Layer 3).
    Realiza o 'Deep Join' entre dados semânticos (Chroma) e relacionais (SQLite).
    """

    def __init__(self, db_session: Session, vector_db: ChromaAdapter):
        self.db = db_session
        self.vector_db = vector_db

    def query_mesh(self, domain: str, semantic_query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Executa uma busca híbrida com Deep Join:
        1. Filtra nós validados no estado 'INDEXED_AND_READY'.
        2. Busca semântica no ChromaDB.
        3. Realiza JOIN dinâmico com a tabela física no SQLite para enriquecimento total.
        """
        ready_nodes = self.db.query(MetadataCatalogORM.node_id)\
            .join(StateMachineORM, MetadataCatalogORM.node_id == StateMachineORM.node_id)\
            .filter(MetadataCatalogORM.domain == domain)\
            .filter(StateMachineORM.current_state == "INDEXED_AND_READY")\
            .distinct().all()
        
        valid_ids = [n[0] for n in ready_nodes]
        if not valid_ids:
            return []

        # 2. Busca Semântica
        vector_results = self.vector_db.query_semantic(
            query_text=semantic_query,
            n_results=n_results
        )

        # 3. Deep Join: Enriquecimento Relacional Total
        enriched_results = []
        for i, full_ueid in enumerate(vector_results.get('ids', [[]])[0]):
            # Extrair o ID base do UEID do chunk (ex: study:topic:tp_async:chunk:0 -> study:topic:tp_async)
            base_ueid = ":".join(full_ueid.split(":")[:3])
            
            node_metadata = self.db.query(MetadataCatalogORM).filter_by(node_id=base_ueid).first()
            if not node_metadata:
                continue

            # Recuperar o objeto completo da tabela física
            structured_data = self._fetch_structured_data(
                node_metadata.physical_table, 
                base_ueid.split(":")[-1]
            )
            
            result_item = {
                "ueid": base_ueid,
                "chunk_ueid": full_ueid,
                "document": vector_results.get('documents', [[]])[0][i],
                "metadata": vector_results.get('metadatas', [[]])[0][i],
                "structured": structured_data,
                "catalog": {
                    "contract": f"{node_metadata.contract_id} v{node_metadata.contract_version}",
                    "source": node_metadata.source_path
                }
            }
            enriched_results.append(result_item)

        return enriched_results

    def _fetch_structured_data(self, table_name: str, entity_id: str) -> Dict[str, Any]:
        """Realiza uma query dinâmica na tabela física para obter o registro completo."""
        query = text(f"SELECT * FROM {table_name} WHERE id = :id")
        result = self.db.execute(query, {"id": entity_id}).fetchone()
        if result:
            return dict(result._mapping)
        return {}

    def get_node_lineage(self, node_id: str) -> Dict[str, Any]:
        catalog = self.db.query(MetadataCatalogORM).filter_by(node_id=node_id).first()
        history = self.db.query(StateMachineORM).filter_by(node_id=node_id).order_by(StateMachineORM.transitioned_at).all()
        return {"catalog": catalog, "state_history": history}
