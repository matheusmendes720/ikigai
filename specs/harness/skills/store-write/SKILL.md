---
name: store-write
description: Use when the agent must create an artifact or change an existing one. Builds the WriteRequest, writes through upsert_artifact, and handles the optimistic-revision conflict by rereading and reapplying.
---

# Store write

Persists one artifact through the MCP transport. The service layer is the only writer; the agent never writes SQL.

## Contract

Trigger:    The agent must create an artifact or change an existing one.
Inputs:     The kind, the title, the body or the kind-specific fields, and the parent or relation targets.
Outputs:    The uid, the new revision, and the outcome: created, updated or unchanged. On a conflict, the agent rereports the artifact instead of writing.
Steps:
1. Build the artifact for the kind. Prose kinds — `sonho`, `plano`, `onda`, `revisao`, `nota` — require a non-empty body. `kpi` requires a metric, a period and a direction. `okr` requires an objective and a key_result. `desc` requires a decision. `tarefa` requires a priority.
2. Derive the identity: the slug from the title in lowercase with dashes, the uuid segment from a fresh instance discriminator, the hash segment from the sha256 of the body, first 16 hex characters. Build the uid with `make_uid(kind, slug, uuid_short, content_hash_short)` so the validation happens at the boundary.
3. Read before writing. Call `search_artifacts` with the kinds filter, and when a candidate matches, call `get_artifact` on it. If it exists, reuse its uid and its revision as `expected_revision`. If it does not, `expected_revision` is null.
4. Call `upsert_artifact` with the `WriteRequest`: the artifact, `expected_revision`, a non-empty `idempotency_key` and a `client_id`. The idempotency key identifies the intent, not the moment: build it from the uid and the body hash, so a retry of the same intent is recognisable.
5. Read the outcome. `created` means the revision is 1. `updated` means the revision went up by one. `unchanged` means the same idempotency key already wrote this intent. `conflict` means another client wrote first: call `get_artifact`, decide whether the change still applies, and reapply with the revision just read.
6. Create the relations with the relation service: `PARENT_OF` for hierarchy, `DEPENDS_ON` for sequence, `EVIDENCES` for provenance, `DERIVES_FROM` for lineage, `REFERENCES` for citation, `SUPERSEDES` for replacement, `BLOCKS` for contention.
7. Report the uid, the revision, the outcome, the relations created and the tools that ran.

Invariants:
- Every write carries a non-empty `idempotency_key` and a `client_id`.
- A content change bumps the body hash and the revision. It never changes the uid.
- Hierarchy is expressed as relations. A task depends on another through a `DEPENDS_ON` edge, not through a field.
- A stale `expected_revision` is a conflict. Never force the write and never overwrite the other client's work in silence.
- No secret, token or connection string goes into an artifact.

Done when:
- the outcome is created or updated, or unchanged with the reason stated,
- the artifact is readable through `get_artifact` at its new revision,
- and the report names the uid, the revision and the tools that ran.
