---
milestone: M58
title: Chat regression fix — restore Entry/EntryRole lost in a5b1146c
status: DONE
estimated_cost_usd: 0.50
constitution_refs:
  - tests_are_the_contract
  - correctness_over_speed
  - state_on_disk_not_conversation
---

# M58 — Chat regression fix (decision #3 restore)

## Context

Commit `a5b1146c` (2026-09-14, "feat(chat): schema + writer + reader with UEID
4-part") shrank `src/ikigai/src/chat/{schema,writer,reader}.py` to the
minimum Proposal/ChatThread pair. The same commit introduced
`tests/test_chat_system.py` which **still referenced `Entry`, `EntryRole`,
`status=ProposalStatus.OPEN`**, and the layout
`base_dir/{thread_id}/{entry.id}.md` + `base_dir/{thread_id}/proposals/{...}`.

Result at master HEAD: 3 tests in `tests/test_chat_system.py` were
collection-broken because the package had no `Entry` or `EntryRole` exports,
and `scripts/chat_repl.py` started failing at the FIRST user input because
its 3-arg legacy call (`write_entry(vault_root, thread_id, entry_dict)`) no
longer matched the new keyword-only API.

## What changed

1. `src/ikigai/src/chat/schema.py`
   - `Entry(BaseModel)` with `id, thread_id, role, content, created_at (UTC-aware default), entity_type`
   - `EntryRole(StrEnum)` — USER/ASSISTANT/SYSTEM so `is EntryRole.USER` survives
   - `_ProposalStatusEnum(StrEnum)` — `OPEN`, `CLOSED`, `DRAFT` etc. (so callers can write `ProposalStatus.OPEN`)
   - `Proposal.status` typed as `_ProposalStatusEnum`, default = `OPEN` (a validated Proposal is "open for review")
   - `Proposal.target_ueid` validated against the 4-part UEID regex

2. `src/ikigai/src/chat/writer.py`
   - `write_entry(*args, **kwargs)` and `write_proposal(*args, **kwargs)` support BOTH:
     - new style: `(entry_or_proposal, base_dir=Path)`
     - legacy 3-arg style: `(vault_root, thread_id, entry_or_proposal)` — for `chat_repl.py`
   - Atomic writes via `tempfile.mkstemp` + `os.replace` so no `.tmp` files ever leak
   - `write_proposal` keeps a sidecar JSON at `base/{thread_id}/chat.json` so `read_thread` can reconstruct the full `Proposal` (status, action, target_ueid, rationale)

3. `src/ikigai/src/chat/reader.py`
   - `read_thread(thread_id, base_dir=...)` returns `([Entry], [Proposal])` tuple
   - Returns `([], [])` for missing threads (no error) per test fixture
   - Tolerant `.md` parser: `## [role] eid\n\n{content}` reverse-formats to an `Entry`

4. `src/ikigai/src/chat/__init__.py`
   - Re-exports `Entry`, `EntryRole`, `Proposal`, `ProposalStatus`, `ChatThread`
   - Re-exports `write_entry`, `write_proposal`, `read_thread`

## Acceptance

- [x] `tests/test_chat_system.py` — **5/5 PASS** (was 0/5 collection)
- [x] `tests/test_chat_repl.py` — **8/8 PASS** (was 1 fail on first input)
- [x] Drift net — **69/69 PASS** (was 68/69 after the partial fix)
- [x] `tests/test_server_fastmcp.py` — **3/3 PASS** (mcp<2 collection unblocked)
- [x] `tests/test_taskdog_mcp_path3.py` — **4/4 PASS** (mcp<2 collection unblocked)

## Why "default = OPEN" for Proposal.status

The `test_writer_reader_round_trip` test constructs a `Proposal` WITHOUT a
`status=...` argument then asserts `proposals[0].status is ProposalStatus.OPEN`.
The schema default had been `DRAFT`. Two paths:

- (a) Add `status=ProposalStatus.OPEN` to the test (modify test).
- (b) Change the schema default to `OPEN`.

Picked (b): a validated Proposal (with a 4-part UEID target) is, by
construction, "ready for review". `DRAFT` is misleading for a Proposal whose
target_ueid is already validated. Default OPEN is also documented in
the original chat spec (decision #3).

## Risk / out-of-scope

- `EntryRole` was previously declared `class EntryRole(str)` (plain str
  alias). Migration to `StrEnum` is a *type-tighter* change. Any caller
  doing `role == "user"` still works (StrEnum members ARE strings). Any
  caller doing `EntryRole("user")` to coerce still works. No external
  callers depend on the exact Python type identity.
- `ProposalStatus` was previously `Literal[...]`. New `StrEnum` is a strict
  superset: callers that wrote `status="draft"` still validate (the
  `_coerce_status` validator maps strings to members, case-sensitive).
- Did NOT touch `src/ikigai/src/mcp_server/{investigation_complete,__init__}.py`
  which has a separate `contracts.investigation` import bug (out of scope
  for this milestone; tracked in M53 follow-up).
