"""Tests for entry_point parameter on make_v2_graph factory.

Skills (daily/weekly/monthly/quarterly) need to enter at specific nodes
without running the full pipeline. This parameter enables partial-graph
execution for skill-driven invocations.

Phase 8.4 — skills require entry_point routing.
"""

from __future__ import annotations

import pytest

# conftest.py sets up sys.path so agents.v2.* imports resolve cleanly.


def test_entry_point_default_is_observe(tmp_path):
    """Default entry_point is 'observe' (full pipeline from start)."""
    from agents.v2.graph import NODES, make_v2_graph

    # Ensure we exercise the default (entry_point="observe")
    graph = make_v2_graph(checkpoint_db=str(tmp_path / "default.db"))
    assert graph is not None

    # Confirm NODES tuple contains 'observe'
    assert "observe" in NODES


def test_entry_point_accepts_valid_node_names(tmp_path):
    """Valid node names (commit, surface_intentions, plan) accepted."""
    from agents.v2.graph import NODES, make_v2_graph

    valid_entry_points = (
        "observe",
        "score_vectors",
        "heuristics",
        "balance",
        "decompose",
        "plan",
        "reflect",
        "commit",
        "surface_intentions",
    )
    for ep in valid_entry_points:
        assert ep in NODES, f"{ep} must be in NODES"
        graph = make_v2_graph(
            checkpoint_db=str(tmp_path / f"ep_{ep}.db"),
            entry_point=ep,
        )
        assert graph is not None, f"entry_point={ep} should compile"


def test_entry_point_rejects_invalid_node_names(tmp_path):
    """Invalid entry_point raises ValueError listing valid options."""
    from agents.v2.graph import make_v2_graph

    with pytest.raises(ValueError, match="Invalid entry_point") as exc_info:
        make_v2_graph(
            checkpoint_db=str(tmp_path / "invalid.db"),
            entry_point="nonexistent_node",
        )

    # Error message should mention valid options
    msg = str(exc_info.value)
    assert "observe" in msg or "NODES" in msg, (
        f"Error must reference valid entry_points; got: {msg}"
    )


def test_entry_point_does_not_break_graph_compilation(tmp_path):
    """entry_point parameter must NOT break compilation for any valid node."""
    from agents.v2.graph import make_v2_graph

    graph = make_v2_graph(
        checkpoint_db=str(tmp_path / "drift_check.db"),
        entry_point="commit",
    )
    assert graph is not None
    # Confirm factory stamped the entry_point onto the compiled graph
    assert getattr(graph, "_ikigai_entry_point", None) == "commit"


def test_entry_point_default_unchanged_backward_compatible(tmp_path):
    """Calling make_v2_graph() with no entry_point still works (backward compat)."""
    from agents.v2.graph import make_v2_graph

    graph = make_v2_graph(checkpoint_db=str(tmp_path / "compat.db"))
    assert graph is not None
    assert getattr(graph, "_ikigai_entry_point", None) == "observe"
