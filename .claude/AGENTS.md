# AGENTS.md — `.claude/`

**Score 13 (246 tracked files, 6 subdirectories, 186 tracked files outside this directory reference it) — created: the only location in its group that deserves its own file.** The harness is the repo's agent-facing surface; nothing here is imported by production code.

## OVERVIEW
`.claude/` is the **local agent harness**: 246 tracked files — 222 Markdown, 12
code (8 `.sh`, 1 `.js`, 1 `.ts`, 1 `.bat`, 1 `.ps1`), 0 Python. No tracked
Python file imports anything under `.claude/`; the published client surface is
`src/transport/mcp_server.py` over the data layer.

It is published (so a cloned cloud agent inherits the context) but it is not
canonical: it holds prompts, skills and loop scripts, and it drifts from
`.agents/` by design.

## STRUCTURE
```
.claude/
├── agents/     # 22 prompt definitions: core/ loop/ consensus/ sparc/ swarm/ browser/
├── commands/   # 148 slash-command prompts in 13 namespaces
├── helpers/    # 5 files: daemon supervisor + notify-wrap (bash)
├── loop/       # 18 files: the tick triad, constitution/roadmap/tasks state
├── skills/     # 48 files = 39 `SKILL.md` manifests
├── workflows/  # 1 JS workflow file
└── settings.json · settings.local.json · proven-config.json · .proven-config-version
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Milestone / task tracker | `loop/roadmap.md`, `loop/tasks.md` | the canonical ids (`M198`, `T-D5`, …) that `specs/` references |
| Loop constitution | `loop/constitution.md` | the values every loop artifact cites |
| Tick driver | `loop/loop-tick.sh` · `loop-tick.bat` · `loop-tick.ts` | one driver in three languages — keep them in sync |
| Daemon supervision | `helpers/daemon-manager.sh`, `helpers/daemon-manager-schedules.sh` | listed in `helpers/helpers.manifest.json` |
| Notification wrapping | `helpers/notify-wrap.sh` | used by the pytest wrapper in `tests/loop/` |
| Agent prompts | `agents/core/planner.md`, `agents/loop/*.md`, `agents/consensus/`, `agents/sparc/`, `agents/swarm/` | 22 files |
| Skill manifests | `skills/<name>/SKILL.md` | 39 skills, YAML frontmatter |
| Harness config | `settings.json`, `proven-config.json` | 9 hook events; the "proven config" guard |

## CONVENTIONS
- **`.claude/skills/` and `.agents/skills/` are two parallel trees.** 32 skill
  names are shared; only 7 are byte-identical, the other 25 differ by a pure
  vendor substitution (`Claude Code` vs `Codex`). 27 skills exist only under
  `.agents/skills/`, 7 only under `.claude/skills/`. No test compares them.
- **Shell is the only executable surface here** (8 `.sh`); `helpers/` is bash
  plus a manifest, and `loop/` mirrors one tick in sh/bat/ts.
- **A skill is a manifest, not code**: `SKILL.md` carries YAML frontmatter
  (`name`, `description`, `version`, `entry_point`, `triggers`).
- **`proven-config.json` + `.proven-config-version`** move together — the
  version file pins the config format.

## ANTI-PATTERNS
- **Never treat the four `ikigai-*` skills as manifests.** `ikigai-daily`,
  `-weekly`, `-monthly`, `-quarterly` are one-line files holding a
  machine-specific absolute path to `src/ikigai/src/agents/v2/skills/<cadence>.md`
  — a directory with 0 tracked files. The path is wrong for every other clone.
- **Never call `agents.v2.skills.*`.** `taskdog-triage` and
  `vault-intent-extract` declare `entry_point: agents.v2.skills.*.run_skill`,
  and `src/mesh/taskdog_chat.py` imports `agents.v2.skills` (lines 229, 300,
  319). The package is absent, so `/triage` and `/extract` fail at runtime
  instead of running.
- **Never assume the hooks are wired.** `settings.json` and `.codex/hooks.json`
  invoke `.claude/helpers/{hook-handler.cjs,auto-memory-hook.mjs,statusline.cjs}`;
  `.claude/helpers/` holds 5 other files and none of those three. The hooks
  fail silently (the `.codex` copy falls back to `%USERPROFILE%`).
- **Never reintroduce `.claude/loop/mcp_bridge.py`** — it was removed with the
  PC-only scope (ADR-037) and `loop-tick.sh` sets `VALID_GRAPH_KEYS=""`
  accordingly.
- **Never treat `.claude-flow/` or `.mcp.json` as sources.** `.mcp.json` is
  absent from git and from disk; `.claude-flow/` holds 0 tracked files and is
  gitignored — any copy on a dev box is untracked runtime state.
- **Never edit one skill tree and leave the other.** With 25 shared skills
  differing only by vendor substitution, a one-sided edit stays invisible until
  someone reads the other tree.
