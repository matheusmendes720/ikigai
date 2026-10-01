"""M164: td tag subsystem — unit tests.

Covers the 4 subcommands (add / remove / list / clear) plus the underlying
adapter helpers (add_tags / remove_tags / clear_tags / get_tags). The goal
is to lock in:

  - tag validation regex (alphanumeric+hyphen+underscore, 1-32 chars)
  - idempotency (add of existing tag is a no-op; remove of missing tag is no-op)
  - audit_log entries on every mutation (in-row JSON column + file)
  - JSON serialization roundtrip
  - lookup error on missing UEID
  - propagation through the review queue + apply_change dispatch

Test isolation:
  - Each test uses ``tmp_path`` for a fresh SQLite DB and monkeypatches
    ``src.mesh.adapters.taskdog.TASKDOG_DB`` (the dual-module identity
    pattern from conftest.py).
  - Each test seeds one row so the helpers have a target to mutate.

Run with:
    cd src/ikigai && python -m pytest tests/test_td_tag.py -q
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# Imports go through the dotted-prefix path that the production code uses
# (per the dual-module identity rule in tests/conftest.py).
from src.contracts.task_change import PropagationEvent, TaskAction
from src.mesh.adapters import taskdog as taskdog_mod
from src.mesh.adapters.taskdog import (
    TaskdogAdapter,
    add_tags,
    clear_tags,
    get_tags,
    remove_tags,
)
from src.mesh.cli import td_tag

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def tag_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fresh taskdog DB with the M163 schema + one seed task."""
    db_path = tmp_path / "tasks.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ueid TEXT UNIQUE,
                name TEXT,
                status TEXT,
                priority INTEGER,
                planned_start TEXT,
                planned_end TEXT,
                deadline TEXT,
                created_at TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                deps TEXT NOT NULL DEFAULT '[]',
                audit_log TEXT NOT NULL DEFAULT '[]',
                started_at TEXT,
                completed_at TEXT,
                priority_label TEXT NOT NULL DEFAULT 'P2'
            );
        """)
        conn.execute(
            "INSERT INTO tasks (ueid, name, status, priority, created_at) "
            "VALUES (?, ?, 'planned', ?, ?)",
            ("ikigai:task:deadbeef:1234", "Tag test task", 2,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(taskdog_mod, "TASKDOG_DB", db_path)
    return db_path


@pytest.fixture
def tag_db_with_tags(tag_db: Path) -> Path:
    """Seed: 1 task with 2 pre-existing tags (`backend`, `urgent`)."""
    conn = sqlite3.connect(tag_db)
    try:
        conn.execute(
            "UPDATE tasks SET tags=? WHERE ueid=?",
            (json.dumps(["backend", "urgent"]),
             "ikigai:task:deadbeef:1234"),
        )
        conn.commit()
    finally:
        conn.close()
    return tag_db


# ----------------------------------------------------------------------
# Validation regex
# ----------------------------------------------------------------------

class TestTagValidation:
    def test_valid_tags(self) -> None:
        """The regex accepts the canonical tag shapes."""
        for tag in ["foo", "FOO", "foo_bar", "foo-bar", "Foo_123", "x"]:
            assert taskdog_mod._is_valid_tag(tag), f"expected valid: {tag!r}"

    def test_invalid_empty(self) -> None:
        assert not taskdog_mod._is_valid_tag("")

    def test_invalid_too_long(self) -> None:
        assert not taskdog_mod._is_valid_tag("a" * 33)
        # Boundary: 32 chars must be valid
        assert taskdog_mod._is_valid_tag("a" * 32)

    def test_invalid_with_space(self) -> None:
        assert not taskdog_mod._is_valid_tag("foo bar")
        assert not taskdog_mod._is_valid_tag(" ")

    def test_invalid_with_punctuation(self) -> None:
        for bad in ["foo!", "foo@bar", "foo#bar", "foo/bar", "foo.bar",
                    "foo,bar", "foo:bar"]:
            assert not taskdog_mod._is_valid_tag(bad), f"expected invalid: {bad!r}"

    def test_invalid_non_string(self) -> None:
        assert not taskdog_mod._is_valid_tag(None)
        assert not taskdog_mod._is_valid_tag(123)
        assert not taskdog_mod._is_valid_tag(["foo"])
        assert not taskdog_mod._is_valid_tag({"foo": "bar"})

    def test_cli_validate_tag_callback(self) -> None:
        """The argparse type= callback delegates to the adapter validator."""
        assert td_tag._validate_tag("ok_tag") == "ok_tag"
        with pytest.raises(argparse.ArgumentTypeError):
            td_tag._validate_tag("bad tag")
        with pytest.raises(argparse.ArgumentTypeError):
            td_tag._validate_tag("")


# ----------------------------------------------------------------------
# Module-level helpers: add_tags / remove_tags / clear_tags / get_tags
# ----------------------------------------------------------------------

class TestAddTags:
    def test_add_appends_unique(self, tag_db: Path) -> None:
        result = add_tags("ikigai:task:deadbeef:1234", ["backend", "urgent"])
        assert result == ["backend", "urgent"]
        # Roundtrip via the storage column
        conn = sqlite3.connect(tag_db)
        try:
            row = conn.execute(
                "SELECT tags FROM tasks WHERE ueid=?", ("ikigai:task:deadbeef:1234",)
            ).fetchone()
            assert json.loads(row[0]) == ["backend", "urgent"]
        finally:
            conn.close()

    def test_add_is_idempotent(self, tag_db_with_tags: Path) -> None:
        """Adding an already-present tag is a no-op (set semantics)."""
        result = add_tags(
            "ikigai:task:deadbeef:1234", ["backend", "frontend", "urgent"],
        )
        # `frontend` is new; `backend` and `urgent` are deduped.
        assert result == ["backend", "frontend", "urgent"]

    def test_add_to_nonexistent_raises(self, tag_db: Path) -> None:
        with pytest.raises(LookupError, match="not found in taskdog"):
            add_tags("ikigai:task:facefeed:5678", ["urgent"])

    def test_add_invalid_tag_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="invalid tag"):
            add_tags("ikigai:task:deadbeef:1234", ["bad tag"])

    def test_add_invalid_tag_empty_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="invalid tag"):
            add_tags("ikigai:task:deadbeef:1234", [""])

    def test_add_invalid_tag_too_long_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="invalid tag"):
            add_tags("ikigai:task:deadbeef:1234", ["a" * 33])

    def test_add_empty_list_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="at least one tag"):
            add_tags("ikigai:task:deadbeef:1234", [])

    def test_add_invalid_ueid_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="invalid UEID"):
            add_tags("not-a-ueid", ["urgent"])


class TestRemoveTags:
    def test_remove_drops_from_set(self, tag_db_with_tags: Path) -> None:
        result = remove_tags("ikigai:task:deadbeef:1234", ["backend"])
        assert result == ["urgent"]

    def test_remove_missing_tag_is_noop(self, tag_db_with_tags: Path) -> None:
        """Removing a tag that isn't present leaves the set unchanged."""
        result = remove_tags("ikigai:task:deadbeef:1234", ["nonexistent"])
        assert result == ["backend", "urgent"]

    def test_remove_mixed_present_and_missing(
        self, tag_db_with_tags: Path
    ) -> None:
        result = remove_tags(
            "ikigai:task:deadbeef:1234", ["backend", "nonexistent", "urgent"],
        )
        assert result == []

    def test_remove_to_nonexistent_ueid_raises(self, tag_db: Path) -> None:
        with pytest.raises(LookupError, match="not found in taskdog"):
            remove_tags("ikigai:task:facefeed:5678", ["urgent"])

    def test_remove_invalid_tag_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="invalid tag"):
            remove_tags("ikigai:task:deadbeef:1234", ["bad tag"])

    def test_remove_empty_list_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="at least one tag"):
            remove_tags("ikigai:task:deadbeef:1234", [])


class TestClearTags:
    def test_clear_wipes_set(self, tag_db_with_tags: Path) -> None:
        result = clear_tags("ikigai:task:deadbeef:1234")
        assert result == []

    def test_clear_on_empty_is_idempotent(self, tag_db: Path) -> None:
        result = clear_tags("ikigai:task:deadbeef:1234")
        assert result == []

    def test_clear_missing_ueid_raises(self, tag_db: Path) -> None:
        with pytest.raises(LookupError, match="not found in taskdog"):
            clear_tags("ikigai:task:facefeed:5678")


class TestGetTags:
    def test_get_returns_list(self, tag_db_with_tags: Path) -> None:
        assert get_tags("ikigai:task:deadbeef:1234") == ["backend", "urgent"]

    def test_get_returns_empty_when_no_tags(self, tag_db: Path) -> None:
        assert get_tags("ikigai:task:deadbeef:1234") == []

    def test_get_missing_ueid_raises(self, tag_db: Path) -> None:
        with pytest.raises(LookupError, match="not found in taskdog"):
            get_tags("ikigai:task:facefeed:5678")

    def test_get_invalid_ueid_raises(self, tag_db: Path) -> None:
        with pytest.raises(ValueError, match="invalid UEID"):
            get_tags("not-a-ueid")


# ----------------------------------------------------------------------
# Audit log: every mutation writes an entry
# ----------------------------------------------------------------------

class TestAuditLog:
    def test_add_writes_audit_entry(self, tag_db: Path) -> None:
        add_tags("ikigai:task:deadbeef:1234", ["backend", "urgent"])
        audit = _read_audit_log(tag_db)
        assert len(audit) == 1
        entry = audit[0]
        assert entry["action"] == "tag_add"
        assert entry["actor"] == "cli"
        assert "timestamp" in entry
        assert entry["fields_diff"]["added"] == ["backend", "urgent"]
        assert entry["fields_diff"]["before"] == []
        assert entry["fields_diff"]["after"] == ["backend", "urgent"]

    def test_remove_writes_audit_entry(self, tag_db_with_tags: Path) -> None:
        remove_tags("ikigai:task:deadbeef:1234", ["backend"])
        audit = _read_audit_log(tag_db_with_tags)
        assert len(audit) == 1
        entry = audit[0]
        assert entry["action"] == "tag_remove"
        assert entry["fields_diff"]["removed"] == ["backend"]
        assert entry["fields_diff"]["before"] == ["backend", "urgent"]
        assert entry["fields_diff"]["after"] == ["urgent"]

    def test_clear_writes_audit_entry(self, tag_db_with_tags: Path) -> None:
        clear_tags("ikigai:task:deadbeef:1234")
        audit = _read_audit_log(tag_db_with_tags)
        assert len(audit) == 1
        entry = audit[0]
        assert entry["action"] == "tag_clear"
        assert entry["fields_diff"]["before"] == ["backend", "urgent"]
        assert entry["fields_diff"]["after"] == []

    def test_multiple_mutations_accumulate(self, tag_db: Path) -> None:
        add_tags("ikigai:task:deadbeef:1234", ["a"])
        add_tags("ikigai:task:deadbeef:1234", ["b"])
        remove_tags("ikigai:task:deadbeef:1234", ["a"])
        clear_tags("ikigai:task:deadbeef:1234")
        audit = _read_audit_log(tag_db)
        assert [e["action"] for e in audit] == [
            "tag_add", "tag_add", "tag_remove", "tag_clear",
        ]

    def test_idempotent_add_no_audit_entry(self, tag_db_with_tags: Path) -> None:
        """Adding a tag that's already present does NOT write audit."""
        # Initial state has [backend, urgent]; adding them again is a no-op
        # at the audit level (the helper short-circuits before writing).
        add_tags("ikigai:task:deadbeef:1234", ["backend", "urgent"])
        audit = _read_audit_log(tag_db_with_tags)
        # No new entry should have been written.
        assert audit == []

    def test_idempotent_remove_no_audit_entry(self, tag_db_with_tags: Path) -> None:
        """Removing a tag that isn't present does NOT write audit."""
        remove_tags("ikigai:task:deadbeef:1234", ["nonexistent"])
        audit = _read_audit_log(tag_db_with_tags)
        assert audit == []


# ----------------------------------------------------------------------
# JSON serialization roundtrip
# ----------------------------------------------------------------------

class TestJsonRoundtrip:
    def test_tags_persist_as_json(self, tag_db: Path) -> None:
        """Tags stored as JSON TEXT roundtrip cleanly through sqlite."""
        add_tags("ikigai:task:deadbeef:1234", ["a", "b", "c"])
        conn = sqlite3.connect(tag_db)
        try:
            row = conn.execute(
                "SELECT tags FROM tasks WHERE ueid=?",
                ("ikigai:task:deadbeef:1234",),
            ).fetchone()
            # The stored value is a JSON string.
            assert isinstance(row[0], str)
            # Roundtrip parse: returns the same list
            assert json.loads(row[0]) == ["a", "b", "c"]
        finally:
            conn.close()

    def test_audit_log_persists_as_json(self, tag_db: Path) -> None:
        add_tags("ikigai:task:deadbeef:1234", ["x"])
        add_tags("ikigai:task:deadbeef:1234", ["y"])
        conn = sqlite3.connect(tag_db)
        try:
            row = conn.execute(
                "SELECT audit_log FROM tasks WHERE ueid=?",
                ("ikigai:task:deadbeef:1234",),
            ).fetchone()
            entries = json.loads(row[0])
            assert len(entries) == 2
            assert all("timestamp" in e for e in entries)
            assert all("action" in e for e in entries)
            # JSON-serializable: re-encode without exception
            json.dumps(entries)
        finally:
            conn.close()

    def test_corrupt_json_falls_back_to_empty(
        self, tag_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Defensive: malformed JSON in tags column reads as empty list."""
        conn = sqlite3.connect(tag_db)
        try:
            conn.execute(
                "UPDATE tasks SET tags=? WHERE ueid=?",
                ("not-valid-json{", "ikigai:task:deadbeef:1234"),
            )
            conn.commit()
        finally:
            conn.close()
        # Should NOT raise — falls back to []
        assert get_tags("ikigai:task:deadbeef:1234") == []


# ----------------------------------------------------------------------
# CLI dispatch (subprocess-style integration)
# ----------------------------------------------------------------------

class TestCliDispatch:
    """Tests for the td_tag cmd_* handlers invoked directly (not via main)."""

    def test_cmd_tag_add_json(self, tag_db: Path) -> None:
        args = argparse_namespace(
            tag_command="add",
            ueid="ikigai:task:deadbeef:1234",
            tag=["backend", "urgent"],
            json=True,
            db_path=str(tag_db),
        )
        rc = td_tag.cmd_tag_add(args)
        assert rc == 0
        assert get_tags("ikigai:task:deadbeef:1234") == ["backend", "urgent"]

    def test_cmd_tag_remove_json(self, tag_db_with_tags: Path) -> None:
        args = argparse_namespace(
            tag_command="remove",
            ueid="ikigai:task:deadbeef:1234",
            tag=["backend"],
            json=True,
            db_path=str(tag_db_with_tags),
        )
        rc = td_tag.cmd_tag_remove(args)
        assert rc == 0
        assert get_tags("ikigai:task:deadbeef:1234") == ["urgent"]

    def test_cmd_tag_list_json(self, tag_db_with_tags: Path) -> None:
        args = argparse_namespace(
            tag_command="list",
            ueid="ikigai:task:deadbeef:1234",
            json=True,
            db_path=str(tag_db_with_tags),
        )
        rc = td_tag.cmd_tag_list(args)
        assert rc == 0

    def test_cmd_tag_clear_json(self, tag_db_with_tags: Path) -> None:
        args = argparse_namespace(
            tag_command="clear",
            ueid="ikigai:task:deadbeef:1234",
            json=True,
            db_path=str(tag_db_with_tags),
        )
        rc = td_tag.cmd_tag_clear(args)
        assert rc == 0
        assert get_tags("ikigai:task:deadbeef:1234") == []

    def test_cmd_tag_add_invalid_tag_returns_2(self, tag_db: Path) -> None:
        args = argparse_namespace(
            tag_command="add",
            ueid="ikigai:task:deadbeef:1234",
            tag=["bad tag"],
            json=True,
            db_path=str(tag_db),
        )
        # argparse type= would have rejected first; emulate post-validation
        # by hand to test the runtime guard too.
        rc = td_tag.cmd_tag_add(args)
        assert rc == 2  # ValueError → exit 2

    def test_cmd_tag_add_missing_ueid_returns_1(self, tag_db: Path) -> None:
        args = argparse_namespace(
            tag_command="add",
            ueid="ikigai:task:facefeed:5678",
            tag=["x"],
            json=True,
            db_path=str(tag_db),
        )
        rc = td_tag.cmd_tag_add(args)
        assert rc == 1  # LookupError → exit 1

    def test_run_tag_command_dispatches(self, tag_db_with_tags: Path) -> None:
        args = argparse_namespace(
            command="tag",
            tag_command="list",
            ueid="ikigai:task:deadbeef:1234",
            json=True,
            db_path=str(tag_db_with_tags),
        )
        rc = td_tag.run_tag_command(args)
        assert rc == 0

    def test_run_tag_command_unknown_returns_2(self) -> None:
        args = argparse_namespace(command="tag", tag_command="bogus")
        rc = td_tag.run_tag_command(args)
        assert rc == 2


# ----------------------------------------------------------------------
# Propagation through apply_change (review queue → adapter dispatch)
# ----------------------------------------------------------------------

class TestApplyChangeDispatch:
    def test_apply_change_tag_add(self, tag_db: Path) -> None:
        event = PropagationEvent(
            event_id="evt-001",
            ueid="ikigai:task:deadbeef:1234",
            action=TaskAction.TAG_ADD,
            fields={"tags": ["backend", "urgent"]},
            approved_at=datetime.now(timezone.utc),
            source_fork="test",
        )
        TaskdogAdapter().apply_change(event)
        assert get_tags("ikigai:task:deadbeef:1234") == ["backend", "urgent"]

    def test_apply_change_tag_remove(self, tag_db_with_tags: Path) -> None:
        event = PropagationEvent(
            event_id="evt-002",
            ueid="ikigai:task:deadbeef:1234",
            action=TaskAction.TAG_REMOVE,
            fields={"tags": ["backend"]},
            approved_at=datetime.now(timezone.utc),
            source_fork="test",
        )
        TaskdogAdapter().apply_change(event)
        assert get_tags("ikigai:task:deadbeef:1234") == ["urgent"]

    def test_apply_change_tag_clear(self, tag_db_with_tags: Path) -> None:
        event = PropagationEvent(
            event_id="evt-003",
            ueid="ikigai:task:deadbeef:1234",
            action=TaskAction.TAG_CLEAR,
            fields={},
            approved_at=datetime.now(timezone.utc),
            source_fork="test",
        )
        TaskdogAdapter().apply_change(event)
        assert get_tags("ikigai:task:deadbeef:1234") == []

    def test_apply_change_tag_add_rejects_non_list(self, tag_db: Path) -> None:
        event = PropagationEvent(
            event_id="evt-004",
            ueid="ikigai:task:deadbeef:1234",
            action=TaskAction.TAG_ADD,
            fields={"tags": "not-a-list"},  # bad type
            approved_at=datetime.now(timezone.utc),
            source_fork="test",
        )
        with pytest.raises(ValueError, match="must be list"):
            TaskdogAdapter().apply_change(event)


# ----------------------------------------------------------------------
# TaskAction enum (contract-level)
# ----------------------------------------------------------------------

class TestTaskActionEnum:
    def test_tag_actions_present(self) -> None:
        assert TaskAction.TAG_ADD.value == "tag_add"
        assert TaskAction.TAG_REMOVE.value == "tag_remove"
        assert TaskAction.TAG_CLEAR.value == "tag_clear"

    def test_existing_actions_intact(self) -> None:
        """Backward-compat: the original 4 actions must still be present."""
        assert TaskAction.CREATE.value == "create"
        assert TaskAction.UPDATE.value == "update"
        assert TaskAction.DELETE.value == "delete"
        assert TaskAction.DONE.value == "done"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def argparse_namespace(**kwargs: Any) -> Any:
    """Build an argparse.Namespace-compatible object without argparse."""
    from argparse import Namespace
    return Namespace(**kwargs)


def _read_audit_log(db_path: Path) -> list[dict]:
    """Read the audit_log JSON column for the seed task."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT audit_log FROM tasks WHERE ueid=?",
            ("ikigai:task:deadbeef:1234",),
        ).fetchone()
        if row is None or row[0] is None:
            return []
        return json.loads(row[0])
    finally:
        conn.close()
