"""Entrega contract — deliverable with artifact tracking.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""
from typing import Optional

from pydantic import Field

from src.contracts.base import BasePlanContract


class Entrega(BasePlanContract):
    """Deliverable with artifact path and publication visibility."""

    artifact_path: Optional[str] = None
    artifact_type: str = Field(default="document", min_length=1)
    is_public: bool = False
