"""
mvl_orchestrator.py — High-Performance Master Orchestrator
Coordinates the Cybernetic Epistemic Mesh: Ingestion -> Validation -> Enrichment -> Persistence.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from pipeline.schema_registry import SchemaRegistry
from pipeline.enrichment_engine import EnrichmentEngine
from storage.metadata_orm import MetadataCatalogORM, StateMachineORM
from storage.ueid import UEID
from storage.chroma_adapter import ChromaAdapter
from storage.orm import StudyTopicORM, RoadmapItemORM

logger = logging.getLogger(__name__)

class MVLOrchestrator:
    """
    Orquestrador mestre do Data Mesh.
    Gerencia o ciclo de vida completo de uma entidade de dado.
    """

    def __init__(
        self,
        db_session: Session,
        vector_db: ChromaAdapter,
        registry: Optional[SchemaRegistry] = None
    ):
        self.db = db_session
        self.vector_db = vector_db
        self.registry = registry or SchemaRegistry()
        self.enricher = EnrichmentEngine()

    def ingest_markdown(
        self, 
        file_path: str, 
        raw_yaml: Dict[str, Any], 
        content: str,
        domain: str = "study",
        version: str = "1.0.0"
    ) -> bool:
        """
        Ingere uma nota do Obsidian seguindo o fluxo de Contratos e Máquina de Estados.
        """
        entity_type = raw_yaml.get("entity_type")
        source_path = file_path

        # 1. Gatekeeper: Validação de Contrato (Fail-Fast)
        result = self.registry.validate_against_contract(
            domain=domain,
            entity_type=entity_type,
            payload=raw_yaml,
            version=version
        )

        if not result.valid:
            self._log_state(source_path, "FAILED_VALIDATION", "CONTRACT_VIOLATION", {"errors": result.errors})
            logger.error(f"[MVL] Validation failed for {source_path}: {result.errors}")
            return False

        entity = result.entity
        ueid = UEID.create(domain, entity_type, entity.id)

        try:
            # 2. Enriquecimento & Chunking (Layer 2)
            enriched_meta = self.enricher.enrich(entity_type, entity)
            if entity_type == "study_topic":
                enriched_meta = self.enricher.enrich_study_note(entity, content)
            
            chunks = self.enricher.chunk_content(content)

            # 3. Persistência Atômica
            with self.db.begin_nested():
                # A. Salva Domínio (SQLite)
                self._persist_domain_entity(entity_type, entity)

                # B. Indexação Vetorial (Chroma)
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{ueid}:chunk:{i}"
                    self.vector_db.upsert_content(
                        entity_id=chunk_id,
                        content=chunk,
                        metadata={**enriched_meta, "chunk_index": i, "source_path": source_path}
                    )

                # C. Registro no Catálogo
                catalog_entry = MetadataCatalogORM(
                    node_id=ueid,
                    domain=domain,
                    source_path=source_path,
                    contract_id=result.contract_id,
                    contract_version=version,
                    physical_table=f"{entity_type}s",
                    vector_collection="vibe_ops_mesh"
                )
                self.db.merge(catalog_entry)

                # D. Transição de Estado
                self._log_state(ueid, "INDEXED_AND_READY", "INGESTION_COMPLETE", enriched_meta)

            self.db.commit()
            logger.info(f"[MVL] Successfully ingested {ueid}")
            return True

        except Exception as e:
            self.db.rollback()
            self._log_state(ueid or source_path, "ERROR", "INGESTION_FAILED", {"error": str(e)})
            logger.error(f"[MVL] Critical error during ingestion of {source_path}: {e}")
            return False

    def _persist_domain_entity(self, entity_type: str, entity: Any):
        """Mapeia Pydantic para ORM e persiste."""
        if entity_type == "study_topic":
            orm_obj = StudyTopicORM(
                id=entity.id,
                title=entity.title,
                parent_study_project=entity.parent_study_project,
                depth_level=entity.depth_level,
                status="active"
            )
            self.db.merge(orm_obj)
        elif entity_type == "roadmap_item":
            orm_obj = RoadmapItemORM(
                id=entity.id,
                title=entity.title,
                goal_id=entity.goal_id,
                storypoints=getattr(entity, 'storypoints', 1),
                status=entity.status
            )
            self.db.merge(orm_obj)

    def _log_state(self, node_id: str, state: str, event: str, payload: dict):
        # Garante entrada no catálogo para o FK
        # (Lógica simplificada para o rastro)
        import datetime
        log = StateMachineORM(
            node_id=node_id,
            current_state=state,
            last_event=event,
            event_payload=payload,
            transitioned_at=datetime.datetime.utcnow()
        )
        self.db.add(log)
        self.db.flush()
