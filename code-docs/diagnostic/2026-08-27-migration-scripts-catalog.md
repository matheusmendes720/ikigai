# Migration Scripts Catalog — 2026-08-27

> **Companion doc** to `2026-08-27-master-system-diagnostic.md`. Concrete specs
> for migration scripts needed before code changes begin. No code yet — pure
> planning artifacts (input/output contract, edge cases, rollback).
>
> **Status:** 🟡 Draft — diagnostic + planning only

---

## 1. Migration Inventory

| ID | Migration | Severity | Blocking | Effort | Sprint |
|----|-----------|:--------:|:--------:|-------:|--------|
| **MIG-1** | Schema split-brain reconciliation | 🔴 Critical | 6+ issues | 5 days | Sprint 2 |
| **MIG-2** | PAV CLI restoration from `604d6af` | 🔴 Critical | All tests | 3 days | Sprint 1 |
| **MIG-3** | Vault B1 blocker graduation years | 🟠 High | H4 | 1 day | Sprint 2 |
| **MIG-4** | `_PersistentRepo` path → `~/.life-operational/` | 🟡 Medium | P3 | 1 day | Sprint 2 |
| **MIG-5** | IKIGAI 5-vector vs 4-vector reconciliation | 🟠 High | G2 | 1 day | Sprint 4 |
| **MIG-6** | Hard-coded paths → env-var config | 🟠 High | S-H7 | 2 days | Sprint 3 |
| **MIG-7** | Stray 0-byte files + orphan test dirs cleanup | 🟡 Medium | P7+P2 | 0.5 day | Sprint 4 |
| **MIG-8** | Dual CLAUDE.md scope clarification | 🔵 Info | P8 | 0.5 day | Sprint 4 |

**Total: 8 migrations, 14 person-days**

---

## 2. MIG-1 — Schema Split-Brain Reconciliation

### Problem

Two competing schemas for `plan_entities` table:
- **Canonical 24-col** (`sqlite_adapter.py:18-80`): has triggers, history, indexes, full frontmatter contract
- **Runtime 11-col** (`commit.py:58-118` + `server.py:347-357`): used by every writer, no triggers, no history

`SQLiteAdapter` is defined but **never called** by `commit_node` or MCP `ikigai_plan_cycle`.

### Input/Output Contract

**Input:**
- `~/.ikigai/plan_entities.db` (runtime 11-col, populated)
- `data/matheus/` (markdown vault, canonical)
- `src/ikigai/propagation/sqlite_adapter.py` (canonical 24-col schema)

**Output:**
- Single canonical 24-col table
- All writers (`commit_node`, `ikigai_plan_cycle` MCP) route through `SQLiteAdapter`
- Old runtime table archived to `plan_entities_legacy_<YYYYMMDD>.db`
- Migration report at `~/.ikigai/migrations/mig-1-report.md`

### Script Spec

```python
# scripts/migrations/mig-1-reconcile-schema.py
# usage: poetry run python scripts/migrations/mig-1-reconcile-schema.py [--dry-run]

class SchemaReconciler:
    """Migrate runtime 11-col → canonical 24-col."""

    def __init__(self, db_path: Path, dry_run: bool = True) -> None: ...
    def analyze(self) -> AnalysisReport:
        """Count rows in runtime table; identify columns missing in canonical."""
    def migrate(self) -> MigrationReport:
        """CREATE TABLE canonical_24col → INSERT FROM runtime → DROP runtime → RENAME."""
    def verify(self) -> VerificationReport:
        """Row count match + spot-check 5 entities by ueid."""
    def archive(self) -> Path:
        """Copy runtime DB to plan_entities_legacy_<YYYYMMDD>.db before DROP."""
    def rollback(self, archive_path: Path) -> None:
        """Restore from archive if migration fails verification."""
```

### Edge Cases

| Case | Detection | Handling |
|------|-----------|----------|
| Runtime DB has rows with NULL in canonical-required cols | `analyze()` | Add DEFAULT values per column contract |
| `ueid` collisions between runtime and markdown vault | `verify()` | Keep markdown as truth; runtime wins only if newer mtime |
| Migration interrupted mid-transaction | `--dry-run` first; idempotent | Wrap in `BEGIN IMMEDIATE; ... COMMIT` |
| Disk space insufficient for archive | `archive()` | Pre-check `Path.stat().st_size * 2 < free_space` |
| Concurrent writers during migration | advisory lock | Acquire `~/.ikigai/.migration.lock` before starting |

### Rollback Plan

1. Stop all writers (kill IKIGAI processes)
2. `cp plan_entities_legacy_<YYYYMMDD>.db plan_entities.db`
3. Revert `sqlite_adapter.py` to pre-migration state
4. Restart processes
5. Document incident in `docs/.sdd-progress.md`

### Test Cases

- [ ] Empty runtime DB → canonical created empty
- [ ] 10 runtime rows → all 10 migrated, schema verified
- [ ] Missing canonical col values → defaults applied correctly
- [ ] Disk full → fails fast with clear error
- [ ] Interrupted migration → rollback succeeds
- [ ] Concurrent lock → second instance exits with "already running"

---

## 3. MIG-2 — PAV CLI Restoration from `604d6af`

### Problem

Commit `604d6af` deleted `apps/cli`, `apps/tui`, `home_v2`, etc. Editable-install
`.pth` files under `.venv/Lib/site-packages/` still point at deleted paths.
Tests in `tests/unit/cli/` fail.

### Input/Output Contract

**Input:**
- Git history: `git log --before=2025-XX-XX -- apps/cli/` (pre-deletion state)
- Current `.venv/Lib/site-packages/operational*.pth` (broken paths)
- Current `pyproject.toml` workspace members (missing cli/tui)

**Output:**
- Restored `apps/cli/src/operational/cli/` from pre-deletion commit
- Restored `apps/tui/src/operational/tui/` (or deleted from workspace if deprecated)
- `.pth` files regenerated by `uv sync`
- `pyproject.toml` updated to include cli/tui workspaces
- All `tests/unit/cli/` tests pass

### Script Spec

```bash
# scripts/migrations/mig-2-restore-pav-cli.sh
# usage: bash scripts/migrations/mig-2-restore-pav-cli.sh

# 1. Find last commit before 604d6af that contained apps/cli
BEFORE_DELETION=$(git log --before="2025-XX-XX" --diff-filter=A --name-only -- apps/cli/src/operational/cli/app.py | head -1 | awk '{print $1}')

# 2. Restore apps/cli from that commit
git checkout $BEFORE_DELETION -- apps/cli/

# 3. Decide on apps/tui (deprecated per AI-native migration?)
if [ "$RESTORE_TUI" = "false" ]; then
  rm -rf apps/tui/
fi

# 4. Regenerate .pth files
cd life-ops/operational
uv sync --all-packages
uv run pytest tests/unit/cli/  # verify
```

### Edge Cases

| Case | Detection | Handling |
|------|-----------|----------|
| Pre-deletion commit has incompatible dependencies | diff against `pyproject.toml` | Add missing deps; commit `uv.lock` change |
| `apps/cli/` was renamed during the deletion | `git log --follow` | Find original path |
| Newer commits depend on the deletion | `git log --all --grep="604d6af"` | Manual review of dependent commits |
| `.pth` files already manually fixed | `grep` for non-deleted path | Skip regeneration |
| Workspace member list in `pyproject.toml` differs | parse + compare | Update to include restored packages |

### Rollback Plan

1. `git checkout 604d6af -- apps/cli/` (restore deletion)
2. `uv sync` (regenerate `.pth` files to broken state)
3. Document incident

### Test Cases

- [ ] `uv run pav --help` returns help text
- [ ] `uv run operational --help` returns help text
- [ ] `uv run pytest tests/unit/cli/` all pass
- [ ] `.pth` files contain valid paths to `apps/cli/src`
- [ ] Workspace member list matches restored packages

---

## 4. MIG-3 — Vault B1 Blocker Graduation Years

### Problem

Vault record marks B1 Blocker as RESOLVED, but taskdog #10 and tuiboard B1
still PENDING. Either:
- (a) graduation years supplied → close interfaces
- (b) vault record reverted to OPEN

### Input/Output Contract

**Input:** Current vault record + taskdog #10 + tuiboard B1 status
**Output:** Consistent state across 3 systems

### Script Spec

```python
# scripts/migrations/mig-3-reconcile-b1-blocker.py
# usage: poetry run python scripts/migrations/mig-3-reconcile-b1-blocker.py [--graduate|--revert]

def graduate(graduation_years: dict[str, int]) -> ReconciliationReport:
    """Mark taskdog #10 and tuiboard B1 as COMPLETED with graduation years."""
    # taskdog: patch status=completed, add graduation_year tag
    # tuiboard: PATCH /board/tasks/<id> { status: "done", graduation_year: ... }
    # vault: keep RESOLVED status

def revert() -> ReconciliationReport:
    """Mark vault record back to OPEN with reason."""
    # vault: frontmatter status = "open", add reconciliation_note
```

### Decision Required (user)

Which path? (a) or (b)? Affects all 3 systems.

---

## 5. MIG-4 — `_PersistentRepo` Path Migration

### Problem

15 `_PersistentRepo` singletons in `cli/state.py:39-86` write to `~/.time-tasker/*.json`.
Should move to `~/.life-operational/` for consistency with PAVConstants.

### Input/Output Contract

**Input:** 15 JSON files at `~/.time-tasker/`
**Output:** Same files at `~/.life-operational/` + symlink (optional) for backward compat

### Script Spec

```python
# scripts/migrations/mig-4-relocate-persistent-repo.py
# usage: poetry run python scripts/migrations/mig-4-relocate-persistent-repo.py [--copy|--move]

def relocate(strategy: Literal["copy", "move"]) -> MigrationReport:
    """Move/copy 15 JSON files + update env-var default in PAVConstants."""
    # 1. mkdir -p ~/.life-operational
    # 2. for each *.json: shutil.copy2 or shutil.move
    # 3. update PAVConstants.DEFAULT_DATA_DIR = "~/.life-operational"
    # 4. if strategy=="copy": leave ~/.time-tasker intact for rollback
```

### Rollback Plan

If `copy` strategy was used: `cp -r ~/.life-operational ~/.time-tasker`.
If `move` strategy: restore from backup created at `~/.time-tasker.backup-<YYYYMMDD>/`.

---

## 6. MIG-5 — IKIGAI 5-Vector vs 4-Vector Reconciliation

### Problem

Root docs (README, CLAUDE.md) advertise 5 vectors; PRD-07 documents 4 vectors.

### Decision Required (user)

- **Option A:** Promote PRD-07 to 5 vectors (add Course)
- **Option B:** Roll root docs back to 4 vectors (remove Course)

### Script Spec

```python
# scripts/migrations/mig-5-reconcile-vector-count.py

def option_a_promote_to_5() -> MigrationReport:
    """Update PRD-07 to document Course vector."""
    # Add Course vector definition, scoring rubric, propagation rules
    # Update PRD-07 examples + verification matrix

def option_b_revert_to_4() -> MigrationReport:
    """Remove Course from root docs + 16 entity definitions."""
    # Remove Course from README.md, CLAUDE.md, ARCHITECTURE_INDEX.md
    # Remove from IKIGAiProfile, IKIGAiVectorEntity
    # Update all tests that reference 5 vectors
```

### Affected Files (estimate)

| Path | Count |
|------|------:|
| `life/CLAUDE.md`, `README.md`, `ARCHITECTURE_INDEX.md` | 3 |
| `vibe-ops/planning/PRD-07.md` | 1 |
| `life-ops/ikigai/src/ikigai/entities/{profile,vector}.py` | 2 |
| `data/matheus/dreams/`, `objectives/`, `projects/` (frontmatter) | 4-6 |
| `tests/` (5-vector assumptions) | ~10 |
| **Total** | ~25 |

---

## 7. MIG-6 — Hard-coded Paths → Env-var Config

### Problem

3 hard-coded paths in `src/agents/tools.py`:
- `_SOLVERFORGE_CLI` (638-640)
- `_TUIBOARD_MCP_CMD` (729-733)
- `_TASKDOG_CLI` (910-912)

Move binary → silent break. No env-var override.

### Script Spec

```python
# scripts/migrations/mig-6-extract-paths-to-config.py

def extract_to_config() -> MigrationReport:
    """Move hard-coded paths to ~/.ikigai/config.toml + env-var fallback."""
    # 1. Create config schema in src/ikigai/config.py
    # 2. Generate ~/.ikigai/config.toml with current defaults
    # 3. Update tools.py to read from config (with env-var override)
    # 4. Add startup warning if config missing
    # 5. Document env vars in README
```

### Config Schema (proposed)

```toml
# ~/.ikigai/config.toml
[externals]
solverforge_cli = "~/code_space/apps/calendar/solverforge-calendar/target/release/solverforge-calendar-cli.exe"
tuiboard_mcp_cmd = ["~/.bun/bin/bun.exe", "run", "~/code_space/apps/kanban/tuiboard/bin/tuiboard-mcp.ts"]
taskdog_cli = "~/code_space/apps/dev-tools/taskdog/.venv/Scripts/taskdog.exe"

[paths]
mcp_gateway_log = "~/.ikigai/logs/mcp-gateway.log"
plan_entities_db = "~/.ikigai/plan_entities.db"
checkpoint_db = "~/.ikigai/ikigai_checkpoints.db"
```

### Env-var Overrides

- `IKIGAI_SOLVERFORGE_CLI`
- `IKIGAI_TUIBOARD_CMD`
- `IKIGAI_TASKDOG_CLI`
- `IKIGAI_LOG_DIR`
- `IKIGAI_DATA_DIR`

---

## 8. MIG-7 — Repo Hygiene Cleanup

### Problem

- Stray 0-byte files at repo root (`2`, `0`, `4}`, `dict[str`, `ISO`, `None`, `String`, `bool`, `new`)
- Orphan test dirs (`tests/tui/`, `tests/ui/` after `604d6af`)
- Throwaway files at `life-ops/operational/` root (`output.txt`, `CheckResult`, `not`)

### Script Spec

```bash
# scripts/migrations/mig-7-cleanup-repo-hygiene.sh

# 1. Delete stray 0-byte files
find . -maxdepth 1 -type f -size 0 -delete  # exclude .gitkeep patterns

# 2. Decide on tests/tui and tests/ui
if [ -z "$(ls apps/tui/ 2>/dev/null)" ]; then
  rm -rf tests/tui/ tests/ui/
fi

# 3. Add .gitignore patterns
cat >> .gitignore <<'EOF'
# Crash/typo artifacts
^[0-9]+$
^[a-z]+}$
^[A-Z][a-z]+$
^dicts*\[str
^new$
EOF
```

---

## 9. MIG-8 — Dual CLAUDE.md Scope Clarification

### Problem

Two CLAUDE.md files describe overlapping scopes:
- `C:\Users\mathe\code_space\life-oss\CLAUDE.md` (monorepo)
- `C:\Users\mathe\code_space\life-oss\life\CLAUDE.md` (life submodule)

### Decision Required (user)

- **Option A:** Keep both, add explicit "scope boundary" header to each
- **Option B:** Merge into one, prefer life submodule as canonical

### Script Spec

```python
# scripts/migrations/mig-8-clarify-claude-md-scope.py

def option_a_add_boundary_headers() -> MigrationReport:
    """Add '## Scope' section to top of each file."""
    # Add to root: "Scope: monorepo-level concerns only"
    # Add to life submodule: "Scope: life/ subsystem only"

def option_b_merge() -> MigrationReport:
    """Merge root into life submodule, delete root."""
    # Move unique content from root → life/CLAUDE.md
    # Delete root CLAUDE.md
```

---

## 10. Migration Order (dependency-aware)

```
MIG-2 (PAV CLI) ──→ MIG-7 (cleanup) ──→ MIG-8 (CLAUDE.md)
                ↘
MIG-1 (schema) ──→ MIG-3 (B1) ──→ MIG-5 (vectors)
                ↘
MIG-6 (paths) ──→ MIG-4 (PersistentRepo)
```

**Sprint 1:** MIG-2 + MIG-7 (cleanup)
**Sprint 2:** MIG-1 + MIG-3 + MIG-6
**Sprint 4:** MIG-4 + MIG-5 + MIG-8

---

## 11. Verification Commands (post-migration)

```bash
# MIG-1
sqlite3 ~/.ikigai/plan_entities.db ".schema plan_entities" | wc -l  # expect 24+ lines

# MIG-2
cd life-ops/operational && uv run pytest tests/unit/cli/ -v

# MIG-3
ikigai-cli cycle status --json | jq '.b1_blocker'

# MIG-4
ls ~/.life-operational/ | wc -l  # expect 15 files

# MIG-5
ikigai vector list --json | jq 'length'  # expect 4 or 5 per user choice

# MIG-6
ikigai config show --json | jq '.externals'

# MIG-7
ls "C:\Users\mathe\code_space\life-oss\life\" | grep -E "^[0-9]+$|^[a-z]+\}$" | wc -l  # expect 0

# MIG-8
head -3 CLAUDE.md life/CLAUDE.md  # both should have scope section
```

---

*Migration Scripts Catalog — v1.0 — 2026-08-27 — planning only, no code yet*
