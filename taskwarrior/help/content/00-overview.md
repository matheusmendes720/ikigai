# Taskwarrior Help System - Overview

**5-level hierarchy** (Sonho → Objetivo → Meta → Tarefa → Atividade)

and **strategic workflows** (#narrativa, #relatórios, #revisão, #supervisão). ^tr-x9cy6e03l

---

## Quick Navigation

### Core Topics

**`th hierarchy`** - 5-Level Hierarchy Guide

- Sonhos (6-12 months), Objetivos (3 months), Metas (15 days), Tarefas (5 days), Atividades (daily)
- How to structure tasks at each level
- UDAs and attributes for each level

**`th workflows`** - Workflow Guides

- Daily (#narrativa), Weekly (#relatórios), 15-day (#revisão), Monthly (#supervisão)
- Rotina Inicial (morning) and Rotina Final (evening)
- Review cycles and correction protocols ^tr-tlmqwdldn

**`th filters`** - Filter Syntax & Examples

- Filter by hierarchy levels (sonho_id, objetivo_id, meta_ciclo, etc.)
- Filter by review types (+narrativa, +relatorios, +revisao, +supervisao)
- Date filters, status filters, virtual tags

**`th args`** - Arguments & Parameters

- Task creation arguments
- Modification syntax
- Description and annotation handling

**`th flags`** - Flags & Modifiers

- Priority flags (H, M, L)
- Date modifiers (due, wait, scheduled)
- Tag operations (+tag, -tag)

**`th reports`** - Custom Reports Reference

- narrativa, relatorios, revisao, supervisao
- sonho, objetivo, meta, tarefa
- blocos, ready, blocked, active, waiting

**`th contexts`** - Context System

- work, focus_today, week, review
- ciclo, onda, teste_fogo
- How to switch and clear contexts

**`th recurrence`** - Recurrence Patterns

- Calendar-based (daily, weekly, monthly)
- Working-day calculations (5, 15, 45 days)
- Using twd, trecurd, trecurw, trecur15, trecurm

**`th udas`** - User Defined Attributes

- sonho_id, objetivo_id, objetivo_trimestre
- meta_ciclo, tarefa_microciclo, bloco_tempo
- ciclo, onda_numero, taxa_conclusao, barreira, teste_fogo_dimensao

**`th aliases`** - Complete Alias Reference

- Core aliases (ta, tl, tn, td, etc.)
- Workflow aliases (tm, te, twk)
- Hierarchy aliases (tsonho, tobj, tmeta, tmicro, tbloco)
- Context aliases (tctxw, tctxft, etc.)

**`th blocks`** - Blocos de Tempo

- Manhã, Tarde, Noite, Planejamento, Revisão
- Time-blocking strategies
- Energy management

**`th metrics`** - Metrics & Analysis

- Taxa de Conclusão (completion rate)
- Eficiência Sistêmica (system efficiency)
- Coerência Estratégica (strategic coherence)
- Using calculate-metrics.py

---

## WSL / Windows Interop Notes

### Path Handling

Since Taskwarrior runs inside WSL, file paths work differently:

**Windows PowerShell:**

```powershell
# Windows paths are automatically converted by wrapper functions
ta "Task description"
tl
```

**WSL/Bash:**

```bash
# Use Linux-style paths
task add "Task description"
task list

# For Windows files, use /mnt/c/ prefix
task export > /mnt/c/Users/mathe/backup.json
```

### Encoding

The help system automatically handles UTF-8 encoding. If you see garbled characters:

- PowerShell: Encoding is set automatically via `[Console]::OutputEncoding`
- WSL: Uses UTF-8 by default

### Exit Codes

All help commands (`th`, `thq`) return exit code 0 (success), allowing chaining:

```bash
th aliases && echo "Help displayed successfully"
```

---

## Your System Architecture

### Temporal Cycles

- **5 Dias Úteis** → Tarefas (microcycles)
- **15 Dias Úteis** → Metas (waves)
- **45 Dias Úteis** → Ciclos (macro phases)
- **180 Dias Úteis** → Teste de Fogo (fire test)

### Review Cadences

- **Daily (#narrativa)** → Morning routine, daily execution
- **Weekly (#relatórios)** → Weekly reports, progress tracking
- **15-day (#revisão)** → Meta reviews, route correction
- **Monthly (#supervisão)** → Sonho supervision, strategic alignment ^tr-qeonchjga

### Hierarchy Levels

```
SONHOS (6-12 months)
│
├─ OBJETIVOS (3 months) → Q1, Q2, Q3, Q4
│  │
│  ├─ METAS (15 days) → Cycles 1-4 per quarter
│  │  │
│  │  ├─ TAREFAS (5 days) → Microcycles 1-3 per meta
│  │  │  │
│  │  │  └─ ATIVIDADES (daily) → Execution 
|____________________________________________________
```

---

## Quick Start Examples

### Daily Morning Routine

```bash
tm              # Rotina Inicial (narrativa, due:today, blocos)
tld             # List tasks due today
tbloco          # View tasks by time blocks
```

### Daily Evening Routine

```bash
te              # Rotina Final (completed today, plan tomorrow)
tldt            # List tasks due tomorrow
```

### Weekly Review

```bash
twk             # Weekly review (relatorios + summary)
task relatorios # Weekly report view
```

### Working with Hierarchy

```bash
tsonho          # View all Sonhos
tobj            # View Objetivos
tmeta           # View Metas (15-day)
tmicro          # View Tarefas (5-day)
```

### Creating Tasks with Hierarchy

```bash
# Sonho level
ta project:sonho:publicar-livro sonho_id:publicar-livro "Write chapter 1"

# Objetivo level
ta objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 meta_ciclo:1 "Complete outline"

# Meta level (15 days)
ta meta_ciclo:1 bloco_tempo:Tarde +revisao "Review chapter 3"

# Tarefa level (5 days)
ta tarefa_microciclo:1 bloco_tempo:Manhã +execucao-diaria "Draft section 1.1"
```

---

## Common Commands

### Task Management

- `ta "description"` - Add task
- `tl` - List tasks
- `tn` - Next tasks (by urgency)
- `td <id>` - Complete task
- `ti <id>` - Task info

### Status & Readiness

- `tready` - Ready tasks
- `tblocked` - Blocked tasks
- `tactive` - Active tasks
- `tw` - Waiting tasks
- `tlo` - Overdue tasks

### Contexts

- `tctxw` - Work context
- `tctxft` - Focus today
- `tctxwk` - Week context
- `tctxrev` - Review context
- `tctx0` - Clear context

### Recurrence

- `trecurd "desc"` - Daily recurrence
- `trecurw "desc"` - Weekly recurrence
- `trecur15 "desc"` - 15-day recurrence
- `twd 2026-01-06 15 "desc"` - Working-day calculation

---

## Getting Help

**`th`** and **`thq`** = this custom system (**taskwarrior/help**). **`thelp`** = vanilla Taskwarrior help (official source, `task help`).

### Custom Help Commands (Comprehensive - Docs 00-12)

- **`th`** - This overview (detailed format) - default
- **`th <topic>`** - Specific topic help (detailed)
- **`thq <topic>`** - Quick reference (tabular format)
- **`th --debug`** - Debug mode (set `$env:TASK_HELP_DEBUG=1`)

### Help Topics

Available topics: `overview`, `hierarchy`, `workflows`, `filters`, `args`, `flags`, `reports`, `contexts`, `recurrence`, `udas`, `aliases`, `blocks`, `metrics`

### Quick Reference

For fast lookup, use `thq` instead of `th`:

```bash
thq aliases    # Quick aliases table
thq reports    # Quick reports table
thq udas       # Quick UDAs table
```

### Vanilla Taskwarrior Help Commands (official source)

- **`thelp`** - Vanilla Taskwarrior help (`task help`)
- **`thelp <command>`** - Vanilla help for specific command
- **`tcmd`** - List all Taskwarrior commands
- **`tman <page>`** - View man page (e.g., `tman task`, `tman taskrc`)
- **`tdoctask`** - View `man task`
- **`tdoctaskrc`** - View `man taskrc`
- **`tdoctaskcolor`** - View `man task-color`
- **`tdoctasksync`** - View `man task-sync`

---

## Related Topics

- See `th hierarchy` for detailed hierarchy guide
- See `th workflows` for workflow patterns
- See `th aliases` for complete alias reference
- See `TASKWARRIOR_HOWTO.md` for quick reference

---

*For vanilla (official) Taskwarrior help, use: `thelp`, `tcmd`, or `tman <page>`*
