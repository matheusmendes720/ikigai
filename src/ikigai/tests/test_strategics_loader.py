"""Unit tests for strategics loader — loads PT-BR strategic docs into agent context."""
from __future__ import annotations

import textwrap
from pathlib import Path


def test_load_strategics_returns_documents(tmp_path: Path) -> None:
    """All .md files under vault/strategics/ are returned as StrategicDoc."""
    from strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "planejamento.md").write_text(textwrap.dedent("""\
        ---
        tags: [strategic, planning]
        title: Planejamento
        ---
        # Planejamento

        Estratégia de planejamento.
    """), encoding="utf-8")
    (strat / "modelagem.md").write_text(textwrap.dedent("""\
        ---
        tags: [strategic, modeling]
        title: Modelagem Operacional
        ---
        # Modelagem Operacional

        Framework de modelagem.
    """), encoding="utf-8")

    ctx = load_strategics(tmp_path)
    titles = sorted(d.title for d in ctx.documents)
    assert titles == ["Modelagem Operacional", "Planejamento"]


def test_load_strategics_filters_by_tag(tmp_path: Path) -> None:
    """Only files with `tags: [strategic]` (or any strategic tag) are loaded."""
    from strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "strat.md").write_text(
        "---\ntags: [strategic]\ntitle: Strategic\n---\n# Strategic\n", encoding="utf-8"
    )
    (strat / "non-strat.md").write_text(
        "---\ntags: [draft]\ntitle: Draft\n---\n# Draft\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    titles = [d.title for d in ctx.documents]
    assert "Strategic" in titles
    assert "Draft" not in titles


def test_load_strategics_index_is_concatenated_body(tmp_path: Path) -> None:
    """index field contains all bodies joined for prompt injection."""
    from strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "a.md").write_text(
        "---\ntags: [strategic]\ntitle: AAA\n---\n# AAA\nbody A\n", encoding="utf-8"
    )
    (strat / "b.md").write_text(
        "---\ntags: [strategic]\ntitle: BBB\n---\n# BBB\nbody B\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    assert "AAA" in ctx.index
    assert "BBB" in ctx.index
    assert "body A" in ctx.index
    assert "body B" in ctx.index


def test_load_strategics_by_tag_index(tmp_path: Path) -> None:
    """by_tag dict groups StrategicDocs by their tag."""
    from strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "p.md").write_text(
        "---\ntags: [strategic, planning]\ntitle: P\n---\n# P\n", encoding="utf-8"
    )
    (strat / "m.md").write_text(
        "---\ntags: [strategic, modeling]\ntitle: M\n---\n# M\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    assert "planning" in ctx.by_tag
    assert "modeling" in ctx.by_tag
    assert len(ctx.by_tag["planning"]) == 1
    assert len(ctx.by_tag["modeling"]) == 1


def test_load_strategics_empty_dir_returns_empty_context(tmp_path: Path) -> None:
    """Empty strategics/ dir returns empty context (no error)."""
    from strategics.loader import load_strategics

    (tmp_path / "strategics").mkdir()
    ctx = load_strategics(tmp_path)
    assert ctx.documents == []
    assert ctx.by_tag == {}
    assert ctx.index == ""


def test_load_strategics_missing_dir_returns_empty_context(tmp_path: Path) -> None:
    """Missing strategics/ dir returns empty context (graceful)."""
    from strategics.loader import load_strategics

    ctx = load_strategics(tmp_path)
    assert ctx.documents == []


def test_load_strategics_handles_portuguese_accents(tmp_path: Path) -> None:
    """UTF-8 PT-BR content parses correctly."""
    from strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "estrategia.md").write_text(
        "---\ntags: [strategic]\ntitle: Estratégia\n---\n# Estratégia\n\nNão priorizar tudo.\n",
        encoding="utf-8",
    )

    ctx = load_strategics(tmp_path)
    assert len(ctx.documents) == 1
    assert "Estratégia" in ctx.documents[0].body
    assert "Não priorizar" in ctx.documents[0].body


def test_load_strategics_preserves_sha256(tmp_path: Path) -> None:
    """Each StrategicDoc carries its sha256."""
    from strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "x.md").write_text(
        "---\ntags: [strategic]\ntitle: X\n---\n# X\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    assert len(ctx.documents[0].sha256) == 64  # sha256 hex length
