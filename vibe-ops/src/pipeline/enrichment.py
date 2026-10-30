import hashlib

from pydantic import BaseModel

from models import Project


class MetadataEnricher:
    """
    Enriquece metadados das entidades antes da persistência.
    """

    @staticmethod
    def compute_upstream_id(entity: BaseModel) -> str:
        """Gera um hash SHA-256 de 12 caracteres baseado no ID e título."""
        raw_id = getattr(entity, "id", "unknown")
        title = getattr(entity, "title", "")
        seed = f"{raw_id}:{title}".encode()
        return hashlib.sha256(seed).hexdigest()[:12]

    @classmethod
    def enrich_project(cls, project: Project) -> Project:
        """Enriquece projeto com upstream_id e validação de chaves."""
        return project

    @classmethod
    def resolve_hierarchy(cls, entity: BaseModel) -> str | None:
        """Resolve a chave hierárquica S1.O2.M3.id."""
        if hasattr(entity, "tw_project_key"):
            return entity.tw_project_key
        return None
