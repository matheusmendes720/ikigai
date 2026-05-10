from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
import hashlib, json

class SyncMappingRule(BaseModel):
    source_system: Literal["obsidian", "taskwarrior", "sqlite"]
    target_table: str
    fk_strategy: str  # "single_project_key" | "full_tree_resolution"
    idempotency_key: str = "upstream_id"
    conflict_resolution: Literal["source_wins", "target_wins", "manual_triage"] = "source_wins"

class SyncContractV1(BaseModel):
    version: str = "1.0.0"
    mapping_rules: list[SyncMappingRule] = Field(default_factory=lambda: [
        SyncMappingRule(
            source_system="obsidian",
            target_table="planning_entities",
            fk_strategy="full_tree_resolution",
            conflict_resolution="source_wins"
        ),
        SyncMappingRule(
            source_system="taskwarrior",
            target_table="roadmap_sync",
            fk_strategy="single_project_key",
            conflict_resolution="target_wins"  # TW é SoT para status/execução
        ),
        SyncMappingRule(
            source_system="sqlite",
            target_table="analytics_snapshots",
            fk_strategy="enrichment_only",
            conflict_resolution="manual_triage"
        )
    ])

    @field_validator("mapping_rules")
    @classmethod
    def validate_idempotency_chain(cls, v):
        for rule in v:
            if rule.idempotency_key != "upstream_id":
                raise ValueError("Todos os contratos devem usar upstream_id (SHA-256 truncated) para idempotência")
        return v
