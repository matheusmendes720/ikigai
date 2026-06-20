# Taskwarrior Command Cheatsheet

**Quick command reference organized by strategic workflow**

## Table of Contents

1. [By Hierarchical Level](#by-hierarchical-level)
2. [By Temporal Cycle](#by-temporal-cycle)
3. [By Review Type](#by-review-type)
4. [By Bloco de Tempo](#by-bloco-de-tempo)
5. [By PAE Component](#by-pae-component)
6. [By Metric](#by-metric)
7. [Complete Quick Reference](#7-complete-quick-reference)
8. [Tag Hierarchy Reference](#8-tag-hierarchy-reference)
7. [Complete Quick Reference](#complete-quick-reference)
8. [Tag Hierarchy Reference](#tag-hierarchy-reference)

---

## By Hierarchical Level

### Sonhos (6-12 months)

```bash
# View Sonhos
task projects

# View tasks for Sonho
task project:sonho:publicar-livro list
tlp sonho:publicar-livro

# Summary for Sonho
task project:sonho:publicar-livro summary

# Statistics for Sonho
task project:sonho:publicar-livro stats

# Monthly supervision
task project:sonho:publicar-livro modified.after:today-30d summary
```

---

### Objetivos (3 months)

```bash
# View Objetivos
task objetivo_id: list
task objetivo_trimestre:Q1 list

# Add Objetivo
task add project:sonho:publicar-livro objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 due:2025-03-31 "Objetivo"

# Quarterly review
task objetivo_trimestre:Q1 summary
task objetivo_trimestre:Q1 completed
```

---

### Metas (15 days)

```bash
# View Metas
task meta_ciclo:1 list
task meta_ciclo:1 +revisao list

# Add Meta
task add meta_ciclo:1 objetivo_id:obj_001_Q1 due:2025-12-18 +revisao "Meta"

# 15-day review
task meta_ciclo:1 completed end.after:today-15d
task meta_ciclo:1 summary
```

---

### Tarefas (5 days)

```bash
# View Tarefas
task tarefa_microciclo:1 list
task tarefa_microciclo:1 +relatorios list

# Add Tarefa
task add tarefa_microciclo:1 meta_ciclo:1 due:2025-12-08 +relatorios "Tarefa"

# Weekly report
task tarefa_microciclo:1 modified.after:today-7d summary
```

---

### Atividades (daily)

```bash
# View Atividades
task due:today +execucao-diaria list
task due:today +narrativa list

# Add Atividade
task add bloco_tempo:Manhã due:today +execucao-diaria "Atividade"

# Complete Atividade
task <id> done
td <id>
```

---

## By Temporal Cycle

### 5 Dias Úteis (Execução)

```bash
# Today's tasks
task due:today list
tld

# Tomorrow's tasks
task due:tomorrow list
tldt

# Morning review
tm

# Evening review
te

# Daily summary
task due:today summary
ts

# Completion tracking
task due:today completed
task due:today summary
```

---

### 3 Semanas (Análise)

```bash
# Weekly review
twk

# This week's tasks
task due.after:today due.before:today+7d list

# Completed this week
task completed end.after:today-7d

# Weekly summary
task modified.after:today-7d summary

# Weekly statistics
task modified.after:today-7d stats
```

---

### 3 Meses (Estratégia)

```bash
# Quarterly planning
task objetivo_trimestre:Q1 list

# Quarterly review
task objetivo_trimestre:Q1 summary
task objetivo_trimestre:Q1 completed

# Monthly review
task modified.after:today-30d summary
task modified.after:today-30d stats

# Export for analysis
task modified.after:today-90d export > quarter-tasks.json
```

---

## By Review Type

### Diário (#narrativa, #to-do)

```bash
# Daily narrative tasks
task +narrativa due:today list
task +execucao-diaria due:today list

# Morning routine
tm
task bloco_tempo:Manhã due:today list

# Evening routine
te
task due:tomorrow list

# Daily completion
task due:today summary
task completed end:today
```

---

### Semanal (#relatórios)

```bash
# Weekly report
twk
task +relatorios modified.after:today-7d list

# Weekly summary
task modified.after:today-7d summary

# Weekly statistics
task modified.after:today-7d stats

# Export for analysis
task modified.after:today-7d export > week-report.json
```

---

### Quinzenal (#revisão)

```bash
# 15-day review
task meta_ciclo:1 +revisao list
task meta_ciclo:1 completed end.after:today-15d

# Meta summary
task meta_ciclo:1 summary

# Correção do Trajeto
task meta_ciclo:1 +OVERDUE list
task meta_ciclo:1 "annotation~barreira" list
```

---

### Mensal (#supervisão) ^tr-a2b46ljt9

```bash
# Monthly supervision
task +supervisao modified.after:today-30d list
task project:sonho:publicar-livro modified.after:today-30d summary

# Monthly statistics
task modified.after:today-30d stats

# Export for analysis
task modified.after:today-30d export > month-report.json
```

---

## By Bloco de Tempo

### Manhã

```bash
# View Manhã tasks
task bloco_tempo:Manhã due:today list

# Add Manhã task
task add bloco_tempo:Manhã due:today +execucao-diaria "Task"

# Complete Manhã tasks
task bloco_tempo:Manhã due:today completed
```

---

### Tarde

```bash
# View Tarde tasks
task bloco_tempo:Tarde due:today list

# Add Tarde task
task add bloco_tempo:Tarde due:today +execucao-diaria "Task"

# Complete Tarde tasks
task bloco_tempo:Tarde due:today completed
```

---

### Noite

```bash
# View Noite tasks
task bloco_tempo:Noite due:today list

# Add Noite task
task add bloco_tempo:Noite due:today +execucao-diaria "Task"

# Complete Noite tasks
task bloco_tempo:Noite due:today completed
```

---

## By PAE Component

### Q1-Q4 Planning

```bash
# View by quarter
task objetivo_trimestre:Q1 list
task objetivo_trimestre:Q2 list
task objetivo_trimestre:Q3 list
task objetivo_trimestre:Q4 list

# Quarterly summary
task objetivo_trimestre:Q1 summary

# Quarterly review
task objetivo_trimestre:Q1 completed
```

---

### Metas Mensais

```bash
# Monthly goals
task +meta_mensal list
task +meta_mensal due.after:today-30d list

# Monthly review
task +meta_mensal modified.after:today-30d summary
```

---

### Checklists Semanais

```bash
# Weekly checklists
task +checklist_semanal list
task +checklist_semanal due.after:today-7d list

# Weekly checklist review
task +checklist_semanal modified.after:today-7d list
```

---

### Rotina Semanal

```bash
# Weekly routine
task +rotina_semanal due.after:today due.before:today+7d list

# Recurring weekly routine
task add recur:weekly due:2025-12-08 +rotina_semanal "Weekly task"
```

---

## By Metric

### Taxa de Conclusão

```bash
# Daily
task due:today summary
task due:today completed

# Weekly
task modified.after:today-7d summary
task completed end.after:today-7d
task modified.after:today-7d export > week-tasks.json

# Monthly
task modified.after:today-30d summary
task completed end.after:today-30d
task modified.after:today-30d export > month-tasks.json

# By level
task meta_ciclo:1 summary
task objetivo_id:obj_001_Q1 summary
task project:sonho:publicar-livro summary
```

---

### Eficiência Sistêmica

```bash
# Export for analysis
task modified.after:today-7d export > week-tasks.json
task completed end.after:today-7d export > week-completed.json

# Calculate (requires script)
python3 calculate-metrics.py week-tasks.json
```

---

### Coerência Estratégica

```bash
# Verify hierarchy connections
task sonho_id: objetivo_id: meta_ciclo: tarefa_microciclo: list

# Export for analysis
task export > all-tasks.json
# Analyze: count tasks with complete hierarchy
```

---

### Sustentabilidade

```bash
# Track energy/workload (via annotations)
task <id> annotate "Energia: 4/5"
task <id> annotate "Carga: 6h"

# Export for analysis
task modified.after:today-7d export > week-tasks.json
# Extract energy/workload from annotations
```

---

## Quick Command Patterns

### Common Patterns

```bash
# Add task with full hierarchy
task add project:sonho:publicar-livro sonho_id:publicar-livro objetivo_id:obj_001_Q1 meta_ciclo:1 tarefa_microciclo:1 bloco_tempo:Tarde due:today +execucao-diaria priority:H "Task"

# Filter by multiple criteria
task project:sonho:publicar-livro +execucao-diaria bloco_tempo:Manhã due:today priority:H list

# Review workflow
tm                    # Morning
task <id> start       # Work
task <id> done        # Complete
te                    # Evening

# Weekly workflow
twk                   # Weekly review
task +relatorios modified.after:today-7d list
task modified.after:today-7d export > week-report.json

# Monthly workflow
task +supervisao modified.after:today-30d list
task project:sonho:publicar-livro modified.after:today-30d summary
```

---

## Alias Quick Reference

| Alias | Command | Use Case |
|-------|---------|----------|
| `task` | Universal wrapper | Any command |
| `ta` | Add task | Create tasks |
| `tl` | List tasks | View tasks |
| `tn` | Next tasks | See urgent |
| `td` | Complete task | Mark done |
| `tm` | Morning review | Rotina Inicial |
| `te` | Evening review | Rotina Final |
| `twk` | Weekly review | #relatórios |
| `tstandup` | Daily standup | #narrativa |
| `ts` | Summary | Quick overview |
| `tst` | Stats | Statistics |
| `tex` | Export | Backup/analysis |
| `tim` | Import | Restore |
| `tld` | Due today | Today's tasks |
| `tldt` | Due tomorrow | Tomorrow's tasks |
| `tlh` | High priority | Urgent tasks |
| `tlo` | Overdue | Late tasks |
| `tlp` | By project | Sonhos |
| `tlt` | By tag | Review types |

---

## Filter Quick Reference

### By Status
```bash
task status:pending list
task status:completed list
task +PENDING list
task +COMPLETED list
```

### By Priority
```bash
task priority:H list
task priority:M list
task priority:L list
task +HIGH list
task +MEDIUM list
task +LOW list
```

### By Date
```bash
task due:today list
task due:tomorrow list
task due.after:today-7d list
task due.before:today+7d list
task +OVERDUE list
```

### By Project
```bash
task project:sonho:publicar-livro list
task project.not:sonho:publicar-livro list
```

### By Tag
```bash
task +execucao-diaria list
task +relatorios list
task +revisao list
task +supervisao list
task -execucao-diaria list
```

### By UDA
```bash
task sonho_id:publicar-livro list
task objetivo_id:obj_001_Q1 list
task meta_ciclo:1 list
task tarefa_microciclo:1 list
task bloco_tempo:Manhã list
```

### Combined Filters
```bash
task project:sonho:publicar-livro +execucao-diaria bloco_tempo:Manhã due:today priority:H list
task meta_ciclo:1 +revisao completed end.after:today-15d
task objetivo_trimestre:Q1 modified.after:today-30d summary
```

---

## Export & Analysis

```bash
# Export for analysis
task export > all-tasks.json
task project:sonho:publicar-livro export > sonho-tasks.json
task modified.after:today-7d export > week-tasks.json
task modified.after:today-30d export > month-tasks.json

# Calculate metrics (requires script)
python3 calculate-metrics.py week-tasks.json
python3 calculate-metrics.py month-tasks.json
```

---

## 7. Complete Quick Reference

> **📖 Full implementation details:**
> → See [[../taskwarrior-custom-integration#9-quick-reference-common-commands|Complete Quick Reference Guide]]

### 7.1 View by Your System

```bash
# Custom reports
task sonho                  # View tasks by Sonho (Dream)
task objetivo               # View tasks by Objetivo (Objective)
task blocos                 # View tasks organized by time blocks
task eficiencia             # View weekly efficiency metrics
task teste_fogo             # View Teste de Fogo evaluation tasks
```

### 7.2 Add Tasks with Your Structure

```bash
# Complete structure example
task add +projeto_designio sonho_id:publicar-livro \
  objetivo_trimestre:Q1 meta_ciclo:1 \
  bloco_tempo:Tarde priority:H "Task description"
```

### 7.3 Complete & Track

```bash
task 123 done                           # Mark task complete
task 123 modify taxa_conclusao:85.5    # Update completion rate
task 123 modify barreira:Recursos      # Log barrier encountered
```

### 7.4 Generate Reports (Automated Scripts)

```bash
task-eficiencia-semanal.py             # Weekly supervision report
correcao-trajeto.py                    # 15-day path correction
kaizen-diario.sh                       # Daily 1% improvement log
```

### 7.5 Sync & Export

```bash
task export > backup.json              # Backup all tasks
sync-to-markdown.py                    # Export to Markdown files
```

### 7.6 Emergency Commands

```bash
task due:today priority:H              # All high-priority today
task tags~critico                      # All critical tasks
task blocked.by:missing                # Tasks blocked by deleted deps
```

---

## 8. Tag Hierarchy Reference

> **📖 Complete tag system documentation:**
> → See [[../taskwarrior-custom-integration#32-tag-hierarchy-convention|Tag Hierarchy Guide]]

### Nível 1: Tipo de Registro

| Tag | Purpose |
|-----|---------|
| `+narrativa` | Narrativa diária |
| `+relatorios` | Relatório semanal |
| `+supervisao` | Supervisão quinzenal |
| `+revisao` | Revisão tática |

### Nível 2: Função

| Tag | Purpose |
|-----|---------|
| `+planejamento` | Planejamento estratégico |
| `+execucao-diaria` | Execução operacional |
| `+otimizacao` | Otimização de processo |

### Nível 3: Tempo

| Tag | Purpose |
|-----|---------|
| `+teste_fogo` | Marcador para Teste de Fogo |
| `+correcao_trajeto` | Correção após 15 dias |
| `+kaizen` | Melhoria contínua diária |

### Nível 4: Área/Projeto

| Tag | Purpose |
|-----|---------|
| `+projeto_designio` | Project Designio |
| `+projeto_carreira` | Career Project |
| `+saude` | Health |
| `+financas` | Finance |

### Usage Examples

```bash
# Daily narrative with execution
task add +narrativa +execucao-diaria +projeto_designio "Daily task"

# Weekly report with planning
task add +relatorios +planejamento +projeto_carreira "Weekly planning"

# Teste de Fogo evaluation
task add +teste_fogo +resiliencia +projeto_designio "Fire test task"
```

---

## Next Steps

- See [[TASKWARRIOR_ALIASES_REFERENCE]] for complete alias documentation
- See [[TASKWARRIOR_COMPLETE_FEATURES]] for complete feature reference
- See [[TASKWARRIOR_STRATEGIC_WORKFLOWS]] for workflow details
- See [[TASKWARRIOR_PITFALLS_AND_WORKAROUNDS]] for limitations and solutions

---

## Related Guides

### For Complete Feature Reference
- [[TASKWARRIOR_COMPLETE_FEATURES]] - **Complete feature reference** with all commands, options, and advanced topics
- [[TASKWARRIOR_COMPLETE_FEATURES#Hooks API]] - Automation hooks
- [[TASKWARRIOR_COMPLETE_FEATURES#Integration]] - Integration methods

### For Workflows
- [[TASKWARRIOR_STRATEGIC_WORKFLOWS]] - Strategic system workflows
- [[TASKWARRIOR_ALIASES_REFERENCE]] - Efficient alias usage

---

*Complete Taskwarrior documentation: [taskwarrior.org/docs](https://taskwarrior.org/docs/)*

