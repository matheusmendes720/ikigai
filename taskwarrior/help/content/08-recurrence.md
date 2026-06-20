# Recurrence Patterns

## Overview

Recurrence allows you to create tasks that automatically regenerate. Your system supports both calendar-based and working-day recurrence patterns aligned with your temporal cycles.

---

## Calendar-Based Recurrence

### Daily Recurrence

```bash
# Daily task
task add recur:daily due:today+1d "Daily task"

# Using helper
trecurd "Daily task"
```

**Helper Function:**
```bash
trecurd "<description>" [modifications]
```

**Example:**
```bash
trecurd "Morning meditation" bloco_tempo:Manhã +execucao-diaria
```

---

### Weekly Recurrence

```bash
# Weekly task
task add recur:weekly due:eow "Weekly task"

# Using helper
trecurw "Weekly task"
```

**Helper Function:**
```bash
trecurw "<description>" [modifications]
```

**Example:**
```bash
trecurw "Weekly review" +relatorios
```

---

### Monthly Recurrence

```bash
# Monthly task
task add recur:monthly due:eom "Monthly task"

# Using helper
trecurm "Monthly task"
```

**Helper Function:**
```bash
trecurm "<description>" [modifications]
```

**Example:**
```bash
trecurm "Monthly supervision" +supervisao
```

---

### Custom Intervals

```bash
# Every 2 weeks
task add recur:2w due:today+14d "Bi-weekly task"

# Every month
task add recur:1mo due:eom "Monthly task"

# 15-day recurrence (for meta cycles)
task add recur:2w due:today+15d "15-day task"
trecur15 "15-day task"
```

**15-Day Helper:**
```bash
trecur15 "<description>" [modifications]
```

**Example:**
```bash
trecur15 "Meta review" +revisao meta_ciclo:1
```

---

## Working-Day Recurrence

### Working-Day Calculation

Your system uses **working days** (dias úteis) instead of calendar days for precise planning aligned with your temporal cycles.

### Working-Day Helper

**Function:** `twd`

```bash
twd <start YYYY-MM-DD> <working-days> "<description>" [modifications]
```

**Parameters:**
- `start`: Start date (YYYY-MM-DD format)
- `working-days`: Number of working days to add
- `description`: Task description
- `modifications`: Additional task attributes

**Examples:**
```bash
# 5 working days from today
twd 2026-01-06 5 "Tarefa 5d úteis" tarefa_microciclo:1 +execucao-diaria

# 15 working days from today (meta cycle)
twd 2026-01-06 15 "Meta 15d úteis" +revisao meta_ciclo:1

# 45 working days from today (ciclo)
twd 2026-01-06 45 "Ciclo 45d úteis" ciclo:1
```

### Working-Day Calculator

**Script:** `taskwarrior/scripts/working-days.py`

```bash
# Calculate working days
python3 taskwarrior/scripts/working-days.py 2026-01-06 15
# Output: 2026-01-27 (15 working days from start)
```

**Usage:**
```bash
python3 taskwarrior/scripts/working-days.py <YYYY-MM-DD> <days>
```

---

## Temporal Cycle Recurrence

### 5-Day Microcycle (Tarefas)

```bash
# 5 working days
twd 2026-01-06 5 "Tarefa microciclo" tarefa_microciclo:1 +execucao-diaria
```

**Use Cases:**
- Weekly task planning
- Microcycle management
- 5-day task cycles

---

### 15-Day Meta Cycle

```bash
# 15 working days
twd 2026-01-06 15 "Meta review" +revisao meta_ciclo:1

# Or using helper
trecur15 "Meta review" meta_ciclo:1 +revisao
```

**Use Cases:**
- Meta cycle reviews
- 15-day planning
- Wave management

---

### 45-Day Cycle

```bash
# 45 working days
twd 2026-01-06 45 "Ciclo review" ciclo:1
```

**Use Cases:**
- Cycle reviews
- Quarterly planning
- Strategic cycles

---

### 180-Day Teste de Fogo

```bash
# 180 working days
twd 2026-01-06 180 "Teste de Fogo" +teste_fogo
```

**Use Cases:**
- Fire test evaluation
- Strategic coherence check
- 180-day assessment

---

## Recurrence with Modifications

### Recurrence + Hierarchy

```bash
# Daily with hierarchy
trecurd "Daily task" sonho_id:publicar-livro +execucao-diaria

# Weekly with meta cycle
trecurw "Weekly review" meta_ciclo:1 +relatorios

# 15-day with meta cycle
trecur15 "Meta review" meta_ciclo:1 +revisao
```

### Recurrence + Time Blocks

```bash
# Daily morning task
trecurd "Morning meditation" bloco_tempo:Manhã +execucao-diaria

# Daily afternoon task
trecurd "Afternoon work" bloco_tempo:Tarde +execucao-diaria
```

### Recurrence + Priority

```bash
# High priority daily
trecurd "Important daily task" priority:H

# Medium priority weekly
trecurw "Weekly review" priority:M
```

---

## Recurrence Patterns Summary

| Pattern | Helper | Interval | Use Case |
|---------|--------|----------|----------|
| Daily | `trecurd` | 1 day | Daily routines |
| Weekly | `trecurw` | 7 days | Weekly reviews |
| 15-day | `trecur15` | 15 days | Meta cycles |
| Monthly | `trecurm` | 1 month | Monthly supervision |
| 5 working days | `twd ... 5` | 5 days | Microcycles |
| 15 working days | `twd ... 15` | 15 days | Meta cycles |
| 45 working days | `twd ... 45` | 45 days | Cycles |
| 180 working days | `twd ... 180` | 180 days | Teste de Fogo |

---

## Recurrence Helpers Reference

### Calendar-Based Helpers

```bash
trecurd "<desc>" [mods]    # Daily
trecurw "<desc>" [mods]    # Weekly
trecur15 "<desc>" [mods]   # 15-day
trecurm "<desc>" [mods]    # Monthly
```

### Working-Day Helper

```bash
twd <start> <days> "<desc>" [mods]
```

**Examples:**
```bash
# 5 days
twd 2026-01-06 5 "Tarefa" tarefa_microciclo:1

# 15 days
twd 2026-01-06 15 "Meta" meta_ciclo:1 +revisao

# 45 days
twd 2026-01-06 45 "Ciclo" ciclo:1
```

---

## Best Practices

### Recurrence + Workflows

1. **Daily tasks:** Use `trecurd` for daily routines
2. **Weekly tasks:** Use `trecurw` for weekly reviews
3. **Meta cycles:** Use `trecur15` or `twd ... 15` for 15-day cycles
4. **Monthly tasks:** Use `trecurm` for monthly supervision

### Working-Day Planning

- Use `twd` for precise working-day calculations
- Align with temporal cycles (5, 15, 45, 180 days)
- Consider weekends and holidays

### Recurrence + Hierarchy

- Link recurrence to hierarchy levels
- Use appropriate UDAs (meta_ciclo, tarefa_microciclo)
- Tag with review types (+revisao, +relatorios, etc.)

---

## Related Topics

- `th workflows` - Workflow-specific recurrence
- `th hierarchy` - Hierarchy-level recurrence
- `th udas` - UDAs for recurrence

---

*For working-day calculations, see `taskwarrior/scripts/working-days.py`*
