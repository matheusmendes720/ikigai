from .frontmatter_parser import FrontmatterParser
from .enrichment import MetadataEnricher
from .router import DataRouter
from .harness_metrics import MetricsHarness
from storage.data_mesh_adapter import DataMeshAdapter

class SyncOrchestrator:
    """
    Orquestrador central de sincronização e processamento do Data Mesh.
    """
    
    def __init__(self, db_path: str = "vibe_ops.db"):
        self.adapter = DataMeshAdapter(db_path)
    
    def process_markdown_file(self, file_path: str):
        """Pipeline completo para um único arquivo Markdown."""
        entity = FrontmatterParser.parse_file(file_path)
        if not entity:
            return
            
        cluster = "general" 
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.adapter.sync_entity(entity, cluster, content)
        
        if entity.entity_type == "changelog_entry":
            metrics = MetricsHarness.extract_test_metrics(entity)
