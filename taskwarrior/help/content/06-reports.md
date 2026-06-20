# Custom Reports Reference

## Overview

Your Taskwarrior system includes **custom reports** tailored to your hierarchy levels and review workflows. These reports provide strategic views of your tasks aligned with your temporal cycles.

---

## Workflow Reports

### narrativa (Daily Review)

**Purpose:** Daily narrative review for morning routine  
**Tag:** `+narrativa`  
**Filter:** `+narrativa due:today`  
**Columns:** id, bloco_tempo, priority, description, due

```bash
task narrativa
# or
tm  # Morning routine (includes narrativa)
```

**Use Cases:**
- Morning routine review
- Daily planning
- Time block organization

---

### relatorios (Weekly Report)

**Purpose:** Weekly progress report  
**Tag:** `+relatorios`  
**Filter:** `+relatorios modified.after:today-7d`  
**Columns:** id, tarefa_microciclo, description, status, due

```bash
task relatorios
# or
twk  # Weekly review (includes relatorios)
```

**Use Cases:**
- Weekly progress review
- Microcycle tracking
- Weekly metrics calculation

---

### revisao (15-Day Review)

**Purpose:** Meta cycle review (quinzenal)  
**Tag:** `+revisao`  
**Filter:** `+revisao meta_ciclo:`  
**Requires:** `meta_ciclo` UDA  
**Columns:** id, meta_ciclo, description, status, due, barreira

```bash
task revisao
# or
tmeta  # View all metas
```

**Use Cases:**
- Meta cycle review (every 15 working days)
- Route correction
- Barrier identification

**Important:** Tasks with `+revisao` tag must have `meta_ciclo` UDA set.

---

### supervisao (Monthly Supervision)

**Purpose:** Monthly supervision and strategic alignment  
**Tag:** `+supervisao`  
**Filter:** `+supervisao modified.after:today-30d`  
**Columns:** id, sonho_id, objetivo_id, description, status

```bash
task supervisao
# or
task sonho  # View all sonhos
```

**Use Cases:**
- Monthly strategic review
- Sonho progress evaluation
- Quarterly objective alignment

---

## Hierarchy Reports

### sonho (Sonhos)

**Purpose:** View all tasks by Sonho  
**Filter:** `status:pending`  
**Columns:** id, active, sonho_id, description, due, priority

```bash
task sonho
# or
tsonho  # Alias
```

**Use Cases:**
- View all sonhos
- Strategic overview
- Long-term goal tracking

---

### objetivo (Objetivos)

**Purpose:** View quarterly objectives  
**Filter:** `status:pending`  
**Columns:** id, objetivo_id, objetivo_trimestre, meta_ciclo, description, urgency

```bash
task objetivo
# or
tobj  # Alias
```

**Use Cases:**
- Quarterly objective tracking
- Trimestre alignment
- Meta cycle overview

---

### meta (Metas)

**Purpose:** View 15-day meta cycles  
**Filter:** `status:pending meta_ciclo:`  
**Columns:** id, meta_ciclo, description, due, priority

```bash
task meta
# or
tmeta  # Alias
```

**Use Cases:**
- Meta cycle tracking
- 15-day cycle review
- Wave management

---

### tarefa (Tarefas)

**Purpose:** View 5-day microcycles  
**Filter:** `status:pending tarefa_microciclo:`  
**Columns:** id, tarefa_microciclo, description, due, priority

```bash
task tarefa
# or
tmicro  # Alias
```

**Use Cases:**
- Microcycle tracking
- 5-day task management
- Weekly planning

---

### blocos (Blocos de Tempo)

**Purpose:** View tasks by time blocks  
**Filter:** `status:pending bloco_tempo: due:today`  
**Columns:** id, bloco_tempo, priority, description, due

```bash
task blocos
# or
tbloco  # Alias
```

**Use Cases:**
- Time block organization
- Daily scheduling
- Energy management

**Time Blocks:**
- Manhã (Morning)
- Tarde (Afternoon)
- Noite (Evening)
- Planejamento (Planning)
- Revisão (Review)

---

## Status Reports

### ready (Ready Tasks)

**Purpose:** Tasks ready to work on  
**Filter:** `status:pending +READY`  
**Alias:** `tready`

```bash
task ready
# or
tready  # Alias
```

**Use Cases:**
- Find actionable tasks
- Next task selection
- Work queue management

---

### blocked (Blocked Tasks)

**Purpose:** Tasks blocked by dependencies  
**Filter:** `status:pending +BLOCKED`  
**Alias:** `tblocked`

```bash
task blocked
# or
tblocked  # Alias
```

**Use Cases:**
- Identify blockers
- Dependency management
- Unblocking workflow

---

### active (Active Tasks)

**Purpose:** Currently active (started) tasks  
**Filter:** `status:pending +ACTIVE`  
**Alias:** `tactive`

```bash
task active
# or
tactive  # Alias
```

**Use Cases:**
- Current work tracking
- Focus management
- Progress monitoring

---

### waiting (Waiting Tasks)

**Purpose:** Tasks in waiting status  
**Filter:** `status:waiting`  
**Alias:** `tw`

```bash
task waiting
# or
tw  # Alias
```

**Use Cases:**
- Deferred tasks
- Future work
- Scheduled tasks

---

### overdue (Overdue Tasks)

**Purpose:** Tasks past due date  
**Filter:** `status:pending +OVERDUE`  
**Alias:** `tlo`

```bash
task overdue
# or
tlo  # Alias
```

**Use Cases:**
- Overdue task management
- Urgency identification
- Deadline tracking

---

### teste_fogo (Teste de Fogo)

**Purpose:** 180-day fire test evaluation  
**Filter:** `status:pending +teste_fogo`  
**Columns:** id, teste_fogo_dimensao, description, status

```bash
task teste_fogo
```

**Use Cases:**
- 180-day evaluation
- Strategic coherence check
- System resilience test

**Dimensions:**
- Resiliência (Resilience)
- Coerência (Coherence)
- Eficiência (Efficiency)
- Adaptabilidade (Adaptability)

---

## Built-in Reports

### list (Default Report)

**Purpose:** Standard task list  
**Filter:** `status:pending`  
**Alias:** `tl`

```bash
task list
# or
tl  # Alias
```

---

### next (Next Tasks)

**Purpose:** Most urgent tasks  
**Filter:** `status:pending` (sorted by urgency)  
**Alias:** `tn`

```bash
task next
# or
tn  # Alias
```

---

### summary (Summary)

**Purpose:** Task summary statistics  
**Alias:** `ts`

```bash
task summary
# or
ts  # Alias
```

**Use Cases:**
- Quick overview
- Daily/weekly summaries
- Progress tracking

---

### stats (Statistics)

**Purpose:** Detailed statistics  
**Alias:** `tst`

```bash
task stats
# or
tst  # Alias
```

**Use Cases:**
- Detailed analysis
- Metrics calculation
- Performance tracking

---

## Report Usage Patterns

### Daily Workflow

```bash
# Morning
tm              # Includes narrativa, due:today, blocos
task narrativa  # Daily narrative
task blocos     # Time blocks

# Evening
te              # Completed today, plan tomorrow
ts              # Summary
```

### Weekly Workflow

```bash
# Weekly review
twk             # Includes relatorios + summary
task relatorios  # Weekly report
task modified.after:today-7d summary
```

### 15-Day Workflow

```bash
# Meta review
task revisao     # 15-day review
task meta        # All metas
task meta_ciclo:1 list  # Specific meta
```

### Monthly Workflow

```bash
# Monthly supervision
task supervisao  # Monthly report
task sonho       # All sonhos
task objetivo    # All objectives
```

---

## Customizing Reports

Reports are defined in `~/.taskrc`. To customize:

```bash
# View report configuration
task config report.narrativa

# Modify report filter
task config report.narrativa.filter '+narrativa due:today'

# Modify report columns
task config report.narrativa.columns 'id,bloco_tempo,priority,description,due'
```

---

## Related Topics

- `th workflows` - Workflow-specific reports
- `th hierarchy` - Hierarchy-level reports
- `th filters` - Report filtering

---

*For report configuration, see `~/.taskrc` or use `task config report.<name>`*
