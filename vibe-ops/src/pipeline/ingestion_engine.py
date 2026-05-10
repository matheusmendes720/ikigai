from __future__ import annotations
import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from pydantic import ValidationError

from models.contracts import StudyNoteContract
from storage.metadata_orm import MetadataCatalogORM, StateMachineORM
from storage.orm import StudyTopicORM
from storage.chroma_adapter import ChromaAdapter
from storage.ueid import UEID
from pipeline.enrichment_engine import EnrichmentEngine
from pipeline.learning_outcome_processor import LearningOutcomeProcessor

class IngestionEngine:
    """
    Atomic Ingestion Engine for the Vibe-Ops Data Mesh.
    Orchestrates validation, registration, and state management for data nodes.
    """

    def __init__(self, db_session: Session, vector_db: ChromaAdapter):
        self.db = db_session
        self.vector_db = vector_db
        self.enricher = EnrichmentEngine()
        self.outcome_processor = LearningOutcomeProcessor(None) # Adapter logic handled elsewhere for now

    def process_obsidian_note(self, file_path: str, raw_yaml: dict, content: str):
        """
        Processes an Obsidian study note through the Minimum Viable Loop (MVL).
        """
        source_path = file_path

        try:
            # 1. Validation
            try:
                contract = StudyNoteContract(**raw_yaml)
            except ValidationError as e:
                self._log_state(
                    node_id=source_path,
                    state="FAILED_VALIDATION",
                    event="VALIDATION_ERROR",
                    payload={"errors": e.errors(), "raw_yaml": raw_yaml}
                )
                return

            # 2. Atomic Orchestration
            try:
                ueid = UEID.create("study", "topic", contract.topic_id)
                
                # LAYER 2: Enrichment & Chunking
                enriched_meta = self.enricher.enrich_study_note(contract, content)
                chunks = self.enricher.chunk_content(content)

                with self.db.begin_nested():
                    # Create/Merge StudyTopicORM
                    topic = self.db.get(StudyTopicORM, contract.topic_id)
                    if topic:
                        topic.depth_level = contract.depth_level
                    else:
                        topic = StudyTopicORM(
                            id=contract.topic_id,
                            title=contract.topic_id.replace("_", " ").title(),
                            parent_study_project=raw_yaml.get("parent_project", "default_study_project"),
                            depth_level=contract.depth_level,
                            status="active"
                        )
                        self.db.add(topic)

                    # Index in vector_db with chunks and enriched metadata
                    for i, chunk in enumerate(chunks):
                        chunk_ueid = f"{ueid}:chunk:{i}"
                        self.vector_db.upsert_content(
                            entity_id=chunk_ueid,
                            content=chunk,
                            metadata={
                                **enriched_meta,
                                "chunk_index": i,
                                "source_path": source_path
                            }
                        )

                    # Upsert entry into MetadataCatalogORM
                    catalog_entry = self.db.get(MetadataCatalogORM, ueid)
                    if catalog_entry:
                        catalog_entry.domain = contract.domain
                        catalog_entry.source_path = source_path
                        catalog_entry.contract_id = contract.schema_id
                        catalog_entry.contract_version = contract.contract_version
                        catalog_entry.updated_at = datetime.datetime.utcnow()
                    else:
                        catalog_entry = MetadataCatalogORM(
                            node_id=ueid,
                            domain=contract.domain,
                            source_path=source_path,
                            contract_id=contract.schema_id,
                            contract_version=contract.contract_version,
                            physical_table="study_topics",
                            vector_collection="vibe_ops_mesh"
                        )
                        self.db.add(catalog_entry)

                    # Log state: INDEXED_AND_READY
                    self._log_state(
                        node_id=ueid,
                        state="INDEXED_AND_READY",
                        event="INGESTION_COMPLETE",
                        payload={"source_path": source_path, "contract_version": contract.contract_version}
                    )

                self.db.commit()

            except Exception as e:
                self.db.rollback()
                raise e

        except Exception as e:
            self._log_state(
                node_id=source_path, # Fallback to file path
                state="ERROR",
                event="UNEXPECTED_FAILURE",
                payload={"error": str(e)}
            )

    def _log_state(self, node_id: str, state: str, event: str, payload: dict):
        """Helper to record state transitions. Ensures MetadataCatalogORM exists."""
        catalog_entry = self.db.get(MetadataCatalogORM, node_id)
        if not catalog_entry:
            catalog_entry = MetadataCatalogORM(
                node_id=node_id,
                domain="unknown",
                source_path=None,
                contract_id="unknown",
                contract_version="unknown",
                physical_table="unknown",
                vector_collection="unknown"
            )
            self.db.add(catalog_entry)
            self.db.flush()

        log_entry = StateMachineORM(
            node_id=node_id,
            current_state=state,
            last_event=event,
            event_payload=payload,
            transitioned_at=datetime.datetime.utcnow()
        )
        self.db.add(log_entry)
        try:
            self.db.flush()
        except Exception:
            self.db.rollback()
