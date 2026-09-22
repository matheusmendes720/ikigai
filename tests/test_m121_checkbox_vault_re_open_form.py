"""M121 tests — CHECKBOX_VAULT_RE open form `[ ] [vault:...]`.

Verifies the regex alternation handles three forms:
  1. closed: `- [x] [vault:rel#line] text`
  2. bare:   `- [vault:rel#line] text`
  3. open:   `- [ ] [vault:rel#line] text` (M121 addition)

And the consumer code (audit_drift) extracts rel_path / line_no / cb_text
correctly for all three alternates via the group(1)/group(4)/group(7) pattern.
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
    CHECKBOX_VAULT_RE,
    DRIFT_PRIORITY_MISMATCH,
    DRIFT_UNMARKED_DONE,
    DRIFT_UNMARKED_OPEN,
    audit_drift,
)


# === Regex behavior ===

def test_regex_matches_open_form_with_priority() -> None:
    """`- [ ] [vault:plan.md#8] Foo | priority=7` matches."""
    line = "- [ ] [vault:plan.md#8] Foo | priority=7"
    m = CHECKBOX_VAULT_RE.match(line)
    assert m is not None
    # Alt 3 (open form) captures groups 7, 8, 9.
    assert m.group(7) == "plan.md"
    assert m.group(8) == "8"
    assert m.group(9) == "Foo | priority=7"


def test_regex_matches_open_form_simple() -> None:
    line = "- [ ] [vault:vault/00-norte/x.md#88] Plank"
    m = CHECKBOX_VAULT_RE.match(line)
    assert m is not None
    assert m.group(7) == "vault/00-norte/x.md"
    assert m.group(8) == "88"
    assert m.group(9) == "Plank"


def test_regex_does_not_match_plain_text() -> None:
    assert CHECKBOX_VAULT_RE.match("- [ ] plain text") is None


def test_regex_does_not_match_indented() -> None:
    """Leading whitespace is not in the convention; intentionally rejected."""
    assert CHECKBOX_VAULT_RE.match("  - [ ] [vault:plan.md#8] Foo") is None


def test_regex_still_matches_bare_form() -> None:
    """Regression guard: bare `[vault:...]` form (no checkbox wrapper) still works."""
    m = CHECKBOX_VAULT_RE.match("- [vault:plan.md#8] Foo")
    assert m is not None
    assert m.group(4) == "plan.md"  # alt 2 captures groups 4, 5, 6


def test_regex_still_matches_closed_form() -> None:
    """Regression guard: closed `[x] [vault:...]` form still works."""
    m = CHECKBOX_VAULT_RE.match("- [x] [vault:plan.md#8] Foo")
    assert m is not None
    assert m.group(1) == "plan.md"  # alt 1 captures groups 1, 2, 3


# === audit_drift() with open form ===

@pytest.fixture
def tmp_vault_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Vault with an OPEN-form linked checkbox `[ ] [vault:...]`."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    vault = repo_root / "vault"
    vault.mkdir()
    plan = vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [ ] [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vp, "VAULT_DIR", repo_root)
    monkeypatch.setattr(vp, "REPO_ROOT", repo_root)
    return vault


def _task(task_id: int, name: str, status: str = "PENDING", priority: int | None = 5) -> dict[str, Any]:
    return {"id": task_id, "name": name, "status": status, "priority": priority}


def test_audit_drift_open_form_priority_mismatch(tmp_vault_open: Path) -> None:
    """Open form `[ ] [vault:...]` is now matched, priority_mismatch fires."""
    plan = tmp_vault_open / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", priority=5)]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    # Both should match — open form is now captured.
    assert DRIFT_PRIORITY_MISMATCH in r["summary"]
    # And phantom_task should NOT fire (because the link matched).
    assert "phantom_task" not in r["summary"]


def test_audit_drift_open_form_unmarked_done(tmp_vault_open: Path) -> None:
    """Open form `[ ] [vault:...]` + COMPLETED task → unmarked_done."""
    plan = tmp_vault_open / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", status="COMPLETED", priority=7)]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_UNMARKED_DONE in r["summary"]


def test_audit_drift_open_form_unmarked_open(tmp_vault_open: Path) -> None:
    """Closed form `[x] [vault:...]` + PENDING task → unmarked_open."""
    plan = tmp_vault_open / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [x] [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", status="PENDING", priority=7)]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_UNMARKED_OPEN in r["summary"]


def test_audit_drift_bare_form_still_works(tmp_vault_open: Path) -> None:
    """Regression guard: bare `[vault:...]` form (used by M114f tests)."""
    plan = tmp_vault_open / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [vault:vault/plan.md#8] Foo | priority=7\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | priority=7", priority=5)]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_PRIORITY_MISMATCH in r["summary"]
