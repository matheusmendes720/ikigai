# Fork Workflow — Kohei-Wada/taskdog integration

UX 2026-09-10: configured `upstream` remote pointing to the ORIGINAL
taskdog project (Kohei-Wada/taskdog). Our work builds ON TOP of taskdog
with IKIGAI-specific customizations. This document describes how to
keep our fork in sync with upstream.

## Remotes

```bash
origin   → https://github.com/matheusmendes720/ikigai.git   (our fork)
upstream → https://github.com/Kohei-Wada/taskdog.git       (original taskdog)
```

## Sync workflow

### 1. Fetch latest from upstream

```bash
git fetch upstream
```

### 2. Check what changed

```bash
# Show recent commits on upstream main
git log upstream/main --oneline | head -20

# Show how far we're behind (commits we're missing)
git rev-list --left-right --count master...upstream/main
# Output: <behind>  <ahead>
# Example: 1136  545 → we're 1136 commits behind, 545 ahead
```

### 3. Merge or rebase

```bash
# Option A: merge commit (preserves history, easier to revert)
git merge upstream/main
# Resolve conflicts if any, then git commit

# Option B: rebase (linear history, rewrites local commits)
git rebase upstream/main
# Resolve conflicts at each commit
```

### 4. Verify after sync

```bash
# Run all tests
.venv/Scripts/python.exe -m pytest src/ikigai/tests/ -q

# Verify our customizations still work
.venv/Scripts/ikigai-chat.exe --no-chat
.venv/Scripts/ikigai-taskdog.exe list
```

## Customization strategy

When merging upstream, preserve these IKIGAI-specific customizations:

- `pyproject.toml` [tool.poetry.scripts]:
  - `ikigai-chat` (our harness)
  - `ikigai-taskdog` (our taskdog CLI)
  - `ikigai-taskdog-mcp` (our MCP server)
  - `ikigai-maintainer-mcp` (orchestrator)
  - `ikigai-deep-agent` (alias)

- `src/mesh/__main__ikigai_taskdog.py` (our CLI, NOT upstream's)
- `src/mesh/__main__ikigai_taskdog_tui.py` (our TUI)
- `src/ikigai/src/agents/persona.py` (IKIGAI system prompt)
- `.deepagents/` (if reintroduced)
- `docs/START_HERE.md` (our user guide)
- `scripts/ikigai-shell.ps1` (PowerShell activator)

## Merge conflict avoidance

When upstream renames files, prefer to:
1. Keep upstream's renamed structure
2. Re-apply our customizations on top
3. Update `pyproject.toml` [tool.poetry.scripts] to match new module paths

## Current state (2026-09-10)

- Local master: ahead of upstream by 545 commits (our 8-month work)
- Upstream: ahead of local by 1136 commits (their development)
- Last full sync: NONE (fresh fork setup)

**Recommendation:** Don't attempt full merge until Phase 1 (ikigai-taskdog expansion)
is done. Merge in small batches:
- 1. Sync just the taskdog-relevant files (src/mesh/, pyproject.toml)
- 2. Skip our docs/scripts changes (they're IKIGAI-specific, won't conflict)
- 3. Re-test integration after each sync
