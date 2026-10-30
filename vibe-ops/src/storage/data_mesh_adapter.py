from typing import Any

from pydantic import BaseModel

from .chroma_adapter import ChromaAdapter
from .sqlite_adapter import SQLiteAdapter
from .ueid import UEID


class DataMeshAdapter:
    """
    Orquestrador central do Data Mesh.
    """

    def __init__(self, db_path: str = "vibe_ops.db", chroma_path: str = "./chroma_db"):
        self.sqlite = SQLiteAdapter(db_path)
        self.chroma = ChromaAdapter(chroma_path)

    def sync_entity(self, entity: BaseModel, cluster: str, content: str | None = None):
        entity_id = getattr(entity, "id", "unknown")
        entity_type = getattr(entity, "entity_type", entity.__class__.__name__.lower())

        self.sqlite.save_entity(entity)

        if content:
            ueid = UEID.create(cluster, entity_type, entity_id)
            metadata = entity.model_dump()
            metadata["ueid"] = ueid
            metadata["cluster"] = cluster

            clean_metadata = {
                k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))
            }

            self.chroma.upsert_content(ueid, content, clean_metadata)

    def search(self, query: str) -> dict[str, Any]:
        return self.chroma.query_semantic(query)

    def query_sql(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Executa uma query SQL no SQLite e devolve as linhas como dicionários."""
        with self.sqlite._get_connection() as conn:
            conn.row_factory = lambda cursor, row: {
                col[0]: row[i] for i, col in enumerate(cursor.description or [])
            }
            return conn.execute(sql, params).fetchall()
