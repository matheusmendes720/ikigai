"""Full-coverage tests for taskdog_tools.py MCP surface (M163/M164).

Drift net: every new tool callable; write tools produce review-queue entries;
read tools return correct data; invalid inputs return error JSON.

M163/M164 ships 13 new tools on top of the original 8 (read/create/status/
priority/due/cancel). The drift net `test_taskdog_tools_read_only_contract`
guards the write surface by requiring every write tool to route through
``_enqueue_task_change`` (no direct SQLite writes from MCP).

These tests verify that contract directly.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from src.ikigai.src.mcp_server import taskdog_tools

# Canonical 4-part UEIDs (per ADR-014). One for the "primary" ueid, one for
# the "other_ueid" used by dep_* tools, and one for the dep target.
UEID_A = "ikigai:task:abc12345:def67890"
UEID_B = "ikigai:task:bbb22222:ccc33333"
UEID_C = "ikigai:task:ddd44444:eee55555"


# ---------------------------------------------------------------------------
# Tag tools
# ---------------------------------------------------------------------------


class TestTagTools:
    """taskdog_tag_add / taskdog_tag_remove / taskdog_tag_list / taskdog_tag_clear."""

    def test_tag_add_enqueues(self) -> None:
        """taskdog_tag_add calls _build_task_change with TAG_ADD + tags list."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-1"
            result = json.loads(taskdog_tools.taskdog_tag_add(UEID_A, ["alpha", "beta"]))
        assert result["event_id"] == "evt-1"
        assert result["action"] == "tag_add"
        assert result["tags"] == ["alpha", "beta"]
        # Verify the call shape: action, ueid, fields
        call_args = mock_build.call_args
        # _build_task_change(action, ueid, fields, ...)
        assert call_args.args[0].value == "tag_add"
        assert call_args.args[1] == UEID_A
        assert call_args.args[2] == {"tags": ["alpha", "beta"]}

    def test_tag_add_rejects_invalid_ueid(self) -> None:
        """Bad UEID → error JSON, no enqueue."""
        result = json.loads(taskdog_tools.taskdog_tag_add("not-a-ueid", ["alpha"]))
        assert "error" in result
        assert "Invalid UEID" in result["error"]

    def test_tag_add_rejects_bad_tag_chars(self) -> None:
        """Tag with disallowed chars → error JSON."""
        result = json.loads(taskdog_tools.taskdog_tag_add(UEID_A, ["bad tag!"]))
        assert "error" in result
        assert "invalid tag" in result["error"]

    def test_tag_add_rejects_empty_list(self) -> None:
        """Empty tag list → error JSON."""
        result = json.loads(taskdog_tools.taskdog_tag_add(UEID_A, []))
        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_tag_add_rejects_non_string_tag(self) -> None:
        """Non-string tag → error JSON."""
        result = json.loads(taskdog_tools.taskdog_tag_add(UEID_A, [123]))  # type: ignore[list-item]
        assert "error" in result
        assert "string" in result["error"]

    def test_tag_remove_enqueues(self) -> None:
        """taskdog_tag_remove calls _build_task_change with TAG_REMOVE."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-2"
            result = json.loads(taskdog_tools.taskdog_tag_remove(UEID_A, ["alpha"]))
        assert result["event_id"] == "evt-2"
        assert result["action"] == "tag_remove"
        call_args = mock_build.call_args
        assert call_args.args[0].value == "tag_remove"
        assert call_args.args[2] == {"tags": ["alpha"]}

    def test_tag_list_returns_tags_from_slice(self) -> None:
        """taskdog_tag_list reads tags from the adapter slice (read-only)."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = {"ueid": UEID_A, "tags": ["alpha", "beta"]}
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_tag_list(UEID_A))
        assert result["count"] == 2
        assert result["tags"] == ["alpha", "beta"]

    def test_tag_list_missing_ueid_returns_error(self) -> None:
        """taskdog_tag_list returns error if slice is None."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = None
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_tag_list(UEID_A))
        assert "error" in result
        assert "not found" in result["error"]

    def test_tag_list_empty_returns_empty(self) -> None:
        """taskdog_tag_list returns count=0 when slice has no tags."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = {"ueid": UEID_A, "tags": []}
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_tag_list(UEID_A))
        assert result["count"] == 0
        assert result["tags"] == []

    def test_tag_clear_enqueues(self) -> None:
        """taskdog_tag_clear calls _build_task_change with TAG_CLEAR."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-3"
            result = json.loads(taskdog_tools.taskdog_tag_clear(UEID_A))
        assert result["event_id"] == "evt-3"
        assert result["action"] == "tag_clear"
        call_args = mock_build.call_args
        assert call_args.args[0].value == "tag_clear"


# ---------------------------------------------------------------------------
# Dep tools
# ---------------------------------------------------------------------------


class TestDepTools:
    """taskdog_dep_add / taskdog_dep_remove / taskdog_dep_list / taskdog_dep_blocked."""

    def test_dep_add_enqueues(self) -> None:
        """taskdog_dep_add calls _build_task_change with UPDATE + deps_add."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-dep-1"
            result = json.loads(taskdog_tools.taskdog_dep_add(UEID_A, UEID_B))
        assert result["event_id"] == "evt-dep-1"
        call_args = mock_build.call_args
        assert call_args.args[0].value == "update"
        assert call_args.args[2] == {"deps_add": [UEID_B]}

    def test_dep_add_rejects_invalid_ueid(self) -> None:
        """Bad primary ueid → error JSON."""
        result = json.loads(taskdog_tools.taskdog_dep_add("bad", UEID_B))
        assert "error" in result

    def test_dep_add_rejects_invalid_other_ueid(self) -> None:
        """Bad other_ueid → error JSON."""
        result = json.loads(taskdog_tools.taskdog_dep_add(UEID_A, "bad"))
        assert "error" in result
        assert "other_ueid" in result["error"]

    def test_dep_add_rejects_self_dep(self) -> None:
        """ueid == other_ueid → error JSON (no self-deps)."""
        result = json.loads(taskdog_tools.taskdog_dep_add(UEID_A, UEID_A))
        assert "error" in result
        assert "self-deps" in result["error"]

    def test_dep_remove_enqueues(self) -> None:
        """taskdog_dep_remove calls _build_task_change with UPDATE + deps_remove."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-dep-2"
            result = json.loads(taskdog_tools.taskdog_dep_remove(UEID_A, UEID_B))
        assert result["event_id"] == "evt-dep-2"
        call_args = mock_build.call_args
        assert call_args.args[2] == {"deps_remove": [UEID_B]}

    def test_dep_list_returns_deps_from_slice(self) -> None:
        """taskdog_dep_list reads deps from the adapter slice."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = {"ueid": UEID_A, "deps": [UEID_B, UEID_C]}
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_dep_list(UEID_A))
        assert result["count"] == 2
        assert result["deps"] == [UEID_B, UEID_C]

    def test_dep_list_missing_ueid_returns_error(self) -> None:
        """taskdog_dep_list returns error if slice is None."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = None
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_dep_list(UEID_A))
        assert "error" in result

    def test_dep_blocked_finds_unmet_deps(self) -> None:
        """taskdog_dep_blocked returns tasks with at least one unmet dep."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.list_all.return_value = [
                # A is blocked: depends on B which is not done
                {"ueid": UEID_A, "name": "A", "status": "planned", "deps": [UEID_B]},
                # B is the dep (not done)
                {"ueid": UEID_B, "name": "B", "status": "planned", "deps": []},
                # C is unblocked: depends on D which is done
                {"ueid": UEID_C, "name": "C", "status": "planned", "deps": [UEID_A]},
                # D doesn't exist in store → C's dep is also "unmet"
            ]
            mock_adapter.return_value = adapter
            # Make A done so C's dep is met
            adapter.list_all.return_value = [
                {"ueid": UEID_A, "name": "A", "status": "done", "deps": [UEID_B]},
                {"ueid": UEID_B, "name": "B", "status": "planned", "deps": []},
                {"ueid": UEID_C, "name": "C", "status": "planned", "deps": [UEID_A]},
            ]
            result = json.loads(taskdog_tools.taskdog_dep_blocked())
        assert result["count"] == 1
        assert result["blocked"][0]["ueid"] == UEID_A
        assert UEID_B in result["blocked"][0]["unmet_deps"]

    def test_dep_blocked_empty_when_all_satisfied(self) -> None:
        """taskdog_dep_blocked returns count=0 when every dep is done."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.list_all.return_value = [
                {"ueid": UEID_A, "name": "A", "status": "done", "deps": []},
                {"ueid": UEID_B, "name": "B", "status": "planned", "deps": [UEID_A]},
            ]
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_dep_blocked())
        assert result["count"] == 0
        assert result["blocked"] == []


# ---------------------------------------------------------------------------
# Note tools
# ---------------------------------------------------------------------------


class TestNoteTools:
    """taskdog_note_add / taskdog_note_show."""

    def test_note_add_enqueues(self) -> None:
        """taskdog_note_add calls _build_task_change with UPDATE + note text."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-note-1"
            result = json.loads(taskdog_tools.taskdog_note_add(UEID_A, "hello world"))
        assert result["event_id"] == "evt-note-1"
        assert result["length"] == len("hello world")
        call_args = mock_build.call_args
        assert call_args.args[0].value == "update"
        assert call_args.args[2] == {"note": "hello world"}

    def test_note_add_rejects_empty(self) -> None:
        """Empty note → error JSON."""
        result = json.loads(taskdog_tools.taskdog_note_add(UEID_A, ""))
        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_note_add_rejects_too_long(self) -> None:
        """Note >4000 chars → error JSON."""
        long_text = "x" * 4001
        result = json.loads(taskdog_tools.taskdog_note_add(UEID_A, long_text))
        assert "error" in result
        assert "4000" in result["error"]

    def test_note_add_rejects_invalid_ueid(self) -> None:
        """Bad UEID → error JSON."""
        result = json.loads(taskdog_tools.taskdog_note_add("bad", "x"))
        assert "error" in result

    def test_note_show_filters_audit_log(self) -> None:
        """taskdog_note_show returns only entries with action='note_add'."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = {
                "ueid": UEID_A,
                "audit_log": [
                    {"action": "tag_add", "timestamp": "2026-01-01T00:00:00Z"},
                    {
                        "action": "note_add",
                        "timestamp": "2026-01-02T00:00:00Z",
                        "fields_diff": {"text": "first note"},
                    },
                    {
                        "action": "note_add",
                        "timestamp": "2026-01-03T00:00:00Z",
                        "fields_diff": {"text": "second note"},
                    },
                ],
            }
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_note_show(UEID_A))
        assert result["count"] == 2
        assert all(n["action"] == "note_add" for n in result["notes"])

    def test_note_show_missing_ueid_returns_error(self) -> None:
        """taskdog_note_show returns error if slice is None."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = None
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_note_show(UEID_A))
        assert "error" in result


# ---------------------------------------------------------------------------
# Status wrappers
# ---------------------------------------------------------------------------


class TestStatusWrappers:
    """taskdog_pause / taskdog_reopen (taskdog_cancel already exists)."""

    def test_pause_enqueues(self) -> None:
        """taskdog_pause calls _build_task_change with UPDATE + status='paused'."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-pause"
            result = json.loads(taskdog_tools.taskdog_pause(UEID_A))
        assert result["event_id"] == "evt-pause"
        assert result["value"] == "paused"
        call_args = mock_build.call_args
        assert call_args.args[2] == {"status": "paused"}

    def test_reopen_enqueues(self) -> None:
        """taskdog_reopen calls _build_task_change with UPDATE + status='planned'."""
        with patch.object(taskdog_tools, "_build_task_change") as mock_build:
            mock_build.return_value = "evt-reopen"
            result = json.loads(taskdog_tools.taskdog_reopen(UEID_A))
        assert result["event_id"] == "evt-reopen"
        assert result["value"] == "planned"
        call_args = mock_build.call_args
        assert call_args.args[2] == {"status": "planned"}

    def test_pause_rejects_invalid_ueid(self) -> None:
        """Bad UEID on pause → error JSON."""
        result = json.loads(taskdog_tools.taskdog_pause("bad"))
        assert "error" in result

    def test_reopen_rejects_invalid_ueid(self) -> None:
        """Bad UEID on reopen → error JSON."""
        result = json.loads(taskdog_tools.taskdog_reopen("bad"))
        assert "error" in result


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class TestAudit:
    """taskdog_audit."""

    def test_audit_returns_full_log(self) -> None:
        """taskdog_audit returns the full audit_log array."""
        audit_data = [
            {"action": "tag_add", "timestamp": "2026-01-01T00:00:00Z"},
            {
                "action": "note_add",
                "timestamp": "2026-01-02T00:00:00Z",
                "fields_diff": {"text": "x"},
            },
        ]
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = {"ueid": UEID_A, "audit_log": audit_data}
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_audit(UEID_A))
        assert result["count"] == 2
        assert result["audit_log"] == audit_data

    def test_audit_missing_ueid_returns_error(self) -> None:
        """taskdog_audit returns error if slice is None."""
        with patch.object(taskdog_tools, "TaskdogAdapter") as mock_adapter:
            adapter = MagicMock()
            adapter.read.return_value = None
            mock_adapter.return_value = adapter
            result = json.loads(taskdog_tools.taskdog_audit(UEID_A))
        assert "error" in result

    def test_audit_invalid_ueid_returns_error(self) -> None:
        """Bad UEID on audit → error JSON."""
        result = json.loads(taskdog_tools.taskdog_audit("bad"))
        assert "error" in result


# ---------------------------------------------------------------------------
# Drift net guard — every write tool must route through _enqueue_task_change.
# If a future contributor adds a write tool that bypasses the queue, this
# guard catches it (CI fails).
# ---------------------------------------------------------------------------

_WRITE_TOOL_NAMES: tuple[str, ...] = (
    "taskdog_create",
    "taskdog_set_status",
    "taskdog_set_priority",
    "taskdog_set_due",
    "taskdog_cancel",
    "taskdog_tag_add",
    "taskdog_tag_remove",
    "taskdog_tag_clear",
    "taskdog_dep_add",
    "taskdog_dep_remove",
    "taskdog_note_add",
    "taskdog_pause",
    "taskdog_reopen",
)


@pytest.mark.parametrize("tool_name", _WRITE_TOOL_NAMES)
def test_write_tool_uses_enqueue(tool_name: str) -> None:
    """Every write tool must call _build_task_change (which routes through
    the review queue). Direct SQLite writes from MCP are forbidden per
    Path 3 contract."""
    fn = getattr(taskdog_tools, tool_name)
    with patch.object(taskdog_tools, "_build_task_change", return_value="evt") as mock_build:
        # Provide minimum-valid args for each tool
        if tool_name in ("taskdog_tag_add", "taskdog_tag_remove"):
            fn(UEID_A, ["a"])
        elif tool_name in ("taskdog_dep_add", "taskdog_dep_remove"):
            fn(UEID_A, UEID_B)
        elif tool_name == "taskdog_note_add":
            fn(UEID_A, "text")
        elif tool_name == "taskdog_create":
            fn(UEID_A, "title")
        elif tool_name == "taskdog_set_priority":
            fn(UEID_A, "high")
        elif tool_name == "taskdog_set_status":
            fn(UEID_A, "planned")
        elif tool_name == "taskdog_set_due":
            fn(UEID_A, "2026-12-31")
        else:
            fn(UEID_A)
    assert mock_build.called, (
        f"{tool_name} did not call _build_task_change — would bypass review queue"
    )


# ---------------------------------------------------------------------------
# FastMCP registration — every tool is exposed on the `taskdog` mcp instance.
# ---------------------------------------------------------------------------


def test_all_new_tools_registered_on_mcp() -> None:
    """All 13 new M163/M164 tools are registered on the taskdog FastMCP."""
    registered = {t.name for t in taskdog_tools.mcp._tool_manager._tools.values()}
    expected_new = {
        "taskdog_tag_add",
        "taskdog_tag_remove",
        "taskdog_tag_list",
        "taskdog_tag_clear",
        "taskdog_dep_add",
        "taskdog_dep_remove",
        "taskdog_dep_list",
        "taskdog_dep_blocked",
        "taskdog_note_add",
        "taskdog_note_show",
        "taskdog_pause",
        "taskdog_reopen",
        "taskdog_audit",
    }
    missing = expected_new - registered
    assert not missing, f"missing from FastMCP registration: {sorted(missing)}"
