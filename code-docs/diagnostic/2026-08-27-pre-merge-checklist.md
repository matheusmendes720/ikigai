# Pre-Merge Checklist — Observability Sprint (4 Repos)

> **Date:** 2026-08-27
> **Author:** Architecture
> **Status:** 🟡 Draft — pending review
> **Scope:** Operationalize the 4-repo observability sprint pattern (1 OTel branch
> per repo) into a repeatable checklist. Source of truth for the merge procedure
> described in `life-ops/ikigai/docs/observability/03-merge-plan.md`.
> **Related work:** Specs 01 (reliability), 02 (smoke test), 03 (merge plan),
> 04 (worktree dissolve).

---

## §0 Purpose

The observability sprint landed the same pattern in 4 independent repos
(IKIGAI + 3 external MCP servers):

- **Dual OTLP/HTTP exporters** — single OpenTelemetry SDK, two sinks
  (LangSmith + Langfuse). Both backends must receive spans for parity.
- **`init_tracing()` server-side boot** — initializes SDK once per process;
  idempotent on repeated calls.
- **`@observed_tool` decorator (Python) / `#[instrument]` (Rust) / `withSpan()`
  (TS) wrapper** — every tool handler is a span root.
- **Server-side reliability layer** — retry (inner) + circuit breaker (outer)
  so CB counts logical calls, not attempts.

This document captures the **operational checklist** for merging each of the 4
feature branches back to its default branch **safely, observably, and with full
rollback coverage**. It exists because:

1. Each repo has its own CI, lint config, dependency manager — divergent gates.
2. A failed merge in any 1 repo blocks downstream consumers of that server.
3. The observability claim ("spans flow to LangSmith + Langfuse") is
   **untestable** without a merge; until we merge, it's a code-side hypothesis.

**Outcome we want:** every merge is atomic, instrumented, revertable in
≤ 5 minutes, and leaves the diagnostic/README/INDEX/ADR web of docs in sync.

**Read first:**

- `life-ops/ikigai/docs/observability/03-merge-plan.md` — branch list + dep order.
- `life-ops/ikigai/docs/observability/02-integration-smoke-test.md` — gated by this.
- `code-docs/diagnostic/README.md` — diagnostic category index.

---

## §1 Pre-Merge Verification

Three gate layers must pass **per branch** before merge is initiated. None of
these are optional — they're the difference between a clean merge and a
mid-merge regression.

### 1.1 Local quality gates

Run all of the following inside the feature branch worktree. **All must pass.**

- [ ] `git status` is clean (no uncommitted noise; `swap`, `lock`, `output.txt`
      files cleaned per `CLAUDE.md §Pitfalls`).
- [ ] Branch is rebased onto the target branch (e.g. `feat/otel-tracing` rebased
      onto `main`, IKIGAI worktree rebased onto `gitbutler/workspace`).
- [ ] Linter passes (mirrors repo-specific CI step):
  - [ ] IKIGAI: `uv run ruff check src/ && uv run ruff format --check src/`
  - [ ] taskdog: `uv run ruff check src/ && uv run ruff format --check src/`
  - [ ] tuiboard: `bun run lint && bun run format:check`
  - [ ] solverforge: `cargo clippy --all-targets -- -D warnings`
- [ ] Type checker passes:
  - [ ] IKIGAI: `uv run mypy src/` (strict mode)
  - [ ] taskdog: `uv run mypy src/`
  - [ ] tuiboard: `bunx tsc --noEmit`
  - [ ] solverforge: `cargo build` (no `cargo check` shortcuts)
- [ ] Unit + integration tests pass with the OTel feature flag **off**
      (baseline invariant):
  - [ ] IKIGAI: `uv run pytest -m "not e2e"` — same count as pre-branch.
  - [ ] taskdog: `uv run pytest -m "not e2e"`
  - [ ] tuiboard: `bun test`
  - [ ] solverforge: `cargo test --lib`
- [ ] Tests pass with `OTEL_ENABLED=true` (no init crashes; span emission
      is best-effort and **must not** fail tests).
- [ ] `OTEL_ENABLED=false` (default) shows **zero regression** in test runtime
      (baseline ±5%). The init must be lazy.
- [ ] No secrets, API keys, or `.env` files staged (`git diff --stat` shows
      no `.env*` / `*.pem` / `*.key` files).

### 1.2 CI quality gates

Each repo has its own CI workflow; do not assume IKIGAI's gates are universal.

- [ ] Branch pushed to origin; PR (or merge target) links to a CI run that's
      **green at HEAD** (not "green at some older commit").
- [ ] CI includes the OTel-specific smoke step if the repo has one
      (e.g. `taskdog/.github/workflows/otel-smoke.yml`).
- [ ] Required reviews on the PR match the repo's CODEOWNERS — IKIGAI requires
      Architecture; the 3 externals require their respective owners.
- [ ] Branch protection rules pass: no direct push; merge via squash or
      `--no-ff` per Spec 03 §Merge procedure.
- [ ] No required CI checks are **skipped** (e.g. a `continue-on-error: true`
      step on smoke). Skipping is escalation territory, not a shortcut.

### 1.3 Cross-repo compatibility check

The 4 repos share **a contract** even though they don't share code:

- [ ] `init_tracing()` signatures match across the 3 externals — both:
      - (a) env-var-driven (no required positional args), and
      - (b) idempotent (calling twice does not double-register providers).
- [ ] `@observed_tool` decorator exported from a common module path
      (e.g. `from observability.decorators import observed_tool`). Avoid
      per-file re-implementations.
- [ ] Span attribute names match the **shared schema** (e.g. `tool.name`,
      `tool.duration_ms`, `retry.attempt`, `cb.state`). Defined in
      `vibe-ops/schema_registry/registry.yaml` (or the IKIGAI equivalent) —
      confirm the new attributes are registered, not ad-hoc.
- [ ] OTLP/HTTP endpoint env vars are identical across repos:
      `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`,
      `LANGSMITH_PROJECT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`,
      `LANGFUSE_HOST`. Document any deviation in the PR description.
- [ ] SDK versions: OpenTelemetry SDK + instrumentation packages pinned to
      compatible majors (no silent upgrades). Deviations must be called out
      in the PR body.
- [ ] Reliability config env vars use the **same names** as Spec 01 §Common
      contract: `RETRY_MAX_ATTEMPTS`, `RETRY_INITIAL_BACKOFF_S`,
      `CB_FAILURE_THRESHOLD`, `CB_RESET_TIMEOUT_S`.

**If any compatibility check fails, STOP.** Fix the contract before merging —
otherwise the 4 servers will report divergent metrics and the LangSmith +
Langfuse dashboards will be apples-to-oranges.

---

## §2 Cross-repo Coordination

The 4 merges are **independent code** but **coupled in observation**. A fan-out
strategy without coordination produces 4 nearly-identical PRs that need to
land in a specific order, or downstream consumers see partial observability
state.

### 2.1 Dependency-ordered merge procedure

Per Spec 03 §Dependency order:

**Phase 1 — Foundation (sequential, must finish before Phase 2):**

1. [ ] `solverforge-calendar` `feat/rust-build-fix` → `main`
      (Commit `1716b16`; without it, OTel Rust crate won't link.)

**Phase 2 — OTel merges (parallel after Phase 1 completes):**

2. [ ] `tuiboard` `feat/otel-tracing` → `main` (Commits `590ea60`, `2c39867`)
3. [ ] `taskdog` `feat/otel-tracing` → `main` (Commits `5a8b1bb2`, `600c92b9`)
4. [ ] `solverforge-calendar` `feat/otel-tracing` → `main`,
      **rebased on Phase 1** (Commits `cfbf12b`, `064b8c9`)
5. [ ] `life-oss/life` (IKIGAI) worktree → `gitbutler/workspace`
      (Commits `f803fb6`, `2b94724`, `87f6ef9`, `0e528d0`, `ca4e65c`,
      `0ff111d`, `eeac3aa`, `e31777f`)

**Phase 3 — Verification (sequential, after all Phase 2 merges):**

6. [ ] Run Spec 02 smoke test (`pav smoke observability`) against all merged
      mains. All 4 interfaces must show ≥ 1 span per backend.
7. [ ] Run Spec 04 worktree-dissolve steps for the IKIGAI worktree only.

**Merge mechanics:**

- [ ] All 4 OTel merges use `--no-ff` (merge commit), not squash. Rationale:
      Spec 04 §Risks mandates `--no-ff` so the 8 IKIGAI commits survive
      individually for cherry-pick / bisect.
- [ ] Each merge is a **separate, atomic PR** — no "merge all 4 in one PR"
      shortcuts. One PR = one rollback unit.
- [ ] Each PR body links to its corresponding spec
      (`docs/observability/0X-*.md`) in this monorepo.

### 2.2 Conflict resolution

Most merges are isolated per-repo, but two collision surfaces exist:

- **Shared OpenTelemetry SDK version** — if 2+ repos upgrade `opentelemetry-*`
  packages to different minors, downstream consumers that share a `pyproject`
  resolve conflict. Mitigation:
  - [ ] Pin SDK version in each repo's `pyproject.toml` (ikigai) or
        `Cargo.toml` (solverforge) — identical pinned versions.
  - [ ] If a conflict is detected at install time, prefer the **higher minor**
        and re-run smoke (Spec 02) on the affected repo.
- **Span attribute naming drift** — Spec 01 §Common contract uses
  `tool.name` / `retry.attempt` / `cb.state`. If a repo adopts a different
  key (e.g. `toolName`, `retryAttempt`), Langfuse dashboards break.
  Mitigation:
  - [ ] Lint check: ban `@observed_tool` registrations that pass ad-hoc
        attribute names. Use `schema_registry/registry.yaml` as the canonical
        vocabulary.
  - [ ] On merge conflict on `registry.yaml`, the **IKIGAI registry entry wins**
        (IKIGAI is the schema owner for the IKIGAI vector namespace).

**Escalation:** if a merge conflict is non-trivial (>50 lines), do not
resolve in-merge — open a "spec amendment" issue, get Architecture sign-off,
rebase and re-run §1 gates.

### 2.3 OTel feature branch merge order

Even within Phase 2, ordering matters if the smoke test (Phase 3) requires
**all 4 servers live at once**:

- [ ] Merge **tuiboard first** in Phase 2 — it's the smallest server and
      the TypeScript pattern is the easiest to debug if smoke fails.
- [ ] Merge **taskdog second** — Python-FastMCP pattern is the closest
      analog to IKIGAI's stack.
- [ ] Merge **solverforge OTel third** (after the build-fix) — Rust is
      the highest-blast-radius language, so it goes last to isolate failures.
- [ ] Merge **IKIGAI observability last** — IKIGAI is the orchestrator.
      Merging it last means Phase 3 smoke exercises the **final state**
      of the consumer, not an intermediate snapshot.

**Why this order:** the LangSmith trace timeline reads left-to-right by merge
time, and the consumer (IKIGAI) merges last means the trace shows the
**natural** call order: tuiboard → taskdog → solverforge → IKIGAI.

---

## §3 Rollback Plan

Three rollback tiers, in increasing severity. All must be **documented before
merge** — not improvised after.

### 3.1 Per-merge rollback

If smoke (Spec 02) fails **after a specific merge**:

- [ ] Identify the merge commit SHA:
      `git log --merges --oneline -n 5 <target-branch>`
- [ ] Revert **only that merge**, preserving history:
      `git revert -m 1 <merge-sha>`
- [ ] Push the revert commit. CI runs; confirm revert passes its own §1 gates.
- [ ] File an incident note in `docs/.sdd-progress.md` (no blame, only facts:
      "Merge X reverted at <time> because smoke returned <symptom>").
- [ ] Re-open the feature branch (`git branch feat/otel-tracing
      <original-sha>`) and triage before any second merge attempt.

**Time budget:** 5 minutes. If the revert doesn't land clean, escalate to
§3.2.

### 3.2 Catastrophic rollback

If **multiple merges** misbehave simultaneously (e.g. OTel SDK version pin
breaks all 4 servers), disable observability at the env layer:

- [ ] Set `OTEL_ENABLED=false` in the deployment config (or the CI secret).
- [ ] Confirm baseline behavior returns within 1 minute. The `init_tracing()`
      no-op path must be tested in `1.1` — this is why we gate on it.
- [ ] File a single incident report linking all 4 affected repos.
- [ ] DO NOT attempt to revert in-place while production is degraded. The
      feature flag is the safety net; use it.

**Restore procedure (after root cause identified):**

- [ ] Document the root cause in `docs/.sdd-progress.md`.
- [ ] Apply the fix on a new branch per affected repo; do not re-merge the
      original.
- [ ] Re-run Spec 02 smoke after the fix; only after PASS, flip
      `OTEL_ENABLED=true` again.

### 3.3 Recovery from failed merge

If a merge **itself** fails (cherry-pick / rebase / conflict, not runtime):

- [ ] Abort the merge: `git merge --abort` or
      `git rebase --abort`.
- [ ] Sync the target branch: `git checkout main && git pull --ff-only`.
- [ ] Re-fetch the feature branch: `git fetch origin feat/otel-tracing`.
- [ ] Re-attempt the merge. If it fails twice, **stop and escalate**.
- [ ] Document in the PR comments — the audit trail matters more than the
      speed of retry.

**Anti-patterns to avoid:**

- ❌ `git push --force` on a shared branch (audit loss).
- ❌ `git reset --hard` to "fix" a merge-in-progress (corruption risk).
- ❌ Silent retry without updating the PR description (reviewers can't see
  what changed).
- ❌ Merging around the failure by submitting a single squashed commit
  (loses the per-commit history that Spec 04 needs).

---

## §4 Documentation Sync

A merge without doc updates is incomplete. This section names **every doc that
must be touched** — not "best effort", but a hard list.

### 4.1 CLAUDE.md update (if scope changed)

- [ ] If the merge introduces a **new pitfall** (e.g. an editable-install
      `.pth` rewrite, a new env var that breaks local dev), append it to
      `life/CLAUDE.md §Pitfalls` in the relevant format
      (4-column table: rule / where / what it forbids).
- [ ] If the merge **changes a command** in §Build/Run/Test or §Architecture,
      update in the same commit as the merge, not in a follow-up.
- [ ] Cross-link from `life-oss/CLAUDE.md` if the change is observable from
      repo-root workflows (rare but possible).

### 4.2 `.sdd-progress.md` (append sprint results)

- [ ] Append a single dated entry to `docs/.sdd-progress.md` per merge
      (one entry, not four — merge results are batched).
- [ ] Entry format: `## YYYY-MM-DD — Observability sprint merges complete`
      with sub-bullets for each of the 4 repos and link to the PR.
- [ ] If a merge was reverted (§3.1 / §3.2), the **same** entry is updated
      — append-only means **history of events**, not final state.

### 4.3 Master diagnostic (mark issues resolved)

- [ ] Open `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` and
      cross-link from §1.4 (IKIGAI backend observability) → the new PR.
- [ ] Issues resolved by these merges (Task 1, Task 4, Task 5 from
      `IKIGAI_BACKEND_DEEP_DIVE_REPORT.md`) flip from 🟡 to ✅ **after** the
      merges land, never before.
- [ ] The 3-external-server issues in the master diagnostic get the same
      treatment per their respective repos.

### 4.4 ADRs (if decision changed)

- [ ] If the merge forces a deviation from an existing ADR (e.g. ADR-009 on
      Pydantic strict mode, ADR-008 on IKIGAI vector count), open a **new**
      ADR in `code-docs/adr/` explaining the deviation. Do not rewrite old ADRs.
- [ ] ADR numbering: continues from the highest existing
      (currently ADR-011 — IKIGAI MCP HTTP+SSE). New: ADR-012 if needed.
- [ ] Cross-link the ADR from the PR body and from §4.5 00-INDEX.

### 4.5 00-INDEX.md (link new docs)

- [ ] `code-docs/00-INDEX.md §Observability` (or wherever the category lives)
      gains a link to any new doc produced during the merge (e.g. a
      runbook, a new spec).
- [ ] If the merge closes a §12 "Known gaps" item, the gap row flips to ✅
      with a link to the PR.
- [ ] Bump the INDEX revision timestamp footer if applicable.

---

## §5 Spec Compliance Verification

The 4 specs were the **promised deliverables**. This section verifies the merges
actually deliver what was specified — not just "code is merged", but
"acceptance criteria are demonstrably met".

### 5.1 Read original spec

- [ ] Re-open the 4 specs:
  - [ ] `life-ops/ikigai/docs/observability/01-server-side-reliability.md`
  - [ ] `life-ops/ikigai/docs/observability/02-integration-smoke-test.md`
  - [ ] `life-ops/ikigai/docs/observability/03-merge-plan.md`
  - [ ] `life-ops/ikigai/docs/observability/04-dissolve-worktree.md`
- [ ] For each spec, extract the **acceptance criteria** (the bullet list under
      `## Acceptance criteria` or equivalent).

### 5.2 Walk through acceptance criteria

Per spec:

- **Spec 01 (server-side reliability)**:
  - [ ] Each of tuiboard / taskdog / solverforge has `withRetryAndBreaker`
        (or equivalent) applied uniformly. Verify in the post-merge tree.
  - [ ] Env-var config (`RETRY_MAX_ATTEMPTS=3`, etc.) is wired in all 3
        externals.
  - [ ] Unit tests for retry / CB / half-open exist and pass.
  - [ ] Zero behavior change when `RETRY_ENABLED=false`.
- **Spec 02 (smoke test)**:
  - [ ] `pav smoke observability` exits 0 against all 4 merged mains.
  - [ ] Both backends (LangSmith + Langfuse) report ≥ 1 span per interface.
  - [ ] Cleanup works: no zombie subprocesses, no leaked SQLite DBs.
- **Spec 03 (merge plan)**:
  - [ ] All 4 merges landed in the dependency order specified.
  - [ ] Each merge is a merge commit (`--no-ff`), not a squash.
  - [ ] Each PR links back to its spec file.
- **Spec 04 (worktree dissolve)**:
  - [ ] `git worktree list` does not include `life-mcp-observability-worktree`.
  - [ ] All 8 IKIGAI commits are reachable from `gitbutler/workspace`.
  - [ ] `git status` on `gitbutler/workspace` is clean.
  - [ ] CI is green on `gitbutler/workspace`.

### 5.3 Mark checklist items in spec

- [ ] In each spec file, flip the open checkboxes (`☐`) to checked
      (`☑`) or strikethrough as appropriate. **Append-only** discipline:
      never delete the original unchecked items — annotate instead
      (`☑ resolved via PR #N at YYYY-MM-DD`).
- [ ] Move the spec's `**Status:**` frontmatter from `Proposed` to
      `Implemented` (no `Completed` — the deliverable might still evolve).
- [ ] If a criterion was **not** met, leave the checkbox open and link to
      the issue tracking the gap. Do not silently close.

---

## §6 PR Template (concrete fields + checklist)

Use this body verbatim for each of the 4 OTel PRs. Adapt the per-repo sections.

```markdown
## Title

feat(observability): <REPO> dual OTLP/HTTP exporters + server-side reliability

## Related spec

- `life-ops/ikigai/docs/observability/0X-*.md` (link)
- Cross-link to the IKIGAI PR that this depends on / depends on this.

## What changed

- [ ] Added `init_tracing()` in <path>
- [ ] Added `@observed_tool` decorator at <path>
- [ ] Wired dual OTLP/HTTP exporters (LangSmith + Langfuse)
- [ ] Reliability layer: retry (inner) + CB (outer) at <path>
- [ ] Updated `pyproject.toml` / `Cargo.toml` / `package.json` deps

## Quality gates

- [ ] §1.1 local gates pass (lint / types / tests / `OTEL_ENABLED=false`
      regression check)
- [ ] §1.2 CI green at HEAD on this PR
- [ ] §1.3 cross-repo contract invariants hold (decorator signature,
      env-var names, span attribute vocabulary, SDK version pin)

## Pre-merge items completed

- [ ] Smoke test (Spec 02) green on this branch
- [ ] Spec compliance (§5) walked through on this branch
- [ ] Doc sync (§4) scheduled for after merge

## Risks

- (paste from Spec 01 §Risks or §3 of this checklist, repo-specific subset)

## Rollback plan

- `git revert -m 1 <merge-sha>` per §3.1
- `OTEL_ENABLED=false` kill-switch per §3.2
- Recovery procedure in §3.3

## Reviewer

- @<CODEOWNER per repo>
- Architecture sign-off (for IKIGAI)
```

**Per-repo fields to fill:**

- IKIGAI: branch = `feat/mcp-observability` ← `gitbutler/workspace`; reviewer = Architecture.
- tuiboard: branch = `feat/otel-tracing` ← `main`; reviewer = tuiboard owner.
- taskdog: branch = `feat/otel-tracing` ← `main`; reviewer = taskdog owner.
- solverforge: branch = `feat/otel-tracing` ← `main`, rebased on
  `feat/rust-build-fix`; reviewer = solverforge owner.

---

## §7 Cross-References

This document is part of the diagnostic category and links to / from the
following canonical sources.

| Topic | Source |
|-------|--------|
| Branch list + dep order | `life-ops/ikigai/docs/observability/03-merge-plan.md` |
| Smoke test definition | `life-ops/ikigai/docs/observability/02-integration-smoke-test.md` |
| Reliability contract | `life-ops/ikigai/docs/observability/01-server-side-reliability.md` |
| Worktree dissolve | `life-ops/ikigai/docs/observability/04-dissolve-worktree.md` |
| Master diagnostic | `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` |
| Issue dependencies | `code-docs/diagnostic/2026-08-27-issue-dependencies.md` |
| Migration scripts | `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` |
| Risk & effort | `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md` |
| Diagnostic README | `code-docs/diagnostic/README.md` |
| Sdd-progress log | `docs/.sdd-progress.md` |
| Span attribute schema | `vibe-ops/schema_registry/registry.yaml` |
| ADR archive | `code-docs/adr/` (latest: ADR-011) |
| IKIGAI backend deep-dive | `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` |
| IKIGAI-side reliability (Task 4) | Commit `87f6ef9` in `life-mcp-observability-worktree` |
| Data-first methodology | `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\MEMORY.md` |

**Maintenance contract:** this doc is **append-only**. When a new spec lands,
add a row to the cross-reference table and link to it from §5.1. Do not edit
the existence of past checkboxes — mark them `☑` with a date annotation.

---

*Pre-merge checklist — v1.0 — 2026-08-27.*
