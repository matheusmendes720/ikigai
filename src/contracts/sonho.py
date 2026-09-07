"""Sonho contract — root of planning hierarchy.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""

from pydantic import Field

from src.contracts.base import BasePlanContract


class Sonho(BasePlanContract):
    """Top-level dream entity. tier must be SONHO; parent_ueid is None."""

    motivation: str
    success_metric: str
    core_values: list[str] = Field(default_factory=list)
