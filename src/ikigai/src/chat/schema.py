"""Pydantic v2 strict models for chat thread (decision #3)."""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

_UEID_RE = re.compile(r"^[a-z]{2,10}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")
ProposalStatus = Literal["draft", "semi", "ready", "approved", "rejected", "archived"]


class Proposal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    proposal_id: str
    status: ProposalStatus
    operations: list = Field(default_factory=list)
    reasoning: str = ""
    citations: list = Field(default_factory=list)
    horizon: Literal["1d", "5d", "15d", "90d", "180d", "1y"] = "15d"
    parent_proposal_id: str | None = None
    profile_at_creation: str = "ikigai-planner"

    @field_validator("proposal_id")
    @classmethod
    def _validate_ueid(cls, v):
        if not _UEID_RE.match(v):
            raise ValueError(f"proposal_id must match ADR-014 4-part UEID: {v}")
        return v


class ChatThread(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    thread_id: str
    created_at: datetime
    profile_active: str = "ikigai-planner"
    soul_path: str = "src/ikigai/souls/ikigai-planner.md"
    title: str = ""
