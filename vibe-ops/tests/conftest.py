"""Shared pytest fixtures for the vault-bidirectional-sync test suite.

Source: .omo/plans/vault-bidirectional-sync.md (T9)
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Iterator

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))


def _make_planning_db(db_path: Path) -> None:
    """Minimal planning_entities table matching the live schema."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS planning_entities (
                id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                upstream_id TEXT NOT NULL,
                synced_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL,
                PRIMARY KEY (id, entity_type)
            )
            """
        )
        conn.commit()


@pytest.fixture
def fixture_vault() -> Path:
    """Absolute path to the canonical 7-file test vault."""
    return Path(__file__).parent / "fixtures" / "vault"


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Ephemeral copy of the fixture vault for mutation-safe tests."""
    src = Path(__file__).parent / "fixtures" / "vault"
    dst = tmp_path / "vault"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Ephemeral SQLite DB with planning_entities schema bootstrapped."""
    db = tmp_path / "vibe_ops.db"
    _make_planning_db(db)
    return db


@pytest.fixture
def sync_engine(temp_vault: Path, temp_db: Path):
    """A BidirectionalSync instance bound to the temp vault + DB."""
    from middleware.bidirectional_sync import BidirectionalSync
    return BidirectionalSync(temp_vault, temp_db)


@pytest.fixture
def populated_sync_engine(temp_vault: Path, temp_db: Path):
    """Sync engine with vault pre-ingested once."""
    from middleware.bidirectional_sync import BidirectionalSync
    sync = BidirectionalSync(temp_vault, temp_db)
    sync.sync_vault_to_code()
    return sync