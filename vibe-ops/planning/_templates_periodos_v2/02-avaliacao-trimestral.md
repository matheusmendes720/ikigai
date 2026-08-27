---
type: period_report
period: quarterly
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
parent_period: sonho_id_do_trimestre
status: draft
tags: [period/quarterly, ikigai/plan, avaliacao-trimestral]
---

# Avaliação Trimestral: [Q1/Q2/Q3/Q4 YYYY]

> **Horizonte:** 90 dias (trimestre) · **Cluster:** PLAN (Estratégico) · **Consolida:** 6 Ondas / 2 Macro-Fases / 12 Rev. Semanais
>
> Aplica Teste de Fogo lite (5 dimensões) sobre o trimestre. Veredito determina macro-foco do próximo trimestre.

---

## 1. Identificação

- **Trimestre:** [Q1/Q2/Q3/Q4] [YYYY]
- **Data Início:** [YYYY-MM-DD]
- **Data Fim:** [YYYY-MM-DD]
- **Sonho(s) Ativo(s):** [FK para 1 ou mais `01-sonho.md`]
- **IKIGAi Vetor Principal:** [ ] Passion / [ ] Skill / [ ] Market / [ ] Revenue
- **Status:** [ ] Draft / [ ] Em Revisão / [ ] Fechado

---

## 2. Ondas Consolidadas (3 Ondas × 15 dias cada)

> *Resumir as 3 Ondas que compõem este trimestre. Para detalhes, ver `_periodos/onda-NN.md`.*

| Onda | Período | Completion Rate | Policy Trail | Verdict |
|------|---------|:---:|---|:---:|
| Onda 1 (Sem 1-3) | [YYYY-MM-DD] → [YYYY-MM-DD] | [0.XX] | [PUSH→MAINTAIN] | [PASS] |
| Onda 2 (Sem 4-6) | [YYYY-MM-DD] → [YYYY-MM-DD] | [0.XX] | [MAINTAIN] | [PASS] |
| Onda 3 (Sem 7-9) | [YYYY-MM-DD] → [YYYY-MM-DD] | [0.XX] | [REDUCE] | [PARTIAL] |

**Completion Rate Médio do Trimestre:** [média das 3 ondas] (0.00 - 1.00)

---

## 3. KPIs Macro (consolidação dos 90 dias)

> *Aplicar a versão resumida do Teste de Fogo (5 dimensões).*

| Dimensão | Meta | Realizado | Gap | Verdict Parcial |
|----------|:---:|:---:|:---:|:---:|
| **Execução** (completion rate médio) | ≥ 0.75 | [X] | [X-0.75] | [ ] OK / [ ] BAIXO |
| **Análise** (corretude da PolicyEngine trail) | ≥ 0.70 | [X] | [X-0.70] | [ ] OK / [ ] BAIXO |
| **Planejamento** (aderência aos planos) | ≥ 0.65 | [X] | [X-0.65] | [ ] OK / [ ] BAIXO |
| **Aprendizado** (xp ganho + mastery delta) | ≥ 0.60 | [X] | [X-0.60] | [ ] OK / [ ] BAIXO |
| **Bem-estar** (Q_HE médio) | ≥ 0.65 | [X] | [X-0.65] | [ ] OK / [ ] BAIXO |

**Média Agregada:** [X.XX] (0.00 - 1.00)

---

## 4. Teste de Fogo Lite (Verdict Algorítmico)

> *Aplicar a regra macro: se o trimestre sobrevive ao teste, o sonho continua. Caso contrário, dispara revisão.*

```
SE media_agregada >= 0.70:
    verdict = PASS
ELIF media_agregada >= 0.50:
    verdict = PARTIAL
ELSE:
    verdict = FAIL
```

- **Verdict Agregado:** [ ] PASS / [ ] PARTIAL / [ ] FAIL
- **Verdict Score:** [0.00 - 1.00]
- **Decisão Automática:**
  - PASS → Continuar sonho no próximo trimestre, refinar sub-sonhos
  - PARTIAL → Aplicar Correção do Trajeto antes de próximo trimestre
  - FAIL → Reabrir o sonho para pivot/abandono

---

## 5. PolicyEngine Trail (Trimestral)

> *Como o sistema regulou esforço ao longo do trimestre?*

```
Estado inicial (Q início):  [MAINTAIN]
   ↓
Onda 1: [PUSH] por [X] dias
Onda 2: [MAINTAIN] por [X] dias
Onda 3: [REDUCE] por [X] dias
   ↓
Estado final (Q fim):       [MAINTAIN]
```

- **Dias em PUSH:** [X]
- **Dias em MAINTAIN:** [X]
- **Dias em REDUCE:** [X]
- **Dias em RECOVER:** [X]
- **Política dominante:** [A que mais dias o sistema ficou]

---

## 6. Dreams Status (consolidação dos sonhos)

| Sonho | Status no início | Status no fim | Δ | Ação |
|-------|:---:|:---:|:---:|---|
| [Sonho 1] | [ACTIVE] | [VALIDATED] | +0.20 | [Manter] |
| [Sonho 2] | [ACTIVE] | [PIVOTED] | -0.15 | [Revisar hipótese] |
| [Sonho 3] | [PIVOTED] | [ABANDONED] | -0.30 | [Encerrar] |

---

## 7. IKIGAi Alignment Check (Trimestral)

> *O trimestre que passou moveu os 4 vetores?*

| Vetor | Score Início | Score Fim | Δ | Comentário |
|-------|:---:|:---:|:---:|---|
| Passion | [0.XX] | [0.XX] | [+0.XX] | [Ex: Calistenia consistente] |
| Skill | [0.XX] | [0.XX] | [+0.XX] | [Ex: ML fundamentals dominados] |
| Market | [0.XX] | [0.XX] | [+0.XX] | [Ex: 2 networking events/mês] |
| Revenue | [0.XX] | [0.XX] | [+0.XX] | [Ex: 1 proposta freelancer] |

**IKIGAi Total:** [soma / 4] — alinhamento final = [X / 4]

---

## 8. Macro-Foco do Próximo Trimestre

> *Se PARTIAL/FAIL, defina aqui. Se PASS, apenas refine.*

1. **[Épico 1]** — [Objetivo Acionável] (IKIGAi: [vetor])
2. **[Épico 2]** — [Objetivo Acionável] (IKIGAi: [vetor])
3. **[Épico 3]** — [Objetivo Acionável] (IKIGAi: [vetor])

---

## 9. Rota de Correção (se PARTIAL ou FAIL)

> *Se o verdict for PARTIAL ou FAIL, defina aqui a correção.*

- **Diagnóstico Macro:** [Qual(is) dimensão(ões) causou(ram) o baixo score?]
- **Correção do Trajeto:**
  - **Execução baixa:** [Reduzir plano diário + aumentar accountability]
  - **Análise baixa:** [Revisar Policy trail — alarme falso?]
  - **Planejamento baixo:** [Aderência vs aspiração — recalibrar metas]
  - **Aprendizado baixo:** [MVK não atingido — investir em fundamentação]
  - **Bem-estar baixo:** [Sonenervoso / energia / foco — descansar uma onda]
- **Sub-sonhos a fechar/abrir:** [Pivots, abbandons, novas tentativas]
- **Próximo Checkpoint (Mensal):** [YYYY-MM-DD]

---

## 10. Marcos Batidos / Perdidos (Marble Track)

> *Quais marcos downstream foram cumpridos? Quais foram perdidos?*

### Marcos Batidos
- [Marco 1 — ex: "MVP do projeto X entregue"]
- [Marco 2 — ex: "Certificação Y obtida"]
- [Marco 3 — ex: "Networking Z com 50 pessoas"]

### Marcos Perdidos
- [Marco A — ex: "Publicar 12 artigos (apenas 6 publicados)"]
- [Marco B — ex: "Fechar 2 freelas (apenas 0)"]

---

## Sincronização e Fechamento

- [ ] As 3 Ondas foram consolidadas (ver `_periodos/onda-NN.md`)
- [ ] As 5 dimensões do Teste de Fogo lite preenchidas
- [ ] Verdict score calculado (0-1)
- [ ] Policy trail completo (PUSH/MAINTAIN/REDUCE/RECOVER)
- [ ] Dreams status atualizados
- [ ] IKIGAi alignment preenchido
- [ ] Top 3 épicos do próximo trimestre definidos
- [ ] Sync com `vibe_ops.db` via `life sync vault`

---

*Template: Avaliação Trimestral · v1.0 · Cluster PLAN (Estratégico) · IKIGAi Sys-01 · 2026-06-26*
