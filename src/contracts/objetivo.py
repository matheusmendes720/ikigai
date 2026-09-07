"""Objetivo contract — quarterly/onda-level objective with key results.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""

from pydantic import Field

from src.contracts.base import BasePlanContract


class Objetivo(BasePlanContract):
    """Objective at QUARTERLY or ONDA tier with key results tracking."""

    key_results: list[str] = Field(default_factory=list)
    progress_pct: float = Field(ge=0.0, le=100.0, default=0.0)
