# ADR-035 — Empty-Commit Guard / Shipping Verification

> **Status:** Accepted (initial)
> **Deciders:** matheus (project owner)
> **Date:** 2026-09-21
> **Wave:** R4 (Master-04 attribution gap closure)
> **Supersedes:** none (new decision — codifies an existing implicit invariant surfaced by a 2026-09-14 incident)
> **Related code / specs:**
> - `docs/superpowers/specs/2026-09-14-file-vanish-investigation.md:7-15` — root-cause spec ("EMPTY commits with substantive claims")
> - `memory/m12-bottom-up-infra-shipped-2026-09-14.md` — M12 FINAL CLEANUP note: "previous workflows reported success but never git committed the files"
> - Recovery commits: `f12653e2`, `28cbf3f1`, `be6a7630`, `df10c683`, `9b6a596e` — forced disk-verified rebuild of the vanished files
> - `src/ikigai/tests/test_drift_extended_invariants.py` — forthcoming enforcement target (`test_empty_commit_guard`, G5 below)

---

## Context

On 2026-09-14, five commits dated 2026-09-14 01:01–01:05 claimed to ship five non-trivial features:

| Claimed feature | Actual `git diff --stat HEAD~1 HEAD` |
|-----------------|---------------------------------------|
| `ikigai_serve` FastAPI entry | 0 file changes (only `.gitkeep` placeholder) |
| taskdog MCP Path 3 server | 0 file changes |
| `GatewayClient` async wrapper | 0 file changes |
| SSE publisher (LangGraph events) | 0 file changes |
| chat schema + souls/loader.py | 0 file changes (directory empty except `__pycache__/`) |

**The subagents reported success. `git commit` ran. The working tree had no real code to stage.** The 5 commits were empty (or contained only a `.gitkeep`), but their commit messages and downstream memory entries claimed substantive deliverables. The disk-verified rebuild (`f12653e2`, `28cbf3f1`, `be6a7630`, `df10c683`, `9b6a596e`) had to be performed to actually land the work.

### Root cause

The previous workflow pattern was:

1. Subagent reports "shipped file X."
2. Workflow trusts the report and runs `git commit -m "ship X"`.
3. `git commit` succeeds even when `git add` staged nothing (or staged an empty placeholder).
4. Memory entry records "X shipped at commit Y."
5. **Nobody verifies disk state or commit content.**

The class of failure is **subagent-hallucination shipping**: the subagent believes it shipped, the workflow believes the subagent, the git history records the claim — but the disk has nothing. The drift net (53 → 68 invariants) cannot catch this class of bug because no code in the working tree is broken; the absence of code is the bug.

### Why the drift net didn't catch it

ADR-032 (bridge ⊆ server) and ADR-033 (UEID single-source) detect **alignment drift** between two existing artifacts. The vanish incident is the inverse class: **absence of artifact**. The drift net counts invariants that ARE present; it does not enumerate invariants that MUST be present. The forthcoming G5 drift test (this ADR) closes the asymmetry.

### M12 final cleanup notes the problem

`memory/m12-bottom-up-infra-shipped-2026-09-14.md` §"FINAL CLEANUP 2026-09-14" records:

> VANISH FIX 2026-09-14: restored ikigai_serve.py + souls/loader.py + 4 mesh adapter stubs after subagent-hallucination commits were empty. f12653e2, 28cbf3f1, be6a7630, df10c683, 9b6a596e. **Root cause: previous workflows reported success but never git committed the files.**

The fix was manual recovery. **No formal guard prevents recurrence.** This ADR establishes the guard.

---

## Decision

**Every milestone's deliverable MUST pass four guards (G1–G4) before its commit is marked DONE. Guard violations are hard-fail; there is no override flag.**

The contract has **4 shipping guards (G1–G4)** and **1 enforcement invariant** (forthcoming G5).

### G1 — `git diff --stat HEAD~1 HEAD` shows > 0 file changes (non-doc-only milestones)

For any milestone that claims to ship code (not pure-docs), the commit MUST contain at least one file change with substantive content. A commit that contains only a `.gitkeep`, a `__pycache__/` artifact, or a memory entry is FORBIDDEN.

```bash
$ git diff --stat HEAD~1 HEAD
# MUST list >= 1 file with non-trivial content
# (interpretation: total lines changed >= 1, no .gitkeep-only, no __pycache__-only)
```

Pure-doc milestones (memory entries, ADR drafts, spec docs) are exempt — `MEMORY.md` updates and ADR file writes are valid zero-code commits. The exemption is explicit per G1.1 below.

### G2 — Each claimed shipped file exists on disk with expected content (hash match)

For every file the milestone claims to ship:

1. The file MUST exist at the claimed path.
2. The file MUST have non-empty content (not 0 bytes).
3. The file MUST match the content described in the commit message / memory entry (hash match where possible).

The verification is `git show <commit>:<path>` for the as-committed content and `test -s <path>` for the post-commit working tree. Both checks MUST pass.

### G3 — Drift net / pytest / ruff MUST pass before commit is marked DONE

The milestone's "DONE" status MUST NOT be written to `MEMORY.md`, `progress.md`, or any other status surface until:

1. `pytest -m "not e2e"` PASS (or the milestone's targeted test scope PASS, with the rest explicitly noted as out-of-scope).
2. `ruff check src/` PASS.
3. `ruff format --check src/` PASS.
4. `mypy src/` shows no regression vs. the prior commit (or PASS if the milestone explicitly cleans up a known warning).

A milestone with PASS gates fails is NOT DONE — even if the code is on disk and tests pass locally. Drift-net drift (regressions vs. prior commit) is a hard-fail.

### G4 — Subagent results MUST be disk-verified before commit (no trust-the-report)

For any milestone shipped via subagent (Sonnet/Haiku worker):

1. The orchestrator (Opus-tier or human) MUST inspect `git diff --stat HEAD~1 HEAD` after the subagent's commit lands and verify the claimed files are present in the diff.
2. The orchestrator MUST inspect the post-commit working tree (`test -s <path>`) for every claimed file.
3. The orchestrator MUST NOT trust subagent status reports ("file X created", "tests pass") without independent verification.

The verification surface is the orchestrator's responsibility, not the subagent's. Subagents report WHAT they did; the orchestrator verifies WHAT landed on disk.

---

## Rationale

1. **The incident is repeatable.** The 2026-09-14 vanish is not a one-off. Subagents are high-throughput (M26–M50 shipped 25+ milestones in one session) but error-prone — the trust-the-report pattern is the default unless an explicit guard exists. Without this ADR, the next vanish incident is a matter of when, not if.

2. **Empty commits are silent.** `git commit` exits 0 even when `git add` staged nothing. There is no built-in git guard against "I committed an empty tree and called it done." The guard MUST come from outside git.

3. **Test-typed enforcement beats documentation.** A drift test that runs `git diff --stat HEAD~1 HEAD` (G5) and asserts non-empty + non-placeholder content cannot go stale without CI catching it. Documentation about "verify before committing" goes stale; tests don't.

4. **Drift net is the canonical enforcement mechanism.** Per ADR-013 §"Persistent enforcement": "drift detectors are load-bearing — running the test in CI is the canonical way to prevent future sessions from accidentally re-introducing deleted code." G5 follows the same template as `test_ueid_regex_single_source` (ADR-033 R4) and `test_mcp_bridge_wrapped_tool_count_matches_canonical` (ADR-032 enforcement).

5. **The four guards are independent.** G1 catches empty commits. G2 catches file-content mismatch (file exists but is wrong). G3 catches "code shipped but tests broke." G4 catches "subagent hallucinated." A failure of any single guard is a hard-fail. Independence ensures no single bypass defeats all four.

6. **Reversibility favors the additive pattern.** Adding a guard is a 1-test edit (G5 in `test_drift_extended_invariants.py`). Removing a guard requires an ADR amendment. The cost asymmetry prevents accidental weakening of the contract.

7. **Subagent-driven-development is a force multiplier.** M39–M50 demonstrated 12+ milestones in one session with the subagent-driven-development review loop. The throughput is valuable. The guard ensures the throughput does not regress into shipping nothing.

---

## Implementation Rules

### (a) Pre-commit hook: bash script checks `git diff --stat > 0` for non-doc changes

A pre-commit hook (`scripts/hooks/pre-commit-empty-guard.sh`) MUST exit non-zero if:

1. The staged change set is empty (`git diff --cached --stat` returns nothing).
2. The staged change set contains ONLY `.gitkeep` files.
3. The staged change set contains ONLY files under `memory/` or `docs/` (pure-doc commits are allowed but must be explicitly opted-in via `--allow-empty` or `--allow-docs-only` flag).

The hook is installed via `make install-hooks` (or the equivalent repo-standard install script) and is loaded by every contributor's local git config. CI also runs the hook on every push (defense-in-depth).

### (b) Drift net enforcement: run drift net before final commit

Before marking a milestone DONE in `MEMORY.md` or `progress.md`, the orchestrator MUST run:

```bash
pytest src/ikigai/tests/test_canonical_scope.py \
       src/ikigai/tests/test_drift_invariants.py \
       src/ikigai/tests/test_drift_extended_invariants.py
```

The drift net MUST show no regression (count unchanged or higher) before the commit is considered DONE. Drift-net drift is recorded in the milestone's "verification" section, not just "shipped."

### (c) Disk-verification: any shipped claim MUST have matching git hash + file content

For every claim of the form "shipped file X at commit Y":

1. `git show <commit>:<path>` MUST return non-empty content.
2. The working tree `<path>` MUST exist and have non-empty content.
3. The commit message MUST reference the file path explicitly (not just "shipped the IKIGAI module").

Memory entries that record "shipped X at commit Y" without a verifiable artifact path are MEDIUM-confidence and MUST be verified before they're cited as source-of-truth in downstream work.

### (d) Roll-back protocol: vanish detection → immediate revert + re-ship

If a vanish is detected post-commit (a milestone claims shipped files that don't exist on disk):

1. **Immediate revert.** `git revert <commit>` to remove the empty commit from history.
2. **Re-ship with disk-verified workflow.** The orchestrator re-runs the milestone via subagent, but with G1/G2 verification at every step (not just at the end).
3. **Post-mortem.** Add an entry to `MEMORY.md` documenting the vanish + recovery, similar to the 2026-09-14 pattern.
4. **Drift test refresh.** If the vanish bypassed G1/G2 (e.g., the hook was disabled or the commit was pushed directly), add a test that catches the specific bypass pattern.

### G5 — Forthcoming enforcement invariant

`test_empty_commit_guard` MUST be added to `src/ikigai/tests/test_drift_extended_invariants.py`. The test MUST:

1. Walk the last N commits (`N=20` default) and assert each non-merge commit has non-trivial content.
2. For each commit, parse the commit message for paths matching `code|sys_ikigai|vibe-ops|src` (i.e., code paths, not `memory/` or `docs/`).
3. For each claimed path, assert the path exists in the commit (`git show <commit>:<path>` returns non-empty).
4. Assert no commit is composed entirely of `.gitkeep` files (excluding pure-doc commits).

If the test fails, CI fails. There is no override flag.

---

## Consequences

### Positive

- **No more vanish incidents.** The 2026-09-14 pattern (5 commits shipped 0 files, subagents reported success) cannot recur: every commit's content is verified by G1 + G2, every subagent report is verified by G4, every milestone's DONE status is gated by G3.
- **Subagent throughput preserved.** The guard is additive (adds verification, not blocking). Subagents can still ship high-throughput (M26–M50 cadence); they just can't ship nothing.
- **Drift net symmetry.** G5 closes the "absence of artifact" gap that ADR-032 and ADR-033 didn't cover. The drift net now covers both **alignment drift** (between existing artifacts) and **absence drift** (artifacts that should exist but don't).
- **Reversible without ADR.** Adding/removing files in a commit (not the guard itself) is a 1-N line edit; no ADR required. The drift detector validates the change.
- **Defense-in-depth.** G1 (pre-commit hook) + G2 (post-commit verify) + G4 (orchestrator disk-check) catch the same class of failure at three different points. Single-point bypass is impossible.

### Negative

- **Slower ship cycle.** Every milestone now requires ~30s of verification overhead (G2 disk-check + G3 drift-net run). At M26–M50 cadence (~25 milestones/session), this adds ~12 min/session. Acceptable cost.
- **1 drift test to maintain.** `test_empty_commit_guard` is load-bearing; if it breaks (false positive) every CI run fails. Per Phase 8.2 SPEC §3 — "drift tests grow with the system; weakening them is forbidden."
- **Pre-commit hook brittleness.** The hook must handle merge commits, rebase commits, amend commits, and `--no-verify` bypass. Edge cases (e.g., cherry-picks, squash merges) need careful maintenance. Future workflow shapes may need detector amendments.
- **G1 exempts pure-doc commits.** `memory/` and `docs/` commits are allowed to be empty or `.gitkeep`-only. This is intentional (memory entries + ADR drafts are valid zero-code commits) but creates a bypass surface: a milestone could abuse the exemption by claiming code ships in `docs/` or `memory/`. The audit (G2) catches this — file content MUST match the claim regardless of exemption class.
- **Orchestrator burden.** G4 places verification responsibility on the orchestrator (Opus-tier or human), not the subagent. This adds cognitive load to the orchestrator workflow. M11 mitigations are documented in `subagent-driven-development` skill; future skill versions may automate the verification step.

### Neutral

- **Pure-doc milestones are exempt from G1.** Memory entries, ADR drafts, spec docs are valid zero-code commits. The exemption is explicit (per (a) above) and the audit (G2) catches abuse.
- **`--allow-empty` and `--allow-docs-only` flags are escape hatches.** They exist for legitimate use (e.g., reverting a feature without code changes, sync a memory entry). The escape hatch is logged in the commit message and is reviewed by the orchestrator. Not treated as equivalent to a real shipping commit.
- **Recovery commits (`f12653e2`, `28cbf3f1`, `be6a7630`, `df10c683`, `9b6a596e`) remain in history.** The 2026-09-14 incident is a permanent part of the git history; this ADR documents the guard that prevents recurrence, not a rewrite of history.

---

## Alternatives Considered

### Alt A — Trust subagents (the pre-ADR-035 state)

Continue relying on subagent status reports without independent verification.

- **Rejected**: this is the pre-incident state. The 2026-09-14 vanish incident is the proof that trust-the-report fails. The M12 FINAL CLEANUP note explicitly identifies this as the root cause. The status quo is not an option.

### Alt B — Skip post-commit verification (reactive only)

Catch vanish incidents post-hoc via manual audits (e.g., daily disk-verification cron).

- **Rejected**: reactive verification catches incidents days after they happen. By the time the audit runs, the empty commit has been cited as source-of-truth in downstream work (memory entries, downstream commits, status reports). The cost of recovery (revert + re-ship + audit trail reconstruction) is much higher than the cost of pre-commit verification.

### Alt C — Manual verification only (no drift test)

Have the orchestrator manually verify each commit's content, but skip G5 (`test_empty_commit_guard`).

- **Rejected**: manual verification doesn't scale. The M26–M50 session shipped 25+ milestones; manual verification per commit would have added ~25×30s = 12.5 min of orchestrator cognitive load. Worse, manual verification is bypassable (the orchestrator forgets, the orchestrator is tired, the orchestrator trusts the subagent's framing). Drift test enforces automatically in CI.

### Alt D — Git-level guard via custom merge hook / server-side pre-receive

Push the guard to a server-side pre-receive hook that rejects empty commits at the remote.

- **Rejected**: the repo is local-only (per CLAUDE.md "Fully local — SQLite + filesystem only, zero cloud deps"). There is no remote pre-receive hook to install. The guard must live in the local pre-commit hook + CI drift test (defense-in-depth via local mechanisms).

### Alt E — Drop subagent-driven-development entirely

Revert to single-developer shipping where one human (or one Opus-tier session) does all work directly.

- **Rejected**: the throughput of subagent-driven-development is valuable (M26–M50 demonstrated this). The guard preserves the throughput while preventing the failure mode. Dropping the pattern would regress the autonomous-loop capability that Wave 5 / M46 established.

### Alt F — Whitelist-specific allowlist for empty commits (e.g., `M12-FIX-*` always exempt)

Create a regex-based allowlist that exempts specific commit-message patterns from G1.

- **Rejected**: allowlist-based bypass is exactly the pattern that lets vanish incidents hide. The 2026-09-14 incident had no allowlist, but a future incident with `--allow-empty` flagrant use could be missed if the allowlist grows. The `--allow-empty` flag is the legitimate escape hatch (per Consequences §Neutral); an allowlist by commit-message pattern is a different and worse pattern.

---

## Cross-references

### Load-bearing prior ADRs

- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) — establishes the pattern of drift-detector load-bearing invariants. G5 (`test_empty_commit_guard`) follows the ADR-013 §"Persistent enforcement" template.
- **ADR-032 — Bridge-Wrapper Drift Contract** (Accepted 2026-09-21) — sister ADR addressing **alignment drift** (existing artifacts out of sync). ADR-035 covers the inverse class: **absence drift** (artifacts that should exist but don't).
- **ADR-033 — UEID Single-Source Mandate** (Accepted 2026-09-21) — sister ADR addressing **drift between two existing definitions**. ADR-035 covers the empty-commit class that ADR-033's pattern doesn't address.

### Related decisions

- **ADR-009 — Pydantic v2 strict** (Accepted 2026-08-31) — verification of milestone status (G3) inherits the "Pydantic models as canonical contracts" pattern; milestone DONE status is typed via the milestone contract, not free-form prose.
- **ADR-026 — Sub-Agent Dispatch Protocol** (Accepted 2026-09-05) — sub-agent dispatch is the surface where G4 applies. The orchestrator that dispatches subagents is responsible for G4 verification.

### Code / spec references

- `docs/superpowers/specs/2026-09-14-file-vanish-investigation.md:7-15` — TL;DR root-cause spec ("EMPTY commits with substantive claims")
- `docs/superpowers/specs/2026-09-14-file-vanish-investigation.md:10-14` — verbatim 5-commit list with zero-file-change observation
- `scripts/hooks/pre-commit-empty-guard.sh` — forthcoming G1 enforcement hook (post-acceptance)
- `src/ikigai/tests/test_drift_extended_invariants.py` — G5 forthcoming drift test (`test_empty_commit_guard`)

### Memory / review references

- `memory/m12-bottom-up-infra-shipped-2026-09-14.md` §"FINAL CLEANUP 2026-09-14" — explicit identification of root cause: "previous workflows reported success but never git committed the files"
- `memory/m12-bottom-up-infra-shipped-2026-09-14.md` §"VANISH FIX 2026-09-14" — recovery commits `f12653e2`, `28cbf3f1`, `be6a7630`, `df10c683`, `9b6a596e`
- `memory/subagent-driven-development-validated-2026-09-15.md` — M39 was first full subagent-driven-development review loop; ADR-035 makes the validation parallel (subagent throughput + verifier disk-check)

### Implementation steps (post-acceptance)

1. Create `scripts/hooks/pre-commit-empty-guard.sh` with G1 enforcement (exit non-zero on empty / .gitkeep-only / undocumented code-path claims).
2. Add `make install-hooks` target (or repo-standard equivalent) that wires the hook into the local git config.
3. Add `test_empty_commit_guard` to `src/ikigai/tests/test_drift_extended_invariants.py` (G5).
4. Update `subagent-driven-development` skill to document G4 (orchestrator disk-verification responsibility).
5. Run drift net + targeted pytest; expect 68 → 69 invariants PASS.

---

*ADR-035 — accepted 2026-09-21 — locks the empty-commit guard surfaced by the 2026-09-14 vanish incident; drift detector forthcoming as G5 in `test_drift_extended_invariants.py`*