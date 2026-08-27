"""Tests for frontmatter_to_dict — frontmatter file → IKIGAiRecord-ready dict."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from ikigai.vault.frontmatter_to_dict import frontmatter_to_dict


@pytest.fixture
def tmp_vault() -> Path:
    d = Path(tempfile.mkdtemp(prefix="vault_test_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def dream_md(tmp_vault: Path) -> Path:
    p = tmp_vault / "vaga-remota-2026.md"
    p.write_text(
        """---
ueid: ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609
entity_type: dream
slug: vaga-remota-2026
title: Primeira vaga remota em Data/AI ate 2026-12-31
description: null
status: active
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.20, skill: 0.20, market: 0.20, revenue: 0.20, course: 0.20}
created_at: 2026-07-03T00:00:00Z
updated_at: 2026-07-03T00:00:00Z
source_md_path: data/matheus/dreams/vaga-remota-2026.md
custom:
  verticals: [data-analytics, ai-llm-tooling]
motivation: quer construir coisas legais
---
# SONHO

Body of the dream note.
""",
        encoding="utf-8",
    )
    return p


def test_round_trip_preserves_null(dream_md: Path) -> None:
    """RT-03: description=null preserved through deserialize."""
    d = frontmatter_to_dict(dream_md)
    assert d["description"] is None


def test_round_trip_preserves_datetime(dream_md: Path) -> None:
    """RT-04: re-parsed datetime carries tzinfo (parsed back to datetime object)."""
    from datetime import datetime, timezone
    d = frontmatter_to_dict(dream_md)
    assert isinstance(d["created_at"], datetime)
    assert d["created_at"].tzinfo is not None
    assert d["created_at"].astimezone(timezone.utc) == datetime(2026, 7, 3, tzinfo=timezone.utc)


def test_round_trip_preserves_extra(dream_md: Path) -> None:
    """RT-06: unknown frontmatter keys pass through."""
    d = frontmatter_to_dict(dream_md)
    assert d["motivation"] == "quer construir coisas legais"


def test_round_trip_preserves_custom(dream_md: Path) -> None:
    d = frontmatter_to_dict(dream_md)
    assert d["custom"]["verticals"] == ["data-analytics", "ai-llm-tooling"]


def test_no_frontmatter_returns_empty(tmp_vault: Path) -> None:
    p = tmp_vault / "plain.md"
    p.write_text("# Just a title, no frontmatter\n", encoding="utf-8")
    assert frontmatter_to_dict(p) == {}


def test_invalid_path_raises(tmp_vault: Path) -> None:
    with pytest.raises(FileNotFoundError):
        frontmatter_to_dict(tmp_vault / "nope.md")