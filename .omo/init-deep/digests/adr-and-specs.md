# DIGEST — code-docs/ + specs/ subtree (ADR and milestone-spec corpus)

## LOCATIONS WRITTEN

none — the ADR and spec tree is covered by the root file

Scores: no file written this wave; every candidate is scored below.

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `code-docs/` | 9 | root `AGENTS.md` L34 + L51 |
| `specs/` | 8 | root `AGENTS.md` L33 — but see fact 3: recommended for its own file |
| `code-docs/adr/` | 7 | root `AGENTS.md` L51 (`code-docs/adr/`) |
| `code-docs/diagnostic/` | 1 | root `AGENTS.md` L34 — not named individually |
| `code-docs/brd/` | 1 | root `AGENTS.md` L34 (pointer file) |
| `code-docs/prd/` | 1 | root `AGENTS.md` L34 (pointer file) |
| `code-docs/specs/` | 0 | root `AGENTS.md` L34 — C1–C5 + META-NP |
| `code-docs/proposals/` | 0 | root `AGENTS.md` L34 |
| `code-docs/observability/` | 0 | root `AGENTS.md` L34 |
| `code-docs/design/` | 0 | root `AGENTS.md` L34 |
| `code-docs/ikigai/` | 0 | root `AGENTS.md` L34 |

Scores: `code-docs/` 9 = 69 files (+3) + 9 subdirs (+2) + own index (+1) + 50 outside refs (+3). `specs/` 8 = 101 files (+3) + 100 subdirs (+2) + 53 refs (+3), no own config. `code-docs/adr/` 7 = 34 files (+3) + own `README.md` (+1) + 52 refs (+3). `code-docs/diagnostic/` 1 = own `README.md` (+1) only (17 files, 17 refs). `code-docs/{brd,prd}/` 1 each = own `README.md` (+1). `code-docs/{specs,proposals,observability,design,ikigai}/` 0 each (≤ 6 files, no own index, ≤ 7 refs). All 11 are 100% Markdown → code ratio 0; no `__init__.py` → module boundary 0; symbol density and export count n/m.

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **ADR inventory — 34 files, next free number ADR-038.** `code-docs/adr/` = 26 numbered ADRs (ADR-007…014, ADR-020…037), 5 dated decision-process docs, 3 index/pointer files (`README.md`, `OPERATIONAL.md`, `VIBE-OPS.md`). Status: 22 Accepted, 4 `Proposta` (ADR-008/009/010/011). `code-docs/adr/README.md:80` fixes **ADR-038**. Load-bearing trio: **ADR-013** "Canonical Scope Discipline (In-Scope vs Out-of-Scope)" (ACCEPTED 2026-08-31), **ADR-014** "UEID Canonical Format (4-part)" (ACCEPTED 2026-09-04; regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`), **ADR-023** "UEID Canonical Format Adjudication (4-part WINS)".
2. **ADR-037 (2026-11-01) reverses the root file's own "fully local" bullet.** ADR-037 "Virada Canônica: camada de dados primeiro" (Accepted) §4 swaps "Fully local — SQLite + filesystem only, zero cloud deps" → "Single cloud store + local cache" (D3 = Supabase, ratified 2026-11-01). `docs/README.md:37,226` already carries the strikethrough; root `AGENTS.md:91` still states it as live.
3. **`specs/` = 100 dirs with two incompatible frontmatter contracts — the one location that deserves its own AGENTS.md.** 101 tracked files / 100 dirs (95 `M*` + 4 feature dirs + `harness`) / 98 `SPEC.md`. All 99 spec dirs in the pre-purge scan scope are still tracked: **no milestone spec was purged**. `specs/M*/SPEC.md` uses YAML frontmatter (`name`, `description`, `status`, `owner`, `created`, `constitution_refs`, optional `shipped`); `code-docs/specs/2026-*-spec-*.md` uses a `>` blockquote header, **no** frontmatter. `specs/harness/` (SKILL-SPECS.md 376 L, SYSTEM-PROMPTS.md 360 L, both 2026-11-01, anchored to ADR-037) was live but absent from the scan scope. **Recommendation: write `specs/AGENTS.md`** — score 8 (bottom of the 8–15 "create if distinct domain" band; milestone-spec authoring rules are the least derivable part of the tree). Not created by this wave.
4. **The `code-docs/` subdir map no longer matches the root file, and `code-docs/README.md` is a stale index.** Root `AGENTS.md:34` says `code-docs/ # prd / brd / adr / ard`; the live tree has 9 subdirs — adr, brd, design, diagnostic, ikigai, observability, prd, proposals, specs — and **no `ard/`**. `code-docs/README.md` still points at `code-docs/ard/`, `code-docs/{adr,prd}/{OPERATIONAL,VIBE-OPS}/`, `code-docs/brd/CLUSTER_PLAN.md` and `life-ops/operational/docs/adr/` — none exist; `src/operational/` has 0 tracked files. `code-docs/00-INDEX.md` (459 L) still carries 13 `life-ops/` refs. Separately, 14 of the 17 `code-docs/diagnostic/` files carry `SUPERSEDED 2026-08-28` — a frozen audit corpus, not a live plan.
5. **The drift file named by four accepted ADRs and by the root file does not exist.** ADR-032 (bridge ⊆ server), ADR-033 (UEID single-source), ADR-034 (Phase 8.2 wiring) and ADR-035 (empty-commit guard) all place their enforcement in `src/ikigai/tests/test_drift_extended_invariants.py`; no tracked file matches `*drift_extended*`. The live drift net is `src/ikigai/tests/test_{canonical_scope,drift_invariants,drift_detector,drift_state}.py` — yet root `AGENTS.md:92` still says to "add to `test_drift_extended_invariants.py` instead".

## VERIFICATION

- `git ls-files code-docs` → 69 files; `specs` → 101 files / 100 dirs (95 `M*`, 4 feature, `harness`); `code-docs/adr` → 34 files (26 `ADR-NNN-*.md`, 5 dated, 3 index).
- Pre-purge scope JSONs `g7-c35.json` + `g7-c36.json` (99 `specs/` dirs) diffed against the live tree: 0 missing, 1 extra (`harness`).
- `git ls-files src/operational` → 0; `git ls-files | grep drift_extended` → 0; `git ls-files 'code-docs/**/AGENTS.md' 'specs/**/AGENTS.md'` → 0.
- Code ratio = extension histogram of `git ls-files` (100% `.md`); subdir counts from the same listing; outside-ref = tracked files outside the dir whose text matches the dir path (`.omo*` tooling excluded).
- Every path was checked against the live tree at HEAD `2ae8478d`; the paths named as absent in facts 4–5 exist nowhere in git.
