# Blocos de Tempo (Time Blocks)

## Overview

Blocos de Tempo organize your daily tasks by time of day, aligning with your energy levels and strategic daily structure. This system helps optimize productivity by matching tasks to appropriate time blocks.

---

## Time Block Values

### Manhã (Morning)

**Time:** Typically 6:00-10:00  
**Energy Level:** High (fresh, focused)  
**Duration:** 3-4 hours  
**Best For:** Strategic thinking, planning, high-priority work

```bash
# Create morning task
ta bloco_tempo:Manhã +execucao-diaria due:today "Morning meditation"

# View morning tasks
task bloco_tempo:Manhã due:today list
tbloco  # View all time blocks
```

**Typical Activities:**
- Meditation
- Strategic planning
- High-priority tasks
- Creative work
- Exercise

---

### Tarde (Afternoon)

**Time:** Typically 13:00-18:00  
**Energy Level:** Peak (maximum productivity)  
**Duration:** 4-5 hours  
**Best For:** Complex tasks, deep work, execution

```bash
# Create afternoon task
ta bloco_tempo:Tarde +execucao-diaria due:today "Write chapter 3"

# View afternoon tasks
task bloco_tempo:Tarde due:today list
```

**Typical Activities:**
- Deep work sessions
- Complex problem-solving
- Technical work
- Writing
- Development

---

### Noite (Evening)

**Time:** Typically 19:00-22:00  
**Energy Level:** Moderate (winding down)  
**Duration:** 1-2 hours  
**Best For:** Review, planning, light work

```bash
# Create evening task
ta bloco_tempo:Noite +execucao-diaria due:today "Evening review"

# View evening tasks
task bloco_tempo:Noite due:today list
```

**Typical Activities:**
- Daily review
- Planning for tomorrow
- Light reading
- Reflection
- Closing tasks

---

### Planejamento (Planning)

**Time:** Flexible (typically end of day or week)  
**Energy Level:** Reflective  
**Duration:** 30-60 minutes  
**Best For:** Strategic planning, goal setting, review

```bash
# Create planning task
ta bloco_tempo:Planejamento "Weekly planning session"

# View planning tasks
task bloco_tempo:Planejamento list
```

**Typical Activities:**
- Weekly planning
- Goal review
- Strategic alignment
- System optimization

---

### Revisão (Review)

**Time:** Flexible (typically end of cycle)  
**Energy Level:** Analytical  
**Duration:** 30-60 minutes  
**Best For:** Reviews, evaluations, corrections

```bash
# Create review task
ta bloco_tempo:Revisão +revisao meta_ciclo:1 "Meta cycle review"

# View review tasks
task bloco_tempo:Revisão list
```

**Typical Activities:**
- Cycle reviews
- Performance evaluation
- Route correction
- Barrier analysis

---

## Time Block Organization

### Daily Time Block View

```bash
# View all time blocks for today
task blocos
# or
tbloco

# Filter by specific time block
task bloco_tempo:Manhã due:today list
task bloco_tempo:Tarde due:today list
task bloco_tempo:Noite due:today list
```

### Time Block Report

**Report:** `blocos`  
**Filter:** `status:pending bloco_tempo: due:today`  
**Columns:** id, bloco_tempo, priority, description, due

```bash
task blocos
# or
tbloco
```

---

## Strategic Time Block Usage

### Energy Management

**Formula:**
```
Saúde = (0.5 × TaxaConclusão) + (0.3 × Qualidade) + (0.2 × Energia)
```

**Protocol:**
- Saúde < 3.0: Reduce workload by 20%
- Saúde 3.0-3.5: Maintain current load
- Saúde > 3.5: Consider gradual increase

### Time Block Allocation

| Block | Duration | Energy | Focus |
|-------|----------|--------|-------|
| **Manhã** | 3-4 hours | High | Strategic, planning |
| **Tarde** | 4-5 hours | Peak | Deep work, execution |
| **Noite** | 1-2 hours | Moderate | Review, planning |
| **Planejamento** | 30-60 min | Reflective | Strategic planning |
| **Revisão** | 30-60 min | Analytical | Reviews, evaluation |

---

## Time Block Patterns

### Daily Pattern

```bash
# Morning routine
tm              # Includes blocos view
task bloco_tempo:Manhã due:today list

# Afternoon work
task bloco_tempo:Tarde due:today list

# Evening routine
te              # Evening review
task bloco_tempo:Noite due:today list
```

### Weekly Pattern

```bash
# Monday: Planning
ta bloco_tempo:Planejamento "Weekly planning" due:monday

# Friday: Review
ta bloco_tempo:Revisão "Weekly review" due:friday
```

### Cycle Pattern

```bash
# Meta cycle review
ta bloco_tempo:Revisão +revisao meta_ciclo:1 "Meta review"
```

---

## Time Block + Hierarchy

### Combining Time Blocks with Hierarchy

```bash
# Morning activity for microcycle
ta tarefa_microciclo:1 bloco_tempo:Manhã +execucao-diaria "Morning work"

# Afternoon activity for meta
ta meta_ciclo:1 bloco_tempo:Tarde "Afternoon meta work"

# Evening review
ta bloco_tempo:Noite +revisao "Evening review"
```

---

## Time Block Best Practices

### 1. Match Tasks to Energy Levels

- **Manhã:** High-energy, strategic tasks
- **Tarde:** Peak-energy, complex tasks
- **Noite:** Moderate-energy, review tasks

### 2. Use Time Blocks Consistently

- Set `bloco_tempo` for all daily tasks
- Review time blocks in morning routine
- Adjust based on energy levels

### 3. Balance Time Blocks

- Don't overload any single block
- Distribute tasks across blocks
- Leave buffer time

### 4. Review and Adjust

- Monitor time block effectiveness
- Adjust based on performance
- Optimize for your energy patterns

---

## Time Block Filters

### Filtering by Time Block

```bash
# All morning tasks
task bloco_tempo:Manhã list

# Morning tasks due today
task bloco_tempo:Manhã due:today list

# Afternoon high priority
task bloco_tempo:Tarde priority:H list

# Evening review tasks
task bloco_tempo:Noite +revisao list
```

### Time Block + Status

```bash
# Active morning tasks
task bloco_tempo:Manhã +ACTIVE list

# Ready afternoon tasks
task bloco_tempo:Tarde +READY list
```

---

## Related Topics

- `th workflows` - Daily workflow with time blocks
- `th hierarchy` - Time blocks in hierarchy
- `th reports` - Blocos report
- `th filters` - Filtering by time blocks

---

*Time blocks are managed via `bloco_tempo` UDA. See `th udas` for UDA reference.*
