import sys
import os
from pathlib import Path
from datetime import datetime
import types

# Mock chromadb before imports to avoid ModuleNotFoundError
chromadb_mock = types.ModuleType('chromadb')
chromadb_mock.config = types.ModuleType('chromadb.config')
chromadb_mock.config.Settings = type('Settings', (), {})
sys.modules['chromadb'] = chromadb_mock
sys.modules['chromadb.config'] = chromadb_mock.config

# Setup path to find vibe-ops src
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.orm import Base, StudyTopicORM
from storage.metadata_orm import MetadataCatalogORM, StateMachineORM
from storage.sqlite_adapter import SQLiteAdapter
from storage.chroma_adapter import ChromaAdapter
from pipeline.ingestion_engine import IngestionEngine

# 1. Setup Test Environment (In-memory SQLite for demo)
engine = create_engine("sqlite:///vibe_ops_test.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Mock Chroma
class MockChroma:
    def upsert_content(self, entity_id, content, metadata):
        print(f"  [Chroma] Indexing semantic content for {entity_id}...")
    def query_semantic(self, text, n_results=5, where=None):
        return {"ids": [["study:topic:tp_python_async"]], "documents": [["Conteúdo de Async Python"]]}

vector_db = MockChroma()
ingestor = IngestionEngine(session, vector_db)

# 2. Simulate Obsidian Note Ingestion
print("🚀 Starting MVL Ingestion Simulation: 'Async Python' Note")

raw_yaml = {
    "contract_version": "v1.0",
    "domain": "study",
    "schema_id": "study_note",
    "topic_id": "tp_python_async",
    "title": "Programação Assíncrona em Python",
    "depth_level": 2.5
}

content = """
# Async Python
O loop de eventos é o coração do asyncio. 
Aprendi sobre await, async def e como evitar bloqueios de IO.
"""

print(f"📦 Processing file: 2026-07-Study-Async.md")
ingestor.process_obsidian_note("2026-07-Study-Async.md", raw_yaml, content)

# 3. Inspect State Machine and Catalog
print("\n🔍 Inspecting Data Mesh Registry:")
catalog_entry = session.query(MetadataCatalogORM).filter_by(node_id="study:topic:tp_python_async").first()
if catalog_entry:
    print(f"  [Catalog] Node: {catalog_entry.node_id} | Version: {catalog_entry.contract_version} | Status: OK")

state_logs = session.query(StateMachineORM).filter_by(node_id="study:topic:tp_python_async").all()
print("\n🔄 State Machine Trace:")
for log in state_logs:
    print(f"  [{log.transitioned_at}] State: {log.current_state} | Event: {log.last_event}")

session.close()
# os.remove("vibe_ops_test.db")
