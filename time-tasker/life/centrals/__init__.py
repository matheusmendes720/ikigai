"""Centrals: task, finance, knowledge, research. Each aggregates a pillar of the life OS."""

from .base import BaseCentral
from .task import task_central
from .finance import finance_central
from .knowledge import knowledge_central
from .research import research_central

__all__ = [
    "BaseCentral",
    "task_central",
    "finance_central",
    "knowledge_central",
    "research_central",
]
