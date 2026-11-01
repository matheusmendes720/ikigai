"""Vectorisation of text for the store's vector index.

The provider is a pluggable hook, and the default is a deterministic local
embedding — a hashing-trick bag of tokens, so texts that share words land near
each other in cosine space.

It is NOT a semantic model: two texts that mean the same thing but share no
words will not land close together. That is a deliberate placeholder, because
the store has to work with no API key and no cost, and swapping the provider
must not require touching the callers. Treat semantic search quality as
unmeasured until a real model is behind the provider.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Protocol

from src.contracts.store import EMBEDDING_DIM
from src.data.client import DataClient

__all__ = ["EmbeddingProvider", "EmbeddingService", "local_embedding"]

_TOKEN_RE = re.compile(r"[0-9a-z]+")
_HASHES_PER_TOKEN = 3


class EmbeddingProvider(Protocol):
    """Anything that turns text into a vector of the configured dimension."""

    def __call__(self, text: str) -> list[float]: ...


def local_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """A deterministic unit-length vector for the text.

    Tokens are hashed into buckets, so the result depends only on the text:
    the same text always produces the same vector, on any machine, without a
    network call.
    """
    vector = [0.0] * dim
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        sign = 1.0 if digest[-1] & 1 else -1.0
        for offset in range(_HASHES_PER_TOKEN):
            chunk = digest[offset * 4 : offset * 4 + 4]
            index = int.from_bytes(chunk, "big") % dim
            vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


class EmbeddingService:
    """Embeds text, caching by content hash so the same text is embedded once."""

    def __init__(
        self,
        client: DataClient | None = None,
        *,
        dim: int = EMBEDDING_DIM,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        self._client = client
        self._dim = dim
        self._provider: EmbeddingProvider = provider or (
            lambda text: local_embedding(text, self._dim)
        )
        self._cache: dict[str, list[float]] = {}
        self._provider_calls = 0

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def provider_calls(self) -> int:
        """How many times the provider was actually invoked. Used to prove the cache works."""
        return self._provider_calls

    async def embed(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        self._provider_calls += 1
        vector = self._provider(text)
        self._cache[key] = vector
        return vector

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]
