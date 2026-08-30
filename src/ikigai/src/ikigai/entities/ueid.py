"""UEID — 5-part canonical identifier per SPEC D10 + §3.1.

Format: <namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>
Namespaces: ikigai | tw | obsidian | external
"""

from __future__ import annotations

from typing import Annotated
from pydantic import StringConstraints

UEID = Annotated[
    str,
    StringConstraints(
        pattern=r"^(ikigai|tw|obsidian|external):[a-z_]+:[a-z0-9_-]+:[0-9a-f]{8}:[0-9a-f]{8}$",
        min_length=1,
    ),
]

__all__ = ["UEID"]
