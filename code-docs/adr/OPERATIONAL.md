> **[PATH-ONLY REWRITE 2026-08-28 — see CLAUDE.md reconciliation]**
> Pre-2026-08-26 paths updated from \`life-ops/operational/\` → \`src/operational/\`.
> PAV is desativado per master-branch-carro-chefe-2026-08-28; ADRs are
> retained as audit reference for the pre-pivot era per
> legacy-pav-ui-era-2026-08-28.

# operational/ ADRs — PAV Productivity Kernel

Architecture Decision Records for the PAV kernel (`src/operational/`).

## Live Specs

The canonical source is at `src/operational/docs/adr/`. These files are the ground truth:

| File | Subject |
|------|---------|
| `src/operational/docs/adr/PRD-CONSTANTS-EXCEPTIONS.md` | PAVConstants + 10 error codes |
| `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` | Habit engine H(t), E(t), Q_HE |
| `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` | PolicyEngine 4-state FSM |
| `src/operational/docs/adr/PRD-CORE-POMODORO-SCENARIO.md` | 8-state pomodoro SM + scenario classifier |
| `src/operational/docs/adr/PRD-CORE-SLEEP-VALIDATION.md` | Sleep calculator + validation |
| `src/operational/docs/adr/PRD-CORE-TIME-BLOCKS-AND-REFLECTION.md` | Time blocks + journal reflection |
| `src/operational/docs/adr/PRD-ENTITIES-JOURNAL-HABIT.md` | JournalEntry, Habit entities |
| `src/operational/docs/adr/PRD-ENTITIES-METRIC-CONSOLIDATION.md` | Metric entities + rollup |
| `src/operational/docs/adr/PRD-ENTITIES-POLICY.md` | PolicySetpoints, PolicyDecision |
| `src/operational/docs/adr/PRD-ENTITIES-ROUTINE-TIMEBLOCK-POMODORO.md` | Routine, TimeBlock, Pomodoro entities |
| `src/operational/docs/adr/PRD-ENUMS-TYPES.md` | Enums and type definitions |
| `src/operational/docs/adr/ARCHITECTURAL_REFRAMING_2026-06-07.md` | Post-Sprint 10 reframe |

## Sprint Reports

| File | Subject |
|------|---------|
| `src/operational/docs/adr/SPRINT-1-REPORT.md` | Sprint 1 verification |
| `src/operational/docs/adr/SPRINT-2-REPORT.md` | Sprint 2 verification |
| `src/operational/docs/adr/SPRINT-3-REPORT.md` | Sprint 3 verification |
