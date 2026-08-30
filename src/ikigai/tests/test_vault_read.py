"""Unit tests for vault_read — read-side mirror of vault_write."""
from __future__ import annotations

import textwrap
from pathlib import Path


def test_vault_read_parses_frontmatter_and_body(tmp_path: Path) -> None:
    """Frontmatter dict + body returned separately."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "test.md").write_text(textwrap.dedent("""\
        ---
        ueid: ikigai:test:read:001
        title: Test
        ---
        # Body section

        Some markdown body.
    """))

    result = vault_read(vault, "test.md")
    assert result["frontmatter"]["ueid"] == "ikigai:test:read:001"
    assert result["frontmatter"]["title"] == "Test"
    assert "# Body section" in result["body"]
    assert len(result["sha256"]) == 64  # sha256 hex
    assert result["mtime"] > 0


def test_vault_read_missing_file_raises(tmp_path: Path) -> None:
    """Missing file raises FileNotFoundError."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    import pytest
    with pytest.raises(FileNotFoundError):
        vault_read(vault, "missing.md")


def test_vault_read_no_frontmatter_returns_empty_dict(tmp_path: Path) -> None:
    """Plain markdown (no frontmatter) returns empty frontmatter dict."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "plain.md").write_text("# Plain markdown\n\nNo frontmatter.\n")
    result = vault_read(vault, "plain.md")
    assert result["frontmatter"] == {}
    assert "# Plain markdown" in result["body"]


def test_vault_read_empty_file_returns_empty_body(tmp_path: Path) -> None:
    """Empty file returns empty body + empty frontmatter."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "empty.md").write_text("")
    result = vault_read(vault, "empty.md")
    assert result["body"] == ""
    assert result["frontmatter"] == {}


def test_vault_read_handles_unicode(tmp_path: Path) -> None:
    """UTF-8 (Portuguese accents) round-trips correctly."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "pt-br.md").write_text(
        "---\ntitle: Planejamento\n---\n# Estratégia\n\nNão priorizar.\n",
        encoding="utf-8",
    )
    result = vault_read(vault, "pt-br.md")
    assert result["frontmatter"]["title"] == "Planejamento"
    assert "Estratégia" in result["body"]
    assert "Não priorizar." in result["body"]


def test_vault_read_concurrent_readers_do_not_block(tmp_path: Path) -> None:
    """Two concurrent readers can both hold VaultLock (shared lock)."""
    import threading

    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "test.md").write_text("---\ntitle: T\n---\nBody\n")

    results: list[dict] = []
    errors: list[Exception] = []

    def reader():
        try:
            results.append(vault_read(vault, "test.md"))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(results) == 5


def test_vault_read_returns_sha256_matches_file_content(tmp_path: Path) -> None:
    """SHA256 hash matches actual file bytes on disk."""
    import hashlib

    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    # Use write_bytes to keep newline semantics consistent on Windows (where
    # write_text converts \n -> \r\n); the sha256 is computed from raw file
    # bytes, so the test must compare against the actual file bytes too.
    raw = b"---\nkey: value\n---\n# body\n"
    target = vault / "h.md"
    target.write_bytes(raw)

    result = vault_read(vault, "h.md")
    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    assert result["sha256"] == expected


def test_vault_read_mtime_matches_file(tmp_path: Path) -> None:
    """mtime is the file's actual mtime."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    f = vault / "m.md"
    f.write_text("x")
    expected_mtime = f.stat().st_mtime

    result = vault_read(vault, "m.md")
    assert abs(result["mtime"] - expected_mtime) < 1.0


def test_vault_read_nested_path(tmp_path: Path) -> None:
    """Read works for nested paths inside vault_root."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    nested = vault / "plans" / "q3"
    nested.mkdir(parents=True)
    (nested / "task-x.md").write_text(
        "---\nueid: ikigai:task:x:1\n---\n# Nested\n",
        encoding="utf-8",
    )

    result = vault_read(vault, "plans/q3/task-x.md")
    assert result["frontmatter"]["ueid"] == "ikigai:task:x:1"
    assert "# Nested" in result["body"]


def test_vault_read_does_not_mutate_target_file(tmp_path: Path) -> None:
    """Read-only contract — file content unchanged after vault_read."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    # write_bytes so Windows does NOT convert \n -> \r\n (we want exact bytes).
    content = b"---\nueid: ikigai:read:001\n---\n# Original body\n\nKeep me safe.\n"
    target = vault / "preserve.md"
    target.write_bytes(content)
    mtime_before = target.stat().st_mtime

    result = vault_read(vault, "preserve.md")
    # frontmatter.loads() preserves body verbatim (no trailing newline
    # stripping unless one was already missing); here the body has no
    # trailing newline after parsing because content was a single chunk.
    assert "# Original body" in result["body"]
    assert "Keep me safe." in result["body"]
    assert target.read_bytes() == content
    assert target.stat().st_mtime == mtime_before
    # No .vault.lock file created as a side effect
    assert not (vault / ".vault.lock").exists()
