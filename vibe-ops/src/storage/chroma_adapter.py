import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import Any, Dict, List, Optional

class ChromaAdapter:
    """
    Adaptador ChromaDB para o Vector Layer do Hybrid RAG.
    """

    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="vibe_ops_mesh")

    def upsert_content(self, entity_id: str, content: str, metadata: Dict[str, Any]):
        """Insere ou atualiza conteúdo vetorial com metadados."""
        self.collection.upsert(
            ids=[entity_id],
            documents=[content],
            metadatas=[metadata]
        )

    def query_semantic(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """Realiza busca semântica no Data Mesh."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

    def delete_entity(self, entity_id: str):
        self.collection.delete(ids=[entity_id])
