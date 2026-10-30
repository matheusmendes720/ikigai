import sys
from unittest.mock import MagicMock

sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.config"] = MagicMock()


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline.mvl_orchestrator import MVLOrchestrator
from pipeline.pipeline_state_machine import PipelineState, PipelineStateMachine
from storage.metadata_orm import (
    Base as MetadataBase,
    MetadataCatalogORM,
    StateMachineORM,
)
from storage.orm import Base as DataBase
from storage.ueid import UEID


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

    # Contract-valid study_topic payload (contracts/study_topic_v1.json):
    # required = entity_type, id, title, parent_study_project, depth_level.
    node_id = "test_note.md"
    domain = "study"
    entity_type = "study_topic"
    payload = {
        "entity_type": entity_type,
        "id": "tp_math_101",
        "title": "Mathematics 101",
        "parent_study_project": "sp_math",
        "depth_level": 1.0,
    }

    # Execute ingestion
    success = orchestrator.ingest_markdown(
        file_path=node_id,
        raw_yaml=payload,
        content="Testing MVL Orchestrator",
        domain=domain,
    )

    assert success is True

    # The canonical node identity is the UEID, not the file path.
    ueid = UEID.create(domain, entity_type, "tp_math_101")

    # Verify state machine (mesh_state_machine rows)
    states = [
        row.current_state
        for row in db_session.query(StateMachineORM).filter_by(node_id=ueid).all()
    ]
    assert "INDEXED_AND_READY" in states

    # Verify catalog (mesh_metadata_catalog row)
    node = db_session.query(MetadataCatalogORM).filter_by(node_id=ueid).first()
    assert node is not None
    assert node.domain == "study"
    assert node.source_path == node_id


def test_mvl_rejects_contract_violation(db_session):
    vector_db = MockChroma()
    orchestrator = MVLOrchestrator(db_session, vector_db)

    # Missing the required "title" field -> contract violation -> fail-fast.
    success = orchestrator.ingest_markdown(
        file_path="broken.md",
        raw_yaml={
            "entity_type": "study_topic",
            "id": "tp_broken",
            "parent_study_project": "sp_math",
            "depth_level": 1.0,
        },
        content="Broken payload",
        domain="study",
    )

    assert success is False

    # Fail-fast path logs the violation against the source path.
    states = [row.current_state for row in db_session.query(StateMachineORM).all()]
    assert "FAILED_VALIDATION" in states


def test_pipeline_state_machine_transitions(db_session):
    """The generic state machine records transitions against the ORM contract."""
    sm = PipelineStateMachine(db_session)
    sm.transition("node_x", PipelineState.RAW, "INGEST_START")
    sm.transition("node_x", PipelineState.VALIDATED, "VALIDATED")

    trace = sm.get_trace("node_x")
    states = [row.current_state for row in trace]
    assert PipelineState.RAW in states
    assert PipelineState.VALIDATED in states
