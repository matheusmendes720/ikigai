"""Vectorisation of text for the store's vector index.

The provider is a pluggable hook, and the default is a deterministic local
embedding — a hashing-trick bag of tokens, so texts that share words land near
each other in cosine space.

It is NOT a semantic model: two texts that mean the same thing but share no
words will not land close together. That is a deliberate placeholder, because
the store has to work with no API key and no cost, and swapping the provider
must not require touching the callers. Treat semantic search quality as
unmeasured until a real model is behind the provider.

A real model can be behind it WITHOUT touching the callers: point
``IKIGAI_EMBEDDING_PROVIDER=openai`` at any OpenAI-compatible ``/embeddings``
endpoint and the vectors become real ones. The provider is selected by the
environment, and the dimension it must return is the one the column was
declared with — ``EMBEDDING_DIM``, 1536.

Two rules the retrieval layer depends on, and that were broken while it was
being built:

- **The vector is written with the artifact, in the same transaction.** A row
  with a body and no vector is a row the semantic index cannot see, and a
  search that silently returns nothing is the worst kind of bug: it reports
  "there is no such thing" about something the store holds.
- **The query is embedded by the SAME provider that wrote the rows.** A query
  vector from another model lands in another space, and the cosine distance
  between two spaces is a number, not a meaning.

Both are enforced by the service layer, which is the layer that owns the
policy. The data layer only stores and compares vectors.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import math
import os
import re
from collections.abc import Awaitable, Sequence
from typing import Any, Protocol

from src.contracts.store import EMBEDDING_DIM

__all__ = [
    "EmbeddingProvider",
    "EmbeddingService",
    "OpenAICompatibleProvider",
    "artifact_text",
    "local_embedding",
    "provider_from_env",
    "text_for",
]

_TOKEN_RE = re.compile(r"[0-9a-z]+")
_HASHES_PER_TOKEN = 3

PROVIDER_ENV = "IKIGAI_EMBEDDING_PROVIDER"
BASE_URL_ENV = "IKIGAI_EMBEDDING_BASE_URL"
MODEL_ENV = "IKIGAI_EMBEDDING_MODEL"
API_KEY_ENV = "IKIGAI_EMBEDDING_API_KEY"
DIM_ENV = "IKIGAI_EMBEDDING_DIM"

_LOCAL = "local"
_OPENAI = "openai"


class EmbeddingProvider(Protocol):
    """Anything that turns text into a vector of the configured dimension.

    It may be a plain function or a coroutine function, and both are
    legitimate: the local provider is arithmetic, and the remote one is an
    HTTP call. The service awaits the result when it is awaitable.
    """

    def __call__(self, text: str) -> list[float] | Awaitable[list[float]]: ...


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


class OpenAICompatibleProvider:
    """Embeds through an OpenAI-compatible ``/embeddings`` endpoint.

    No SDK: the request is two fields and the response is a list. The point of
    this repository is that no published file imports a model SDK (ADR-037 D7),
    and an HTTP call does not break that rule.

    The endpoint is named by the environment and the key never leaves it.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        *,
        dim: int = EMBEDDING_DIM,
        timeout_s: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._dim = dim
        self._timeout_s = timeout_s

    async def __call__(self, text: str) -> list[float]:
        import httpx

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {"model": self._model, "input": text}
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()

        try:
            vector = body["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(
                f"the embedding endpoint at {self._base_url} did not answer with an "
                f"embedding: {body!r}"
            ) from exc

        values = [float(value) for value in vector]
        if len(values) != self._dim:
            raise ValueError(
                f"the embedding endpoint returned {len(values)} dimensions and the column "
                f"holds {self._dim} (EMBEDDING_DIM): the model and the store disagree, "
                f"and a vector of the wrong width is refused by pgvector"
            )
        return values


def provider_from_env(env: dict[str, str] | None = None) -> EmbeddingProvider:
    """The provider the environment asks for.

    ``local`` is the default and needs nothing. ``openai`` needs a base URL
    and a model; a missing one is a configuration error, and it says so rather
    than silently falling back to the placeholder — a service that quietly
    vectors with the hashing trick while the operator believes it uses a model
    is a lie with a search box.
    """
    source = os.environ if env is None else env
    name = (source.get(PROVIDER_ENV) or _LOCAL).strip().lower()
    dim = int(source.get(DIM_ENV) or EMBEDDING_DIM)

    if name == _LOCAL:

        def provider(text: str) -> list[float]:
            return local_embedding(text, dim)

        return provider

    if name == _OPENAI:
        base_url = (source.get(BASE_URL_ENV) or "").strip()
        model = (source.get(MODEL_ENV) or "").strip()
        api_key = (source.get(API_KEY_ENV) or "").strip()
        missing = [
            variable
            for variable, value in (
                (BASE_URL_ENV, base_url),
                (MODEL_ENV, model),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"{PROVIDER_ENV}=openai needs {', '.join(missing)} in the environment")
        return OpenAICompatibleProvider(base_url, model, api_key, dim=dim)

    raise ValueError(f"unknown {PROVIDER_ENV}: {name!r} (expected {_LOCAL} or {_OPENAI})")


def text_for(title: str, body: str) -> str:
    """The text that represents an artifact in the vector space.

    It is the title and the body, the same pair the full-text index reads, so
    the two ways of finding a thing are grounded in the same words.
    """
    return f"{title}\n{body}".strip()


def artifact_text(artifact: Any) -> str:
    """The text of an artifact — the one the store keeps a vector of."""
    title = getattr(artifact, "title", "") or ""
    body = getattr(artifact, "body", "") or ""
    return text_for(title, body)


class EmbeddingService:
    """Embeds text, caching by content hash so the same text is embedded once."""

    def __init__(
        self,
        client: Any | None = None,
        *,
        dim: int = EMBEDDING_DIM,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        self._client = client
        self._dim = dim
        self._provider: EmbeddingProvider = provider or provider_from_env()
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
        if inspect.isawaitable(vector):
            vector = await vector
        values = list(vector)
        if len(values) != self._dim:
            raise ValueError(
                f"the provider returned {len(values)} dimensions and the column holds "
                f"{self._dim} (EMBEDDING_DIM): the model and the store disagree"
            )
        self._cache[key] = values
        return values

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]

    async def embed_artifact(self, artifact: Any) -> list[float]:
        """The vector of an artifact — the one the store keeps beside it."""
        return await self.embed(artifact_text(artifact))


async def _backfill(limit: int) -> int:
    """Embed the rows the vector index cannot see, and write the vectors.

    The repair for a store that was written before the vectors were — or whose
    provider changed underneath it. It is idempotent: a row that already has a
    vector is not read again.
    """
    from src.data.client import DataClient
    from src.data.repository import ArtifactRepository

    client = DataClient()
    repo = ArtifactRepository(client)
    embeddings = EmbeddingService(client)

    written = 0
    while True:
        rows = await repo.artifacts_without_embedding(limit=limit)
        if not rows:
            break
        for row in rows:
            vector = await embeddings.embed(
                text_for(str(row.get("title") or ""), str(row.get("body") or ""))
            )
            await repo.set_embedding(str(row["uid"]), vector)
            written += 1
        if len(rows) < limit:
            break
    return written


def main(argv: list[str] | None = None) -> int:
    """The embedding maintenance commands.

        python -m src.services.embeddings backfill

    Backfills the rows the semantic index cannot see. Without it, the
    retrieval layer answers "nothing found" about everything that was written
    before the vectors were — a store that holds the prose and cannot be asked
    for it.
    """
    parser = argparse.ArgumentParser(prog="python -m src.services.embeddings")
    sub = parser.add_subparsers(dest="command")
    backfill = sub.add_parser("backfill", help="embed the artifacts that have no vector")
    backfill.add_argument("--limit", type=int, default=500, help="rows per batch")
    args = parser.parse_args(argv)

    if args.command != "backfill":
        parser.print_help()
        return 2

    from src.services.wiring import prepare_runtime

    prepare_runtime()
    written = asyncio.run(_backfill(args.limit))
    print(f"embedded {written} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
