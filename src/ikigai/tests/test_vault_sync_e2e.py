"""E2E test for vault-to-taskdog sync — Phase B6.4.

Uses an in-process mock MCP server (StdioAdapter fake) + tmp vault +
tmp state. Verifies run_sync() produces correct taskdog_add / taskdog_done
calls and updates the state file.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.ikigai.vault.sync import load_state, run_sync


# ─────────────────────────────────────────────────────────────────────────────
# Mock StdioAdapter (mirrors StubAdapter from test_review_queue_worker_e2e.py)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MockStdioAdapter:
    """Protocol-conformant mock for StdioAdapter."""

    name: str = "mock-taskdog"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def call_tool(self, name: str, args: dict) -> dict:
        self.calls.append({"tool": name, "args": args})
        ueid = args.get("ueid", "")
        if name == "taskdog_add":
            return {"id": f"td-{ueid[-4:]}"}
        if name == "taskdog_done":
            return {"ok": True}
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def e2e_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()

    # File 1: NEW task (not in state)
    (vault / "new-task.md").write_text(
        "---\n"
        "ueid: ikigai:task:new:001\n"
        "title: Brand new task\n"
        'tags: [task]\n'
        "status: planned\n"
        "---\n",
        encoding="utf-8",
    )

    # File 2: CHANGED task (status planned → in_progress)
    (vault / "changed-task.md").write_text(
        "---\n"
        "ueid: ikigai:task:changed:002\n"
        "title: Status changed task\n"
        'tags: [task]\n'
        "status: in_progress\n"
        "---\n",
        encoding="utf-8",
    )

    # File 3: DONE task (status done → done, unchanged in vault)
    (vault / "done-task.md").write_text(
        "---\n"
        "ueid: ikigai:task:done:003\n"
        "title: Task now done\n"
        'tags: [task]\n'
        "status: done\n"
        "---\n",
        encoding="utf-8",
    )

    return vault


@pytest.fixture
def e2e_state(tmp_path: Path) -> Path:
    """Pre-existing state with two tasks (one needs update, one unchanged)."""
    state_path = tmp_path / "sync-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_data = {
        "version": 1,
        "last_sync_at": "2026-08-29T08:00:00Z",
        "tasks": {
            # CHANGED: was planned, now in_progress
            "ikigai:task:changed:002": {
                "last_synced_at": "2026-08-29T08:00:00Z",
                "last_status": "planned",
                "taskdog_id": "td-002",
                "vault_path": "changed-task.md",
            },
            # UNCHANGED: was done, still done
            "ikigai:task:done:003": {
                "last_synced_at": "2026-08-29T08:00:00Z",
                "last_status": "done",
                "taskdog_id": "td-003",
                "vault_path": "done-task.md",
            },
        },
    }
    state_path.write_text(json.dumps(state_data), encoding="utf-8")
    return state_path


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_vault_sync_e2e_calls_taskdog_with_correct_actions(
    e2e_vault: Path, e2e_state: Path
) -> None:
    """run_sync() calls taskdog_add for NEW and CHANGED tasks.

    Fixture analysis:
    - new-task.md (status: planned) NOT in state → NEW → added
    - changed-task.md (status: in_progress) in state as planned → CHANGED → updated
    - done-task.md (status: done) in state as done → UNCHANGED → skipped

    Adapter expectations:
    - taskdog_add for new-task (NEW)
    - taskdog_add for changed-task (CHANGED - not done, uses add)
    - NO taskdog_done (done-task is UNCHANGED)
    """
    adapter = MockStdioAdapter()

    result = run_sync(
        vault_root=e2e_vault,
        state_path=e2e_state,
        adapter=adapter,
    )

    # Corrected counts (per fixture analysis):
    # - new-task.md (status: planned) NOT in state → NEW
    # - changed-task.md (status: in_progress) in state as planned → CHANGED → taskdog_add (not done)
    # - done-task.md (status: done) in state as done → UNCHANGED
    assert result.scanned == 3
    assert result.added == 1    # new-task: NEW
    assert result.updated == 1   # changed-task: CHANGED (planned→in_progress)
    assert result.completed == 0  # done-task: UNCHANGED (done→done)
    assert result.skipped == 1    # done-task
    assert result.errors == []

    # Adapter call assertions
    call_tools = [c["tool"] for c in adapter.calls]
    add_ueids = {c["args"]["ueid"] for c in adapter.calls if c["tool"] == "taskdog_add"}
    done_ueids = {c["args"]["ueid"] for c in adapter.calls if c["tool"] == "taskdog_done"}

    assert call_tools.count("taskdog_add") == 2, f"expected 2 taskdog_add calls, got {call_tools}"
    assert call_tools.count("taskdog_done") == 0, f"expected 0 taskdog_done calls, got {call_tools}"

    assert "ikigai:task:new:001" in add_ueids
    assert "ikigai:task:changed:002" in add_ueids

    # State file updated with both NEW and CHANGED entries
    state = load_state(e2e_state)
    assert "ikigai:task:new:001" in state.tasks
    assert state.tasks["ikigai:task:new:001"].last_status == "planned"
    assert "ikigai:task:changed:002" in state.tasks
    assert state.tasks["ikigai:task:changed:002"].last_status == "in_progress"
