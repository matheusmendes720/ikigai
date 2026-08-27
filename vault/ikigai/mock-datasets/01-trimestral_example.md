---
type: period_report
entity_type: period_report
period: quarterly
id: quarterly-2026-Q3
template_role: aggregate_root
template_version: 1.0
ikigai_cluster: plan

date_start: 2026-07-06
date_end: 2026-09-30

verdict: ACTIVE
verdict_score: 0.71

# Hierarquia do trimestre (preenchida na execucao)
sonho_id: marina.climate-tech-lead.2027
parent_period: marina.climate-tech-lead.2027
# IKIGAi alignment snapshot
ikigai_vector: passion
ikigai_score_inicio: 0.66
ikigai_score_fim: 0.71

# Sync metadata
vault_path: .omo/ikigai/marina-souza/01-trimestral-2026-Q3.md
vault_hash: sha256:placeholder-will-fill-on-first-sync
status: active
tags: [period/quarterly, ikigai/plan, template/quarterly-planning, persona/marina, ano/2026, q/Q3]
---

# Planejamento Trimestral: Q3 2026 — Climate-Tech Internal Demo + First Interview

> **Horizonte:** 90 dias (2026-07-06 → 2026-09-30) · **Cluster:** PLAN (Estrategico) · **Persona:** Marina Souza
>
> Sonho pai: `00-sonho_example.md` · `sonho_id: marina.climate-tech-lead.2027`
> Ondas filhas: `onda-01-climate-tech-internal-demo`, `onda-02-climate-interview-prep`, `onda-03-half-marathon-block`
> Regimes previstos: **PUSH para Q3 (Onda 1+2) → MAINTAIN para Q4 (Onda 3, decisão promo vs oferta)**

---

## 1. Sondagem (Deteccao de Contexto)

### 1.1 Estado Atual do Sistema
- **Q_HE atual (media 7 dias):** **0.69** (rolling 7-day; weekly review 03 confirmou 0.71 mas 4 dias pioraram)
- **Ultima Policy decision:** **MAINTAIN** (week 1 fechou em PARTIAL → recomendou MANTER)
- **Ultima evaluation trimestral:** Q2-2026 (PASS, 0.78) — boa base, sistema descansado
- **Trend velocity (pomodoros/semana):** **+12 vs Q2** (42 → 54 pomodoros/semana)

### 1.2 Sonhos Ativos (vinculados)

| Sonho | Status | Kill Switch | Verdict Score | Vetor IKIGAi |
|-------|--------|-------------|---------------|---------------|
| `marina.climate-tech-lead.2027` | ACTIVE | 2027-12-31 | 0.62 | passion |
| `marina.half-marathon-prep.2027` | ACTIVE | 2027-09-15 | 0.68 | course |

### 1.3 Capacidade Disponivel
- **Horas liquidas de foco / semana:** **28h** (5 dias × 5.6h líquido, descontando 1h almoço + 0.4h meetings)
- **Histerese atual:** **5 dias** em MAINTAIN pós-Q2 PASS
- **Risco de burnout (Q_HE<0.45 sustentado):** **BAIXO** (Q_HE 0.69, sono médio 7.6h)

---

## 2. Definicao Estrategica (Sonho → Trimestral)

### 2.1 Hipotese Falsificavel (Axis 1 — Kill Switch)
- **Hipotese:** *"Concluo uma demo interna de climate-tech (12-min pitch + repo público) e recebo pelo menos 1 processo seletivo técnico (phone screen ou onsite) em climate-tech até 2026-09-30."*
- **Criterio de falsificacao:** `demo_published == false` AND `interviews_climate_tech < 1` em 2026-09-30 23:59 BRT.
- **Data do Kill Switch:** **2026-09-30 23:59 BRT** (trimester end; verdict FAIL dispara subdivisão do sonho).
- **Janela de medicao:** 87 dias (2026-07-06 → 2026-09-30).
- **Status atual:** ACTIVE.

### 2.2 Leading vs Lagging Indicators (Axis 2)

**Leading (comportamento, controlavel):**
| Indicador | Meta/semana | Verificacao |
|-----------|-------------|-------------|
| Pomodoros Deep Work em climate-tech (demo + estudo) | ≥ 18 | `pomodoros_climate_tech / week` |
| PRs mergeados no repo da demo | ≥ 2 | `git_prs_merged / week` (repo: `marina/climate-impact-sim`) |
| Outreach para fundadores climate-tech (LinkedIn DM) | ≥ 4 | `outreach_sent / week` |
| Treinos físicos completados | ≥ 3 | `training_log / week` |
| Sono ≥ 7.5h | ≥ 6 noites | `sleep_log / week` |

**Lagging (resultado, fora de controle):**
| Indicador | Meta/trimestre | Verificacao |
|-----------|----------------|-------------|
| Demo publicada (repo público + pitch gravado) | 1 | `demo_published / quarter` |
| Phone screens em climate-tech | ≥ 3 | `phone_screens / quarter` |
| Onsites em climate-tech | ≥ 1 | `onsites / quarter` |
| Recrutadores climate-tech respondendo | ≥ 6 | `recruiter_responses / quarter` |
| Long Run ≥ 18km completado | 1 | `long_runs_completed / quarter` |

### 2.3 Gatilhos de Refatoracao (Axis 3)
- [x] Saude: lesao (panturrilha no Long Run) — já ocorreu em 2026-08-15, recuperado
- [x] Mercado: IPO Mosaic Forest adiado — não impacta diretamente Marina ainda
- [ ] Familia: nenhum gatilho
- [x] Energia Mental: Q_HE < 0.45 sustentado > 30 dias — gatilho configurado, nunca disparado
- [ ] Hipotese invalidada externamente — não observado

---

## 3. Proporcao 5x3x3 (5 dias → 3 semanas → 3 meses)

### 3.1 Calculo Matematico
```
Execucao (5 dias uteis)   →  Relatorio Diario        →  aggregation: completion_rate
Analise  (3 semanas)       →  Revisao Semanal         →  aggregation: policy_trail
Planejamento (3 meses)     →  Avaliacao Trimestral    →  aggregation: teste_de_fogo
```

### 3.2 Distribuicao Alocada
| Dimensao | Peso | Alvo Mensal | Status Q (até 2026-08-01) |
|----------|------|-------------|---------------------------|
| Execucao (completion_rate) | 0.50 | >= 0.75 | [x] 0.83 (meta batida) |
| Analise (policy_accuracy)   | 0.20 | >= 0.70 | [x] 0.74 (meta batida) |
| Planejamento (adherence)    | 0.15 | >= 0.65 | [x] 0.71 (meta batida) |
| Aprendizado (xp + mastery)   | 0.10 | >= 0.60 | [ ] 0.58 (gap -0.02) |
| Bem-estar (Q_HE avg)         | 0.05 | >= 0.65 | [x] 0.69 (meta batida) |

**Teste de Fogo parcial (4 semanas):** média = **0.71** → PARTIAL (ver §6 do sonho).
Recomendação: apertar Aprendizado em Onda 2 (semanas 6-9).

### 3.3 Formulas Explcitas
```
completion_rate = tarefas_concluidas / tarefas_planejadas
verdict_score   = (media_teste_fogo * 0.5) + (leading_cumprido * 0.3) + (histerese_sustentada * 0.2)
periodic_proportions = Execucao(0.50) : Analise(0.20) : Planejamento(0.15) : Aprendizado(0.10) : Bem-estar(0.05)
```

**Aplicado ao Q3-2026 parcial:**
- media_teste_fogo = 0.71
- leading_cumprido = 0.78 (4/5 leading acima da meta em 4 semanas)
- histerese_sustentada = 0.65 (Q_HE médio últimos 28 dias = 0.69 normalizado para escala 0-1)
- **verdict_score** = (0.71 × 0.5) + (0.78 × 0.3) + (0.65 × 0.2) = 0.355 + 0.234 + 0.130 = **0.719** ≈ **0.72**

---

## 4. Desdobramento em 3 Ondas (15 dias uteis cada)

### 4.1 Onda 1 (2026-07-06 → 2026-07-24, 15 dias úteis)

> **Ver exemplo detalhado:** `02-onda_example.md`

- **Tema:** **Climate-Tech Internal Demo — Fundamentação Técnica**
- **Goal unico:** *"Repo público `marina/climate-impact-sim` com MVP funcional + apresentação 12-min gravada."*
- **3 Semanais vinculadas:**
  - Semana 1 (2026-07-06 → 2026-07-12): Estudo de stack (Python + Polars + Streamlit) + prototipagem
  - Semana 2 (2026-07-13 → 2026-07-19): Implementação MVP + primeiro deploy
  - Semana 3 (2026-07-20 → 2026-07-24): Pitch gravado + publicação GitHub
- **Verdict esperado:** **CONTINUE_WAVE** (já executada; ver `02-onda_example.md`)
- **Verdict real:** **CONTINUE_WAVE** (verdict_score 0.83)
- **Onda 2 herda:** Repo MVP + script do pitch + 150 pomodoros acumulados

### 4.2 Onda 2 (2026-07-27 → 2026-08-14, 15 dias úteis)

- **Tema:** **Climate Interview Prep + Networking Blitz**
- **Goal unico:** *"Receber ≥ 1 phone screen em climate-tech + adicionar ≥ 4 fundadores ao network ativo."*
- **3 Semanais vinculadas:**
  - Semana 4 (2026-07-27 → 2026-08-02): Leitura de 2 papers + curso Sustainable Software Design (módulos 1-3)
  - Semana 5 (2026-08-03 → 2026-08-09): Outreach intensivo (≥ 30 DMs LinkedIn) + aplicação para 5 vagas
  - Semana 6 (2026-08-10 → 2026-08-14): Mock interview técnico (com Vinicius, ex-googler) + ajustes
- **Verdict esperado:** **CONTINUE_WAVE**
- **Onda 3 herda:** Network de 4 fundadores, 1 phone screen marcado, 8 papers anotados

### 4.3 Onda 3 (2026-08-17 → 2026-09-30, 33 dias úteis)

- **Tema:** **Half-Marathon Block + Demo Polish + Q4 Decision Framework**
- **Goal unico:** *"Completar 1 long-run 18km + publicar case study da demo + rascunho do framework de decisão Q4."*
- **3 Semanais vinculadas:**
  - Semana 7-8 (2026-08-17 → 2026-08-30): Half-marathon training peak (3×/semana treino + 1 long run 18km em 2026-08-30)
  - Semana 9-10 (2026-09-01 → 2026-09-13): Case study publicado no blog técnico + 1 paper final
  - Semana 11-13 (2026-09-14 → 2026-09-30): Verdict Q3 + rascunho Q4 trimestral
- **Verdict esperado:** **CONTINUE_WAVE**
- **Handoff para Q4-2026:** Demo publicada + interview(s) agendada(s) + half-marathon prep em fase 2 (volume)

---

## 5. Teste de Fogo (5 Dimensoes x 4 Semanas)

> *Aplicado às 4 semanas transcorridas em 2026-08-01. W5-W13 ainda no futuro.*

| Dimensao | W1 Target | W2 Target | W3 Target | W4 Target | Real W1 | Real W2 | Real W3 | Real W4 |
|----------|-----------|-----------|-----------|-----------|---------|---------|---------|---------|
| **Execucao** (completion_rate) | >= 0.70 | >= 0.75 | >= 0.80 | >= 0.85 | **0.86** | 0.78 | 0.92 | 0.83 |
| **Analise** (policy_accuracy)  | >= 0.65 | >= 0.70 | >= 0.70 | >= 0.75 | **0.71** | 0.74 | 0.78 | 0.71 |
| **Planejamento** (adherence)    | >= 0.60 | >= 0.65 | >= 0.70 | >= 0.70 | **0.69** | 0.74 | 0.70 | 0.71 |
| **Aprendizado** (xp + mastery)  | >= 0.55 | >= 0.60 | >= 0.65 | >= 0.70 | **0.55** | 0.59 | 0.57 | 0.61 |
| **Bem-estar** (Q_HE avg)        | >= 0.60 | >= 0.65 | >= 0.70 | >= 0.70 | **0.66** | 0.73 | 0.74 | 0.65 |

**Realizado agregado (W1-W4):**
- Execucao média: (0.86 + 0.78 + 0.92 + 0.83) / 4 = **0.847**
- Analise média: (0.71 + 0.74 + 0.78 + 0.71) / 4 = **0.735**
- Planejamento média: (0.69 + 0.74 + 0.70 + 0.71) / 4 = **0.710**
- Aprendizado média: (0.55 + 0.59 + 0.57 + 0.61) / 4 = **0.580**
- Bem-estar média: (0.66 + 0.73 + 0.74 + 0.65) / 4 = **0.695**

**Teste de Fogo geral (5 dims):** (0.847 + 0.735 + 0.710 + 0.580 + 0.695) / 5 = **0.713**

> ⚠️ **Aprendizado abaixo da meta (0.58 < 0.60).** Adiar `reading_notes_atomized` para Onda 2 semanas 4-6 (já planejado).

---

## 6. Top 3 Epicos do Trimestre (Goal-aligned)

1. **`EPIC-CLIMATE-DEMO`** — Publicar `marina/climate-impact-sim` v1.0 com pitch 12-min gravado até 2026-09-15. **(IKIGAi: passion + skill)**
2. **`EPIC-CLIMATE-FIRST-INTERVIEW`** — Receber ≥ 1 phone screen técnico em climate-tech até 2026-09-30. **(IKIGAi: market + revenue)**
3. **`EPIC-HALF-MARATHON-BLOCK`** — Completar long run 18km em 2026-08-30 + manter 3× treino/semana por 13 semanas. **(IKIGAi: course)**

---

## 7. Capacity Planning (Histerese + 5x3x3)

### 7.1 Histerese Asymmetric
- **Days up (MAINTAIN → PUSH):** >= 3 dias com Q_HE >= 0.85
- **Days down (MAINTAIN → REDUCE):** >= 2 dias com Q_HE < 0.65
- **Emergency (RECOVER):** Q_HE < 0.30 OU infractions >= 3

### 7.2 Carga Planejada vs Capacidade
- **Pomodoros planejados / semana:** **48** (16 clima-tech + 12 portfolio + 8 networking + 12 treino+estudo)
- **Horas de Deep Work / dia:** **5.6h** (meta)
- **Taxa ocupacao:** 48 × 1h / (5 × 5.6h) = **171%** — ⚠️ impossível! Recalibrar para **30 pomodoros/semana**.

> ⚠️ **Ação corretiva já em curso (2026-07-08):** meta de pomodoros reduzida de 48 → 30/semana; o excedente virou buffer.

---

## 8. Criterios de Saida (End-of-Quarter)

| Criterio | Meta | Medicao |
|----------|------|---------|
| Teste de Fogo (media 5 dims) | >= 0.70 | Avg(W1+W2+...+W13) — parcial: 0.713 (PASS parcial) |
| Leading indicators cumpridos | >= 80% | sum(actual / target) — parcial: 78% (borderline) |
| Lagging indicators cumpridos | >= 60% | sum(actual / target) — parcial: 22% (esperado, lagging atrasado) |
| Histerese sustained | Q_HE >= 0.65 | mean(Q_HE last 30 days) — atual: **0.69** (PASS) |
| Sonho verdict | FALSIFIED ou VALIDATED | projeção: ainda ACTIVE |

---

## 9. Verdict Computado (Algoritmo)

> *Aplicação da fórmula ao estado parcial em 2026-08-01 (após 4 semanas de 13):*

```
media_teste_fogo = 0.71 (W1-W4 realizado)
leading_cumprido = 0.78

media_teste_fogo (0.71) >= 0.70 AND leading_cumprido (0.78) >= 0.50?
    → SIM (0.71 >= 0.70 E 0.78 >= 0.50)

ENTÃO:
    verdict = PASS  (justo, mas PASS)
```

- **Verdict parcial:** [x] **PASS** (borderline; precisa de Aprendizado em W5-W13)
- **Verdict Score:** **0.72** (= 0.5 × 0.71 + 0.3 × 0.78 + 0.2 × 0.65)
- **Acao para proximo trimestre (Q4-2026):**
  - [x] CONTINUE — se Q3 fechar PASS e ≥ 1 lagging cumprido
  - [ ] CORRECT — se Q3 fechar PARTIAL
  - [ ] PIVOT — se leading < 50% ou burnout detectado

---

## 10. Recalibracao (Handoff para Q4-2026)

- [ ] Sonho atualizado (validado / pivotado / abandonado) — agendado 2027-12-31
- [ ] Novas hipoteses candidatas para Q4 — rascunho após 2026-09-30
- [ ] Trimestral Q4-2026 rascunhado: *"Q4 bet: Decide between staying (tech-lead promo) vs moving (climate-tech offer)"*
- [x] Daily Reflection consolidada em Relatorio Trimestral (em curso)
- [ ] Sync com `vibe_ops.db` via `life sync vault --folder _templates_periodos` (2026-09-30)

---

## Sincronizacao e Fechamento

- [x] YAML frontmatter validado contra ADR-006
- [x] Verdict score calculado (0.72)
- [x] IKIGAi alignment preenchido (passion: 0.66 → 0.71)
- [x] Histerese tracking ativo (5 dias MAINTAIN, transição para PUSH em 2026-07-20 após Onda 1 verdict CONTINUE)
- [ ] Sync com DB via `life sync vault` — agendado 2026-09-30

---

*Template: Planejamento Trimestral · v1.0 · Cluster PLAN · Persona: Marina Souza · 2026-07-02 · Q3 2026 (parcial: 4/13 semanas)*
