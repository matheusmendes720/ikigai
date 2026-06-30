---
type: period_report
entity_type: period_report
period: quarterly
id: quarterly-YYYY-QN
template_role: aggregate_root
template_version: 1.0
ikigai_cluster: plan

date_start: YYYY-MM-DD
date_end: YYYY-MM-DD

verdict: ACTIVE
verdict_score: 0.0

# Hierarquia do trimestre (preenchida na execucao)
sonho_id:
parent_period:
# IKIGAi alignment snapshot
ikigai_vector: passion
ikigai_score_inicio: 0.0
ikigai_score_fim: 0.0

# Sync metadata
vault_path:
vault_hash:
status: draft
tags: [period/quarterly, ikigai/plan, template/quarterly-planning]
---

# Planejamento Trimestral: Q[N] [YYYY] — [TEMA]

> **Horizonte:** 90 dias · **Cluster:** PLAN (Estrategico) · **Vinculado a:** [[sonho-ativo]]
>
> Este template agrega o ciclo completo: Sondagem → Sonho → Trimestral → 3× Onda → 9× Semanal → 45× Diario.

---

## 1. Sondagem (Deteccao de Contexto)

### 1.1 Estado Atual do Sistema
- **Q_HE atual (media 7 dias):** [0.00]
- **Ultima Policy decision:** [MAINTAIN/REDUCE/PUSH/RECOVER]
- **Ultima evaluation trimestral:** [data] → [PASS/PARTIAL/FAIL]
- **Trend velocity (pomodoros/semana):** [+X / -X / estavel]

### 1.2 Sonhos Ativos (vinculados)
| Sonho | Status | Kill Switch | Verdict Score | Vetor IKIGAi |
|-------|--------|-------------|---------------|---------------|
| [Nome] | [ACTIVE/PIVOTED/VALIDATED] | [YYYY-MM-DD] | [0.0-1.0] | [passion/skill/market/revenue] |

### 1.3 Capacidade Disponivel
- **Horas liquidas de foco / semana:** [X]
- **Histerese atual:** [dias em MAINTAIN/REDUCE]
- **Risco de burnout (Q_HE<0.45 sustentado):** [BAIXO/MEDIO/ALTO]

---

## 2. Definicao Estrategica (Sonho → Trimestral)

### 2.1 Hipotese Falsificavel (Axis 1 — Kill Switch)
- **Hipotese:** [Declaracao clara e mensuravel. Ex: "Posso conseguir oferta em IA ate YYYY-MM-DD"]
- **Criterio de falsificacao:** [Evento/timing/threshold que prova hipotese falsa]
- **Data do Kill Switch:** [YYYY-MM-DD]
- **Janela de medicao:** [X dias]
- **Status atual:** [ACTIVE]

### 2.2 Leading vs Lagging Indicators (Axis 2)
**Leading (comportamento, controlavel):**
| Indicador | Meta/semana | Verificacao |
|-----------|-------------|-------------|
| [Ex: Pomodoros Deep Work em IA] | [>= 20] | [DB: pomodoros_ia / week] |
| [Ex: PRs mergeados] | [>= 2] | [git_prs_merged / week] |

**Lagging (resultado, fora de controle):**
| Indicador | Meta/trimestre | Verificacao |
|-----------|----------------|-------------|
| [Ex: Aplicacoes enviadas] | [>= 50] | [applications / quarter] |
| [Ex: Ofertas recebidas] | [>= 3] | [offers / quarter] |

### 2.3 Gatilhos de Refatoracao (Axis 3)
- [ ] Saude: lesao, burnout, doenca cronica
- [ ] Mercado: mudanca significativa no setor
- [ ] Familia: nascimento, mudanca, perda
- [ ] Energia Mental: Q_HE<0.45 sustentado > 30 dias
- [ ] Hipotese invalidada externamente

---

## 3. Proporcao 5x3x3 (5 dias → 3 semanas → 3 meses)

### 3.1 Calculo Matematico
```
Execucao (5 dias uteis)   →  Relatorio Diario       →  aggregation: completion_rate
Analise  (3 semanas)       →  Revisao Semanal        →  aggregation: policy_trail
Planejamento (3 meses)     →  Avaliacao Trimestral   →  aggregation: teste_de_fogo
```

### 3.2 Distribuicao Alocada
| Dimensao | Peso | Alvo Mensal | Status Q |
|----------|------|-------------|----------|
| Execucao (completion_rate) | 0.50 | >= 0.75 | [ ] |
| Analise (policy_accuracy)   | 0.20 | >= 0.70 | [ ] |
| Planejamento (adherence)    | 0.15 | >= 0.65 | [ ] |
| Aprendizado (xp + mastery)   | 0.10 | >= 0.60 | [ ] |
| Bem-estar (Q_HE avg)         | 0.05 | >= 0.65 | [ ] |

### 3.3 Formulas Explcitas
```
completion_rate = tarefas_concluidas / tarefas_planejadas
verdict_score   = (media_teste_fogo * 0.5) + (leading_cumprido * 0.3) + (histerese_sustentada * 0.2)
periodic_proportions = Execucao(0.50) : Analise(0.20) : Planejamento(0.15) : Aprendizado(0.10) : Bem-estar(0.05)
```

---

## 4. Desdobramento em 3 Ondas (15 dias uteis cada)

### 4.1 Onda 1 (Dias 1-45)
- **Tema:** [TEMA]
- **Goal unico:** [Single observable outcome]
- **3 Semanais vinculadas:**
  - Semana 1 (dias 1-7): [must-haves]
  - Semana 2 (dias 8-14): [must-haves]
  - Semana 3 (dias 15-21): [must-haves]
- **Verdict esperado:** CONTINUE_WAVE
- **Onda 2 herda:** [conhecimento/ativos]

### 4.2 Onda 2 (Dias 46-90)
- **Tema:** [TEMA]
- **Goal unico:** [Single observable outcome]
- **3 Semanais vinculadas:** [mesma estrutura]
- **Verdict esperado:** CONTINUE_WAVE
- **Onda 3 herda:** [conhecimento/ativos]

### 4.3 Onda 3 (Dias 91-135... ou D-90)
- **Tema:** [TEMA]
- **Goal unico:** [Single observable outcome]
- **3 Semanais vinculadas:** [mesma estrutura]
- **Verdict esperado:** [CONTINUE_WAVE / CORRECT_TRAJECTORY / KILL_WAVE]
- **Handoff para proximo trimestre:** [artefatos para Q+1]

---

## 5. Teste de Fogo (5 Dimensoes x 4 Semanas)

| Dimensao | W1 Target | W2 Target | W3 Target | W4 Target |
|----------|-----------|-----------|-----------|-----------|
| **Execucao** (completion_rate) | >= 0.70 | >= 0.75 | >= 0.80 | >= 0.85 |
| **Analise** (policy_accuracy)  | >= 0.65 | >= 0.70 | >= 0.70 | >= 0.75 |
| **Planejamento** (adherence)    | >= 0.60 | >= 0.65 | >= 0.70 | >= 0.70 |
| **Aprendizado** (xp + mastery)  | >= 0.55 | >= 0.60 | >= 0.65 | >= 0.70 |
| **Bem-estar** (Q_HE avg)        | >= 0.60 | >= 0.65 | >= 0.70 | >= 0.70 |

---

## 6. Top 3 Epicos do Trimestre (Goal-aligned)

1. **[Epico 1]** — [Objetivo Claro e Acionavel] (IKIGAi: [vetor])
2. **[Epico 2]** — [Objetivo Claro e Acionavel] (IKIGAi: [vetor])
3. **[Epico 3]** — [Objetivo Claro e Acionavel] (IKIGAi: [vetor])

---

## 7. Capacity Planning (Histerese + 5x3x3)

### 7.1 Histerese Asymmetric
- **Days up (MAINTAIN → PUSH):** >= 3 dias com Q_HE >= 0.85
- **Days down (MAINTAIN → REDUCE):** >= 2 dias com Q_HE < 0.65
- **Emergency (RECOVER):** Q_HE < 0.30 OU infractions >= 3

### 7.2 Carga Planejada vs Capacidade
- **Pomodoros planejados / semana:** [X]
- **Horas de Deep Work / dia:** [Y]
- **Taxa ocupacao:** [X / capacidade_total]

---

## 8. Criterios de Saida (End-of-Quarter)

| Criterio | Meta | Medicao |
|----------|------|---------|
| Teste de Fogo (media 5 dims) | >= 0.70 | Avg(W1+W2+W3+W4) |
| Leading indicators cumpridos | >= 80% | sum(actual / target) |
| Lagging indicators cumpridos | >= 60% | sum(actual / target) |
| Histerese sustained | Q_HE >= 0.65 | mean(Q_HE last 30 days) |
| Sonho verdict | FALSIFIED ou VALIDATED | (depende do outcome) |

---

## 9. Verdict Computado (Algoritmo)

```
SE media_teste_fogo >= 0.70 AND leading_cumprido >= 0.80:
    verdict = PASS
ELIF media_teste_fogo >= 0.50 OR leading_cumprido >= 0.50:
    verdict = PARTIAL
ELSE:
    verdict = FAIL
```

- **Verdict:** [PASS / PARTIAL / FAIL]
- **Verdict Score:** [0.00-1.00]
- **Acao para proximo trimestre:** [CONTINUE / CORRECT / KILL / PIVOT]

---

## 10. Recalibracao (Handoff para Q+1)

- [ ] Sonho atualizado (validado / pivotado / abandonado)
- [ ] Novas hipoteses candidatas para Q+1
- [ ] Trimestral Q+1 rascunhado com Ondas alinhadas
- [ ] Daily Reflection consolidada em Relatorio Trimestral
- [ ] Sync com `vibe_ops.db` via `life sync vault --folder _templates_periodos`

---

## Sincronizacao e Fechamento

- [ ] YAML frontmatter validado contra ADR-006
- [ ] Verdict score calculado (0-1)
- [ ] IKIGAi alignment preenchido (inicio vs fim)
- [ ] Histerese tracking ativo
- [ ] Sync com DB via `life sync vault`

---

*Template: Planejamento Trimestral · v1.0 · Cluster PLAN · IKIGAi Sys-01 · 2026-06-26*
