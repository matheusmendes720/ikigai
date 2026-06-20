# Complete Alias Reference

## Overview

This guide provides a complete reference for all Taskwarrior aliases in your system. Aliases are available in both PowerShell (`scripts/task-aliases.ps1`) and WSL (`~/.task_aliases.sh`).

---

## Core Aliases

### Task Management

| Alias | Command | Description |
|-------|---------|-------------|
| `ta` | `task add` | Add new task |
| `tl` | `task list` | List tasks |
| `tn` | `task next` | Next tasks (by urgency) |
| `td` | `task done` | Complete task |
| `tc` | `task done` | Complete task (alternative) |
| `tall` | `task all` | All tasks (pending, completed, etc.) |
| `tcomp` | `task completed` | Completed tasks |
| `tready` | `task ready` | Ready tasks |
| `tblocked` | `task blocked` | Blocked tasks |
| `tactive` | `task +ACTIVE list` | Active tasks |
| `tw` | `task waiting` | Waiting tasks |

### Date-Based Aliases

| Alias | Command | Description |
|-------|---------|-------------|
| `tld` | `task due:today list` | Tasks due today |
| `tldt` | `task due:tomorrow list` | Tasks due tomorrow |
| `tlo` | `task +OVERDUE list` | Overdue tasks |

### Priority Aliases

| Alias | Command | Description |
|-------|---------|-------------|
| `tlh` | `task priority:H list` | High priority tasks |

### Information Aliases

| Alias | Command | Description |
|-------|---------|-------------|
| `ti <id>` | `task <id> info` | Task information |
| `ts` | `task summary` | Summary statistics |
| `tst` | `task stats` | Detailed statistics |
| `tp` | `task projects` | List projects |
| `ttags` | `task tags` | List tags |
| `tcal` | `task calendar` | Calendar view |
| `tdiag` | `task diagnostics` | System diagnostics |

### Data Management

| Alias | Command | Description |
|-------|---------|-------------|
| `tex` | `task export` | Export tasks |
| `tim` | `task import` | Import tasks |
| `tundo` | `task undo` | Undo last action |

---

## Workflow Aliases

### Daily Workflows

| Alias | Command | Description |
|-------|---------|-------------|
| `tm` | Morning routine | Narrativa, due:today, blocos |
| `te` | Evening routine | Completed today, plan tomorrow |
| `tstandup` | Standup | Daily standup view |

**Morning Routine (`tm`):**
```bash
tm
# Equivalent to:
task narrativa
task due:today list
task blocos
```

**Evening Routine (`te`):**
```bash
te
# Equivalent to:
task completed end:today
task due:tomorrow list
```

### Weekly Workflows

| Alias | Command | Description |
|-------|---------|-------------|
| `twk` | Weekly review | Relatorios + summary |

**Weekly Review (`twk`):**
```bash
twk
# Equivalent to:
task relatorios
task modified.after:today-7d summary
```

---

## Hierarchy Aliases

| Alias | Command | Description |
|-------|---------|-------------|
| `tsonho` | `task sonho` | View all Sonhos |
| `tobj` | `task objetivo` | View Objetivos |
| `tmeta` | `task meta` | View Metas (15-day) |
| `tmicro` | `task tarefa` | View Tarefas (5-day) |
| `tbloco` | `task blocos` | View Blocos de Tempo |

---

## Context Aliases

| Alias | Command | Description |
|-------|---------|-------------|
| `tctxw` | `task context work` | Work context |
| `tctxft` | `task context focus_today` | Focus today context |
| `tctxwk` | `task context week` | Week context |
| `tctxrev` | `task context review` | Review context |
| `tctxciclo` | `task context ciclo` | Ciclo context |
| `tctxonda` | `task context onda` | Onda context |
| `tctxtf` | `task context teste_fogo` | Teste de Fogo context |
| `tctx0` | `task context none` | Clear context |

---

## Recurrence Aliases

### Calendar-Based

| Alias | Command | Description |
|-------|---------|-------------|
| `trecurd "<desc>"` | `task add recur:daily due:today+1d` | Daily recurrence |
| `trecurw "<desc>"` | `task add recur:weekly due:eow` | Weekly recurrence |
| `trecur15 "<desc>"` | `task add recur:2w due:today+15d` | 15-day recurrence |
| `trecurm "<desc>"` | `task add recur:monthly due:eom` | Monthly recurrence |

### Working-Day Helper

| Alias | Command | Description |
|-------|---------|-------------|
| `twd <start> <days> "<desc>"` | Working-day calculator | Calculate working days |

**Example:**
```bash
twd 2026-01-06 15 "Meta 15d úteis" +revisao meta_ciclo:1
```

---

## Task Operation Aliases

| Alias | Command | Description |
|-------|---------|-------------|
| `tstart <id>` | `task <id> start` | Start task |
| `tstop <id>` | `task <id> stop` | Stop task |

---

## Help Aliases

### Custom Help System (Comprehensive - Docs 00-12)

| Alias | Command | Description |
|-------|---------|-------------|
| `th` | Custom help router | Overview (default) |
| `th <topic>` | Custom help topic | Specific help topic (detailed) |
| `thq <topic>` | Quick reference | Quick reference (tabular format) |

**Help Topics:**
- `th` or `th overview` - Overview
- `th hierarchy` - Hierarchy guide
- `th workflows` - Workflow guides
- `th filters` - Filter syntax
- `th args` - Arguments
- `th flags` - Flags
- `th reports` - Reports
- `th contexts` - Contexts
- `th recurrence` - Recurrence
- `th udas` - UDAs
- `th aliases` - This guide
- `th blocks` - Blocos de Tempo
- `th metrics` - Metrics

### Vanilla Taskwarrior Help

| Alias | Command | Description |
|-------|---------|-------------|
| `thelp` | `task help` | Vanilla Taskwarrior help |
| `thelp <command>` | `task help <command>` | Help for specific command |
| `tcmd` | `task commands` | List all Taskwarrior commands |
| `tman <page>` | `man task-<page>` | View man page (e.g., `tman task`, `tman taskrc`) |
| `tdoctask` | `man task` | View task man page |
| `tdoctaskrc` | `man taskrc` | View taskrc man page |
| `tdoctaskcolor` | `man task-color` | View task-color man page |
| `tdoctasksync` | `man task-sync` | View task-sync man page |

---

## Alias Usage Patterns

### Daily Workflow

```bash
# Morning
tm              # Morning routine
tld             # Tasks due today
tbloco          # Time blocks

# During day
tactive         # Active tasks
tstart <id>     # Start task
tstop <id>      # Stop task
td <id>         # Complete task

# Evening
te              # Evening routine
tldt            # Tasks due tomorrow
```

### Weekly Workflow

```bash
# Weekly review
twk             # Weekly review
task relatorios # Weekly report
ts              # Summary
```

### Hierarchy Workflow

```bash
# View hierarchy levels
tsonho          # Sonhos
tobj            # Objetivos
tmeta           # Metas
tmicro          # Tarefas
tbloco          # Blocos
```

### Context Workflow

```bash
# Set context
tctxw           # Work context
tctxft          # Focus today
tctxwk          # Week context

# Clear context
tctx0           # Clear
```

### Recurrence Workflow

```bash
# Calendar-based
trecurd "Daily task"
trecurw "Weekly task"
trecur15 "15-day task"
trecurm "Monthly task"

# Working-day
twd 2026-01-06 15 "15 working days"
```

---

## Quick Reference

### Most Used Aliases

```bash
ta              # Add task
tl              # List tasks
tn              # Next tasks
td <id>         # Complete task
tm              # Morning routine
te              # Evening routine
twk             # Weekly review
tsonho          # View sonhos
tbloco          # View time blocks
th              # Help
```

### Alias Categories

- **Core:** ta, tl, tn, td, tc, ts, tst
- **Workflows:** tm, te, twk, tstandup
- **Hierarchy:** tsonho, tobj, tmeta, tmicro, tbloco
- **Contexts:** tctxw, tctxft, tctxwk, tctxrev, tctxciclo, tctxonda, tctxtf, tctx0
- **Recurrence:** trecurd, trecurw, trecur15, trecurm, twd
- **Status:** tready, tblocked, tactive, tw, tlo
- **Info:** ti, tp, ttags, tcal, tdiag
- **Data:** tex, tim, tundo

---

## Related Topics

- `th workflows` - Workflow-specific aliases
- `th hierarchy` - Hierarchy aliases
- `th contexts` - Context aliases
- `th recurrence` - Recurrence aliases

---

*Aliases are defined in `scripts/task-aliases.ps1` (PowerShell) and `~/.task_aliases.sh` (WSL)*
