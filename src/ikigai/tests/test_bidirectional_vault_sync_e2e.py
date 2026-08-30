"""Roundtrip E2E: vault → taskdog → reverse_sync → queue → vault_write.

Full bidirectional loop verified:
  1. vault_write creates initial vault file (planned)
  2. taskdog SQLite created with planned status
  3. taskdog updated to done
  4. reverse_sync detects change → emits TaskChange to queue
  5. propagate() called with approved validation → vault_write invoked
  6. vault file reflects done status

vault_write is sync (per corrections — no asyncio).
UEIDs are 4-part hex (e.g. task:t:a1b2:c3d4).
Uses the double-ikigai src/ layout consistent with existing ikigai tests.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Ensure repo root on sys.path (matches existing ikigai test pattern)
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.ikigai.vault.sync import (
    ReverseSyncState,
    ReverseSyncTaskEntry,
    reverse_sync,
    save_reverse_state,
)
from src.ikigai.src.ikigai.vault.vault_write import vault_write
from src.mesh.agent_consumer import Decision, ValidationResult
from src.mesh import queue as _queue
from src.mesh.agent_propagator import propagate
from src.contracts.task_change import TaskAction, TaskChange


@pytest.fixture
def fresh_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolated vault root + taskdog SQLite + queue dir to tmp."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    db_path = tmp_path / "taskdog.db"
    qdir = tmp_path / "queue"
    qdir.mkdir()
    monkeypatch.setattr("src.mesh.queue.QUEUE_DIR", qdir)
    return vault_root, db_path, qdir


def test_roundtrip_done_status_propagates_back_to_vault(fresh_env, monkeypatch):
    """Full flow: vault task → taskdog → reverse → queue → agent → vault_write."""
    vault_root, db_path, qdir = fresh_env

    # 1. Initial vault task via vault_write (sync, no asyncio)
    vault_write(
        vault_root=vault_root,
        vault_path="task-t.md",
        frontmatter_fields={
            "ueid": "task:t:a1b2:c3d4",
            "title": "T",
            "status": "planned",
        },
        body="# T\n",
    )

    # 2. Taskdog SQLite reflects planned
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ueid TEXT UNIQUE, name TEXT, status TEXT, priority INTEGER,
            planned_start TEXT, planned_end TEXT, deadline TEXT, created_at TEXT
        );
    """)
    conn.execute(
        "INSERT INTO tasks (ueid, name, status, priority, created_at) VALUES (?, ?, ?, ?, ?)",
        ("task:t:a1b2:c3d4", "T", "planned", 1, "2026-08-29T00:00:00"),
    )
    conn.commit()
    conn.close()

    # 3. User marks done in taskdog
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE tasks SET status='done' WHERE ueid=?",
        ("task:t:a1b2:c3d4",),
    )
    conn.commit()
    conn.close()

    # 4. Save reverse sync state with known snapshot
    state_path = qdir.parent / "state.json"
    save_reverse_state(
        state_path,
        ReverseSyncState(
            version=1,
            tasks={
                "task:t:a1b2:c3d4": ReverseSyncTaskEntry(
                    last_seen_status="planned",
                    last_seen_title="T",
                    vault_path="task-t.md",
                )
            },
        ),
    )

    # 5. reverse_sync detects done → emits TaskChange to queue
    class LiveAdapter:
        def __init__(self, db):
            self.db = db

        def list_all(self):
            conn = sqlite3.connect(self.db)
            try:
                rows = conn.execute(
                    "SELECT ueid, name, status, priority FROM tasks"
                ).fetchall()
                return [
                    {"ueid": r[0], "name": r[1], "status": r[2], "priority": r[3]}
                    for r in rows
                ]
            finally:
                conn.close()

    result = reverse_sync(
        state_path=state_path,
        adapter=LiveAdapter(db_path),
        source_fork="taskdog",
    )
    assert result.emitted == 1, f"expected 1 emitted, got {result.emitted}"

    # 6. Read TaskChange from queue
    events = list(qdir.glob("*.json"))
    assert len(events) == 1, f"expected 1 event, got {len(events)}"
    event_data = json.loads(events[0].read_text())
    assert event_data["action"] == "done"
    assert event_data["fields"]["vault_path"] == "task-t.md"

    # 7. Construct TaskChange + ValidationResult for propagate()
    task_change = TaskChange(
        event_id=event_data["event_id"],
        ueid=event_data["ueid"],
        action=TaskAction.DONE,
        fields=event_data["fields"],
        source_fork="vault",  # vault-bound: triggers vault_write in propagate()
        timestamp=datetime.now(timezone.utc),
        status="pending",
    )
    validation = ValidationResult(
        decision=Decision.APPROVE,
        reason="task marked done in taskdog — update vault",
        approved_fields=event_data["fields"],
    )

    # 8. Monkeypatch vault_write to redirect to tmp vault and capture calls.
    #    propagate() resolves vault_root from agent_propagator.py paths;
    #    we intercept _vault_write_impl and point it at our tmp vault so the
    #    file lands where we can verify it.
    import src.mesh.agent_propagator as _prop
    import src.ikigai.src.ikigai.vault.vault_write as _vw

    writes: list[dict] = []

    def mock_vault_write(**kwargs):
        writes.append(kwargs)
        # Redirect to our tmp vault for real I/O verification in step 9
        return original(
            vault_root=vault_root,
            vault_path=kwargs["vault_path"],
            frontmatter_fields=kwargs["frontmatter_fields"],
            body=kwargs["body"],
        )

    original = _vw.vault_write
    _vw.vault_write = mock_vault_write
    try:
        propagate(
            event=task_change,
            validation=validation,
            adapters=[],  # no real fork adapters needed — vault is the target
        )
    finally:
        _vw.vault_write = original

    # 9. Verify vault_write was called with done status
    assert len(writes) == 1, f"expected 1 vault_write call, got {len(writes)}"
    w = writes[0]
    assert w["vault_path"] == "task-t.md"
    assert w["frontmatter_fields"]["status"] == "done"
    assert w["frontmatter_fields"]["ueid"] == "task:t:a1b2:c3d4"

    # 10. Vault reflects done (file was written to tmp vault by mock→original)
    final = (vault_root / "task-t.md").read_text()
    # Check both frontmatter and body markers
    assert "status: done" in final.lower() or "status done" in final.lower()
    assert "done" in final.lower()
