---
type: period_report
period: onda
template_version: 1.0
ikigai_cluster: plan
entity_type: period_report
date_start: 2026-07-06
date_end: 2026-07-24
sonho_id: marina.climate-tech-lead.2027
ikigai_vector: skill
xp_gained: 312
mastery_delta: 0.08
verdict: CONTINUE_WAVE
verdict_score: 0.83
policy_recommendation: PUSH
parent_period: quarterly-2026-Q3
status: closed
tags: [period/onda, ikigai/plan, micro-fase, persona/marina, onda/01, demo/climate-internal]
---

# Onda 01: Climate-Tech Internal Demo — Fundamentação Técnica

> **Horizonte:** 15 dias úteis (3 semanas) · **Cluster:** PLAN (Tático) · **Persona:** Marina Souza
>
> Vinculado a: `00-sonho_example.md` (sonho pai) · `01-trimestral_example.md` (trimestre pai)
> Filhas: `03-revisao-semanal_example.md` (semana 01) · `semana-02` (W2) · `semana-03` (W3)
> Status: **FECHADA** em 2026-07-24 com verdict CONTINUE_WAVE.

---

## 1. Identificação da Onda

- **Onda ID:** `onda-01-climate-tech-internal-demo`
- **Período:** 2026-07-06 → 2026-07-24 (15 dias úteis: 3 semanas completas)
- **Tema Central:** Construir o MVP da demo interna de climate-tech + gravar pitch de 12 min
- **Sonho Pai:** `marina.climate-tech-lead.2027` (FK → `00-sonho_example.md`)
- **Trimestre Pai:** `quarterly-2026-Q3` (FK → `01-trimestral_example.md`)
- **IKIGAi Vetor:** [x] Passion  [x] Skill  [ ] Market  [ ] Revenue  (vetor primário: Skill)
- **Status:** [ ] Draft  [ ] Em Execução  [x] **Em Revisão**  [x] Fechada (2026-07-24)

---

## 2. 3 Revisões Semanais Consolidadas

> *Resumo das 3 Semanais desta onda. Para detalhes, ver `_periodos/semana-NN.md`.*

| Semana | Período | Completion Rate | Verdict Semanal | Policy Estado (final) |
|--------|---------|:---:|:---:|:---:|
| Semana 1 | 2026-07-06 → 2026-07-12 | **0.86** | [x] **PASS** | [x] PUSH |
| Semana 2 | 2026-07-13 → 2026-07-19 | **0.78** | [ ] PARTIAL | [x] MAINTAIN |
| Semana 3 | 2026-07-20 → 2026-07-24 | **0.92** | [x] **PASS** | [x] PUSH |

**Completion Rate Médio da Onda:** (0.86 + 0.78 + 0.92) / 3 = **0.853** ≈ **0.85**

---

## 3. Diagnóstico de Gaps (por dimensão)

> *Onde a onda perdeu força?*

| Dimensão | Meta | Realizado | Gap | Severidade |
|----------|:---:|:---:|:---:|:---:|
| Execução (pomodoros concluídos) | 90 (6/dia × 15 dias) | **84** | −6 | [ ] H  [x] M  [ ] L |
| Análise (correção de rota — policy_accuracy) | ≥ 0.72 (média) | **0.74** | +0.02 | [ ] H  [ ] M  [x] L |
| Aprendizado (MVK atingido) | 1 pilar subir nível (Python→Polars mastery) | **0.7** (parcial — Polars dominado, Streamlit básico) | −0.30 | [ ] H  [x] M  [ ] L |
| Bem-estar (Q_HE médio) | 0.65 (sustentado) | **0.71** | +0.06 | [ ] H  [ ] M  [x] L |

> ⚠️ **Gaps reais:** Execução (−6 pomodoros, perdido na W2 pelo burnout do meetup de quarta) e Aprendizado (Streamlit ficou em "uso supervisionado", não "domínio pleno"). Bem-estar e análise dentro da meta.

---

## 4. Verdict Computado (Algoritmo da Onda)

```
completion_medio = 0.85

SE 0.85 >= 0.75:
    verdict = CONTINUE_WAVE     ← TOMAMOS ESTE RAMO
```

- **Verdict:** [x] **CONTINUE_WAVE**
- **Verdict Score:** **0.83**
  - (0.85 × 0.5) + (0.85 × 0.3) + (0.65 × 0.2) = 0.425 + 0.255 + 0.130 = 0.810 → normalizado para **0.83** (clamp)
- **Policy Recommendation para próxima onda:** [x] **PUSH** (continuar investindo; não desacelerar)

---

## 5. Ações Corretivas (NÃO se aplica — verdict CONTINUE, mas registrar mesmo assim)

> *Como CONTINUE_WAVE, sem correções estruturais obrigatórias. Apenas tightening.*

- **Causa Raiz do gap de execução:** Queda de energia na quarta-feira de W2 (meetup pós-trabalho que durou 3h).
- **Mudanças Estruturais (opcionais, melhorar o que já funciona):**
  - "Time blocking de manhã (06:30-12:00) é sagrado — defender de reuniões pós-12h"
  - "MVK de Streamlit: mudar meta de 'domínio pleno' para 'uso supervisionado' (realista)"
  - "Adicionar 1 pomodoro/semana de leitura técnica deliberada (papers climate-tech)"
- **Política da Próxima Onda:** [x] **PUSH** (recomendado pelo verdict; regime Q3 manda PUSH até 2026-09-30)

---

## 6. Roadmap da Próxima Onda (Onda 02)

> *Onda 02: Climate Interview Prep + Networking Blitz (2026-07-27 → 2026-08-14).*

1. **[Épico: Paper Reading]** — Ler e anotar 2 papers de climate computing (Sustainable ML, Green Software Foundation). (IKIGAi: **Skill** + **Course**)
2. **[Épico: Outreach Blitz]** — Disparar ≥ 30 DMs LinkedIn para fundadores/líderes climate-tech + aplicar para 5 vagas. (IKIGAi: **Market**)
3. **[Épico: Mock Interview]** — Completar 1 mock interview técnico com Vinicius (ex-Google, mentor). (IKIGAi: **Skill** + **Revenue**)

---

## 7. Sinais de Alerta (Watchlist)

> *O que monitorar durante a Onda 02.*

- [ ] Queda sustentada de Q_HE < 0.45 por >3 dias
- [ ] Aumento de infrações (Leve/Média/Grave) > 5/semana
- [ ] Burnout sustentado (>2 semanas em RECOVER)
- [ ] Falta de progresso no eixo MVK (pilar não subiu de nível)
- [x] Refactor trigger externo monitorado: layoff Mosaic Forest (2026-07-22) — acompanhar impacto, mas sem pivot por ora

---

## 8. Policy Trail da Onda

> *Como o sistema regulou durante a onda (PolicyEngine state por dia).*

```
Estado inicial:    PUSH (Q3 regime mandatório; histerese desde Q2 PASS)
   ↓
Semana 1: PUSH por 7 dias
Semana 2: PUSH por 3 dias → MAINTAIN por 4 dias (Q_HE caiu para 0.62 na quarta)
Semana 3: MAINTAIN por 2 dias → PUSH por 5 dias (recuperado; sleep 7.8h média)
   ↓
Estado final:      PUSH (verdict CONTINUE_WAVE autoriza)
```

- **Dias em PUSH:** **15** (incluindo dias parciais nas transições; arredondamento conservador)
- **Dias em MAINTAIN:** **2** (quarta e quinta de W2)
- **Dias em REDUCE:** **0**
- **Dias em RECOVER:** **0**
- **Total de transições:** **3** (PUSH→MAINTAIN na quarta de W2; MAINTAIN→PUSH na segunda de W3; nenhuma para REDUCE/RECOVER)

---

## 9. Consolidação IKIGAi (Delta da Onda)

> *Snapshot início (2026-07-06) vs fim (2026-07-24).*

| Vetor | Score Início | Score Fim | Δ | Comentário |
|-------|:---:|:---:|:---:|---|
| Passion | 0.60 | 0.65 | **+0.05** | 3 conversas com fundadores durante outreach inicial reforçaram propósito. |
| Skill | 0.70 | 0.78 | **+0.08** | Python/Polars dominados; Streamlit básico; git/PR workflow consolidado. |
| Market | 0.40 | 0.48 | **+0.08** | 12 fundadores mapped; 4 conversas DMs iniciadas; vocabulário climate-tech adquirido. |
| Revenue | 0.60 | 0.60 | **+0.00** | Sem alteração visível — primeira oferta ainda no horizonte Q4-2026. |
| Course | 0.50 | 0.55 | **+0.05** | 1 paper Sustainable ML anotado + pitch gravado contribuem para meta-aprendizado. |

**IKIGAi Total Δ:** +0.05 + 0.08 + 0.08 + 0.00 + 0.05 = **+0.26** (em 5 vetores)
**IKIGAi Total Δ (média):** 0.26 / 5 = **+0.052** (média ponderada por vetor)

**Comparação com meta Q3-2026:**
- Meta Q3 (parcial): passion +0.10, skill +0.08, market +0.15, revenue +0.10, course +0.10 (delta de 18 dias proporcional)
- Realizado: 0.05 / 0.08 / 0.08 / 0.00 / 0.05 → **52% da meta Q3** (em 38% do tempo, run-rate saudável)

---

## Sincronização e Fechamento

- [x] As 3 Semanais foram consolidadas (ver `03-revisao-semanal_example.md` para W1; W2/W3 em arquivos paralelos)
- [x] Completion rate médio calculado (0-1): **0.85**
- [x] Diagnóstico de gaps preenchido (4 dims)
- [x] Verdict computado (CONTINUE_WAVE)
- [x] Ações corretivas definidas (opcionais — tightening, não pivot)
- [x] Roadmap da próxima onda definido (Onda 02)
- [x] Sinais de alerta configurados (5 watchlist items)
- [x] Sync com `vibe_ops.db` via `life sync vault` (executado em 2026-07-25)

---

*Template: Onda · v1.0 · Cluster PLAN (Tático) · Persona: Marina Souza · Onda 01 fechada em 2026-07-24*
