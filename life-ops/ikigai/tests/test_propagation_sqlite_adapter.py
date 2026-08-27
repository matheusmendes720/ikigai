"""Tests for ikigai.propagation.sqlite_adapter — upsert method."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from ikigai.propagation.sqlite_adapter import SQLiteAdapter, SCHEMA_SQL


class TestUpsert:
    """Tests for SQLiteAdapter.upsert()."""

    @pytest.fixture
    def adapter(self) -> SQLiteAdapter:
        """Create a file-based SQLiteAdapter with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield SQLiteAdapter(db_path=db_path)

    def test_upsert_insert(self, adapter: SQLiteAdapter) -> None:
        """upsert() should insert a new entity."""
        adapter.upsert(
            ueid="t:e:s:00000001:00000001",
            entity_type="goal",
            slug="test-goal",
            title="Test Goal",
            description="A test goal",
            status="ACTIVE",
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
            tags=["test", "unit"],
            ikigai_vectors={"passion": 0.8, "skill": 0.6},
        )

        result = adapter.get_by_ueid("t:e:s:00000001:00000001")
        assert result is not None
        assert result["ueid"] == "t:e:s:00000001:00000001"
        assert result["entity_type"] == "goal"
        assert result["slug"] == "test-goal"
        assert result["title"] == "Test Goal"
        assert result["description"] == "A test goal"
        assert result["status"] == "ACTIVE"
        assert result["tags"] == '["test", "unit"]'
        assert result["ikigai_vectors"] == '{"passion": 0.8, "skill": 0.6}'

    def test_upsert_update_preserves_history(self, adapter: SQLiteAdapter) -> None:
        """upsert() should update existing entity and preserve history."""
        # Insert initial entity
        adapter.upsert(
            ueid="t:e:s:00000001:00000002",
            entity_type="goal",
            slug="update-test",
            title="Original Title",
            status="ACTIVE",
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
        )

        # Update the entity
        adapter.upsert(
            ueid="t:e:s:00000001:00000002",
            entity_type="goal",
            slug="update-test",
            title="Updated Title",
            status="ACTIVE",
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-27T00:00:00Z",
        )

        # Verify update
        result = adapter.get_by_ueid("t:e:s:00000001:00000002")
        assert result is not None
        assert result["title"] == "Updated Title"

        # Verify history has both entries
        history = adapter.history_for("t:e:s:00000001:00000002")
        assert len(history) == 2
        assert history[0]["change_kind"] == "created"
        assert history[1]["change_kind"] == "updated"

        # Verify original snapshot preserved
        created_snapshot = json.loads(history[0]["snapshot"])
        assert created_snapshot["title"] == "Original Title"

    def test_upsert_with_all_fields(self, adapter: SQLiteAdapter) -> None:
        """upsert() should handle all fields including optional ones."""
        adapter.upsert(
            ueid="t:e:s:00000001:00000003",
            entity_type="dream",
            slug="full-fields-dream",
            title="Full Fields Dream",
            description="Dream with all fields",
            parent_ueid="t:e:s:00000001:00000002",
            related_ueids=["t:e:s:00000001:00000004", "t:e:s:00000001:00000005"],
            status="ACTIVE",
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
            last_reviewed_at="2026-08-25T00:00:00Z",
            archived_at=None,
            ikigai_vectors={"passion": 0.9, "skill": 0.7, "market": 0.5},
            vector_weights_snapshot={"passion": 0.4, "skill": 0.3, "market": 0.3},
            phase_at_creation="creation",
            regime_at_creation="push",
            horizon_days=90,
            primary_score=0.85,
            is_placeholder=False,
            placeholder_owner=None,
            claimed_by="matheus",
            source="ikigai",
            source_md_path="/data/matheus/dreams/full-fields-dream.md",
            custom={"key": "value"},
            tags=["priority", "q3-2026"],
        )

        result = adapter.get_by_ueid("t:e:s:00000001:00000003")
        assert result is not None
        assert result["parent_ueid"] == "t:e:s:00000001:00000002"
        assert result["related_ueids"] == '["t:e:s:00000001:00000004", "t:e:s:00000001:00000005"]'
        assert result["last_reviewed_at"] == "2026-08-25T00:00:00Z"
        assert result["phase_at_creation"] == "creation"
        assert result["regime_at_creation"] == "push"
        assert result["horizon_days"] == 90
        assert result["primary_score"] == '{"value": 0.85, "unit": "score"}'
        assert result["claimed_by"] == "matheus"
        assert result["source"] == "ikigai"
        assert result["source_md_path"] == "/data/matheus/dreams/full-fields-dream.md"
        assert result["custom"] == '{"key": "value"}'
        assert result["tags"] == '["priority", "q3-2026"]'

    def test_upsert_default_values(self, adapter: SQLiteAdapter) -> None:
        """upsert() should use sensible defaults for optional fields."""
        adapter.upsert(
            ueid="t:e:s:00000001:00000004",
            entity_type="goal",
            slug="defaults-test",
            title="Defaults Test",
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
        )

        result = adapter.get_by_ueid("t:e:s:00000001:00000004")
        assert result is not None
        assert result["status"] == "ACTIVE"  # default
        assert result["description"] == ""  # default
        assert result["related_ueids"] == "[]"  # default
        assert result["ikigai_vectors"] == "{}"  # default
        assert result["vector_weights_snapshot"] == "{}"  # default
        assert result["is_placeholder"] == 0  # default
        assert result["source"] == "ikigai"  # default

    def test_upsert_placeholder_entity(self, adapter: SQLiteAdapter) -> None:
        """upsert() should handle placeholder entities."""
        adapter.upsert(
            ueid="t:e:s:00000001:00000005",
            entity_type="objective",
            slug="placeholder-obj",
            title="Placeholder Objective",
            is_placeholder=True,
            placeholder_owner="matheus",
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
        )

        result = adapter.get_by_ueid("t:e:s:00000001:00000005")
        assert result is not None
        assert result["is_placeholder"] == 1
        assert result["placeholder_owner"] == "matheus"


class TestUpsertSchema:
    """Tests for upsert with canonical 24-col schema."""

    @pytest.fixture
    def adapter(self) -> SQLiteAdapter:
        """Create a file-based SQLiteAdapter with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "schema_test.db"
            yield SQLiteAdapter(db_path=db_path)

    def test_schema_has_26_columns(self, adapter: SQLiteAdapter) -> None:
        """Verify the canonical schema has exactly 26 columns (ueid through mtime)."""
        with adapter._connect() as conn:
            cols = conn.execute("PRAGMA table_info(plan_entities)").fetchall()
            assert len(cols) == 26, f"Expected 26 columns, got {len(cols)}"

    def test_schema_has_history_table(self, adapter: SQLiteAdapter) -> None:
        """Verify history table exists."""
        with adapter._connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert "plan_entities_history" in table_names
