"""Tests for transition_validator (Plan A Task 7).

Per spec 2026-09-03-sonho-tree-hybrid-design §Decision 8 + Drift Invariant (c).
SONHO phase transitions require actor=user. OBJETIVO/META/PROJETO/ENTREGA/TAREFA
accept any actor.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.contracts.sonho import Sonho  # noqa: I001 — `src.` prefix is the canonical repo-root import path
from src.contracts.objetivo import Objetivo
from src.contracts.meta import Meta
from sys_ikigai.security.transition_validator import validate_phase_transition


# Valid 4-part UEIDs (UEID regex enforces ^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$)
_SONHO_UEID = "sn:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef"
_OBJETIVO_UEID = "ob:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef"
_META_UEID = "me:test:abc12345-1234-5678-9abc-def012345678:0123456789abcdef"

_CREATED_AT = datetime.fromisoformat("2026-09-03T00:00:00+00:00")


def _make_sonho() -> Sonho:
    return Sonho(
        id=_SONHO_UEID,
        title="T",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=_CREATED_AT,
        motivation="m",
        success_metric="s",
    )


def _make_objetivo() -> Objetivo:
    return Objetivo(
        id=_OBJETIVO_UEID,
        title="T",
        tier="QUARTERLY",
        parent_ueid=_SONHO_UEID,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=_CREATED_AT,
    )


def _make_meta() -> Meta:
    return Meta(
        id=_META_UEID,
        title="T",
        tier="ONDA",
        parent_ueid=_OBJETIVO_UEID,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="ONDA",
        created_at=_CREATED_AT,
    )


def test_sonho_transition_with_user_actor_allowed():
    s = _make_sonho()
    # No exception
    validate_phase_transition(
        s, old_cycle_phase="plan", new_cycle_phase="evaluate", actor="user"
    )


def test_sonho_transition_with_agent_actor_rejected():
    s = _make_sonho()
    with pytest.raises(
        PermissionError, match="SONHO phase transitions require actor=user"
    ):
        validate_phase_transition(
            s, old_cycle_phase="plan", new_cycle_phase="evaluate", actor="agent"
        )


def test_objetivo_transition_with_agent_actor_allowed():
    o = _make_objetivo()
    # No exception
    validate_phase_transition(
        o, old_cycle_phase="plan", new_cycle_phase="adjust", actor="agent"
    )


def test_meta_transition_with_agent_actor_allowed():
    m = _make_meta()
    # No exception
    validate_phase_transition(
        m, old_cycle_phase="plan", new_cycle_phase="evaluate", actor="agent"
    )


def test_creation_no_transition_skips_check():
    s = _make_sonho()
    # old=None means creation, no transition
    validate_phase_transition(
        s, old_cycle_phase=None, new_cycle_phase="plan", actor="agent"
    )


def test_same_phase_no_transition_skips_check():
    o = _make_objetivo()
    validate_phase_transition(
        o, old_cycle_phase="plan", new_cycle_phase="plan", actor="agent"
    )
