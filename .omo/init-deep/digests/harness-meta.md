# DIGEST — harness-meta subtree (`.claude/`, `.agents/`, `.codex/`)

## LOCATIONS WRITTEN

none — the harness and skills trees are covered by the root file

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `.claude/` | 13 | root `AGENTS.md` — local-only harness; add one STRUCTURE line + a WHERE TO LOOK row |
| `.claude/skills/` | 10 | root `AGENTS.md` — 39 `SKILL.md` manifests (a `.claude/` entry covers them) |
| `.claude/agents/` | 10 | root `AGENTS.md` — 22 prompt definitions, 18 agent ids |
| `.claude/commands/` | 7 | root `AGENTS.md` — 148 slash-command prompts in 13 namespaces |
| `.claude/loop/` | 4 | root `AGENTS.md` — 18 files: tick triad + constitution/roadmap state |
| `.claude/helpers/` | 6 | root `AGENTS.md` — 5 files: daemon-supervisor bash |
| `.claude/workflows/` | 2 | root `AGENTS.md` — 1 JS workflow file |
| `.agents/skills/` | 7 | root `AGENTS.md` — 59 skill dirs, the Codex-flavoured twin of `.claude/skills/` |
| `.agents/` | 5 | root `AGENTS.md` — single child `skills/` |
| `.codex/` | 1 | root `AGENTS.md` — 2 config files (`config.toml`, `hooks.json`) |

Scores: factor order = file count (3, >20) / subdirs (2, >5) / code ratio (2, >70%) / own config (1) / package root (2) / symbols (2, >30) / exports (2, >10) / inbound refs (3, >20).
`.claude/` = 3 (246 files) + 2 (6 subdirs) + 0 (12/246 = 4.9% code) + 1 (`settings.json`, `proven-config.json`) + 0 (no package root) + 2 (59 symbols: 26 shell fns, 19 TS, 14 JS) + 2 (26 sourceable shell fns) + 3 (186 outside files) = 13.
`.claude/skills/` = 3 (48) + 2 (39) + 0 (0/48 code) + 0 + 0 + n/m (Markdown) + 2 (39 skill manifests) + 3 (37 outside) = 10.
`.claude/agents/` = 3 (22) + 2 (7) + 0 (0/22 code) + 0 + 0 + n/m + 2 (18 agent ids) + 3 (35 outside) = 10.
`.claude/commands/` = 3 (148) + 2 (13) + 0 (0/148 code) + 0 + 0 + n/m + 2 (148 command files) + 0 (12 outside) = 7.
`.claude/loop/` = 0 (18 files) + 0 (2 subdirs) + 0 (8/18 = 44% code) + 1 (`schedules.json`) + 0 + 0 (24 symbols) + 0 (<10 exports) + 3 (82 outside) = 4.
`.claude/helpers/` = 0 (5) + 0 (0) + 0 (3/5 = 60%) + 1 (`helpers.manifest.json`) + 0 + 0 (21 symbols) + 2 (21 shell fns) + 3 (29 outside) = 6.
`.claude/workflows/` = 0 (1) + 0 + 2 (1/1 = 100% code) + 0 + 0 + 0 (14 symbols) + 0 (1 export) + 0 (5 outside) = 2.
`.agents/skills/` = 3 (68) + 2 (59) + 0 (0/68 code) + 0 + 0 + n/m + 2 (59 skill manifests) + 0 (7 outside) = 7.
`.agents/` = 3 (68) + 0 (1 subdir) + 0 + 0 + 0 + n/m + 2 (59) + 0 (7) = 5.
`.codex/` = 0 (2) + 0 + 0 (0/2 code) + 1 (`config.toml`) + 0 + n/m + 0 + 0 (4 outside) = 1.

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **The harness trees are local-only harness, not a canonical surface.** `.claude/` holds 246 tracked files — 222 Markdown, 12 code (8 `.sh`, 1 `.js`, 1 `.ts`, 1 `.bat`, 1 `.ps1`), 0 Python — and `.agents/` holds 68 files, 64 of them Markdown. No tracked Python file imports from them (`git grep -E "^\s*(from|import)\s+.*\.claude" -- "*.py"` → 0 hits), and the root `AGENTS.md` mentions none of `.claude`, `.agents`, `.codex`, `.mcp.json` or `skill` (0 hits each).
2. **`.claude/` (score 13) is the one location in this group that deserves its own `AGENTS.md`.** It is the only candidate in the 8-15 create band that is also a distinct domain; `.claude/skills/` (10) and `.claude/agents/` (10) would then be covered by it instead of the root. Recommended, not created — this wave writes no subtree file.
3. **`.agents/skills/` and `.claude/skills/` are two parallel skill trees with no sync guard.** 32 skill names are shared, 27 exist only under `.agents/skills/` (`ruflo` + 26 `source-command-*`), 7 only under `.claude/skills/` (`ikigai-daily|weekly|monthly|quarterly`, `loop-engineering`, `taskdog-triage`, `vault-intent-extract`). Of the 32 shared, only 7 are byte-identical; the other 25 differ by a pure vendor substitution (`Codex`/`Codex-flow` in `.agents` vs `Claude Code`/`claude-flow` in `.claude`) at identical line counts. No test or script compares the two trees.
4. **Two `.claude/skills/` entries point at a package root that is absent from the tree.** The 4 `ikigai-*` skills are one-line absolute paths to `src/ikigai/src/agents/v2/skills/<cadence>.md`, and `taskdog-triage` / `vault-intent-extract` declare `entry_point: agents.v2.skills.*.run_skill` — the same root, which has 0 tracked files. `src/mesh/taskdog_chat.py:300` and `:319` still import from it inside `try/except Exception`, so `/triage` and `/extract` print "error running triage" instead of running.
5. **The canonical MCP surface is `src/transport/mcp_server.py` (6 tools); the legacy harness config roots are absent.** `.claude/loop/mcp_bridge.py` is absent (deleted at 2ae8478d) and `.claude/loop/loop-tick.sh` now sets `VALID_GRAPH_KEYS=""`; `.claude/agents/loop/orchestrator.md` states the same. `.mcp.json` is absent from git and from disk. `.claude-flow/` has 0 tracked files and is excluded by `.gitignore:612` (`/.claude-flow/`) — any such directory on a dev box is untracked runtime state. `.codex/` is 2 files (`config.toml`, `hooks.json`); `hooks.json` invokes `.claude/helpers/hook-handler.cjs`, and `.claude/settings.json` (10 hook events) invokes `.claude/helpers/{hook-handler.cjs,auto-memory-hook.mjs,statusline.cjs}` — none of the three exists (`.claude/helpers/` holds 5 files).

## VERIFICATION

- `git ls-files .agents/skills` → 68 files / 59 skill dirs; `git ls-files .claude` → 246 files / 6 subdirs; `git ls-files .codex` → 2 files.
- `git ls-files .mcp.json` and `git ls-files .claude-flow` → empty; disk probe: `.mcp.json` ABSENT, `.claude/loop/mcp_bridge.py` ABSENT, `.claude-flow/` present but gitignored (`.gitignore:612`).
- `git log --diff-filter=D -- .claude/loop/mcp_bridge.py` → `2ae8478d`; `git ls-files src/ikigai/src/agents` → 0 files.
- `git grep -l -F ".claude/"` → 186 tracked files outside `.claude/`; same for `.agents/` → 7, `.codex/` → 4.
- Per-directory file/subdir/code-ratio counts computed from `git ls-files`; symbol and export counts read from the 12 code files in `.claude/`.
- Byte comparison of all 32 shared skill dirs: 7 identical, 25 vendor-substitution only.
- `git show HEAD:AGENTS.md` → 0 mentions of `.claude`, `.agents`, `.codex`, `.mcp.json`, `skill`.
- Every path named above was checked against the live tree at HEAD `2ae8478d`.
