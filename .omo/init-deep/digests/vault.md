# DIGEST — vault/ subtree

## LOCATIONS WRITTEN

none — vault/ is covered by the root file

Scores: code = executable source only (`.py/.js/.ts/.sh/.bat/.ps1`); MD/YAML/JSON/TXT are data. No subtree under `vault/` has an own config or a package root (`__init__.py`) — 0 hits. Refs = tracked files outside `vault/` whose text contains the path (init-deep tooling files excluded).
`vault/` = 175 tracked files (>20) 3 + 34 dirs (>5) 2 + 223 refs (>20) 3 = 8.
`vault/ikigai/` = 48 files 3 + 25 dirs 2 + 76 refs 3 = 8.
`vault/evidence/` = 96 files 3 + 9 code symbols (<30) + 8 exports (<10) + 2 refs (<20) = 3.
`vault/drafts/` = 12 files (<20) + 0 dirs + 2/12 code (16.7%) + 0 symbols + 9 refs (<20) = 0.
`vault/plans/` = 7 files + 0 dirs + 0% code + 2 refs = 0.
`vault/run-continuation/` = 7 files + 0 dirs + 0% code (6 JSON) + 6 refs = 0.
`vault/00-norte/` = 1 file + 0 dirs + 8 refs = 0.
`vault/projetos/` = 1 file + 0 dirs + 5 refs = 0.
`vault/paperclipai_issues/` = 1 file + 0 dirs + 0 refs = 0.
`vault/_strategics_excerpt.md` = 1 file + 0 refs = 0.
`vault/test-vault-task.md` = 1 file + 0 refs = 0.
Symbol density / export count are n/m for the markdown-only trees (no code symbols to count).

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `vault/` | 8 | root `AGENTS.md` — STRUCTURE row, ANTI-PATTERNS (ADR-012 `vault_write` = sole writer), UNIQUE STYLES (Planning Note channel) |
| `vault/ikigai/` | 8 | root `AGENTS.md` — planning-note channel + `closing-2026` tree; deserves its own file (fact 2) |
| `vault/evidence/` | 3 | root `AGENTS.md` — 96 committed review artifacts, no config, no package, no importers |
| `vault/drafts/` | 0 | root `AGENTS.md` — working drafts; generator + consumers live in `tools/backtest/` (own `AGENTS.md`) |
| `vault/plans/` | 0 | root `AGENTS.md` — 7 plan notes, 0 code |
| `vault/run-continuation/` | 0 | root `AGENTS.md` — 7 run artifacts (6 JSON) |
| `vault/00-norte/` | 0 | root `AGENTS.md` — 1 folha-norte SOT note |
| `vault/projetos/` | 0 | root `AGENTS.md` — 1 projeto note |
| `vault/paperclipai_issues/` | 0 | root `AGENTS.md` — 1 sync-log note |
| `vault/_strategics_excerpt.md` | 0 | root `AGENTS.md` — 1 excerpt note |
| `vault/test-vault-task.md` | 0 | root `AGENTS.md` — 1 scratch note |

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **`vault/` is append-only in practice and owns no `AGENTS.md`.** 175 tracked files / 920,726 B tracked (195 files / 1,423,814 B on disk) across 34 dirs and 8 top-level trees. No `AGENTS.md` exists anywhere under `vault/`; the only `agents.md` is `vault/ikigai/meta/agents.md` (13,675 B), a vault *note* addressed to future agents — not an agent-instruction file. Root `AGENTS.md` + ADR-012 stay the covering authority.
2. **`vault/ikigai/` is the one subtree that clears the create band (score 8) — recommend `vault/ikigai/AGENTS.md`.** 48 tracked files, 25 dirs (7 top-level: `closing-2026`, `cycles`, `decisions`, `meta`, `mock-datasets`, `runtime`, `templates`), referenced by 76 tracked files outside `vault/`. Distinct domain (planning-note channel, the ADR-037 pivot decision, the governance registry) that needs its own conventions file. Not created by this digest.
3. **The Planning Note channel is confirmed live.** `vault/ikigai/templates/sonho-log.md` carries frontmatter `type: planning_note`, `note_version: 1.0`, `cluster: ikigai/plan`, `triggered_by: manual`, one `## Mudança` section, and names its own destination (quoted verbatim from the template, `<quarter>` is a placeholder) `vault/ikigai/closing-2026/<quarter>/04-relatórios-diários/YYYY-MM-DD.md`. The live quarter dirs under `vault/ikigai/closing-2026/` are `01-q3-2026` and `02-q4-2026` (each `00-sonho` … `04-relatórios-diários`), plus `99-archive/`.
4. **Tracked ≠ on disk: 20 runtime artifacts under `vault/` are untracked.** `vault/evidence/pae-coverage-html/` (16 files, own `.gitignore` = `*`), `vault/ikigai/decisions/2026-10-17.jsonl`, `vault/ikigai/decisions/2026-11-01.jsonl`, `vault/.vault_audit.log`, `vault/.vault_events.jsonl`. Any vault number in the root file must come from `git ls-files vault/` (175), not from a directory listing.
5. **`vault/` is written from outside the vault writer, and its committed code is throwaway.** `tools/backtest/AGENTS.md` documents `seed_q3_scenarios.py --out vault/drafts/q3-scenarios.yaml`, `taskdog_exhaustiveness.py` and `role_anchors.py` writing the other two scenario fixtures *inside* `vault/drafts/` — a real exception to the ADR-012 one-writer rule. The only other committed code under `vault/` is 6 one-shot scripts with 0 importers (`vault/drafts/add_engine_ref.py`, `check_state.py`; `vault/evidence/scan_pae.py`, `period-3-verify.py`, `verify_t3.py`, `w.py`); `vault/evidence/w.py` (33 B) is a committed `SyntaxError`.

## VERIFICATION

- `git ls-files -z vault/` → 175 tracked files; `git ls-files -z` (all) → 1,750 tracked files; HEAD `2ae8478d`, branch `fix/ci-gates-green`.
- Byte totals via `Bun.file(path).arrayBuffer()` per tracked path → 920,726 B tracked; on-disk walk → 1,423,814 B / 195 files.
- `Bun.Glob("**/*")` over `vault/` → 195 files; 20 absent from `git ls-files` (listed in fact 4).
- `Bun.Glob("**/AGENTS.md")` over `vault/` → 0 hits; `agents.md` (any case) → only `vault/ikigai/meta/agents.md`.
- Config/package scan of `git ls-files vault/` for `pyproject.toml`, `package.json`, `setup.py`, `pytest.ini`, `ruff.toml`, `mypy.ini`, `__init__.py` → 0 hits (only `vault/ikigai/runtime/chat/.gitkeep`).
- `ast.parse` of the 6 `.py` files under `vault/` → `drafts`: 0 functions / 0 classes (module names only); `evidence`: 5 functions + 4 module-level names; `vault/evidence/w.py` → `SyntaxError: unterminated triple-quoted string literal`.
- `git grep` for `add_engine_ref`, `check_state`, `scan_pae`, `verify_t3`, `period-3-verify`, `period_3_verify` over tracked files → 0 importers each.
- Ref counts by direct content scan of all 1,750 tracked files (git grep skips dot-dirs, so it under-counts `.claude/loop/`), excluding `.omo-initdeep-chunks.json` and `.omo/init-deep/definition.json`.
- `vibe-ops/src/middleware/period_sync.py` exists (the `middleware.period_sync` import in the two evidence scripts still resolves); `vibe-ops/src/agents/pae_maintainer/` is absent.
- Every path named above was checked against the live tree at HEAD `2ae8478d`.
