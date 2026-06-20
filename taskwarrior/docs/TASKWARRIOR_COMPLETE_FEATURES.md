1# Taskwarrior Complete Features Guide

**Comprehensive coverage of ALL Taskwarrior features from [taskwarrior.org/docs](https://taskwarrior.org/docs/)**

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Basic Usage](#2-basic-usage)
3. [All Commands](#3-all-commands)
4. [Searching & Filtering](#4-searching--filtering)
5. [Reports](#5-reports)
6. [Priority System](#6-priority-system)
7. [Tags & Virtual Tags](#7-tags--virtual-tags)
8. [Date & Time](#8-date--time)
9. [Configuration](#9-configuration)
10. [Advanced Topics](#10-advanced-topics)
11. [Data Management](#11-data-management)
12. [Hooks API](#12-hooks-api)
13. [Integration](#13-integration)

---

## 1. Getting Started

### 1.1 Installation

Taskwarrior is installed via package manager or built from source.

**Check Installation:**
```bash
task --version
```

**Strategic Context:** Verify installation before starting your PAE + Hierarquia system setup.

---

### 1.2 Configuration File (.taskrc)

**Location:** `~/.taskrc` (or `%USERPROFILE%\.taskrc` on Windows)

**View Configuration:**
```bash
task config
task show
```

**Edit Configuration:**
```bash
task config <setting> <value>
# Or edit ~/.taskrc directly
```

**Strategic Context:** Configure UDAs, custom reports, and settings for your hierarchical system here.

---

### 1.3 Data Directory

**Location:** `~/.task/` (or `%USERPROFILE%\.task\` on Windows)

**Contents:**
- `pending.data` - Pending tasks
- `completed.data` - Completed tasks
- `undo.data` - Undo history
- `backlog.data` - Backlog tasks

**Backup:**
```bash
# Backup entire directory
cp -r ~/.task ~/.task.backup

# Or export to JSON
task export > backup.json
```

**Strategic Context:** Regular backups essential for preserving your Sonhos, Objetivos, Metas tracking.

---

### 1.4 First Task

**Create your first task:**
```bash
task add "My first task"
```

**View it:**
```bash
task list
task next
```

**Complete it:**
```bash
task 1 done
```

---

## 2. Basic Usage

### 2.1 Command Line Syntax

**General Format:**
```bash
task [filter] <command> [modifications]
```

**Examples:**
```bash
# Command only
task list

# Filter + command
task project:work list

# Command + modifications
task 1 modify priority:H

# Filter + command + modifications
task project:work modify +urgent
```

**Strategic Context:** Use filters to work with specific levels (Sonhos, Objetivos, Metas) or review types.

---

### 2.2 Best Practices

1. **Use Projects for Sonhos:**
   ```bash
   task add project:sonho:publicar-livro "Write chapter 1"
   ```

2. **Use Tags for Review Types:**
   ```bash
   task add +execucao-diaria "Daily task"
   task add +relatorios "Weekly report task"
   ```

3. **Use UDAs for Hierarchy:**
   ```bash
   task add sonho_id:publicar-livro objetivo_id:obj_001_Q1 "Task"
   ```

4. **Set Due Dates:**
   ```bash
   task add due:2025-12-15 "Task with deadline"
   ```

5. **Use Priorities:**
   ```bash
   task add priority:H "High priority"
   ```

**Strategic Context:** These practices align with your PAE + Hierarquia system structure.

---

### 2.3 Example Commands

**Daily Workflow:**
```bash
# Morning: See what's due today
task due:today list

# Add task for today
task add due:today "Review chapter 3"

# Work on task
task 5 start

# Complete task
task 5 done

# Evening: Plan tomorrow
task due:tomorrow list
```

**Strategic Context:** Maps to Rotina Inicial (morning) and Rotina Final (evening).

---

### 2.4 Example Workflows

**Weekly Review Workflow:**
```bash
# See completed this week
task completed end.after:today-7d

# See pending for next week
task due.after:today due.before:today+7d list

# Update priorities
task +relatorios modify priority:M
```

**Strategic Context:** Maps to #relatórios (weekly reports) in your system.

---

## 3. All Commands

### 3.1 Task Creation Commands

#### `add` - Add New Task

**Syntax:**
```bash
task add [modifications] <description>
```

**Examples:**
```bash
# Simple task
task add "Write blog post"

# With priority
task add priority:H "Urgent task"

# With due date
task add due:2025-12-15 "Task with deadline"

# With project
task add project:sonho:publicar-livro "Chapter 1"

# With tags
task add +execucao-diaria +obrigacoes "Daily task"

# With UDAs (custom attributes)
task add sonho_id:publicar-livro objetivo_id:obj_001_Q1 "Task"

# Complex example
task add project:sonho:publicar-livro sonho_id:publicar-livro objetivo_id:obj_001_Q1 meta_ciclo:1 bloco_tempo:Tarde +execucao-diaria priority:H due:today "Review chapter 3"
```

**Strategic Context:** Use for creating Atividades (daily) and Tarefas (5-day microcycle).

**Alias:** `ta`

---

#### `log` - Add Completed Task

**Syntax:**
```bash
task log [modifications] <description>
```

**Examples:**
```bash
# Log completed task
task log "Finished chapter 1" end:2025-12-03

# Log with metadata
task log project:sonho:publicar-livro "Completed review" end:2025-12-03
```

**Strategic Context:** Use to record tasks completed outside Taskwarrior (backfill history).

---

### 3.2 Task Viewing Commands

#### `list` - List Tasks

**Syntax:**
```bash
task [filter] list
```

**Examples:**
```bash
# All pending tasks
task list

# Filtered by project
task project:sonho:publicar-livro list

# Filtered by tag
task +execucao-diaria list

# Filtered by date
task due:today list
task due.after:today-7d list

# Complex filter
task project:sonho:publicar-livro +execucao-diaria priority:H due:today list
```

**Strategic Context:** Primary command for all review types (#narrativa, #relatórios, #revisão, #supervisão). ^tr-llmbr0pod

**Alias:** `tl`

---

#### `next` - Show Next Tasks

**Syntax:**
```bash
task [filter] next
```

**Description:** Shows tasks sorted by urgency (default Taskwarrior view).

**Examples:**
```bash
# Next tasks overall
task next

# Next tasks for project
task project:sonho:publicar-livro next

# Next high priority
task priority:H next
```

**Strategic Context:** Use in Rotina Inicial to see most urgent tasks.

**Alias:** `tn`

---

#### `all` - Show All Tasks

**Syntax:**
```bash
task [filter] all
```

**Description:** Shows all tasks (pending, completed, deleted, waiting, recurring).

**Examples:**
```bash
# All tasks
task all

# All for project
task project:sonho:publicar-livro all
```

**Strategic Context:** Use for comprehensive historical analysis.

**Alias:** `tall`

---

#### `completed` - Show Completed Tasks

**Syntax:**
```bash
task [filter] completed
```

**Examples:**
```bash
# All completed
task completed

# Completed this week
task completed end.after:today-7d

# Completed for project
task project:sonho:publicar-livro completed
```

**Strategic Context:** Use for calculating Taxa de Conclusão in reviews.

**Alias:** `tcompleted`

---

#### `waiting` - Show Waiting Tasks

**Syntax:**
```bash
task [filter] waiting
```

**Description:** Shows tasks blocked by dependencies.

**Examples:**
```bash
# All waiting tasks
task waiting

# Waiting for project
task project:sonho:publicar-livro waiting
```

**Strategic Context:** Identify blocked Tarefas in microcycles.

**Alias:** `tw`

---

#### `info` - Show Task Details

**Syntax:**
```bash
task <id> info
```

**Examples:**
```bash
# Full task details
task 5 info

# Shows: description, status, priority, due date, tags, UDAs, dependencies, annotations, etc.
```

**Strategic Context:** Review task details before completing or modifying.

**Alias:** `ti`

---

### 3.3 Task Modification Commands

#### `modify` - Modify Task

**Syntax:**
```bash
task <id> modify [modifications]
```

**Examples:**
```bash
# Change priority
task 5 modify priority:H

# Change due date
task 5 modify due:2025-12-20

# Add tag
task 5 modify +urgent

# Remove tag
task 5 modify -urgent

# Change project
task 5 modify project:sonho:publicar-livro

# Modify UDA
task 5 modify meta_ciclo:2

# Multiple changes
task 5 modify priority:H due:2025-12-20 +urgent
```

**Strategic Context:** Use to update tasks during Correção do Trajeto (route correction).

---

#### `annotate` - Add Annotation

**Syntax:**
```bash
task <id> annotate <note>
```

**Examples:**
```bash
# Add note
task 5 annotate "Blocked by external dependency"

# Add multiple notes
task 5 annotate "Progress: 50% complete"
task 5 annotate "Need to review with team"
```

**Strategic Context:** Use for Rotina Inicial/Final notes, insights, and barreiras (barriers).

---

#### `denotate` - Remove Annotation

**Syntax:**
```bash
task <id> denotate <annotation-number>
```

**Examples:**
```bash
# Remove first annotation
task 5 denotate 1
```

---

#### `start` - Start Task

**Syntax:**
```bash
task <id> start
```

**Description:** Marks task as active (started).

**Examples:**
```bash
# Start working on task
task 5 start

# See active tasks
task +ACTIVE list
```

**Strategic Context:** Use when beginning work in a Bloco de Tempo.

**Alias:** `tstart`

---

#### `stop` - Stop Task

**Syntax:**
```bash
task <id> stop
```

**Description:** Marks task as inactive (stopped).

**Examples:**
```bash
# Stop working on task
task 5 stop
```

**Strategic Context:** Use when switching Blocos de Tempo or pausing work.

**Alias:** `tstop`

---

#### `done` - Complete Task

**Syntax:**
```bash
task <id> [id2] [id3]... done
```

**Examples:**
```bash
# Complete single task
task 5 done

# Complete multiple tasks
task 5 6 7 done

# Complete with note
task 5 done "Completed successfully"
```

**Strategic Context:** Primary command for tracking completion in all review cycles.

**Alias:** `td`, `tc`

---

#### `delete` - Delete Task

**Syntax:**
```bash
task <id> delete
```

**Examples:**
```bash
# Delete task
task 5 delete

# Delete with confirmation (PowerShell alias)
tdel 5
```

**Strategic Context:** Use sparingly - prefer completing tasks to maintain history.

**Alias:** `tdel`

---

#### `duplicate` - Duplicate Task

**Syntax:**
```bash
task <id> duplicate [modifications]
```

**Examples:**
```bash
# Duplicate task
task 5 duplicate

# Duplicate with changes
task 5 duplicate due:tomorrow priority:H
```

**Strategic Context:** Use for recurring patterns in cycles or waves.

---

### 3.4 Information Commands

#### `summary` - Show Summary

**Syntax:**
```bash
task [filter] summary
```

**Description:** Shows summary statistics (pending, completed, deleted counts).

**Examples:**
```bash
# Overall summary
task summary

# Summary for project
task project:sonho:publicar-livro summary

# Summary for period
task modified.after:today-7d summary
```

**Strategic Context:** Quick overview for daily Rotina Final and weekly #relatórios.

**Alias:** `ts`

---

#### `stats` - Show Statistics

**Syntax:**
```bash
task [filter] stats
```

**Description:** Shows detailed statistics.

**Examples:**
```bash
# Overall stats
task stats

# Stats for period
task modified.after:today-30d stats
```

**Strategic Context:** Use for Eficiência Sistêmica calculations in monthly #supervisão. ^tr-9h7v5bm3t

**Alias:** `tst`

---

#### `projects` - List Projects

**Syntax:**
```bash
task projects
```

**Description:** Lists all projects with task counts.

**Examples:**
```bash
# All projects
task projects

# Filtered projects
task project:sonho:publicar-livro projects
```

**Strategic Context:** View all active Sonhos.

**Alias:** `tp`

---

#### `tags` - List Tags

**Syntax:**
```bash
task tags
```

**Description:** Lists all tags with task counts.

**Examples:**
```bash
# All tags
task tags
```

**Strategic Context:** View all review types and metadata tags.

**Alias:** `ttags`

---

#### `version` - Show Version

**Syntax:**
```bash
task --version
task version
```

**Examples:**
```bash
task --version
# Output: 2.6.2
```

**Alias:** `tv`

---

#### `help` - Show Help

**Syntax:**
```bash
task help
task help <command>
```

**Examples:**
```bash
# General help
task help

# Command help
task help add
task help list
task help modify
```

**Alias:** `th`

---

### 3.5 Data Management Commands

#### `export` - Export Tasks

**Syntax:**
```bash
task [filter] export [format]
```

**Examples:**
```bash
# Export all to JSON
task export

# Export filtered
task project:sonho:publicar-livro export

# Export to file
task export > backup.json

# Export specific format
task export json
task export yaml
```

**Strategic Context:** Use for backups and analysis scripts (Taxa de Conclusão, Eficiência, etc.).

**Alias:** `tex`

---

#### `import` - Import Tasks

**Syntax:**
```bash
task import [file]
```

**Examples:**
```bash
# Import from file
task import backup.json

# Import from stdin
cat backup.json | task import
```

**Strategic Context:** Restore backups or import from other systems.

**Alias:** `tim`

---

#### `sync` - Sync Tasks

**Syntax:**
```bash
task sync
task sync init
```

**Description:** Syncs tasks with Taskserver (if configured).

**Examples:**
```bash
# Sync with server
task sync

# Initialize sync
task sync init
```

**Strategic Context:** Sync across devices if using Taskserver.

**Alias:** `tsync`

---

#### `undo` - Undo Last Action

**Syntax:**
```bash
task undo
```

**Examples:**
```bash
# Undo last change
task undo

# Undo multiple times
task undo
task undo
```

**Strategic Context:** Recover from accidental changes.

**Alias:** `tundo`

---

### 3.6 Configuration Commands

#### `config` - Configure Settings

**Syntax:**
```bash
task config [setting] [value]
task show [setting]
```

**Examples:**
```bash
# Show all config
task config
task show

# Show specific setting
task config default.command
task show dateformat

# Set configuration
task config default.command next
task config dateformat Y-M-D
task config defaultwidth 120
```

**Strategic Context:** Configure UDAs, custom reports, and system settings.

**Alias:** `tconfig`

---

## 4. Searching & Filtering

### 4.1 Filter Syntax

**Basic Filters:**
```bash
# By status
task status:pending list
task status:completed list
task status:deleted list
task status:waiting list
task status:recurring list

# By project
task project:sonho:publicar-livro list
task project.not:sonho:publicar-livro list

# By tag
task +execucao-diaria list
task -execucao-diaria list
task +execucao-diaria +obrigacoes list

# By priority
task priority:H list
task priority.not:L list

# By due date
task due:today list
task due.before:2025-12-15 list
task due.after:today-7d list
task due.after:today-7d due.before:today+7d list
```

**Strategic Context:** Essential for filtering by hierarchy level, review type, or time period.

---

### 4.2 Date Filters

**Date Formats:**
```bash
# Absolute dates
task due:2025-12-15 list
task due:2025-12-15T10:00:00 list

# Relative dates
task due:today list
task due:tomorrow list
task due:yesterday list
task due:eow list      # End of week
task due:eom list      # End of month
task due:eoy list      # End of year

# Date ranges
task due.after:today-7d list
task due.before:today+7d list
task due.after:2025-12-01 due.before:2025-12-31 list

# Entry dates
task entry.after:today-7d list
task entry.before:today list

# Modification dates
task modified.after:today-7d list
task modified.before:today list

# Completion dates
task end.after:today-7d list
task end.before:today list
task completed end.after:today-7d
```

**Strategic Context:** Use for filtering by cycles (5 dias, 3 semanas, 3 meses) and review periods.

---

### 4.3 Text Search Filters

**Description Search:**
```bash
# Contains text
task "description~designio" list
task "description~portfólio" list

# Exact match
task "description:exact text" list

# Case insensitive
task "description~DESIGNIO" list
```

**Annotation Search:**
```bash
# Search annotations
task "annotation~blocked" list
```

**Strategic Context:** Find tasks across all hierarchy levels by keywords.

---

### 4.4 UDA Filters

**Custom Attribute Filters:**
```bash
# Filter by UDA
task sonho_id:publicar-livro list
task objetivo_id:obj_001_Q1 list
task meta_ciclo:1 list
task bloco_tempo:Tarde list

# UDA comparisons
task meta_ciclo.greater:1 list
task taxa_conclusao.less:80 list
```

**Strategic Context:** Primary way to filter by your hierarchical system levels.

---

### 4.5 Combined Filters

**Multiple Conditions:**
```bash
# AND (default)
task project:sonho:publicar-livro +execucao-diaria priority:H list

# OR
task "(project:sonho:publicar-livro OR project:sonho:melhorar-saude)" list

# NOT
task project.not:sonho:publicar-livro list
task -execucao-diaria list

# Complex
task "(project:sonho:publicar-livro OR project:sonho:melhorar-saude) +execucao-diaria priority:H due:today" list
```

**Strategic Context:** Build complex queries for specific review types and hierarchy levels.

---

### 4.6 Virtual Tags

**Built-in Virtual Tags:**
```bash
# Status-based
task +PENDING list
task +COMPLETED list
task +DELETED list
task +WAITING list
task +ACTIVE list

# Date-based
task +TODAY list
task +TOMORROW list
task +YESTERDAY list
task +WEEK list
task +MONTH list
task +YEAR list
task +OVERDUE list
task +DUETODAY list
task +DUETOMORROW list

# Priority-based
task +HIGH list
task +MEDIUM list
task +LOW list
task +NONE list

# Other
task +BLOCKED list
task +BLOCKING list
task +UNBLOCKED list
task +READY list
task +PARENT list
task +CHILD list
task +UNTIL list
task +ANNOTATED list
task +PRIORITY list
task +PROJECT list
task +TAGGED list
```

**Strategic Context:** Quick filters for common scenarios in daily workflows.

---

## 5. Reports

### 5.1 Built-in Reports

**Default Reports:**
```bash
task list          # Default report
task next          # Next tasks by urgency
task ls            # Short list
task minimal       # Minimal output
task newest        # Newest tasks
task oldest        # Oldest tasks
task active        # Active tasks
task waiting       # Waiting tasks
task completed     # Completed tasks
task all           # All tasks
task ready         # Ready tasks
task blocked       # Blocked tasks
task unblocked     # Unblocked tasks
task projects      # Projects
task tags          # Tags
task summary       # Summary
task stats         # Statistics
task calendar      # Calendar view
task ghistory      # Burndown chart
task ghburndown    # Burndown chart
task ghistory.annual # Annual history
task ghistory.monthly # Monthly history
```

**Strategic Context:** Use `list`, `next`, `summary`, `stats` most frequently in your workflows.

---

### 5.2 Custom Reports

**Define in .taskrc:**
```bash
# Custom report for Sonhos
report.sonho.description=Tarefas por Sonho
report.sonho.columns=id,active,sonho_id,description,due,priority
report.sonho.labels=ID,Act,Sonho,Descrição,Devido,Pri
report.sonho.sort=sonho_id+,due+
report.sonho.filter=status:pending

# Custom report for Objetivos
report.objetivo.description=Objetivos Trimestrais
report.objetivo.columns=id,objetivo_id,objetivo_trimestre,meta_ciclo,description,urgency
report.objetivo.labels=ID,Objetivo,Q,Ciclo,Descrição,Urgência
report.objetivo.sort=objetivo_trimestre+,due+
report.objetivo.filter=status:pending

# Custom report for Blocos de Tempo
report.blocos.description=Tarefas por Bloco de Tempo
report.blocos.columns=id,bloco_tempo,priority,description,due
report.blocos.labels=ID,Bloco,Pri,Descrição,Devido
report.blocos.sort=bloco_tempo+,priority-
report.blocos.filter=status:pending bloco_tempo:
```

**Use Custom Reports:**
```bash
task sonho
task objetivo
task blocos
```

**Strategic Context:** Create reports for each level of your hierarchy and review type.

---

### 5.3 Report Configuration

**Column Options:**
```bash
# Available columns
id, uuid, description, status, entry, start, end, due, until, wait, modified, scheduled, recur, mask, imask, parent, project, priority, depends, tags, uda.<name>

# Column modifiers
task list rc.report.list.columns=id,description.count,description.truncated
```

**Sort Options:**
```bash
# Sort by field
report.list.sort=due+,priority-,project+

# Sort modifiers
+ ascending, - descending
```

**Filter Options:**
```bash
# Filter in report
report.list.filter=status:pending
```

**Strategic Context:** Customize reports for your specific workflow needs.

---

## 6. Priority System

### 6.1 Priority Levels

**Priority Values:**
- `H` - High
- `M` - Medium  
- `L` - Low
- (none) - No priority

**Set Priority:**
```bash
task add priority:H "High priority task"
task 5 modify priority:M
```

**Filter by Priority:**
```bash
task priority:H list
task priority.not:L list
task +HIGH list
task +MEDIUM list
task +LOW list
```

**Strategic Context:** Map to your !critico, !urgente, !importante system.

---

### 6.2 Urgency Calculation

**Urgency Factors:**
- Priority (H=6, M=3, L=1, none=0)
- Due date proximity
- Age
- Tags
- Project
- Dependencies

**View Urgency:**
```bash
task next          # Sorted by urgency
task <id> info     # Shows urgency value
```

**Strategic Context:** Use `next` command to see most urgent tasks in Rotina Inicial.

---

## 7. Tags & Virtual Tags

### 7.1 Tag Management

**Add Tags:**
```bash
task add +execucao-diaria "Task"
task 5 modify +obrigacoes
task 5 modify +execucao-diaria +obrigacoes
```

**Remove Tags:**
```bash
task 5 modify -execucao-diaria
```

**List Tags:**
```bash
task tags
```

**Filter by Tags:**
```bash
task +execucao-diaria list
task -execucao-diaria list
task +execucao-diaria +obrigacoes list
task +execucao-diaria -obrigacoes list
```

**Strategic Context:** Use tags for review types (#narrativa, #relatórios, #revisão, #supervisão) and metadata. ^tr-bg3kvwy5g

---

### 7.2 Tag Naming Conventions

**Recommended Tags for Your System:**
```bash
# Review types
+execucao-diaria    # Daily execution
+relatorios         # Weekly reports
+revisao            # 15-day reviews
+supervisao         # Monthly supervision

# Task types
+obrigacoes         # Obligations
+tarefas            # Regular tasks
+narrativa          # Narrative/reflection

# Areas
+projeto_designio   # Designio project
+saude              # Health
+carreira           # Career
+estudos            # Studies

# Complexity
+simples            # Simple (1-2h)
+moderado           # Moderate (3-8h)
+complexo           # Complex (>8h)

# Urgency
+critico            # Critical (<24h)
+urgente            # Urgent (<72h)
+importante         # Important (this cycle)
```

**Strategic Context:** Consistent tagging enables powerful filtering and reporting.

---

### 7.3 Virtual Tags

**See [Section 4.6](#46-virtual-tags) for complete list.**

**Common Virtual Tags:**
```bash
+PENDING            # Pending tasks
+COMPLETED          # Completed tasks
+ACTIVE             # Active tasks
+WAITING            # Waiting tasks
+TODAY              # Due today
+TOMORROW           # Due tomorrow
+OVERDUE            # Overdue
+HIGH               # High priority
+BLOCKED            # Blocked by dependencies
+READY              # Ready to work on
```

**Strategic Context:** Quick filters for common daily workflow scenarios.

---

## 8. Date & Time

### 8.1 Date Formats

**Supported Formats:**
```bash
# ISO 8601
2025-12-15
2025-12-15T10:30:00
2025-12-15T10:30:00Z

# Relative
today
tomorrow
yesterday
eow        # End of week
eom        # End of month
eoy        # End of year
sow        # Start of week
som        # Start of month
soy        # Start of year

# Named dates (custom in .taskrc)
task config dateformat Y-M-D
```

**Examples:**
```bash
task add due:2025-12-15 "Task"
task add due:today "Task"
task add due:tomorrow "Task"
task add due:eow "Task"
```

**Strategic Context:** Use for setting due dates in all hierarchy levels.

---

### 8.2 Named Dates

**Define in .taskrc:**
```bash
# Custom named dates
dateformat Y-M-D
date.iso=yes

# Define custom dates
# (requires custom script or configuration)
```

**Use:**
```bash
task add due:today "Task"
task add due:tomorrow "Task"
```

---

### 8.3 Duration Values

**Duration Syntax:**
```bash
# Time durations
1s, 1m, 1h, 1d, 1w, 1mo, 1y

# Examples
task add wait:1d "Task waiting 1 day"
task add due:today+1w "Task due in 1 week"
```

**Strategic Context:** Use for scheduling tasks in cycles and waves.

---

### 8.4 Recurrence

**Recurring Tasks:**
```bash
# Daily
task add recur:daily "Daily task"

# Weekly
task add recur:weekly "Weekly task"

# Monthly
task add recur:monthly "Monthly task"

# Custom
task add recur:2w "Every 2 weeks"
task add recur:1mo "Every month"

# With due date
task add recur:weekly due:2025-12-15 "Weekly review"
```

**Strategic Context:** Use for recurring reviews (#relatórios weekly, #supervisão monthly). ^tr-xuuglkj26

---

### 8.5 Date Arithmetic

**Date Calculations:**
```bash
# Relative dates
today-7d           # 7 days ago
today+7d           # 7 days from now
today-1w           # 1 week ago
today+1mo          # 1 month from now

# Examples
task due.after:today-7d list
task due.before:today+7d list
task add due:today+15d "Task in 15 days"
```

**Strategic Context:** Essential for filtering by cycles (5 dias, 15 dias, 45 dias).

---

## 9. Configuration

### 9.1 .taskrc File

**Location:** `~/.taskrc`

**Structure:**
```bash
# Comments start with #

# UDAs
uda.sonho_id.label=Sonho ID
uda.sonho_id.type=string

# Reports
report.list.columns=id,description,due,priority
report.list.sort=due+,priority-

# Settings
default.command=next
dateformat=Y-M-D
defaultwidth=120
```

**Edit:**
```bash
# Via command
task config <setting> <value>

# Direct edit
nano ~/.taskrc
# or
notepad ~/.taskrc
```

**Strategic Context:** Configure all UDAs, custom reports, and system settings here.

---

### 9.2 Verbosity

**Verbosity Levels:**
```bash
# Set verbosity
task config verbosity=1    # Minimal
task config verbosity=2    # Default
task config verbosity=3    # Verbose
task config verbosity=4    # Debug

# Per-command
task --verbose list
task --quiet list
```

---

### 9.3 Color Themes

**Configure Colors:**
```bash
# Enable colors
task config color=on

# Custom colors (in .taskrc)
color.header=bold white on blue
color.footnote=white on blue
color.error=bold white on red
color.label=bold white
color.debug=white on magenta
```

**View Theme:**
```bash
task _show color
```

---

### 9.4 Terminology

**Customize Terms:**
```bash
# In .taskrc
# (Taskwarrior uses standard terms, but you can customize via reports)
```

**Strategic Context:** Use Portuguese terms in descriptions and UDAs to match your system.

---

## 10. Advanced Topics

### 10.1 Urgency

**Urgency Calculation:**
- Priority weight
- Due date proximity
- Age
- Tags
- Project
- Dependencies

**View Urgency:**
```bash
task next          # Sorted by urgency
task <id> info     # Shows urgency value
```

**Strategic Context:** Use to prioritize tasks in Rotina Inicial.

---

### 10.2 ID Numbers

**Task IDs:**
- Sequential numbers (1, 2, 3...)
- UUIDs (universal unique identifiers)
- Short UUIDs

**Use IDs:**
```bash
task 5 done
task 5 modify priority:H
task 5 info

# UUIDs
task <uuid> done
```

**Strategic Context:** IDs change, use projects/tags/UDAs for stable references.

---

### 10.3 Context

**Context System:**
```bash
# Define context
task context define work "project:work OR +work"

# Use context
task context work
task list          # Now filtered by work context

# Clear context
task context none

# List contexts
task context list
```

**Strategic Context:** Switch between different Sonhos or work modes quickly.

---

### 10.4 Recurrence Details

**Recurrence Patterns:**
```bash
# Simple
task add recur:daily "Daily task"
task add recur:weekly "Weekly task"
task add recur:monthly "Monthly task"

# Custom intervals
task add recur:2w "Every 2 weeks"
task add recur:1mo "Every month"

# With due date
task add recur:weekly due:2025-12-15 "Weekly review"

# Until date
task add recur:daily until:2025-12-31 "Daily until end of year"
```

**Strategic Context:** Use for recurring reviews and routine tasks.

---

### 10.5 User Defined Attributes (UDAs)

**Define UDAs in .taskrc:**
```bash
# String UDA
uda.sonho_id.label=Sonho ID
uda.sonho_id.type=string

# Numeric UDA
uda.meta_ciclo.label=Meta Ciclo
uda.meta_ciclo.type=numeric

# Date UDA
uda.onda_inicio.label=Onda Início
uda.onda_inicio.type=date

# Enum UDA
uda.bloco_tempo.label=Bloco Tempo
uda.bloco_tempo.type=string
uda.bloco_tempo.values=Manhã,Tarde,Noite,Planejamento,Revisão
```

**Use UDAs:**
```bash
# Set UDA
task add sonho_id:publicar-livro "Task"
task 5 modify meta_ciclo:1

# Filter by UDA
task sonho_id:publicar-livro list
task meta_ciclo:1 list
task bloco_tempo:Tarde list
```

**Strategic Context:** UDAs are essential for representing your 5-level hierarchy.

---

### 10.6 External Scripts

**Run Scripts:**
```bash
# Via hooks (see Hooks API section)
# Via shell integration
```

**Strategic Context:** Use scripts for metrics calculation, cycle management, and automation.

---

### 10.7 Escaping Command Line Characters

**Special Characters:**
```bash
# Quotes for spaces
task add "Task with spaces"

# Escape special characters
task add "Task with \"quotes\""

# Use single quotes in bash
task add 'Task with "quotes"'
```

---

## 11. Data Management

### 11.1 JSON Import/Export Format

**Export Format:**
```json
[
  {
    "uuid": "task-uuid",
    "description": "Task description",
    "entry": "2025-12-03T18:30:00Z",
    "status": "pending",
    "priority": "H",
    "due": "2025-12-15T00:00:00Z",
    "project": "sonho:publicar-livro",
    "tags": ["execucao-diaria", "obrigacoes"],
    "sonho_id": "publicar-livro",
    "objetivo_id": "obj_001_Q1",
    "meta_ciclo": 1,
    "bloco_tempo": "Tarde"
  }
]
```

**Export:**
```bash
task export > tasks.json
task project:sonho:publicar-livro export > livro-tasks.json
```

**Import:**
```bash
task import tasks.json
cat tasks.json | task import
```

**Strategic Context:** Use for backups, analysis scripts, and data migration.

---

### 11.2 DOM - Document Object Model

**DOM Access:**
```bash
# Via export
task export | jq '.[] | select(.project == "sonho:publicar-livro")'

# Via scripts
# (requires programming language integration)
```

**Strategic Context:** Use for complex analysis and metrics calculation.

---

### 11.3 Task Representation

**Internal Format:**
- Tasks stored in `pending.data`, `completed.data`
- JSON format internally
- Human-readable via commands

**View Raw:**
```bash
# Export shows internal representation
task export
```

---

### 11.4 Syncing Tasks

**Taskserver Sync:**
```bash
# Configure sync
task config taskd.server=your-server.com
task config taskd.credentials=your-credentials

# Sync
task sync
task sync init
```

**Strategic Context:** Sync across devices if using Taskserver.

---

## 12. Hooks API

### 12.1 Hooks v1 API

**Hook Locations:**
- `~/.task/hooks/` directory
- Executable scripts

**Hook Types:**
- `on-add` - When task is added
- `on-modify` - When task is modified
- `on-exit` - When command exits

**Example Hook:**
```bash
#!/bin/bash
# ~/.task/hooks/on-add
# Called when task is added

# Log to file
echo "$(date): Task added: $TASK_DESCRIPTION" >> ~/.task/hooks.log
```

**Strategic Context:** Use hooks for automation, metrics tracking, and notifications.

---

### 12.2 Hooks v2 API

**Enhanced Hooks:**
- More context
- Better error handling
- JSON input/output

**Example:**
```bash
#!/bin/bash
# ~/.task/hooks/on-add
# Receives JSON on stdin

# Process JSON
TASK_JSON=$(cat)
# Process and output modified JSON
echo "$TASK_JSON"
```

**Strategic Context:** Use for complex automation and data transformation.

---

### 12.3 Hook Author's Guide

**Best Practices:**
- Make hooks executable
- Handle errors gracefully
- Don't block user
- Use appropriate exit codes

**Strategic Context:** Create hooks for review reminders, metrics calculation, and cycle management.

---

## 13. Integration

### 13.1 3rd Party Application Guidelines

**Integration Methods:**
- JSON export/import
- Hooks API
- Command-line interface
- Taskserver sync

**Strategic Context:** Integrate with your analysis scripts for Taxa de Conclusão, Eficiência, etc.

---

### 13.2 Design Documents (RFCs)

**Reference:**
- Taskwarrior RFCs for design decisions
- API specifications
- Data format specifications

**Strategic Context:** Understand system limitations and capabilities for your customizations.

---

## Strategic System Integration Notes

### Mapping Your Hierarchy

**Sonhos (6-12 months):**
- Use `project` attribute
- Example: `project:sonho:publicar-livro`

**Objetivos (3 months):**
- Use UDA `objetivo_id` and `objetivo_trimestre`
- Example: `objetivo_id:obj_001_Q1 objetivo_trimestre:Q1`

**Metas (15 days):**
- Use UDA `meta_ciclo`
- Example: `meta_ciclo:1`

**Tarefas (5 days):**
- Use UDA `tarefa_microciclo`
- Example: `tarefa_microciclo:1`

**Atividades (daily):**
- Standard tasks with `bloco_tempo` UDA
- Example: `bloco_tempo:Manhã`

### Review Types

**#narrativa (Daily):**
- Tag: `+narrativa`
- Use: `task +narrativa list`

**#relatórios (Weekly):**
- Tag: `+relatorios`
- Use: `task +relatorios modified.after:today-7d list`

**#revisão (15-day):**
- Tag: `+revisao`
- Use: `task +revisao meta_ciclo:1 list`

**#supervisão (Monthly):**
- Tag: `+supervisao`
- Use: `task +supervisao modified.after:today-30d list` ^tr-cjpnvizfs

---

## Next Steps

- See [[TASKWARRIOR_STRATEGIC_WORKFLOWS]] for workflow integration
- See [[TASKWARRIOR_PITFALLS_AND_WORKAROUNDS]] for limitations and solutions
- See [[TASKWARRIOR_COMMAND_CHEATSHEET]] for quick command reference
- See [[TASKWARRIOR_ALIASES_REFERENCE]] for complete alias documentation
- See [[VANILLA_USAGE_GUIDE]] for learning path before advanced topics

---

## Related Guides

### Learning Path
- [[VANILLA_USAGE_GUIDE]] - Master vanilla Taskwarrior first (prerequisite)
- [[GETTING_STARTED]] - Basic usage guide
- [[START_HERE_TASKWARRIOR]] - Quick start

### Reference
- [[TASKWARRIOR_COMMAND_CHEATSHEET]] - Quick command lookup
- [[TASKWARRIOR_ALIASES_REFERENCE]] - Alias shortcuts
- [[taskwarrior-quick-reference]] - Visual quick reference

### Advanced
- [[TASKWARRIOR_STRATEGIC_WORKFLOWS]] - PAE + Hierarquia workflows
- [[TASKWARRIOR_PITFALLS_AND_WORKAROUNDS]] - Limitations & workarounds

---

*Complete Taskwarrior documentation: [taskwarrior.org/docs](https://taskwarrior.org/docs/)*

