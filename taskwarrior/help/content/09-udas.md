# User Defined Attributes (UDAs)

## Overview

User Defined Attributes (UDAs) extend Taskwarrior with custom fields tailored to your hierarchy system. Your setup includes 11 UDAs aligned with your 5-level hierarchy and strategic workflows.

---

## Hierarchy UDAs

### sonho_id

**Type:** string  
**Purpose:** Identify tasks belonging to a Sonho  
**Level:** Sonhos (6-12 months)

```bash
# Set sonho_id
ta sonho_id:publicar-livro "Task"

# Filter by sonho_id
task sonho_id:publicar-livro list
```

**Use Cases:**
- Link tasks to sonhos
- Filter by sonho
- Strategic alignment

---

### objetivo_id

**Type:** string  
**Purpose:** Identify tasks belonging to an Objetivo  
**Level:** Objetivos (3 months)  
**Format:** `obj_<number>_<quarter>` (e.g., `obj_001_Q1`)

```bash
# Set objetivo_id
ta objetivo_id:obj_001_Q1 "Task"

# Filter by objetivo_id
task objetivo_id:obj_001_Q1 list
```

**Use Cases:**
- Link tasks to objetivos
- Quarterly planning
- Objective tracking

---

### objetivo_trimestre

**Type:** string  
**Purpose:** Identify quarter for objetivo  
**Level:** Objetivos (3 months)  
**Values:** Q1, Q2, Q3, Q4

```bash
# Set objetivo_trimestre
ta objetivo_trimestre:Q1 "Task"

# Filter by quarter
task objetivo_trimestre:Q1 list
```

**Use Cases:**
- Quarterly organization
- Trimestre alignment
- Seasonal planning

---

### meta_ciclo

**Type:** numeric  
**Purpose:** Identify meta cycle (15-day cycle)  
**Level:** Metas (15 days)  
**Values:** 1, 2, 3, 4 (cycles per quarter)

```bash
# Set meta_ciclo
ta meta_ciclo:1 "Task"

# Filter by meta_ciclo
task meta_ciclo:1 list

# Required for +revisao tag
ta +revisao meta_ciclo:1 "Review task"
```

**Use Cases:**
- 15-day cycle tracking
- Meta cycle reviews
- Wave management

**Important:** Required when using `+revisao` tag (validated by on-add hook).

---

### tarefa_microciclo

**Type:** numeric  
**Purpose:** Identify microcycle (5-day cycle)  
**Level:** Tarefas (5 days)  
**Values:** 1, 2, 3 (microcycles per meta)

```bash
# Set tarefa_microciclo
ta tarefa_microciclo:1 "Task"

# Filter by tarefa_microciclo
task tarefa_microciclo:1 list
```

**Use Cases:**
- 5-day cycle tracking
- Microcycle management
- Weekly planning

---

### bloco_tempo

**Type:** string  
**Purpose:** Identify time block for daily tasks  
**Level:** Atividades (daily)  
**Values:** Manhã, Tarde, Noite, Planejamento, Revisão

```bash
# Set bloco_tempo
ta bloco_tempo:Manhã "Morning task"
ta bloco_tempo:Tarde "Afternoon task"
ta bloco_tempo:Noite "Evening task"

# Filter by bloco_tempo
task bloco_tempo:Manhã due:today list
```

**Use Cases:**
- Time block organization
- Daily scheduling
- Energy management

**Time Blocks:**
- **Manhã:** Morning (3-4 hours)
- **Tarde:** Afternoon (4-5 hours)
- **Noite:** Evening (1-2 hours)
- **Planejamento:** Planning time
- **Revisão:** Review time

---

## Strategic UDAs

### ciclo

**Type:** numeric  
**Purpose:** Identify strategic cycle (45-day cycle)  
**Level:** Strategic  
**Values:** 1, 2, 3, 4 (cycles per 180 days)

```bash
# Set ciclo
ta ciclo:1 "Strategic task"

# Filter by ciclo
task ciclo:1 list
```

**Use Cases:**
- 45-day cycle tracking
- Strategic cycle management
- Quarterly alignment

---

### onda_numero

**Type:** numeric  
**Purpose:** Identify wave number within cycle  
**Level:** Strategic  
**Values:** 1, 2, 3 (waves per cycle)

```bash
# Set onda_numero
ta onda_numero:1 "Wave task"

# Filter by onda_numero
task onda_numero:1 list
```

**Use Cases:**
- Wave tracking
- 3-week wave management
- Strategic waves

---

## Metrics UDAs

### taxa_conclusao

**Type:** numeric (precision: 2)  
**Purpose:** Track completion rate  
**Level:** Metrics  
**Format:** Percentage (0.00-100.00)

```bash
# Set taxa_conclusao
ta taxa_conclusao:85.50 "Task with completion rate"

# Filter by taxa_conclusao
task taxa_conclusao.greater:80 list
task taxa_conclusao.less:60 list
```

**Use Cases:**
- Completion rate tracking
- Performance metrics
- Progress monitoring

---

## Analysis UDAs

### barreira

**Type:** string  
**Purpose:** Identify barriers to completion  
**Level:** Analysis  
**Values:** Estrutural, Recurso, Habilidade, Motivacional

```bash
# Set barreira
ta barreira:Estrutural "Task with barrier"
ta barreira:Recurso "Resource barrier"
ta barreira:Habilidade "Skill barrier"
ta barreira:Motivacional "Motivation barrier"

# Filter by barreira
task barreira:Estrutural list
```

**Use Cases:**
- Barrier identification
- Problem analysis
- Route correction

**Barrier Types:**
- **Estrutural:** Structural/systemic barriers
- **Recurso:** Resource constraints
- **Habilidade:** Skill/knowledge gaps
- **Motivacional:** Motivation issues

---

### teste_fogo_dimensao

**Type:** string  
**Purpose:** Identify fire test dimension  
**Level:** Teste de Fogo (180 days)  
**Values:** Resiliência, Coerência, Eficiência, Adaptabilidade

```bash
# Set teste_fogo_dimensao
ta teste_fogo_dimensao:Resiliência "Resilience test"
ta teste_fogo_dimensao:Coerência "Coherence test"
ta teste_fogo_dimensao:Eficiência "Efficiency test"
ta teste_fogo_dimensao:Adaptabilidade "Adaptability test"

# Filter by teste_fogo_dimensao
task teste_fogo_dimensao:Resiliência list
```

**Use Cases:**
- 180-day fire test
- Strategic evaluation
- System resilience check

**Dimensions:**
- **Resiliência:** System resilience
- **Coerência:** Strategic coherence
- **Eficiência:** System efficiency
- **Adaptabilidade:** Adaptability

---

## UDA Usage Patterns

### Complete Hierarchy Example

```bash
# Sonho level
ta project:sonho:publicar-livro sonho_id:publicar-livro "Publish book"

# Objetivo level
ta objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 sonho_id:publicar-livro "Q1 objective"

# Meta level
ta meta_ciclo:1 objetivo_id:obj_001_Q1 +revisao "Meta cycle 1"

# Tarefa level
ta tarefa_microciclo:1 meta_ciclo:1 +execucao-diaria "Microcycle 1"

# Atividade level
ta tarefa_microciclo:1 bloco_tempo:Manhã +execucao-diaria due:today "Morning activity"
```

### Filtering by UDAs

```bash
# By sonho
task sonho_id:publicar-livro list

# By objetivo
task objetivo_id:obj_001_Q1 list

# By quarter
task objetivo_trimestre:Q1 list

# By meta cycle
task meta_ciclo:1 list

# By microcycle
task tarefa_microciclo:1 list

# By time block
task bloco_tempo:Manhã due:today list

# By ciclo
task ciclo:1 list

# By onda
task onda_numero:1 list
```

### UDA Comparisons

```bash
# Numeric comparisons
task meta_ciclo.greater:1 list
task meta_ciclo.less:3 list
task taxa_conclusao.greater:80 list

# Presence checks
task meta_ciclo.any: list      # Has meta_ciclo
task bloco_tempo.any: list      # Has bloco_tempo
task meta_ciclo.none: list      # No meta_ciclo
```

---

## UDA Reference Table

| UDA | Type | Level | Values | Purpose |
|-----|------|-------|--------|---------|
| `sonho_id` | string | Sonhos | any | Sonho identification |
| `objetivo_id` | string | Objetivos | obj_XXX_QX | Objetivo identification |
| `objetivo_trimestre` | string | Objetivos | Q1, Q2, Q3, Q4 | Quarter identification |
| `meta_ciclo` | numeric | Metas | 1-4 | Meta cycle (15 days) |
| `tarefa_microciclo` | numeric | Tarefas | 1-3 | Microcycle (5 days) |
| `bloco_tempo` | string | Atividades | Manhã, Tarde, Noite, Planejamento, Revisão | Time block |
| `ciclo` | numeric | Strategic | 1-4 | Strategic cycle (45 days) |
| `onda_numero` | numeric | Strategic | 1-3 | Wave number |
| `taxa_conclusao` | numeric | Metrics | 0.00-100.00 | Completion rate |
| `barreira` | string | Analysis | Estrutural, Recurso, Habilidade, Motivacional | Barrier type |
| `teste_fogo_dimensao` | string | Teste de Fogo | Resiliência, Coerência, Eficiência, Adaptabilidade | Fire test dimension |

---

## Related Topics

- `th hierarchy` - Hierarchy levels and UDAs
- `th filters` - Filtering by UDAs
- `th reports` - Reports using UDAs

---

*UDAs are defined in `~/.taskrc`. View with `task config uda.<name>`*
