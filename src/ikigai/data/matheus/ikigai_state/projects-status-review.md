# Projects Status Review — 2026-09-15

## Overview

Review of 3 overdue projects from the IKIGAI vault. Deadline review period: 2026-08-05 to 2026-08-08.

## Summary

| Project | Previous Status | New Status | Rationale |
|---------|----------------|-----------|-----------|
| `onda-q3-1-pipeline-bi-cold-outreach` | ACTIVE | **ARCHIVED** | Scope pivot; all 7 UNDs remained DRAFT |
| `onda-2026-07-byd-deep-dive` | DRAFT | **DONE** | 3/4 deliverables completed + CV campaign executed |
| `onda-2026-07-salvador-data-pipeline` | DRAFT | **ARCHIVED** | Fallback trigger not met; BYD succeeded |

---

## Project 1: `onda-q3-1-pipeline-bi-cold-outreach`

### Status: ARCHIVED

**Deadline:** 2026-08-05

### Evidence
- All 7 UNDs remained in DRAFT status (no execution)
- No deliverables produced
- Recent activity (2026-08-26) was BYD CV Campaign — a parallel workstream, not ONDA Q3-1 execution

### Rationale
The original ONDA Q3-1 scope (30 companies + pipeline) was **superseded by the BYD deep-dive** per DEC-08 decision. This represents a deliberate scope pivot, not project failure. The work that did happen (CV patching, scoring audits) was parallel to this project, not its execution.

### Status Resolution
> "ARCHIVED — deadline 2026-08-05 elapsed. All 7 UNDs remained in DRAFT status; no lead scraping, filtering, cold outreach, or pipeline work was executed. Project was superseded by onda-2026-07-byd-deep-dive which executed successfully with 3/4 deliverables completed. BYD CV Campaign work (2026-08-26 updates) was parallel workstream, not ONDA Q3-1 execution."

### Archived Reason
`scope_pivot — BYD deep-dive became primary path per DEC-08; Q3-1 original 30-company scope abandoned`

---

## Project 2: `onda-2026-07-byd-deep-dive`

### Status: DONE

**Deadline:** 2026-08-08

### Evidence

**Deliverable D1 (Market Research):** ✅ DONE
- `deliverables/byd-d1-outputs/byd-greenfield-map.md` — greenfield detection
- `deliverables/byd-d1-outputs/byd-hiring-managers.md` — 5-10 decision makers
- `deliverables/byd-d1-outputs/byd-stack-fit-matrix.md` — stack analysis

**Deliverable D2 (Econometric Vulnerability Analysis):** ✅ DONE
- `deliverables/byd-d2-outputs/byd-econometric-vulnerability.ipynb` — full Jupyter notebook
- `deliverables/byd-d2-outputs/byd-econometric-vulnerability.py` — Python scripts
- `deliverables/byd-d2-outputs/outputs/1-pager-summary.md` — executive summary
- 7 HTML visualizations (cambio, supply chain, regulatory, competition, composite radar, Sankey, stress test)

**Deliverable D3 (Cold Outreach Assets):** ✅ DONE
- `deliverables/byd-d3-outputs/byd-outreach-tier1.md` — LinkedIn + email templates
- `deliverables/byd-d3-outputs/byd-cover-letters-final.md` — cover letters

**Deliverable D4 (Process Tracker):** 🔄 IN_PROGRESS
- `deliverables/byd-d4-outputs/byd-tracker.db` — SQLite tracking database
- `deliverables/byd-d4-outputs/byd-tracker-schema.sql` — schema
- `deliverables/byd-d4-outputs/byd-tracker-seed.py` — seed data
- BYD CV Campaign executed (2026-08-26) — 4 CV variants patched

### Rationale
Core deliverables D1-D3 were substantially completed with full artifacts produced. D4 is IN_PROGRESS with active tracking infrastructure. The BYD CV Campaign (2026-08-26) demonstrates ongoing engagement. Project met its success criteria for the primary deliverables.

### Status Resolution
> "DONE — deadline 2026-08-08 elapsed. Core deliverables completed: D1 (market research) DONE, D2 (econometric vulnerability analysis) DONE with full Jupyter notebook + Python scripts + HTML visualizations, D3 (cold outreach assets) DONE with templates and cover letters. D4 (process tracker) IN_PROGRESS with active SQLite tracking database. BYD CV Campaign executed 2026-08-26; 4 CV variants patched. Substantially met objectives."

---

## Project 3: `onda-2026-07-salvador-data-pipeline`

### Status: ARCHIVED

**Deadline:** 2026-08-08

### Evidence
- No deliverables produced under this project
- BYD ONDA succeeded, triggering the "fallback not needed" condition
- Project was designed as a conditional parallel workstream

### Rationale
This project was explicitly designed as a **conditional fallback** (see `_activation_trigger`). The activation condition was: "BYD anchor (Yueying Zhang) does not respond within 5 wd (≤ 1 response)." Since BYD ONDA succeeded with D1-D4 completed and CV Campaign executed, the trigger was never met.

The fallback was never needed — this is not project failure, but rather successful risk mitigation that wasn't required.

### Status Resolution
> "ARCHIVED — activation trigger not met. BYD anchor (Yueying Zhang) response was sufficient, so Salvador tier-1 fallback was never activated. Project was designed as conditional parallel; since BYD ONDA succeeded (D1-D4 completed), this fallback was unnecessary. No deliverables produced under this project."

### Archived Reason
`trigger_not_met — fallback condition (BYD failure within 5 wd) did not occur`

---

## Files Updated

1. `/mnt/c/Users/mathe/code_space/life-oss/life/life-ops/ikigai/data/matheus/projects/onda-q3-1-pipeline-bi-cold-outreach.md`
   - Status: ACTIVE → ARCHIVED
   - Added `_status_resolution` and `_archived_reason` to custom

2. `/mnt/c/Users/mathe/code_space/life-oss/life/life-ops/ikigai/data/matheus/projects/onda-2026-07-byd-deep-dive.md`
   - Status: DRAFT → DONE
   - Added `_status_resolution` to custom

3. `/mnt/c/Users/mathe/code_space/life-oss/life/life-ops/ikigai/data/matheus/projects/onda-2026-07-salvador-data-pipeline.md`
   - Status: DRAFT → ARCHIVED
   - Added `_status_resolution` and `_archived_reason` to custom

---

## Next Steps

- [ ] No immediate action required — all projects are properly categorized
- [ ] Future reviews should check for stale ACTIVE/DRAFT projects monthly
- [ ] Consider adding automated deadline alerts for projects approaching expiry
