# ADR-039 — The websocket sync channel, and the retrieval layer that feeds it

**Status:** Accepted
**Date:** 2026-11-08
**Deciders:** human (Matheus) + agent
**Scope:** whether the canonical service grows a second transport, and whether the vector index is fed
**Anchor:** [ADR-037](./ADR-037-data-layer-canonical-turn.md) · [ADR-011](./ADR-011-ikigai-mcp-http-sse-transport.md)

> **ADR-038 is reserved.** `deploy/README.md` records that the trigger for the
> second `client_id` — the one that would make the row-level isolation real —
> is written in ADR-038. That number belongs to that decision, so this one
> takes the next: ADR-039. The numbering is sequential and append-only
> (`code-docs/adr/README.md` §"Numbering").

---

## Status

**Accepted.** The websocket is a second way to reach the same six tools, and
a channel for the changes the store announces. The MCP transport is untouched:
still six tools, still the harness's way in, still the only place a client
writes through.

---

## Context

ADR-037 renewed the scope into one store, one transport, one client, one
external harness. That architecture is right, and this ADR does not change it.
It closes two gaps that the renewed scope left open, both of which are
measured, not suspected.

### 1. The vector index was never fed

The store had everything a semantic retrieval layer needs:

- `ikig.artifacts.embedding vector(1536)` (`0002_indexes.sql:18`),
- an HNSW index over it (`0002_indexes.sql:19`),
- a search that compares vectors (`src/data/repository.py:421`).

And nothing ever wrote a vector. `set_embedding` existed in the repository
(`src/data/repository.py:449`) and **no caller reached it** — the only
producers of embeddings were the `embed_text` tool, which returns a vector to
the caller and stores nothing, and `_embed_for_search`, which embedded the
*query* with a hardcoded local function.

So `ikig.artifacts.embedding` was NULL for every row, and the semantic search
filtered on `embedding is not null`. It answered **nothing found, about
everything, silently**. The retrieval layer existed on paper and returned
zero rows in practice.

The cause was structural: the repository embedded the query by importing the
service layer (`from src.services.embeddings import local_embedding` inside
`_embed_for_search`) — a layering inversion — and the write path had no place
where a vector was produced. The query was embedded somewhere the write was
not, which is why one half of the retrieval layer worked (a query vector was
computed) and the other half never existed (nothing to compare it against).

### 2. The writers are in different processes

The canonical deployment has four roles, and they are not one process:

| Role | Writes? | Knows about the others' writes? |
|---|---|---|
| `api` (MCP over HTTP) | yes, through the tools | no |
| `bot` (Telegram) | yes, through the tools | no |
| `sync` (the vault ingestion) | yes, directly through the service layer | no |
| `ws` (this ADR) | no | — |

MCP is request/response. A client asks, the server answers, and the
connection carries nothing else. That is the right shape for a harness that
drives the store, and the wrong shape for a client that has to **stay in
sync** with writers it cannot see. The Telegram bot would learn about its own
writes and nothing else — while the vault ingestion, running in its own
container, changed the very prose the bot reads through the store.

### 3. The vault was a copy, not a volume

`deploy/Dockerfile:64` copies the vault into the image. A container that only
sees that copy knows the prose of the commit it was built from, not the prose
of now — and the ingestion had no runnable command at all: the `vault-sync`
skill says "run the ingestion" and named nothing to run.

---

## Decision

### 1. The vector is written with the artifact, in the same transaction

The **service layer** produces the vector and hands it to the repository,
which writes it in the same statement as the row:

```text
ArtifactService.upsert(req)
  → EmbeddingService.embed_artifact(artifact)   # the provider, chosen by the environment
  → ArtifactRepository.upsert(req, embedding=…)  # one statement, one transaction
```

The query is embedded by the **same** service, with the same provider:

```text
ArtifactService.search(query)
  → EmbeddingService.embed(query.text)   # only when query.semantic
  → ArtifactRepository.search(query, embedding=…)
```

The repository no longer imports the service layer. The layering inversion is
gone, and with it the reason the two halves of the retrieval layer could
disagree.

The provider is chosen by the environment, and the default still needs
nothing:

| Variable | Meaning |
|---|---|
| `IKIGAI_EMBEDDING_PROVIDER` | `local` (default) or `openai` |
| `IKIGAI_EMBEDDING_BASE_URL` | an OpenAI-compatible `/embeddings` endpoint |
| `IKIGAI_EMBEDDING_MODEL` | the model name |
| `IKIGAI_EMBEDDING_API_KEY` | the key (never in the repo) |
| `IKIGAI_EMBEDDING_DIM` | the width; must equal `EMBEDDING_DIM` |

No SDK: the call is two fields in and a list out, and no published file
imports a model SDK (ADR-037 D7 holds).

Rows written before this ADR have no vector. `python -m src.services.embeddings
backfill` embeds them — the repair for a store that was written while the
index was empty.

### 2. The store announces its own changes

A trigger on `ikig.artifacts` announces the uid and the operation on the
channel `ikig_artifact_events` (`0004_artifact_events.sql`). The data layer
listens on a dedicated connection — LISTEN cannot share the pool, because a
notification arrives on the connection that asked for it. The service layer
(`src/services/changes.py`) turns the announcement into a domain event; the
transport forwards it.

This is what makes the channel a sync and not a mirror: the ingestion writes
in its own container, and its writes reach the clients.

### 3. The websocket is a SEPARATE surface, on its own port

`src/transport/ws_server.py` serves:

- `WS /sync` — the channel,
- `GET /healthz` — the data-plane probe, the same one the api uses.

Its tool registry is built **from the MCP server**: it asks the MCP server
which tools exist and takes the functions from the same module the MCP server
registers. The two surfaces therefore cannot drift, and the test holds them
equal.

The wire protocol is four frames:

```jsonc
→ {"type": "call",   "id": "…", "tool": "search_artifacts", "arguments": {…}}
← {"type": "result", "id": "…", "ok": true,  "data": {…}}
← {"type": "result", "id": "…", "ok": false, "error": {"code": "conflict", …}}
← {"type": "event",  "event": "artifact.update", "data": {"uid": "…", "op": "UPDATE"}}
```

One kind of answer to a request, with the outcome in `ok`. The error codes
are the service's own — a conflict over the websocket means "reread", exactly
as it does over MCP.

The channel is a **write path**, so it fails closed: without
`IKIGAI_WS_TOKEN` the server refuses to start, unless
`IKIGAI_WS_ALLOW_ANONYMOUS=1` is set explicitly.

### 4. The vault is a volume, and the ingestion is a command

`deploy/compose.yml` mounts `./vault:/app/vault:ro` into the ingestion, and
`python -m src.services.sync --interval 60` runs it on a timer. The trees it
reads are named by the environment (`IKIGAI_VAULT_ROOTS`, `path=layout`), so
a container reads the prose where the deployment put it.

The vault stays read-only: the ingestion reads it and never writes it.

---

## Consequences

### Positive

- **The retrieval layer works.** Semantic search returns rows, because rows
  have vectors.
- **The clients are in sync.** A write made by the ingestion reaches the
  Telegram bot, which forwards it to the owner.
- **The prose is live.** The volume carries the prose of now, not the prose of
  the build.
- **One tool vocabulary.** The websocket exposes the six, built from the MCP
  server itself.
- **The deployment is reproducible.** CI builds the image, pushes it to
  GHCR, and the server runs THAT image.

### Negative

- **A second surface to keep.** The websocket is a protocol; it has to stay
  in step with the tools it exposes. The registry is built from the MCP
  server to make that automatic, and the test holds it equal.
- **Another port.** 8001, bound to the loopback on the host, reachable by the
  other containers on the compose network.
- **A token to manage.** `IKIGAI_WS_TOKEN` is another secret in `.env`.
- **The store now announces itself.** A trigger fires on every write; on a
  hot store that is a real cost.

### Neutral

- **The MCP transport is unchanged.** Six tools, the same functions, the same
  harness contract (`.pi/mcp.json`).
- **The bot keeps both transports.** `IKIGAI_WS_URL` decides; the MCP call
  still works on its own.

---

## Alternatives Considered

### A1 — WebSocket transport for the MCP server itself (rejected)

**Rejected because.** The MCP server's transport is chosen by
`IKIGAI_MCP_TRANSPORT` and the harness reads `.pi/mcp.json`, which speaks
MCP over HTTP. Replacing it with a bespoke websocket would break the harness
contract and the six-tool surface ADR-037 D6 binds. A separate surface costs
a port and not a contract.

### A2 — SSE instead of a websocket (rejected)

**Rejected because.** SSE is one-way. The channel needs the client to call
tools as well as to receive events, and a websocket carries both on one
connection.

### A3 — Polling instead of LISTEN/NOTIFY (rejected)

**Rejected because.** Polling asks "what changed?" every N seconds and
answers with a watermark; it misses a write that lands between two polls,
and it makes every client a reader of the whole table. The store already
knows what it wrote, and it says so.

### A4 — The webhook as a seventh MCP tool (rejected)

**Rejected because.** ADR-037 D6 binds the surface to six tools and the
drift test holds the set. A push channel is not a tool: it has no arguments
and no result, it is a stream. Putting it in the tool surface would bend
the rule that a tool expresses one domain intent.

### A5 — Keep the vault baked into the image (rejected)

**Rejected because.** The image is built on a commit; the vault is edited
between commits. A container that only sees the copy cannot see the change
until it is rebuilt — and the retrieval layer answers from a stale memory
while the vault says otherwise.

### A6 — A3 in ADR-011 rejected the websocket (superseded)

ADR-011 (2026-08-27) rejected a websocket transport for the pre-pivot
runtime, because "one-way streaming is sufficient" there. That was a
statement about a harness driving a store over MCP, and it was right for its
subject. ADR-037 retired that runtime. The canonical service has writers in
separate processes, so one-way is not sufficient — and the websocket is a
**separate** surface, which is what ADR-011's alternative was about.

---

## Implementation Rules

1. **The websocket exposes the six tools, built from the MCP server.** A
   tool added to one is in the other; a tool that exists in the list but not
   in the module is a startup error.
2. **A write over the websocket is a write over MCP.** The same service
   layer, the same revision guard, the same idempotency key.
3. **The transport holds no SQL.** The test greps the tool surfaces.
4. **The vector is written with the row.** One statement, one transaction.
5. **The query is embedded by the provider that wrote the rows.** The service
   layer owns both.
6. **The channel fails closed.** No token, no start.
7. **The vault is never written from code.** The volume is mounted read-only.
8. **The change channel is named in one place per side**, and the test
   compares them.
9. **The drift net grows; it does not shrink.** The new guards are added
   beside the old ones.

---

## Roll-back Criteria

Every part is reversible on its own:

- The websocket is opt-in for a client (`IKIGAI_WS_URL`); unset it and the
  bot uses MCP alone.
- The server is a separate container; remove it from the compose and nothing
  else changes.
- The trigger is a migration with a reverse script; `down` removes it.
- The vector write is one statement; removing it leaves the store as it was
  (and the semantic index empty, which is the bug this ADR fixes).

---

## Related Decisions

- **ADR-037** — the canonical turn this ADR lives inside: one store, one
  transport, one client, an external harness.
- **ADR-011** — the MCP transport decision, and the websocket rejection this
  ADR supersedes for the canonical service.
- **ADR-013** — the canonical scope discipline: the layering the embedding
  change repairs.
- **ADR-014 / ADR-033** — the UEID pattern, defined once.

---

## Notes

- The measured facts behind this ADR (2026-11-08): `set_embedding` had no
  caller; `ikig.artifacts.embedding` was NULL for every row; the semantic
  search filtered on `embedding is not null` and therefore returned zero
  rows; `src/transport/` contained no websocket, no FastAPI and no uvicorn;
  `deploy/compose.yml` baked the vault into the image and named no ingestion
  command; `.github/workflows/ci.yml` had no build and no deploy job.
- The image is `ghcr.io/matheusmendes720/ikigai`, built by CI and deployed
  over SSH. `IKIGAI_IMAGE` names the tag a deployment runs.

---

*ADR-039 — Accepted — 2026-11-08 — the websocket sync channel and the retrieval layer that feeds it*
