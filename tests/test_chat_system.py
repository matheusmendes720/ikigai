import json
import sys
from pathlib import Path
sys.path.insert(0, "src/ikigai/src")

from chat.schema import Proposal, ChatThread
from chat.writer import write_entry, write_proposal
from chat.reader import read_thread
import pytest


def test_proposal_ueid_validates():
    p = Proposal(proposal_id="ikigai:task:abc:def", status="draft", operations=[], reasoning="")
    assert p.proposal_id == "ikigai:task:abc:def"


def test_proposal_rejects_5part_ueid():
    with pytest.raises(ValueError):
        Proposal(proposal_id="ikigai:task:abc:def:ghi", status="draft", operations=[], reasoning="")


def test_chat_thread_frozen():
    t = ChatThread(thread_id="abc", created_at="2026-09-14T00:00:00Z")
    assert t.profile_active == "ikigai-planner"


def test_write_and_read_entry(tmp_path):
    vault_root = tmp_path / "vault"
    md = write_entry(vault_root, "thread-1", {"ts": "2026-09-14T10:00", "actor": "user", "content": "hello"})
    assert md.exists()
    data = read_thread(vault_root, "thread-1")
    assert "hello" in data["chat_md"]


def test_write_proposal_creates_json_sidecar(tmp_path):
    vault_root = tmp_path / "vault"
    proposal = {
        "proposal_id": "ikigai:task:abc:def",
        "status": "draft",
        "operations": [{"type": "task.create", "target": "x"}],
        "reasoning": "test",
    }
    js = write_proposal(vault_root, "thread-2", proposal)
    assert js.exists()
    data = json.loads(js.read_text(encoding="utf-8"))
    assert "ikigai:task:abc:def" in data["proposals"]
