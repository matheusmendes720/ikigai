"""Tests for UEID.from_legacy() — bridge between 2-part underscore and canonical 4-part.

Phase 1 of zazzy-plotting-flask.md §5.

Run::

    pytest src/ikigai/tests/test_ueid_dual_format.py -v
"""

from __future__ import annotations

import pytest
from contracts.common import UEID


class TestUEIDFromLegacy:
    def test_canonical_format_still_works(self) -> None:
        """Canonical 4-part UEID construction is unaffected by from_legacy."""
        raw = "tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef"
        ueid = UEID(raw)
        assert ueid == raw

    def test_from_legacy_accepts_canonical_format(self) -> None:
        """from_legacy() passes canonical 4-part colon format directly to constructor."""
        canonical = "tsk:foo:00000000-0000-0000-0000-000000000000:0000000000000000"
        result = UEID.from_legacy(canonical)
        assert result == canonical

    def test_from_legacy_parses_2part_underscore(self) -> None:
        """Legacy type_slug format is converted to canonical 4-part with zero UUID/hash."""
        result = UEID.from_legacy("tsk_morning_water")
        expected = UEID(
            "tsk:morning-water:00000000-0000-0000-0000-000000000000:0000000000000000"
        )
        assert result == expected

    def test_from_legacy_accepts_various_types(self) -> None:
        """Table-driven: from_legacy() handles tsk_, hab_, proj_, sub_, chk_ prefixes."""
        cases = [
            ("tsk_foo", "tsk:foo:00000000-0000-0000-0000-000000000000:0000000000000000"),
            ("hab_morning_water", "hab:morning-water:00000000-0000-0000-0000-000000000000:0000000000000000"),
            ("proj_vaga_remota_2026", "proj:vaga-remota-2026:00000000-0000-0000-0000-000000000000:0000000000000000"),
            ("sub_deliverable_review", "sub:deliverable-review:00000000-0000-0000-0000-000000000000:0000000000000000"),
            ("chk_prerequisite_check", "chk:prerequisite-check:00000000-0000-0000-0000-000000000000:0000000000000000"),
        ]
        for legacy, expected_canonical in cases:
            result = UEID.from_legacy(legacy)
            assert result == expected_canonical

    def test_from_legacy_rejects_garbage(self) -> None:
        """Invalid legacy strings raise ValueError with a descriptive message."""
        invalid_cases = [
            "garbage",          # no delimiter
            "x_y_z",            # 3 parts
            "TSK_foo",          # uppercase type
            "tsk_",             # empty suffix
            "tsk-legacy",       # wrong delimiter (dash, not underscore)
            "_tsk_foo",         # leading underscore
        ]
        for invalid in invalid_cases:
            with pytest.raises(ValueError, match="Invalid UEID"):
                UEID.from_legacy(invalid)

    def test_from_legacy_returns_canonical_regex_compliant(self) -> None:
        """The UEID produced by from_legacy() passes the canonical 4-part regex."""
        legacy_cases = [
            "tsk_morning_water",
            "hab_sleep_8h",
            "proj_byd_case_review",
            "sub_deliverable_a",
            "chk_prerequisite",
        ]
        for legacy in legacy_cases:
            result = UEID.from_legacy(legacy)
            # Re-constructing via the canonical constructor must not raise
            re_parsed = UEID(result)
            assert re_parsed == result
