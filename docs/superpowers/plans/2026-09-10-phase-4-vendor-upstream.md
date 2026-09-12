# Phase 4 — Vendor Upstream Kohei-Wada/taskdog

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the upstream Kohei-Wada/taskdog monorepo into our project as `vendor/taskdog/` so future IKIGAI patches layer cleanly on top.

**Architecture:** `git subtree add --prefix=vendor/taskdog upstream/main` imports upstream's full commit history. Upstream stays pristine under `vendor/taskdog/`; our IKIGAI customizations live in their own files (`ikigai_taskdog/` thin wrappers, `ikigai-chat` entry point) and import from `vendor.taskdog_*` packages.

**Tech Stack:** git subtree, uv workspace, FastAPI (server), Textual (ui), FastMCP (mcp).

## Context (state anchor)

- Local master HEAD: `49815ac8` (FORK_WORKFLOW.md commit)
- Upstream main HEAD: `2352f6120f4941528ebfcd4e1dc203ec76896292`
- Upstream remotes already configured (commit `49815ac8`).
- ikigai-taskdog gambiarra files REMOVED from master (preserved at branch `backup-loop-prod-ready-2026-09-10` + `C:\temp\ikigai-backup\`).
- Worktree base: `.worktrees/` (all old worktrees cleaned up).

## Why subtree, not submodule

| | subtree | submodule |
|---|---|---|
| Clone work | none | requires `--recursive` |
| Patches layered on top | ✅ trivial, normal commits | ⚠ separate branch |
| Future sync | `git subtree pull` | `git submodule update --remote` |
| Transparent to users | ✅ | ❌ |
| Edit upstream files | visible diff | hidden in submodule |

Decision: subtree. User explicitly said "syncing upstream" should be Phase 4 — subtree pull is the canonical sync command.

## Global Constraints

- **Append-only rule still applies to `vendor/`**: never edit vendored files in-place. Wrap them in our own files.
- **Path preservation**: upstream paths stay 1:1 under `vendor/taskdog/` so diffing against `upstream/main` is trivial.
- **No `.gitignore` entries for `vendor/taskdog/`**: it MUST be tracked (we want it in git, not gitignored).
- **Upstream commits get their original hashes**: subtree merge preserves history; we don't rebase or rewrite.
- **5 vendored packages**: `taskdog-core` (334 files), `taskdog-server` (67), `taskdog-client` (49), `taskdog-ui` (317), `taskdog-mcp` (23) = ~790 files.
- **No CI changes yet**: vendor branch is just code, CI gates come in Phase 4.1.
- **No entry-point renames**: upstream's own entry points (`taskdog`, `taskdog-server`, etc.) stay as-is. Our `ikigai-chat` stays in `src/ikigai/pyproject.toml`.
- **Drift net stays untouched**: this phase adds zero changes to existing tests.

## File Structure

```
life/
├── vendor/
│   └── taskdog/                  ← subtree of Kohei-Wada/taskdog @ 2352f612
│       ├── .github/
│       ├── packages/
│       │   ├── taskdog-core/
│       │   ├── taskdog-server/
│       │   ├── taskdog-client/
│       │   ├── taskdog-ui/
│       │   └── taskdog-mcp/
│       ├── docs/
│       ├── pyproject.toml        ← upstream workspace pyproject
│       └── CLAUDE.md             ← upstream's own CLAUDE.md
├── docs/FORK_WORKFLOW.md         ← updated with Phase 4 status
└── .gitignore                    ← NEW: ignore vendor/taskdog/**/__pycache__/ etc.
```

---

### Task 1: Create worktree + branch

**Files:**
- Create: `.worktrees/phase-4/`

- [ ] **Step 1: Cut fresh branch + worktree from master**

```bash
cd "C:/Users/mathe/code_space/life-oss/life"
git worktree add .worktrees/phase-4 -b loop/phase-4-vendor-taskdog master
```

Expected: branch `loop/phase-4-vendor-taskdog` checked out at `.worktrees/phase-4/`, parent `master` (49815ac8).

- [ ] **Step 2: Verify worktree state**

```bash
cd .worktrees/phase-4
git status
git log --oneline -1
```

Expected: clean, `49815ac8 ... docs: FORK_WORKFLOW.md`.

- [ ] **Step 3: Commit marker (no work yet)**

No commit needed yet — vendoring is the next task.

---

### Task 2: Vendor upstream as subtree

**Files:**
- Create: `vendor/taskdog/` (~790 files, 5 packages)
- Modify: `.gitignore` (add 2 lines)

- [ ] **Step 1: Verify subtree support + upstream reachable**

```bash
cd .worktrees/phase-4
git merge -s subtree -h 2>&1 | head -3
git ls-remote upstream main | head -1
```

Expected: `git merge -s subtree` documentation shown; upstream HEAD `2352f6120f4941528ebfcd4e1dc203ec76896292` returned.

- [ ] **Step 2: Run subtree add**

```bash
cd .worktrees/phase-4
git subtree add --prefix=vendor/taskdog upstream/main
```

Expected: large merge commit added. Files appear under `vendor/taskdog/`. ~790 files.

⚠ This is a LARGE commit. May take 30-90s. Subtree copies ALL upstream history into our repo.

- [ ] **Step 3: Confirm 5 packages landed**

```bash
cd .worktrees/phase-4
ls vendor/taskdog/packages/
```

Expected: `taskdog-client  taskdog-core  taskdog-mcp  taskdog-server  taskdog-ui`.

- [ ] **Step 4: Confirm HEAD message**

```bash
cd .worktrees/phase-4
git log --oneline -3
```

Expected: top commit is the subtree merge, parent is `49815ac8`.

- [ ] **Step 5: Verify file count**

```bash
cd .worktrees/phase-4
git ls-files vendor/taskdog/ | wc -l
```

Expected: ~790 files (allow 780-810).

---

### Task 3: Add vendor cache patterns to .gitignore

**Files:**
- Modify: `.gitignore` (append 4 lines)

- [ ] **Step 1: Check current .gitignore**

```bash
cd .worktrees/phase-4
cat .gitignore 2>&1 | head -10
cat .gitignore 2>&1 | grep -c "__pycache__" || echo "0"
```

Expected: `.gitignore` exists, may already have `__pycache__/` (root pattern). Our addition is more specific.

- [ ] **Step 2: Append vendor-specific ignore patterns**

Append to `.gitignore`:

```
# vendored taskdog: don't track their build artifacts
vendor/taskdog/**/__pycache__/
vendor/taskdog/**/.pytest_cache/
vendor/taskdog/**/.ruff_cache/
vendor/taskdog/**/.mypy_cache/
vendor/taskdog/**/dist/
vendor/taskdog/**/build/
vendor/taskdog/**/*.egg-info/
```

⚠ These match only inside `vendor/taskdog/` — root project caches unaffected.

- [ ] **Step 3: Verify no real vendor file is accidentally ignored**

```bash
cd .worktrees/phase-4
git check-ignore vendor/taskdog/packages/taskdog-core/pyproject.toml 2>&1
git check-ignore vendor/taskdog/packages/taskdog-core/README.md 2>&1
```

Expected: both return non-zero exit (NOT ignored — these are real files).

- [ ] **Step 4: Check current tracked pyproject still tracked**

```bash
cd .worktrees/phase-4
git ls-files --error-unmatch vendor/taskdog/packages/taskdog-core/pyproject.toml
```

Expected: outputs the path (it IS tracked).

---

### Task 4: Verify vendored tree is sane

**Files:**
- (Read-only verification)

- [ ] **Step 1: Inspect vendored workspace pyproject**

```bash
cd .worktrees/phase-4
head -40 vendor/taskdog/pyproject.toml
```

Expected: `[tool.uv.workspace]` with `members = ["packages/*"]`.

- [ ] **Step 2: Check each package has a pyproject**

```bash
cd .worktrees/phase-4
for pkg in taskdog-core taskdog-server taskdog-client taskdog-ui taskdog-mcp; do
    test -f "vendor/taskdog/packages/$pkg/pyproject.toml" && echo "✓ $pkg" || echo "✗ MISSING: $pkg"
done
```

Expected: 5 ✓ lines.

- [ ] **Step 3: Spot-check taskdog-core layout**

```bash
cd .worktrees/phase-4
ls vendor/taskdog/packages/taskdog-core/src/
head -20 vendor/taskdog/packages/taskdog-core/src/taskdog_core/__init__.py 2>&1
```

Expected: directory `taskdog_core/` (or `src/taskdog_core/`) exists.

- [ ] **Step 4: Verify CLI entry point declared**

```bash
cd .worktrees/phase-4
grep -A2 "\[project.scripts\]" vendor/taskdog/packages/taskdog-ui/pyproject.toml | head -10
```

Expected: `taskdog = "taskdog.cli_main:main"` or similar.

---

### Task 5: Smoke test — install vendored core in throwaway venv

**Files:**
- (Verification only, no file changes)

- [ ] **Step 1: Create disposable venv**

```bash
cd .worktrees/phase-4
python -m venv .venv-vendor-test 2>&1 | tail -3
```

Expected: venv created.

- [ ] **Step 2: pip install taskdog-core (editable)**

```bash
cd .worktrees/phase-4
.venv-vendor-test/Scripts/python.exe -m pip install --quiet -e vendor/taskdog/packages/taskdog-core 2>&1 | tail -5
```

Expected: install succeeds. (May take 1-2 min — pulls in sqlalchemy, pydantic, etc.)

- [ ] **Step 3: Import test**

```bash
cd .worktrees/phase-4
.venv-vendor-test/Scripts/python.exe -c "from taskdog_core import __version__; print('taskdog-core version:', __version__)"
```

Expected: prints version string (e.g., `0.x.y`).

- [ ] **Step 4: Dispose test venv**

```bash
cd .worktrees/phase-4
rm -rf .venv-vendor-test
```

Expected: cleanup. This venv is NOT used for runtime — just install/import verification.

---

### Task 6: Update FORK_WORKFLOW.md with vendoring status

**Files:**
- Modify: `docs/FORK_WORKFLOW.md` (replace "Current state" section)

- [ ] **Step 1: Read current FORK_WORKFLOW.md state**

Already done — see `docs/FORK_WORKFLOW.md` lines 83-93.

- [ ] **Step 2: Replace "Current state (2026-09-10)" section**

Find:
```
## Current state (2026-09-10)

- Local master: ahead of upstream by 545 commits (our 8-month work)
- Upstream: ahead of local by 1136 commits (their development)
- Last full sync: NONE (fresh fork setup)

**Recommendation:** Don't attempt full merge until Phase 1 (ikigai-taskdog expansion)
is done. Merge in small batches:
- 1. Sync just the taskdog-relevant files (src/mesh/, pyproject.toml)
- 2. Skip our docs/scripts changes (they're IKIGAI-specific, won't conflict)
- 3. Re-test integration after each sync
```

Replace with:
```
## Current state (2026-09-10 — Phase 4 SHIPPED)

- **Vendored at `vendor/taskdog/`** (commit `2352f612`, upstream HEAD at vendoring time)
- 5 packages vendored: taskdog-core, taskdog-server, taskdog-client, taskdog-ui, taskdog-mcp
- Future upstream syncs: `git subtree pull --prefix=vendor/taskdog upstream main`
- Local master: ahead of upstream by 545 commits (our 8-month work) — IKIGAI layer
- Vendored tree: IS upstream at vendoring time, no customizations yet

### Sync strategy (post-Phase 4)
1. `git fetch upstream`
2. `git subtree pull --prefix=vendor/taskdog upstream main --squash` (squash to keep our history clean)
3. Resolve conflicts (should be ZERO — `vendor/taskdog/` is upstream-only)
4. Re-run smoke tests from `vibe-ops/` and `interfaces/`

### Future phases (on `loop/phase-4-vendor-taskdog` branch)
- Phase 4.1: Layer IKIGAI customizations as thin wrappers in `src/ikigai/` (NOT editing `vendor/taskdog/*`)
- Phase 4.2: Replace `src/mesh/__main__ikigai_taskdog*.py` gambiarra with `vendor.taskdog_client.TaskdogClient` calls
- Phase 4.3: Wire upstream `taskdog-mcp` into UnifiedMCPGateway alongside `ikigai-taskdog-mcp`
```

- [ ] **Step 3: Verify diff**

```bash
cd .worktrees/phase-4
git diff docs/FORK_WORKFLOW.md | head -40
```

Expected: 2 sections changed, additions clearly visible.

---

### Task 7: Commit + push branch

**Files:**
- (git only)

- [ ] **Step 1: Stage changes**

```bash
cd .worktrees/phase-4
git add -A vendor/taskdog/
git add .gitignore docs/FORK_WORKFLOW.md
git status --short | head -10
```

Expected: thousands of `A vendor/taskdog/...` lines + 2 file modifications.

- [ ] **Step 2: Write commit message to temp file (Windows heredoc safety)**

```bash
cd .worktrees/phase-4
cat > /tmp/commit-msg.txt << 'EOF'
vendor(taskdog): subtree import upstream @ 2352f612

Bring the full Kohei-Wada/taskdog monorepo into our project as
vendor/taskdog/. Upstream stays pristine; future IKIGAI customizations
will be thin wrappers in src/ikigai/, NOT edits to vendored files.

Vendored (5 packages, ~790 files):
- taskdog-core: domain + SQLite + SQLAlchemy + Alembic
- taskdog-server: FastAPI REST API
- taskdog-client: HTTP client (used by CLI/TUI/MCP)
- taskdog-ui: Click + Rich CLI + Textual TUI
- taskdog-mcp: FastMCP server for Claude Desktop

Sync strategy: `git subtree pull --prefix=vendor/taskdog upstream main`
(preserves upstream's full commit history in our repo).

Replaces: src/mesh/__main__ikigai_taskdog.py + __main__ikigai_taskdog_tui.py
gambiarra (4 subcommands, direct SQLite). Phase 4.2 will rewire those to
use vendor.taskdog_client.TaskdogClient.

Files:
- vendor/taskdog/ (NEW, 790 files)
- .gitignore (NEW vendor/taskdog cache patterns)
- docs/FORK_WORKFLOW.md (Phase 4 sync strategy)

Phase 4.1+ deferred: IKIGAI customizations, MCP wiring, agent tool integration.
EOF
echo "commit message written:"
cat /tmp/commit-msg.txt | head -5
```

⚠ Use temp file, NOT heredoc `@'...'@` per [[bash-heredoc-at-leak]].

- [ ] **Step 3: Commit using message file**

```bash
cd .worktrees/phase-4
git commit -F /tmp/commit-msg.txt
```

Expected: large commit. Output ends with `[loop/phase-4-vendor-taskdog <hash>] vendor(taskdog): ...`.

- [ ] **Step 4: Verify commit landed**

```bash
cd .worktrees/phase-4
git log --oneline -3
git show --stat HEAD | head -10
git show --stat HEAD | tail -3
```

Expected: top commit is the vendor commit. Stat shows ~790 files changed.

- [ ] **Step 5: Push branch (no PR yet, user decides)**

```bash
cd .worktrees/phase-4
git push -u origin loop/phase-4-vendor-taskdog 2>&1 | tail -10
```

Expected: branch pushed. If rejected (remote has it), do `git push --force-with-lease`.

---

### Task 8: Final report

**Files:**
- Create: `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\phase-4-vendored-2026-09-10.md`

- [ ] **Step 1: Capture metrics**

```bash
cd .worktrees/phase-4
COMMIT=$(git rev-parse HEAD)
FILES=$(git ls-files vendor/taskdog/ | wc -l)
echo "commit: $COMMIT"
echo "files: $FILES"
```

- [ ] **Step 2: Write memory entry**

Create `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/phase-4-vendored-2026-09-10.md` with:

```markdown
---
name: phase-4-vendored-2026-09-10
description: Kohei-Wada/taskdog vendored at vendor/taskdog/ (5 packages, ~790 files) — Phase 4 SHIPPED
metadata:
  type: project
---

Vendored the upstream Kohei-Wada/taskdog monorepo into our project at `vendor/taskdog/` (commit `2352f612` at vendoring time). Five packages: taskdog-core (334), taskdog-server (67), taskdog-client (49), taskdog-ui (317), taskdog-mcp (23). Subtree-merged — full upstream history preserved.

Branch: `loop/phase-4-vendor-taskdog`, worktree at `.worktrees/phase-4/`. Replacement for the ikigai-taskdog gambiarra (commit batch removed; backup at branch `backup-loop-prod-ready-2026-09-10`).

**Why:** User realized the gambiarra was ~15% of upstream (4 of 20+ subcommands, no FastMCP, no HTTP server). Subtree gives us clean future syncs without submodule's `--recursive` quirks.

**How to apply:** Future IKIGAI customizations are thin wrappers in `src/ikigai/` that import from `vendor.taskdog_*` — never edit vendored files in place. Sync command: `git subtree pull --prefix=vendor/taskdog upstream main`. Next phases: 4.1 (customizations), 4.2 (replace gambiarra with TaskdogClient), 4.3 (wire taskdog-mcp into UnifiedMCPGateway).

**Why:** Vendoring is append-only — upstream tracks upstream, our wrapper code lives in our tree.
```

- [ ] **Step 3: Add memory pointer**

Append to `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md`:

```
- [Phase 4 vendor SHIPPED](phase-4-vendored-2026-09-10.md) — Kohei-Wada/taskdog @ vendor/taskdog/; 5 pkgs; subtree-merged; branch loop/phase-4-vendor-taskdog
```

- [ ] **Step 4: Final status report to user**

Print summary:
- Vendored commit hash
- Branch name + worktree path
- File count
- Next phase (4.1: IKIGAI customizations) is open question for user

---

## Self-Review

✅ **Spec coverage:** All 5 upstream packages vendored (taskdog-core, taskdog-server, taskdog-client, taskdog-ui, taskdog-mcp). Sync strategy documented. Branch pushed.

✅ **Placeholder scan:** No "TODO" or "implement later" in steps. Every command shown. Test verification at Task 5.

✅ **Type consistency:** Vendor dir path `vendor/taskdog/` consistent across all tasks. Subtree commands use `--prefix=vendor/taskdog` consistently.

✅ **Critical files mapped:** vendor/taskdog/, .gitignore, docs/FORK_WORKFLOW.md, memory entry.

✅ **Windows safety:** temp-file commit message per [[bash-heredoc-at-leak]].

---

## What This Plan Does NOT Do

- Does NOT edit any vendored file (append-only — never touch `vendor/taskdog/*`).
- Does NOT add `taskdog` to our root `pyproject.toml` (uv workspace conflict; future phase).
- Does NOT replace the ikigai-taskdog gambiarra in `src/mesh/` (Phase 4.2).
- Does NOT wire `taskdog-mcp` into UnifiedMCPGateway (Phase 4.3).
- Does NOT register `taskdog` as a CLI entry point (upstream stays as-installed-via-uvx).
- Does NOT add CI gates for vendored tree (Phase 4.1).
- Does NOT add IKIGAI customizations to vendored packages (Phase 4.1).
- Does NOT merge to master (user decides).

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Subtree pull later introduces conflicts | Low | `--squash` keeps our tree clean; future merges are into pristine subtree |
| Vendored `pyproject.toml` conflicts with ours at install time | Medium | Don't merge `vendor/taskdog/pyproject.toml` into our root; install upstream packages separately |
| 790 files in single commit clutters history | Medium | Document in `docs/FORK_WORKFLOW.md`; squash-equivalent on future pulls |
| User wants different path (not `vendor/taskdog/`) | Medium | Decision is committed; can `git mv` in follow-up if needed |
