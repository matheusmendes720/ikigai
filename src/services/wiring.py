"""The wiring of the service layer against the store.

The composition root lives HERE, not in the transport. A transport that
builds its own services has to import the data client — and then the
transport depends on the store, which breaks the pyramid ADR-037 D5 draws:

    transport  →  services  →  data  →  Postgres

The service layer is the layer that knows what the store is, so it is the
layer that knows how to build itself against it. The transport asks the
service layer for its wiring and translates intent into calls; it never
learns how the store is reached.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.data.client import DataClient
from src.data.repository import ArtifactRepository
from src.services.artifacts import ArtifactService
from src.services.embeddings import EmbeddingService
from src.services.relations import RelationService

__all__ = ["Services", "build_services"]


@dataclass
class Services:
    """The service wiring the tools call into."""

    artifacts: ArtifactService
    relations: RelationService
    embeddings: EmbeddingService


def build_services() -> Services:
    """Wire the services against the configured store.

    Nothing here connects: the store client opens its pool on first use, so
    building the wiring is cheap and never fails on a missing driver.
    """
    client = DataClient()
    repo = ArtifactRepository(client)
    return Services(
        artifacts=ArtifactService(repo),
        relations=RelationService(repo),
        embeddings=EmbeddingService(client),
    )
