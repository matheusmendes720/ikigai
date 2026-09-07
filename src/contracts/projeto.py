"""Projeto contract — project with tech stack and revenue tracking.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""


from pydantic import Field

from src.contracts.base import BasePlanContract


class Projeto(BasePlanContract):
    """Project entity with technology stack and revenue fields."""

    tech_stack: list[str] = Field(default_factory=list)
    repo_url: str | None = None
    target_revenue_brl: float = Field(default=0.0, ge=0.0)
    actual_revenue_brl: float = Field(default=0.0, ge=0.0)
