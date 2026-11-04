# Skill Specs - usability routines for the canonical serverless scope

**Status:** specification (2026-11-02, revised for the renewed remote-branch scope)
**Scope:** executable contracts for the routines a cloud agent performs on the published repository.
**Anchor:** [ADR-037](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md)
**Companion:** [SYSTEM-PROMPTS.md](./SYSTEM-PROMPTS.md) · [router.md](./router.md)

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
- Never invent a path. If a file is not in the tree, it does not exist.
- No step writes SQL. The service layer in `src/services/artifacts.py` is the only writer of the store.
- No step edits or deletes a file under `vault/`. The vault is append-only.
- Every skill ends by reporting the commands it ran and their result.

The agent reaches the store through the six MCP tools of `src/transport/mcp_server.py`:
`search_artifacts`, `get_artifact`, `upsert_artifact`, `delete_artifact`, `list_relations`
and `embed_text`.

Identifier format: `UEID` is `type:slug:uuid:hash` and is defined once, in
`src/contracts/common.py`. The type segment is the kind namespace, the slug is
lowercase with dashes, the uuid segment identifies the instance and is frozen at
creation, and the hash segment fingerprints the content the artifact was created
with. Build a new one with `make_uid(kind, slug, uuid_short, content_hash_short)`.
Never hand-build one.

---

## Index

| # | Skill | Trigger | Primary surface |
|---|-------|---------|-----------------|
| 1 | `store-write` | The agent must persist an artifact | `src/transport/` |
| 2 | `store-read` | The agent must find or read artifacts | `src/transport/` |
| 3 | `vault-sync` | Markdown changed, or the store is behind the prose | `src/services/sync.py` |
| 4 | `daily-note` | The daily cycle runs | store, `strategics/` |
| 5 | `weekly-review` | The weekly cycle runs, plan vs actual | store, `strategics/` |
| 6 | `monthly-review` | The monthly cycle runs, objectives vs results | store, `strategics/` |
| 7 | `quarterly-plan` | The quarterly cycle runs | store, `strategics/` |
| 8 | `contract-change-drift-test` | A contract or an invariant changed | `src/contracts/`, drift net |
| 9 | `ci-green-gate` | Before a push or a release | `.github/` |
| 10 | `release-deploy` | The service is deployed or upgraded | `src/contracts/migrations/` |

---

### store-write

```
Trigger:    The agent must create an artifact or change an existing one.
Inputs:     The kind, the title, the body or the kind-specific fields, and the
            parent or relation targets.
Outputs:   The uid, the new revision, and the outcome: created, updated or
            unchanged. On a conflict, the agent returns a rereported artifact
            rather than a write.
Steps:
1. Build the artifact for the kind. Prose kinds - sonho, plano, onda, revisao,
   nota - require a non-empty body. KPI requires a metric, a period and a
   direction. OKR requires an objective and a key_result. DESC requires a
   decision. TAREFA requires a priority.
2. Derive the identity:
   - slug from the title, lowercase with dashes;
   - uuid segment from a fresh instance discriminator;
   - hash segment from the sha256 of the body, first 16 hex characters.
   Build the uid with make_uid so the validation happens at the boundary.
3. Read before writing. Call search_artifacts with the kinds filter, and when a
   candidate matches, call get_artifact on it. If it exists, reuse its uid and
   its revision. If it does not, expected_revision is null.
4. Call upsert_artifact with the WriteRequest: the artifact, expected_revision,
   a non-empty idempotency_key, and a client_id.
   The idempotency key identifies the intent, not the moment: build it from the
   uid and the body hash, so a retry of the same intent is recognisable.
5. Read the outcome:
   - created: the revision is 1.
   - updated: the revision went up by one.
   - unchanged: the same idempotency key already wrote this intent.
   - conflict: another client wrote first. Call get_artifact, decide whether the
     change still applies, and reapply with the revision just read.
6. Create the relations with list_relations and upsert through the relation
   service: PARENT_OF for hierarchy, DEPENDS_ON for sequence, EVIDENCES for
   provenance, DERIVES_FROM for lineage, REFERENCES for citation, SUPERSEDES for
   replacement, BLOCKS for contention.
7. Report the uid, the revision, the outcome, the relations created and the
   tools that ran.
Invariants:
- One writer per store. The agent never writes SQL and never edits the store
  directly.
- Every write carries a non-empty idempotency_key and a client_id.
- A content change bumps the body hash and the revision. It never changes the
  uid.
- Hierarchy is expressed as relations. A task depends on another through a
  DEPENDS_ON edge, not through a field.
- A stale expected_revision is a conflict. Never force the write.
- No secret, token or connection string goes into an artifact.
Done when:
- the outcome is created or updated, or unchanged with the reason stated,
- the artifact is readable through get_artifact at its new revision,
- and the report names the uid, the revision and the tools that ran.
```

### store-read

```
Trigger:    The agent must find artifacts, read one, or follow the graph.
Inputs:     A kind filter, a quarter, a status, a parent uid, a text, or a uid.
Outputs:   The artifacts found, the artifact read with its relations and
            neighbours, or the edges at a node. When nothing matches, the report
            says what was searched for.
Steps:
1. Narrow with search_artifacts before fetching anything. The query carries text,
   kinds, quarter, status, parent_uid, semantic, limit and cursor. The limit
   goes from 1 to 200 and defaults to 20.
2. Page with the cursor. The cursor is opaque: take next_cursor from the result
   and pass it back verbatim. Never construct one.
3. Read one artifact with get_artifact and the depth you need: depth 1 returns
   the artifact, its relations and its immediate neighbours; depth 0 returns the
   artifact and its edges only.
4. Walk the graph with list_relations. Narrow with the relation type when the
   edge type matters. Keep a visited set so a cycle terminates.
5. Report the fields that came from where, and name the source of each one.
Invariants:
- This skill is read-only. It writes no artifact, no relation and no file.
- An artifact missing from one place is reported as missing. It is not
  reconstructed from a neighbour.
- The uid format is defined once, in src/contracts/common.py.
Done when:
- every requested field is reported with its source,
- or the report states that the uid exists nowhere, with the search that showed
  it.
```

### vault-sync

```
Trigger:    Markdown under vault/ changed, or a store-backed read returns content
            that is behind the prose.
Inputs:    The vault trees declared in src/services/sync.py, the store
            connection, and the write requests built from the markdown.
Outputs:   A report with the counts of scanned, created, updated, unchanged and
            skipped, and every skipped file with its reason.
Steps:
1. Read the design first: specs/data-layer/TECH.md, then src/services/sync.py
   for the mapping.
2. Confirm the store is reachable. The variable name is in src/contracts/store.py.
   A missing variable is a configuration error, not a reason to fall back to
   local state.
3. Run the ingestion. It reads the trees from default_sources(), skips README
   files, locates the kind and the quarter from the layout, computes the body
   hash and compares it with the stored revision.
   Two layouts exist. The closing layout is <quarter>/<kind>/<file>.md, where the
   quarter directory sits in front of the kind directory. The persona layout is
   flat, one directory per tier: dreams, objectives, projects, ikigai_state,
   deliverables.
4. Write through src/services/artifacts.py into src/data/repository.py. Every
   write carries an idempotency key, a client_id and the expected revision.
   The idempotency key is built from the layout, the relative path and the body
   hash, so an unchanged file is recognised as already ingested.
5. Report the counters and every skipped file with its reason.
Invariants:
- The ingestion is idempotent. Running it twice creates no duplicate and does
  not rewrite what did not change.
- Artifact identity comes from the location. A content change bumps body_hash
  and revision and never changes the uid.
- A file that declares its own ueid in the frontmatter keeps that identity.
- A stale expected_revision is a conflict and returns to the caller. Never force
  the write.
- One failing file does not abort the batch. It lands in skipped with its reason.
- The ingestion never writes, moves or deletes anything under vault/.
Done when:
- the report shows zero unexpected failures,
- a second run reports unchanged for the same tree,
- and every skipped file has a stated reason.
```

### daily-note

```
Trigger:    The daily cycle runs, or the owner asks for the day to be recorded.
Inputs:     The quarter, the tasks planned for today, the notes written today,
            and the evidence the agent can point at in the store.
Outputs:   A NOTA artifact for the day, with the uid, and the counts of what was
            done, partly done, not started and dropped.
Steps:
1. Read the skill's conceptual source in strategics/: the daily block and the
   daily report sections of "Analise (Tatico e Operacional)" define what a day
   is made of.
2. Gather the state from the store:
   - search_artifacts with kinds=(tarefa,) and the quarter, for the tasks of the
     period;
   - search_artifacts with kinds=(nota,) and the quarter, for the notes already
     written today;
   - get_artifact on each task that has evidence, to read its relations.
3. Classify each task as done, partly done, not started or dropped, and cite the
   evidence: the note uid or the relation that proves it. An item with no
   evidence stays open.
4. Write the NOTA. The prose kinds require a non-empty body. The body carries
   the classification and the evidence. Set the quarter and the note date.
5. Link the note to each task it speaks about with an EVIDENCES edge.
6. Report the note uid, the counts per class, the evidence per class and the
   tools that ran.
Invariants:
- The note is a new artifact. The previous day's note is never rewritten.
- Every classification cites evidence. A recollection is not evidence.
- The note never contains a secret, a token or a connection string.
Done when:
- the note exists at its uid with the counts and the evidence,
- and the report names the uid, the counts per class and the tools that ran.
```

### weekly-review

```
Trigger:    The weekly cycle runs, or the owner asks how the plan compares to
            reality.
Inputs:     The current plan, the tasks of the period, the notes of the week,
            and the evidence in the store.
Outputs:   A REVISAO artifact for the week, the uid, and the counts per class.
Steps:
1. Read the conceptual source in strategics/: "Desempenho Subjacente" defines the
   five-day consolidation the weekly review consumes, and "Hierarquia de
   Objetivos" defines the review template and the meta table it feeds.
2. Gather the state from the store:
   - search_artifacts with kinds=(plano, onda, okr, kpi) and the quarter;
   - search_artifacts with kinds=(tarefa,) for the period;
   - search_artifacts with kinds=(nota,) and the quarter, for the notes of the
     week.
3. Classify each planned item as done, partly done, not started or dropped, and
   cite the evidence for the classification.
4. Write the REVISAO with the classification and the evidence. Set the quarter.
5. Link the review to what it reviews with REFERENCES edges.
6. Report the review uid, the counts per class and the tools that ran.
Invariants:
- The pipeline is arithmetic over state in the store. There is no LLM in the
  count.
- The review is a new artifact. The plan is not edited.
- An item with no evidence stays open.
- A stale expected_revision is a conflict. Reread and reapply; never force.
Done when:
- the review exists at its uid with the counts,
- every planned item has a class and a piece of evidence,
- and the summary counts match what the tools returned.
```

### monthly-review

```
Trigger:    The monthly cycle runs, or the owner asks how the objectives are
            tracking.
Inputs:     The objectives of the quarter, the KPIs with their targets, the
            actuals read from the weeklies, and the decisions already recorded.
Outputs:   A DESC artifact against the objectives, its uid, and the gap between
            target and actual per indicator.
Steps:
1. Read the conceptual source in strategics/: "Hierarquia de Objetivos" defines
   the monthly, dream-oriented review, and "Desempenho Subjacente" defines the
   three-month consolidation it feeds.
2. Gather the state from the store:
   - search_artifacts with kinds=(okr,) and the quarter, for the objectives;
   - search_artifacts with kinds=(kpi,) and the quarter, for the indicators with
     their targets and periods;
   - search_artifacts with kinds=(revisao,) and the quarter, for the weeklies
     that carry the actuals;
   - search_artifacts with kinds=(desc,) and the quarter, for the decisions
     already recorded.
3. Compare each indicator's actual against its target and compute the gap. The
   indicator carries Decimal values, never float: a KPI that loses precision is
   a wrong KPI.
4. Write the DESC with the decision, the rationale and the outcome. A DESC
   records a decision and why it was taken, so the body states what the gap
   means and what is being decided about it.
5. Link the decision to the objectives and the indicators it speaks about.
6. Report the decision uid, the gap per indicator and the tools that ran.
Invariants:
- The comparison is arithmetic over the store. There is no LLM in the gap.
- A DESC states the rationale. A decision without a rationale is not a decision.
- The prior monthly decision is never rewritten.
Done when:
- the decision exists at its uid with the gap per indicator,
- and the report names the uid, the gaps and the tools that ran.
```

### quarterly-plan

```
Trigger:    The quarterly cycle runs, or the owner asks for the next quarter.
Inputs:     The dreams, the last quarter's review, the objectives and indicators
            that closed, and the Teste de Fogo result.
Outputs:   A PLANO artifact for the quarter, its FASE rows, its OKR objectives,
            its ONDA waves, and the uid of each.
Steps:
1. Read the conceptual source in strategics/:
   - "Modelagem Operacional" defines the five levels and the cycles;
   - "Planejamento (Estrategico e Tatico)" defines the quarterly planning, the
     5x3x3 proportion and the Teste de Fogo;
   - "Correcao do Trajeto" defines what a failed Teste de Fogo triggers;
   - "Desempenho Subjacente" defines the three-month consolidation this feeds.
2. Gather the state from the store:
   - search_artifacts with kinds=(sonho,) for the dreams in force;
   - search_artifacts with kinds=(revisao, desc) and the closing quarter, for the
     verdict and the decisions;
   - search_artifacts with kinds=(okr, kpi) and the closing quarter, for what
     closed and what did not.
3. Run the Teste de Fogo against the closing quarter. A verdict that is not PASS
   opens the Correcao do Trajeto: the correction is written before the new plan.
4. Write the PLANO for the new quarter, with its plan tier and its quarter. Set
   the quarter on every artifact that belongs to it.
5. Write the FASE rows of the plan, the OKR objectives with their key results
   and targets, and the ONDA waves of the quarter.
6. Link them: PARENT_OF from the plan to its phases, the phases to the waves,
   the waves to the tasks; DERIVES_FROM when a wave comes from an objective.
7. Report the plan uid, the uids of the phases, objectives and waves, the
   Teste de Fogo verdict, and the tools that ran.
Invariants:
- The plan is a new artifact. The closing quarter's plan is never edited.
- The Teste de Fogo verdict is computed from the store, not asserted.
- A failed verdict produces a Correcao do Trajeto before a new plan.
- Hierarchy is expressed as relations, never as duplicated fields.
Done when:
- the plan, its phases, its objectives and its waves exist and are linked,
- the Teste de Fogo verdict is reported with the evidence it was computed from,
- and the report names every uid it wrote.
```

### contract-change-drift-test

```
Trigger:    A contract in src/contracts/ changed, or a load-bearing invariant
            changed.
Inputs:    The contract diff, the drift net, and the affected suites.
Outputs:   The changed invariant, the drift test that covers it, and the test
            results per package.
Steps:
1. Make the smallest contract change. Contracts are Pydantic v2, frozen, with
   extra fields forbidden. Import a model, never redefine it.
2. Keep the UEID pattern in one place, src/contracts/common.py. Extend the
   canonical pattern instead of copying it.
3. Keep the contract and the schema in step. A kind that needs its own fields
   gets a model in dom_kinds.py and a table in the migrations, and an entry in
   KIND_TABLES in src/contracts/store.py. A kind without own fields gets no
   table.
4. Extend the drift net:
   - src/ikigai/tests/test_canonical_scope.py holds the scope checks;
   - src/ikigai/tests/test_drift_invariants.py holds the load-bearing invariants;
   - src/ikigai/tests/test_drift_extended_invariants.py holds the later ones;
   - src/ikigai/tests/store/test_store_schema.py holds the checks that the SQL
     matches the contract without a database.
5. Run the suites in the environment that owns the code:
   cd src/ikigai && poetry run pytest
   cd src/contracts && uv run pytest
6. When the schema changed, add the next numbered migration under
   src/contracts/migrations/ and apply it in order with
   python -m src.contracts.migrations.apply. Never edit a migration that already
   ran.
7. Report the invariant, the test that covers it and the results of every
   command.
Invariants:
- Drift tests are append-only. Never delete one and never weaken an assertion to
  make a suite green.
- A changed invariant without a covering test is an incomplete change.
- A suite that did not run is not a passing suite. Say which commands ran.
- The agent layer stays planner-only. No algorithm constants, no policy math and
  no scoring reach it.
Done when:
- the new test fails without the contract change and passes with it,
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
Done when:
- the review orchestrator exits zero with --gate,
- every listed suite passes in its own environment,
- and the verdict, the commands that ran and the first violation, if any, are
  reported.
```

### release-deploy

```
Trigger:    The service is deployed or upgraded, or the store schema must move.
Inputs:    The target store, the migration files, the service image, and the
            transport configuration.
Outputs:   The applied migration list, the service state, the result of a tool
            round trip, and the rollback path.
Steps:
1. Confirm the target. The DSN arrives in the environment variable named in
   src/contracts/store.py. Read it from the environment. Never from a file in the
   tree.
2. Inspect the schema state:
   python -m src.contracts.migrations.apply status
3. Apply the pending migrations in order:
   python -m src.contracts.migrations.apply
   The runner takes an advisory lock, records a checksum per migration and is a
   no-op when there is nothing pending. Never edit a migration that already ran.
4. Bring the service up. The transport is selected by the IKIGAI_MCP_TRANSPORT
   environment variable: stdio is the default, http and streamable-http serve
   over HTTP, sse is accepted for a legacy client.
   python -m src.transport.mcp_server
5. Verify that the service answers. Call search_artifacts with an empty query
   and read the result, then upsert_artifact a throwaway artifact and delete it
   with delete_artifact, which is a soft delete.
6. Report the applied migrations, the service state, the round trip and the
   rollback path.
Invariants:
- The DSN is never written to a file, a log line or a report.
- A migration that already ran is never edited. The rollback is the matching
  .down.sql, applied with:
  python -m src.contracts.migrations.apply down --yes
  The --yes flag is required because a rollback can destroy data.
- The smoke artifact is deleted before the step ends. It never becomes part of
  the record.
- A deployment that cannot verify the round trip is reported as a failure, not
  as a success with a warning.
Done when:
- the status command shows the expected migration set,
- the round trip succeeded and left no throwaway artifact behind,
- and the report names the applied migrations, the state and the rollback path.
```
