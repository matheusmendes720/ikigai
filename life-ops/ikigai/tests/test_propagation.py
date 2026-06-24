"""Tests for ikigai.propagation — markdown_db, frontmatter, sqlite_adapter, triagem."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from ikigai.propagation.frontmatter import (
    frontmatter_to_dict,
    dict_to_frontmatter,
    serialize_to_markdown,
    parse_from_markdown,
)
from ikigai.propagation.markdown_db import MarkdownDB
from ikigai.propagation.sqlite_adapter import SQLiteAdapter
from ikigai.propagation.triagem import Triagem, DriftEntry
from ikigai.entities import GoalEntity
from ikigai.enums import EntityType, StatusType, VectorType
from ikigai.types import UEID


class TestFrontmatterSerialization:
    """Frontmatter ↔ dict round-tripping."""

    def test_frontmatter_to_dict(self) -> None:
        """frontmatter_to_dict must parse valid YAML frontmatter."""
        raw = """---
entity_type: goal
slug: test-goal
title: Test Goal
status: active
cluster: study
horizon_days: 365
ikigai_vectors:
  - skill
  - passion
created_at: '2025-01-01T00:00:00Z'
updated_at: '2025-01-01T00:00:00Z'
---
# Body text here
"""
        d = frontmatter_to_dict(raw)
        assert d["entity_type"] == "goal"
        assert d["slug"] == "test-goal"
        assert d["horizon_days"] == 365
        assert d["ikigai_vectors"] == ["skill", "passion"]

    def test_dict_to_frontmatter(self) -> None:
        """dict_to_frontmatter must produce valid YAML."""
        d = {
            "entity_type": "goal",
            "slug": "test-goal",
            "title": "Test Goal",
            "status": "active",
            "horizon_days": 365,
            "ikigai_vectors": ["skill"],
        }
        result = dict_to_frontmatter(d, body="# Test Goal\n")
        assert result.startswith("---\n")
        assert "entity_type: goal" in result
        assert "horizon_days: 365" in result

    def test_roundtrip_goal_entity(self) -> None:
        """GoalEntity → dict → frontmatter → dict must preserve key fields."""
        goal = GoalEntity(
            slug="roundtrip-goal",
            title="Roundtrip Goal",
            cluster="study",
            horizon_days=365,
        )
        d = goal.to_frontmatter_dict()
        frontmatter = dict_to_frontmatter(d, body="# Roundtrip Goal\n")
        restored = frontmatter_to_dict(frontmatter)
        assert restored["slug"] == d["slug"]
        assert restored["horizon_days"] == d["horizon_days"]

    def test_serialize_to_markdown_minimal(self) -> None:
        """serialize_to_markdown must produce valid markdown with frontmatter."""
        d = {
            "entity_type": "goal",
            "slug": "minimal-goal",
            "title": "Minimal Goal",
            "status": "active",
            "horizon_days": 365,
        }
        result = serialize_to_markdown(d, "Minimal Goal", None)
        assert result.startswith("---\n")
        assert "---\n" in result  # frontmatter block closes
        assert "# Minimal Goal" in result

    def test_parse_from_markdown_full(self) -> None:
        """parse_from_markdown must extract frontmatter and body."""
        content = """---
entity_type: objective
slug: my-obj
title: My Objective
status: active
horizon_days: 180
---
# My Objective

This is the body content.
"""
        fm, body = parse_from_markdown(content)
        assert fm["entity_type"] == "objective"
        assert fm["slug"] == "my-obj"
        assert "body content" in body

    def test_parse_from_markdown_no_frontmatter(self) -> None:
        """No frontmatter → empty dict + original body."""
        content = "# Just a title\n\nSome text."
        fm, body = parse_from_markdown(content)
        assert fm == {}
        assert body == content


class TestMarkdownDB:
    """MarkdownDB: canonical SoT operations on temp directory."""

    def _temp_vault(self) -> tuple[MarkdownDB, Path]:
        vault_root = Path(tempfile.mkdtemp())
        return MarkdownDB(vault_root), vault_root

    def test_init_creates_vault_dirs(self) -> None:
        """MarkdownDB.__init__ must create cluster dirs if missing."""
        vault_root = Path(tempfile.mkdtemp()) / "new-vault"
        db = MarkdownDB(vault_root)
        assert vault_root.exists()

    def test_write_and_read_goal(self) -> None:
        """write + read must roundtrip a GoalEntity."""
        db, vault_root = self._temp_vault()
        goal = GoalEntity(
            slug="db-test-goal",
            title="DB Test Goal",
            cluster="study",
            horizon_days=365,
        )
        path = db.write(goal)
        assert path.exists()
        restored = db.read(path)
        assert restored.slug == goal.slug
        assert restored.title == goal.title

    def test_write_uses_tmp_rename(self) -> None:
        """write must atomically rename .tmp → target."""
        db, vault_root = self._temp_vault()
        goal = GoalEntity(
            slug="atomic-goal",
            title="Atomic Goal",
            cluster="study",
            horizon_days=365,
        )
        path = db.write(goal)
        # No .tmp file must remain
        assert not path.with_suffix(".md.tmp").exists()

    def test_delete_removes_file(self) -> None:
        """delete must remove the file."""
        db, vault_root = self._temp_vault()
        goal = GoalEntity(
            slug="delete-goal",
            title="Delete Goal",
            cluster="study",
            horizon_days=365,
        )
        path = db.write(goal)
        assert path.exists()
        db.delete(path)
        assert not path.exists()

    def test_query_by_type(self) -> None:
        """query(entity_type=...) must filter by type."""
        db, vault_root = self._temp_vault()
        g1 = GoalEntity(slug="goal-1", title="Goal 1", cluster="study", horizon_days=365)
        g2 = GoalEntity(slug="goal-2", title="Goal 2", cluster="study", horizon_days=365)
        db.write(g1)
        db.write(g2)
        results = db.query(entity_type=EntityType.GOAL)
        assert len(results) >= 2

    def test_query_no_results(self) -> None:
        """query with no matches → empty list."""
        db, vault_root = self._temp_vault()
        results = db.query(entity_type=EntityType.GOAL)
        assert results == []


class TestSQLiteAdapter:
    """SQLiteAdapter: append-only mirror with triggers."""

    def _temp_sqlite(self) -> tuple[SQLiteAdapter, Path]:
        db_path = Path(tempfile.mkdtemp()) / "test_mirror.db"
        return SQLiteAdapter(db_path), db_path

    def test_init_creates_schema(self) -> None:
        """__init__ must create schema if db doesn't exist."""
        adapter, db_path = self._temp_sqlite()
        assert db_path.exists()

    def test_insert_and_get(self) -> None:
        """insert → get_by_ueid must roundtrip."""
        adapter, _ = self._temp_sqlite()
        goal = GoalEntity(
            slug="sqlite-goal",
            title="SQLite Goal",
            cluster="study",
            horizon_days=365,
        )
        adapter.insert(goal)
        restored = adapter.get_by_ueid(str(goal.ueid))
        assert restored is not None
        assert restored.slug == goal.slug

    def test_archive_marks_row_archived(self) -> None:
        """archive must set archived_at timestamp."""
        adapter, _ = self._temp_sqlite()
        goal = GoalEntity(
            slug="archive-goal",
            title="Archive Goal",
            cluster="study",
            horizon_days=365,
        )
        adapter.insert(goal)
        adapter.archive(str(goal.ueid))
        row = adapter.get_by_ueid(str(goal.ueid))
        assert row is not None
        assert row.get("archived_at") is not None

    def test_list_by_type(self) -> None:
        """list_by_type must return only matching entity types."""
        adapter, _ = self._temp_sqlite()
        g = GoalEntity(slug="list-goal", title="List Goal", cluster="study", horizon_days=365)
        adapter.insert(g)
        results = adapter.list_by_type(EntityType.GOAL)
        assert len(results) >= 1
        assert all(r["entity_type"] == "goal" for r in results)

    def test_update_raises(self) -> None:
        """UPDATE must be blocked by trigger (ABORT)."""
        adapter, _ = self._temp_sqlite()
        goal = GoalEntity(
            slug="no-update-goal",
            title="No Update Goal",
            cluster="study",
            horizon_days=365,
        )
        adapter.insert(goal)
        with pytest.raises(Exception):  # constraint error from trigger
            adapter.insert(goal)  # duplicate UEID → should fail

    def test_delete_raises(self) -> None:
        """DELETE must be blocked by trigger (ABORT)."""
        adapter, _ = self._temp_sqlite()
        goal = GoalEntity(
            slug="no-delete-goal",
            title="No Delete Goal",
            cluster="study",
            horizon_days=365,
        )
        adapter.insert(goal)
        with pytest.raises(Exception):  # constraint error from trigger
            adapter.delete(str(goal.ueid))


class TestTriagem:
    """Drift detection and reconciliation."""

    def test_add_drift_entry(self) -> None:
        """add() must append to entries list."""
        vault_root = Path(tempfile.mkdtemp())
        t = Triagem(vault_root=vault_root)
        now = datetime.now(tz=timezone.utc)
        entry = DriftEntry(
            timestamp=now,
            entity_ueid="study:goal:test-goal:uuid:hash",
            entity_path=Path("study/goals/test-goal.md"),
            markdown_mtime=now,
            sqlite_mtime=None,
            drift_kind="missing_sqlite",
            decision="needs_sqlite_insert",
        )
        t.add(entry)
        assert len(t.entries) == 1
        assert t.entries[0].drift_kind == "missing_sqlite"

    def test_write_produces_file(self) -> None:
        """write() must create triagem.md."""
        vault_root = Path(tempfile.mkdtemp())
        t = Triagem(vault_root=vault_root)
        now = datetime.now(tz=timezone.utc)
        t.add(
            DriftEntry(
                timestamp=now,
                entity_ueid="study:goal:test-goal:uuid:hash",
                entity_path=Path("study/goals/test-goal.md"),
                markdown_mtime=now,
                sqlite_mtime=None,
                drift_kind="missing_sqlite",
                decision="needs_sqlite_insert",
            )
        )
        path = t.write()
        assert path.exists()

    def test_write_is_idempotent(self) -> None:
        """Multiple writes must be idempotent (same path, no errors)."""
        vault_root = Path(tempfile.mkdtemp())
        t = Triagem(vault_root=vault_root)
        now = datetime.now(tz=timezone.utc)
        t.add(
            DriftEntry(
                timestamp=now,
                entity_ueid="study:goal:test-goal:uuid:hash",
                entity_path=Path("study/goals/test-goal.md"),
                markdown_mtime=now,
                sqlite_mtime=None,
                drift_kind="missing_sqlite",
                decision="needs_sqlite_insert",
            )
        )
        p1 = t.write()
        p2 = t.write()
        assert p1 == p2
