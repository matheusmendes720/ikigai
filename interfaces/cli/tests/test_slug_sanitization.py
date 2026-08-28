"""Unit tests for slug sanitization used in task-add → UEID generation.

The slug must match `[a-z0-9-]+` per the UEID regex:
    ^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$

This test exercises the regex `re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-")[:50]`
indirectly via the generate_ueid() helper.
"""
from __future__ import annotations

import pytest

from interfaces.cli.read_tasks import generate_ueid
from src.contracts.common import UEID


@pytest.mark.parametrize(
    "title",
    [
        "Simple task",
        "Test foundation G1+G2+G3",
        "Buy groceries (urgent!)",
        "Read book & write notes",
        "Fix #1234 in repo",
        "A" * 100,  # long title
        "with   multiple    spaces",
        "  leading and trailing  ",
        "Unicode: ação rápida",
        "Special: !@#$%^&*()",
    ],
)
def test_title_produces_valid_ueid(title: str) -> None:
    """Any title should yield a UEID that matches the 5-part regex."""
    ueid = generate_ueid(title)
    # UEID type itself validates via regex on construction
    assert isinstance(ueid, UEID)
    parts = str(ueid).split(":")
    assert len(parts) == 4
    type_, slug, uuid_, hash_ = parts
    assert type_ == "tsk"
    # slug must be [a-z0-9-]+ (no +, no spaces, no parens)
    assert all(c.isalnum() or c == "-" for c in slug), f"slug has invalid chars: {slug!r}"
    assert uuid_  # non-empty
    assert hash_  # non-empty


def test_slug_strips_edge_hyphens() -> None:
    """Slugs should not start or end with hyphens after sanitization."""
    ueid = generate_ueid("___wrap___")
    parts = str(ueid).split(":")
    slug = parts[1]
    assert not slug.startswith("-"), f"slug starts with hyphen: {slug!r}"
    assert not slug.endswith("-"), f"slug ends with hyphen: {slug!r}"


def test_slug_truncates_to_50_chars() -> None:
    """UEID slug segment should be ≤ 50 chars to keep UEIDs sane length."""
    long_title = "a" * 200
    ueid = generate_ueid(long_title)
    parts = str(ueid).split(":")
    slug = parts[1]
    assert len(slug) <= 50, f"slug too long ({len(slug)} chars): {slug[:60]}..."


def test_ueids_are_unique() -> None:
    """generate_ueid produces unique IDs across calls (uuid4 + hash16)."""
    a = generate_ueid("same title")
    b = generate_ueid("same title")
    assert a != b
