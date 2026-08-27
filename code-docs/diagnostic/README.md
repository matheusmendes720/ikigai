# Diagnostic — Master Index

Cross-cutting diagnostic artifacts for the Algorithmic Life OS. Each document
catalogues known issues across subsystems with severity, fix suggestions, and
sequencing. Append-only — issues are added, never removed; resolution is
tracked in `docs/.sdd-progress.md` per sprint.

---

## Diagnostic Categories

| Category | Location | Owner | Status |
|----------|----------|-------|--------|
| **IKIGAI backend deep-dive** | `life-ops/ikigai/docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md` | IKIGAI team | ✅ 19 issues catalogued (2026-08-26) |
| **Master system diagnostic** | `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` | Architecture | 🟡 Draft (2026-08-27) |
| **Issue dependencies + sprint plan** | `code-docs/diagnostic/2026-08-27-issue-dependencies.md` | Architecture | 🟡 Draft (2026-08-27) |
| **Migration scripts catalog** | `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` | Architecture | 🟡 Draft (2026-08-27) |
| **Risk & effort matrix** | `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md` | Architecture | 🟡 Draft (2026-08-27) |
| **IKIGAI error code catalog** | `code-docs/diagnostic/2026-08-27-error-catalog.md` | IKIGAI team | 🟡 Draft (2026-08-27) |
| **Pending constructions detail** | `code-docs/diagnostic/2026-08-27-pending-constructions-detail.md` | Architecture | 🟡 Draft (2026-08-27) |
| **GitHub issues backlog** | `code-docs/diagnostic/2026-08-27-github-issues-backlog.md` | Issue tracker | 🟡 Draft (2026-08-27, 80 issues) |
| **Test coverage strategy** | `code-docs/diagnostic/2026-08-27-test-coverage-strategy.md` | QA | 🟡 Draft (2026-08-27) |
| **Pre-merge checklist** | `code-docs/diagnostic/2026-08-27-pre-merge-checklist.md` | Release eng | 🟡 Draft (2026-08-27) |
| **Architecture diagrams** | `code-docs/diagnostic/2026-08-27-architecture-diagrams.md` | Architecture | 🟡 Draft (2026-08-27, 6 Mermaids) |
| **Observability dashboard design** | `code-docs/observability/05-dashboard-design.md` | Observability | 🟡 Draft (2026-08-27, 10 dashboards) |
| **IKIGAI bootstrap runbook** | `code-docs/diagnostic/2026-08-27-ikigai-bootstrap-runbook.md` | IKIGAI team | 🟡 Draft (2026-08-27, C1-C5 fixes + boot sequence) |
| **Sprint 1 implementation plan** | `code-docs/diagnostic/2026-08-27-sprint1-implementation-plan.md` | Architecture | 🟡 Draft (2026-08-27, 16 TDD tasks) |
| **Incident response runbook** | `code-docs/diagnostic/2026-08-27-incident-response-runbook.md` | SRE / on-call | 🟡 Draft (2026-08-27, 13 INC-* runbooks) |
| **Sprint 1 diagrams** | `code-docs/diagnostic/2026-08-27-sprint1-diagrams.md` | Architecture | 🟡 Draft (2026-08-27, 6 Mermaid diagrams) |
| **Test integration recovery** | `code-docs/diagnostic/2026-08-28-test-integration-recovery.md` | Architecture | 🟡 Draft (2026-08-28, 27-test gate from unify branch) |
| **PAV kernel fate options** | `code-docs/diagnostic/2026-08-28-pav-kernel-fate-options.md` | Architecture | 🟡 Draft (2026-08-28, 3 options + recommendation) |
| **System design report** | (transient) Plan-mode artifact | Architecture | Source of §1-§2 of master |
| **Known gaps** | `code-docs/00-INDEX.md §12` | Index maintainer | ✅ 5 items |
| **CLAUDE.md pitfalls** | `CLAUDE.md §Pitfalls` + `life/CLAUDE.md §Pitfalls` | Repo maintainer | ✅ 9+ items |

---

## Master Diagnostic — Issue Count

| Subsystem | Critical | High | Medium | Info | Total |
|-----------|---------:|-----:|-------:|-----:|------:|
| IKIGAI backend (deep-dive) | 5 | 6 | 5 | 3 | **19** |
| System architecture (design report) | 3 | 8 | 7 | 4 | **22** |
| PAV kernel restoration | 1 | 4 | 2 | 1 | **8** |
| External MCP servers (3 servers) | 0 | 9 | 6 | 3 | **18** |
| Known gaps / pitfalls (cross-cutting) | 1 | 3 | 4 | 2 | **10** |
| **TOTAL** | **10** | **30** | **24** | **13** | **77** |

> **Note:** Some issues overlap (e.g., schema split-brain is in both IKIGAI
> deep-dive and system architecture). Cross-references resolve to the
> canonical source.

---

## Cross-References

| Topic | Canonical source |
|-------|------------------|
| Schema split-brain (plan_entities) | IKIGAI deep-dive §schema + system design §7.1 |
| dcode ↔ IKIGAI MCP disconnect | System design §7.2 |
| PAV CLI broken post-`604d6af` | `CLAUDE.md §Pitfalls` + `life/CLAUDE.md §Pitfalls` |
| 5 vs 4 IKIGAI vectors | Known gaps §12.2 + algorithm-issues-registry |
| Stray 0-byte files at repo root | `life/CLAUDE.md §Pitfalls` |
| Observability sprint status | `docs/.sdd-progress.md` + IKIGAI README §Observability |

---

## Maintenance

When adding a new diagnostic doc:

1. **Append-only** — never delete or rewrite an existing issue
2. **Severity legend** — Critical (system won't start) / High (functional but wrong) / Medium (edge-case bug) / Info (design note)
3. **Cross-reference** — every issue points to canonical source (file + line range)
4. **Fix suggestion** — every issue has a recommended resolution path
5. **Target branch** — every issue lists which branch the fix lands on
6. **Update the master table** — bump counts in this README

---

*Diagnostic category — v1.0 — 2026-08-27*
