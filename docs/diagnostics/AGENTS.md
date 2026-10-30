# docs/diagnostics

## OVERVIEW
Dated forensic audits and migration evidence; score 8 because this directory is a distinct, substantial diagnostic domain.

## STRUCTURE
```
diagnostics/
├── 2026-08-27-backend-audit/       # layer map and backend breakage inventory
├── 2026-08-28-doc-migration/       # documentation migration findings
├── 2026-08-28-phase1-audit/        # verified gaps and priorities
├── 2026-08-28-phase2-interface-re/ # per-fork interface readiness
├── 2026-08-28-structure-audit/     # repository structure review
└── 2026-08-30-backend-topology-diagnosis/ # topology diagnosis
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Understand the earliest backend snapshot | `2026-08-27-backend-audit/00-INDEX.md` | Starts with the layer map, breakage inventory, and verification matrix |
| Trace the post-pivot repository assessment | `2026-08-28-structure-audit/00-INDEX.md` | Structural findings around the 2026-08-28 migration |
| Review documentation cleanup | `2026-08-28-doc-migration/00-INDEX.md` | Canonical/superseded document migration map |
| Review initial remediation priorities | `2026-08-28-phase1-audit/00-INDEX.md` | Verified findings, gaps, and sequencing |
| Review fork readiness | `2026-08-28-phase2-interface-re/00-INDEX.md` | Per-interface synthesis plus detailed fork reports |
| Inspect the later topology diagnosis | `2026-08-30-backend-topology-diagnosis/README.md` | Focused backend topology findings |
| Inspect loose Phase 3 evidence | `2026-08-28-phase3-*.md` | Decisions, usage evidence, and verification notes |

## CONVENTIONS
- Treat every audit as evidence captured on its stated date, not as a description of the current checkout.
- Begin with the nearest `00-INDEX.md` or `README.md`; detailed reports use stable finding IDs and cross-file links.
- Preserve the distinction between verified code, reported claims, false retrospective claims, and recommendations.
- Dates and folder names are part of the evidence boundary; do not merge snapshots into an undated “current” report.
- The corpus uses both Portuguese and English and records code paths and line-level evidence at audit time.
- New audit work should identify its scope, evidence date, and whether findings remain open.

## ANTI-PATTERNS
- NEVER present an audit conclusion as current implementation truth without checking the referenced code and current contracts.
- DO NOT copy old counts, active-development claims, or path inventories into current guidance; several audits predate the PAV archival and namespace refactors.
- NEVER silently revise an old finding to match today's code; add a dated follow-up or update source instead.
- DO NOT execute remediation steps from an audit without validating destructive impact and current architecture rules.
- DO NOT move a pending algorithm recommendation into implementation; adjudication belongs in the decision process.
- Keep archived PAV findings as history; do not infer that the PAV kernel is active again.
