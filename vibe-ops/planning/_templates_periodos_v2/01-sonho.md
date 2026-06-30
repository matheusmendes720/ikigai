---
type: period_report
period: sonho
template_version: 1.0
ikigai_cluster: plan
entity_type: period_report
date_start: YYYY-MM-DD
date_end: YYYY-MM-DD
sonho_id:
ikigai_vector:
xp_gained:
mastery_delta:
verdict:
verdict_score:
policy_recommendation:
parent_period:
status: draft
tags: [period/sonho, ikigai/plan, falsifiable]
---

# Sonho: [Nome do Sonho — ex: "Emprego remoto em IA Engineering"]

> **Horizonte:** 6-12 meses · **Cluster:** PLAN (Estratégico) · **Vinculado a:** [[Modelagem Operacional]] §1.2 e [[Planejamento (Estratégico e Tático)]]
>
> Este template é a entrada do nível mais alto da pirâmide. Define o sonho como hipótese falseável, mapeia seus indicadores e dispara a Revisão Mensal / Avaliação Trimestral / Teste de Fogo downstream.

---

## 1. Definição do Sonho (Hipótese Falseável — Axis 1)

> *O sonho só é válido se puder ser provado falso. Defina a hipótese de forma mensurável.*

- **Título do Sonho:** [Nome claro, verbo no infinitivo, horizonte temporal]
- **Hipótese (texto):** [Mínimo 10 caracteres. Ex: "Posso conquistar uma vaga remota em IA Engineering com salário ≥ R$ 12k até Dez/2026."]
- **Horizonte:** [Data Início] → [Data Fim] (6-12 meses)
- **IKIGAi Vetor Principal:** [ ] Passion / [ ] Skill / [ ] Market / [ ] Revenue
- **KPIs de Saída (definição de "done"):**
  1. [KPI 1 — ex: "Receber ≥ 3 ofertas de emprego"]
  2. [KPI 2 — ex: "Construir portfólio público com 5 projetos de IA"]
  3. [KPI 3 — ex: "Manter Q_HE ≥ 0.65 por 6 meses consecutivos"]

---

## 2. Critério de Falsificação (Kill Switch — Axis 1)

> *O que precisa acontecer ou deixar de acontecer para você matar / pivotar o sonho?*

- **Janela de Medição:** [X dias] (recomendado: 90-365)
- **Threshold de Evidência:** [Descreva o evento, métrica ou limite de tempo que prova a hipótese falsa. Ex: "0 ofertas após 6 meses + completion_rate < 0.5 nos trimestres intermediários"]
- **Data do Kill Switch:** [YYYY-MM-DD — o sistema dispara avaliação automática neste dia]
- **Ação ao Atingir Threshold:**
  - [ ] Abandono total
  - [ ] Pivot (revisar hipótese, manter esforço)
  - [ ] Extensão de prazo (revisar horizonte)
  - [ ] Subdivisão (quebrar em sub-sonhos menores)

---

## 3. Indicadores Leading vs Lagging (Axis 2)

> *Separar o que você controla (leading) do que o mercado devolve (lagging).*

### 3.1 Leading Indicators (comportamento — você controla)

| Indicador | Meta (semanal) | Medição |
|----------|:---:|---------|
| [Ex: Pomodoros de Deep Work em IA] | ≥ 20 | `pomodoros_ia / week` |
| [Ex: PRs mergeados no portfólio] | ≥ 2 | `git_prs_merged / week` |
| [Ex: Networking ativo] | ≥ 3 interações | `outreach_sent / week` |
| [Ex: Horas de sono ≥ 7h] | ≥ 6 dias | `sleep_log / week` |

### 3.2 Lagging Indicators (impacto — mercado devolve)

| Indicador | Meta (trimestral) | Medição |
|----------|:---:|---------|
| [Ex: Aplicações enviadas] | ≥ 50 | `applications / quarter` |
| [Ex: Entrevistas técnicas] | ≥ 8 | `interviews / quarter` |
| [Ex: Ofertas recebidas] | ≥ 3 | `offers / quarter` |
| [Ex: Seguidores LinkedIn (relevância)] | ≥ 2000 | `linkedin_followers / quarter` |

---

## 4. Gatilhos de Refatoração (Axis 3)

> *Que mudanças no ambiente forçam uma reavaliação automática da Folha Norte?*

- [ ] **Saúde:** Lesão, burnout sustentado (>2 semanas em RECOVER), doença crônica
- [ ] **Mercado:** Mudança significativa no setor (nova tech dominante, recessão, layoff em massa)
- [ ] **Família:** Nascimento, mudança de cidade, perda familiar
- [ ] **Energia Mental:** Queda sustentada de Q_HE < 0.45 por >30 dias
- [ ] **Hipótese invalidada externamente:** Evidência pública de que o sonho não é mais viável
- [ ] **Outro:** [Especificar]

---

## 5. Verdict Computado (Algoritmo 3-Axis)

> **Fórmula:** Veredito = interseção dos 3 eixos.

```
SE kill_switch_date <= hoje:
    SE leading_met >= 0.8 AND lagging_met >= 0.8:
        verdict = VALIDATED
    ELIF leading_met >= 0.8 AND lagging_met < 0.5:
        verdict = FALSIFIED
    ELIF refactor_trigger_detected:
        verdict = PIVOTED
    ELSE:
        verdict = ABANDONED
SENÃO:
    verdict = ACTIVE
```

- **Status Atual:** [ ] ACTIVE / [ ] VALIDATED / [ ] FALSIFIED / [ ] PIVOTED / [ ] ABANDONED
- **Verdict Score:** [0.00 - 1.00] — média ponderada: 0.5 × (leading_met) + 0.5 × (1 - lagging_gap)
- **Próxima Avaliação Automática:** [YYYY-MM-DD]

---

## 6. KPIs Macro (Trimestral — Teste de Fogo lite)

> *Aplicar a versão resumida do Teste de Fogo (5 dimensões), consolidando os 3 meses.*

| Dimensão | Meta | Realizado | Gap | Verdict Parcial |
|----------|:---:|:---:|:---:|:---:|
| **Execução** (completion rate médio) | ≥ 0.75 | [X] | [X-0.75] | [ ] OK / [ ] BAIXO |
| **Análise** (policy corretude) | ≥ 0.70 | [X] | [X-0.70] | [ ] OK / [ ] BAIXO |
| **Planejamento** (adherence to plans) | ≥ 0.65 | [X] | [X-0.65] | [ ] OK / [ ] BAIXO |
| **Aprendizado** (xp ganho + mastery delta) | ≥ 0.60 | [X] | [X-0.60] | [ ] OK / [ ] BAIXO |
| **Bem-estar** (Q_HE médio) | ≥ 0.65 | [X] | [X-0.65] | [ ] OK / [ ] BAIXO |

**Verdict Agregado:** [ ] PASS (média ≥ 0.70) / [ ] PARTIAL (0.50-0.70) / [ ] FAIL (< 0.50)

---

## 7. Status dos Dreams Vinculados (se houver sub-sonhos)

| Sub-sonho | Status | Verdict | Próxima Ação |
|-----------|:---:|:---:|---|
| [Nome do sub-sonho 1] | [ACTIVE] | [0.65] | [Continue] |
| [Nome do sub-sonho 2] | [PIVOTED] | [0.42] | [Revisar hipótese] |
| [Nome do sub-sonho 3] | [VALIDATED] | [0.88] | [Marcar done] |

---

## 8. IKIGAi Alignment Check

> *Este sonho está alinhado com seus 4 vetores IKIGAi?*

| Vetor | Peso (1-5) | Score Atual (0-1) | Contribuição (peso × score) |
|-------|:---:|:---:|:---:|
| Passion | [X] | [X] | [X] |
| Skill | [X] | [X] | [X] |
| Market | [X] | [X] | [X] |
| Revenue | [X] | [X] | [X] |

**IKIGAi Total:** [soma / 20] — alinhamento = [X / 20]

---

## 9. Macro-Foco do Próximo Trimestre

> *Top 3 objetivos que movem a agulha para este sonho.*

1. **[Épico 1]** — [Objetivo Acionável] (IKIGAi: [vetor])
2. **[Épico 2]** — [Objetivo Acionável] (IKIGAi: [vetor])
3. **[Épico 3]** — [Objetivo Acionável] (IKIGAi: [vetor])

---

## 10. Rota de Correção (se PARTIAL ou FAIL)

> *Se o verdict for PARTIAL ou FAIL, defina aqui a correção. Caso contrário, ignore.*

- **Diagnóstico:** [Por que este sonho está em risco?]
- **Correção do Trajeto:** [O que mudar no próximo trimestre?]
- **Novos Indicadores:** [Adicionar/remover algum leading/lagging indicator?]
- **Sub-sonhos a fechar/abrir:** [Pivots, abbandons, novas tentativas]
- **Próximo Checkpoint:** [YYYY-MM-DD]

---

## Sincronização e Fechamento

- [ ] Hipótese escrita com ≥ 10 caracteres
- [ ] Kill switch data definida e ≤ horizonte + 90 dias
- [ ] Leading + lagging indicators têm metas mensuráveis
- [ ] Refactor triggers listados (≥ 1)
- [ ] Verdict score calculado (0-1)
- [ ] IKIGAi alignment preenchido
- [ ] Top 3 épicos do próximo trimestre definidos
- [ ] Sub-sonhos atualizados (se aplicável)
- [ ] Sync com `vibe_ops.db` via `life sync vault`

---

*Template: Sonho · v1.0 · Cluster PLAN (Estratégico) · IKIGAi Sys-01 · 2026-06-26*
