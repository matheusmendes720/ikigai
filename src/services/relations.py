"""Graph navigation over the artifact edges.

The graph is part of the DOM, so traversing it is a service concern rather than
a query the client writes. Traversal is bounded and cycle-safe: a graph that
points back at itself must terminate.
"""

from __future__ import annotations

from typing import Any

from src.contracts.dom import Relation, RelationType
from src.data.repository import ArtifactRepository

__all__ = ["RelationService"]


class RelationService:
    """Reads and writes the edges between artifacts."""

    def __init__(self, repo: ArtifactRepository) -> None:
        self._repo = repo

    async def neighbors(
        self,
        uid: Any,
        rel: RelationType | None = None,
    ) -> list[Relation]:
        """Edges touching the artifact, optionally limited to one relation type."""
        return await self._repo.list_relations(uid, rel)

    async def traverse(
        self,
        uid: Any,
        rel: RelationType | None = None,
        depth: int = 1,
    ) -> list[Relation]:
        """Every edge reachable within `depth` hops, without revisiting an artifact."""
        seen: set[str] = {str(uid)}
        collected: list[Relation] = []
        frontier = [str(uid)]

        for _ in range(max(depth, 0)):
            next_frontier: list[str] = []
            for node in frontier:
                for relation in await self._repo.list_relations(node, rel):
                    if relation not in collected:
                        collected.append(relation)
                    other = relation.dst_uid if str(relation.src_uid) == node else relation.src_uid
                    key = str(other)
                    if key not in seen:
                        seen.add(key)
                        next_frontier.append(key)
            frontier = next_frontier
            if not frontier:
                break
        return collected

    async def link(
        self,
        src_uid: Any,
        dst_uid: Any,
        rel: RelationType,
        *,
        weight: float | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Relation:
        """Create or update an edge."""
        relation = Relation(
            src_uid=src_uid,
            dst_uid=dst_uid,
            rel=rel,
            weight=weight,
            meta=meta or {},
        )
        await self._repo.upsert_relation(relation)
        return relation
