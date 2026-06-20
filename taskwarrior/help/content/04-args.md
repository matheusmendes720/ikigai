# Arguments & Parameters

## Overview

This guide covers Taskwarrior command arguments, parameters, and how to structure task descriptions and modifications.

---

## Command Structure

**General Format:**
```bash
task [filter] <command> [modifications]
```

**Components:**
1. **Filter** (optional) - Selects which tasks to operate on
2. **Command** (required) - What action to perform
3. **Modifications** (optional) - Changes to apply

---

## Task Creation Arguments

### Basic Task Creation

```bash
# Simple task
ta "Write blog post"
# or
task add "Write blog post"
```

### With Attributes

```bash
# With project
ta project:sonho:publicar-livro "Write chapter 1"

# With priority
ta priority:H "Urgent task"

# With due date
ta due:2026-12-15 "Task with deadline"

# With tags
ta +execucao-diaria +obrigacoes "Daily task"
```

### Complex Task Creation

```bash
# Full example with hierarchy
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
   "Write section 1.1"
```

---

## Description Handling

### Quoting Descriptions

**Spaces require quotes:**
```bash
# ✅ Correct
ta "Task with spaces"
ta 'Task with spaces'

# ❌ Incorrect (will be treated as multiple arguments)
ta Task with spaces
```

### Special Characters

**Escape special characters:**
```bash
# Quotes in description
ta "Task with \"quotes\""
ta 'Task with "quotes"'

# Special shell characters
ta "Task with \$variable"
ta "Task with \`command\`"
```

### Multi-line Descriptions

**Use quotes for multi-line:**
```bash
ta "First line
Second line
Third line"
```

---

## Modification Arguments

### Modify Existing Task

```bash
# Change priority
task 5 modify priority:H

# Change due date
task 5 modify due:2026-12-20

# Add tag
task 5 modify +urgent

# Remove tag
task 5 modify -urgent

# Change project
task 5 modify project:sonho:publicar-livro

# Modify UDA
task 5 modify meta_ciclo:2

# Multiple changes
task 5 modify priority:H due:2026-12-20 +urgent
```

### Append/Prepend Description

```bash
# Append text
task 5 append " - Updated"

# Prepend text
task 5 prepend "URGENT: "
```

### Description Replacement

```bash
# Replace first match
task 5 modify /old/new/

# Replace all matches
task 5 modify /old/new/g
```

---

## Filter Arguments

### Task IDs

```bash
# Single ID
task 5 done
task 5 modify priority:H

# Multiple IDs
task 5 6 7 done
task 5,6,7 done
task 5-7 done
task 1,2-5,19 modify priority:H
```

### UUIDs

```bash
# UUID format
task ebeeab00-ccf8-464b-8b58-f7f2d606edfb done
```

### Filters

```bash
# Filter by project
task project:sonho:publicar-livro list

# Filter by tag
task +execucao-diaria list

# Filter by date
task due:today list

# Combined filters
task project:sonho:publicar-livro +execucao-diaria priority:H list
```

---

## Attribute Arguments

### Projects

```bash
# Set project
ta project:sonho:publicar-livro "Task"

# Change project
task 5 modify project:sonho:publicar-livro

# Remove project
task 5 modify project:
```

### Priority

```bash
# Set priority
ta priority:H "High priority task"
ta priority:M "Medium priority task"
ta priority:L "Low priority task"

# Change priority
task 5 modify priority:H

# Remove priority
task 5 modify priority:
```

### Due Dates

```bash
# Absolute date
ta due:2026-12-15 "Task"

# Relative date
ta due:today "Task"
ta due:tomorrow "Task"
ta due:eow "Task"      # End of week
ta due:eom "Task"      # End of month

# Date arithmetic
ta due:today+7d "Task in 7 days"
ta due:today-7d "Task 7 days ago"
```

### Tags

```bash
# Add tag
ta +execucao-diaria "Task"
task 5 modify +urgent

# Remove tag
task 5 modify -execucao-diaria

# Multiple tags
ta +execucao-diaria +obrigacoes "Task"
task 5 modify +urgent -obrigacoes
```

### UDAs

```bash
# Set UDA
ta sonho_id:publicar-livro "Task"
ta objetivo_id:obj_001_Q1 "Task"
ta meta_ciclo:1 "Task"
ta bloco_tempo:Manhã "Task"

# Modify UDA
task 5 modify meta_ciclo:2
task 5 modify bloco_tempo:Tarde

# Remove UDA
task 5 modify meta_ciclo:
```

---

## Special Arguments

### The `--` Separator

**Treat everything after `--` as description:**
```bash
# Useful when description starts with attribute-like text
ta -- project:Home needs scheduling
ta -- priority:H is important
```

### Abbreviations

**Commands and attributes can be abbreviated:**
```bash
# Full command
task list project:sonho:publicar-livro

# Abbreviated
task li pro:sonho:publicar-livro
```

---

## Strategic Examples

### Creating Hierarchy Tasks

```bash
# Sonho level
ta project:sonho:publicar-livro sonho_id:publicar-livro "Publish book"

# Objetivo level
ta objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 sonho_id:publicar-livro "Complete Q1 chapters"

# Meta level
ta meta_ciclo:1 objetivo_id:obj_001_Q1 +revisao "Review meta cycle 1"

# Tarefa level
ta tarefa_microciclo:1 meta_ciclo:1 +execucao-diaria "Complete microcycle 1"

# Atividade level
ta tarefa_microciclo:1 bloco_tempo:Manhã +execucao-diaria due:today "Morning task"
```

### Modifying Hierarchy Tasks

```bash
# Update meta cycle
task 5 modify meta_ciclo:2

# Change bloco tempo
task 5 modify bloco_tempo:Tarde

# Add review tag
task 5 modify +revisao

# Update objetivo
task 5 modify objetivo_id:obj_002_Q1
```

---

## Common Patterns

### Batch Operations

```bash
# Complete multiple tasks
task 5 6 7 done

# Modify multiple tasks
task 5-10 modify priority:H

# Delete multiple tasks
task 5,6,7 delete
```

### Conditional Modifications

```bash
# Modify all high priority tasks
task priority:H modify due:today

# Add tag to all tasks in project
task project:sonho:publicar-livro modify +urgent

# Update meta cycle for all tasks in cycle
task meta_ciclo:1 modify meta_ciclo:2
```

---

## Related Topics

- `th flags` - Flags and modifiers
- `th filters` - Filter syntax
- `th hierarchy` - Hierarchy arguments
- `th udas` - UDA arguments

---

*For more examples, see `TASKWARRIOR_COMPLETE_FEATURES.md` section 3*
