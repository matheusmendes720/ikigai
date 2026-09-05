"""PAE phase transition validator.

Per spec 2026-09-03-sonho-tree-hybrid-design §Decision 8 + Drift Invariant (c).
SONHO phase transitions require actor=user. META/OBJETIVO/PROJETO/ENTREGA/TAREFA
accept any actor.
"""

from __future__ import annotations

from typing import Literal

from src.contracts.base import BasePlanContract
from src.contracts.common import PaeCyclePhase


def validate_phase_transition(
    entity: BasePlanContract,
    old_cycle_phase: PaeCyclePhase | None,
    new_cycle_phase: PaeCyclePhase,
    actor: Literal["user", "agent", "system"],
) -> None:
    """Validate PAE phase transition.

    Args:
        entity: The entity undergoing transition.
        old_cycle_phase: Previous phase (None if creation).
        new_cycle_phase: Target phase.
        actor: Principal performing the transition (user/agent/system).

    Raises:
        PermissionError: If SONHO.cycle_phase change attempted by non-user.
    """
    # Creation or no-op skips check
    if old_cycle_phase is None or old_cycle_phase == new_cycle_phase:
        return

    # Decision #8: SONHO requires user actor
    if entity.tier == "SONHO" and actor != "user":
        raise PermissionError(
            f"SONHO phase transitions require actor=user (got {actor!r}, "
            f"entity={entity.id}, transition={old_cycle_phase}->{new_cycle_phase})"
        )

    # All other tiers (OBJETIVO, META, PROJETO, ENTREGA, TAREFA) accept any actor
