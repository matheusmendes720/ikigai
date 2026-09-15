---
name: M55-zero-byte-claude-n-cleanup
description: Gitignore the .claude/n zero-byte bash-redirect leak + delete the existing artifact.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
estimated_ticks: 1
---

# M55 — Zero-byte .claude/n cleanup

## Problem

A 0-byte file `n` at `.claude/n` was created by a bash redirect leak on
2026-09-15 18:55 (during a daemon loop-tick iteration — exact command
not recovered but matches the pattern of `> N` redirects where `N` is a
single character or short name). M20 T-20.1 + M46 both extended
`.gitignore` patterns for root-level leaks but did NOT cover paths inside
subdirectories like `.claude/`.

## Disposition applied

1. Added explicit `/.claude/n` to `.gitignore` (also added `/n` for root-level
   variants — `git check-ignore /n` would fail at the repo root since `/n`
   is an absolute path outside the repo, but the pattern is correct for
   paths inside the repo like `n` at any depth)
2. `rm .claude/n` — removes the existing artifact
3. Verified: `git status -s` no longer shows `.claude/n`; `git check-ignore -v
   .claude/n` returns the `.gitignore` rule that catches it

## Acceptance

- [x] `.gitignore` extended: `+/.claude/n` (T-55.1)
- [x] `rm .claude/n` (T-55.2)
- [x] `git status -s` clean of `.claude/n` (T-55.3)
- [x] `git check-ignore -v .claude/n` confirms the rule (T-55.4)
- [x] Drift net preserved: 69/69 + 11/11 (T-55.5)
- [x] 1 atomic commit + push to origin master (T-55.6)

## Why M20 + M46 missed this

M20's gitignore focused on root-level leaks (`/0`, `/IN`, etc.). M46
extended to multi-digit numerics (`/[0-9]*`) and f-string fragments
(`/{len(lf_data)}`). Neither extended to single-character paths INSIDE
subdirectories like `.claude/n` — the M20 patterns were specifically
rooted (`/N`), which doesn't match `.claude/n`.

## Note

This is a small, contained fix. Daemon loop-tick.sh has likely been
generating similar artifacts across iterations; the `/n` pattern at
repo root will catch the next root-level instance, and `/.claude/n`
handles the specific pattern observed.

## Reversibility

`git revert HEAD`. Two-line change to .gitignore.