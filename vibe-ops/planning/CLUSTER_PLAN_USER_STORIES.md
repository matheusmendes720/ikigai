# CLUSTER PLAN — User Stories Detalhadas

> 10 user stories para o Cluster PLAN, com acceptance criteria testáveis.
> Origem: [`CLUSTER_PLAN_BRD.md`](CLUSTER_PLAN_BRD.md) §3 (versão resumida).
> Este doc expande com cenários alternativos, edge cases, e KPIs.

---

## US-001: Cold-Start Matinal (Diário)

**Persona:** Operador (Matheus)
**Trigger:** Acorda entre 3-5h
**Duração alvo:** ≤ 15 min
**Frequência:** 1x/dia

**Fluxo principal:**
1. Operador acorda (3-5h)
2. Hidratação + luz natural (5 min)
3. Meditação (5-15 min)
4. Operador roda `plan journal log --morning`
5. Wizard abre 5 perguntas em sequência
6. Operador responde (1-2 min por pergunta)
7. Sistema calcula Q_HE + regime
8. Sistema persiste em `auto_indagacao` (UNIQUE(date, ritual_type='morning'))
9. Sistema retorna regime + IKIGAi focus recomendado
10. Operador inicia bloco manhã (Deep Work ou Training)

**Acceptance criteria (expandido):**
- [ ] CLI: `plan journal log --morning`
- [ ] Input: 5 perguntas socráticas
- [ ] Validação: cada resposta 1-500 chars (não-vazio)
- [ ] Persistência: `auto_indagacao` table, UNIQUE(date, ritual_type)
- [ ] Idempotência: re-execução ATUALIZA row existente, não cria nova
- [ ] Cálculo: Q_HE = média de `sleep_window.quality_score` (último) + streak_days
- [ ] Cálculo: regime = algoritmo [`ikigai_meta_heuristics.md §1`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md)
- [ ] Output JSON: `{date, regime, qhe, ikigai_focus, pomodoros_recommended}`
- [ ] Tempo total ≤ 15 min (média 5 min)
- [ ] Funciona offline (zero network)

**Edge cases:**
- Acordou 5-6h (borderline): warning amarelo, regime ainda calculado
- Acordou 6h+ (infrção): forçar REDUCE se Q_HE < 0.70
- Acordou < 3h (impossível fisicamente): forçar RECOVER
- Skip meditação: campo opcional, não bloqueia
- Idempotência testada: rodar 2x no mesmo dia não cria 2 rows

**KPIs:**
- Taxa de execução diária (target: ≥ 90% dos dias)
- Tempo médio de resposta (target: ≤ 5 min)
- Aderência ao regime predito (target: ≥ 70% dos dias regime predito == regime real)

---

## US-002: Re-Entry Tarde (Diário)

**Persona:** Operador
**Trigger:** Pós-almoço (~12:30-13:30)
**Duração alvo:** ≤ 5 min
**Frequência:** 1x/dia

**Fluxo principal:**
1. Operador volta do almoço
2. Operador roda `plan journal log --afternoon`
3. Wizard: 1 pergunta ("Tô pronto para Deep Work? [🟢/🟡/🔴]")
4. Sistema valida: se 🔴 ou Q_HE < 0.60, força REDUCE
5. Sistema persiste em `auto_indagacao` (mesma data, ritual_type='afternoon')
6. Sistema retorna regime atualizado (pode ter mudado)

**Acceptance criteria:**
- [ ] CLI: `plan journal log --afternoon`
- [ ] Input: 1 pergunta + opcional note
- [ ] Persistência: `auto_indagacao` (UNIQUE evita duplicata)
- [ ] Override: regime atualiza se Q_HE < 0.60
- [ ] Tempo ≤ 5 min

**Edge cases:**
- Operador não almoçou: skip (registra direto)
- Operador em RECOVER: skip, mantém RECOVER
- Operador em PUSH mas almoço pesado: downgrade para MAINTAIN

---

## US-003: Shutdown Noturno (Diário)

**Persona:** Operador
**Trigger:** 18-21h (janela ideal)
**Duração alvo:** 15-30 min
**Frequência:** 1x/dia

**Fluxo principal:**
1. Operador termina trabalho (18-21h)
2. Operador roda `plan journal log --evening`
3. Wizard: 5 perguntas + 1 input pomodoros fechados
4. Sistema calcula Q_HE rolling 7d
5. Sistema calcula regime de amanhã (histerese)
6. Sistema persiste
7. Operador revê regime de amanhã e dorme

**Acceptance criteria:**
- [ ] CLI: `plan journal log --evening`
- [ ] Input: 5 perguntas + pomodoros_done
- [ ] Cálculo: Q_HE rolling 7d
- [ ] Predição: regime de amanhã (com histerese 2-3d)
- [ ] Output: regime_amanhã + wave_progress + cycle_progress
- [ ] Tempo ≤ 30 min

**Edge cases:**
- Esqueceu de rodar: detecta via `daily_routine.pomodoros_done = 0` (alerta)
- Regime de hoje foi RECOVER: 5 perguntas opcionais (skip OK)
- Wave transitioning: indica d15 (Wave-End) automaticamente

---

## US-004: Report Semanal (Semanal)

**Persona:** Operador
**Trigger:** Sábado à noite (cron)
**Duração:** ≤ 2 segundos
**Frequência:** 1x/semana

**Fluxo principal:**
1. Operador roda `plan report weekly`
2. Sistema query: 7 dias de `auto_indagacao` + `daily_routine` + `pomodoro`
3. Sistema calcula: pomodoros planejados vs fechados, regime distribution,
   IKIGAi avg scores, Q_HE trend
4. Sistema gera markdown + JSON
5. Sistema imprime output

**Acceptance criteria:**
- [ ] CLI: `plan report weekly [--json]`
- [ ] Output markdown com: cabeçalho (semana), tabela de dias, totais, regime distribution, IKIGAi avg, Q_HE trend
- [ ] Output JSON com mesmas métricas
- [ ] Tempo de geração ≤ 2 segundos (SQLite + aritmética)
- [ ] Sem LLM, sem embeddings, sem charts interativos

**Edge cases:**
- Semana incompleta: mostra dados parciais com aviso
- Falta 1+ dias: usa média dos dias disponíveis

---

## US-005: Mid-Wave Review (d7)

**Persona:** Operador
**Trigger:** d7 de WAVE (15d) — automático via cron
**Duração:** 15-20 min
**Frequência:** 1x a cada 15d

**Acceptance criteria:**
- [ ] CLI: `plan wave review --mid`
- [ ] Mostra: $H_{wave}$ esperado (48%), $C_{comp}$ atual, top 3 aprendizados
- [ ] Sugere ajuste de carga (sem aplicar)
- [ ] Persiste review em `qhe_history.regime_changed` (se aplicável)

---

## US-006: Wave-End Review (d15)

**Persona:** Operador
**Trigger:** d15 de WAVE
**Duração:** 30-45 min
**Frequência:** 1x a cada 15d

**Acceptance criteria:**
- [ ] CLI: `plan wave review --end`
- [ ] Mostra: $H_{wave}$ real (target 75%), tasks/tópicos concluídos, streak, IKIGAi Δ
- [ ] Decisão: continuar/pivotar/pausar hábito
- [ ] Persiste em nova tabela `wave_reviews` (a criar Sprint 2)

---

## US-007: Cycle-End Review (d45)

**Persona:** Operador
**Trigger:** d45 de CYCLE
**Duração:** 60-90 min
**Frequência:** 1x a cada 45d

**Acceptance criteria:**
- [ ] CLI: `plan cycle review --end`
- [ ] Mostra: 3 WAVE reviews consolidadas, $H_{cycle}$ (target 98.5%),
  skill velocity, ROI vector, Cognitive Debt
- [ ] PAE HALF_QUARTER check
- [ ] Decisão de próximo CYCLE tema

---

## US-008: Phase-End Review (d180)

**Persona:** Operador
**Trigger:** d180 de PHASE
**Duração:** 2-3h
**Frequência:** 1x a cada 180d

**Acceptance criteria:**
- [ ] CLI: `plan phase review --end`
- [ ] Mostra: 4 CYCLEs, $H_{phase}$ (target 99.98%), Teste de Fogo,
  IKIGAi vectors recalibrados, PAE anual
- [ ] Decisão de próxima PHASE

---

## US-009: Recovery Day (Regime RECOVER)

**Persona:** Operador
**Trigger:** Q_HE < 0.60 sustentado 2d (automático) ou manual
**Duração:** 1-2 dias
**Frequência:** conforme necessário

**Acceptance criteria:**
- [ ] CLI: `plan regime recover [--auto]`
- [ ] Ativa protocolo (Q_HE < 0.60 + sleep_debt > 2h → forçar)
- [ ] Pomodoros permitidos: 1-2 críticos
- [ ] Histerese: 3 dias com Q_HE ≥ 0.65 → sair
- [ ] Log em `qhe_history.regime_changed`

---

## US-010: Traverse Chaos (Modo Sobrevivência)

**Persona:** Operador
**Trigger:** manual (evento extraordinário)
**Duração:** 1-7 dias
**Frequência:** raro (~2-3x/ano)

**Acceptance criteria:**
- [ ] CLI: `plan regime traverse`
- [ ] Ativa modo sobrevivência
- [ ] Telemetria simplificada (apenas sono + 1 nota/dia)
- [ ] Histerese de retorno: 4 dias gradativos (RECOVER → REDUCE → MAINTAIN)
- [ ] Log em `qhe_history.regime_changed`

---

## Cross-refs

- [`CLUSTER_PLAN_BRD.md`](CLUSTER_PLAN_BRD.md) — Business Requirements
- [`CLUSTER_PLAN_DATA_MODEL.md`](CLUSTER_PLAN_DATA_MODEL.md) — Schema SQLite + Pydantic
- [`CLUSTER_PLAN_CLI_SPEC.md`](CLUSTER_PLAN_CLI_SPEC.md) — CLI spec completa
- [`../../CLUSTER_PLAN.md §2.5`](../../CLUSTER_PLAN.md) — Templates inline (referência)
- [`../../life-ops/planner/Points_of_premisses-task-habits.md §3-4`](../../life-ops/planner/Points_of_premisses-task-habits.md) — Q_HE + histerese
- [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) — Algoritmos regime

---

*CLUSTER_PLAN_USER_STORIES.md — v1.0 — 2026-06-05 — 10 user stories detalhadas para Cluster PLAN*
