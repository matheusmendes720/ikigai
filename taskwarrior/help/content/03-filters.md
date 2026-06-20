# Filter Syntax & Examples

## Overview

Filters allow you to select specific tasks based on attributes, dates, tags, UDAs, and more. This guide covers filter syntax with strategic examples for your hierarchy system.

---

## Basic Filter Syntax

**General Format:**
```bash
task [filter] <command> [modifications]
```

**Examples:**
```bash
# Filter + command
task project:sonho:publicar-livro list

# Filter + command + modifications
task meta_ciclo:1 modify priority:H
```

---

## Status Filters

### By Status

```bash
# Pending tasks (default)
task status:pending list
task list  # Same as above

# Completed tasks
task status:completed list
task completed

# Waiting tasks
task status:waiting list
task waiting
tw

# Deleted tasks
task status:deleted list
```

### Virtual Tags for Status

```bash
task +PENDING list    # Pending tasks
task +COMPLETED list   # Completed tasks
task +WAITING list     # Waiting tasks
task +ACTIVE list      # Active (started) tasks
tactive                # Alias for active tasks
```

---

## Project Filters

### By Project (Sonhos)

```bash
# Specific sonho
task project:sonho:publicar-livro list
tsonho  # View all sonhos

# All tasks with project
task project.any: list

# Tasks without project
task project.none: list

# Exclude specific project
task project.not:sonho:publicar-livro list
```

### Strategic Examples

```bash
# All tasks for a sonho
task sonho_id:publicar-livro list

# All tasks for an objetivo
task objetivo_id:obj_001_Q1 list

# All tasks for a meta cycle
task meta_ciclo:1 list

# All tasks for a microcycle
task tarefa_microciclo:1 list
```

---

## Tag Filters

### By Tags

```bash
# Tasks with tag
task +execucao-diaria list
task +narrativa list
task +relatorios list
task +revisao list
task +supervisao list

# Tasks without tag
task -execucao-diaria list

# Multiple tags (AND)
task +execucao-diaria +obrigacoes list

# Either tag (OR)
task '(+execucao-diaria OR +obrigacoes)' list
```

### Review Type Tags

```bash
# Daily execution
task +execucao-diaria list

# Weekly reports
task +relatorios list

# 15-day reviews
task +revisao list

# Monthly supervision
task +supervisao list
```

---

## Priority Filters

### By Priority

```bash
# High priority
task priority:H list
task +HIGH list
tlh  # Alias for high priority

# Medium priority
task priority:M list
task +MEDIUM list

# Low priority
task priority:L list
task +LOW list

# No priority
task priority.none: list
task +NONE list

# Not low priority
task priority.not:L list
```

---

## Date Filters

### Relative Dates

```bash
# Due today
task due:today list
tld  # Alias

# Due tomorrow
task due:tomorrow list
tldt  # Alias

# Due yesterday
task due:yesterday list

# Overdue
task +OVERDUE list
tlo  # Alias

# Due this week
task +WEEK list

# Due this month
task +MONTH list
```

### Date Ranges

```bash
# Due after date
task due.after:today-7d list
task due.after:2026-01-01 list

# Due before date
task due.before:today+7d list
task due.before:2026-12-31 list

# Due in range
task due.after:today-7d due.before:today+7d list
```

### Entry Dates

```bash
# Created after date
task entry.after:today-7d list

# Created before date
task entry.before:today list
```

### Modification Dates

```bash
# Modified in last 7 days
task modified.after:today-7d list

# Modified in last 30 days
task modified.after:today-30d list
```

### Completion Dates

```bash
# Completed after date
task completed end.after:today-7d
task end.after:today-7d list

# Completed before date
task end.before:today list
```

---

## UDA Filters

### Hierarchy UDAs

```bash
# By sonho_id
task sonho_id:publicar-livro list

# By objetivo_id
task objetivo_id:obj_001_Q1 list

# By objetivo_trimestre
task objetivo_trimestre:Q1 list

# By meta_ciclo
task meta_ciclo:1 list
task meta_ciclo:2 list

# By tarefa_microciclo
task tarefa_microciclo:1 list

# By bloco_tempo
task bloco_tempo:Manhã list
task bloco_tempo:Tarde list
task bloco_tempo:Noite list
```

### UDA Comparisons

```bash
# Meta cycle greater than 1
task meta_ciclo.greater:1 list

# Meta cycle less than 3
task meta_ciclo.less:3 list

# Taxa conclusão greater than 80
task taxa_conclusao.greater:80 list
```

### UDA Presence

```bash
# Has meta_ciclo (any value)
task meta_ciclo.any: list

# Has bloco_tempo
task bloco_tempo.any: list

# No meta_ciclo
task meta_ciclo.none: list
```

---

## Text Search Filters

### Description Search

```bash
# Contains text
task "description~livro" list
task "description~capitulo" list

# Exact match
task "description:exact text" list

# Case insensitive
task "description~LIVRO" list
```

### Annotation Search

```bash
# Search annotations
task "annotation~blocked" list
task "annotation~progress" list
```

---

## Combined Filters

### Multiple Conditions (AND)

```bash
# Project AND tag AND priority
task project:sonho:publicar-livro +execucao-diaria priority:H list

# Meta cycle AND due today
task meta_ciclo:1 due:today list

# Bloco tempo AND due today
task bloco_tempo:Manhã due:today list
```

### OR Conditions

```bash
# Either project OR tag
task '(project:sonho:publicar-livro OR project:sonho:melhorar-saude)' list

# Either tag
task '(+execucao-diaria OR +obrigacoes)' list
```

### NOT Conditions

```bash
# Not specific project
task project.not:sonho:publicar-livro list

# Not specific tag
task -execucao-diaria list

# Not low priority
task priority.not:L list
```

### Complex Filters

```bash
# Complex example: Sonho with high priority due this week
task '(project:sonho:publicar-livro AND priority:H AND due.after:today due.before:today+7d)' list

# Review tasks for meta cycle 1
task '+revisao meta_ciclo:1' list

# Daily execution tasks due today in morning block
task '+execucao-diaria bloco_tempo:Manhã due:today' list
```

---

## Virtual Tags

### Status-Based

```bash
+PENDING      # Pending tasks
+COMPLETED    # Completed tasks
+WAITING      # Waiting tasks
+ACTIVE       # Active (started) tasks
+BLOCKED      # Blocked by dependencies
+READY        # Ready to work on
```

### Date-Based

```bash
+TODAY        # Due today
+TOMORROW     # Due tomorrow
+YESTERDAY    # Due yesterday
+WEEK         # Due this week
+MONTH        # Due this month
+OVERDUE      # Overdue
+DUETODAY     # Due today
+DUETOMORROW  # Due tomorrow
```

### Priority-Based

```bash
+HIGH         # High priority
+MEDIUM       # Medium priority
+LOW          # Low priority
+NONE         # No priority
```

### Other

```bash
+BLOCKING     # Blocking other tasks
+UNBLOCKED    # Not blocked
+PARENT       # Has child tasks
+CHILD        # Has parent task
+ANNOTATED    # Has annotations
+PRIORITY     # Has priority set
+PROJECT      # Has project
+TAGGED       # Has tags
```

---

## Strategic Filter Patterns

### Daily Workflow Filters

```bash
# Morning routine
task '+execucao-diaria bloco_tempo:Manhã due:today' list

# Afternoon tasks
task 'bloco_tempo:Tarde due:today' list

# Evening tasks
task 'bloco_tempo:Noite due:today' list
```

### Weekly Workflow Filters

```bash
# Weekly report tasks
task '+relatorios modified.after:today-7d' list

# Completed this week
task 'completed end.after:today-7d' list
```

### 15-Day Workflow Filters

```bash
# Meta review tasks
task '+revisao meta_ciclo:1' list

# All tasks for meta cycle
task 'meta_ciclo:1' list
```

### Monthly Workflow Filters

```bash
# Supervision tasks
task '+supervisao modified.after:today-30d' list

# All tasks for a sonho
task 'sonho_id:publicar-livro' list
```

---

## Filter Modifiers

### Attribute Modifiers

| Modifier | Example | Meaning |
|----------|---------|---------|
| (none) | `due:today` | Fuzzy match |
| `not` | `due.not:today` | Fuzzy non-match |
| `before`, `below` | `due.before:today` | Exact date comparison (<) |
| `after`, `above` | `due.after:today` | Exact date comparison (>=) |
| `none` | `project.none:` | Empty |
| `any` | `project.any:` | Not empty |
| `is`, `equals` | `project.is:x` | Exact match |
| `isnt` | `project.isnt:x` | Exact non-match |
| `has`, `contains` | `desc.has:Hello` | Pattern match |
| `hasnt` | `desc.hasnt:Hello` | Pattern non-match |
| `startswith`, `left` | `desc.left:Hel` | Beginning match |
| `endswith`, `right` | `desc.right:llo` | End match |
| `word` | `desc.word:Hello` | Boundaried word match |
| `noword` | `desc.noword:Hello` | Boundaried word non-match |

---

## Related Topics

- `th args` - Arguments and parameters
- `th flags` - Flags and modifiers
- `th hierarchy` - Hierarchy-level filtering
- `th workflows` - Workflow-specific filters

---

*For more examples, see `TASKWARRIOR_COMPLETE_FEATURES.md` section 4*
