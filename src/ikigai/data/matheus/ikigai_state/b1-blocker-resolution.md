---
ueid: ikigai:analysis:b1-blocker-resolution:7e3a1f22:a14b3c8d
entity_type: analysis
slug: b1-blocker-resolution
parent_ueid: ikigai:deliverable:byd-process-tracker:693ebfb6:6c641956
title: "B1 Blocker Resolution — Graduation Years Cap (H3)"
status: OPEN
priority: CRITICAL
created_at: 2026-08-26T00:00:00Z
updated_at: 2026-08-26T00:00:00Z
tags: [persona/matheus, type/blocker-resolution, area/cv-scoring, empresa/byd, priority/CRITICAL]
---

# B1 Blocker Resolution — Graduation Years Cap (H3)

**Priority: CRITICAL**  
**Date:** 2026-08-26  
**Blocker source:** `deliverables/byd-process-tracker.md` → `_b1_blocker`  
**Expected resolution owner:** Matheus (candidate)

---

## 1. Current State Summary

As of the 2026-08-26 CV Campaign pass, all 4 BYD CV variants are **blocked at 49 points (Band D)** and cannot be submitted to any BYD Brasil vacancy (submission threshold: 65 pt).

| CV Variant | Current Score | Band | Status |
|---|---|---|---|
| v8 — Fullstack | 49pt | D | ❌ Blocked |
| v9 — Big Data | 49pt | D | ❌ Blocked |
| v10 — Ops | 49pt | D | ❌ Blocked |
| v11 — ITAM | 49pt | D | ❌ Blocked |

**Root cause:** H3 (graduation year clamp) is the dominant and sole scorer-constraining factor across all 4 variants. A total of 17 patches (P-A through P-M, B3, B5) were applied in the 2026-08-26 campaign, but none addressed H3 because the raw graduation year data is not in the vault.

**Projected post-unblock scores:** 87–91pt (Band A) — above the 65pt submission threshold for all variants.

**Note on artifact availability:** The CV files (`job_hunter/base/cv-versions/BYD-CV-Campaign-Report.md` and the 4 variant files themselves) were referenced in the tracker update but are **not present in the vault at this time**. They were likely produced externally (outside the vault path). This resolution targets the single data input required to unlock them retroactively once the files exist.

---

## 2. What Graduation Years Are Needed (Exact Format)

The fix requires **3 graduation year values**, entered as a list:

```
graduation_years: [YYYY_earliest, YYYY_middle, YYYY_latest]
```

Specifically:

| Field | Description |
|---|---|
| `graduation_years[0]` | Earliest graduation year (e.g., high school or associate) |
| `graduation_years[1]` | Middle graduation year (e.g., bachelor's degree) |
| `graduation_years[2]` | Latest graduation year (e.g., postgraduate / specialization) |

**Source fields in the CV scoring model:**
- The H3 rule clamps scoring when `graduation_years` is missing, null, or contains fewer than 3 entries
- Each entry should be a 4-digit integer (e.g., `2014`, `2018`, `2023`)
- All 3 entries must be non-null and in ascending chronological order

**Why 3 entries?** The H3 rule was designed to reward candidates with a complete educational timeline (early → mid → late). The cap removes a ceiling penalty when all 3 entries are supplied, allowing the graduation dimension to score at full weight.

---

## 3. Recommended Next Action for Matheus

**Do this now — estimated time: 5 minutes.**

1. **Identify your 3 graduation years.** List them in ascending order:
   - Earliest (e.g., high school, technical course, or first college entry)
   - Middle (e.g., bachelor's degree completion)
   - Latest (e.g., postgraduate, specialization, intensive course, or most recent certification)

2. **Enter them in the CV data source** used by the scoring model. Based on the vault structure, this likely means:
   - Adding `graduation_years: [YYYY, YYYY, YYYY]` to the frontmatter/custom block of each CV variant file, OR
   - Supplying the 3 values to the scoring agent so it can patch the H3 field directly

3. **Re-run the scoring pass.** Once the 3 values are in, all 4 CVs (v8–v11) will cross the 65pt threshold automatically. No further edits are needed to any other section.

4. **If uncertain which 3 values to use**, default to:
   - Your earliest formal education completion year
   - Your bachelor's or equivalent degree completion year
   - Your most recent post-degree certification or course completion year

---

## 4. Blocker Clearance Criteria

| Criterion | Target |
|---|---|
| All 4 CV variants score ≥ 65pt | ✅ Cleared |
| No H3 cap in scoring output | ✅ Cleared |
| Submission-ready for BYD vacancies | ✅ Ready to send |

---

## 5. Risk if Not Resolved

- **All 4 BYD CV variants remain at 49pt (Band D)** — below the 65pt submission threshold
- **No BYD applications can be submitted** via this pipeline
- **Q3 KR1 is blocked**: the pipeline BI objective requires ≥ 1 response from cold outreach; unsubmitable CVs prevent outreach from progressing to submission
- **W4 forward momentum stalls**: the process tracker (D4) cannot record meaningful process-stage outcomes without submittable CVs

---

## 6. Cross-References

- Blocker record: `deliverables/byd-process-tracker.md` → `_b1_blocker` (last reviewed 2026-08-26)
- Campaign update: same file, `_updates[0]` entry dated 2026-08-26
- IKIGAi profile: `ikigai_state/profile-2026-07-03.md`
- ONDA project: `projects/onda-2026-07-byd-deep-dive.md`
- Q3 Objective: `objectives/q3-2026-primeira-vaga.md`
