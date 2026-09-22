"""M130 tests — due_date drift kind (7th drift kind).

Captures `| due=YYYY-MM-DD` from vault checkbox text and compares to
taskdog's `deadline` field on the date portion only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import vault_propagation as vp  # noqa: E402
from tools.backtest.vault_propagation import (  # noqa: E402
    DRIFT_DUE_DATE_MISMATCH,
    DUE_TAG_RE,
    audit_drift,
)


# === DUE_TAG_RE ===

def test_due_tag_re_basic() -> None:
    """Basic match: 'Task | due=2026-09-30' captures '2026-09-30'."""
    m = DUE_TAG_RE.search("Task | due=2026-09-30")
    assert m is not None
    assert m.group(1) == "2026-09-30"


def test_due_tag_re_combined() -> None:
    """Combined with other tags: due + priority."""
    m = DUE_TAG_RE.search("Task | due=2026-09-30 | priority=5")
    assert m is not None
    assert m.group(1) == "2026-09-30"


def test_due_tag_re_combined_with_tags() -> None:
    """Combined with priority + tags."""
    m = DUE_TAG_RE.search("Task | priority=5 | tags=foo,bar | due=2026-12-31")
    assert m is not None
    assert m.group(1) == "2026-12-31"


def test_due_tag_re_no_match() -> None:
    """No due tag → no match."""
    assert DUE_TAG_RE.search("Task without due date") is None
    assert DUE_TAG_RE.search("Task | priority=5") is None


def test_due_tag_re_extra_whitespace() -> None:
    """Extra whitespace tolerated: `|  due=...`."""
    m = DUE_TAG_RE.search("Task |  due=2026-09-30")
    assert m is not None
    assert m.group(1) == "2026-09-30"


# === audit_drift: due_date_mismatch ===

def _run_audit_drift_with_data(
    tmp_path: Path,
    vault_checkbox_text: str,
    taskdog_task: dict[str, Any],
) -> dict[str, Any]:
    """Helper: run audit_drift with a single synthetic plan + task."""
    plan = tmp_path / "plan.md"
    # Format: checkbox with link + custom text.
    plan.write_text(
        f"- [ ] [vault:plan.md#1] {vault_checkbox_text}\n",
        encoding="utf-8",
    )
    # Make sure taskdog task has the matching link token in name.
    if "name" not in taskdog_task:
        taskdog_task = {**taskdog_task, "name": "Task [vault:plan.md#1]"}
    return audit_drift(vault_plans=[plan], taskdog_tasks=[taskdog_task])


def test_audit_drift_due_date_match(tmp_path: Path) -> None:
    """vault due=2026-09-30 + taskdog deadline=2026-09-30T... → no mismatch."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="My task | due=2026-09-30",
        taskdog_task={"status": "PENDING", "deadline": "2026-09-30T18:00:00"},
    )
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    assert due_drifts == []


def test_audit_drift_due_date_mismatch(tmp_path: Path) -> None:
    """vault due=2026-09-30 + taskdog deadline=2026-10-01 → mismatch."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="My task | due=2026-09-30",
        taskdog_task={"status": "PENDING", "deadline": "2026-10-01T18:00:00"},
    )
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    assert len(due_drifts) == 1
    d = due_drifts[0]
    assert d["vault_due_date"] == "2026-09-30"
    assert d["taskdog_due_date"] == "2026-10-01"


def test_audit_drift_due_date_match_no_timezone(tmp_path: Path) -> None:
    """taskdog deadline with no time component (just date) still matches."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="My task | due=2026-09-30",
        taskdog_task={"status": "PENDING", "deadline": "2026-09-30"},
    )
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    assert due_drifts == []


def test_audit_drift_due_no_taskdog_deadline_skipped(tmp_path: Path) -> None:
    """No taskdog deadline → no mismatch (don't know what it should be)."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="My task | due=2026-09-30",
        taskdog_task={"status": "PENDING", "deadline": None},
    )
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    assert due_drifts == []


def test_audit_drift_due_no_vault_due_skipped(tmp_path: Path) -> None:
    """No vault due tag → no drift detected (don't fire mismatch)."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="My task",
        taskdog_task={"status": "PENDING", "deadline": "2026-09-30T18:00:00"},
    )
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    assert due_drifts == []


def test_audit_drift_due_combined_with_priority_and_tags(tmp_path: Path) -> None:
    """All 3 annotations on one checkbox: due + priority + tags."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="Combined | priority=5 | tags=foo,bar | due=2026-09-30",
        taskdog_task={
            "status": "PENDING",
            "priority": 5,
            "tags": ["foo", "bar"],
            "deadline": "2026-09-30T18:00:00",
        },
    )
    # All 3 should match → 0 drifts.
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    prio_drifts = [d for d in result["drifts"] if d["drift_kind"] == "priority_mismatch"]
    tag_drifts = [d for d in result["drifts"] if d["drift_kind"] == "tag_mismatch"]
    assert due_drifts == []
    assert prio_drifts == []
    assert tag_drifts == []


def test_audit_drift_due_short_deadline_safe(tmp_path: Path) -> None:
    """taskdog deadline shorter than 10 chars → skip (no date portion)."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="My task | due=2026-09-30",
        taskdog_task={"status": "PENDING", "deadline": "soon"},
    )
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    assert due_drifts == []


def test_audit_drift_due_drift_dict_has_required_fields(tmp_path: Path) -> None:
    """Mismatched due drift dict carries the right fields."""
    result = _run_audit_drift_with_data(
        tmp_path,
        vault_checkbox_text="Task | due=2026-09-30",
        taskdog_task={"status": "PENDING", "deadline": "2026-12-31T00:00:00"},
    )
    due_drifts = [d for d in result["drifts"] if d["drift_kind"] == DRIFT_DUE_DATE_MISMATCH]
    assert len(due_drifts) == 1
    d = due_drifts[0]
    required = {"drift_kind", "plan_file", "plan_line", "plan_text",
                "taskdog_id", "taskdog_status", "taskdog_name",
                "vault_due_date", "taskdog_due_date"}
    assert required.issubset(d.keys()), f"missing fields: {required - set(d.keys())}"


# === Constant export ===

def test_due_date_mismatch_constant_exists() -> None:
    """The DRIFT_DUE_DATE_MISMATCH constant is exported."""
    assert hasattr(vp, "DRIFT_DUE_DATE_MISMATCH")
    assert vp.DRIFT_DUE_DATE_MISMATCH == "due_date_mismatch"


def test_due_tag_re_constant_exists() -> None:
    """The DUE_TAG_RE constant is exported."""
    assert hasattr(vp, "DUE_TAG_RE")
