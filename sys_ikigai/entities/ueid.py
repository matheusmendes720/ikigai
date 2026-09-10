"""UEID — 4-part canonical identifier per ADR-014 (supersedes 2026-08-31 5-part).

Format: <namespace>:<entity_type>:<uuid>:<seq>
Regex:   ^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$
Namespaces: 2-5 lowercase letters (ikigai | tw | obsidian | external | kill)

History:
- 2026-08-31: 5-part format (namespace:entity:slug:uuid_short:hash_short)
- 2026-09-05: canonical switched to 4-part per ADR-014; subgraph.py + kill_switch.py
  already use 4-part but sys_ikigai/entities/ueid.py was stale.
- 2026-09-10 (B1 fix): aligned sys_ikigai/entities/ueid.py to 4-part to match
  v2 graph + kill_switch + subgraph + agent_consumer validation chain.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

UEID = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$",
        min_length=1,
    ),
]

__all__ = ["UEID"]
