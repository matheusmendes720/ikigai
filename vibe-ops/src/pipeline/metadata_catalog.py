from datetime import datetime
from src.storage.metadata_orm import MetadataCatalog as MetadataCatalogModel

class MetadataCatalog:
    def __init__(self, session):
        self.session = session

    def upsert_node(self, node_id: str, domain: str, source_path: str = None, 
                    contract_id: str = None, contract_version: str = None, 
                    physical_table: str = None, vector_collection: str = None):
        node = self.session.query(MetadataCatalogModel).filter_by(node_id=node_id).first()
        if not node:
            node = MetadataCatalogModel(node_id=node_id)
            self.session.add(node)
        
        if domain: node.domain = domain
        if source_path: node.source_path = source_path
        if contract_id: node.contract_id = contract_id
        if contract_version: node.contract_version = contract_version
        if physical_table: node.physical_table = physical_table
        if vector_collection: node.vector_collection = vector_collection
        node.updated_at = datetime.utcnow()
        
        self.session.commit()
        return node

    def get_node(self, node_id: str):
        return self.session.query(MetadataCatalogModel).filter_by(node_id=node_id).first()
