"""UEID — canonical identifier per ADR-014 (with legacy compatibility).

Canonical format (4-part per ADR-014):
    <namespace>:<slug>:<uuid_short>:<content_hash_short>

Legacy format (5-part, accepted for backward-compat with existing fixtures):
    <namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>

Both regex branches are anchored; the validator picks whichever matches.
The short-form uses 6-8 hex chars; the long-form uses 8-36 (full UUID
allowed for fixture keys like `tsk:foo:11111111-1111-...:1111111111111111`).
Namespaces: 2-8 lowercase letters (ikigai, tw, obsidian, external, ...).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

_UEID_PATTERN = (
    r"^(?:"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{6,8}:[a-f0-9]{6,8}"
    r"|"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{6,64}"
    r"|"
    r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{6,8}:[a-f0-9]{6,8}"
    r")$"
)

UEID = Annotated[
    str,
    StringConstraints(
        pattern=_UEID_PATTERN,
        min_length=1,
    ),
]

__all__ = ["UEID"]
