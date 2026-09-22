"""M122 tests — tag_mismatch drift detection.

Verifies the 6th drift kind:
- `| tags=a,b,c` in vault checkbox text is captured
- Treated as unordered set (case-insensitive, whitespace-trimmed)
- Mismatch vs taskdog tags → DRIFT_TAG_MISMATCH
- Match → no drift
- Empty vault tags → no drift (don't compare to empty)
- taskdog tags missing / None → no drift
- taskdog tags as comma-separated string (legacy serialization) → still works
- Mixed order doesn't matter
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
    DRIFT_TAG_MISMATCH,
    TAGS_TAG_RE,
    audit_drift,
)


@pytest.fixture
def tmp_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    vault = repo_root / "vault"
    vault.mkdir()
    plan = vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [ ] [vault:vault/plan.md#8] Foo | tags=urgent,frontend\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vp, "VAULT_DIR", repo_root)
    monkeypatch.setattr(vp, "REPO_ROOT", repo_root)
    return vault


def _task(task_id: int, name: str, tags: list[str] | str | None = None) -> dict[str, Any]:
    return {
        "id": task_id,
        "name": name,
        "status": "PENDING",
        "priority": 5,
        "tags": tags if tags is not None else [],
    }


# === Regex ===

def test_tags_regex_captures_simple() -> None:
    m = TAGS_TAG_RE.search("Foo | tags=urgent,frontend")
    assert m is not None
    assert m.group(1) == "urgent,frontend"


def test_tags_regex_captures_with_spaces() -> None:
    m = TAGS_TAG_RE.search("Foo | tags=foo, bar, baz")
    assert m is not None
    assert m.group(1) == "foo, bar, baz"


def test_tags_regex_no_match_when_no_pipe() -> None:
    assert TAGS_TAG_RE.search("Foo tags=urgent") is None


# === Drift detection ===

def test_tag_mismatch_emitted(tmp_vault: Path) -> None:
    plan = tmp_vault / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | tags=urgent,frontend",
                   tags=["urgent", "backend"])]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in r["drifts"]]
    assert DRIFT_TAG_MISMATCH in kinds
    drift = next(d for d in r["drifts"] if d["drift_kind"] == DRIFT_TAG_MISMATCH)
    assert drift["vault_tags"] == ["frontend", "urgent"]
    assert drift["taskdog_tags"] == ["backend", "urgent"]


def test_tag_match_no_drift(tmp_vault: Path) -> None:
    plan = tmp_vault / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | tags=urgent,frontend",
                   tags=["urgent", "frontend"])]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_TAG_MISMATCH not in r["summary"]


def test_tag_match_unordered(tmp_vault: Path) -> None:
    """Order doesn't matter — vault tags=[A,B], taskdog tags=[B,A] → match."""
    plan = tmp_vault / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | tags=urgent,frontend",
                   tags=["frontend", "urgent"])]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_TAG_MISMATCH not in r["summary"]


def test_tag_match_case_insensitive(tmp_vault: Path) -> None:
    plan = tmp_vault / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | tags=URGENT,Frontend",
                   tags=["urgent", "frontend"])]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_TAG_MISMATCH not in r["summary"]


def test_tag_match_whitespace_tolerated(tmp_vault: Path) -> None:
    """`tags=foo, bar` is normalized to `{foo, bar}` regardless of inner whitespace."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [ ] [vault:vault/plan.md#8] Foo | tags=foo, bar\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | tags=foo, bar",
                   tags=["foo", "bar"])]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_TAG_MISMATCH not in r["summary"]


def test_no_tag_declaration_no_drift(tmp_vault: Path) -> None:
    """Vault checkbox without `| tags=...` → no tag drift regardless of taskdog tags."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [ ] [vault:vault/plan.md#8] Foo (no tags)\n",
        encoding="utf-8",
    )
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo (no tags)", tags=["urgent"])]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_TAG_MISMATCH not in r["summary"]


def test_taskdog_tags_none_no_drift(tmp_vault: Path) -> None:
    """taskdog tags missing/None → no crash, no drift."""
    plan = tmp_vault / "plan.md"
    t = {"id": 1, "name": "do [vault:vault/plan.md#8] Foo | tags=urgent,frontend",
         "status": "PENDING", "priority": 5}  # no tags field
    r = audit_drift(vault_plans=[plan], taskdog_tasks=[t])
    assert DRIFT_TAG_MISMATCH not in r["summary"]


def test_taskdog_tags_empty_list_no_drift(tmp_vault: Path) -> None:
    """taskdog tags=[] → if vault has tags, mismatch (vault has, taskdog doesn't)."""
    plan = tmp_vault / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | tags=urgent,frontend", tags=[])]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert DRIFT_TAG_MISMATCH in r["summary"]


def test_taskdog_tags_comma_separated_string(tmp_vault: Path) -> None:
    """Some servers serialize tags as a comma-separated string — still parsed correctly."""
    plan = tmp_vault / "plan.md"
    tasks = [_task(1, "do [vault:vault/plan.md#8] Foo | tags=urgent,frontend",
                   tags="urgent,backend")]  # string!
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    # Should still detect mismatch (frontend vs backend)
    assert DRIFT_TAG_MISMATCH in r["summary"]


def test_tag_mismatch_with_completed_task(tmp_vault: Path) -> None:
    """Tag drift is independent of completion status."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [x] [vault:vault/plan.md#8] Done | tags=urgent\n",
        encoding="utf-8",
    )
    tasks = [{"id": 1, "name": "do [vault:vault/plan.md#8] Done | tags=urgent",
              "status": "COMPLETED", "priority": 5, "tags": ["done"]}]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    kinds = [d["drift_kind"] for d in r["drifts"]]
    assert DRIFT_TAG_MISMATCH in kinds


def test_tag_mismatch_independent_of_priority_mismatch(tmp_vault: Path) -> None:
    """Single scenario can emit both priority_mismatch AND tag_mismatch."""
    plan = tmp_vault / "plan.md"
    plan.write_text(
        "---\ntitle: t\n---\n# T\n\n- [ ] [vault:vault/plan.md#8] Foo | priority=7 | tags=urgent,frontend\n",
        encoding="utf-8",
    )
    tasks = [{"id": 1, "name": "do [vault:vault/plan.md#8] Foo | priority=7 | tags=urgent,frontend",
              "status": "PENDING", "priority": 5, "tags": ["urgent", "backend"]}]
    r = audit_drift(vault_plans=[plan], taskdog_tasks=tasks)
    assert "priority_mismatch" in r["summary"]
    assert DRIFT_TAG_MISMATCH in r["summary"]
