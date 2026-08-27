---
type: period_report
entity_type: period_report
period: onda
id: sprint-YYYY-WNN
template_role: sprint_kickoff
template_version: 1.0
ikigai_cluster: plan

date_start: YYYY-MM-DD
date_end: YYYY-MM-DD

verdict: ACTIVE
verdict_score: 0.0

sonho_id:
parent_period: quarterly-review-YYYY-QN
ikigai_vector: skill
ikigai_score_inicio: 0.0

vault_path:
vault_hash:
status: draft
tags: [period/onda, ikigai/plan, template/sprint-kickoff]
---

# Sprint Kickoff: [TEMA] (Onda [N] / Q[N])

> **Horizonte:** 15 dias uteis (3 semanas) · **Cluster:** PLAN (Tatico) · **Tipo:** Sprint Backlog
>
> Este template abre uma Onda. Define capacidade, goal unico e quebra tarefas para as 3 Semanais.

---

## 1. Contexto da Onda (Inputs do Trimestral)

- **Trimestral pai:** [id]
- **Tema da Onda:** [descricao]
- **Ondas anteriores no trimestre:**
  - Onda 1: [verdict] [score]
  - Onda 2: [verdict] [score]
- **Ondas restantes:**
  - Onda atual: [N] / 3
  - Onda final: [N+1]
- **Histerese atual:** [dias em MAINTAIN/PUSH]
- **Q_HE atual:** [0.XX]

---

## 2. Sprint Goal (Single Observable Outcome)

### 2.1 Goal Statement
> [Uma unica sentenca declarando o resultado observavel do sprint. Se apenas UMA coisa for cumprida, e esta.]

### 2.2 Nao-Objetivos (Out of Scope)
- [Ex: Nao otimizar performance de queries neste sprint]
- [Ex: Nao migrar para novo framework]
- [Ex: Nao contratar novo membro do time]

### 2.3 Definition of Done (Sprint-Level)
- [ ] Goal statement 100% cumprido
- [ ] Testes passando (>90% coverage na area tocada)
- [ ] Documentacao atualizada (README, CHANGELOG)
- [ ] Code review aprovado
- [ ] Deploy em ambiente de staging
- [ ] Metricas de uso monitoradas por 24h
- [ ] Daily Reflection finalizada

---

## 3. Capacity Planning (Histerese + 5x3x3)

### 3.1 Capacidade Disponivel
- **Horas liquidas de foco / dia:** [X]
- **Dias uteis no sprint:** [N]
- **Total horas sprint:** [X x N]
- **Buffer para imprevistos (20%):** [X x 0.2]
- **Capacidade efetiva:** [X x N x 0.8]

### 3.2 Distribuicao Alocada (5x3x3)
| Dimensao | Horas Alocadas | % Capacidade |
|----------|----------------|--------------|
| Execucao (deep work + execucao) | [X] | [X/cap_efetiva] |
| Analise (review + reflexao) | [X] | [X/cap_efetiva] |
| Planejamento (planning + design) | [X] | [X/cap_efetiva] |

### 3.3 Cognitive Debt Tracking
- **Tarefas com MVK < target:** [N] (risco de inchaco)
- **Tarefas com MVK >= target:** [M] (prontas para execucao)
- **Knowledge gaps bloqueantes:** [lista de skills/conceitos a aprender antes]

---

## 4. Sprint Backlog (Task Breakdown)

### 4.1 Tasks por MVK (Minimum Viable Knowledge)
| Task | MVK Atual | MVK Target | Delta | Estimativa (h) | Cognitive Debt Flag | Status |
|------|-----------|------------|-------|----------------|---------------------|--------|
| [Task 1] | [0-5] | [0-5] | [+] | [X] | [ ] Sim / [X] Nao | [ ] |
| [Task 2] | [0-5] | [0-5] | [+] | [X] | [ ] Sim / [X] Nao | [ ] |
| [Task 3] | [0-5] | [0-5] | [+] | [X] | [X] Sim / [ ] Nao | [ ] |
| [Task 4] | [0-5] | [0-5] | [+] | [X] | [ ] Sim / [X] Nao | [ ] |

### 4.2 Tasks por Semana
- **Semana 1 (Dias 1-7):**
  - [ ] [Task A] --- [horas]
  - [ ] [Task B] --- [horas]
  - [ ] [Task C] --- [horas]
- **Semana 2 (Dias 8-14):**
  - [ ] [Task D] --- [horas]
  - [ ] [Task E] --- [horas]
- **Semana 3 (Dias 15-21):**
  - [ ] [Task F] --- [horas]
  - [ ] [Task G] --- [horas]

### 4.3 Tarefas com Cognitive Debt (Requerem aprendizado previo)
- **[Task com debt]:** [Acao de cobertura --- ex: ler paper X, fazer tutorial Y, MVP Z]
- **Estimativa de tempo de coverage:** [horas]

---

## 5. Sprint Risks & Mitigations

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| [Ex: API externa fora do ar] | [B/M/A] | [B/M/A] | [Mock + retry exponencial] |
| [Ex: Bloqueio de key resource] | [B/M/A] | [B/M/A] | [Pair programming] |
| [Ex: Scope creep] | [B/M/A] | [B/M/A] | [Reuniao diaria de 15min] |

---

## 6. Sprint Ceremonies (Schedule)

| Dia | Horario | Cerimonia | Duracao |
|-----|---------|-----------|---------|
| D+0 (Segunda) | 09:00 | Sprint Planning (this template) | 1h |
| Diario | 09:00 | Daily Standup | 15min |
| D+5 (Sexta W1) | 16:00 | Weekly Review + Retro | 30min |
| D+10 (Sexta W2) | 16:00 | Weekly Review + Retro | 30min |
| D+15 (Sexta W3) | 16:00 | Sprint Review + Retro (closes onda) | 1h |

---

## 7. Sprint Tracking

### 7.1 Burndown Tracking
- **Tasks completadas:** [X / Total]
- **Horas queimadas:** [X / Capacidade]
- **Velocity real:** [tasks/dia]
- **Estimativa de conclusao:** [data]

### 7.2 Daily Snapshot
| Dia | Tasks Feitas | Horas | Q_HE | Comentario |
|-----|--------------|-------|------|------------|
| D+1 | [X] | [X] | [X.XX] | [...] |
| D+2 | [X] | [X] | [X.XX] | [...] |

---

## 8. Handoff & Sync

- [ ] Sprint backlog sync'd com `vibe_ops.db` via `life sync vault`
- [ ] Tasks linkadas a sonhos (FK)
- [ ] Daily reflection gerada automaticamente
- [ ] Sprint kickoff documentado para retrospectiva

---

## Sincronizacao e Fechamento

- [ ] YAML frontmatter validado
- [ ] Goal unico declarado
- [ ] Capacity calculada
- [ ] Tasks com MVK estimado
- [ ] Cerimonias agendadas
- [ ] Risks mapeados
- [ ] Commit `feat(agentic-md): sprint kickoff template`

---

*Template: Sprint Kickoff · v1.0 · Cluster PLAN · IKIGAi Sys-01 · 2026-06-26*
