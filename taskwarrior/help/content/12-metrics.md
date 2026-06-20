# Metrics & Analysis

## Overview

Your Taskwarrior system includes metrics calculation tools to track completion rates, efficiency, and strategic alignment. These metrics align with your temporal cycles and review workflows.

---

## Key Metrics

### Taxa de Conclusão (Completion Rate)

**Purpose:** Track percentage of completed tasks  
**Formula:** `(Completed Tasks / Total Tasks) × 100`  
**Target:** 80%+ for daily, 70%+ for weekly

```bash
# Calculate completion rate
python3 taskwarrior/scripts/calculate-metrics.py backup.json

# For specific period
python3 taskwarrior/scripts/calculate-metrics.py backup.json --days 7
python3 taskwarrior/scripts/calculate-metrics.py backup.json --days 30
```

**Output:**
```
Tasks: total=50 completed=40 pending=8 waiting=2
Taxa de Conclusao: 80.0%
```

---

### Eficiência Sistêmica (System Efficiency)

**Purpose:** Measure result per hour invested  
**Formula:** `(Resultados Alcançados) / (Horas Investidas × Fator Qualidade)`  
**Where:** Fator Qualidade = 1 + (0.2 × notas de qualidade)

**Use Cases:**
- 15-day meta cycle evaluation
- Weekly efficiency tracking
- Performance optimization

---

### Coerência Estratégica (Strategic Coherence)

**Purpose:** Measure alignment between activities and sonhos  
**Scale:** 1-10  
**Use Cases:**
- Monthly supervision
- Quarterly evaluation
- Strategic alignment check

---

### Sustentabilidade (Sustainability)

**Purpose:** Measure system health and sustainability  
**Formula:** `Saúde = (0.5 × TaxaConclusão) + (0.3 × Qualidade) + (0.2 × Energia)`  
**Target:** 3.5+ (on scale of 5)

**Protocol:**
- Saúde < 3.0: Reduce workload by 20%
- Saúde 3.0-3.5: Maintain current load
- Saúde > 3.5: Consider gradual increase

---

## Metrics Calculation

### Using calculate-metrics.py

**Script:** `taskwarrior/scripts/calculate-metrics.py`

```bash
# Basic usage
python3 taskwarrior/scripts/calculate-metrics.py <export.json>

# With time filter
python3 taskwarrior/scripts/calculate-metrics.py <export.json> --days N
```

**Parameters:**
- `export.json`: Taskwarrior export file
- `--days N`: Filter by last N days (optional)

**Example:**
```bash
# Export tasks
task export > tasks.json

# Calculate overall metrics
python3 taskwarrior/scripts/calculate-metrics.py tasks.json

# Calculate weekly metrics
python3 taskwarrior/scripts/calculate-metrics.py tasks.json --days 7

# Calculate monthly metrics
python3 taskwarrior/scripts/calculate-metrics.py tasks.json --days 30
```

---

## Workflow Metrics

### Daily Metrics

**Script:** `taskwarrior/scripts/daily-review.sh`

```bash
# Run daily review
taskwarrior/scripts/daily-review.sh
```

**What it calculates:**
- Tasks due today
- Completed today
- Summary statistics
- Tomorrow's tasks

---

### Weekly Metrics

**Script:** `taskwarrior/scripts/weekly-review.sh`

```bash
# Run weekly review
taskwarrior/scripts/weekly-review.sh
```

**What it calculates:**
- Weekly report (relatorios)
- Modified tasks (last 7 days)
- Completed tasks (last 7 days)
- Exports to week-tasks.json

**Calculate weekly completion rate:**
```bash
# Export week data
task modified.after:today-7d export > week-tasks.json

# Calculate metrics
python3 taskwarrior/scripts/calculate-metrics.py week-tasks.json --days 7
```

---

### Monthly Metrics

**Calculate monthly completion rate:**
```bash
# Export month data
task modified.after:today-30d export > month-tasks.json

# Calculate metrics
python3 taskwarrior/scripts/calculate-metrics.py month-tasks.json --days 30
```

---

## Hierarchy-Level Metrics

### Sonho Metrics

```bash
# Export sonho tasks
task sonho_id:publicar-livro export > sonho-tasks.json

# Calculate sonho metrics
python3 taskwarrior/scripts/calculate-metrics.py sonho-tasks.json
```

### Objetivo Metrics

```bash
# Export objetivo tasks
task objetivo_id:obj_001_Q1 export > objetivo-tasks.json

# Calculate objetivo metrics
python3 taskwarrior/scripts/calculate-metrics.py objetivo-tasks.json
```

### Meta Cycle Metrics

```bash
# Export meta cycle tasks
task meta_ciclo:1 export > meta-tasks.json

# Calculate meta metrics
python3 taskwarrior/scripts/calculate-metrics.py meta-tasks.json
```

---

## Metrics Tracking

### Using UDAs for Metrics

**taxa_conclusao UDA:**
```bash
# Set completion rate
ta taxa_conclusao:85.50 "Task with completion rate"

# Filter by completion rate
task taxa_conclusao.greater:80 list
task taxa_conclusao.less:60 list
```

### Using Reports for Metrics

```bash
# Summary statistics
ts              # Quick summary
tst             # Detailed statistics

# Status reports
tready          # Ready tasks
tblocked        # Blocked tasks
tactive         # Active tasks
tw              # Waiting tasks
```

---

## Metrics Analysis Patterns

### Daily Analysis

```bash
# Morning: Review yesterday's metrics
task completed end:yesterday
ts

# Evening: Review today's metrics
task completed end:today
ts
```

### Weekly Analysis

```bash
# Weekly review
twk             # Includes summary
task modified.after:today-7d summary

# Calculate weekly completion rate
task modified.after:today-7d export > week-tasks.json
python3 taskwarrior/scripts/calculate-metrics.py week-tasks.json --days 7
```

### Monthly Analysis

```bash
# Monthly supervision
task supervisao
task modified.after:today-30d summary

# Calculate monthly completion rate
task modified.after:today-30d export > month-tasks.json
python3 taskwarrior/scripts/calculate-metrics.py month-tasks.json --days 30
```

---

## Metrics Best Practices

### 1. Regular Calculation

- Calculate daily metrics in evening routine
- Calculate weekly metrics in weekly review
- Calculate monthly metrics in monthly supervision

### 2. Track Trends

- Compare metrics across cycles
- Identify patterns and trends
- Adjust strategies based on metrics

### 3. Use Metrics for Improvement

- Set targets based on metrics
- Identify areas for improvement
- Optimize workflows based on data

### 4. Balance Metrics

- Don't optimize for single metric
- Consider multiple metrics together
- Balance completion rate with quality

---

## Related Topics

- `th workflows` - Workflow-specific metrics
- `th hierarchy` - Hierarchy-level metrics
- `th udas` - Metrics UDAs (taxa_conclusao)

---

*For metrics calculation scripts, see `taskwarrior/scripts/calculate-metrics.py`*
