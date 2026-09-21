"""UEID — canonical identifier per ADR-014 (with legacy compatibility).

Canonical format (4-part per ADR-014):
    <namespace>:<slug>:<uuid_short>:<content_hash_short>

Legacy format (5-part, accepted for backward-compat with existing fixtures):
    <namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>

Both regex branches are anchored; the validator picks whichever matches.
The short-form uses 4-8 hex chars; the long-form uses 8-36 (full UUID
allowed for fixture keys like `tsk:foo:11111111-1111-...:1111111111111111`).
Namespaces: 2-8 lowercase letters (ikigai, tw, obsidian, external, ...).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

# R4.2-followup: import the canonical pattern from src/contracts/common per
# ADR-033 (single source of truth). Previously this file redeclared the
# triple-pattern; the redeclaration is now removed so any future regex
# amendment happens in exactly one place.
from src.contracts.common import _UEID_PATTERN  # re-exported for backward compat

UEID = Annotated[
    str,
    StringConstraints(
        pattern=_UEID_PATTERN,
        min_length=1,
    ),
]

__all__ = ["UEID", "_UEID_PATTERN"]
