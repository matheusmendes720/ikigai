from pydantic import BaseModel, Field
from typing import Literal

class DataContract(BaseModel):
    contract_version: str = Field(pattern=r'^v\d+\.\d+$')
    domain: Literal["study", "development", "planning"]
    schema_id: str

class StudyNoteContract(BaseModel):
    contract_version: str = Field(pattern=r'^v\d+\.\d+$')
    domain: Literal["study"] = "study"
    schema_id: Literal["study_note"] = "study_note"
    topic_id: str
    depth_level: float = Field(ge=0.0, le=5.0)
