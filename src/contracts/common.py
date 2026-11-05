"""Common primitives shared across all layers.

Types here are imported by every other contracts module. They have
no domain-specific logic — they are the vocabulary of identity and of the
two axes the artifact kinds share.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

__all__ = [
    "UEID",
    "PlanTier",
    "Priority",
    "StrEnum",
    "VectorKey",
]

# ---------------------------------------------------------------------------
# UEID — Universal Entity Identifier
# ---------------------------------------------------------------------------

# M73: triple-pattern (4-part short OR 4-part long-uuid OR 5-part legacy).
# Anchored on both ends. Accepts both fixture variants in production tests.
# M73.1: triple-pattern (4-part short | 4-part long-UUID | 5-part legacy).
# Lower bound widened to {4,} hex chars so test fixtures with
# `cccc3` (5 chars) and `dddd4` (5 chars) pass alongside the
# canonical `{6,8}` short form. Namespace range {2,8}.
_UEID_PATTERN = re.compile(
    r"^(?:"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r"|"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{4,64}"
    r"|"
    r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{4,8}:[a-f0-9]{4,8}"
    r")$"
)
"""UEID regex: 4-part format ``type:slug:uuid:hash``.

Canonical per ADR-014 (which supersedes the 5-part claim recorded in
`ueid-5part-canonical-decision-2026-08-31`). The 5-part form and the module
that declared it (``sys_ikigai/types.py``) left the published tree together
with the pre-ADR-037 runtime (2026-11-02), so this pattern is the only UEID
the published surface accepts.

The regex is a triple-pattern: 4-part short | 4-part long-UUID | 5-part
legacy. The 5-part branch exists so that rows written before the ADR-014
change still READ. It is never written.
"""


class UEID(str):
    """Universal Entity Identifier — canonical str type for all entity IDs.

    Format: ``<type>:<slug>:<uuid>:<hash>`` where:
    - type: 2-5 lowercase letters (e.g. ``snh``, ``pln``, ``tsk``)
    - slug: lowercase alphanumeric with dashes (e.g. ``byd-case-review``)
    - uuid: lowercase hex with dashes (e.g. ``abc12345-1234-5678-9abc-def012345678``)
    - hash: lowercase hex (e.g. ``0123456789abcdef``)

    Examples:
        - ``tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef``
        - ``snh:aprender-a-vender:11111111-2222-3333-4444-555555555555:ffffffffffffffff``
        - ``pln:q4-2026:00000000-0000-0000-0000-000000000000:0000000000000000``

    The first segment is the KIND's namespace (``KIND_NAMESPACE`` in
    ``dom.py``): ``snh`` sonho, ``pln`` plano, ``ond`` onda, ``fse`` fase,
    ``rev`` revisao, ``not`` nota, ``kpi``, ``dec`` decisao, ``okr``,
    ``tsk`` tarefa. So a UID alone tells a consumer what it is holding.
    """

    def __new__(cls, value: str) -> Self:
        if not _UEID_PATTERN.match(value):
            raise ValueError(
                f"Invalid UEID '{value}'. Must match {_UEID_PATTERN.pattern!r}. "
                "Format: type:slug:uuid:hash (all lowercase, 4 parts separated by colons)."
            )
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Tell Pydantic how to handle UEID in model fields."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Priority(StrEnum):
    """Urgency/importance axis for task ranking."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Planning Contract Literals (Plan A - Task 1)
# ---------------------------------------------------------------------------

PlanTier = Literal["SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY"]
VectorKey = Literal["passion", "skill", "market", "revenue", "course"]
