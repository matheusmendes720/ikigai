from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DocBackend(BaseModel):
    id: str = Field(pattern=r'^doc_cli_[a-z0-9_]+$')
    title: str
    storage_path: str
    related_tasks: List[str] = Field(default_factory=list)

class DocFrontend(BaseModel):
    id: str
    title: str
    tech_stack: List[str] = Field(default_factory=list)
