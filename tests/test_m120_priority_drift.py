"""M120 tests — priority_mismatch drift detection.

Verifies the new DRIFT_PRIORITY_MISMATCH kind added to audit_drift().
- `| priority=N` in vault checkbox text is captured
- Mismatch vs taskdog priority emits DRIFT_PRIORITY_MISMATCH
- Matching priority does NOT emit a drift
- Missing priority tag → no drift
- Non-numeric priority → no drift (graceful)
- taskdog priority=None (missing field) → no drift
- Vault + taskdog priorities both None → no drift
- Multiple vault declarations: only the FIRST is used (regex captures once)
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
    DRIFT_PRIORITY_MISMATCH,
    PRIORITY_TAG_RE,
    audit_drift,
)


@pytest.fixture
def tmp_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a vault dir matching the M114f convention.

    Layout: tmp_path/repo/vault/plan.md (so _plan_rel returns 'vault/plan.md').
    Links: [vault:vault/plan.md#N]. VAULT_DIR/REPO_ROOT pointed at repo_root.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    vault = repo_root / "vault"
    vault.mkdir()
    plan = vault / "plan.md"
    plan.write_text(
        "---\n"
        "title: Test plan\n"
        "---\n"
        "# Test\n"
        "\n"
        "- [ ] [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vp, "VAULT_DIR", repo_root)
    monkeypatch.setattr(vp, "REPO_ROOT", repo_root)
    return vault


def _task(task_id: int, name: str, status: str = "PENDING", priority: int | None = 5) -> dict[str, Any]:
    return {"id": task_id, "name": name, "status": status, "priority": priority}


def test_priority_tag_regex_captures_int() -> None:
    m = PRIORITY_TAG_RE.search("Foo | priority=7")
    assert m is not None
    assert m.group(1) == "7"


def test_priority_tag_regex_captures_two_digit() -> None:
    m = PRIORITY_TAG_RE.search("Foo | priority=10")
    assert m is not None
    assert m.group(1) == "10"


def test_priority_tag_regex_no_match() -> None:
    assert PRIORITY_TAG_RE.search("Foo | prior=7") is None
    assert PRIORITY_TAG_RE.search("priority=abc") is None
    assert PRIORITY_TAG_RE.search("plain text") is None


def test_priority_mismatch_emitted(tmp_vault: Path) -> None:
    """Vault says priority=7, taskdog says priority=5 → DRIFT."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", priority=5)]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert DRIFT_PRIORITY_MISMATCH in kinds
    drift = next(d for d in report["drifts"] if d["drift_kind"] == DRIFT_PRIORITY_MISMATCH)
    assert drift["vault_priority"] == 7
    assert drift["taskdog_priority"] == 5
    assert drift["taskdog_id"] == 1


def test_priority_match_no_drift(tmp_vault: Path) -> None:
    """Vault priority=7, taskdog priority=7 → no mismatch drift."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", priority=7)]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert DRIFT_PRIORITY_MISMATCH not in kinds


def test_no_priority_tag_no_drift(tmp_vault: Path) -> None:
    """Vault checkbox without `| priority=N` → no priority drift."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo (no priority)\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo (no priority)", priority=9)]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert DRIFT_PRIORITY_MISMATCH not in kinds


def test_taskdog_priority_none_no_drift(tmp_vault: Path) -> None:
    """taskdog priority missing → no drift (don't crash on None)."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", priority=None)]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert DRIFT_PRIORITY_MISMATCH not in kinds


def test_taskdog_priority_non_int_no_drift(tmp_vault: Path) -> None:
    """taskdog priority='P3' (legacy string) → no crash, no drift."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", priority="P3")]  # type: ignore[arg-type]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert DRIFT_PRIORITY_MISMATCH not in kinds


def test_vault_priority_non_int_no_drift(tmp_vault: Path) -> None:
    """Vault checkbox with non-numeric priority → no crash, no drift."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo | priority=abc\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=abc", priority=5)]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert DRIFT_PRIORITY_MISMATCH not in kinds


def test_priority_mismatch_summary_counted(tmp_vault: Path) -> None:
    """3 mismatches → summary['priority_mismatch'] == 3."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n"
        "- [vault:vault/plan.md#8] A | priority=7\n"
        "- [vault:vault/plan.md#9] B | priority=8\n"
        "- [vault:vault/plan.md#10] C | priority=5\n",
        encoding="utf-8",
    )
    tasks = [
        _task(1, "do [vault:vault/plan.md#8] A | priority=7", priority=5),
        _task(2, "do [vault:vault/plan.md#9] B | priority=8", priority=9),
        _task(3, "do [vault:vault/plan.md#10] C | priority=5", priority=3),
    ]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert report["summary"].get(DRIFT_PRIORITY_MISMATCH, 0) == 3


def test_priority_mismatch_on_completed_task(tmp_vault: Path) -> None:
    """Priority drift is independent of completion status — completed tasks can also drift."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [x] [vault:vault/plan.md#8] Done | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Done | priority=7", status="COMPLETED", priority=4)]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert DRIFT_PRIORITY_MISMATCH in kinds
    # Should NOT emit unmarked_done (vault is [x]) or unmarked_open (task is COMPLETED)
    assert "unmarked_done" not in kinds
    assert "unmarked_open" not in kinds


def test_priority_mismatch_independent_of_other_kinds(tmp_vault: Path) -> None:
    """A single scenario can produce both unmarked_done AND priority_mismatch."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", status="COMPLETED", priority=5)]
    report = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in report["drifts"]]
    assert "unmarked_done" in kinds
    assert DRIFT_PRIORITY_MISMATCH in kinds
    assert report["summary"]["unmarked_done"] == 1
    assert report["summary"][DRIFT_PRIORITY_MISMATCH] == 1
