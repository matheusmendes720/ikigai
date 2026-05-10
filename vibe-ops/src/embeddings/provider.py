from abc import ABC, abstractmethod
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class EmbeddingProvider(ABC):
    """Interface para provedores de embeddings."""
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Gera embedding para um texto único."""
        pass

    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings para uma lista de textos."""
        pass

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Provedor usando a API da OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            logger.error("Pacote 'openai' não encontrado. Instale com 'pip install openai'.")
            raise

    def get_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(input=[text], model=self.model)
        return response.data[0].embedding

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]

class LocalEmbeddingProvider(EmbeddingProvider):
    """Provedor local usando sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            logger.warning("Pacote 'sentence-transformers' não encontrado. Usando Mock.")
            self.model = None

    def get_embedding(self, text: str) -> List[float]:
        if self.model:
            return self.model.encode(text).tolist()
        # Mock de 384 dimensões (tamanho do MiniLM)
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        mock = [(b / 255.0) for b in h]
        return (mock * 12)[:384]

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.model:
            return self.model.encode(texts).tolist()
        return [self.get_embedding(t) for t in texts]

def get_provider(config: dict) -> EmbeddingProvider:
    """Factory para instanciar o provedor baseado na configuração."""
    provider_type = config.get("type", "local")
    if provider_type == "openai":
        return OpenAIEmbeddingProvider(
            api_key=config.get("api_key"),
            model=config.get("model", "text-embedding-3-small")
        )
    return LocalEmbeddingProvider(model_name=config.get("model", "all-MiniLM-L6-v2"))
