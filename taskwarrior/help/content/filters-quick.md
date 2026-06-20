# Filters - Quick Reference

## Basic Filters

| Filter | Example | Description |
|--------|---------|-------------|
| Status | `status:pending` | Task status |
| Project | `project:sonho:publicar-livro` | Project name |
| Tag | `+execucao-diaria` | Has tag |
| Priority | `priority:H` | Priority level |
| Due Date | `due:today` | Due date |

## Date Filters

| Filter | Example | Description |
|--------|---------|-------------|
| Today | `due:today` | Due today |
| Tomorrow | `due:tomorrow` | Due tomorrow |
| After | `due.after:today-7d` | After date |
| Before | `due.before:today+7d` | Before date |
| Range | `due.after:today-7d due.before:today+7d` | Date range |

## UDA Filters

| Filter | Example | Description |
|--------|---------|-------------|
| Sonho | `sonho_id:publicar-livro` | Filter by sonho |
| Objetivo | `objetivo_id:obj_001_Q1` | Filter by objetivo |
| Meta | `meta_ciclo:1` | Filter by meta cycle |
| Tarefa | `tarefa_microciclo:1` | Filter by microcycle |
| Bloco | `bloco_tempo:Tarde` | Filter by time block |

## Filter Modifiers

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

## Virtual Tags

| Tag | Description |
|-----|-------------|
| `+PENDING` | Pending tasks |
| `+COMPLETED` | Completed tasks |
| `+ACTIVE` | Active tasks |
| `+WAITING` | Waiting tasks |
| `+TODAY` | Due today |
| `+TOMORROW` | Due tomorrow |
| `+OVERDUE` | Overdue |
| `+HIGH` | High priority |
| `+BLOCKED` | Blocked |
| `+READY` | Ready to work |

## Combined Filters

```bash
# AND (default)
task project:sonho:publicar-livro +execucao-diaria priority:H list

# OR
task "(project:sonho:publicar-livro OR project:sonho:melhorar-saude)" list

# NOT
task project.not:sonho:publicar-livro list
task -execucao-diaria list
```
