"""M125 tests — indented checkbox support in CHECKBOX_VAULT_RE.

Verifies the regex accepts up to 4 spaces / tabs of leading whitespace
(typical nested-checkbox indentation). Beyond that, it's a code block or
deeper list — not a checkbox.

Rejection cases:
- 6+ spaces → too deep
- plain text (even indented) → no link
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
    audit_drift,
)


# === Regex accepts reasonable indent ===

def test_zero_indent_accepted() -> None:
    m = CHECKBOX_VAULT_RE.match("- [ ] [vault:plan.md#8] Foo")
    assert m is not None


def test_two_space_indent_accepted() -> None:
    m = CHECKBOX_VAULT_RE.match("  - [ ] [vault:plan.md#8] Foo")
    assert m is not None


def test_four_space_indent_accepted() -> None:
    m = CHECKBOX_VAULT_RE.match("    - [ ] [vault:plan.md#8] Foo")
    assert m is not None


def test_tab_indent_accepted() -> None:
    m = CHECKBOX_VAULT_RE.match("\t- [ ] [vault:plan.md#8] Foo")
    assert m is not None


def test_closed_form_indented_accepted() -> None:
    m = CHECKBOX_VAULT_RE.match("  - [x] [vault:plan.md#8] Foo")
    assert m is not None


def test_bare_form_indented_accepted() -> None:
    m = CHECKBOX_VAULT_RE.match("    - [vault:plan.md#8] Foo")
    assert m is not None


# === Regex rejects too-deep indent ===

def test_six_space_indent_rejected() -> None:
    """Beyond 4 spaces: likely code block or deeper list, not a checkbox."""
    m = CHECKBOX_VAULT_RE.match("      - [ ] [vault:plan.md#8] Foo")
    assert m is None


def test_eight_space_indent_rejected() -> None:
    m = CHECKBOX_VAULT_RE.match("        - [ ] [vault:plan.md#8] Foo")
    assert m is None


# === Regex rejects plain text (with or without indent) ===

def test_plain_text_no_indent_rejected() -> None:
    assert CHECKBOX_VAULT_RE.match("- [ ] plain text") is None


def test_plain_text_indented_rejected() -> None:
    """Indented plain text without [vault:...] link → still rejected."""
    assert CHECKBOX_VAULT_RE.match("  - [ ] plain text (no link)") is None


# === audit_drift with indented checkboxes ===

@pytest.fixture
def tmp_vault_indented(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    vault = repo_root / "vault"
    vault.mkdir()
    plan = vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n"
        "  - [ ] [vault:vault/plan.md#6] Nested | priority=7\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vp, "VAULT_DIR", repo_root)
    monkeypatch.setattr(vp, "REPO_ROOT", repo_root)
    return vault


def _task(task_id: int, name: str, priority: int = 5) -> dict[str, Any]:
    return {"id": task_id, "name": name, "status": "PENDING", "priority": priority}


def test_audit_drift_matches_indented_checkbox(tmp_vault_indented: Path) -> None:
    """Indented linked checkbox is matched → priority_mismatch fires."""
    plan = tmp_vault_indented / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#6] Nested | priority=7", priority=5)]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_PRIORITY_MISMATCH in r["summary"]
