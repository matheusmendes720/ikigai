# DIGEST — docs-aux subtree

## LOCATIONS WRITTEN

none — the auxiliary docs trees are covered by root file

Scores:
- `diagrams/` = 1: files 14≤20→0/3; subdirs 0≤5→0/2; executable code 0/14=0%→0/2 (even counting 6 Mermaid sources, 43%≤70%); own `puppeteer-config.json`→+1; module boundary 0→0/2; symbols n/m; exports 0→0/2; external files referencing it 6≤20→0/3.
- `notes/` = 0: files 4→0/3; subdirs 1→0/2; code 0/4=0%→0/2; own config 0→0/1; module boundary 0→0/2; symbols n/m; exports 0→0/2; external files referencing it 9≤20→0/3.
- `openwiki/` = 0: files 2→0/3; subdirs 0→0/2; code 0/2=0%→0/2; own config 0→0/1; module boundary 0→0/2; symbols n/m; exports 0→0/2; external files referencing it 9≤20→0/3.
- `reports/` = 3: files 18→0/3; subdirs 1→0/2; code 0/18=0%→0/2; own config 0→0/1; module boundary 0→0/2; symbols n/m; exports 0→0/2; external files referencing it 31>20→+3.
- `strategics/` = 3: parent-tracked files 9→0/3; tracked subdirs 0→0/2; code 0/9=0%→0/2; own config 0→0/1; module boundary 0→0/2; symbols n/m; exports 0→0/2; external files referencing it 111>20→+3. The separate nested checkout is excluded from parent scope.
- `notes/_templates/` = 0: files 3→0/3; subdirs 0→0/2; code 0/3=0%→0/2; own config 0→0/1; module boundary 0→0/2; symbols n/m; exports 0→0/2; external files referencing it 1≤20→0/3.
- `reports/baselines/` = 0: files 8→0/3; subdirs 0→0/2; code 0/8=0%→0/2; own config 0→0/1; module boundary 0→0/2; symbols n/m; exports 0→0/2; external files referencing it 11≤20→0/3.

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `diagrams/` | 1 | `AGENTS.md` — repository-wide canonical-scope, read-only, and documentation rules |
| `notes/` | 0 | `AGENTS.md` — repository-wide canonical-scope and append-only rules |
| `openwiki/` | 0 | `AGENTS.md` — repository-wide canonical-scope and documentation rules |
| `reports/` | 3 | `AGENTS.md` — repository-wide canonical-scope and documentation rules |
| `strategics/` | 3 | `AGENTS.md` — repository-wide canonical-scope and protected-content rules |
| `notes/_templates/` | 0 | `AGENTS.md` — parent `notes/` documentation and append-only rules |
| `reports/baselines/` | 0 | `AGENTS.md` — parent `reports/` documentation rules |

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **Auxiliary roots contain no executable implementation.** `git ls-files` counts 47 parent-tracked files across `diagrams/` (14), `notes/` (4), `openwiki/` (2), `reports/` (18), and `strategics/` (9): Markdown/templates, Mermaid, JSON data, PNG renders, checksums, and one signature, but no executable source modules.
2. **`reports/` and `openwiki/` remain tracked.** `reports/` has 18 tracked files (6 Markdown, 10 JSON, checksum and signature); `openwiki/` has 2 (`INSTRUCTIONS.md` and `.last-update.json`). Their JSON is data/metadata, not an import surface.
3. **Diagram sources and PNG renders travel in pairs.** `diagrams/` contains 6 editable `.mmd` files and 6 checked-in `.png` peers, plus `README.md` and `puppeteer-config.json`; the PNGs are generated artifacts.
4. **Notes and wiki instructions define writer boundaries.** `notes/_templates/README.md` requires append-only session logs and separates agent-written backlog from human-written reflection; `openwiki/INSTRUCTIONS.md` says the agent reads but never rewrites it and requires source anchors for material claims.
5. **The planning engine is a nested third-party checkout.** `git ls-files strategics/planning-with-files` returns 0; that subtree has its own `.git`, tracks 402 files internally, is clean internally, is ignored by `.gitignore:480`, and the parent has no `.gitmodules`. Do not ingest or commit its contents.

## VERIFICATION

- `git -c core.quotePath=false ls-files -- diagrams notes openwiki reports strategics` → 14/4/2/18/9 files (47 total); no tracked `AGENTS.md` below these roots.
- Recursive live listings of all five roots confirmed the tracked counts and their two tracked subdirectories (`notes/_templates/`, `reports/baselines/`); the planning checkout is a live nested Git repository but contributes no parent-tracked files.
- `git ls-files -- strategics/planning-with-files` → empty; `git -C strategics/planning-with-files ls-files | wc -l` → 402; `git -C strategics/planning-with-files status --porcelain` → empty; `.gitmodules` is absent; `.gitignore:480` excludes the subtree.
- `git grep -l -I -F -- "<dir>/" -- . ":(exclude)<dir>/**" | wc -l` → distinct external files referencing each location: diagrams 6, notes 9, openwiki 9, reports 31, strategics 111, notes/_templates 1, reports/baselines 11.
- Every path named above was checked against the live tree.
