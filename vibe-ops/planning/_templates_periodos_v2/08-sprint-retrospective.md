---
type: period_report
entity_type: period_report
period: onda
id: sprint-retro-YYYY-WNN
template_role: sprint_retrospective
template_version: 1.0
ikigai_cluster: plan

date_start: YYYY-MM-DD
date_end: YYYY-MM-DD

verdict: ACTIVE
verdict_score: 0.0

sonho_id:
parent_period: sprint-YYYY-WNN
ikigai_vector: skill

vault_path:
vault_hash:
status: draft
tags: [period/onda, ikigai/plan, template/sprint-retrospective]
---

# Sprint Retrospective: [TEMA] (Onda [N] / Q[N])

> **Horizonte:** 15 dias úteis (3 semanas) · **Cluster:** PLAN (Tatico) · **Tipo:** Fechamento de Sprint
>
> Este template fecha a Onda. Captura Start/Stop/Continue, KAIZEN, e alimenta a proxima Onda ou o Quarterly Review.

---

## 1. Sprint Snapshot (Inputs)

### 1.1 Metricas Agregadas
- **Sprint ID:** [sprint-YYYY-WNN]
- **Onda:** [N] / 3 do trimestre
- **Goal statement:** [do kickoff]
- **Tasks planejadas:** [X]
- **Tasks completadas:** [X / Y]
- **Completion rate:** [0.XX]
- **Velocity (tasks/dia):** [X.XX]
- **Horas queimadas vs capacidade:** [X / Y]
- **Q_HE medio no sprint:** [0.XX]
- **Policy trail:** [PUSH: Xd, MAINTAIN: Xd, REDUCE: Xd, RECOVER: Xd]

### 1.2 Verdict Computado
```
SE completion >= 0.80 AND Q_HE >= 0.65:
    verdict = PASS
ELIF completion >= 0.50 OR Q_HE >= 0.45:
    verdict = PARTIAL
ELSE:
    verdict = FAIL
```
- **Verdict:** [PASS / PARTIAL / FAIL]
- **Verdict Score:** [0.00-1.00]

---

## 2. Start / Stop / Continue (Core Retro)

### 2.1 START (Coisas que devemos COMECAR a fazer)
- [Item 1 - ex: "Pair programming em tasks com MVK<target"]
- [Item 2 - ex: "Daily reflection as 18h em vez de 22h"]
- [Item 3 - ex: "Buffer de 1 task/sprint para imprevistos"]

### 2.2 STOP (Coisas que devemos PARAR de fazer)
- [Item 1 - ex: "Reunioes diarias > 15min sem agenda"]
- [Item 2 - ex: "Multitasking em >2 tasks simultaneas"]
- [Item 3 - ex: "Commits sem rodar testes localmente"]

### 2.3 CONTINUE (Coisas que devemos MANTER)
- [Item 1 - ex: "Code review em <4h apos PR aberto"]
- [Item 2 - ex: "Daily standup as 9h em ponto"]
- [Item 3 - ex: "Pomodoros de 50+10 com pausas ativas"]

---

## 3. KAIZEN (1 melhoria por sprint)

### 3.1 Melhoria Selecionada
- **Descricao:** [1-2 frases sobre a melhoria. Ex: "Reduzir tempo de code review de 4h para 2h, atraves de PR templates mais detalhados"]
- **Por que esta e nao outras:** [Justificativa baseada nos dados do sprint]
- **Como medir sucesso:** [Metrica mensuravel. Ex: "tempo medio PR->approve <2h"]
- **Owner:** [Quem sera responsavel]
- **Prazo:** [Quando vai ser implementada]

### 3.2 Anti-patterns Observados
- [Anti-pattern 1 - ex: "Context switching entre 3+ tasks/dia"]
- [Anti-pattern 2 - ex: "Decisoes sem criterio escrito"]
- [Anti-pattern 3 - ex: "Skip de testes para 'velocidade'"]

---

## 4. Velocity Tracking

### 4.1 Comparacao Trimestral
| Sprint | Tasks | Horas | Velocity | Completion | Q_HE | Verdict |
|--------|-------|-------|----------|-------------|------|---------|
| [Sprint -2] | [X] | [X] | [X.XX] | [0.XX] | [X.XX] | [...] |
| [Sprint -1] | [X] | [X] | [X.XX] | [0.XX] | [X.XX] | [...] |
| **[Sprint atual]** | [X] | [X] | [X.XX] | [0.XX] | [X.XX] | [...] |

### 4.2 Analise de Velocity
- **Trend:** [+/-/=]
- **Causa raiz:** [Por que velocity subiu/desceu/estagnou]
- **Meta para proximo sprint:** [X.XX tasks/dia]

---

## 5. Cognitive Debt Status (End-of-Sprint)

### 5.1 Knowledge Gaps Resolvidos
- [Gap 1 - ex: "MVK para Kubernetes: 2 -> 4"]
- [Gap 2 - ex: "MVK para Terraform: 1 -> 3"]

### 5.2 Knowledge Gaps Pendentes
- [Gap 1 - ex: "MVK para Grafana: 1 (target 3) - ainda bloqueante"]
- [Gap 2 - ex: "MVK para debugging async: 2 (target 4)"]

### 5.3 Tasks com Cognitive Debt Residual
- [Task com debt] - [Acao de cobertura pend]

---

## 6. Histerese & Policy Trail

### 6.1 Dias em cada Estado
| Estado | Dias | Periodo | Notas |
|--------|------|---------|-------|
| PUSH | [X] | [DD/MM-DD/MM] | [Ex: bloqueio removido] |
| MAINTAIN | [X] | [DD/MM-DD/MM] | [Ex: equilibrio] |
| REDUCE | [X] | [DD/MM-DD/MM] | [Ex: carga alta] |
| RECOVER | [X] | [DD/MM-DD/MM] | [Ex: Q_HE<0.30] |

### 6.2 Transicoes Significativas
- [Ex: "D+5: MAINTAIN -> REDUCE (3 tasks paralelas, risco de burnout)"]
- [Ex: "D+10: REDUCE -> MAINTAIN (recuperado)"]
- [Ex: "D+12: PUSH -> MAINTAIN (histerese sustentada 3+ dias)"]

---

## 7. Cross-references

- **Onda pai:** [sprint-YYYY-WNN]
- **Quarterly pai:** [quarterly-review-YYYY-QN]
- **Sonho vinculado:** [id]
- **Next sprint:** [sprint-YYYY-WNN+1]
- **Proximo Quarterly Review:** [quarterly-review-YYYY-QN+1]

---

## 8. Handoff para Proximo Sprint

### 8.1 Tasks Pendentes (carregadas para proximo sprint)
- [Task A] - [Razao: blocker X] - [Estimativa: Yh]
- [Task B] - [Razao: dependency Z] - [Estimativa: Wh]

### 8.2 Acoes para Proximo Sprint Kickoff
- [ ] Revisar Sprint Backlog do proximo sprint
- [ ] Atualizar capacity planning baseado em velocity real
- [ ] Aplicar KAIZEN definido em SS3.1
- [ ] Ajustar cognitive debt plan
- [ ] Decidir KILL_WAVE / CORRECT_TRAJECTORY / CONTINUE_WAVE

### 8.3 Decisao da Proxima Onda
- [ ] **CONTINUE_WAVE** (manter momentum)
- [ ] **CORRECT_TRAJECTORY** (ajustar approach)
- [ ] **KILL_WAVE** (abandonar, pivotar)

---

## Sincronizacao e Fechamento

- [ ] YAML frontmatter validado
- [ ] Verdict score calculado
- [ ] KAIZEN documentado
- [ ] Velocity tracking atualizado
- [ ] Histerese trail registrado
- [ ] Next kickoff agendado
- [ ] Commit `feat(agentic-md): sprint retrospective template`

---

*Template: Sprint Retrospective · v1.0 · Cluster PLAN · IKIGAi Sys-01 · 2026-06-26*
