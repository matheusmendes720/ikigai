---
name: vault-sync
description: Use when markdown under vault/ changed or a store-backed read returns content behind the prose. Ingests the markdown trees into the store, idempotently, one direction only.
---

# Vault sync

Ingests the markdown trees under `vault/` into the store. The direction is one way: markdown into the store. The agent never writes markdown.

## Conceptual source

`strategics/` holds the conceptual material, but the prose itself is the input. The vault stays prose; the store holds the structured form, and the store wins on structured fields.

## Contract

Trigger:    Markdown under `vault/` changed, or a store-backed read returns content that is behind the prose.
Inputs:    The vault trees declared in `src/services/sync.py`, the store connection, and the write requests built from the markdown.
Outputs:   A report with the counts of scanned, created, updated, unchanged and skipped, and every skipped file with its reason.
Steps:
1. Read the design first: `specs/data-layer/TECH.md`, then `src/services/sync.py` for the mapping.
2. Confirm the store is reachable. The variable name is in `src/contracts/store.py`. A missing variable is a configuration error, not a reason to fall back to local state.
3. Run the ingestion. It reads the trees from `default_sources()`, skips README files, locates the kind and the quarter from the layout, computes the body hash and compares it with the stored revision.
   Two layouts exist. The closing layout is `<quarter>/<kind>/<file>.md`, where the quarter directory sits in front of the kind directory. The persona layout is flat, one directory per tier: dreams, objectives, projects, ikigai_state, deliverables.
4. Write through `src/services/artifacts.py` into `src/data/repository.py`. Every write carries an idempotency key, a `client_id` and the expected revision. The idempotency key is built from the layout, the relative path and the body hash, so an unchanged file is recognised as already ingested.
5. Report the counters and every skipped file with its reason.

Invariants:
- The ingestion is idempotent. Running it twice creates no duplicate and does not rewrite what did not change.
- Artifact identity comes from the location. A content change bumps `body_hash` and `revision` and never changes the uid.
- A file that declares its own `ueid` in the frontmatter keeps that identity.
- A stale `expected_revision` is a conflict and returns to the caller. Never force the write.
- One failing file does not abort the batch. It lands in skipped with its reason.
- The ingestion never writes, moves or deletes anything under `vault/`.

Done when:
- the report shows zero unexpected failures,
- a second run reports unchanged for the same tree,
- and every skipped file has a stated reason.
