diff --git a/vibe-ops/tests/test_mvl_orchestrator.py b/vibe-ops/tests/test_mvl_orchestrator.py
index 8e34bd14..d0da3e06 100644
--- a/vibe-ops/tests/test_mvl_orchestrator.py
+++ b/vibe-ops/tests/test_mvl_orchestrator.py
@@ -2,0 +3 @@ from unittest.mock import MagicMock
+
@@ -5,0 +7 @@ sys.modules["chromadb.config"] = MagicMock()
+
@@ -9,6 +11,11 @@ from sqlalchemy.orm import sessionmaker
-from src.storage.metadata_orm import Base as MetadataBase
-from src.storage.orm import Base as DataBase
-from src.storage.chroma_adapter import ChromaAdapter
-from src.pipeline.mvl_orchestrator import MVLOrchestrator
-from src.pipeline.pipeline_state_machine import PipelineState
-import os
+
+from pipeline.mvl_orchestrator import MVLOrchestrator
+from pipeline.pipeline_state_machine import PipelineState, PipelineStateMachine
+from storage.metadata_orm import (
+    Base as MetadataBase,
+    MetadataCatalogORM,
+    StateMachineORM,
+)
+from storage.orm import Base as DataBase
+from storage.ueid import UEID
+
@@ -20,0 +28 @@ class MockChroma:
+
@@ -31,0 +40 @@ def db_session():
+
@@ -36,4 +45,2 @@ def test_mvl_ingestion_flow(db_session):
-    # Define a sample payload for a StudyTopic (we know this exists in models/contracts)
-    # Actually, we need to check registry.yaml to see what's valid.
-    # For now, let's assume we have a valid contract or mock the registry if needed.
-    
+    # Contract-valid study_topic payload (contracts/study_topic_v1.json):
+    # required = entity_type, id, title, parent_study_project, depth_level.
@@ -43,0 +51 @@ def test_mvl_ingestion_flow(db_session):
+        "entity_type": entity_type,
@@ -47 +55 @@ def test_mvl_ingestion_flow(db_session):
-        "status": "active"
+        "depth_level": 1.0,
@@ -51,2 +59,4 @@ def test_mvl_ingestion_flow(db_session):
-    success = orchestrator.ingest(
-        node_id=node_id,
+    success = orchestrator.ingest_markdown(
+        file_path=node_id,
+        raw_yaml=payload,
+        content="Testing MVL Orchestrator",
@@ -54,3 +63,0 @@ def test_mvl_ingestion_flow(db_session):
-        entity_type=entity_type,
-        payload=payload,
-        content="Testing MVL Orchestrator"
@@ -60,7 +66,0 @@ def test_mvl_ingestion_flow(db_session):
-    
-    # Verify state machine
-    trace = orchestrator.state_machine.get_trace(node_id)
-    states = [t.current_state for t in trace]
-    assert PipelineState.RAW in states
-    assert PipelineState.VALIDATED in states
-    assert PipelineState.INDEXED in states
@@ -68,2 +68,12 @@ def test_mvl_ingestion_flow(db_session):
-    # Verify catalog
-    node = orchestrator.catalog.get_node(node_id)
+    # The canonical node identity is the UEID, not the file path.
+    ueid = UEID.create(domain, entity_type, "tp_math_101")
+
+    # Verify state machine (mesh_state_machine rows)
+    states = [
+        row.current_state
+        for row in db_session.query(StateMachineORM).filter_by(node_id=ueid).all()
+    ]
+    assert "INDEXED_AND_READY" in states
+
+    # Verify catalog (mesh_metadata_catalog row)
+    node = db_session.query(MetadataCatalogORM).filter_by(node_id=ueid).first()
@@ -71,0 +82,37 @@ def test_mvl_ingestion_flow(db_session):
+    assert node.source_path == node_id
+
+
+def test_mvl_rejects_contract_violation(db_session):
+    vector_db = MockChroma()
+    orchestrator = MVLOrchestrator(db_session, vector_db)
+
+    # Missing the required "title" field -> contract violation -> fail-fast.
+    success = orchestrator.ingest_markdown(
+        file_path="broken.md",
+        raw_yaml={
+            "entity_type": "study_topic",
+            "id": "tp_broken",
+            "parent_study_project": "sp_math",
+            "depth_level": 1.0,
+        },
+        content="Broken payload",
+        domain="study",
+    )
+
+    assert success is False
+
+    # Fail-fast path logs the violation against the source path.
+    states = [row.current_state for row in db_session.query(StateMachineORM).all()]
+    assert "FAILED_VALIDATION" in states
+
+
+def test_pipeline_state_machine_transitions(db_session):
+    """The generic state machine records transitions against the ORM contract."""
+    sm = PipelineStateMachine(db_session)
+    sm.transition("node_x", PipelineState.RAW, "INGEST_START")
+    sm.transition("node_x", PipelineState.VALIDATED, "VALIDATED")
+
+    trace = sm.get_trace("node_x")
+    states = [row.current_state for row in trace]
+    assert PipelineState.RAW in states
+    assert PipelineState.VALIDATED in states
