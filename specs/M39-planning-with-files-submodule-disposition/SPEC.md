---
name: M39-planning-with-files-submodule-disposition
description: Resolve the broken-gitlink state at strategics/planning-with-files (mode 160000 without .gitmodules registration).
status: IN_PROGRESS
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_conversation
  - tests_are_the_contract
  - spec_driven_not_vibe_driven
  - reversibility_over_cleverness
dependencies:
  - M20 (operational hygiene — flagged the submodule dirty state)
estimated_ticks: 1
---

# M39 — planning-with-files submodule disposition

## Problem

`strategics/planning-with-files/` is registered as mode 160000 (gitlink) in
the parent repo's tree but has no `.gitmodules` entry at the parent root
and no `.git/modules/strategics/planning-with-files/` registration.
`git submodule status` returns:

```
fatal: no submodule mapping found in .gitmodules for path
'strategics/planning-with-files'
```

The embedded directory has its own complete `.git/` (with remote
`https://github.com/matheusmendes720/planning-with-files.git`, branch
`master`, HEAD `8f5a3c2e`). Working tree had 55 modified files
(+2928/-2117) before this milestone — local IDE integrations, hooks,
version-test scripts — committed nowhere.

This is the "ghost submodule" state that breaks `git submodule update`,
breaks `git status` reporting in CI, and accumulates untracked work.

## State preserved (2026-09-15)

- Full diff of the 55 modified files: `strategics/_local-snapshots/planning-with-files-local-edits-2026-09-15.patch`
  (429KB patch, can be re-applied with `git -C strategics/planning-with-files apply < patch`).
- Inner repo HEAD: `8f5a3c2e1c347635cf94debde033b3c1ac97e4ab` (release v3.1.3).
- Parent gitlink commit ref: `8f5a3c2e1c347635cf94debde033b3c1ac97e4ab`.
- Working tree in submodule: `git restore .` applied — clean.

## Why this matters

- CI: `git submodule status` erroring breaks any CI step that depends on
  submodule awareness.
- Index bloat: phantom gitlinks without metadata confuse tooling.
- Hidden work: the 55 modified files were never committed anywhere —
  they would silently disappear on a `git submodule update --force`.
- Contradicts governance: append-only rule + state-on-disk principle
  say every change must be reflected in a milestone SPEC. None was.

## Disposition options

| # | Action | Effect | Reversibility |
|---|---|---|---|
| A | Register as proper submodule (reconstruct `.gitmodules` + `.git/modules/strategics/planning-with-files/`, move to `apps/` for consistency with taskdog/solverforge-calendar/tuiboard) | Clean state, follows project pattern | Trivial (re-rm) |
| B | Unlink entirely: `git rm --cached strategics/planning-with-files` (strips gitlink), keep working tree | Vendored copy, no submodule tooling | Trivial (re-add as submodule) |
| C | Track all files directly: blow away inner `.git/`, `git add` everything, commit to parent | Permanent vendored copy, no separate repo | Hard (would need subtree split) |
| D | Defer: leave broken-gitlink state, document in roadmap only | No change | N/A |

## Recommendation

**Option A** (register as proper submodule + relocate to `apps/dev-tools/planning-with-files/`):
- Aligns with the other 3 submodules (taskdog, solverforge-calendar, tuiboard all in `apps/`)
- Preserves the separate remote (Matheus's fork of OthmanAdi's project)
- Restores `git submodule status` to working
- Makes future sync work tractable
- Reversible if user wants to switch to B/C later

**NOT recommended: Option C** — destroys the inner `.git`, breaks IDE plugin
hosting that depends on `.hermes/plugins/planning-with-files/` being a
real working tree.

## Acceptance

- [ ] `.gitmodules` exists at root with `strategics/planning-with-files`
      entry (path, url, branch) — OR strategic decision documented in
      roadmap why not
- [ ] `git submodule status` returns clean (no fatal) — OR strategic
      decision documented why broken state is intentional
- [ ] `git status` shows no "phantom submodule" dirt on `strategics/planning-with-files`
- [ ] `_local-snapshots/planning-with-files-local-edits-2026-09-15.patch`
      either applied (local edits integrated into a commit) OR
      intentionally archived with a `M39-local-edits-DEFERRED.md` note
- [ ] Drift net preserved: 68/68 (ikigai drift) + 11/11 (test_loop_infra)
- [ ] No regress in any of: `git submodule foreach`, `git submodule sync`,
      `git clone --recurse-submodules` (smoke test on the result)

## Dependencies

- M20 (operational hygiene) — already DONE; this milestone is the
  follow-up that M20 explicitly deferred.

## Estimated ticks

1 (snapshot + decision + apply + verification).

## Constitution gate

- **state_on_disk_not_in_conversation:** the 55-file diff was only in
  filesystem state, never declared anywhere. Fixed by snapshotting.
- **tests_are_the_contract:** drift net must stay green throughout.
- **spec_driven:** this SPEC is the artifact (in_progress).
- **reversibility_over_cleverness:** Option A is trivial to undo; we
  explicitly chose not to lock in Option C.

## Open questions for user

1. Confirm Option A vs B vs C vs D?
2. If A: relocate path (`apps/dev-tools/planning-with-files/` to match
   taskdog's convention) or keep at `strategics/`?
3. The 55 local edits: ship them as a commit inside the submodule
   (push to `matheusmendes720/planning-with-files.git`), or apply +
   commit to the parent as a vendored patch, or archive only (current
   state)?