# Context System

## Overview

Contexts in Taskwarrior allow you to apply default filters to all commands. This enables quick switching between different work modes, hierarchy levels, and review types.

---

## Available Contexts

### work

**Filter:** `project:sonho:publicar-livro`  
**Purpose:** Focus on specific sonho work  
**Alias:** `tctxw`

```bash
task context work
# or
tctxw  # Alias
```

**Use Cases:**
- Focus on specific sonho
- Project-based work sessions
- Strategic work mode

---

### focus_today

**Filter:** `due:today`  
**Purpose:** Focus on today's tasks  
**Alias:** `tctxft`

```bash
task context focus_today
# or
tctxft  # Alias
```

**Use Cases:**
- Daily focus mode
- Today's priority tasks
- Immediate action items

---

### week

**Filter:** `due.after:today due.before:today+7d`  
**Purpose:** Focus on this week's tasks  
**Alias:** `tctxwk`

```bash
task context week
# or
tctxwk  # Alias
```

**Use Cases:**
- Weekly planning
- Week view
- Short-term focus

---

### review

**Filter:** `+relatorios or +revisao or +supervisao`  
**Purpose:** Focus on review tasks  
**Alias:** `tctxrev`

```bash
task context review
# or
tctxrev  # Alias
```

**Use Cases:**
- Review mode
- All review types
- Strategic evaluation

---

### ciclo

**Filter:** `meta_ciclo.any:`  
**Purpose:** Focus on meta cycles  
**Alias:** `tctxciclo`

```bash
task context ciclo
# or
tctxciclo  # Alias
```

**Use Cases:**
- Meta cycle focus
- 15-day cycle work
- Wave management

---

### onda

**Filter:** `onda_numero.any:`  
**Purpose:** Focus on waves (ondas)  
**Alias:** `tctxonda`

```bash
task context onda
# or
tctxonda  # Alias
```

**Use Cases:**
- Wave-based work
- Onda tracking
- Strategic waves

---

### teste_fogo

**Filter:** `+teste_fogo`  
**Purpose:** Focus on fire test tasks  
**Alias:** `tctxtf`

```bash
task context teste_fogo
# or
tctxtf  # Alias
```

**Use Cases:**
- 180-day evaluation
- Fire test mode
- Strategic coherence check

---

### none

**Purpose:** Clear context (no filter)  
**Alias:** `tctx0`

```bash
task context none
# or
tctx0  # Alias
```

**Use Cases:**
- Reset to default view
- Clear filters
- Full task view

---

## Context Management

### Set Context

```bash
# Set context
task context <name>
# or use aliases
tctxw      # Work context
tctxft     # Focus today
tctxwk     # Week context
tctxrev    # Review context
tctxciclo  # Ciclo context
tctxonda   # Onda context
tctxtf     # Teste fogo context
```

### List Contexts

```bash
# List all contexts
task context list
```

### Clear Context

```bash
# Clear context
task context none
# or
tctx0  # Alias
```

---

## Context Behavior

### Persistent Contexts

**Important:** Contexts persist across commands until explicitly changed or cleared.

```bash
# Set context
tctxw

# All subsequent commands use work context
task list      # Filtered by work context
task next      # Filtered by work context
task summary   # Filtered by work context

# Clear context
tctx0

# Commands now use no context filter
task list      # All tasks
```

### Context + Filters

You can combine contexts with additional filters:

```bash
# Set context
tctxw

# Add additional filter
task priority:H list  # Work context + high priority
task due:today list   # Work context + due today
```

---

## Strategic Context Usage

### Daily Workflow

```bash
# Morning: Focus on today
tctxft
task list      # Today's tasks
task next      # Most urgent today

# Clear for full view
tctx0
```

### Weekly Workflow

```bash
# Week view
tctxwk
task list      # This week's tasks
task summary   # Week summary

# Review mode
tctxrev
task list      # All review tasks
```

### Meta Cycle Workflow

```bash
# Meta cycle focus
tctxciclo
task list      # All meta cycle tasks
task meta      # Meta report

# Clear for other work
tctx0
```

### Strategic Workflow

```bash
# Work on specific sonho
tctxw
task list      # Sonho tasks
task summary   # Sonho summary

# Switch to review mode
tctxrev
task list      # Review tasks

# Clear for full view
tctx0
```

---

## Context Aliases Reference

| Alias | Context | Filter |
|-------|--------|--------|
| `tctxw` | work | `project:sonho:publicar-livro` |
| `tctxft` | focus_today | `due:today` |
| `tctxwk` | week | `due.after:today due.before:today+7d` |
| `tctxrev` | review | `+relatorios or +revisao or +supervisao` |
| `tctxciclo` | ciclo | `meta_ciclo.any:` |
| `tctxonda` | onda | `onda_numero.any:` |
| `tctxtf` | teste_fogo | `+teste_fogo` |
| `tctx0` | none | (no filter) |

---

## Best Practices

### Context Switching

1. **Set context at start of work session**
   ```bash
   tctxw  # Start work session
   ```

2. **Use context for focused work**
   ```bash
   tctxft  # Focus on today
   task list
   ```

3. **Clear context when done**
   ```bash
   tctx0  # Clear context
   ```

### Context + Workflows

- **Daily:** Use `tctxft` for today's focus
- **Weekly:** Use `tctxwk` for week view
- **Review:** Use `tctxrev` for review mode
- **Strategic:** Use `tctxw` for sonho work

---

## Related Topics

- `th workflows` - Workflow-specific contexts
- `th filters` - Filter syntax
- `th reports` - Context-aware reports

---

*Remember: Contexts persist until cleared. Use `tctx0` to reset.*
