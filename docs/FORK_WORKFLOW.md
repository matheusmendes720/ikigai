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

## Current state (2026-09-10 — Phase 4 SHIPPED)

- **Vendored at `vendor/taskdog/`** (commit `2352f612`, upstream HEAD at vendoring time)
- 5 packages vendored: taskdog-core (334), taskdog-server (67), taskdog-client (49), taskdog-ui (317), taskdog-mcp (23) = ~865 files, ~106k LOC
- Vendored via `git subtree add --prefix=vendor/taskdog upstream/main` on branch `loop/phase-4-vendor-taskdog`
- `.gitignore` already covers vendor caches via `**/__pycache__/` etc. (no edits needed)
- Local master: ahead of upstream by 545 commits (our 8-month IKIGAI work)
- Vendored tree: IS upstream at vendoring time, NO IKIGAI customizations yet

### Sync strategy (post-Phase 4)
1. `git fetch upstream`
2. `git subtree pull --prefix=vendor/taskdog upstream main --squash` (squash keeps our history clean)
3. Resolve conflicts (should be ZERO — `vendor/taskdog/` is upstream-only)
4. Re-run smoke tests from `vibe-ops/` and `interfaces/`

### Future phases (on `loop/phase-4-vendor-taskdog` branch)
- Phase 4.1: Layer IKIGAI customizations as thin wrappers in `src/ikigai/` (NEVER edit `vendor/taskdog/*` in place — append-only)
- Phase 4.2: Replace `src/mesh/__main__ikigai_taskdog*.py` gambiarra with `vendor.taskdog_client.TaskdogClient` calls
- Phase 4.3: Wire upstream `taskdog-mcp` into UnifiedMCPGateway alongside `ikigai-taskdog-mcp`
