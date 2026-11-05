# AGENTS.md — `src/services/`

**Score 8 (6 modules, 100% code, ~990 LOC, 9 public names) — created: distinct domain (the only layer a client reaches).** Domain rules with no transport concerns.

## OVERVIEW
`services/` is the only layer clients reach (ADR-037 §6 rule 2). The transport in `src/transport/` translates domain intent into MCP tool calls; **nothing below this line knows that MCP exists.** The services hold the rules: validation, versioning, idempotency, the conflict contract.

## WHERE TO LOOK
| Module | Role |
|---|---|
| `artifacts.py` | `ArtifactService` — **the only writer of the store** (ADR-037 D5). |
| `relations.py` | `RelationService` — graph navigation over the artifact edges; bounded and cycle-safe. |
| `embeddings.py` | `EmbeddingService`, `EmbeddingProvider` (Protocol), `local_embedding`. |
| `sync.py` | `VaultSync`, `VaultSource`, `SyncReport`, `default_sources` — ingestion of the vault's markdown. |
| `wiring.py` | `Services`, `build_services()` — **the composition root**. It is HERE, not in the transport, so that `transport → services → data` is a grep and not a convention. |
| `__init__.py` | package docstring only. |

## CONVENTIONS
- **`ArtifactService` is the store's single writer.** Clients never touch the database; they call the service, and the service is where the rules live.
- **`expected_revision=None` means create; a stale value means the write is rejected.** The artifact keeps whatever the other client wrote — the service never converts a conflict into an upsert.
- **Payload validation lives in the service, not in the model.** `idempotency_key` and `client_id` must be non-blank and `expected_revision` starts at 1; a violation raises `InvalidPayloadError`.
- **The embedding provider is a pluggable hook.** `EmbeddingProvider` is a `Protocol`; the default is `local_embedding`, a deterministic hashing-trick bag of tokens (3 hashes per token, signed, unit-length). The same text always gives the same vector, on any machine, with no network call, and swapping the provider must not touch the callers.
- **The default embedding is NOT semantic.** Two texts that mean the same thing but share no words will not land close together. Treat semantic-search quality as unmeasured until a real model is behind the provider.
- **`EmbeddingService` caches by content hash**, so the same text is embedded once; `provider_calls` exists to prove the cache works.
- **Traversal is bounded and cycle-safe.** `RelationService.traverse` keeps a `seen` set of UIDs, so a graph that points back at itself terminates.
- **`VaultSync` is idempotent and read-only.** The idempotency key is the vault path plus the content hash, so an unchanged file is recognised as already ingested. Nothing under `vault/` is written, moved or deleted (ADR-012).
- **Two vault tree shapes are ingested**: `closing` (`closing-2026/<quarter>/<kind>/`) and `persona` (`dreams/`, `objectives/`, `projects/`, `ikigai_state/`, `deliverables/`). Which shape applies is decided by the file, not by the order of the sources.
- **A declared `ueid` in frontmatter wins** over any derived identity — it is the identity the rest of the system already links to, and it survives a move between the two trees.
- **One bad file must not stop the run.** Validation and upsert failures are caught per file and recorded in `SyncReport.skipped`; `README.md` files and `99-archive/` are skipped as scaffolding.

## ANTI-PATTERNS
- **Never add a second writer of the store.** `ArtifactService.upsert` is the only sanctioned write path; `src/data/repository.py` is called from here and nowhere else.
- **Never let a service import the transport.** The dependency runs `transport → services → data → contracts`; a back-reference inverts it.
- **Never swallow a `ConflictError`.** A conflict means "reread and reapply" — it is a normal outcome the caller must see, not an error to retry blindly.
- **Never make `VaultSync` write.** It reads the vault and upserts into the store; the vault stays append-only prose.
- **Never change `EMBEDDING_DIM` alone.** An HNSW index is built for exactly one dimension (`src/contracts/store.py`); changing it needs a new column, a backfill, an index swap and a migration.

## NOTES
- The store's contract surface is `src/contracts/dom.py` (the ten kinds), `dom_kinds.py` (the typed subclasses) and `store.py` (domain, dimension, kind→table map).
