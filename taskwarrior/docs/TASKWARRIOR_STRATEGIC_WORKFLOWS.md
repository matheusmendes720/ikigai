# Taskwarrior Strategic Workflows

**Deep integration with PAE + Hierarquia de Objetivos system - Complete workflow guide**

## Table of Contents

1. [Hierarchical Mapping](#1-hierarchical-mapping)
2. [Temporal Workflows](#2-temporal-workflows)
3. [Review Workflows](#3-review-workflows)
4. [PAE Integration](#4-pae-integration)
5. [Estrutura Hierárquica Integration](#5-estrutura-hierárquica-integration)
6. [Metrics & Analysis](#6-metrics--analysis)

---

## 1. Hierarchical Mapping

### 1.1 Sonhos (6-12 months)

**Definition:** Resultados-alvo que representam mudanças significativas na sua vida.

**Taskwarrior Implementation:**
- Use `project` attribute for Sonhos
- Format: `project:sonho:<nome-do-sonho>`
- Add UDA `sonho_id` for tracking

**Commands:**

```bash
# Create Sonho (as project)
# Note: Sonhos are represented as projects, not tasks themselves

# Add task linked to Sonho
task add project:sonho:publicar-livro sonho_id:publicar-livro "Write chapter 1"

# View all tasks for a Sonho
task project:sonho:publicar-livro list

# View all Sonhos (projects)
task projects

# Summary for Sonho
task project:sonho:publicar-livro summary

# Statistics for Sonho
task project:sonho:publicar-livro stats
```

**Review Cycle:** Mensal (#supervisão) ^tr-ete49woga

**Example Workflow:**
```bash
# Monthly supervision of Sonho
task project:sonho:publicar-livro modified.after:today-30d summary
task project:sonho:publicar-livro completed end.after:today-30d
task project:sonho:publicar-livro +supervisao list
```

---

### 1.2 Objetivos (3 months/trimestre)

**Definition:** Metas intermediárias que detalham passos concretos para a realização de cada sonho.

**Taskwarrior Implementation:**
- Use UDAs: `objetivo_id` and `objetivo_trimestre`
- Link to Sonho via `project` and `sonho_id`
- Set due date for 3-month period

**Commands:**

```bash
# Add Objetivo (as task with UDAs)
task add project:sonho:publicar-livro sonho_id:publicar-livro objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 due:2025-03-31 "Complete first draft of book"

# View Objetivos for a Sonho
task project:sonho:publicar-livro +objetivo list
# Or filter by UDA
task objetivo_id:obj_001_Q1 list

# View Objetivos by trimestre
task objetivo_trimestre:Q1 list

# View all Objetivos
task objetivo_id: list

# Update Objetivo progress
task <id> modify objetivo_id:obj_001_Q1
task <id> annotate "Progress: 60% complete"
```

**Review Cycle:** Trimestral (at end of each quarter)

**Example Workflow:**
```bash
# Quarterly review of Objetivos
task objetivo_trimestre:Q1 summary
task objetivo_trimestre:Q1 completed
task objetivo_trimestre:Q1 +revisao list
```

---

### 1.3 Metas (15 days)

**Definition:** Divisão prática de objetivos em etapas semanais, permitindo análise da execução.

**Taskwarrior Implementation:**
- Use UDA: `meta_ciclo` (cycle number)
- Link to Objetivo via `objetivo_id`
- Set due date for 15-day period
- Tag with `+revisao` for review tracking

**Commands:**

```bash
# Add Meta (15-day goal)
task add project:sonho:publicar-livro sonho_id:publicar-livro objetivo_id:obj_001_Q1 meta_ciclo:1 due:2025-12-18 +revisao "Complete chapters 1-3"

# View Metas for current cycle
task meta_ciclo:1 list

# View Metas for Objetivo
task objetivo_id:obj_001_Q1 meta_ciclo: list

# View Metas due in next 15 days
task due.after:today due.before:today+15d +revisao list

# Update Meta
task <id> modify meta_ciclo:2
task <id> annotate "Barreira: Falta de tempo. Solução: Reorganizar prioridades"
```

**Review Cycle:** Quinzenal (#revisão) - every 15 days

**Example Workflow:**
```bash
# 15-day review (Quinzenal)
task meta_ciclo:1 +revisao list
task meta_ciclo:1 completed end.after:today-15d
task meta_ciclo:1 summary
```

---

### 1.4 Tarefas (5 days)

**Definition:** Microciclos de 5 dias úteis dentro de uma Meta.

**Taskwarrior Implementation:**
- Use UDA: `tarefa_microciclo` (microcycle number: 1, 2, or 3 per Meta)
- Link to Meta via `meta_ciclo`
- Set due date for 5-day period
- Tag with `+relatorios` for weekly tracking

**Commands:**

```bash
# Add Tarefa (5-day microcycle task)
task add project:sonho:publicar-livro sonho_id:publicar-livro objetivo_id:obj_001_Q1 meta_ciclo:1 tarefa_microciclo:1 due:2025-12-08 +relatorios "Write chapter 1 outline"

# View Tarefas for current microcycle
task tarefa_microciclo:1 list

# View Tarefas for Meta
task meta_ciclo:1 tarefa_microciclo: list

# View Tarefas due in next 5 days
task due.after:today due.before:today+5d +relatorios list

# Update Tarefa
task <id> modify tarefa_microciclo:2
```

**Review Cycle:** Semanal (#relatórios) - every week

**Example Workflow:**
```bash
# Weekly report (Semanal)
task tarefa_microciclo:1 +relatorios modified.after:today-7d list
task tarefa_microciclo:1 completed end.after:today-7d
task tarefa_microciclo:1 summary
```

---

### 1.5 Atividades (daily)

**Definition:** Registros operacionais do dia: turnos, checklists, insights e produtividade.

**Taskwarrior Implementation:**
- Standard tasks with `bloco_tempo` UDA
- Link to Tarefa via `tarefa_microciclo` and `meta_ciclo`
- Set due date for today or specific day
- Tag with `+execucao-diaria` and `+narrativa`

**Commands:**

```bash
# Add Atividade (daily activity)
task add project:sonho:publicar-livro sonho_id:publicar-livro objetivo_id:obj_001_Q1 meta_ciclo:1 tarefa_microciclo:1 bloco_tempo:Manhã due:today +execucao-diaria +narrativa priority:H "Review chapter 1 draft"

# View Atividades for today
task due:today +execucao-diaria list

# View Atividades by Bloco de Tempo
task bloco_tempo:Manhã due:today list
task bloco_tempo:Tarde due:today list
task bloco_tempo:Noite due:today list

# View Atividades for current Tarefa
task tarefa_microciclo:1 +execucao-diaria list

# Complete Atividade
task <id> done
task <id> annotate "Concluído com sucesso. Taxa: 100%"
```

**Review Cycle:** Diário (#narrativa) - every day

**Example Workflow:**
```bash
# Daily narrative (Diário)
task due:today +narrativa list
task due:today +execucao-diaria completed
task due:today summary
```

---

## 2. Temporal Workflows

### 2.1 5 Dias Úteis (Execução)

**Definition:** Ciclo de 5 dias úteis - padrão: 3 dias execução + 1 dia ajuste + 1 dia planejamento.

**Métrica-chave:** Taxa de conclusão diária (alvo: 80%+)

**Daily Workflow:**

#### Rotina Inicial (Morning Routine)

**4 Questions:**
1. 🔁 O que é que eu fiz ontem que devo repetir?
2. 🚫 O que é que eu fiz ontem que preciso de deixar de fazer?
3. 🔄 Que tarefa de ontem deve tornar-se um hábito?
4. 🏆 Qual é a grande vitória de hoje?

**Commands:**

```bash
# Morning review - see what's due today
tm                    # Morning review alias (shows: due today, high priority, next tasks)
# Or manually:
task due:today list
task priority:H list
task next

# View yesterday's completed tasks (for reflection)
task completed end:yesterday list

# View tasks for today by Bloco de Tempo
task bloco_tempo:Manhã due:today list
task bloco_tempo:Tarde due:today list

# Start working on a task
task <id> start
```

**Strategic Context:** Use `tm` or `task due:today list` to see today's Atividades organized by Blocos de Tempo.

---

#### Blocos de Tempo (Time Blocks)

> **📖 For complete daily workflow implementation examples:**
> → See [[../taskwarrior-custom-integration#71-daily-workflow-with-taskwarrior|Daily Workflow Guide]]

**Manhã (Morning - 3-4 hours):**
- Treino físico, meditação, planejamento estratégico

**Commands:**

```bash
# Check today's priorities in Manhã block
task blocos filter 'bloco_tempo:Manhã and due:today'

# Add morning meditation/planning task
task add +projeto_designio +planejamento bloco_tempo:Manhã \
  priority:M due:today "Meditação e Planejamento Estratégico"

# View all Manhã tasks
task blocos

# View Manhã tasks (alternative)
task bloco_tempo:Manhã due:today list

# Add Manhã task
task add bloco_tempo:Manhã due:today +execucao-diaria "Treino em jejum"
task add bloco_tempo:Manhã due:today +execucao-diaria "Meditação"
task add bloco_tempo:Manhã due:today +execucao-diaria priority:H "Planejamento estratégico"

# Work on Manhã tasks
task bloco_tempo:Manhã due:today +ACTIVE list
task <id> start
task <id> done
```

**Tarde (Afternoon - 4-5 hours):**
- Execução de tarefas técnicas complexas

**Commands:**

```bash
# Check complex technical tasks for afternoon
task blocos filter 'bloco_tempo:Tarde and due:today and priority:H'

# Add afternoon execution task
task add +projeto_designio +execucao-diaria bloco_tempo:Tarde \
  priority:H due:today "Desenvolver módulo X"

# View Tarde tasks
task bloco_tempo:Tarde due:today list

# Add Tarde task
task add bloco_tempo:Tarde due:today +execucao-diaria priority:H "Desenvolvimento do sistema"

# Work on Tarde tasks
task bloco_tempo:Tarde due:today +ACTIVE list

# Mark task as complete when done
task <id> done
```

**Noite (Evening - 1-2 hours):**
- Revisão do dia, planejamento seguinte

**Commands:**

```bash
# Generate daily narrative (hook runs automatically)
# Or manually trigger:
task narrativa

# Plan for tomorrow
task add +planejamento bloco_tempo:Revisão priority:M \
  due:tomorrow "Planejar dia de amanhã"

# View Noite tasks
task bloco_tempo:Noite due:today list

# Add Noite task
task add bloco_tempo:Noite due:today +execucao-diaria "Arremate do dia"
task add bloco_tempo:Noite due:today +execucao-diaria "Planejamento para amanhã"
```

---

#### Rotina Final (Evening Routine)

**3 Questions:**
1. ✅ O que é que eu fiz hoje que correu bem?
2. ❌ O que é que eu fiz hoje que correu mal?
3. 📚 Qual foi o maior aprendizado do dia?

**Commands:**

```bash
# Evening review - see what's next for tomorrow
te                    # Evening review alias (shows: tomorrow's tasks, next tasks)
# Or manually:
task due:tomorrow list
task next

# Review today's completed tasks
task completed end:today list

# Calculate Taxa de Conclusão for today
task due:today summary
# Compare: completed vs pending for today

# Plan tomorrow
task add bloco_tempo:Manhã due:tomorrow +execucao-diaria "Task for tomorrow morning"
```

**Strategic Context:** Use `te` or `task due:tomorrow list` to plan tomorrow's Blocos de Tempo.

---

#### Taxa de Conclusão Diária (Daily Completion Rate)

**Target:** 80%+

**Calculation:**
```bash
# View today's tasks
task due:today list
task due:today summary

# Export for analysis
task due:today export > today-tasks.json

# Manual calculation:
# Taxa = (Completed today) / (Total due today) × 100
```

**Alert System:** If <60% for 2 consecutive days, trigger review

**Commands:**

```bash
# Check completion rate for last 2 days
task due.after:today-2d due.before:today list
task completed end.after:today-2d

# If <60%, review
task due.after:today-2d +OVERDUE list
task due.after:today-2d summary
```

---

### 2.2 3 Semanas (Análise)

**Definition:** Ciclo de 3 semanas (15 dias úteis) - estrutura: 2 semanas execução + 1 semana otimização.

**Métrica-chave:** Eficiência sistêmica (resultado/hora)

**Weekly Workflow:**

#### Supervisão Semanal (Weekly Supervision)

**Commands:**

```bash
# Weekly review
twk                   # Weekly review alias (shows: this week's tasks, completed this week)
# Or manually:
task due.after:today-7d list
task completed end.after:today-7d

# Weekly summary
task modified.after:today-7d summary
task modified.after:today-7d stats

# Tasks for current week
task due.after:today due.before:today+7d list

# Weekly report by project/Sonho
task project:sonho:publicar-livro modified.after:today-7d summary
```

**Strategic Context:** Use for #relatórios (weekly reports) to track progress on Tarefas.

---

#### Relatórios de Eficiência (Efficiency Reports)

**Eficiência Sistêmica Formula:**
```
Eficiência = (Resultados Alcançados) / (Horas Investidas × Fator Qualidade)
Onde Fator Qualidade = 1 + (0.2 × notas de qualidade)
```

**Commands:**

```bash
# Export tasks for analysis
task modified.after:today-7d export > week-tasks.json

# View completed tasks with metadata
task completed end.after:today-7d list
task completed end.after:today-7d export > week-completed.json

# Calculate efficiency (requires external script)
# Use exported JSON to calculate: results / (hours × quality_factor)
```

**Strategic Context:** Export data and use scripts to calculate Eficiência Sistêmica.

---

#### Correção do Trajeto (Route Correction)

**After each 15-day cycle (Onda):**

**Commands:**

```bash
# Review completed Metas
task meta_ciclo:1 completed end.after:today-15d

# Review pending Metas
task meta_ciclo:1 +revisao list

# Identify barreiras (barriers)
task meta_ciclo:1 "annotation~barreira" list

# Summary for cycle
task meta_ciclo:1 summary

# Plan next cycle
task add meta_ciclo:2 +revisao "Next 15-day goal"
```

**Strategic Context:** Use after each Onda (3-week wave) to adjust course.

---

### 2.3 3 Meses (Estratégia)

**Definition:** Ciclo trimestral - estrutura: 2 trimestres execução + 1 trimestre realinhamento.

**Métrica-chave:** Alinhamento estratégico (escala 1-10)

**Quarterly Workflow:**

#### Planejamento Trimestral (Quarterly Planning)

**Commands:**

```bash
# View Objetivos for quarter
task objetivo_trimestre:Q1 list

# Create Objetivos for new quarter
task add project:sonho:publicar-livro sonho_id:publicar-livro objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 due:2025-03-31 "Objetivo Q1"

# Plan Metas for quarter (15-day cycles)
task add objetivo_id:obj_001_Q1 meta_ciclo:1 due:2025-01-15 +revisao "Meta 1"
task add objetivo_id:obj_001_Q1 meta_ciclo:2 due:2025-01-30 +revisao "Meta 2"
# ... continue for all cycles in quarter
```

**Strategic Context:** Set up Objetivos and Metas at start of each quarter (Q1, Q2, Q3, Q4).

---

#### Avaliação Trimestral (Quarterly Evaluation)

**Commands:**

```bash
# Summary for quarter
task objetivo_trimestre:Q1 summary
task objetivo_trimestre:Q1 stats

# Completed Objetivos
task objetivo_trimestre:Q1 completed

# All tasks for quarter
task objetivo_trimestre:Q1 all

# Export for analysis
task objetivo_trimestre:Q1 export > q1-tasks.json
```

**Strategic Context:** Evaluate progress at end of each quarter.

---

#### Realinhamento Estratégico (Strategic Realignment)

**Commands:**

```bash
# Review all Sonhos
task projects

# Review progress on each Sonho
task project:sonho:publicar-livro summary
task project:sonho:publicar-livro completed end.after:today-90d

# Identify what needs adjustment
task project:sonho:publicar-livro +OVERDUE list
task project:sonho:publicar-livro "annotation~barreira" list

# Adjust Objetivos for next quarter
task objetivo_id:obj_001_Q1 modify objetivo_trimestre:Q2
# Or create new Objetivos
task add objetivo_id:obj_002_Q2 objetivo_trimestre:Q2 "Adjusted Objetivo"
```

**Strategic Context:** Realign strategy based on quarterly evaluation.

---

## 3. Review Workflows

### 3.1 Diário (#narrativa, #to-do)

**Frequency:** Daily

**Purpose:** Registros operacionais do dia: turnos, checklists, insights e produtividade.

**Workflow:**

**Morning (Rotina Inicial):**
```bash
# See today's tasks
tm                    # Morning review
# Or:
task due:today list
task bloco_tempo:Manhã due:today list

# Start day
task <id> start
```

**During Day:**
```bash
# Work on tasks
task +ACTIVE list
task <id> done

# Add insights as annotations
task <id> annotate "Insight: This approach worked well"
task <id> annotate "Barreira: Falta de tempo. Solução: Reorganizar"
```

**Evening (Rotina Final):**
```bash
# Review day
te                    # Evening review
# Or:
task completed end:today list
task due:today summary

# Answer 3 questions (record as annotations or separate notes)
# 1. ✅ O que correu bem?
# 2. ❌ O que correu mal?
# 3. 📚 Maior aprendizado?

# Plan tomorrow
task due:tomorrow list
task add bloco_tempo:Manhã due:tomorrow +execucao-diaria "Tomorrow's task"
```

**Commands Summary:**
```bash
# Daily narrative tasks
task +narrativa due:today list
task +execucao-diaria due:today list

# Daily completion tracking
task due:today summary
task completed end:today
```

---

### 3.2 Semanal (#relatórios)

**Frequency:** Weekly

**Purpose:** Consolida checklists e insights diários.

> **📖 For automated weekly supervision scripts:**
> → See [[../taskwarrior-custom-integration#72-weekly-supervision-supervisão-semanal|Weekly Supervision Guide]]
> → See [[../taskwarrior-custom-integration#53-python-script-weekly-efficiency-report|Weekly Efficiency Report Script]]

**Workflow:**

```bash
# View efficiency report for this week (automated script)
task-eficiencia-semanal.py

# Check barriers encountered
task eficiencia | grep barreira

# Weekly report (manual)
twk                   # Weekly review alias
# Or:
task modified.after:today-7d summary
task completed end.after:today-7d

# Weekly tasks
task +relatorios modified.after:today-7d list

# Calculate Taxa de Conclusão for week
task modified.after:today-7d export > week-report.json
# Analyze: completed vs pending

# Review Tarefas (5-day microcycles)
task tarefa_microciclo: +relatorios modified.after:today-7d list

# Plan next week's adjustments
task add sonho_id:publicar-livro objetivo_trimestre:Q1 \
  meta_ciclo:1 +supervisao +revisao priority:H \
  "Revisar e ajustar estratégia da semana"

# Weekly insights
task modified.after:today-7d "annotation~aprendizado" list
task modified.after:today-7d "annotation~barreira" list
```

**Commands Summary:**
```bash
# Weekly report generation
task +relatorios modified.after:today-7d list
task modified.after:today-7d summary
task completed end.after:today-7d

# Export for analysis
task modified.after:today-7d export > week-report.json
```

---

### 3.3 Quinzenal (#revisão)

**Frequency:** Every 15 days (end of each Onda)

**Purpose:** Analisa a eficácia dos objetivos (Metas).

> **📖 For quinzenal review commands and Correção de Trajeto automation:**
> → See [[../taskwarrior-custom-integration#73-quinzenal-review-meta-level-15-days|Quinzenal Review Guide]]
> → See [[../taskwarrior-custom-integration#81-correção-de-trajeto-15-day-correction-cycle|Correção de Trajeto Script]]

**Workflow:**

```bash
# View all tasks for current meta_ciclo
task objetivo filter 'meta_ciclo:1'

# Create quinzenal review task
task add objetivo_id:obj_001 meta_ciclo:1 +revisao priority:H \
  due:2025-12-15 "Supervisão Quinzenal - Meta 1"

# 15-day review
task meta_ciclo:1 +revisao list
task meta_ciclo:1 completed end.after:today-15d

# Review Metas for cycle
task meta_ciclo:1 summary
task meta_ciclo:1 stats

# Generate report
task export status:completed modified.after:today-15d | \
  jq '.[] | {description, taxa_conclusao, barreira}'

# Identify barreiras
task meta_ciclo:1 "annotation~barreira" list

# Correção do Trajeto (or use automated script)
correcao-trajeto.py  # Automated 15-day analysis
task meta_ciclo:1 +OVERDUE list
task meta_ciclo:1 modify  # Adjust as needed

# Plan next cycle
task add meta_ciclo:2 +revisao "Next 15-day Meta"
```

**Commands Summary:**
```bash
# Quinzenal review
task meta_ciclo:<n> +revisao list
task meta_ciclo:<n> completed end.after:today-15d
task meta_ciclo:<n> summary

# Correção do Trajeto
task meta_ciclo:<n> +OVERDUE list
task meta_ciclo:<n> "annotation~barreira" list
```

---

### 3.4 Mensal (#supervisão) ^tr-r9lonfzs0

**Frequency:** Monthly

**Purpose:** Avalia o progresso em direção aos sonhos.

**Workflow:**

```bash
# Monthly supervision
task project:sonho:publicar-livro modified.after:today-30d summary
task project:sonho:publicar-livro completed end.after:today-30d

# Review Sonhos
task projects
task project:sonho:publicar-livro +supervisao list

# Monthly statistics
task modified.after:today-30d stats

# Review Objetivos progress
task objetivo_id: modified.after:today-30d list

# Export for analysis
task modified.after:today-30d export > month-report.json
```

**Commands Summary:**
```bash
# Monthly supervision
task +supervisao modified.after:today-30d list
task project:<sonho> modified.after:today-30d summary
task modified.after:today-30d stats

# Export for analysis
task modified.after:today-30d export > month-report.json
```

---

## 4. PAE Integration

### 4.0 Complete Tag Hierarchy System

> **📖 For complete tag system reference:**
> → See [[../taskwarrior-custom-integration#32-tag-hierarchy-convention|Tag Hierarchy Guide]]

**Tag Structure for Your Strategic System:**

**Nível 1: Tipo de Registro**
- `+narrativa` - Narrativa diária
- `+relatorios` - Relatório semanal
- `+supervisao` - Supervisão quinzenal
- `+revisao` - Revisão tática

**Nível 2: Função**
- `+planejamento` - Planejamento estratégico
- `+execucao-diaria` - Execução operacional
- `+otimizacao` - Otimização de processo

**Nível 3: Tempo**
- `+teste_fogo` - Marcador para Teste de Fogo
- `+correcao_trajeto` - Correção após 15 dias
- `+kaizen` - Melhoria contínua diária

**Nível 4: Área/Projeto**
- `+projeto_designio`
- `+projeto_carreira`
- `+saude`
- `+financas`

**Usage Examples:**
```bash
# Daily narrative
task add +narrativa +execucao-diaria "Task description"

# Weekly report
task add +relatorios +projeto_designio "Weekly task"

# Teste de Fogo
task add +teste_fogo +resiliencia "Fire test task"
```

---

### 4.1 Q1-Q4 Planning

**PAE Structure:** 4 trimestres (Q1, Q2, Q3, Q4) - ~13 weeks each

**Commands:**

```bash
# View Objetivos by quarter
task objetivo_trimestre:Q1 list
task objetivo_trimestre:Q2 list
task objetivo_trimestre:Q3 list
task objetivo_trimestre:Q4 list

# Quarterly planning
task add objetivo_id:obj_001_Q1 objetivo_trimestre:Q1 due:2025-03-31 "Q1 Objetivo"
task add objetivo_id:obj_002_Q2 objetivo_trimestre:Q2 due:2025-06-30 "Q2 Objetivo"

# Quarterly review
task objetivo_trimestre:Q1 summary
task objetivo_trimestre:Q1 completed
```

**Strategic Context:** PAE uses calendar quarters, while Estrutura Hierárquica uses 45-day cycles. Track both.

---

### 4.2 Metas Mensais

**PAE Structure:** Monthly goals within quarters

**Commands:**

```bash
# Monthly goals (can use meta_ciclo or create monthly tags)
task add +meta_mensal due:2025-12-31 "Meta Mensal Dezembro"

# View monthly goals
task +meta_mensal list
task +meta_mensal due.after:today-30d list

# Monthly review
task +meta_mensal modified.after:today-30d summary
```

**Strategic Context:** PAE focuses on monthly goals, complement your 15-day Metas.

---

### 4.3 Checklists Semanais

**PAE Structure:** Weekly checklists

**Commands:**

```bash
# Weekly checklist tasks
task add +checklist_semanal due:2025-12-08 "Checklist Semanal"

# View weekly checklists
task +checklist_semanal list
task +checklist_semanal due.after:today-7d list

# Weekly checklist review
task +checklist_semanal modified.after:today-7d list
```

**Strategic Context:** Use alongside your #relatórios (weekly reports).

---

### 4.4 Rotina Semanal

**PAE Structure:** Weekly routine (Segunda-Domingo)

**Commands:**

```bash
# Daily routine tasks (can set due dates for specific days)
task add due:2025-12-08 +rotina_semanal "Segunda: Planejamento técnico"
task add due:2025-12-09 +rotina_semanal "Terça: Desenvolvimento backend"
task add due:2025-12-10 +rotina_semanal "Quarta: Prototipação frontend"

# View weekly routine
task +rotina_semanal due.after:today due.before:today+7d list

# Recurring weekly routine
task add recur:weekly due:2025-12-08 +rotina_semanal "Weekly routine task"
```

**Strategic Context:** Map your weekly routine to Taskwarrior with due dates or recurrence.

---

## 5. Estrutura Hierárquica Integration

### 5.1 Ciclos de 45 dias úteis

**Definition:** 4 cycles of 45 working days = 180 days total

**Commands:**

```bash
# Track cycles (use meta_ciclo or create ciclo UDA)
task add ciclo:1 meta_ciclo:1 "Cycle 1, Meta 1"

# View tasks for cycle
task ciclo:1 list
task meta_ciclo:1 list  # First meta of cycle

# Cycle summary
task ciclo:1 summary

# Track 180-day period
task modified.after:today-180d summary
```

**Strategic Context:** Each 45-day cycle contains 3 Ondas (waves) of 15 days each.

---

### 5.2 Ondas de 3 semanas

**Definition:** 3-week waves (15 working days) within 45-day cycles

**Commands:**

```bash
# Track waves (use meta_ciclo: 1, 2, 3 per cycle)
task add meta_ciclo:1 onda_numero:1 "Wave 1, Meta 1"
task add meta_ciclo:2 onda_numero:1 "Wave 1, Meta 2"
task add meta_ciclo:3 onda_numero:1 "Wave 1, Meta 3"

# View tasks for wave
task onda_numero:1 list
task meta_ciclo:1 list  # First meta = first wave

# Wave review (15-day)
task meta_ciclo:1 +revisao list
task meta_ciclo:1 completed end.after:today-15d
```

**Strategic Context:** Each Onda = 15 days = 1 Meta. Structure: Week 1 (implementation) + Week 2 (optimization) + Week 3 (consolidation).

---

### 5.3 Blocos Diários

**Definition:** Daily time blocks (Manhã, Tarde, Noite)

**Commands:**

```bash
# View tasks by Bloco de Tempo
task bloco_tempo:Manhã due:today list
task bloco_tempo:Tarde due:today list
task bloco_tempo:Noite due:today list

# Add task to specific Bloco
task add bloco_tempo:Manhã due:today +execucao-diaria "Manhã task"
task add bloco_tempo:Tarde due:today +execucao-diaria "Tarde task"
task add bloco_tempo:Noite due:today +execucao-diaria "Noite task"

# Review Bloco completion
task bloco_tempo:Manhã due:today completed
task bloco_tempo:Tarde due:today completed
```

**Strategic Context:** Organize daily Atividades by time blocks for better execution.

---

### 5.4 Correção do Trajeto

**Definition:** Route correction after each Onda (15-day cycle)

**Workflow:**

```bash
# Review completed Metas
task meta_ciclo:1 completed end.after:today-15d

# Identify problems
task meta_ciclo:1 +OVERDUE list
task meta_ciclo:1 "annotation~barreira" list

# Analyze barreiras
task meta_ciclo:1 "annotation~barreira" info

# Adjust next cycle
task meta_ciclo:2 modify  # Adjust based on learnings
task add meta_ciclo:2 +revisao "Adjusted Meta based on cycle 1 learnings"
```

**Strategic Context:** Use after each 15-day Onda to correct course and improve next cycle.

---

## 6. Metrics & Analysis

### 6.1 Taxa de Conclusão (Completion Rate)

**Definition:** Percentage of tasks completed vs. planned

**Calculation:**
```
Taxa = (Completed) / (Total) × 100
```

**Commands:**

```bash
# Daily Taxa
task due:today summary
# Compare: completed vs pending

# Weekly Taxa
task modified.after:today-7d summary
task completed end.after:today-7d
task modified.after:today-7d export > week-tasks.json
# Analyze JSON: count completed vs pending

# Monthly Taxa
task modified.after:today-30d summary
task completed end.after:today-30d
task modified.after:today-30d export > month-tasks.json

# By level
task meta_ciclo:1 summary
task objetivo_id:obj_001_Q1 summary
task project:sonho:publicar-livro summary
```

**Strategic Context:** Target 80%+ for daily, track weekly and monthly for trends.

---

### 6.2 Eficiência Sistêmica (System Efficiency)

**Definition:** Results achieved per hour invested

**Formula:**
```
Eficiência = (Resultados Alcançados) / (Horas Investidas × Fator Qualidade)
Onde Fator Qualidade = 1 + (0.2 × notas de qualidade)
```

**Commands:**

```bash
# Export tasks for analysis
task modified.after:today-7d export > week-tasks.json
task completed end.after:today-7d export > week-completed.json

# Use external script to calculate:
# - Count completed tasks (resultados)
# - Sum estimated/actual hours (from annotations or UDAs)
# - Calculate quality factor
# - Compute efficiency
```

**Strategic Context:** Requires external script analysis of exported JSON data.

---

### 6.3 Coerência Estratégica (Strategic Coherence)

**Definition:** Alignment between daily activities and long-term Sonhos

**Calculation:**
```
Coerência = (Número de conexões verificadas / Total de conexões possíveis) × 100
Target: >85%
```

**Commands:**

```bash
# Verify connections: Atividade → Tarefa → Meta → Objetivo → Sonho
task +execucao-diaria sonho_id: list  # Atividades linked to Sonhos
task tarefa_microciclo: meta_ciclo: objetivo_id: sonho_id: list  # Full chain

# Count tasks with full hierarchy
task sonho_id: objetivo_id: meta_ciclo: tarefa_microciclo: list

# Export for analysis
task export > all-tasks.json
# Analyze: count tasks with complete hierarchy vs. total tasks
```

**Strategic Context:** Ensure all Atividades link back to Sonhos through the hierarchy.

---

### 6.4 Sustentabilidade (Sustainability)

**Definition:** Energy level vs. workload

**Formula:**
```
Sustentabilidade = (Energia média da semana) / (Carga horária média)
Target: >0.7
```

**Commands:**

```bash
# Track energy (use annotations or UDAs)
task <id> annotate "Energia: 4/5"
task <id> annotate "Carga: 6h"

# Export for analysis
task modified.after:today-7d export > week-tasks.json
# Extract energy and workload data from annotations
# Calculate sustainability
```

**Strategic Context:** Monitor weekly to maintain sustainable pace.

---

### 6.5 Teste de Fogo (Fire Test)

**Definition:** Evaluation after 180 working days

> **📖 For complete Teste de Fogo commands and evaluation workflow:**
> → See [[../taskwarrior-custom-integration#74-teste-de-fogo-every-180-days|Teste de Fogo Guide]]

**Dimensions:**
1. Resiliência Operacional
2. Coerência Estratégica
3. Eficiência Sistêmica
4. Adaptabilidade

**Commands:**

```bash
# Tag important assessment tasks for Teste de Fogo
task add objetivo_id:obj_001 +teste_fogo +resiliencia priority:H \
  due:2025-12-20 "Avaliar Resiliência Operacional"

task add objetivo_id:obj_001 +teste_fogo +coerencia priority:H \
  due:2025-12-20 "Verificar Coerência Estratégica"

task add objetivo_id:obj_001 +teste_fogo +eficiencia priority:H \
  due:2025-12-20 "Calcular ROI do Tempo"

task add objetivo_id:obj_001 +teste_fogo +adaptabilidade priority:H \
  due:2025-12-20 "Testar Adaptabilidade"

# Generate Teste de Fogo report
task teste_fogo

# 180-day evaluation (alternative)
task modified.after:today-180d summary
task modified.after:today-180d stats
task modified.after:today-180d export > 180d-evaluation.json

# Review all Sonhos
task projects
task project:sonho:publicar-livro summary

# Review all Objetivos
task objetivo_id: all

# Analyze dimensions (requires external script)
# Use exported JSON to evaluate each dimension
```

**Strategic Context:** Comprehensive evaluation after full 180-day cycle (4 × 45-day cycles).

---

## Workflow Quick Reference

### Daily (Diário)
```bash
tm                    # Morning review
task bloco_tempo:Manhã due:today list
task <id> start
task <id> done
te                    # Evening review
task due:tomorrow list
```

### Weekly (Semanal)
```bash
twk                   # Weekly review
task +relatorios modified.after:today-7d list
task modified.after:today-7d summary
```

### 15-Day (Quinzenal)
```bash
task meta_ciclo:<n> +revisao list
task meta_ciclo:<n> completed end.after:today-15d
task meta_ciclo:<n> summary
```

### Monthly (Mensal)
```bash
task +supervisao modified.after:today-30d list
task project:<sonho> modified.after:today-30d summary
```

### Quarterly (Trimestral)
```bash
task objetivo_trimestre:Q1 summary
task objetivo_trimestre:Q1 completed
```

---

## Next Steps

- See [[TASKWARRIOR_PITFALLS_AND_WORKAROUNDS]] for limitations and solutions
- See [[TASKWARRIOR_COMMAND_CHEATSHEET]] for quick command reference
- See [[TASKWARRIOR_COMPLETE_FEATURES#Hooks API]] for automation hooks
- See [[TASKWARRIOR_COMPLETE_FEATURES#Integration]] for integration methods

---

## Related Guides

### For Advanced Implementation
- [[TASKWARRIOR_COMPLETE_FEATURES#Hooks API]] - **Hooks API** for automating reviews and metrics
- [[TASKWARRIOR_COMPLETE_FEATURES#Integration]] - **Integration** with external tools and scripts
- [[TASKWARRIOR_COMPLETE_FEATURES#Advanced Topics]] - **Advanced Topics** (Context, UDAs, Custom Reports)

### For Practical Workflows
- [[TASKWARRIOR_ALIASES_REFERENCE]] - Complete alias documentation for efficient workflows
- [[TASKWARRIOR_COMMAND_CHEATSHEET]] - Quick command reference

### For Understanding Limitations
- [[TASKWARRIOR_PITFALLS_AND_WORKAROUNDS]] - Workarounds and best practices

---

*Complete Taskwarrior documentation: [taskwarrior.org/docs](https://taskwarrior.org/docs/)*

