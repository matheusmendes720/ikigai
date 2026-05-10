import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from storage.sqlite_vec_integration import SQLiteVecIntegration
from embeddings.provider import EmbeddingProvider, get_provider
from pipeline.frontmatter_parser import FrontmatterParser

logger = logging.getLogger(__name__)

class HybridRAGIndexer:
    """
    Orquestrador para indexação semântica e busca híbrida.
    """
    
    def __init__(self, 
                 db_path: str = "vibe_ops.db", 
                 embedding_config: Optional[Dict[str, Any]] = None):
        self.vec_store = SQLiteVecIntegration(db_path)
        self.embedding_provider = get_provider(embedding_config or {"type": "local"})
        self.parser = FrontmatterParser()

    def index_vault(self, vault_path: str):
        """
        Varre o vault do Obsidian e indexa todos os arquivos Markdown.
        """
        vault_root = Path(vault_path)
        if not vault_root.exists():
            logger.error(f"Vault path não encontrado: {vault_path}")
            return

        logger.info(f"Iniciando indexação do vault: {vault_path}")
        
        indexed_count = 0
        for root, _, files in os.walk(vault_root):
            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    try:
                        self.index_file(file_path)
                        indexed_count += 1
                    except Exception as e:
                        logger.error(f"Erro ao indexar {file_path}: {e}")

        logger.info(f"Indexação concluída. {indexed_count} arquivos processados.")

    def index_file(self, file_path: Path):
        """Indexa um arquivo individual."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extrai frontmatter
        metadata = self.parser.extract_raw(content) or {}
        
        # Remove frontmatter do conteúdo para o embedding (opcional, mas recomendado)
        import re
        clean_content = re.sub(r'^---\s*\n(.*?)\n---\s*\n', '', content, flags=re.DOTALL).strip()
        
        if not clean_content:
            return

        # ID único baseado no path relativo
        rel_path = str(file_path.relative_to(file_path.anchor)).replace("\\", "/")
        entity_id = metadata.get("id", rel_path)
        entity_type = metadata.get("entity_type", "note")

        # Gera embedding
        embedding = self.embedding_provider.get_embedding(clean_content)

        # Adiciona metadados extras
        metadata.update({
            "path": rel_path,
            "filename": file_path.name,
            "char_count": len(clean_content)
        })

        # Upsert no banco
        self.vec_store.upsert_vector(
            entity_id=entity_id,
            entity_type=entity_type,
            content=clean_content[:1000], # Guardamos um snippet ou o conteúdo todo
            embedding=embedding,
            metadata=metadata
        )

    def search(self, query: str, limit: int = 5, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Realiza busca semântica."""
        query_emb = self.embedding_provider.get_embedding(query)
        return self.vec_store.semantic_search(
            query_embedding=query_emb,
            limit=limit,
            filter_type=entity_type
        )

if __name__ == "__main__":
    # Teste rápido se executado diretamente
    logging.basicConfig(level=logging.INFO)
    indexer = HybridRAGIndexer()
    # indexer.index_vault("./vault_test")
    # print(indexer.search("como estudar python?"))
