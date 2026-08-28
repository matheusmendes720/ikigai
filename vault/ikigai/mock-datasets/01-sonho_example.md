---
type: period_report
period: sonho
template_version: 1.0
ikigai_cluster: plan
entity_type: period_report
date_start: 2026-07-06
date_end: 2027-12-31
sonho_id: marina.climate-tech-lead.2027
ikigai_vector: passion
xp_gained: 0
mastery_delta: 0
verdict: ACTIVE
verdict_score: 0.62
policy_recommendation: PUSH
parent_period: null
status: active
tags: [period/sonho, ikigai/plan, falsifiable, persona/marina, horizon/18m]
---

# Sonho: Become a Tech Lead at a Climate-Tech Startup

> **Horizonte:** 18 meses (2026-07-06 → 2027-12-31) · **Cluster:** PLAN (Estratégico) · **Persona:** Marina Souza
>
> Vinculado a: `02-trimestral_example.md` (Q3-2026, Q4-2026) · `01-sonho-2027-q1.md` (forward).
> Este é o sonho root; todos os trimestres descendentes herdam o `sonho_id: marina.climate-tech-lead.2027`.

---

## 1. Definição do Sonho (Hipótese Falseável — Axis 1)

- **Título do Sonho:** *"Become a tech lead at a climate-tech startup within 3 years, while sustaining 8h sleep and 3x/week training for a half-marathon in 2027."*
- **Hipótese (texto — 142 caracteres):** *"Posso conquistar uma vaga de tech lead em climate-tech, com salário ≥ R$ 28k, mantendo sono ≥ 7.5h e treino físico 3×/semana, até Dez/2027."*
- **Horizonte:** 2026-07-06 → 2027-12-31 (18 meses, 547 dias)
- **IKIGAi Vetor Principal:** **Passion** — climate-tech combina impacto + skill técnico
- **KPIs de Saída (definição de "done"):**
  1. **Receber ≥ 3 ofertas** de empresas climate-tech (carvão, energia, agro-tech verde)
  2. **Construir portfólio público** com 1 demo interno até 2026-09-30 + 1 projeto green OSS até 2027-06-30
  3. **Manter Q_HE ≥ 0.65 por 6 meses consecutivos** durante todo o horizonte (sem burnout)

---

## 2. Critério de Falsificação (Kill Switch — Axis 1)

- **Janela de Medição:** 547 dias (2026-07-06 → 2027-12-31); sub-checagens a cada trimestre.
- **Threshold de Evidência:** Falsifica-se se **ocorrer uma das três condições abaixo**:
  1. **0 entrevistas em climate-tech** após 12 meses (2027-07-06) E completion_rate < 0.50 nos trimestres intermediários;
  2. **Q_HE < 0.45 sustentado por > 30 dias** consecutivos (burnout estrutural);
  3. **Lesão ou doença crônica** que impeça treino 3×/semana (half-marathon fica impossível).
- **Data do Kill Switch:** **2027-12-31** (limite do horizonte; o sistema dispara avaliação automática em `life sync vault --date 2027-12-31`).
- **Ação ao Atingir Threshold:**
  - [ ] Abandono total — se FALSIFIED + (1) E Q_HE < 0.45
  - [x] **Pivot** — se FALSIFIED + (1) isoladamente: revisar hipótese (talvez startup → Scale-up established)
  - [ ] Extensão de prazo — se PIVOTED + mercado ainda aquecido
  - [x] Subdivisão — quebrar em sub-sonhos ("interview-ready" / "demo-shipped" / "training-finished")

---

## 3. Indicadores Leading vs Lagging (Axis 2)

### 3.1 Leading Indicators (comportamento — você controla)

| Indicador | Meta (semanal) | Medição |
|----------|:---:|---------|
| Pomodoros Deep Work climate-tech (estudo + demo) | ≥ 18 | `pomodoros_climate_tech / week` |
| PRs mergeados em projetos portfolio | ≥ 2 | `git_prs_merged / week` |
| Networking outreach (LinkedIn + cold email) | ≥ 4 | `outreach_sent / week` |
| Horas de sono ≥ 7.5h | ≥ 6 dias | `sleep_log / week` |
| Treinos físicos completados | 3 / semana | `training_log / week` |
| Leituras (papers / livros climate-tech) | ≥ 2 / semana | `reading_log / week` |

### 3.2 Lagging Indicators (impacto — mercado devolve)

| Indicador | Meta (trimestral) | Medição |
|----------|:---:|---------|
| Aplicações enviadas a climate-techs | ≥ 30 / quarter | `applications / quarter` |
| Entrevistas técnicas (todas as fases) | ≥ 6 / quarter | `interviews / quarter` |
| Recrutadores respondendo | ≥ 8 / quarter | `recruiter_responses / quarter` |
| Ofertas verbais/escritas | ≥ 3 (acumulado) | `offers_received / quarter` |
| Seguidores LinkedIn (rede climate-tech) | ≥ 1500 | `linkedin_followers / quarter` |

---

## 4. Gatilhos de Refatoração (Axis 3)

- [x] **Saúde:** Lesão ou burnout sustentado (>2 semanas em RECOVER Policy) — ação: pivotar para sub-sonho "training-finished" isolado.
- [x] **Mercado:** IPO climate-tech adiado > 6 meses, layoffs em massa no setor (2027-Q2) — ação: pivotar para "engineering manager" em empresas established.
- [x] **Família:** Nascimento de filho, mudança para outro estado, perda familiar — ação: subdividir sonho em 2 ondas menores (impacto profissional reduzido).
- [x] **Energia Mental:** Queda sustentada de Q_HE < 0.45 por > 30 dias — ação: triggering obrigatório de pivô.
- [ ] Hipótese invalidada externamente — ainda não observado.

---

## 5. Verdict Computado (Algoritmo 3-Axis)

> **Estado atual:** horizonte ativo desde 2026-07-06 (26 dias transcorridos no momento da redação, 2026-08-01).

```
HOJE = 2026-08-01 (26 dias após início)
kill_switch_date = 2027-12-31 (ainda não atingido)

leading_met (Q3 parcial, 4 semanas): 78% (próximo do threshold 0.80)
lagging_met: 22% (Q3 acabado de começar; aplicando conservador)
refactor_trigger_detected: false

ENTÃO:
    verdict = ACTIVE
```

- **Status Atual:** [x] **ACTIVE**
- **Verdict Score:** **0.62** (= 0.5 × 0.78 + 0.5 × (1 − 0.78) = 0.5 × 0.78 + 0.5 × 0.22)
  - Leading 0.78 × 0.5 = 0.390
  - Lagging gap 0.78 × 0.5 = 0.390
  - (Refactor penalty: 0 — nenhum gatilho ativo)
- **Próxima Avaliação Automática:** **2026-09-30** (fim do Q3-2026; trimestral consolidado dispara verdict de meio-de-horizonte)

---

## 6. KPIs Macro (Trimestral — Teste de Fogo lite)

> *Aplicado ao Q3-2026 (parcial, semanas 1-4 de 13). Resultado reflete o que está consolidado até 2026-08-01.*

| Dimensão | Meta | Realizado | Gap | Verdict Parcial |
|----------|:---:|:---:|:---:|:---:|
| **Execução** (completion rate médio) | ≥ 0.75 | **0.83** | +0.08 | [x] OK |
| **Análise** (policy corretude) | ≥ 0.70 | **0.74** | +0.04 | [x] OK |
| **Planejamento** (adherence to plans) | ≥ 0.65 | **0.71** | +0.06 | [x] OK |
| **Aprendizado** (xp ganho + mastery delta) | ≥ 0.60 | **0.58** | −0.02 | [ ] BAIXO (gap mínimo) |
| **Bem-estar** (Q_HE médio) | ≥ 0.65 | **0.69** | +0.04 | [x] OK |

**Média das 5 dimensões:** (0.83 + 0.74 + 0.71 + 0.58 + 0.69) / 5 = **0.71**
**Verdict Agregado:** [x] **PARTIAL** (0.50 ≤ 0.71 < 0.70? NÃO — 0.71 ≥ 0.70, então PASS)
  - Correção de leitura: 0.71 ≥ 0.70 → **PASS** (mas apertado, com gap no aprendizado).
- **Recomendação:** apertar Aprendizado em Q3 semanas 5-13 (Onda 2 e Onda 3).

---

## 7. Status dos Dreams Vinculados (sub-sonhos Q3-2026)

| Sub-sonho | Status | Verdict | Próxima Ação |
|-----------|:---:|:---:|---|
| `marina.climate-internal-demo.2026q3` | ACTIVE | 0.71 | Continue (Onda 1 em curso) |
| `marina.first-climate-interview.2026q3` | ACTIVE | 0.45 | Empurrar para Q3 semanas 9-13 |
| `marina.half-marathon-prep.2027` | ACTIVE | 0.68 | Manter 3x treino/semana |
| `marina.leadership-coaching-pilot.2026q4` | DRAFT | — | Aberto em 2026-10 |

---

## 8. IKIGAi Alignment Check

> *Snapshot de hoje (2026-08-01) e meta do horizonte (2027-12-31).*

| Vetor | Peso (1-5) | Score Atual (0-1) | Contribuição (peso × score) | Score Alvo (2027-12-31) | Δ necessário |
|-------|:---:|:---:|:---:|:---:|:---:|
| Passion | 5 | 0.68 | 3.40 | 0.80 | +0.12 |
| Skill | 5 | 0.74 | 3.70 | 0.85 | +0.11 |
| Market | 4 | 0.48 | 1.92 | 0.70 | +0.22 |
| Revenue | 3 | 0.60 | 1.80 | 0.80 | +0.20 |
| Course | 3 | 0.55 | 1.65 | 0.70 | +0.15 |

**IKIGAi Total atual:** (3.40 + 3.70 + 1.92 + 1.80 + 1.65) / 20 = **0.624**
**IKIGAi Total alvo (2027-12-31):** 4.00 + 4.25 + 2.80 + 2.40 + 2.10 = **15.55 / 20 = 0.778**
**Gap IKIGAi:** +0.154 ao longo de 17 meses restantes (~0.009 por mês, atingível).

**Alinhamento qualitativo:**
- Passion + Skill já estão bem encaminhados (foco em demo + entrevista técnica).
- **Market** é o vetor de maior gap — Marina precisa expor-se a mais eventos do setor, ler mais papers, conversar com fundadores.
- Revenue só vai subir se houver ofertas concretas (lagging indicator puro).
- Course requer o coaching pilot em Q4-2026.

---

## 9. Macro-Foco do Próximo Trimestre (Q3-2026)

1. **Internal Demo Ready** — Concluir a demo interna de climate-tech (Pitch de 12min + repo GitHub público) até 2026-09-15 (IKIGAi: **Skill** + **Passion**).
2. **Primeira Entrevista Climate-Tech** — Conseguir ≥ 1 processo seletivo técnico (Phone Screen ou Onsite) em climate-tech até 2026-09-30 (IKIGAi: **Market**).
3. **Half-Marathon Long Run 18km** — Sustentar 3× treino/semana + completar Long Run de 18km em 2026-08-30 (IKIGAi: **Course** / physiology).

---

## 10. Rota de Correção (caso PARTIAL ou FAIL no fim do trimestre)

> *Q3-2026 está em PARTIAL (0.71) — gap mínimo em Aprendizado. Plano Q4 já endereça.*

- **Diagnóstico:** Onda 1 (15 dias) sobrecarregou execução + planejamento, mas aprendizado caiu.
- **Correção do Trajeto:** Onda 2 (semanas 6-9) prioriza leitura técnica deliberada: 1 paper/semana com anotações atômicas, 1 curso curto (Sustainable Software Design).
- **Novos Indicadores:** Adicionar `reading_notes_atomized / week` (≥ 3) e `course_modules_completed / week` (≥ 2).
- **Sub-sonhos:** Adiar `marina.leadership-coaching-pilot.2026q4` para Q1-2027 se Q3 não entregar a demo.
- **Próximo Checkpoint:** **2026-09-30** (veredito Q3 final).

---

## Sincronização e Fechamento

- [x] Hipótese escrita com ≥ 10 caracteres (142 chars ✓)
- [x] Kill switch data definida e ≤ horizonte + 90 dias (2027-12-31 = horizonte exato)
- [x] Leading + lagging indicators têm metas mensuráveis (6 leading + 5 lagging)
- [x] Refactor triggers listados (≥ 1, atualmente 4)
- [x] Verdict score calculado (0.62)
- [x] IKIGAi alignment preenchido (5 vetores)
- [x] Top 3 épicos do próximo trimestre definidos
- [x] Sub-sonhos atualizados (3 ACTIVE + 1 DRAFT)
- [ ] Sync com `vibe_ops.db` via `life sync vault` — agendado para 2026-09-30 (não diário)

---

*Template: Sonho · v1.0 · Cluster PLAN (Estratégico) · Persona: Marina Souza · 2026-07-02*
