"""One composition root: the vault ingestion shares the services' repository.

The sync used to open its own DataClient, a second pool beside the one the
tools use. build_services now wires VaultSync against the SAME repository, so
there is one pool and one write path through the data layer (ADR-037 D5).

Falsification: revert build_services to leave vault_sync unset, or give the
sync its own repository, and this fails.
"""

from __future__ import annotations

import pytest

from src.services.sync import VaultSync
from src.services.wiring import build_services


def test_vault_sync_shares_the_services_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IKIGAI_STORE_DSN", "postgresql://u:p@127.0.0.1:5432/db")
    services = build_services()
    assert isinstance(services.vault_sync, VaultSync)
    assert services.vault_sync._repo is services.artifacts._repo
