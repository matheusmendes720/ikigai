"""Tests for compute_rice_score + compute_priority_rank (T5).

Pure arithmetic — no I/O, no fixtures. Runs in <50ms.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from pipeline.rice_exporter import (  # noqa: E402
    RiceInput,
    compute_priority_rank,
    compute_rice_score,
)


class TestComputeRiceScore:
    def test_basic_formula(self):
        # 100 * 2.5 * 0.8 / 5 = 40.0
        assert compute_rice_score(100, 2.5, 0.8, 5) == pytest.approx(40.0)

    def test_zero_effort_uses_min_guard(self):
        # 100 * 1 * 1 / 0.1 = 1000.0 (guarded)
        assert compute_rice_score(100, 1.0, 1.0, 0) == pytest.approx(1000.0)

    def test_negative_components_clamped_to_zero(self):
        # (-100, -1, -1, 5) -> all clamped to 0 -> 0 / 5 = 0
        assert compute_rice_score(-100, -1, -1, 5) == pytest.approx(0.0)

    def test_zero_components_yield_zero(self):
        assert compute_rice_score(0, 0, 0, 0) == pytest.approx(0.0)

    def test_higher_confidence_higher_score(self):
        low = compute_rice_score(100, 1.0, 0.1, 1.0)
        high = compute_rice_score(100, 1.0, 1.0, 1.0)
        assert high > low

    def test_higher_effort_lower_score(self):
        low_effort = compute_rice_score(100, 1.0, 1.0, 1.0)
        high_effort = compute_rice_score(100, 1.0, 1.0, 100.0)
        assert low_effort > high_effort


class TestComputePriorityRank:
    def test_empty_list_returns_empty(self):
        assert compute_priority_rank([]) == {}

    def test_single_task_ranks_one(self):
        tasks = [RiceInput("t1", 100, 1, 1, 1)]
        assert compute_priority_rank(tasks) == {"t1": 1}

    def test_descending_order(self):
        tasks = [
            RiceInput("low", 10, 1, 1, 1),
            RiceInput("high", 100, 1, 1, 1),
            RiceInput("mid", 50, 1, 1, 1),
        ]
        ranks = compute_priority_rank(tasks)
        assert ranks["high"] == 1
        assert ranks["mid"] == 2
        assert ranks["low"] == 3

    def test_dense_ranking_on_ties(self):
        # All equal score -> all rank 1.
        tasks = [
            RiceInput("a", 100, 1, 1, 1),
            RiceInput("b", 100, 1, 1, 1),
            RiceInput("c", 100, 1, 1, 1),
        ]
        ranks = compute_priority_rank(tasks)
        assert ranks == {"a": 1, "b": 1, "c": 1}

    def test_mixed_ties_and_unique(self):
        tasks = [
            RiceInput("a", 100, 1, 1, 1),  # score 100
            RiceInput("b", 100, 1, 1, 1),  # score 100 (tie with a)
            RiceInput("c", 50, 1, 1, 1),   # score 50
            RiceInput("d", 25, 1, 1, 1),   # score 25
        ]
        ranks = compute_priority_rank(tasks)
        assert ranks["a"] == 1
        assert ranks["b"] == 1
        assert ranks["c"] == 2
        assert ranks["d"] == 3

    def test_dict_input_supported(self):
        tasks = [
            {"id": "x", "reach": 100, "impact": 1, "confidence": 1, "effort_h": 1},
            {"id": "y", "reach": 50, "impact": 1, "confidence": 1, "effort_h": 1},
        ]
        ranks = compute_priority_rank(tasks)
        assert ranks == {"x": 1, "y": 2}

    def test_deterministic_tiebreaker_alphabetical(self):
        # Same score, different ids -> sorted alphabetically.
        tasks = [
            RiceInput("zeta", 100, 1, 1, 1),
            RiceInput("alpha", 100, 1, 1, 1),
            RiceInput("mid", 100, 1, 1, 1),
        ]
        ranks = compute_priority_rank(tasks)
        assert ranks == {"alpha": 1, "mid": 1, "zeta": 1}