# CLUSTER PLAN — Business Requirements Document (BRD)

> **O que construir para o Cluster PLAN** (rotinas, blocos, rituais).
> Este doc é **AI-native**: uma coding agent deve ser capaz de implementar
> o Sprint 1 apenas lendo este arquivo + o `CLUSTER_PLAN.md` cluster doc.

---

## 1. Visão do Produto

### 1.1. Problema

O operador (Matheus) tem **~157,5 min/dia desperdiçados em overhead de transição**
entre blocos de tempo. A causa raiz: rituais de cold-start (5min) e
warm-down (15min) não são disciplinados. A tensão se manifesta como:

- Pomodoros abertos sem fechar
- Métricas orçado × realizado sem lastro
- Regimes (PUSH/MAINTAIN/REDUCE/RECOVER) sem feedback loop

### 1.2. Solução

Um sistema de **inputs manuais estruturados** (CLI) que registra 3 momentos
do dia (manhã, tarde, noite) com **11 perguntas socráticas**, persiste em
SQLite, e gera **relatórios determinísticos** (orçado × realizado) sem
LLM, sem NLP, sem embeddings.

### 1.3. Não-objetivos (esta Sprint 1)

- ❌ Sem NLP / LLM no pipeline diário
- ❌ Sem embeddings / vector store (deixa ADR-004 para Sprint 2+)
- ❌ Sem dashboards interativos (apenas reports markdown/JSON)
- ❌ Sem notificações push (apenas CLI)
- ❌ Sem sincronização com Taskwarrior (Sprint 2+)
- ❌ Sem dependência de qualquer LLM (incluindo AI Harness, por ora)

---

## 2. Personas

- **Operador (Matheus):** single-user, expert técnico, AI-curious, com
  contexto de estudante ADS no SENAI (6-12h, dias úteis)
- **Agente IA (futuro):** consome reports para gerar sugestões (mas não
  escreve no DB, não decide regime)

---

## 3. User Stories

### US-001: Cold-Start Matinal (Diário)

- **Como** operador
- **Quero** registrar 5 perguntas socráticas da manhã em ≤15 min
- **Para** definir regime do dia e pomodoros planejados

**Perguntas:**
1. 🔁 "O que fiz ontem que preciso repetir?"
2. 🚫 "O que fiz ontem que preciso parar de fazer?"
3. 🔄 "Que tarefa de ontem deve virar hábito?"
4. 🏆 "Qual é a grande vitória de hoje?"
5. 🎯 "Se eu só pudesse fazer 1 coisa, qual seria?"

**Acceptance criteria:**
- [ ] CLI `plan journal log --morning` abre wizard interativo
- [ ] Salva em SQLite `auto_indagacao` table (id, date, q1..q5, regime_predicted, qhe_at_moment)
- [ ] Retorna Q_HE previsto + regime (PUSH/MAINTAIN/REDUCE/RECOVER) calculado
- [ ] Idempotente (re-execução não cria duplicata, atualiza row existente)
- [ ] Tempo total ≤ 15 min

### US-002: Re-Entry Tarde (Diário)

- **Como** operador
- **Quero** registrar Q_HE pós-almoço em ≤5 min
- **Para** decidir se continuo/reduzo o bloco tarde

**Acceptance criteria:**
- [ ] CLI `plan journal log --afternoon` (1 pergunta: "Tô pronto para Deep Work?")
- [ ] Salva em SQLite `auto_indagacao` (mesma tabela, mesmo dia)
- [ ] Override do regime se Q_HE < 0.60 (força REDUCE)

### US-003: Shutdown Noturno (Diário)

- **Como** operador
- **Quero** consolidar o dia com 5 perguntas socráticas + pomodoros
- **Para** alimentar streak e preparar amanhã

**Perguntas:**
1. ✅ "O que correu bem hoje?"
2. ❌ "O que correu mal hoje?"
3. 📚 "Qual foi o maior aprendizado?"
4. 🧘 "O que estou levando de tensão desnecessária?"
5. 🎯 "Se amanhã eu só pudesse fazer 1 coisa, qual seria?"

**Acceptance criteria:**
- [ ] CLI `plan journal log --evening` (5 perguntas + pomodoros fechados)
- [ ] Salva em SQLite `auto_indagacao` (mesma tabela, mesmo dia)
- [ ] Calcula Q_HE rolling 7d
- [ ] Prediz regime de amanhã

### US-004: Report Semanal (Semanal)

- **Como** operador
- **Quero** relatório "orçado × realizado" da semana em ≤2 segundos
- **Para** detectar padrões de over/under-commitment

**Acceptance criteria:**
- [ ] CLI `plan report weekly` retorna markdown + JSON
- [ ] Mostra: pomodoros planejados vs fechados, regime (P/ M/ R/ Rec),
  IKIGAi scores médios da semana, Q_HE trend
- [ ] Apenas aritmética (zero LLM, zero embeddings)
- [ ] Tempo de geração ≤ 2 segundos

### US-005: Mid-Wave Review (d7)

- **Como** operador
- **Quero** revisar o progresso da WAVE (15d) no meio
- **Para** ajustar carga antes da consolidação

**Acceptance criteria:**
- [ ] CLI `plan wave review --mid` retorna status
- [ ] Mostra: $H_{wave}$ esperado (48%), $C_{comp}$ atual, top 3 aprendizados
- [ ] Sugere ajuste de carga (sem aplicar automaticamente)

### US-006: Wave-End Review (d15)

- **Como** operador
- **Quero** consolidar a WAVE
- **Para** decidir se WAVE foi sucesso e planejar próxima

**Acceptance criteria:**
- [ ] CLI `plan wave review --end` retorna fechamento
- [ ] Mostra: $H_{wave}$ real (target 75%), tasks/tópicos concluídos,
  streak final, IKIGAi vector Δs
- [ ] Decisão de continuidade (manter/pivotar/pausar hábito)

### US-007: Cycle-End Review (d45)

- **Como** operador
- **Quero** consolidar o CYCLE (45d = HALF_QUARTER)
- **Para** realinhar estratégia

**Acceptance criteria:**
- [ ] CLI `plan cycle review --end` retorna fechamento
- [ ] Mostra: 3 WAVE reviews consolidadas, $H_{cycle}$ (target 98.5%),
  skill velocity, ROI vector, Cognitive Debt
- [ ] PAE HALF_QUARTER check
- [ ] Decisão de próximo CYCLE tema

### US-008: Phase-End Review (d180)

- **Como** operador
- **Quero** consolidar a PHASE (180d = 2×QUARTER)
- **Para** transição de competência (ex: beginner → intermediate)

**Acceptance criteria:**
- [ ] CLI `plan phase review --end` retorna fechamento
- [ ] Mostra: 4 CYCLEs, $H_{phase}$ (target 99.98%), Teste de Fogo,
  IKIGAi vectors recalibrados, PAE anual
- [ ] Decisão de próxima PHASE

### US-009: Recovery Day (Regime RECOVER)

- **Como** operador
- **Quero** ativar modo "minimal routine" quando Q_HE < 0.60
- **Para** regenerar sem acumular fadiga

**Acceptance criteria:**
- [ ] CLI `plan regime recover` ativa protocolo (apenas quando aplicável)
- [ ] Pomodoros permitidos: 1-2 críticos
- [ ] Histerese: 3 dias com Q_HE ≥ 0.65 → sair

### US-010: Traverse Chaos (Modo Sobrevivência)

- **Como** operador
- **Quero** ativar modo "traverse chaos" para eventos extraordinários
- **Para** atravessar sem quebrar o sistema

**Acceptance criteria:**
- [ ] CLI `plan regime traverse` ativa modo sobrevivência
- [ ] Telemetria simplificada (apenas sono + 1 nota)
- [ ] Histerese de retorno: 4 dias gradativos

---

## 4. Critérios de Aceitação Globais

- [ ] Operador pode completar 1 semana de journaling em ≤30 min total
- [ ] Report semanal gerado em ≤2 segundos (queries SQLite + aritmética)
- [ ] **Zero chamadas LLM / embeddings / NLP** no pipeline diário
- [ ] 100% dos inputs persistidos **antes** de calcular qualquer report
- [ ] Q_HE calculado pela fórmula canônica (PRD-02 §3)
- [ ] Regime com histerese 2-3 dias (PRD-06 §2)
- [ ] Idempotência: re-execução não cria duplicatas
- [ ] Funciona offline (sem internet)

---

## 5. Dependências

- **SQLite** (built-in Python ≥ 3.10)
- **Typer** (CLI framework, já em `life-ops/pyproject.toml`)
- **Sem dependência de:**
  - ❌ LLM
  - ❌ Vector store (ChromaDB/sqlite-vec)
  - ❌ Taskwarrior (apenas observa, não sincroniza em Sprint 1)
  - ❌ Network (offline-first)

---

## 6. Sprint 1 Deliverables (esta semana)

- [ ] **US-001** Cold-Start Matinal: CLI `plan journal log --morning`
- [ ] **US-002** Re-Entry Tarde: CLI `plan journal log --afternoon`
- [ ] **US-003** Shutdown Noturno: CLI `plan journal log --evening`
- [ ] SQLite `auto_indagacao` table (ver [`CLUSTER_PLAN_DATA_MODEL.md`](CLUSTER_PLAN_DATA_MODEL.md))
- [ ] First weekly report (US-004) básico: orçado × realizado markdown
- [ ] Tests: `tests/test_journal.py` (in-memory SQLite)

## 7. Sprint 2-4 (preliminar)

- Sprint 2: Wave/Mid-Wave reviews (US-005, US-006)
- Sprint 3: Cycle-End review (US-007)
- Sprint 4: Phase-End review (US-008) + Recovery (US-009) + Chaos (US-010)

## 8. Out of Scope (próximos quarters)

- Sincronização TW (cluster PROJ) — Q4 2026
- AI Harness (sugestões, não-decisões) — Q4 2026
- Streamlit dashboard — Q1 2027
- Mobile app — Q2 2027
- Neo4j (grafo de dependencies) — Q3 2027

---

## 9. Cross-refs

- [`../../CLUSTER_PLAN.md`](../../CLUSTER_PLAN.md) — Standalone Memory Machine Cluster 1
- [`../../CONCEPTUAL_MODEL.md §3-4`](../../CONCEPTUAL_MODEL.md) — IKIGAi + regime
- [`../PRD-02-habit-tracker.md`](../PRD-02-habit-tracker.md) — Q_HE formula
- [`../PRD-06-policy-governance.md`](../PRD-06-policy-governance.md) — Regime state machine
- [`../../life-ops/planner/Points_of_premisses-task-habits.md`](../../life-ops/planner/Points_of_premisses-task-habits.md) — Q_HE math
- [`../../life-ops/planner/ikigai_planning/`](../../life-ops/planner/ikigai_planning/) — IKIGAi meta-brain
- [`../../life-ops/life_tatics/`](../../life-ops/life_tatics/) — Standalone CLI (reutilizar `block start/stop`)
- [`../../life-ops/life_tatics/cli.py`](../../life-ops/life_tatics/cli.py) — Typer CLI base
- [`../../life-ops/life_tatics/domain/time_blocks.py`](../../life-ops/life_tatics/domain/time_blocks.py) — TimeBlocks logic
- [`../../CLUSTER_PLAN.md §2.5`](../../CLUSTER_PLAN.md) — Templates inline (referência visual)
- [`../../CLUSTER_PLAN.md §6.5.B`](../../CLUSTER_PLAN.md) — 11 perguntas socráticas (origem)

---

*CLUSTER_PLAN_BRD.md — v1.0 — 2026-06-05 — Business Requirements para Cluster PLAN (Sprint 1)*
