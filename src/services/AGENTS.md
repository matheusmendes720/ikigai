# AGENTS.md — `src/services/`

**Score 11 (9 modules, 100% code, ~2090 LOC) — distinct domain: the only layer a client reaches.** Domain rules with no transport concerns.

## OVERVIEW
`services/` is only layer clients reach (ADR-037 §6 rule 2). The transport in `src/transport/` translates domain intent into MCP tool calls; **nothing below this line knows that MCP exists.** The services hold the rules: validation, versioning, idempotency, the conflict contract — and, since ADR-039, the **vector policy** and the **change feed**.

## WHERE TO LOOK
| Module | Role |
|---|---|
| `artifacts.py` | `ArtifactService` — **the only writer of the store** (ADR-037 D5). |
| `relations.py` | `RelationService` — graph navigation over the artifact edges; bounded and cycle-safe. |
| `embeddings.py` | `EmbeddingService`, `EmbeddingProvider` (Protocol), `local_embedding`, `provider_from_env` — and `python -m src.services.embeddings backfill`. |
| `sync.py` | `VaultSync`, `VaultSource`, `SyncReport`, `default_sources` — ingestion of the vault's markdown; `python -m src.services.sync` runs it. |
| `vault_write.py` | `VaultWrite`, `WriteReport`, `render_artifact` — the write-back, store → markdown (ADR-043); `python -m src.services.vault_write` runs it. |
| `changes.py` | `ChangeFeed`, `ChangeEvent`, `Replay` — the store's own announcements, as domain events. |
| `drafts.py` | `DraftService` — the only writer of `ikig.drafts`. |
| `wiring.py` | `Services`, `build_services()`, `prepare_runtime()` — **the composition root**. It is HERE, not in the transport, so that `transport → services → data` is a grep and not a convention. |
| `__init__.py` | package docstring only. |

## CONVENTIONS
- **`ArtifactService` is the store's single writer.** Clients never touch the database; they call the service, and the service is where the rules live.
- **`expected_revision=None` means create; a stale value means the write is rejected.** The artifact keeps whatever the other client wrote — the service never converts a conflict into an upsert.
- **Payload validation lives in the service, not in the model.** `idempotency_key` and `client_id` must be non-blank and `expected_revision` starts at 1; a violation raises `InvalidPayloadError`.
- **The embedding provider is a pluggable hook.** `EmbeddingProvider` is a `Protocol`; the default is `local_embedding`, a deterministic hashing-trick bag of tokens (3 hashes per token, signed, unit-length). The same text always gives the same vector, on any machine, with no network call, and swapping the provider must not touch the callers. A provider may be a plain function or a coroutine function: the local one is arithmetic, the remote one is an HTTP call.
- **The provider is chosen by the environment** (ADR-039): `IKIGAI_EMBEDDING_PROVIDER` (`local` or `openai`), with the base URL, the model and the key beside it. A provider that is asked for and not configured is an error, never a silent fall back to the placeholder.
- **The default embedding is NOT semantic.** Two texts that mean the same thing but share no words will not land close together. Treat semantic-search quality as unmeasured until a real model is behind the provider.
- **`EmbeddingService` caches by content hash**, so the same text is embedded once; `provider_calls` exists to prove the cache works.
- **The vector is written WITH the artifact, in the same transaction** (ADR-039). The service produces it and hands it to the repository; a row with a body and no vector is a row the semantic index cannot see, and the search that silently finds nothing is worse than one that fails.
- **The query is embedded by the same provider that wrote the rows.** A query vector from another model lands in another space, where the cosine distance between two spaces is a number, not a meaning. The repository takes the vector as an argument; it never computes one.
- **The store announces its own changes** (ADR-039). The trigger raises `ikig_artifact_events`; `ChangeFeed` turns the announcement into a `ChangeEvent`; the transport forwards it. The SQL lives in the data layer, and the channel name lives in ONE place per side — the test compares them. `Replay` holds the floor and the `lost` count: a client that reconnects asks for the events after its last sequence, and is told how many it missed.
- **Traversal is bounded and cycle-safe.** `RelationService.traverse` keeps a `seen` set of UIDs, so a graph that points back at itself terminates.
- **`VaultSync` is idempotent and read-only.** The idempotency key is the vault path plus the content hash, so an unchanged file is recognised as already ingested. Nothing under `vault/` is written, moved or deleted (ADR-012).
- **Four vault tree shapes are ingested**: `closing` (`closing-2026/<quarter>/<kind>/`), `persona` (`dreams/`, `objectives/`, `projects/`, `ikigai_state/`, `deliverables/`), `zones` and `escrita`. Which shape applies is decided by the file, not by the order of the sources; `IKIGAI_VAULT_ROOTS` spells the root as `<path>=<layout>` (`=`, not `:`, because Windows paths carry colons).
- **The write-back is the mirror image, and it is narrow** (ADR-043). `VaultWrite` renders an artifact to markdown under `IKIGAI_VAULT_WRITE_ROOTS` — new files only, an edited file is a recorded conflict, never a last-write-wins — and it refuses to write inside the repository's own `vault/` (the deploy discards it with `git reset --hard`) and refuses more than one write root.
- **The render is a pure function of stable fields** — no clock, no timestamp in the file body — so the same artifact always renders to the same bytes and the same hash.
- **Timestamps are always timezone-aware UTC**; a declared frontmatter date is a fact, the clock only a fallback. Files the writer writes use LF (`newline="\n"`) so the hashes are machine-independent.
- **A declared `ueid` in frontmatter wins** over any derived identity — it is the identity the rest of the system already links to, and it survives a move between the two trees.
- **One bad file must not stop the run.** Validation and upsert failures are caught per file and recorded in `SyncReport.skipped`; `README.md` files and `99-archive/` are skipped as scaffolding.

## ANTI-PATTERNS
- **Never add a second writer of the store.** `ArtifactService.upsert` is the only sanctioned write path; `src/data/repository.py` is called from here and nowhere else.
- **Never let a service import the transport.** The dependency runs `transport → services → data → contracts`; a back-reference inverts it.
- **Never let the data layer import the service layer.** It happened once: the repository embedded the query by importing `src.services.embeddings` from inside a function. The vector now arrives as an argument.
- **Never swallow a `ConflictError`.** A conflict means "reread and reapply" — it is a normal outcome the caller must see, not an error to retry blindly.
- **Never make `VaultSync` write.** It reads the vault and upserts into the store; the vault stays append-only prose.
- **Never change `EMBEDDING_DIM` alone.** An HNSW index is built for exactly one dimension (`src/contracts/store.py`); changing it needs a new column, a backfill, an index swap and a migration.
- **Never fall back to the placeholder embedding silently.** A provider that is asked for and not configured is an error — the placeholder is "a lie with a search box"; and never embed the query in another space than the rows'.
- **Never let the write-back touch the repository's `vault/`, push to git, or stage a file it did not write.** The deploy discards that tree; a push from a writer is an unreviewed change to the owner's prose.

## NOTES
- The store's contract surface is `src/contracts/dom.py` (the ten kinds), `dom_kinds.py` (the typed subclasses) and `store.py` (domain, dimension, kind→table map).
- The ingestion has a command: `python -m src.services.sync`. The skill used to say "run the ingestion" and named nothing to run.
- The vector index has a repair: `python -m src.services.embeddings backfill`.
