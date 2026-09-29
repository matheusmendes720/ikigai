"""M159 — Vault embeddings cache (JSON-backed, no external deps).

The v2 deep agent's `recall_node` reads the vault (markdown files) on every
invocation. Without a cache, that means either:
  (a) re-reading the file from disk each time (cheap but repeated), or
  (b) re-embedding the same content each time (expensive API call).

This module provides a small cache layer:

  - JSON file at `<persist_dir>/vault_cache.json` keyed by absolute file path
  - One entry per file: {embedding: [...], mtime: float, text_snippet: "..."}
  - mtime-based invalidation: if the file's mtime changed since last
    index, we re-embed
  - Cosine similarity in pure Python (no numpy required)

Why JSON instead of ChromaDB?

  - ChromaDB 0.4.x requires numpy<2.0
  - ChromaDB 0.5+ requires opentelemetry modules that don't exist in
    installed versions (chroma itself is broken on Python 3.14 + otel)
  - We don't need HNSW for hundreds of vault files (linear scan is fine)
  - JSON cache is debuggable (you can `cat cache.json | jq`)

This is M159 minimum viable. Swap to ChromaDB / FAISS later if cache
size warrants it.

The embedding function is intentionally a deterministic local hash-based
fallback so tests are reproducible without an external model. Once a real
embedding backend is chosen (MiniMax probe, sentence-transformers, OpenAI),
swap `_deterministic_embed()`.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

_CACHE_FILENAME = "vault_cache.json"
_EMBED_DIM = 384


def _deterministic_embed(text: str, dim: int = _EMBED_DIM) -> list[float]:
    """Deterministic pseudo-embedding. Stable across runs.

    Uses 2-word shingles, hashes each, projects into a 384-dim vector.
    Not semantically meaningful, but stable + machine-independent.
    """
    vec = [0.0] * dim
    if not text:
        return vec
    words = text.split()
    if len(words) < 2:
        shingles = [text]
    else:
        shingles = [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)]
        shingles.append(text)
    for sh in shingles:
        h = hashlib.sha256(sh.encode("utf-8", errors="replace")).digest()
        bucket = struct.unpack(">Q", h[:8])[0] % dim
        sign = 1.0 if h[8] % 2 == 0 else -1.0
        vec[bucket] += sign * 1.0
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = sum(x * x for x in a) ** 0.5 or 1.0
    nb = sum(x * x for x in b) ** 0.5 or 1.0
    return dot / (na * nb)


class VaultEmbeddingCache:
    """Persistent JSON-backed embeddings cache for vault markdown files.

    Usage:
        cache = VaultEmbeddingCache()
        vec = cache.get_or_compute("vault/2026/09-29.md")
        sims = cache.similarity_to("show me what's pending", top_k=5)
    """

    def __init__(self, persist_dir: str = "data/chroma_db") -> None:
        self.persist_dir = persist_dir
        self._cache_path = Path(persist_dir) / _CACHE_FILENAME
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._cache_path.exists():
            try:
                self._data = json.loads(self._cache_path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        try:
            self._cache_path.write_text(
                json.dumps(self._data), encoding="utf-8"
            )
        except OSError:
            pass

    def _embed(self, text: str) -> list[float]:
        return _deterministic_embed(text)

    def get_or_compute(self, file_path: str) -> list[float]:
        """Return the embedding for `file_path`, computing if mtime changed."""
        p = Path(file_path)
        if not p.exists():
            return self._embed("")
        mtime = p.stat().st_mtime
        cached = self._data.get(file_path)
        if cached and cached.get("mtime") == mtime:
            emb = cached.get("embedding")
            if emb and len(emb) == _EMBED_DIM:
                return emb
        # Cache miss: compute and persist
        text = p.read_text(encoding="utf-8", errors="replace")
        embedding = self._embed(text)
        self._data[file_path] = {
            "embedding": embedding,
            "mtime": mtime,
            "text_snippet": text[:200],
            "size": p.stat().st_size,
        }
        self._save()
        return embedding

    def similarity_to(
        self, query: str, top_k: int = 5
    ) -> list[tuple[str, float]]:
        """Return top_k (file_path, similarity) for a query string."""
        qvec = self._embed(query)
        scored: list[tuple[str, float]] = []
        for file_id, entry in self._data.items():
            emb = entry.get("embedding")
            if not emb:
                continue
            scored.append((file_id, _cosine(qvec, emb)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def invalidate(self, file_path: str) -> None:
        """Drop the cached entry for a file (forces re-embed on next get)."""
        self._data.pop(file_path, None)
        self._save()

    def clear(self) -> None:
        """Drop all cached entries."""
        self._data = {}
        self._save()

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "persist_dir": str(self._cache_path.parent),
            "cache_file": str(self._cache_path),
            "count": len(self._data),
            "embed_dim": _EMBED_DIM,
        }


# Module-level singleton for convenience
_default_cache: VaultEmbeddingCache | None = None


def default_cache() -> VaultEmbeddingCache:
    """Return the process-wide default cache."""
    global _default_cache
    if _default_cache is None:
        _default_cache = VaultEmbeddingCache()
    return _default_cache
