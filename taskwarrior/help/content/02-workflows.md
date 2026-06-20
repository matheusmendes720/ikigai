# Workflow Guides

## Overview

Your Taskwarrior system supports **4 review cadences** aligned with your temporal cycles. Each workflow has specific commands, reports, and strategic purposes.

---

## Daily Workflow (#narrativa)

**Frequency:** Every day  
**Time:** Morning (Rotina Inicial) and Evening (Rotina Final)  
**Tag:** `+narrativa`, `+execucao-diaria`  
**Report:** `narrativa`

### Morning Routine (Rotina Inicial)

**Purpose:** Review daily tasks, plan the day, check time blocks

```bash
tm              # Complete morning routine
# Equivalent to:
task narrativa  # Daily narrative report
task due:today list  # Tasks due today
task blocos     # Tasks by time blocks
```

**Manual Steps:**
```bash
# 1. View daily narrative
task narrativa

# 2. Check tasks due today
tld             # List due today
# or
task due:today list

# 3. View tasks by time blocks
tbloco          # View blocos report
# or
task blocos

# 4. Check active tasks
tactive         # Currently active tasks

# 5. Start working on a task
tstart <id>     # Mark task as active
```

### During the Day

**Purpose:** Track progress, manage active tasks

```bash
# Check active tasks
tactive         # What you're working on now

# Start/stop tasks
tstart <id>     # Start working
tstop <id>      # Stop working

# Complete tasks
td <id>         # Mark as done
```

### Evening Routine (Rotina Final)

**Purpose:** Review completed work, plan tomorrow

```bash
te              # Complete evening routine
# Equivalent to:
task completed end:today  # What you completed today
task due:tomorrow list    # What's due tomorrow
```

**Manual Steps:**
```bash
# 1. Review completed today
task completed end:today
# or
tcomp end:today

# 2. Plan tomorrow
tldt            # List due tomorrow
# or
task due:tomorrow list

# 3. Summary of the day
ts              # Quick summary
```

### Daily Review Script

Automated daily review:
```bash
taskwarrior/scripts/daily-review.sh
```

**What it does:**
- Shows narrativa report
- Lists tasks due today
- Shows blocos report
- Lists completed tasks (end:today)
- Shows summary
- Lists tasks due tomorrow

---

## Weekly Workflow (#relatórios)

**Frequency:** Once per week  
**Time:** End of week (typically Sunday evening)  
**Tag:** `+relatorios`  
**Report:** `relatorios`

### Weekly Review

**Purpose:** Analyze weekly progress, adjust strategies, plan next week

```bash
twk             # Complete weekly review
# Equivalent to:
task relatorios                    # Weekly report
task modified.after:today-7d summary  # Summary of last 7 days
```

**Manual Steps:**
```bash
# 1. View weekly report
task relatorios
# or
twk

# 2. Summary of last 7 days
task modified.after:today-7d summary

# 3. Completed this week
task completed end.after:today-7d

# 4. Export for analysis
task modified.after:today-7d export > week-tasks.json

# 5. Calculate metrics
python3 taskwarrior/scripts/calculate-metrics.py week-tasks.json --days 7
```

### Weekly Review Script

Automated weekly review:
```bash
taskwarrior/scripts/weekly-review.sh
```

**What it does:**
- Shows relatorios report
- Summary of modified tasks (last 7 days)
- Lists completed tasks (last 7 days)
- Exports to week-tasks.json

### Weekly Metrics

Calculate completion rate for the week:
```bash
# Export week data
task modified.after:today-7d export > week-tasks.json

# Calculate metrics
python3 taskwarrior/scripts/calculate-metrics.py week-tasks.json --days 7
```

**Output:**
```
Tasks: total=X completed=Y pending=Z waiting=W
Taxa de Conclusao: XX.X%
```

---

## 15-Day Workflow (#revisão)

**Frequency:** Every 15 working days  
**Time:** End of meta cycle  
**Tag:** `+revisao`  
**Report:** `revisao`  
**Requires:** `meta_ciclo` UDA

### Meta Review (Revisão Quinzenal)

**Purpose:** Review meta progress, correct route, adjust strategies

```bash
# View meta review report
task revisao
# or
tmeta

# Filter by specific meta cycle
task +revisao meta_ciclo:1 list
```

**Manual Steps:**
```bash
# 1. View all metas
task revisao
# or
tmeta

# 2. Review specific meta cycle
task meta_ciclo:1 list

# 3. Review tasks with +revisao tag
task +revisao meta_ciclo:1 list

# 4. Check completion rate for meta
task meta_ciclo:1 completed
task meta_ciclo:1 summary
```

### Creating Meta Review Tasks

```bash
# Meta review task (requires meta_ciclo)
ta +revisao meta_ciclo:1 "Review meta cycle 1 progress"

# With working-day due date (15 days from start)
twd 2026-01-06 15 "Meta review" +revisao meta_ciclo:1

# Using recurrence helper
trecur15 "Revisão quinzenal" meta_ciclo:1 +revisao
```

### Important: Validation

The `on-add` hook warns if you add `+revisao` without `meta_ciclo`:

```bash
# ❌ This will trigger a warning
ta +revisao "Review task"

# ✅ Correct: include meta_ciclo
ta +revisao meta_ciclo:1 "Review task"
```

### Meta Cycle Structure

Each meta cycle (15 working days) contains:
- **3 microcycles** (tarefas) of 5 days each
- **Weekly reviews** (#relatórios) during the meta
- **Final review** (#revisão) at the end

---

## Monthly Workflow (#supervisão) ^tr-726ftyjay

**Frequency:** Once per month  
**Time:** End of month  
**Tag:** `+supervisao`  
**Report:** `supervisao`

### Monthly Supervision

**Purpose:** Evaluate sonho progress, strategic alignment, quarterly objectives

```bash
# View monthly supervision report
task supervisao
# or
task sonho      # View all sonhos
```

**Manual Steps:**
```bash
# 1. View supervision report
task supervisao

# 2. View all sonhos
task sonho
# or
tsonho

# 3. Summary of last 30 days
task modified.after:today-30d summary

# 4. Completed this month
task completed end.after:today-30d

# 5. Check strategic alignment
task sonho_id:publicar-livro all  # All tasks for a sonho
```

### Monthly Metrics

Calculate monthly completion rate:
```bash
# Export month data
task modified.after:today-30d export > month-tasks.json

# Calculate metrics
python3 taskwarrior/scripts/calculate-metrics.py month-tasks.json --days 30
```

### Quarterly Objectives Review

During monthly #supervisão, also review quarterly objectives: ^tr-z0lbbzjwm

```bash
# View objectives for current quarter
task objetivo_trimestre:Q1 list

# View all objectives
task objetivo
# or
tobj
```

---

## Workflow Summary

| Workflow | Frequency | Tag | Report | Command |
|----------|-----------|-----|--------|---------|
| **Daily (#narrativa)** | Every day | `+narrativa`, `+execucao-diaria` | `narrativa` | `tm` (morning), `te` (evening) |
| **Weekly (#relatórios)** | Once per week | `+relatorios` | `relatorios` | `twk` |
| **15-day (#revisão)** | Every 15 working days | `+revisao` | `revisao` | `task revisao` |
| **Monthly (#supervisão)** | Once per month | `+supervisao` | `supervisao` | `task supervisao` | ^tr-iidfww1gs

---

## Workflow Integration

### Daily → Weekly → 15-day → Monthly

```
Daily (#narrativa)
  ↓
Weekly (#relatórios) - aggregates daily progress
  ↓
15-day (#revisão) - reviews 3 weeks of work
  ↓
Monthly (#supervisão) - evaluates sonho progress
```
^tr-6lnv2bhsj

### Example: Complete Workflow Cycle

**Day 1-5 (Microcycle 1):**
- Daily: `tm` (morning), `te` (evening)
- End of week: `twk` (weekly review)

**Day 6-10 (Microcycle 2):**
- Daily: `tm`, `te`
- End of week: `twk`

**Day 11-15 (Microcycle 3):**
- Daily: `tm`, `te`
- End of week: `twk`
- End of meta: `task revisao` (15-day review)

**End of Month:**
- `task supervisao` (monthly supervision)

---

## Related Topics

- `th hierarchy` - Hierarchy levels and their workflows
- `th reports` - Custom reports for each workflow
- `th contexts` - Context switching for workflows
- `th metrics` - Metrics calculation for workflows

---

*For automation scripts, see `taskwarrior/scripts/daily-review.sh` and `taskwarrior/scripts/weekly-review.sh`*
