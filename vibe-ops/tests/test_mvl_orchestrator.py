import sys
from unittest.mock import MagicMock
sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.config"] = MagicMock()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage.metadata_orm import Base as MetadataBase
from src.storage.orm import Base as DataBase
from src.storage.chroma_adapter import ChromaAdapter
from src.pipeline.mvl_orchestrator import MVLOrchestrator
from src.pipeline.pipeline_state_machine import PipelineState
import os

# Mocking ChromaAdapter for testing
class MockChroma:
    def upsert_content(self, entity_id, content, metadata):
        pass

@pytest.fixture
def db_session():
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    MetadataBase.metadata.create_all(engine)
    DataBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_mvl_ingestion_flow(db_session):
    vector_db = MockChroma()
    orchestrator = MVLOrchestrator(db_session, vector_db)

    # Define a sample payload for a StudyTopic (we know this exists in models/contracts)
    # Actually, we need to check registry.yaml to see what's valid.
    # For now, let's assume we have a valid contract or mock the registry if needed.
    
    node_id = "test_note.md"
    domain = "study"
    entity_type = "study_topic"
    payload = {
        "id": "tp_math_101",
        "title": "Mathematics 101",
        "parent_study_project": "sp_math",
        "status": "active"
    }

    # Execute ingestion
    success = orchestrator.ingest(
        node_id=node_id,
        domain=domain,
        entity_type=entity_type,
        payload=payload,
        content="Testing MVL Orchestrator"
    )

    assert success is True
    
    # Verify state machine
    trace = orchestrator.state_machine.get_trace(node_id)
    states = [t.current_state for t in trace]
    assert PipelineState.RAW in states
    assert PipelineState.VALIDATED in states
    assert PipelineState.INDEXED in states

    # Verify catalog
    node = orchestrator.catalog.get_node(node_id)
    assert node is not None
    assert node.domain == "study"
