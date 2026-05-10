from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from .sqlite_adapter import SQLiteAdapter
from .chroma_adapter import ChromaAdapter
from .ueid import UEID

class DataMeshAdapter:
    """
    Orquestrador central do Data Mesh.
    """

    def __init__(self, db_path: str = "vibe_ops.db", chroma_path: str = "./chroma_db"):
        self.sqlite = SQLiteAdapter(db_path)
        self.chroma = ChromaAdapter(chroma_path)

    def sync_entity(self, entity: BaseModel, cluster: str, content: Optional[str] = None):
        entity_id = getattr(entity, "id", "unknown")
        entity_type = getattr(entity, "entity_type", entity.__class__.__name__.lower())
        
        self.sqlite.save_entity(entity)
        
        if content:
            ueid = UEID.create(cluster, entity_type, entity_id)
            metadata = entity.model_dump()
            metadata["ueid"] = ueid
            metadata["cluster"] = cluster
            
            clean_metadata = {
                k: v for k, v in metadata.items() 
                if isinstance(v, (str, int, float, bool))
            }
            
            self.chroma.upsert_content(ueid, content, clean_metadata)

    def search(self, query: str) -> Dict[str, Any]:
        return self.chroma.query_semantic(query)
