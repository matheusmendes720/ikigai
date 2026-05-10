from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SQLIndex(BaseModel):
    index_name: str
    table: str
    columns: List[str]
    query_template: str

class VectorIndex(BaseModel):
    index_name: str
    model: str
    dimension: int
    metadata_fields: List[str]

class GraphIndex(BaseModel):
    index_name: str
    query_template: str

class RAGIndex(BaseModel):
    id: str
    sql_indexes: List[SQLIndex] = Field(default_factory=list)
    vector_indexes: List[VectorIndex] = Field(default_factory=list)
    graph_indexes: List[GraphIndex] = Field(default_factory=list)
