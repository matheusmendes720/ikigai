# Skill Specs - usability routines for the canonical serverless scope

**Status:** specification (2026-11-01)
**Scope:** executable contracts for the routines a cloud agent performs on the published repository.
**Anchor:** [ADR-037](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md)
**Companion:** [SYSTEM-PROMPTS.md](./SYSTEM-PROMPTS.md)

A skill here is a contract, not a suggestion. Each one names the trigger, the
inputs, the exact output, the steps, the invariants it protects, and the check
that tells you the skill is finished.

Format of every spec below:

```
### <skill-id>
Trigger:    when the agent runs it
Inputs:     what it consumes
Outputs:    what it delivers
Steps:      numbered, executable
Invariants: what it must never break
Done when:  the observable check that ends the skill
```

Rules shared by every skill:

- The published repository is the canonical system. A cloud clone is a working copy, not the owner's desktop.
- No step writes a fork slice file by hand. Cross-fork writes go through the review queue.
- No step edits or deletes a file under `vault/`. The vault is append-only.
- Every skill ends by reporting the commands it ran and their result.

Path note: every path in this document that sits under data/ is runtime state. It
is created on demand and is gitignored on purpose, so it never shows up in
`git ls-files`. Every other path named here is a tracked repository file.

---

## Index

| # | Skill | Trigger | Primary surface |
|---|-------|---------|-----------------|
| 1 | `mesh-task-add` | Owner asks for a new task | `interfaces/cli/`, `src/mesh/` |
| 2 | `mesh-task-show` | Owner asks about one task across forks | `src/mesh/` |
| 3 | `mesh-task-propagate` | A queued change needs to reach the second fork | `src/mesh/` |
| 4 | `weekly-review` | Weekly cycle, plan vs actual | `life/`, `src/mesh/`, `vault/` |
| 5 | `vault-note-append` | A decision or report must be persisted | `sys_ikigai/vault/` |
| 6 | `data-layer-store-sync` | Vault content changed, store is behind | `src/services/`, `src/data/` |
| 7 | `contract-change-drift-test` | A contract or an invariant changed | `src/contracts/`, drift net |
| 8 | `ci-green-gate` | Before a push or a release | `.github/` |

---

### mesh-task-add

```
Trigger:    The owner asks for a task to exist and to be visible in both forks.
Inputs:     A title (required), an optional due date, an optional priority.
Outputs:    The UEID of the created task, the queue event id, the decision
            returned by the consumer, and the worker counters.
Steps:
1. Run the CLI producer command:
   python -m interfaces.cli task-add --title "<title>" --due YYYY-MM-DD --priority P
   The command writes the CLI fork slice through src/mesh/adapters/cli.py and
   enqueues a TaskChange in data/review_queue/. It prints the UEID.
2. Read the decision produced by src/mesh/agent_consumer.py:
   approve, reject or clarify, with the reason.
3. Drain the queue once:
   python -m src.mesh.review_queue_worker run-once
   It prints consumed, approved, rejected, clarified and partial counts.
4. Read the joined view:
   python -m src.mesh.mesh_cli show <ueid>
5. Report the UEID, the decision, the counters and the slice state.
Invariants:
- The UEID comes from src/contracts/common.py. Never hand-build an identifier.
- The producer never writes to the vault and never writes the taskdog fork
  directly. Only the worker propagates.
- A rejected or clarified create stays in the queue with its reason. Do not
  re-enqueue a copy of the same event.
- The vault is untouched by this skill.
Done when:
- The task is visible in the CLI fork slice,
- the event is no longer pending in data/review_queue/,
- `python -m src.mesh.mesh_cli show <ueid>` prints both slices or states clearly
  that the second fork has no slice yet,
- and the report names the UEID and the decision.
```

### mesh-task-show

```
Trigger:    The owner asks what state one task is in, across forks.
Inputs:     A UEID.
Outputs:    A joined view of the task: CLI slice, taskdog slice, queue events and
            the taskdog note and dependency edges when they exist.
Steps:
1. Run the cross-fork view:
   python -m src.mesh.mesh_cli show <ueid>
2. When the joined view is not enough, read each fork directly:
   python -m src.mesh.cli_cli show <ueid>
   python -m src.mesh.taskdog_cli show <ueid>
3. List the related queue events:
   python -m src.mesh.review_queue_cli list
   python -m src.mesh.review_queue_cli show <event_id>
4. Read the note and the dependency edges when the owner asks about them:
   python -m src.mesh.taskdog_cli note show <ueid>
   python -m src.mesh.taskdog_cli dep list <ueid>
5. Report the fields that differ between the forks first, then the fields that agree.
Invariants:
- This skill is read-only. It writes no slice, no queue file and no vault note.
- A slice that is missing in one fork is reported as missing. It is not
  recreated from the other fork.
- The UEID format is defined once, in src/contracts/common.py, and enforced by
  code-docs/adr/ADR-014-ueid-canonical-format.md.
Done when:
- Every requested field is reported with its source fork,
- or the skill reports that the UEID exists in no fork, with the command output
  that shows it.
```

### mesh-task-propagate

```
Trigger:    The review queue holds events, and the owner wants them applied to the
            second fork.
Inputs:    The pending events in data/review_queue/.
Outputs:   One line per event with its decision and its propagation result, plus
            the worker counters.
Steps:
1. Inspect the queue before draining it:
   python -m src.mesh.review_queue_cli status
   python -m src.mesh.review_queue_cli list
2. Drain the queue once:
   python -m src.mesh.review_queue_worker run-once
   The worker consumes pending events, validates them through
   src/mesh/agent_consumer.py and applies the approved ones through
   src/mesh/agent_propagator.py.
3. Read the outcome for each event:
   - approve: the event was applied to the forks that support the action.
   - reject: the event stays unapplied and keeps its reason.
   - clarify: the event waits for the owner.
4. Confirm the second fork directly:
   python -m src.mesh.taskdog_cli show <ueid>
5. Report the counters, the per-event decision and any partial propagation.
Invariants:
- Only approved events reach a fork. The worker never applies a rejected or
  clarified event.
- A partial propagation is acked as partial and is not retried automatically.
  Report it, do not loop on it.
- The UEID collision check is create-only. A create that collides with an
  existing task carrying different content is rejected.
- No step writes to the vault unless the event source fork is the vault.
Done when:
- `python -m src.mesh.review_queue_cli status` shows no pending event left from
  the drained batch,
- every approved event is visible in the second fork,
- and every non-applied event is reported with its reason.
```

### weekly-review

```
Trigger:    The weekly cycle runs, or the owner asks how the plan compares to reality.
Inputs:     The current plan, the mesh state, the append-only feedback log, and the
            review script configured for this installation.
Outputs:    A review note under vault/ikigai/closing-2026/ in the weekly review
            folder of the current quarter, plus the JSON summary of the run.
Steps:
1. Run the pipeline:
   python -m life.cli weekly run --json
   life/handlers/weekly.py drives the task central in life/centrals/task.py and
   collects the review and the metrics output.
2. Read the plan state:
   .claude/loop/tasks.md and the current quarter folder under
   vault/ikigai/closing-2026/.
3. Read the actual state from the mesh:
   python -m interfaces.cli list
   python -m interfaces.cli stats
   python -m src.mesh.review_queue_cli status
4. Classify each planned item as done, partly done, not started or dropped, and
   cite the evidence for the classification.
5. Write the review note with the shape of
   vault/ikigai/mock-datasets/04-revisao-semanal_example.md.
6. Append the new state to .claude/loop/tasks.md. Add lines, never rewrite history.
7. Report the note path, the item counts per class and the commands that ran.
Invariants:
- The pipeline runs without an LLM. It is pure arithmetic over state on disk.
- Feedback the owner left on a task lives in data/feedback.jsonl and is
  append-only. Read it, never rewrite it.
- The review note is a new file. The plan note is not edited.
- An item with no evidence stays open.
Done when:
- The review note exists at the expected path and opens with frontmatter,
- every planned item has a class and a piece of evidence,
- and the summary counts match what the commands returned.
```

### vault-note-append

```
Trigger:    A decision, a report or a planning note must be persisted.
Inputs:     The note body, the frontmatter fields, and the target path under vault/.
Outputs:    A new markdown file under vault/ with frontmatter, plus the audit entry
            the writer appends at the vault root.
Steps:
1. Pick the target path:
   - a decision goes to vault/ikigai/decisions/<date>-<slug>.md
   - a report goes to the current quarter folder under vault/ikigai/closing-2026/
   - the quarterly plan for this cycle is at
     vault/ikigai/closing-2026/02-q4-2026/01-plano-trimestral/deep-agent-build-q4-2026.md
   - the change channel template is vault/ikigai/templates/sonho-log.md
2. Build the frontmatter: title, date, status, decision_owner, tags.
3. Write through the sanctioned writer, sys_ikigai/vault/vault_write.py:
   vault_write(vault_root, vault_path, frontmatter_fields, body, actor="agent")
   It locks through sys_ikigai/vault/lock.py, writes atomically and appends the
   audit entry. sys_ikigai/security/vault_write_wrapper.py wraps it for the
   gateway surface.
4. Read the file back with sys_ikigai/vault/vault_read.py and confirm the
   frontmatter and the body.
5. Run the guard tests. They live at src/ikigai/tests/test_vault_write.py,
   src/ikigai/tests/test_vault_write_audit_log.py and
   src/ikigai/tests/test_vault_lock.py. The command runs them from inside
   src/ikigai, so the paths are relative to that directory:
   cd src/ikigai && poetry run pytest tests/test_vault_write.py tests/test_vault_write_audit_log.py tests/test_vault_lock.py
6. Report the path, the actor and the audit result.
Invariants:
- The agent is the only writer of the vault. Interfaces read it and never write it.
- Append only. A new note, never an edit or a deletion of an existing note.
- Frontmatter is mandatory. A note without it is rejected by the drift net.
- No secret, token, key or connection string goes into a note.
- A decision note quotes the owner literally and links the related ADR, for
  example code-docs/adr/ADR-037-data-layer-canonical-turn.md.
Done when:
- The file exists at the target path with valid frontmatter,
- the read-back matches what you wrote,
- the audit log at the vault root records the write with the actor,
- and the guard tests pass.
```

### data-layer-store-sync

```
Trigger:    Vault content changed, or a store-backed read returns content that is
            behind the markdown.
Inputs:    The vault trees listed by src/services/sync.py, the cloud store
            connection, and the write requests built from the markdown.
Outputs:   A sync report with the counts of scanned, created, updated, unchanged
            and skipped files.
Steps:
1. Read the design first: specs/data-layer/TECH.md and
   docs/superpowers/specs/2026-11-01-02-cloud-store.md.
2. Confirm the store is reachable with the environment variable named in
   src/contracts/store.py, IKIGAI_STORE_DSN. A missing variable is a
   configuration error, not a reason to fall back to local state.
3. Run the ingestion in src/services/sync.py. It reads the vault trees from
   default_sources(), skips README files, locates the kind and the quarter from
   the tree layout, computes the body hash and compares it with the stored
   revision.
4. Write through src/services/artifacts.py into src/data/repository.py. Every
   write carries an idempotency key, a client_id and the expected revision.
5. Report the report counters and every skipped file with its reason.
Invariants:
- The ingestion is idempotent. Running it twice creates no duplicate and does
  not rewrite what did not change.
- Artifact identity comes from the location. A content change bumps body_hash
  and revision and never changes the uid.
- A stale expected_revision is a conflict and returns to the caller. Never force
  the write.
- One failing file does not abort the batch. It lands in skipped with its reason.
- No local daemon and no localhost service. The store is Postgres serverless.
Done when:
- The report shows zero unexpected failures,
- a second run reports unchanged for the same tree,
- and every skipped file has a stated reason.
```

### contract-change-drift-test

```
Trigger:    A contract in src/contracts/ changed, or a load-bearing invariant changed.
Inputs:    The contract diff, the drift net, and the affected suites.
Outputs:   The changed invariant, the drift test that covers it, and the test
            results per package.
Steps:
1. Make the smallest contract change. Contracts are Pydantic v2, frozen, with
   extra fields forbidden. Import a model, never redefine it.
2. Keep the UEID pattern in one place, src/contracts/common.py, per
   code-docs/adr/ADR-033-ueid-single-source-mandate.md. Extend the canonical
   pattern instead of copying it.
3. Extend the drift net:
   - src/ikigai/tests/test_canonical_scope.py holds the scope checks: forbidden
     imports and calls in the agent layer, the tool count, the UEID regex, the
     append-only queues, the skill manifest, the memory schema.
   - src/ikigai/tests/test_drift_invariants.py holds the load-bearing invariants.
   - src/ikigai/tests/test_drift_detector.py and
     src/ikigai/tests/test_drift_state.py hold the detector and its state.
4. Run the suites in the environment that owns the code:
   cd src/ikigai && poetry run pytest
   cd src/contracts && uv run pytest
   pytest tests/
5. When a schema change touches the store, add the next numbered migration under
   src/contracts/migrations/ and apply it in order with
   src/contracts/migrations/apply.py. Never edit a migration that already ran.
6. Report the invariant, the test that covers it and the results of every command.
Invariants:
- Drift tests are append-only. Never delete one and never weaken an assertion
  to make a suite green.
- A changed invariant without a covering test is an incomplete change.
- A suite that did not run is not a passing suite. Say which commands ran.
- The agent layer stays planner-only. No algorithm constants, no policy math and
  no scoring reach it.
Done when:
- The new test fails without the contract change and passes with it,
- every drift test that existed before still exists and still passes,
- and the package suites report green with the commands listed.
```

### ci-green-gate

```
Trigger:    Before a push, before a release, or when a CI job is red.
Inputs:    The diff against the base branch, the CI workflow, and the per-package
            environments.
Outputs:   A verdict of PASS or FAIL, the first violation found, and the file path
            that carries it.
Steps:
1. Run the review orchestrator, which type checks and lints each package in its
   own environment:
   python .github/scripts/code_review.py --base <base-ref> --type-only --gate
   python .github/scripts/code_review.py --base <base-ref> --test-only --missing --review-format --gate
2. Run the suites the workflow runs, each in the environment that owns it:
   pytest tests/
   cd src/ikigai && poetry run pytest
   cd src/contracts && uv run pytest
   cd vibe-ops && uv run pytest
   cd interfaces/cli && uv run pytest
3. Check the scope of the diff. It must touch canonical code only.
4. Scan the diff for secrets. No key, token, password or connection string, and
   .env.example stays placeholder-only.
5. Check that the migration files under src/contracts/migrations/ are numbered
   and ordered, and that no applied migration was edited.
6. Report PASS or FAIL with the first violation and its path.
Invariants:
- The verdict is about invariants, not about style.
- A failing check is reported as FAIL. Never suppress a failure and never delete
  a test to reach green.
- Pre-existing debt is reported separately and does not fail the diff.
- The kill switch in sys_ikigai/security/kill_switch.py, exposed as
  python -m interfaces.cli kill-switch status, is the owner control for pausing
  writes. The gate does not trigger it.
Done when:
- The review orchestrator exits zero with --gate,
- every listed suite passes in its own environment,
- and the verdict, the commands that ran and the first violation, if any, are
  reported.
```

---

## RETIRED surfaces

These surfaces are gone from the published tree. They are listed so you recognize
them and stay away from them. Do not create them and do not write code for them.

| RETIRED surface | Former path | Status |
|-----------------|--------------|--------|
| The Textual TUI | `interfaces/tui/` | RETIRED, gitignored, absent from the published tree |
| The stdio MCP fork servers | `src/solverforge_calendar/` | RETIRED, gitignored, absent from the published tree |
| The stdio MCP fork servers | `src/tuiboard/` | RETIRED, gitignored, absent from the published tree |
| The legacy agent harness built on langchain and langgraph | `src/ikigai/src/agents/` | RETIRED, gitignored, absent from the published tree |
| The legacy agent harness built on langchain and langgraph | `src/ikigai/src/chat/` | RETIRED, gitignored, absent from the published tree |
| The `life v2` CLI sub-app | `interfaces/cli/v2.py` | RETIRED, gitignored, absent from the published tree |
| The vibe-ops Rust TUI | `vibe-ops/` TUI crate | RETIRED, absent from the published tree |

The canonical CLI in `interfaces/cli/` replaces the retired sub-app, and the HTTP
MCP transport in `src/transport/mcp_server.py` replaces the retired stdio
servers. The two published forks are `src/mesh/adapters/cli.py` and
`src/mesh/adapters/taskdog.py`.
