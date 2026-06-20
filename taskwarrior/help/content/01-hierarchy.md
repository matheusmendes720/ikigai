# Hierarchy Levels Guide

## Overview

Your Taskwarrior system uses a **5-level hierarchy** aligned with temporal cycles. Each level has specific time horizons, review cadences, and Taskwarrior attributes.

---

## Level 1: Sonhos (6-12 months)

**Time Horizon:** 6-12 months  
**Review Cadence:** Monthly (#supervisão)  
**Taskwarrior Attribute:** `project` (format: `project:sonho:<name>`)  
**UDAs:** `sonho_id`

### Strategic Context

Sonhos represent long-term aspirations and major life goals. They provide the strategic direction for all lower-level objectives and tasks.

### Creating Sonho Tasks

```bash
# Basic sonho task
ta project:sonho:publicar-livro sonho_id:publicar-livro "Write book outline"

# With priority and due date
ta project:sonho:publicar-livro sonho_id:publicar-livro priority:H due:2026-12-31 "Complete book manuscript"
```

### Viewing Sonhos

```bash
tsonho          # Custom report: all sonhos
task sonho       # Same as above
task project:sonho:publicar-livro list  # Tasks for specific sonho
```

### Best Practices

- Use `project:sonho:<name>` format consistently
- Set `sonho_id` UDA to match project name
- Review monthly using `task supervisao`
- Link objectives to sonhos via `objetivo_id`

---

## Level 2: Objetivos (3 months)

**Time Horizon:** 3 months (quarterly)  
**Review Cadence:** Trimestral (quarterly)  
**Taskwarrior Attributes:** `objetivo_id`, `objetivo_trimestre`  
**UDAs:** `objetivo_id`, `objetivo_trimestre` (values: Q1, Q2, Q3, Q4)

### Strategic Context

Objetivos break down Sonhos into quarterly milestones. Each objetivo should contribute directly to one or more Sonhos.

### Creating Objetivo Tasks

```bash
# Objetivo for Q1
ta objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 sonho_id:publicar-livro "Complete book outline"

# With meta_ciclo (links to 15-day meta)
ta objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 meta_ciclo:1 "Draft first 3 chapters"
```

### Viewing Objetivos

```bash
tobj            # Custom report: all objetivos
task objetivo   # Same as above
task objetivo_id:obj_001_Q1 list  # Tasks for specific objetivo
task objetivo_trimestre:Q1 list  # All Q1 objetivos
```

### Best Practices

- Use consistent naming: `obj_<number>_<quarter>`
- Set `objetivo_trimestre` to Q1, Q2, Q3, or Q4
- Link to sonho via `sonho_id`
- Review quarterly during #supervisão

---

## Level 3: Metas (15 days)

**Time Horizon:** 15 days úteis (working days)  
**Review Cadence:** Quinzenal (#revisão)  
**Taskwarrior Attribute:** `meta_ciclo` (numeric: 1, 2, 3, 4)  
**UDAs:** `meta_ciclo`

### Strategic Context

Metas represent 15-day working cycles within a quarter. Each quarter has approximately 4 metas (45 days úteis ÷ 15 = 3 metas, with buffer). Metas are reviewed every 15 days using #revisão tag.

### Creating Meta Tasks

```bash
# Meta for cycle 1
ta meta_ciclo:1 objetivo_id:obj_001_Q1 +revisao "Complete chapter 1 draft"

# With working-day due date (15 days from today)
twd $(date +%Y-%m-%d) 15 "Meta 15d úteis" +revisao meta_ciclo:1

# Using recurrence helper
trecur15 "Revisão quinzenal" meta_ciclo:1 +revisao
```

### Viewing Metas

```bash
tmeta           # Custom report: all metas
task meta       # Same as above
task meta_ciclo:1 list  # Tasks for specific meta cycle
task +revisao meta_ciclo:1 list  # Review tasks for cycle 1
```

### Best Practices

- Always set `meta_ciclo` when using `+revisao` tag
- Use working-day calculations for due dates (15 days)
- Review every 15 days using `task revisao`
- Link to objetivo via `objetivo_id`

### Important: Validation

The `on-add` hook warns if you add a task with `+revisao` tag without `meta_ciclo`:

```bash
# ❌ This will trigger a warning
ta +revisao "Review task"

# ✅ Correct: include meta_ciclo
ta +revisao meta_ciclo:1 "Review task"
```

---

## Level 4: Tarefas (5 days)

**Time Horizon:** 5 days úteis (microcycle)  
**Review Cadence:** Semanal (#relatórios)  
**Taskwarrior Attribute:** `tarefa_microciclo` (numeric: 1, 2, 3)  
**UDAs:** `tarefa_microciclo`

### Strategic Context

Tarefas break down Metas into 5-day working microcycles. Each meta (15 days) contains approximately 3 tarefas (microcycles). Tarefas are reviewed weekly.

### Creating Tarefa Tasks

```bash
# Tarefa for microcycle 1
ta tarefa_microciclo:1 meta_ciclo:1 +execucao-diaria "Draft section 1.1"

# With working-day due date (5 days from today)
twd $(date +%Y-%m-%d) 5 "Tarefa 5d úteis" tarefa_microciclo:1 +execucao-diaria

# With bloco_tempo
ta tarefa_microciclo:1 bloco_tempo:Manhã +execucao-diaria "Morning writing session"
```

### Viewing Tarefas

```bash
tmicro          # Custom report: all tarefas
task tarefa      # Same as above
task tarefa_microciclo:1 list  # Tasks for specific microcycle
task meta_ciclo:1 tarefa_microciclo:1 list  # Tarefas for meta cycle 1
```

### Best Practices

- Use `tarefa_microciclo:1`, `tarefa_microciclo:2`, `tarefa_microciclo:3`
- Link to meta via `meta_ciclo`
- Use `+execucao-diaria` tag for daily execution tasks
- Review weekly using `task relatorios`

---

## Level 5: Atividades (daily)

**Time Horizon:** Daily  
**Review Cadence:** Diário (#narrativa)  
**Taskwarrior Attributes:** `bloco_tempo`, standard task attributes  
**UDAs:** `bloco_tempo` (values: Manhã, Tarde, Noite, Planejamento, Revisão)

### Strategic Context

Atividades are the daily execution tasks. They are organized by time blocks (Blocos de Tempo) and reviewed daily in the morning (#narrativa) and evening routines.

### Creating Atividade Tasks

```bash
# Basic atividade
ta +execucao-diaria "Review email"

# With bloco_tempo
ta bloco_tempo:Manhã +execucao-diaria "Morning meditation"
ta bloco_tempo:Tarde +execucao-diaria "Write blog post"
ta bloco_tempo:Noite +execucao-diaria "Evening review"

# With due date (today)
ta due:today bloco_tempo:Manhã +execucao-diaria "Urgent task"
```

### Viewing Atividades

```bash
tbloco          # Custom report: tasks by time blocks
task blocos     # Same as above
task bloco_tempo:Manhã due:today list  # Morning tasks due today
task +execucao-diaria due:today list  # Daily execution tasks
```

### Best Practices

- Use `+execucao-diaria` tag for daily tasks
- Set `bloco_tempo` to organize by time of day
- Review daily using `tm` (morning) and `te` (evening)
- Use `due:today` for urgent daily tasks

---

## Hierarchy Relationships

### Linking Levels

Tasks should link across hierarchy levels:

```bash
# Complete example: Sonho → Objetivo → Meta → Tarefa → Atividade

# Sonho
ta project:sonho:publicar-livro sonho_id:publicar-livro "Publish book"

# Objetivo (linked to sonho)
ta objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 sonho_id:publicar-livro "Complete Q1 chapters"

# Meta (linked to objetivo)
ta meta_ciclo:1 objetivo_id:obj_001_Q1 +revisao "Complete chapter 1"

# Tarefa (linked to meta)
ta tarefa_microciclo:1 meta_ciclo:1 +execucao-diaria "Draft section 1.1"

# Atividade (linked to tarefa, with bloco_tempo)
ta tarefa_microciclo:1 bloco_tempo:Manhã +execucao-diaria "Write 500 words"
```

### Filtering Across Levels

```bash
# All tasks for a sonho (all levels)
task sonho_id:publicar-livro list

# All tasks for an objetivo
task objetivo_id:obj_001_Q1 list

# All tasks for a meta cycle
task meta_ciclo:1 list

# All tasks for a microcycle
task tarefa_microciclo:1 list
```

---

## Temporal Cycles Summary

| Level | Time Horizon | Review | UDA/Attribute | Report |
|-------|--------------|--------|---------------|--------|
| **Sonhos** | 6-12 months | Monthly (#supervisão) | `project`, `sonho_id` | `tsonho` |
| **Objetivos** | 3 months | Trimestral | `objetivo_id`, `objetivo_trimestre` | `tobj` |
| **Metas** | 15 days | Quinzenal (#revisão) | `meta_ciclo` | `tmeta` |
| **Tarefas** | 5 days | Semanal (#relatórios) | `tarefa_microciclo` | `tmicro` |
| **Atividades** | Daily | Diário (#narrativa) | `bloco_tempo` | `tbloco` |

---

## Related Topics

- `th workflows` - Workflow patterns for each level
- `th udas` - Complete UDA reference
- `th reports` - Custom reports for each level
- `th filters` - Filtering by hierarchy levels

---

*For more examples, see `TASKWARRIOR_HOWTO.md`*
^tr-2k1lak12i