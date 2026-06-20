# Flags & Modifiers

## Overview

This guide covers Taskwarrior flags, modifiers, and attribute operations for tasks.

---

## Priority Flags

### Priority Levels

```bash
# High priority
priority:H
ta priority:H "Urgent task"
task 5 modify priority:H

# Medium priority
priority:M
ta priority:M "Important task"

# Low priority
priority:L
ta priority:L "Nice to have"

# No priority (remove)
priority:
task 5 modify priority:
```

### Priority Aliases

```bash
# High priority list
tlh            # Alias for task priority:H list
task +HIGH list
```

---

## Date Flags

### Due Date

```bash
# Set due date
due:2026-12-15
ta due:2026-12-15 "Task"

# Relative dates
due:today
due:tomorrow
due:yesterday
due:eow        # End of week
due:eom        # End of month
due:eoy        # End of year

# Date arithmetic
due:today+7d
due:today-7d
due:today+1w
due:today+1mo
```

### Wait Date

```bash
# Hide task until date
wait:2026-01-15
ta wait:2026-01-15 "Future task"

# Relative wait
wait:today+7d
ta wait:today+7d "Task in 7 days"
```

### Scheduled Date

```bash
# Schedule task
scheduled:2026-01-15
ta scheduled:2026-01-15 "Scheduled task"

# Relative schedule
scheduled:today+3d
```

### Until Date

```bash
# Expiration date
until:2026-12-31
ta until:2026-12-31 "Time-limited task"
```

---

## Tag Flags

### Add Tags

```bash
# Single tag
+execucao-diaria
ta +execucao-diaria "Daily task"

# Multiple tags
+execucao-diaria +obrigacoes
ta +execucao-diaria +obrigacoes "Task"

# Review tags
+narrativa
+relatorios
+revisao
+supervisao
```

### Remove Tags

```bash
# Remove tag
-execucao-diaria
task 5 modify -execucao-diaria

# Remove multiple tags
-execucao-diaria -obrigacoes
task 5 modify -execucao-diaria -obrigacoes
```

---

## Project Flags

### Set Project

```bash
# Project format
project:sonho:publicar-livro
ta project:sonho:publicar-livro "Task"

# Change project
task 5 modify project:sonho:publicar-livro

# Remove project
project:
task 5 modify project:
```

---

## Status Flags

### Status Modifications

```bash
# Mark as done
task 5 done
td 5            # Alias

# Mark as waiting
task 5 modify status:waiting

# Mark as pending
task 5 modify status:pending

# Delete task
task 5 delete
```

### Start/Stop

```bash
# Start task
task 5 start
tstart 5        # Alias

# Stop task
task 5 stop
tstop 5         # Alias
```

---

## UDA Flags

### Hierarchy UDAs

```bash
# Sonho ID
sonho_id:publicar-livro
ta sonho_id:publicar-livro "Task"

# Objetivo ID
objetivo_id:obj_001_Q1
ta objetivo_id:obj_001_Q1 "Task"

# Objetivo Trimestre
objetivo_trimestre:Q1
ta objetivo_trimestre:Q1 "Task"

# Meta Ciclo
meta_ciclo:1
ta meta_ciclo:1 "Task"

# Tarefa Microciclo
tarefa_microciclo:1
ta tarefa_microciclo:1 "Task"

# Bloco Tempo
bloco_tempo:Manhã
bloco_tempo:Tarde
bloco_tempo:Noite
bloco_tempo:Planejamento
bloco_tempo:Revisão
```

### Other UDAs

```bash
# Ciclo
ciclo:1

# Onda Número
onda_numero:1

# Taxa Conclusão
taxa_conclusao:85.5

# Barreira
barreira:Estrutural
barreira:Recurso
barreira:Habilidade
barreira:Motivacional

# Teste de Fogo Dimensão
teste_fogo_dimensao:Resiliência
teste_fogo_dimensao:Coerência
teste_fogo_dimensao:Eficiência
teste_fogo_dimensao:Adaptabilidade
```

---

## Recurrence Flags

### Recurrence Patterns

```bash
# Daily
recur:daily
ta recur:daily due:today+1d "Daily task"

# Weekly
recur:weekly
ta recur:weekly due:eow "Weekly task"

# Monthly
recur:monthly
ta recur:monthly due:eom "Monthly task"

# Custom intervals
recur:2w        # Every 2 weeks
recur:1mo       # Every month
```

### Recurrence Helpers

```bash
# Daily recurrence helper
trecurd "Daily task"

# Weekly recurrence helper
trecurw "Weekly task"

# 15-day recurrence helper
trecur15 "15-day task"

# Monthly recurrence helper
trecurm "Monthly task"

# Working-day helper
twd 2026-01-06 15 "15 working days task"
```

---

## Description Modifiers

### Append

```bash
# Append text
task 5 append " - Updated"
```

### Prepend

```bash
# Prepend text
task 5 prepend "URGENT: "
```

### Replace

```bash
# Replace first match
task 5 modify /old/new/

# Replace all matches
task 5 modify /old/new/g
```

---

## Annotation Flags

### Add Annotation

```bash
# Add note
task 5 annotate "Blocked by external dependency"

# Multiple annotations
task 5 annotate "Progress: 50% complete"
task 5 annotate "Need to review with team"
```

### Remove Annotation

```bash
# Remove annotation by number
task 5 denotate 1
```

---

## Dependency Flags

### Dependencies

```bash
# Task depends on other tasks
depends:5
ta depends:5 "Task depends on task 5"

# Multiple dependencies
depends:5,6,7
ta depends:5,6,7 "Task depends on multiple tasks"
```

---

## Strategic Flag Combinations

### Daily Task

```bash
ta +execucao-diaria bloco_tempo:Manhã due:today priority:H "Morning task"
```

### Weekly Review Task

```bash
ta +relatorios due:eow "Weekly review"
```

### Meta Review Task

```bash
ta +revisao meta_ciclo:1 due:today+15d "Meta review"
```

### Monthly Supervision Task

```bash
ta +supervisao due:eom "Monthly supervision"
```

### Complete Hierarchy Task

```bash
ta project:sonho:publicar-livro \
   sonho_id:publicar-livro \
   objetivo_id:obj_001_Q1 \
   objetivo_trimestre:Q1 \
   meta_ciclo:1 \
   tarefa_microciclo:1 \
   bloco_tempo:Tarde \
   +execucao-diaria \
   priority:H \
   due:today \
   "Complete task"
```

---

## Flag Modifiers

### Attribute Modifiers

| Modifier | Example | Meaning |
|----------|---------|---------|
| (none) | `due:today` | Set value |
| `:` (empty) | `priority:` | Remove value |
| `not` | `priority.not:L` | Not equal |
| `before` | `due.before:today` | Less than |
| `after` | `due.after:today` | Greater than or equal |
| `any` | `project.any:` | Has value |
| `none` | `project.none:` | No value |

---

## Common Flag Patterns

### High Priority Today

```bash
ta priority:H due:today "Urgent today"
```

### Weekly Recurring

```bash
ta recur:weekly due:eow +relatorios "Weekly report"
```

### Meta Cycle Task

```bash
ta meta_ciclo:1 +revisao due:today+15d "Meta review"
```

### Morning Block Task

```bash
ta bloco_tempo:Manhã +execucao-diaria due:today "Morning work"
```

---

## Related Topics

- `th args` - Arguments and parameters
- `th filters` - Filter syntax
- `th recurrence` - Recurrence patterns
- `th udas` - UDA reference

---

*For more examples, see `TASKWARRIOR_COMPLETE_FEATURES.md` sections 6, 7, 8*
