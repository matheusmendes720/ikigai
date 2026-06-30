"""Tests for FrontmatterParser MODEL_MAP (T11) and Dream entity (T6 follow-up)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from models.dream_entities import Dream  # noqa: E402
from models.hypothesis_entities import (  # noqa: E402
    FalsifiableHypothesis,
    HypothesisEvaluation,
)
from pipeline.frontmatter_parser import FrontmatterParser  # noqa: E402


class TestModelMapRegistry:
    def test_dream_registered(self):
        assert "dream" in FrontmatterParser.MODEL_MAP
        assert FrontmatterParser.MODEL_MAP["dream"] is Dream

    def test_falsifiable_hypothesis_registered(self):
        assert "falsifiable_hypothesis" in FrontmatterParser.MODEL_MAP
        assert (
            FrontmatterParser.MODEL_MAP["falsifiable_hypothesis"]
            is FalsifiableHypothesis
        )

    def test_hypothesis_evaluation_registered(self):
        assert "hypothesis_evaluation" in FrontmatterParser.MODEL_MAP
        assert (
            FrontmatterParser.MODEL_MAP["hypothesis_evaluation"]
            is HypothesisEvaluation
        )

    def test_24_entity_types_total(self):
        assert len(FrontmatterParser.MODEL_MAP) == 24


class TestFrontmatterParsingDream:
    def test_parse_dream_from_file(self, tmp_path):
        md = tmp_path / "dream.md"
        md.write_text(
            "---\n"
            "entity_type: dream\n"
            "id: dr_architect\n"
            "title: Become a Life OS architect\n"
            "ikigai_vector: passion\n"
            "horizon_years: 5\n"
            "falsification_criteria: No paid offer by 2027-12-31\n"
            "leading_indicators:\n  - study_hours_weekly > 10\n"
            "milestones:\n  - 'Y1: shipping MVP'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8",
        )
        parsed = FrontmatterParser.parse_file(str(md))
        assert parsed is not None
        assert isinstance(parsed, Dream)
        assert parsed.id == "dr_architect"
        assert parsed.horizon_years == 5
        assert parsed.ikigai_vector == "passion"
        assert "study_hours_weekly > 10" in parsed.leading_indicators

    def test_parse_falsifiable_hypothesis_from_file(self, tmp_path):
        md = tmp_path / "fh.md"
        md.write_text(
            "---\n"
            "entity_type: falsifiable_hypothesis\n"
            "id: fh_q1\n"
            "dream_id: dr_architect\n"
            "hypothesis_text: Daily 90-min blocks sustain QHE > 0.7\n"
            "evidence_threshold: QHE < 0.5 over 90 days\n"
            "leading_indicators:\n  - study_min >= 60\n"
            "lagging_indicators:\n  - QHE > 0.7\n"
            "refactor_triggers:\n  - market_collapse\n"
            "---\n",
            encoding="utf-8",
        )
        parsed = FrontmatterParser.parse_file(str(md))
        assert parsed is not None
        assert isinstance(parsed, FalsifiableHypothesis)
        assert parsed.dream_id == "dr_architect"
        assert "study_min >= 60" in parsed.leading_indicators


class TestDreamEntity:
    def test_basic_dream(self):
        d = Dream(id="dr_x", title="Become a senior engineer")
        assert d.horizon_years == 5
        assert d.status == "active"
        assert d.ikigai_vector is None

    def test_invalid_id_pattern(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Dream(id="bad_id", title="Valid Title")

    def test_horizon_years_bounds(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Dream(id="dr_x", title="Valid Title", horizon_years=0)
        with pytest.raises(ValidationError):
            Dream(id="dr_x", title="Valid Title", horizon_years=21)

    def test_milestones_assigned(self):
        d = Dream(
            id="dr_x",
            title="Senior Engineer",
            milestones=["Y1: ship MVP", "Y3: scale to 100 users"],
        )
        assert len(d.milestones) == 2
        assert "ship MVP" in d.milestones[0]