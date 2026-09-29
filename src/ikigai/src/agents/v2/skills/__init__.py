"""v2 skills package.

Each skill is a module that exposes:
  - SKILL_NAME: str (e.g. "taskdog-triage")
  - run_skill(*args, **kwargs) -> Proposal

Skills emit Proposals; never execute directly.
"""
from __future__ import annotations

from typing import Any

from agents.v2.proposals import Proposal

# Import skills so SKILL_NAME is discoverable
from agents.v2.skills import taskdog_triage  # noqa: F401
from agents.v2.skills import vault_intent_extract  # noqa: F401
from agents.v2.skills import ikigai_daily  # noqa: F401
from agents.v2.skills import ikigai_weekly  # noqa: F401
from agents.v2.skills import ikigai_monthly  # noqa: F401
from agents.v2.skills import ikigai_quarterly  # noqa: F401


SKILL_REGISTRY: dict[str, Any] = {
    taskdog_triage.SKILL_NAME: taskdog_triage,
    vault_intent_extract.SKILL_NAME: vault_intent_extract,
    ikigai_daily.SKILL_NAME: ikigai_daily,
    ikigai_weekly.SKILL_NAME: ikigai_weekly,
    ikigai_monthly.SKILL_NAME: ikigai_monthly,
    ikigai_quarterly.SKILL_NAME: ikigai_quarterly,
}


def list_skills() -> list[str]:
    """Return the names of all registered skills."""
    return sorted(SKILL_REGISTRY.keys())


def get_skill(name: str) -> Any:
    """Look up a skill by name. Raises KeyError if not found."""
    return SKILL_REGISTRY[name]
