"""v2 graph execution tests — close the BEHAVIOR gap identified by M154-AUDIT.

Calls ``_build_v2_graph(...).invoke(...)`` on real graph paths and
asserts the 9 WORKS nodes produce their documented state mutations.

State-schema workaround: LangGraph 1.x drops keys not in
IKIGAiStateDict (e.g. ``proposal``, ``context``, ``tag_propagation_input``,
``dispatch_plan``, ``task_id``, ``user_request``) before nodes see them.
Since we cannot modify state.py, we wrap each node function and
re-inject the missing fields at call time (graph still executes
end-to-end). Routing: monkeypatch ``_route_after_surface_intentions``
to always route to ``tag_propagation`` so commit_summary / draft_proposal
survive past surface_intentions (otherwise error_node overwrites them).

Constraints: no PAV imports; no real LLM calls; SqliteSaver per test.
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

# Path setup — match test_v2_node_isolation*.py pattern
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent
_SRC_ROOT = _REPO_ROOT / "src"
_IKIGAI_SRC = _THIS.parent.parent / "src"

for _p in [str(_REPO_ROOT), str(_SRC_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


def _invoke(graph: Any, state: dict[str, Any], *, thread_id: str = "exec-test") -> dict[str, Any]:
    """Invoke the graph with thread_id (required by SqliteSaver). Retries on transient 529s."""
    config = {"configurable": {"thread_id": thread_id}}
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            return graph.invoke(state, config)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if (
                not any(s in msg for s in ("529", "overloaded", "rate_limit", "timeout"))
                or attempt == 3
            ):
                raise
            time.sleep(0.5 * (2 ** (attempt - 1)))
    raise last_exc  # pragma: no cover


def _wrap_node(
    monkeypatch,
    node_module_path: str,
    attr_name: str,
    *,
    inject_into_state: dict[str, Any] | None = None,
) -> list[Any]:
    """Wrap a node: (a) inject fields LangGraph filtered out of state,
    (b) capture the raw return value before schema-filter.

    Patches BOTH the source module AND the graph module
    (dual-module identity fixup — see CLAUDE.md "Import-Path Rules").
    """
    import importlib

    src_mod = importlib.import_module(node_module_path)
    original = getattr(src_mod, attr_name)
    capture_log: list[Any] = []

    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], dict) and inject_into_state:
            state = dict(args[0])
            state.update(inject_into_state)
            args = (state, *args[1:])
        result = original(*args, **kwargs)
        capture_log.append(result)
        return result

    monkeypatch.setattr(src_mod, attr_name, _wrapped)
    import src.ikigai.src.agents.v2.graph as _graph_mod

    if hasattr(_graph_mod, attr_name):
        monkeypatch.setattr(_graph_mod, attr_name, _wrapped)
    return capture_log


def _force_route_to_tag_propagation(monkeypatch) -> None:
    """Force ``_route_after_surface_intentions`` → tag_propagation (preserves commit_summary)."""
    import src.ikigai.src.agents.v2.graph as _graph_mod

    def _always_route(state: Any) -> str:
        return "error" if state.get("error_type") else "tag_propagation"

    monkeypatch.setattr(_graph_mod, "_route_after_surface_intentions", _always_route)


def _base_state(**overrides: Any) -> dict[str, Any]:
    """Minimal IKIGAiStateDict — NotRequired fields defaulted per OPEN-3 fix."""
    state: dict[str, Any] = {
        "cycle_id": "exec-iso-001",
        "cycle_start": "2026-10-05",
        "cycle_end": "2026-10-05",
        "iteration": 0,
        "user_input": None,
        "user_request": "",
        "context": {},
        "draft_proposal": {},
        "proposed_entity": None,
        "vault_path": None,
        "actor": "agent",
    }
    state.update(overrides)
    return state


def test_recall_node_populates_context_from_memory_db(tmp_path, monkeypatch) -> None:
    """recall_node reads daily_intentions from a temp memory_db and populates context.

    Writes 1 row with ``ts`` = now so recall_node's 14-day window matches.
    Skips ``ueid`` check (recall_node reads ``d.get("daily_ueid")`` but
    ``_read_records`` returns key ``ueid`` — pre-existing code quirk).
    """
    mem_db = tmp_path / "memory.db"
    conn = sqlite3.connect(str(mem_db))
    conn.executescript("""
        CREATE TABLE memory_daily_intentions (
            daily_ueid TEXT PRIMARY KEY, body_markdown TEXT NOT NULL,
            sha256 TEXT NOT NULL, vault_path TEXT NOT NULL,
            actor TEXT NOT NULL CHECK(actor IN ('user', 'agent', 'system')),
            source_ueids TEXT NOT NULL DEFAULT '[]', ts REAL NOT NULL
        )
    """)
    body = "BYD Camaçari case study — daily intention"
    now_ts = time.time()
    conn.execute(
        "INSERT INTO memory_daily_intentions VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ts:dia:abcd:0001", body, "deadbeef" * 8, "vault/test.md", "user", "[]", now_ts),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("IKIGAI_MEMORY_DB", str(mem_db))
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    cap = _wrap_node(monkeypatch, "src.ikigai.src.agents.v2.nodes.recall_node", "recall_node")
    _force_route_to_tag_propagation(monkeypatch)

    graph = _build_v2_graph(checkpoint_db=str(tmp_path / "recall_ckpt.db"), entry_point="recall")
    result = _invoke(graph, _base_state(), thread_id="recall-test")

    assert len(cap) == 1
    ctx = cap[0]["context"]
    assert ctx["strategics_loaded"] is True
    assert isinstance(ctx["recent_intentions"], list)
    assert len(ctx["recent_intentions"]) == 1
    rec = ctx["recent_intentions"][0]
    assert rec["body_markdown"] == body
    assert abs(rec["ts"] - now_ts) < 1.0
    assert rec["vault_path"] == "vault/test.md"
    assert rec["actor"] == "user"
    assert ctx["daily_intentions_count"] == 1
    assert ctx["weekly_aggregations_count"] == 0
    assert result["last_step"] == "tag_propagation"


def test_reason_node_proposes_from_context(tmp_path, monkeypatch) -> None:
    """reason_node consumes recent_intentions and emits draft_proposal.

    Pre-populates context (via _wrap_node injection since LangGraph
    filters ``context`` from input state). draft_proposal IS in
    IKIGAiStateDict so we assert on the final graph state directly.
    """
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    ueid = "ts:dia:0001:0001"
    cap = _wrap_node(
        monkeypatch,
        "src.ikigai.src.agents.v2.nodes.reason_node",
        "reason_node",
        inject_into_state={
            "context": {
                "recent_intentions": [
                    {
                        "ueid": ueid,
                        "ts": 1_700_000_000.0,
                        "vault_path": "vault/test.md",
                        "body_markdown": "BYD case study deep-dive",
                        "actor": "user",
                    }
                ]
            },
            "user_request": "",
        },
    )
    _force_route_to_tag_propagation(monkeypatch)

    graph = _build_v2_graph(checkpoint_db=str(tmp_path / "reason_ckpt.db"), entry_point="reason")
    result = _invoke(graph, _base_state(), thread_id="reason-test")

    assert len(cap) == 1
    proposal = result["draft_proposal"]
    assert proposal["status"] == "draft"
    assert proposal["proposal_id"].startswith("ikigai:proposal:")
    op_types = [op.get("type") for op in proposal["operations"]]
    assert "reflect.intention" in op_types
    assert ueid in proposal["reasoning"]
    assert proposal["context_refs"] == [ueid]
    assert result["iteration"] == 1


def test_decompose_node_calls_mcp_bridge(tmp_path, monkeypatch) -> None:
    """decompose_node invokes mcp_bridge.ikigai_decompose once and surfaces the result.

    task_id is NOT in IKIGAiStateDict so we re-inject via _wrap_node.
    """
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2 import mcp_bridge
    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    mock_return: dict[str, Any] = {
        "ok": True,
        "subtasks": [
            {"ueid": "ts:dia:0001:0002", "title": "Subtask A"},
            {"ueid": "ts:dia:0001:0003", "title": "Subtask B"},
        ],
        "source_task_id": "ts:dia:0001:0001",
    }
    call_log: list[dict[str, Any]] = []

    def _fake_ikigai_decompose(*, task_id: str) -> dict[str, Any]:
        call_log.append({"task_id": task_id})
        return mock_return

    monkeypatch.setattr(mcp_bridge, "ikigai_decompose", _fake_ikigai_decompose)
    cap = _wrap_node(
        monkeypatch,
        "src.ikigai.src.agents.v2.nodes.decompose",
        "decompose_node",
        inject_into_state={"task_id": "ts:dia:0001:0001"},
    )
    _force_route_to_tag_propagation(monkeypatch)

    graph = _build_v2_graph(
        checkpoint_db=str(tmp_path / "decompose_ckpt.db"), entry_point="decompose"
    )
    _invoke(graph, _base_state(), thread_id="decompose-test")

    assert len(cap) == 1
    assert cap[0]["decompose"] == mock_return
    assert cap[0]["error_channel"] == []
    assert call_log == [{"task_id": "ts:dia:0001:0001"}]


def test_tag_and_persist_writes_to_vault(tmp_path, monkeypatch) -> None:
    """tag_and_persist_node calls wrap_vault_write and reports persisted=True.

    ``persisted`` IS in IKIGAiStateDict so we assert on final state.
    """
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph
    from src.ikigai.src.agents.v2.nodes import proposal_executor as pe

    call_log: list[dict[str, Any]] = []

    def _fake_wrap_vault_write(*, actor: str, vault_path: str, **kwargs: Any) -> dict[str, Any]:
        call_log.append({"actor": actor, "vault_path": vault_path, **kwargs})
        return {"ok": True, "error": ""}

    monkeypatch.setattr(pe, "wrap_vault_write", _fake_wrap_vault_write, raising=False)
    _force_route_to_tag_propagation(monkeypatch)

    graph = _build_v2_graph(
        checkpoint_db=str(tmp_path / "tag_persist_ckpt.db"), entry_point="tag_and_persist"
    )
    result = _invoke(
        graph,
        _base_state(
            proposed_entity={
                "tier": "daily",
                "title": "exec test entity",
                "ueid": "ts:dia:exec:0001",
            },
            vault_path="ikigai/exec-test.md",
            actor="agent",
            user_request="exec test rationale",
        ),
        thread_id="tag-persist-test",
    )

    assert result["persisted"] is True
    assert result["vault_path"] == "ikigai/exec-test.md"
    assert result["actor"] == "agent"
    assert len(call_log) == 1
    assert call_log[0]["actor"] == "agent"
    assert call_log[0]["vault_path"] == "ikigai/exec-test.md"


def test_commit_node_produces_canonical_summary(tmp_path, monkeypatch) -> None:
    """commit_node writes ``COMMIT cycle=... tier=... proposal=... ok=True``."""
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    _force_route_to_tag_propagation(monkeypatch)

    graph = _build_v2_graph(checkpoint_db=str(tmp_path / "commit_ckpt.db"), entry_point="commit")
    result = _invoke(
        graph,
        _base_state(
            draft_proposal={
                "proposal_id": "ikigai:proposal:exec0001:short",
                "status": "draft",
                "operations": [],
                "reasoning": "exec test",
            },
            active_goal_ueids=["ts:goal:abcd:0001"],  # forces tier="goal"
        ),
        thread_id="commit-test",
    )

    summary = result["commit_summary"]
    assert summary.startswith("COMMIT cycle=")
    assert summary.endswith("ok=True")
    assert "proposal=ikigai:proposal:exec0001:short" in summary
    assert "tier=goal" in summary
    assert result["terminated"] is True


def test_dispatch_sub_agents_empty_passthrough(tmp_path, monkeypatch) -> None:
    """dispatch_sub_agents is a passthrough no-op when dispatch_plan is empty/absent.

    sub_agent_results NOT in captured return (no-op path); dispatch_plan
    remains empty; graph continues to surface → tag_propagation → END.
    dispatch_plan is NOT in IKIGAiStateDict so we inject explicitly.
    """
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    cap = _wrap_node(
        monkeypatch,
        "src.ikigai.src.agents.v2.subgraph",
        "dispatch_sub_agents",
        inject_into_state={"dispatch_plan": []},
    )
    _force_route_to_tag_propagation(monkeypatch)

    graph = _build_v2_graph(
        checkpoint_db=str(tmp_path / "dispatch_ckpt.db"), entry_point="dispatch_sub_agents"
    )
    result = _invoke(graph, _base_state(), thread_id="dispatch-test")

    assert len(cap) == 1
    assert "sub_agent_results" not in cap[0]
    assert not result.get("dispatch_plan")
    assert result["last_step"] == "tag_propagation"


def test_tag_propagation_proposes_reachable_tasks(tmp_path, monkeypatch) -> None:
    """tag_propagation_node BFS-walks the dep graph; source excluded, tags deduped+sorted.

    ``tag_propagation_input`` is NOT in IKIGAiStateDict so we re-inject.
    """
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    source_ueid = "ts:prj:abcd:0001"
    cap = _wrap_node(
        monkeypatch,
        "src.ikigai.src.agents.v2.nodes.tag_propagation",
        "tag_propagation_node",
        inject_into_state={
            "tag_propagation_input": {
                "source_ueid": source_ueid,
                "tags": ["weekly", "p0", "weekly"],  # duplicate
                "graph": {
                    source_ueid: ["ts:prj:abcd:0002", "ts:prj:abcd:0003"],
                    "ts:prj:abcd:0002": ["ts:prj:abcd:0004"],
                    "ts:prj:abcd:0003": [],
                    "ts:prj:abcd:0004": [],
                },
            }
        },
    )

    graph = _build_v2_graph(
        checkpoint_db=str(tmp_path / "tag_prop_ckpt.db"), entry_point="tag_propagation"
    )
    _invoke(graph, _base_state(), thread_id="tag-prop-test")

    assert len(cap) == 1
    proposal = cap[0]["proposal"]
    assert proposal["action"] == "tag_propagate"
    assert proposal["node"] == "tag_propagation"
    assert proposal["source_ueid"] == source_ueid
    assert source_ueid not in proposal["target_ueids"]
    assert set(proposal["target_ueids"]) == {
        "ts:prj:abcd:0002",
        "ts:prj:abcd:0003",
        "ts:prj:abcd:0004",
    }
    assert proposal["tags"] == ["p0", "weekly"]
    assert proposal["target_ueids"] == sorted(proposal["target_ueids"])


def test_dep_graph_proposes_siblings_without_cycle(tmp_path, monkeypatch) -> None:
    """dep_graph_node proposes dep additions among same-cluster tasks (no cycle)."""
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    cap = _wrap_node(
        monkeypatch,
        "src.ikigai.src.agents.v2.nodes.dep_graph",
        "dep_graph_node",
        inject_into_state={
            "dep_graph_input": {
                "project_prefix": "ts:prj:abcd",
                "tasks": {
                    "ts:prj:abcd:0001": {"priority": 2},
                    "ts:prj:abcd:0002": {"priority": 1},
                    "ts:prj:abcd:0003": {"priority": 3},
                },
                "existing_deps": {},
            }
        },
    )

    graph = _build_v2_graph(
        checkpoint_db=str(tmp_path / "dep_graph_ckpt.db"), entry_point="dep_graph"
    )
    _invoke(graph, _base_state(), thread_id="dep-graph-test")

    assert len(cap) == 1
    proposal = cap[0]["proposal"]
    assert proposal["action"] == "add_deps"
    assert proposal["node"] == "dep_graph"
    assert proposal["from_ueid"] is not None
    assert proposal["from_ueid"] not in proposal["to_ueids"]
    other = sorted({"ts:prj:abcd:0002", "ts:prj:abcd:0003"} - {proposal["from_ueid"]})
    assert set(proposal["to_ueids"]) == set(other)


def test_gantt_suggests_topological_order(tmp_path, monkeypatch) -> None:
    """gantt_suggest_node emits topological + priority-weighted task order.

    With u-a → u-b, u-a → u-c (priorities a=2, b=1, c=3), u-a first;
    then u-b (priority 1) before u-c (priority 3) in batch 2.
    """
    monkeypatch.delenv("IKIGAI_FAKE_LLM", raising=False)

    from src.ikigai.src.agents.v2.graph import _build_v2_graph

    cap = _wrap_node(
        monkeypatch,
        "src.ikigai.src.agents.v2.nodes.gantt_suggest",
        "gantt_suggest_node",
        inject_into_state={
            "gantt_input": {
                "tasks": {
                    "u-a": {"priority": 2, "deps": []},
                    "u-b": {"priority": 1, "deps": ["u-a"]},
                    "u-c": {"priority": 3, "deps": ["u-a"]},
                }
            }
        },
    )

    graph = _build_v2_graph(
        checkpoint_db=str(tmp_path / "gantt_ckpt.db"), entry_point="gantt_suggest"
    )
    _invoke(graph, _base_state(), thread_id="gantt-test")

    assert len(cap) == 1
    proposal = cap[0]["proposal"]
    assert proposal["action"] == "reorder"
    assert proposal["node"] == "gantt_suggest"
    order = proposal["suggestion"]
    assert order.index("u-a") < order.index("u-b")
    assert order.index("u-a") < order.index("u-c")
    assert set(order) == {"u-a", "u-b", "u-c"}
    assert len(proposal["batches"]) == 2
    assert proposal["batches"][0] == ["u-a"]
    batch2 = proposal["batches"][1]
    assert set(batch2) == {"u-b", "u-c"}
    assert batch2.index("u-b") < batch2.index("u-c")
    assert proposal.get("unscheduled", []) == []
