# Taskwarrior Vanilla Usage Guide
## Understanding Vanilla Taskwarrior Before Customization

**Purpose:** Learn vanilla Taskwarrior thoroughly before adding customizations  
**Audience:** Developers setting up Taskwarrior for the first time  
**Prerequisites:** Taskwarrior installed (built from source or package manager)

---

## Table of Contents

1. [Core Concepts](#1-core-concepts)
2. [Data Structure](#2-data-structure)
3. [Essential Commands](#3-essential-commands)
4. [Common Workflows](#4-common-workflows)
5. [File Structure](#5-file-structure)
6. [Configuration Basics](#6-configuration-basics)
7. [Understanding Default Behavior](#7-understanding-default-behavior)
8. [Before Customizing](#8-before-customizing)

---

## 1. Core Concepts

### 1.1 What is Taskwarrior?

Taskwarrior is a **command-line task management tool** that:
- Stores tasks in a local database
- Uses plain text commands for all operations
- Supports projects, tags, priorities, due dates
- Extensible via User Defined Attributes (UDAs)
- Filterable and reportable via flexible queries

### 1.2 Key Principles

**Tasks are simple by default:**
- Every task has a description (required)
- Optional: project, tags, priority, due date, dependencies
- Tasks can be pending, completed, waiting, or deleted

**Everything is filterable:**
- List tasks by project: `task project:work list`
- List tasks by tag: `task +important list`
- List tasks by date: `task due:today list`
- Combine filters: `task project:work +important due:today list`

**Reports are customizable:**
- Default reports: `list`, `next`, `waiting`, `projects`, `summary`
- You can create custom reports (but understand defaults first)

---

## 2. Data Structure

### 2.1 Task Components

A vanilla Taskwarrior task contains:

```
Task ID:          Unique numeric identifier (auto-assigned)
UUID:             Globally unique identifier
Description:      Required text describing the task
Status:           pending | completed | waiting | deleted
Project:          Optional grouping (e.g., "work", "personal")
Tags:             Optional labels (e.g., +important, +home)
Priority:         L (Low) | M (Medium) | H (High)
Due Date:         Optional target completion date
Entry Date:       When task was created (automatic)
Modified Date:    When task was last changed (automatic)
Urgency:          Calculated score (automatic)
```

### 2.2 Example Task

```bash
$ task add "Write documentation" project:work priority:H due:tomorrow +important

$ task 1 info
Name          Value
ID            1
Description   Write documentation
Status        Pending
Project       work
Tags          important
Priority      H
Due           2025-12-04 00:00:00
Urgency       12.95
UUID          abc123...
Entered       2025-12-03 18:30:00 (1min)
```

### 2.3 Status Lifecycle

```
pending  →  (default state, active tasks)
   ↓
waiting  →  (blocked by dependencies)
   ↓
completed → (finished, archived)
   ↓
deleted   → (removed from system)
```

---

## 3. Essential Commands

### 3.1 Creating Tasks

**Basic task:**
```bash
task add "Buy groceries"
```

**With attributes:**
```bash
task add "Write report" project:work priority:H due:tomorrow +important
```

**Multiple tasks:**
```bash
task add "Task 1" "Task 2" "Task 3"
```

### 3.2 Listing Tasks

**Default list (pending tasks):**
```bash
task list
# or
task ls
```

**All tasks (including completed):**
```bash
task all
```

**Next tasks (sorted by urgency):**
```bash
task next
```

**Waiting tasks (blocked by dependencies):**
```bash
task waiting
```

### 3.3 Modifying Tasks

**Change description:**
```bash
task 1 modify "Updated description"
```

**Set priority:**
```bash
task 1 modify priority:H
```

**Set due date:**
```bash
task 1 modify due:tomorrow
task 1 modify due:2025-12-25
task 1 modify due:"next friday"
```

**Add/remove tags:**
```bash
task 1 modify +urgent
task 1 modify -important
```

**Set project:**
```bash
task 1 modify project:work
```

### 3.4 Completing Tasks

**Mark as done:**
```bash
task 1 done
# or
task 1 complete
```

**Undo completion:**
```bash
task 1 modify status:pending
```

### 3.5 Deleting Tasks

**Delete task:**
```bash
task 1 delete
```

**Note:** Deleted tasks are kept in the database but hidden from normal views.

---

## 4. Common Workflows

### 4.1 Daily Planning

**Morning routine:**
```bash
# Check what's due today
task due:today list

# Check high priority items
task priority:H list

# See urgent items
task next

# Start working on a task
task 5 start
```

**Evening routine:**
```bash
# Review completed tasks
task completed end.after:today-1d

# Plan tomorrow
task add "Tomorrow's task" due:tomorrow priority:M

# Review what's next
task next
```

### 4.2 Weekly Review

**Review completed work:**
```bash
# Tasks completed this week
task completed end.after:today-7d

# Summary of work
task summary
```

**Plan next week:**
```bash
# See what's coming
task due.after:today due.before:today+7d

# Check project status
task projects
```

### 4.3 Project Management

**Organize by project:**
```bash
# List all projects
task projects

# List tasks in a project
task project:work list

# Create project tasks
task add "Task 1" project:work
task add "Task 2" project:work
```

**Project statistics:**
```bash
task project:work summary
```

### 4.4 Tag Management

**Use tags for categorization:**
```bash
# Add tasks with tags
task add "Fix bug" +bug +urgent
task add "Write tests" +testing

# Filter by tags
task +bug list
task +urgent +important list

# Remove tag
task 1 modify -bug
```

---

## 5. File Structure

### 5.1 Configuration Files

**Main config file:**
```
~/.taskrc
```

This file contains:
- Report definitions
- Color settings
- Default values
- User Defined Attributes (when customized)

**Location can be changed:**
```bash
task config rc.data.location /custom/path
```

### 5.2 Data Files

**Default data directory:**
```
~/.local/share/task/
```

**Key files:**
```
pending.data    - Active tasks (pending, waiting)
completed.data  - Completed tasks
undo.data       - Undo history
```

**Data format:**
- Tasks stored in plain text format
- Human-readable (can edit manually if needed)
- One task per line (JSON-like format)

### 5.3 Backup

**Export tasks:**
```bash
task export > backup.json
```

**Import tasks:**
```bash
task import < backup.json
```

---

## 6. Configuration Basics

### 6.1 Viewing Configuration

**Show all settings:**
```bash
task config
```

**Show specific setting:**
```bash
task config default.command
```

**Show configuration file location:**
```bash
task config rc
```

### 6.2 Common Settings

**Set default command:**
```bash
task config default.command 'next'
```

**Set confirmation prompts:**
```bash
task config confirmation on
task config confirmation off
```

**Set date format:**
```bash
task config dateformat Y-M-D
```

**Enable/disable colors:**
```bash
task config color on
task config color off
```

### 6.3 Report Customization

**View report definition:**
```bash
task config report.list
```

**Modify report columns:**
```bash
task config report.list.columns 'id,project,description,due,priority'
task config report.list.labels 'ID,Project,Description,Due,Priority'
task config report.list.sort 'due+,priority-'
```

---

## 7. Understanding Default Behavior

### 7.1 Default Reports

**`task list`** - Shows pending tasks:
- Columns: ID, Age, Description, Urgency
- Sorted by: Project, then urgency
- Filter: `status:pending`

**`task next`** - Shows next tasks:
- Shows next 20 tasks by urgency
- Automatically filters out blocked tasks
- Sorted by urgency (highest first)

**`task waiting`** - Shows blocked tasks:
- Tasks with unmet dependencies
- Cannot be completed until dependencies are done

**`task projects`** - Shows project summary:
- Lists all projects
- Shows task counts per project

**`task summary`** - Shows statistics:
- Total tasks by status
- Tasks by project
- Tasks by tag

### 7.2 Urgency Calculation

Urgency is automatically calculated based on:
- Priority (H=6, M=3.9, L=1.95)
- Due date proximity (closer = higher)
- Age (older = slightly higher)
- Tags (some tags increase urgency)
- Project (some projects have base urgency)

**View urgency:**
```bash
task next  # Sorted by urgency
task _get 1.urgency  # Get specific task's urgency
```

### 7.3 Date Handling

**Relative dates:**
```bash
task add "Task" due:today
task add "Task" due:tomorrow
task add "Task" due:yesterday
task add "Task" due:"next friday"
task add "Task" due:"next month"
```

**Date ranges:**
```bash
task due.after:today list
task due.before:tomorrow list
task modified.after:today-7d list
```

**Date formats:**
- Default: YYYY-MM-DD (e.g., 2025-12-03)
- Configurable via `dateformat` setting

### 7.4 Filtering

**Filter operators:**
```bash
task project:work          # Exact match
task project.is:work       # Exact match (explicit)
task project.isnt:work     # Not equal
task priority.none:        # No priority set
task priority.any:         # Any priority
task +important            # Has tag
task -urgent               # Doesn't have tag
task description~bug       # Description contains "bug"
task urgency.above:10      # Urgency > 10
task due.after:today       # Due after today
```

**Combining filters:**
```bash
task project:work priority:H due:today list
task +important +urgent priority:H list
```

---

## 8. Before Customizing

### 8.1 Master These First

Before adding customizations, ensure you can:

✅ **Create tasks** with different attributes  
✅ **List and filter** tasks effectively  
✅ **Modify tasks** (priority, due dates, tags)  
✅ **Complete tasks** and review completed work  
✅ **Organize by projects** and tags  
✅ **Use date filters** and relative dates  
✅ **Understand urgency** calculation  
✅ **Export/import** tasks  

### 8.2 Practice Exercises

**Exercise 1: Basic Task Management**
```bash
# Create 5 tasks with different priorities
task add "High priority task" priority:H
task add "Medium priority task" priority:M
task add "Low priority task" priority:L
task add "Task with project" project:work
task add "Tagged task" +important

# List them
task list

# Modify one
task 1 modify due:tomorrow

# Complete one
task 2 done
```

**Exercise 2: Project Organization**
```bash
# Create tasks in different projects
task add "Work task 1" project:work
task add "Work task 2" project:work
task add "Home task 1" project:home

# List by project
task project:work list
task projects
```

**Exercise 3: Date Filtering**
```bash
# Create tasks with different due dates
task add "Due today" due:today
task add "Due tomorrow" due:tomorrow
task add "Due next week" due:"next week"

# Filter by date
task due:today list
task due.after:today list
```

**Exercise 4: Tags and Filtering**
```bash
# Create tasks with multiple tags
task add "Task 1" +important +urgent
task add "Task 2" +important
task add "Task 3" +urgent

# Filter by tags
task +important list
task +urgent +important list
task -important list  # Tasks without important tag
```

### 8.3 Understand the Defaults

**Know what works out of the box:**
- Projects (flat structure, no hierarchy)
- Tags (multiple per task, simple labels)
- Priority (L/M/H, affects urgency)
- Due dates (single date per task)
- Dependencies (one task depends on another)
- Status (pending, waiting, completed, deleted)

**Know what doesn't exist by default:**
- Custom attributes (need UDAs)
- Hierarchical projects (projects are flat)
- Complex date ranges (single due date only)
- Custom fields (need UDAs)
- Custom reports (need configuration)

### 8.4 When You're Ready to Customize

Once you're comfortable with vanilla Taskwarrior:

1. ✅ Review customization roadmap: `taskwarrior-customization-roadmap.md`
2. ✅ Understand UDA system (User Defined Attributes)
3. ✅ Learn report customization syntax
4. ✅ Plan your custom fields and reports
5. ✅ Test customizations incrementally

---

## Quick Reference

### Essential Commands
```bash
task add "Description"              # Create task
task list                           # List tasks
task next                           # Next tasks
task 1 done                         # Complete task
task 1 modify priority:H            # Modify task
task 1 delete                       # Delete task
task 1 info                         # Task details
task projects                       # List projects
task summary                        # Statistics
```

### Common Filters
```bash
task project:work list              # By project
task +important list                # By tag
task due:today list                 # By date
task priority:H list                # By priority
task status:completed list          # By status
```

### Useful Aliases
See `cli/win/task-aliases.sh` for shortcuts like:
- `ta` = task add
- `tl` = task list
- `td` = task done
- `tn` = task next

---

## Next Steps

1. **Run hello-world tests:** `./cli/win/hello-world-tasks.sh`
2. **Set up aliases:** `source cli/win/task-aliases.sh`
3. **Practice vanilla usage** for a few days
4. **Review customization roadmap:** [[../taskwarrior-customization-roadmap]]
5. **Plan your customizations** based on your needs

---

## Resources

### Official Documentation
- **Taskwarrior Docs:** https://taskwarrior.org/docs/
- **Taskwarrior Guide:** https://taskwarrior.org/docs/guide.html
- **Command Reference:** https://taskwarrior.org/docs/commands.html
- **Filtering Guide:** https://taskwarrior.org/docs/filter.html
- **Report Reference:** https://taskwarrior.org/docs/report.html

### Advanced Topics & Reference
- [[TASKWARRIOR_COMPLETE_FEATURES]] - **Complete feature reference** (Hooks API, Integration, Advanced Topics)
  - Comprehensive coverage of ALL Taskwarrior features
  - Advanced topics: Urgency, Context, Recurrence, UDAs
  - Hooks API for automation
  - Integration guidelines
  - Deep dive into all commands and options

### Next Steps
- [[TASKWARRIOR_STRATEGIC_WORKFLOWS]] - Implement your strategic system
- [[TASKWARRIOR_PITFALLS_AND_WORKAROUNDS]] - Understand limitations before customizing
- [[TASKWARRIOR_COMMAND_CHEATSHEET]] - Quick command reference

---

**Remember:** Master vanilla Taskwarrior first. Customizations build on this foundation!

