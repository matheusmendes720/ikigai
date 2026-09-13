"""UEID — 4-part canonical identifier per ADR-014.

Format: <namespace>:<slug>:<uuid>:<hash>
Namespaces: 2-5 lowercase letters (ikigai, tw, obsidian, external, …).

Canonical regex matches `src/contracts/common.py:34`.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

UEID = Annotated[
    str,
    StringConstraints(
        # ADR-014 canonical: 4-part UEID regex (matches src/contracts/common.py:34)
        # ^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$
        pattern=r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$",
        min_length=1,
    ),
]

__all__ = ["UEID"]
