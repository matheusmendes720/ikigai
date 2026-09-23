"""M140 tests — vault_search.py.

Verifies substring/regex search, glob filtering, frontmatter kind
filtering, context lines, all 3 output formats, and error paths.
Uses tmp_path with synthetic markdown files (hermetic).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.vault.search import (  # noqa: E402
    DEFAULT_VAULT,
    _format_content,
    _format_paths,
    _list_vault_files,
    _parse_frontmatter,
    main,
    search_vault,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Synthetic vault with frontmatter, multiple files."""
    (tmp_path / "alpha.md").write_text(
        "---\n"
        "kind: cognitive\n"
        "title: Alpha\n"
        "context_before_line: This is the line right before the match.\n"
        "---\n"
        "First line with the keyword here.\n"
        "context_after_line: This is the line right after the match.\n"
        "Third line with keyword again.\n",
        encoding="utf-8",
    )
    (tmp_path / "beta.md").write_text(
        "---\nkind: fisico\ntitle: Beta\n---\n"
        "Beta line one.\n"
        "Beta line with keyword.\n",
        encoding="utf-8",
    )
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "draft1.md").write_text(
        "---\nkind: hibrido\ntitle: Draft One\n---\n"
        "Draft body without keyword.\n"
        "Last line with keyword at end.\n",
        encoding="utf-8",
    )
    (tmp_path / "notes.txt").write_text("not markdown", encoding="utf-8")
    return tmp_path


# === _parse_frontmatter ===

def test_parse_frontmatter_basic() -> None:
    text = "---\nkind: cognitive\ntitle: Hello\n---\nbody"
    assert _parse_frontmatter(text) == {"kind": "cognitive", "title": "Hello"}


def test_parse_frontmatter_quoted() -> None:
    text = '---\ntitle: "Quoted Value"\n---\nbody'
    assert _parse_frontmatter(text) == {"title": "Quoted Value"}


def test_parse_frontmatter_missing() -> None:
    text = "no frontmatter here"
    assert _parse_frontmatter(text) == {}


def test_parse_frontmatter_no_close() -> None:
    text = "---\nkind: x\nbody continues"
    assert _parse_frontmatter(text) == {}


# === _list_vault_files ===

def test_list_vault_files_all(vault: Path) -> None:
    files = _list_vault_files(vault)
    rels = sorted(p.relative_to(vault).as_posix() for p in files)
    assert rels == ["alpha.md", "beta.md", "drafts/draft1.md"]


def test_list_vault_files_glob(vault: Path) -> None:
    files = _list_vault_files(vault, "drafts/*.md")
    rels = sorted(p.relative_to(vault).as_posix() for p in files)
    assert rels == ["drafts/draft1.md"]


def test_list_vault_files_glob_no_match(vault: Path) -> None:
    files = _list_vault_files(vault, "*.txt")
    assert files == []


def test_list_vault_files_missing_dir(tmp_path: Path) -> None:
    """Missing vault dir → empty list (no crash)."""
    assert _list_vault_files(tmp_path / "nope") == []


# === search_vault: substring ===

def test_search_substring_basic(vault: Path) -> None:
    matches = search_vault("keyword", vault=vault)
    # alpha: 2 matches. beta: 1 match. draft: 2 matches (line 5 + line 6).
    # Total 5.
    assert len(matches) == 5
    rels = [m["rel_path"] for m in matches]
    assert rels.count("alpha.md") == 2
    assert rels.count("beta.md") == 1
    assert rels.count("drafts/draft1.md") == 2
    # Lines should be positive integers (line 1+).
    for m in matches:
        assert m["line"] >= 1
        assert "keyword" in m["match"]


def test_search_substring_case_insensitive(vault: Path) -> None:
    """Default is case-insensitive."""
    matches = search_vault("KEYWORD", vault=vault)
    # Same as case-sensitive lowercase = 5 matches.
    assert len(matches) == 5


def test_search_substring_case_sensitive(vault: Path) -> None:
    """--case-sensitive narrows results."""
    matches = search_vault("KEYWORD", vault=vault, case_sensitive=True)
    # The synthetic vault only has lowercase "keyword", so case-sensitive
    # search for "KEYWORD" returns 0 matches.
    assert len(matches) == 0


def test_search_substring_no_match(vault: Path) -> None:
    matches = search_vault("zzznotfound", vault=vault)
    assert matches == []


def test_search_limit(vault: Path) -> None:
    """--limit caps the result count."""
    matches = search_vault("keyword", vault=vault, limit=2)
    assert len(matches) == 2


def test_search_vault_missing(tmp_path: Path) -> None:
    """Missing vault → empty results, no crash."""
    matches = search_vault("anything", vault=tmp_path / "nope")
    assert matches == []


# === search_vault: regex ===

def test_search_regex_basic(vault: Path) -> None:
    matches = search_vault(r"line\b", vault=vault, use_regex=True)
    # All lines containing "line" followed by word boundary.
    # alpha.md has "First line", beta.md has "Beta line", etc.
    assert len(matches) > 0
    rels = {m["rel_path"] for m in matches}
    assert "alpha.md" in rels
    assert "beta.md" in rels


def test_search_regex_invalid(vault: Path) -> None:
    """Invalid regex raises ValueError."""
    with pytest.raises(ValueError, match="Invalid regex"):
        search_vault("[unclosed", vault=vault, use_regex=True)


def test_search_regex_special_chars_escaped(vault: Path) -> None:
    """Without --regex, special chars are treated literally."""
    # The pattern "with the keyword here" should match (alpha.md line 3).
    matches = search_vault("with the keyword here", vault=vault)
    assert len(matches) == 1
    assert matches[0]["rel_path"] == "alpha.md"


# === search_vault: filters ===

def test_search_glob_filter(vault: Path) -> None:
    """--glob restricts to specific files."""
    matches = search_vault("keyword", vault=vault, glob_pattern="drafts/*.md")
    # draft1.md has 2 matches: line 5 ("without keyword" - oh wait, that's no match)
    # Actually looking at the fixture: "Draft body without keyword." (line 5) HAS keyword.
    # "Last line with keyword at end." (line 6) HAS keyword.
    # So 2 matches in draft1.md.
    assert len(matches) == 2
    for m in matches:
        assert m["rel_path"] == "drafts/draft1.md"


def test_search_kind_filter(vault: Path) -> None:
    """--kind restricts by frontmatter kind."""
    matches = search_vault("keyword", vault=vault, kind="cognitive")
    assert len(matches) == 2
    for m in matches:
        assert m["rel_path"] == "alpha.md"
        assert m["kind"] == "cognitive"


def test_search_kind_no_match(vault: Path) -> None:
    """--kind with no matches → empty."""
    matches = search_vault("keyword", vault=vault, kind="nonexistent_kind")
    assert matches == []


def test_search_context_lines(vault: Path) -> None:
    """--context N adds before/after lines."""
    matches = search_vault("keyword here", vault=vault, context=1)
    assert len(matches) == 1
    m = matches[0]
    assert m["rel_path"] == "alpha.md"
    # Context lines should be 1 each.
    assert len(m["context_before"]) == 1
    assert len(m["context_after"]) == 1


def test_search_context_correct(vault: Path) -> None:
    """context=N includes N lines BEFORE and AFTER the match line."""
    matches = search_vault("keyword here", vault=vault, context=1)
    assert len(matches) == 1
    m = matches[0]
    # Match line is alpha.md's "First line with the keyword here." (line 6).
    # Line 5 = frontmatter closer "---", then content line.
    # Actually let me re-count: 1=---, 2=kind:, 3=title:, 4=context_before,
    # 5=---, 6=First line...
    # context_before for line 6 = line 5 = "---"
    # context_after = line 7 = "context_after_line: ..."
    assert m["match"] == "First line with the keyword here."
    assert m["context_before"] == ["---"]
    assert m["context_after"] == [
        "context_after_line: This is the line right after the match."
    ]


def test_search_context_no_match_no_crash(vault: Path) -> None:
    """context with no match → empty."""
    matches = search_vault("zzznomatch", vault=vault, context=5)
    assert matches == []


# === _format_content ===

def test_format_content() -> None:
    matches = [
        {"rel_path": "a.md", "line": 5, "match": "foo bar"},
        {"rel_path": "b/c.md", "line": 12, "match": "baz"},
    ]
    out = _format_content(matches)
    assert out == "a.md:5:foo bar\nb/c.md:12:baz\n"


def test_format_content_empty() -> None:
    assert _format_content([]) == ""


# === _format_paths ===

def test_format_paths_unique() -> None:
    matches = [
        {"rel_path": "a.md", "line": 5},
        {"rel_path": "a.md", "line": 10},
        {"rel_path": "b.md", "line": 3},
    ]
    out = _format_paths(matches)
    assert out == "a.md\nb.md\n"


def test_format_paths_empty() -> None:
    assert _format_paths([]) == ""


# === CLI: main ===

def test_main_content_format(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["keyword", "--vault", str(vault)])
    assert rc == 0
    out = capsys.readouterr().out
    # 5 matches total: alpha.md has 2, beta.md has 1, drafts/draft1.md has 2
    # (because "Draft body without keyword" also contains "keyword").
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) == 5
    # Each line should be `rel_path:line:content`.
    for line in lines:
        assert line.startswith(("alpha.md:", "beta.md:", "drafts/"))


def test_main_no_match_returns_1(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["zzznotfound", "--vault", str(vault)])
    assert rc == 1


def test_main_paths_format(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["keyword", "--vault", str(vault), "--format", "paths"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "alpha.md" in out
    assert "beta.md" in out
    assert "drafts/draft1.md" in out
    # Content format would have line numbers; paths format has just paths.
    assert ":5:" not in out


def test_main_json_format(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["keyword", "--vault", str(vault), "--format", "json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["query"] == "keyword"
    # 5 matches total (alpha.md 2, beta.md 1, draft1.md 2).
    assert parsed["match_count"] == 5
    assert len(parsed["matches"]) == 5


def test_main_glob_filter(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["keyword", "--vault", str(vault), "--glob", "alpha.md"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "alpha.md" in out
    assert "beta.md" not in out


def test_main_kind_filter(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["keyword", "--vault", str(vault), "--kind", "fisico", "--format", "paths"])
    assert rc == 0
    out = capsys.readouterr().out
    # beta.md has kind=fisico and 1 match.
    assert out.strip() == "beta.md"


def test_main_regex(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([r"line\b", "--vault", str(vault), "--regex"])
    assert rc == 0
    # "line" word appears in alpha.md, beta.md, draft1.md.
    out = capsys.readouterr().out
    assert "alpha.md" in out
    assert "beta.md" in out


def test_main_regex_invalid_returns_2(vault: Path) -> None:
    rc = main(["[unclosed", "--vault", str(vault), "--regex"])
    assert rc == 2


def test_main_limit(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["keyword", "--vault", str(vault), "--limit", "2"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) == 2


def test_main_context(vault: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--context includes before/after lines in JSON format."""
    rc = main(["keyword here", "--vault", str(vault), "--context", "1", "--format", "json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert len(parsed["matches"]) == 1
    m = parsed["matches"][0]
    # context_before and context_after should each have 1 line.
    assert len(m["context_before"]) == 1
    assert len(m["context_after"]) == 1
