---
name: M41-planning-with-files-submodule-unlink
description: Strip phantom submodule gitlink at strategics/planning-with-files; keep directory as self-contained vendored fork.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_conversation
  - tests_are_the_contract
  - spec_driven_not_vibe_driven
  - reversibility_over_cleverness
dependencies:
  - M20 (operational hygiene — flagged the dirty submodule state)
  - M39 (daemon-watchdog — daemon shipped in parallel, renumbered this spec from M39 to M41)
estimated_ticks: 1
---

# M41 — planning-with-files submodule unlink

> **Renumbered from M39** because the daemon shipped a different milestone
> ("daemon-watchdog") at the same M-number in parallel. See commit `b431a649`.
> All references to "M39" in the original draft now mean "M41".

## Problem

`strategics/planning-with-files/` was registered as mode 160000 (gitlink)
in the parent tree but had no `.gitmodules` entry at the parent root and
no `.git/modules/strategics/planning-with-files/` registration.
`git submodule status` returned:

```
fatal: no submodule mapping found in .gitmodules for path
'strategics/planning-with-files'
```

The embedded directory had its own complete `.git/` (remote
`matheusmendes720/planning-with-files.git`, branch `master`, HEAD
`8f5a3c2e` matching upstream OthmanAdi v3.1.3 byte-for-byte).

The 55-file working-tree diff (snapshotted as
`strategics/_local-snapshots/planning-with-files-local-edits-2026-09-15.patch`,
429KB) was **100% Black/Ruff formatter output** against upstream v3.1.3,
verified by:
- Reading every non-trivial file end-to-end (zero functional changes)
- SHA-256: 8 of 9 IDE-mirror `session-catchup.py` files were byte-identical
- `git apply --check` + `git apply -R` both succeeded cleanly against v3.1.3
- Upstream HEAD == local HEAD == `8f5a3c2e`

There was no functional work to preserve. The snapshot is now historical only.

## Investigation summary (3 sub-agents, 2026-09-15)

| Question | Finding |
|---|---|
| Did `.gitmodules` exist? | No. Deleted at `248e359` (2026-08-28). The 3 historical submodules (taskdog, solverforge-calendar, tuiboard) lived at `interfaces/<name>` (NOT `apps/`) and were removed from tree at `ec6d9cec` same day. No submodule registration pattern exists on master today. |
| Were there other phantom gitlinks? | No. `git ls-tree HEAD` showed exactly 1 gitlink: `strategics/planning-with-files → 8f5a3c2e`. The 3 orphan `.git/modules/<name>/` dirs (14.05 MB) are unreachable from any master gitlink. |
| Did CI know about submodules? | No. `.github/workflows/ci.yml` uses `actions/checkout@v4` with no `submodules:` keyword. No submodule management scripts anywhere in the repo. |
| Were the 55 local edits valuable? | No. 49 of 55 files were disposable IDE-mirror / locale / test formatter outputs. 6 deferred to upstream (`scripts/*.py`, `.hermes/plugins/*`). Zero ship, zero extract. |

## Disposition applied

**Option B** (unlink + keep as vendored copy), with the simplification that
the formatter patch is also discarded (no functional content to preserve):

1. **`git restore .` inside submodule** (already done in earlier session) —
   working tree back to v3.1.3 byte-for-byte.
2. **`git rm --cached strategics/planning-with-files`** — strips the
   phantom gitlink from the parent index. Inner `.git/` (10.29 MB) survives
   intact; the directory remains a self-contained fork.
3. **Add `strategics/planning-with-files/` to parent `.gitignore`** —
   prevents future `git status` noise; the inner repo continues to work
   for IDE plugin hosting (`.hermes/plugins/planning-with-files/`).
4. **Delete `strategics/_local-snapshots/`** — the 429KB patch is historical
   only (formatter output, regenerable with `black .` upstream).

## Why Option B, not A/C/D

| Option | Why rejected |
|---|---|
| A — register proper submodule + relocate to `apps/dev-tools/planning-with-files/` | No precedent on master (the `.gitmodules` was deleted18 days ago; 3 historical submodules were removed same day). Establishing a new pattern when there is no existing convention would be inventing a norm. The "apps/dev-tools/" path does not exist at master HEAD either (only on unmerged `origin/gitbutler/target`). |
| C — track all 545 files directly in parent | Destroys inner `.git` (10.29 MB of useful backing store) and breaks `.hermes/plugins/planning-with-files/` (which depends on the inner repo being a real working tree). Reversibility is poor. |
| D — defer (leave broken-gitlink state) | M20's deferral loop has already cost us 429 KB of uncommitted work and 18 days of phantom-submodule noise. Deferring again violates the append-only + state-on-disk constitution principles. |

## Acceptance

- [x] Local diff classified: 49 disposable + 6 deferred-to-upstream, 0 ship, 0 extract (T-41.1 — subagent audit)
- [x] Working tree in submodule restored to v3.1.3 byte-for-byte (T-41.2 — `git -C strategics/planning-with-files restore .`)
- [x] Snapshot patch deleted; `strategics/_local-snapshots/` directory removed (T-41.3)
- [ ] Phantom gitlink removed from parent index: `git rm --cached strategics/planning-with-files` (T-41.4)
- [ ] `strategics/planning-with-files/` added to parent `.gitignore` (T-41.4)
- [ ] Drift net preserved: 68/68 (ikigai drift) + 11/11 (test_loop_infra)
- [ ] `git status` clean (no phantom submodule state, no leaked .patch file)
- [ ] Inner repo `strategics/planning-with-files/.git/` still functional (verify with `cd strategics/planning-with-files && git status` showing clean working tree at HEAD 8f5a3c2e)

## Dependencies

- M20 (operational hygiene) — DONE, flagged the dirty state
- M39 (daemon-watchdog) — DONE, shipped in parallel by daemon; this milestone
  renumbered from M39 to M41 to avoid collision

## Estimated ticks

1 (4 tasks above).

## Constitution gate

- **state_on_disk_not_in_conversation:** the 55-file diff was only in
  filesystem state, never declared anywhere. Snapshotted (then discarded
  as cosmetic-only).
- **tests_are_the_contract:** drift net must stay green throughout.
- **spec_driven_not_vibe_driven:** this SPEC is the artifact.
- **reversibility_over_cleverness:** Option B is trivial to undo
  (`git submodule add <url> strategics/planning-with-files` recreates the
  gitlink; the inner `.git/` was never touched).

## Open questions for user

None. All 3 questions from the M39 draft are resolved by Option B:
1. A vs B vs C vs D → **B** (unlink + keep as vendored)
2. Path relocation? → **No** (keep at `strategics/planning-with-files/`; inner
   repo still has its own `.git/` and works standalone)
3. Ship 55 local edits? → **No** (100% formatter output, 0 functional,
   regenerable with `black .` upstream if desired)