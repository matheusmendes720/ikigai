from pydantic import BaseModel, Field


class SQLIndex(BaseModel):
    index_name: str
    table: str
    columns: list[str]
    query_template: str


class VectorIndex(BaseModel):
    index_name: str
    model: str
    dimension: int
    metadata_fields: list[str]


class GraphIndex(BaseModel):
    index_name: str
    query_template: str


class RAGIndex(BaseModel):
    id: str
    sql_indexes: list[SQLIndex] = Field(default_factory=list)
    vector_indexes: list[VectorIndex] = Field(default_factory=list)
    graph_indexes: list[GraphIndex] = Field(default_factory=list)
