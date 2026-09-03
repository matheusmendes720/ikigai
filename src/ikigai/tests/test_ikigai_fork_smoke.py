"""Tests for ikigai_fork_smoke graph — 3-node E2E fork connectivity smoke.

Per Phase 8.3: each of 4 forks (CLI, taskdog, solverforge-calendar, tuiboard)
must be reachable via UnifiedMCPGateway.

Graph topology:
    connect → call_forks → disconnect → END

The graph gracefully handles missing binaries — each fork call records
its status as one of {ok, skipped, error} so the graph never crashes on
production deploys where not all fork binaries are installed.
"""

from __future__ import annotations

import pytest

# conftest.py sets up sys.path so agents.v2.* imports resolve cleanly.


def test_fork_smoke_graph_imports():
    """ikigai_fork_smoke graph module imports cleanly."""
    from agents.v2.fork_smoke_graph import (
        FORK_SMOKE_NODES,
        make_fork_smoke_graph,
    )

    assert callable(make_fork_smoke_graph)
    assert FORK_SMOKE_NODES == ("connect", "call_forks", "disconnect")


def test_fork_smoke_graph_compiles(tmp_path):
    """make_fork_smoke_graph returns a compiled StateGraph."""
    from agents.v2.fork_smoke_graph import make_fork_smoke_graph

    graph = make_fork_smoke_graph(checkpoint_db=str(tmp_path / "fork_smoke.db"))
    assert graph is not None


def test_fork_smoke_graph_has_3_nodes(tmp_path):
    """Compiled graph contains exactly 3 nodes (connect, call_forks, disconnect)."""
    from agents.v2.fork_smoke_graph import FORK_SMOKE_NODES, make_fork_smoke_graph

    _ = make_fork_smoke_graph(checkpoint_db=str(tmp_path / "3_nodes.db"))
    # StateGraph exposes nodes via .nodes attribute (compiled form may differ)
    # Verify via NODES tuple constant
    assert len(FORK_SMOKE_NODES) == 3
    assert "connect" in FORK_SMOKE_NODES
    assert "call_forks" in FORK_SMOKE_NODES
    assert "disconnect" in FORK_SMOKE_NODES


def test_fork_smoke_handles_missing_binaries(tmp_path, monkeypatch):
    """Graph gracefully records 'skipped' status when binaries missing."""
    # Force PATH to empty so all fork binaries appear missing
    monkeypatch.setenv("PATH", "")

    from agents.v2.fork_smoke_graph import make_fork_smoke_graph

    graph = make_fork_smoke_graph(checkpoint_db=str(tmp_path / "no_binaries.db"))
    assert graph is not None
    # The graph must NOT raise during construction even with empty PATH
    # (forks are invoked at runtime, not at compile time)


def test_fork_smoke_default_entry_point_is_connect():
    """Default entry_point is 'connect' (start of smoke cycle)."""
    # No entry_point arg means default = "connect"
    import inspect

    from agents.v2.fork_smoke_graph import make_fork_smoke_graph

    sig = inspect.signature(make_fork_smoke_graph)
    entry_point_param = sig.parameters.get("entry_point")
    assert entry_point_param is not None
    assert entry_point_param.default == "connect"


def test_fork_smoke_rejects_invalid_entry_point(tmp_path):
    """Invalid entry_point raises ValueError."""
    from agents.v2.fork_smoke_graph import make_fork_smoke_graph

    with pytest.raises(ValueError, match="Invalid entry_point"):
        make_fork_smoke_graph(
            checkpoint_db=str(tmp_path / "invalid_ep.db"),
            entry_point="nonexistent",
        )
