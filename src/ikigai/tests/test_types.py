"""Tests for ikigai.types — UEID and ScoreValue."""

from __future__ import annotations

import pytest
from ikigai.types import ScoreValue, UEID


class TestUEID:
    """UEID tri-key anti-fragile identifier."""

    def test_pattern_matches_valid_ueid(self) -> None:
        """_PATTERN must accept the canonical format."""
        valid = "study:goal:go_master_backend:8e3f1a2c:d4b9e7"
        assert UEID._PATTERN.match(valid), f"Expected {valid!r} to match"

    def test_pattern_rejects_invalid(self) -> None:
        """Invalid formats must be rejected."""
        invalid = [
            "no_colon_at_all",
            "only:two",
            "missing:trailing:uuid:hash",
            "UPPERCASE:SLUG:fail",
            "study: invalid-slug:8e3f1a2c:d4b9e7",
        ]
        for s in invalid:
            assert UEID._PATTERN.match(s) is None, f"Expected {s!r} to NOT match"

    def test_generate_produces_deterministic_slugs(self) -> None:
        """Same namespace+type+slug must always produce same ueid."""
        ueid1 = UEID.generate("study", "goal", "go_master_python")
        ueid2 = UEID.generate("study", "goal", "go_master_python")
        assert ueid1 == ueid2, "Same inputs must produce same UEID (content-hash is deterministic)"

    def test_generate_different_slugs_differ(self) -> None:
        """Different slugs must produce different content-hashes."""
        u1 = UEID.generate("study", "goal", "go_a")
        u2 = UEID.generate("study", "goal", "go_b")
        assert u1 != u2

    def test_generate_handles_all_namespaces(self) -> None:
        """All 5 namespaces must be accepted without error."""
        for ns in ["study", "work", "health", "vibe", "meta"]:
            ueid = UEID.generate(ns, "goal", "test_goal")
            assert ns in str(ueid)

    def test_generate_handles_all_entity_types(self) -> None:
        """All entity types must be accepted."""
        from ikigai.enums import EntityType

        for et in EntityType:
            ueid = UEID.generate("study", et, "test")
            assert str(ueid).startswith(f"study:{et.value}:")

    def test_short_returns_8_chars(self) -> None:
        """short() must return exactly 8 characters."""
        short = UEID.generate("study", "goal", "test_goal").short()
        assert len(short) == 8
        assert short.isalnum() or short.isalpha()

    def test_with_new_content_hash_changes_hash(self) -> None:
        """with_new_content_hash must produce a different UEID."""
        original = UEID.generate("study", "goal", "test_goal")
        changed = original.with_new_content_hash()
        assert str(original) != str(changed)
        assert original.slug == changed.slug
        assert original.namespace == changed.namespace

    def test_with_new_content_hash_preserves_slug_and_namespace(self) -> None:
        """Slug and namespace must be preserved through hash change."""
        original = UEID.generate("work", "project", "my_project")
        changed = original.with_new_content_hash()
        assert original.slug == changed.slug
        assert original.namespace == changed.namespace
        assert original.entity_type == changed.entity_type

    def test_str_representation_contains_all_parts(self) -> None:
        """String must contain namespace:type:slug:uuid8:hash8."""
        ueid = UEID.generate("health", "habit", "run_daily")
        s = str(ueid)
        assert s.startswith("health:habit:run_daily:")
        parts = s.split(":")
        assert len(parts) == 5


class TestScoreValue:
    """ScoreValue — value + explicit unit field."""

    def test_creation_with_unit(self) -> None:
        """Must accept arbitrary unit strings."""
        sv = ScoreValue(value=42.0, unit="percent")
        assert sv.value == 42.0
        assert sv.unit == "percent"

    def test_to_percent(self) -> None:
        """to_percent must convert percent-unit values to 0-100."""
        sv = ScoreValue(value=0.75, unit="ratio")
        assert sv.to_percent() == 75.0

    def test_to_percent_passthrough(self) -> None:
        """Already-percent values must stay the same."""
        sv = ScoreValue(value=80.0, unit="percent")
        assert sv.to_percent() == 80.0

    def test_to_ratio(self) -> None:
        """to_ratio must convert 0-100 percent to 0-1."""
        sv = ScoreValue(value=85.0, unit="percent")
        assert sv.to_ratio() == 0.85

    def test_to_ratio_passthrough(self) -> None:
        """Already-ratio values must stay the same."""
        sv = ScoreValue(value=0.6, unit="ratio")
        assert sv.to_ratio() == 0.6

    def test_unit_is_preserved_in_dict(self) -> None:
        """to_dict must include the unit field."""
        sv = ScoreValue(value=50.0, unit="ikigai_score")
        d = sv.to_dict()
        assert d["unit"] == "ikigai_score"
        assert d["value"] == 50.0

    def test_equality_same_value_and_unit(self) -> None:
        """Equal values and units must be equal."""
        a = ScoreValue(value=42.0, unit="percent")
        b = ScoreValue(value=42.0, unit="percent")
        assert a == b

    def test_inequality_different_value(self) -> None:
        """Different values with same unit must differ."""
        a = ScoreValue(value=42.0, unit="percent")
        b = ScoreValue(value=99.0, unit="percent")
        assert a != b

    def test_inequality_different_unit(self) -> None:
        """Same value with different unit must differ."""
        a = ScoreValue(value=42.0, unit="percent")
        b = ScoreValue(value=42.0, unit="ratio")
        assert a != b
