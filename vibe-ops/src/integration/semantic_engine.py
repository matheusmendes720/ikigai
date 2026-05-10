import sqlite_vec
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict
import json

class SemanticEngine:
    def __init__(self, db_path: str, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.db_path = db_path
        self.model = SentenceTransformer(model_name)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vibe_vectors (
                id INTEGER PRIMARY KEY,
                content_hash TEXT UNIQUE,
                metadata TEXT,
                embedding FLOAT[384]
            )
        """)
        conn.commit()
        conn.close()

    def upsert_content(self, content: str, metadata: Dict):
        embedding = self.model.encode(content)
        content_hash = metadata.get("hash") or str(hash(content))
        
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        
        # Inserção usando a sintaxe nativa do sqlite-vec
        conn.execute("""
            INSERT INTO vibe_vectors (content_hash, metadata, embedding)
            VALUES (?, ?, ?)
            ON CONFLICT(content_hash) DO UPDATE SET
                metadata = excluded.metadata,
                embedding = excluded.embedding
        """, (content_hash, json.dumps(metadata), embedding.tobytes()))
        
        conn.commit()
        conn.close()

    def query(self, text: str, limit: int = 5) -> List[Tuple[Dict, float]]:
        query_embedding = self.model.encode(text)
        
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        
        rows = conn.execute("""
            SELECT 
                metadata,
                vec_distance_L2(embedding, ?) as distance
            FROM vibe_vectors
            ORDER BY distance ASC
            LIMIT ?
        """, (query_embedding.tobytes(), limit)).fetchall()
        
        conn.close()
        return [(json.loads(r[0]), r[1]) for r in rows]
