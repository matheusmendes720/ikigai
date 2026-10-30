from pydantic import BaseModel, Field


class DocBackend(BaseModel):
    id: str = Field(pattern=r"^doc_cli_[a-z0-9_]+$")
    title: str
    storage_path: str
    related_tasks: list[str] = Field(default_factory=list)


class DocFrontend(BaseModel):
    id: str
    title: str
    tech_stack: list[str] = Field(default_factory=list)
