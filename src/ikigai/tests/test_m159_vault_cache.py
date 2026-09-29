"""Tests for M159 vault embeddings cache."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from agents.v2.vault_cache import (
    VaultEmbeddingCache,
    _cosine,
    _deterministic_embed,
)


@pytest.fixture
def tmp_cache_dir():
    """Yield a fresh tempdir for each test."""
    with tempfile.TemporaryDirectory(prefix="vault_cache_test_") as d:
        yield d


# ---------------------------------------------------------------------------
# Embedding function (deterministic)
# ---------------------------------------------------------------------------


def test_deterministic_embed_is_stable():
    """Same input → same output across calls."""
    a = _deterministic_embed("hello world")
    b = _deterministic_embed("hello world")
    assert a == b


def test_deterministic_embed_different_inputs_differ():
    """Different inputs → different vectors."""
    a = _deterministic_embed("hello world")
    b = _deterministic_embed("goodbye universe")
    assert a != b


def test_deterministic_embed_empty_input_returns_zeros():
    """Empty input → zero vector."""
    a = _deterministic_embed("")
    assert all(x == 0.0 for x in a)


def test_deterministic_embed_is_normalized():
    """Embedding vector has unit norm (for cosine similarity)."""
    a = _deterministic_embed("some text here")
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_deterministic_embed_returns_384_dims():
    """Default dimension is 384."""
    a = _deterministic_embed("test")
    assert len(a) == 384


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def test_cosine_identical_vectors_is_one():
    """Cosine of a vector with itself is 1.0."""
    a = [0.5, 0.5, 0.5]
    assert abs(_cosine(a, a) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors_is_zero():
    """Cosine of orthogonal vectors is 0."""
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(_cosine(a, b)) < 1e-9


def test_cosine_empty_input_returns_zero():
    """Empty vectors → 0.0 (no crash)."""
    assert _cosine([], []) == 0.0
    assert _cosine([1.0], []) == 0.0
    assert _cosine([], [1.0]) == 0.0


# ---------------------------------------------------------------------------
# Cache: basic operations
# ---------------------------------------------------------------------------


def test_cache_creates_persist_dir(tmp_cache_dir):
    """Constructor creates the cache directory if it doesn't exist."""
    target = os.path.join(tmp_cache_dir, "deep", "nested", "chroma")
    cache = VaultEmbeddingCache(persist_dir=target)
    assert Path(target).exists()


def test_cache_first_call_is_miss(tmp_cache_dir):
    """First call for a file computes the embedding and stores it."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    f = Path(tmp_cache_dir) / "test.md"
    f.write_text("hello world", encoding="utf-8")

    vec = cache.get_or_compute(str(f))
    assert len(vec) == 384
    assert cache.stats()["count"] == 1


def test_cache_second_call_is_hit(tmp_cache_dir):
    """Second call for same file returns same vector without re-embedding."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    f = Path(tmp_cache_dir) / "test.md"
    f.write_text("hello world", encoding="utf-8")

    vec1 = cache.get_or_compute(str(f))
    vec2 = cache.get_or_compute(str(f))
    assert vec1 == vec2


def test_cache_modified_file_invalidates(tmp_cache_dir):
    """Modifying the file's mtime triggers re-embedding."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    f = Path(tmp_cache_dir) / "test.md"
    f.write_text("hello world", encoding="utf-8")

    vec1 = cache.get_or_compute(str(f))
    # Force mtime change with sleep + rewrite
    time.sleep(0.05)
    f.write_text("completely different content", encoding="utf-8")
    vec2 = cache.get_or_compute(str(f))
    assert vec1 != vec2


def test_cache_missing_file_returns_zero_vector(tmp_cache_dir):
    """Non-existent file returns zero vector without crashing."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    f = Path(tmp_cache_dir) / "nope.md"  # doesn't exist
    vec = cache.get_or_compute(str(f))
    assert all(x == 0.0 for x in vec)


def test_cache_persists_across_instances(tmp_cache_dir):
    """New VaultEmbeddingCache instance loads existing cache from disk."""
    f = Path(tmp_cache_dir) / "test.md"
    f.write_text("hello", encoding="utf-8")

    # First instance populates cache
    cache1 = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    vec1 = cache1.get_or_compute(str(f))

    # Second instance reads from disk
    cache2 = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    assert cache2.stats()["count"] == 1
    vec2 = cache2.get_or_compute(str(f))
    assert vec1 == vec2


# ---------------------------------------------------------------------------
# Cache: similarity search
# ---------------------------------------------------------------------------


def test_similarity_returns_empty_when_cache_empty(tmp_cache_dir):
    """Empty cache → empty similarity result."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    sims = cache.similarity_to("anything")
    assert sims == []


def test_similarity_returns_cached_files(tmp_cache_dir):
    """After caching files, similarity_to returns them."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    f1 = Path(tmp_cache_dir) / "a.md"
    f1.write_text("apple banana cherry", encoding="utf-8")
    f2 = Path(tmp_cache_dir) / "b.md"
    f2.write_text("zebra yoga xylophone", encoding="utf-8")

    cache.get_or_compute(str(f1))
    cache.get_or_compute(str(f2))

    sims = cache.similarity_to("fruit", top_k=5)
    assert len(sims) == 2
    # Both files appear in results
    paths = [p for p, _ in sims]
    assert str(f1) in paths
    assert str(f2) in paths


def test_similarity_top_k_limits_results(tmp_cache_dir):
    """top_k limits the number of returned results."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    for i in range(5):
        f = Path(tmp_cache_dir) / f"f{i}.md"
        f.write_text(f"content {i}", encoding="utf-8")
        cache.get_or_compute(str(f))

    sims = cache.similarity_to("query", top_k=3)
    assert len(sims) == 3


# ---------------------------------------------------------------------------
# Cache: invalidation
# ---------------------------------------------------------------------------


def test_invalidate_drops_entry(tmp_cache_dir):
    """invalidate() removes the cached entry for a file."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    f = Path(tmp_cache_dir) / "test.md"
    f.write_text("hello", encoding="utf-8")

    cache.get_or_compute(str(f))
    assert cache.stats()["count"] == 1

    cache.invalidate(str(f))
    assert cache.stats()["count"] == 0


def test_invalidate_missing_file_is_noop(tmp_cache_dir):
    """invalidate() on a non-cached file does not crash."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    cache.invalidate("/nonexistent/path.md")  # should not raise


def test_clear_drops_all_entries(tmp_cache_dir):
    """clear() removes every cached entry."""
    cache = VaultEmbeddingCache(persist_dir=tmp_cache_dir)
    for i in range(3):
        f = Path(tmp_cache_dir) / f"f{i}.md"
        f.write_text(f"content {i}", encoding="utf-8")
        cache.get_or_compute(str(f))
    assert cache.stats()["count"] == 3

    cache.clear()
    assert cache.stats()["count"] == 0


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


def test_default_cache_returns_singleton():
    """default_cache() returns the same instance across calls."""
    from agents.v2.vault_cache import default_cache

    a = default_cache()
    b = default_cache()
    assert a is b


def test_default_cache_uses_default_persist_dir():
    """default_cache() uses data/chroma_db/ (the project default)."""
    from agents.v2.vault_cache import default_cache

    cache = default_cache()
    assert "chroma_db" in cache.stats()["persist_dir"]
