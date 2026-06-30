---
type: period_report
entity_type: period_report
period: quarterly
id: quarterly-review-YYYY-QN
template_role: aggregate_review
template_version: 1.0
ikigai_cluster: plan

date_start: YYYY-MM-DD
date_end: YYYY-MM-DD

verdict: PASS
verdict_score: 0.0

sonho_id:
parent_period:
ikigai_vector: passion
ikigai_score_inicio: 0.0
ikigai_score_fim: 0.0

vault_path:
vault_hash:
status: draft
tags: [period/quarterly, ikigai/plan, template/quarterly-review]
---

# Avaliacao Trimestral: Q[N] [YYYY]

> **Horizonte:** 90 dias **Cluster:** PLAN (Estrategico) **Tipo:** Revisao + Recalibracao
>
> Este template fecha o ciclo trimestral agregando os 3 Ondas + 9 Semanais + 45 Diarios.

---

## 1. Agregacao Automatica (Inputs)

### 1.1 Ondas (3 esperadas)
- **Onda 1:** id=[id], verdict=[verdict], score=[X], children=[N]
- **Onda 2:** id=[id], verdict=[verdict], score=[X], children=[N]
- **Onda 3:** id=[id], verdict=[verdict], score=[X], children=[N]

### 1.2 Semanais (9 esperadas)
- Total Semanais: [N]
- PASS: [N], PARTIAL: [N], FAIL: [N]

### 1.3 Diarios (45 esperados, +- 5 work weeks x 5 dias)
- Total Diarios: [N]
- Media completion_rate: [0.XX]
- Media Q_HE: [0.XX]
- Total pomodoros: [N]

---

## 2. Teste de Fogo (5 Dimensoes x 4 Semanas x 3 Ondas)

### 2.1 Matriz Agregada
| Dimensao | W1 | W2 | W3 | W4 | Onda1 | Onda2 | Onda3 | Media | Target | Gap |
|----------|----|----|----|----|-------|-------|-------|-------|--------|-----|
| **Execucao** (completion) | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.75 | [-/+] |
| **Analise** (policy trail) | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.70 | [-/+] |
| **Planejamento** (adherence) | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.65 | [-/+] |
| **Aprendizado** (xp + mastery) | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.60 | [-/+] |
| **Bem-estar** (Q_HE) | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX | 0.65 | [-/+] |

### 2.2 Agregacao Final
- **Media 5 dimensoes:** [0.XX]
- **Target cumprido:** [SIM/NAO -- se media >= 0.70]

---

## 3. IKIGAi Alignment Delta (3-Axis)

### 3.1 Vetores IKIGAi
| Vetor | Score Inicio | Score Fim | D | Comentario |
|-------|--------------|-----------|---|------------|
| Passion | 0.XX | 0.XX | [+/-X.XX] | [Ex: Calistenia consistente] |
| Skill | 0.XX | 0.XX | [+/-X.XX] | [Ex: ML fundamentals dominados] |
| Market | 0.XX | 0.XX | [+/-X.XX] | [Ex: 2 networking events/mes] |
| Revenue | 0.XX | 0.XX | [+/-X.XX] | [Ex: 1 proposta freelancer] |

### 3.2 Agregacao
- **IKIGAi Total inicio:** [0.XX / 4.00]
- **IKIGAi Total fim:** [0.XX / 4.00]
- **D Total:** [+/-X.XX]
- **Vetor mais evoluido:** [Nome]
- **Vetor mais estagnado:** [Nome]

---

## 4. Dreams Status Roll-up

| Sonho | Status inicio | Status fim | D | Decisao |
|-------|:---:|:---:|:---:|---------|
| [Nome] | [ACTIVE] | [VALIDATED] | [+0.20] | [Manter / Pivotar / Abandonar] |
| [Nome] | [ACTIVE] | [PIVOTED] | [-0.15] | [Revisar hipotese] |
| [Nome] | [PIVOTED] | [ABANDONED] | [-0.30] | [Encerrar] |

### 4.1 Kill Switch Evaluation
- **Data do kill switch:** [YYYY-MM-DD]
- **Status atual:** [ATINGIDO / NAO ATINGIDO]
- **Janela de medicao:** [X dias, restantes Y]
- **Acao imediata:** [ENCERRAR / RENOVAR / PIVOTAR]

---

## 5. Policy Trail (Histerese)

| Estado | Dias | Periodo |
|--------|------|---------|
| PUSH | [X] | [DD/MM-DD/MM] |
| MAINTAIN | [X] | [DD/MM-DD/MM] |
| REDUCE | [X] | [DD/MM-DD/MM] |
| RECOVER | [X] | [DD/MM-DD/MM] |

**Histerese asimetrica aplicada:**
- 3+ dias em MAINTAIN com Q_HE >= 0.85 -> promoted to PUSH
- 2+ dias em MAINTAIN com Q_HE < 0.65 -> demoted to REDUCE
- Q_HE < 0.30 OU infractions >= 3 -> emergency to RECOVER

---

## 6. Verdict Computado (Algoritmo)

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
- **Confianca:** [ALTA / MEDIA / BAIXA]

---

## 7. Recomendacao para Proximo Trimestre

### 7.1 Decisao Macro
- [ ] **CONTINUE** (manter hipotese, refinar sub-sonhos)
- [ ] **CORRECT TRAJECTORY** (ajustar Teste de Fogo, realocar 5x3x3)
- [ ] **KILL WAVE** (abandonar sonho, pivotar)
- [ ] **PIVOTED** (reformular hipotese, novo sonho)

### 7.2 Razao
[2-3 paragrafos justificando a recomendacao acima]

### 7.3 Top 3 Epicos do Proximo Trimestre
1. **[Epico 1]** -- [Objetivo Claro e Acionavel] (IKIGAi: [vetor])
2. **[Epico 2]** -- [Objetivo Claro e Acionavel] (IKIGAi: [vetor])
3. **[Epico 3]** -- [Objetivo Claro e Acionavel] (IKIGAi: [vetor])

---

## 8. Handoff para Q+1

- [ ] Sonho atualizado (validado / pivotado / abandonado)
- [ ] Novas hipoteses candidatas para Q+1 listadas
- [ ] 3 Ondas do Q+1 rascunhadas (tema + goal)
- [ ] Daily Reflection consolidada
- [ ] Sync com `vibe_ops.db` via `life sync vault --folder _templates_periodos`
- [ ] Notebooks PRs / referencias externas linkadas

---

## Sincronizacao e Fechamento

- [ ] YAML frontmatter validado
- [ ] Verdict score calculado
- [ ] IKIGAi delta registrado
- [ ] Policy trail completo
- [ ] 8 sub-tarefas acima concluidas

---

*Template: Avaliacao Trimestral v1.0 **Cluster PLAN ** IKIGAi Sys-01 ** 2026-06-26*
