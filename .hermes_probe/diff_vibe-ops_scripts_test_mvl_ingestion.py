diff --git a/vibe-ops/scripts/test_mvl_ingestion.py b/vibe-ops/scripts/test_mvl_ingestion.py
index 94d67446..78457f9e 100644
--- a/vibe-ops/scripts/test_mvl_ingestion.py
+++ b/vibe-ops/scripts/test_mvl_ingestion.py
@@ -2,3 +1,0 @@ import sys
-import os
-from pathlib import Path
-from datetime import datetime
@@ -5,0 +3 @@ import types
+from pathlib import Path
@@ -8,5 +6,5 @@ import types
-chromadb_mock = types.ModuleType('chromadb')
-chromadb_mock.config = types.ModuleType('chromadb.config')
-chromadb_mock.config.Settings = type('Settings', (), {})
-sys.modules['chromadb'] = chromadb_mock
-sys.modules['chromadb.config'] = chromadb_mock.config
+chromadb_mock = types.ModuleType("chromadb")
+chromadb_mock.config = types.ModuleType("chromadb.config")
+chromadb_mock.config.Settings = type("Settings", (), {})
+sys.modules["chromadb"] = chromadb_mock
+sys.modules["chromadb.config"] = chromadb_mock.config
@@ -19,4 +17 @@ from sqlalchemy.orm import sessionmaker
-from storage.orm import Base, StudyTopicORM
-from storage.metadata_orm import MetadataCatalogORM, StateMachineORM
-from storage.sqlite_adapter import SQLiteAdapter
-from storage.chroma_adapter import ChromaAdapter
+
@@ -23,0 +19,2 @@ from pipeline.ingestion_engine import IngestionEngine
+from storage.metadata_orm import MetadataCatalogORM, StateMachineORM
+from storage.orm import Base
@@ -30,0 +28 @@ session = Session()
+
@@ -34,0 +33 @@ class MockChroma:
+
@@ -36 +35,5 @@ class MockChroma:
-        return {"ids": [["study:topic:tp_python_async"]], "documents": [["Conteúdo de Async Python"]]}
+        return {
+            "ids": [["study:topic:tp_python_async"]],
+            "documents": [["Conteúdo de Async Python"]],
+        }
+
@@ -50 +53 @@ raw_yaml = {
-    "depth_level": 2.5
+    "depth_level": 2.5,
@@ -59 +62 @@ Aprendi sobre await, async def e como evitar bloqueios de IO.
-print(f"📦 Processing file: 2026-07-Study-Async.md")
+print("📦 Processing file: 2026-07-Study-Async.md")
@@ -64 +67,3 @@ print("\n🔍 Inspecting Data Mesh Registry:")
-catalog_entry = session.query(MetadataCatalogORM).filter_by(node_id="study:topic:tp_python_async").first()
+catalog_entry = (
+    session.query(MetadataCatalogORM).filter_by(node_id="study:topic:tp_python_async").first()
+)
@@ -66 +71,3 @@ if catalog_entry:
-    print(f"  [Catalog] Node: {catalog_entry.node_id} | Version: {catalog_entry.contract_version} | Status: OK")
+    print(
+        f"  [Catalog] Node: {catalog_entry.node_id} | Version: {catalog_entry.contract_version} | Status: OK"
+    )
