"""Meta contract — measurable goal with success metrics and review cadence.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""

from pydantic import Field

from src.contracts.base import BasePlanContract


class Meta(BasePlanContract):
    """Measurable goal with success metrics and periodic review cadence."""

    success_metrics: list[str] = []
    review_frequency_days: int = Field(default=7, ge=1)
