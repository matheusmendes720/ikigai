"""Tarefa contract — task at the leaf of the planning hierarchy.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""

from src.contracts.base import BasePlanContract


class Tarefa(BasePlanContract):
    """Task at the leaf of the planning hierarchy. No extra fields."""
