> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> This glossary bridges IKIGAI vault terminology with PAV kernel terminology.
> Post-pivot, PAV is desativado; PAV terms are retained for audit only. For
> current canonical terminology, see:
> - \`code-docs/glossary.md\` (master glossary)
> - \`vault/.db.markdown\` schema (canonical source of truth for IKIGAI entities)

# Glossário IKIGAI × PAV — Métricas e Nomenclaturas

> **Fonte unificada:** IKIGAI vault (SPEC.md + entidades Pydantic) · PAV kernel (constants.py + core algorithms) · strategics/ (PT-BR framework)
> **Data:** 2026-08-26

---

## Convenções de Leitura

| Convenção | Significado |
|---|---|
| `code` | Termo técnico usado no código |
| `EN` | Nomenclatura inglesa (código-fonte) |
| `PT-BR` | Nomenclatura portuguesa (documentação estratégica) |
| `→` | Fluxo de derivação ou transição |
| `[a, b]` | Intervalo inclusivo |
| `∈` | Pertence a conjunto |

---

## Parte I — Pirâmide do Desempenho (`strategics/`)

*Fonte: `strategics/Modelagem Operacional.md` · INNER GUIDELINES (camada constitucional)*

### 🔷 Princípio Cardinal — TENSÃO → COMPORTAMENTO → SOLUÇÃO

> **Este é o princípio constitucional do sistema.** Toda decisão estratégica
> é derivada desta链条. Nunca contradizer este fluxo.

```
TENSÃO (tension)
    ↓  driver
COMPORTAMENTO (behavior)
    ↓  manifestação
SOLUÇÃO (solution)
```

| Camada | Definição | Exemplo |
|--------|-----------|---------|
| **Tensão** | Força motriz — problema não-resolvido, gap, oportunidade ou risco | "Q_HE 0.45, abaixo do target" |
| **Comportamento** | Resposta adaptativa — como o sistema reage à tensão | Regime desce PUSH→REDUCE |
| **Solução** | Intervenção deliberada — ação estruturada para resolver | Adicionar 2h de sleep, reduzir hardwork |

### 5 Tensões Estratégicas (Strategic Tensions)

| # | Tensão | Domínio | Tensão PT-BR |
|---|--------|---------|-------------|
| 1 | **Tensão de Propósito** | Paixão vs. Mercado | `passion` vs `market` |
| 2 | **Tensão de Capacidade** | Habilidade vs. Oportunidade | `skill` vs `market` |
| 3 | **Tensão de Recompensa** | Receita vs. Curso/Formação | `revenue` vs `course` |
| 4 | **Tensão Temporal** | Horizonte longo (547d) vs. curto (7d) | SONHO vs. bloco diário |
| 5 | **Tensão de Energia** | Q_HE disponível vs. Demanda de execução | `q_he_score` vs `hardwork_orçado` |

> **Nota:** As 5 tensões são a lente através da qual cada vetor IKIGAI é avaliado.
> Cada decisão estratégica deve responder: "qual tensão isto resolve?"

### 4 Regimes — Hysteresis Assimétrica

> **Regra constitucional:** Descidas são mais rápidas que subidas.
> Isso previne burnout crônico. Nunca atribuir regime sem calcular Q_HE primeiro.

| Regime | Emoji | Q_HE limiar | Trabalho | Pomodoros | Sono | Hysteresis |
|--------|-------|-------------|----------|-----------|------|------------|
| `PUSH` | 🚀 | ≥ 0.85 | 8h | 10 | 7h | ↑ 3 dias consecutivos |
| `MAINTAIN` | 🔧 | 0.70–0.85 | 6h | 8 | 8h | neutro |
| `REDUCE` | 📉 | 0.60–0.70 | 4h | 5 | 8h | ↓ 2 dias |
| `RECOVER` | 🛌 | < 0.60 | 2h | 2 | 9h | ↓ 2 dias OU emergência |

**Limiar MAINTAIN no ciclo bootstrap:** O valor `Q_HE: 0.6500` no seu output está no limiar
inferior de MAINTAIN (0.70-0.85) — indica que o sistema está marginalmente estável.

### Princípios Operacionais (Constitutionais)

1. **Hierarquia de Sonhos** — SONHO (547d) é raiz de tudo. Objetivos derivam dele.
2. **Fases são envelopes de peso vetorial** — cada fase distribui atenção nos 5 vetores de forma diferente.
3. **Q_HE é métrica primária de execução** — governa regime, não o contrário.
4. **Heurísticas H1–H6 são sinais, não comandos** — orientam correção mas não substituem judgment.
5. **Vault é memória verificável** — todo estado persistido é auditável.

### Proibições Constitucionais (Strategics/)

- ❌ Nunca contradizer ou reescrever conteúdo de `strategics/`
- ❌ Nunca atribuir regime sem calcular Q_HE primeiro
- ❌ Nunca ignorar sinais H1–H6 por mais de 1 ciclo
- ❌ Nunca confundir fase com regime (são camadas diferentes)

### Níveis Hierárquicos

| Nível PT-BR | Nível EN | Horizonte | Foco | Revisões |
|---|---|---|---|---|
| **Estratégico** | Strategic | 6–12 meses | Sonhos → Objetivos | Mensal |
| **Tático** | Tactical | 15 dias – 3 meses | Ondas, metas semanais | Quinzenal |
| **Operacional** | Operational | Diário | Blocos, hábitos | Diário |

### Ciclos Temporais

| Termo PT-BR | Termo EN | Valor | Notas |
|---|---|---|---|
| Ciclo | Cycle | 45 dias úteis | 4 ciclos/ano = 180 dias úteis |
| Onda | Wave | 3 semanas = 15 dias úteis | 3 ondas/ciclo |
| Bloco diário | Daily block | — | Manhã / Tarde / Noite |
| Trimestre | Quarter | 13 semanas (PAE) | Q1–Q4 |

### Blocos Diários (Turnos)

| Bloco PT-BR | Horário | Conteúdo |
|---|---|---|
| **Manhã** (MANHA) | 3–5h | Treino em jejum, Meditação |
| **Tarde** (TARDE) | 8–17h | Trabalho / Deep Work |
| **Noite** (NOITE) | 18–21h | Arremate, Planejamento do próximo dia |

### Cadência de Revisões

| Frequência | Termo PT-BR | Trigger |
|---|---|---|
| Diário | Relatório diário / Balanceamento | Rotina final (NOITE) |
| Semanal | Supervisão semanal | Otimização de eficiência |
| Quinzenal | Revisão quinzenal | `#revisão` |
| Mensal | Revisão mensal | Sonho-oriented |
| Por onda (3 sem) | Revisão Geral | Correção do Trajeto |
| Por ciclo (45d) | Avaliação geral | Fim de ciclo |

### Perguntas-Semente da Rotina Diária

**Rotina Inicial (MANHA):**
- "O que fiz ontem que devo repetir?"
- "O que fiz ontem que preciso deixar de fazer?"
- "Que tarefa de ontem deve tornar-se um hábito?"
- "Qual é a grande vitória de hoje?"

**Rotina Final (NOITE):**
- "O que fiz hoje que correu bem?"
- "O que fiz hoje que correu mal?"
- "Qual foi o maior aprendizado do dia?"

---

## Parte II — IKIGAI (Meta-Cérebro e Portfólio)

*Fontes: `life-ops/ikigai/SPEC.md`, `src/ikigai/entities/`, `src/ikigai/enums.py`*

### Hierarquia de Entidades (SONHO → ENTREGA)

| Nível PT-BR | Entidade EN | UEID prefix | Horizonte (dias) | Status canônico |
|---|---|---|---|---|
| **SONHO** | `DREAM` | `ikigai:dream:` | 547 / 1825–3650 | `seed → active` |
| **OBJETIVO** | `OBJECTIVE` | `ikigai:objective:` | 90 / 120 / 150 / 180 / 240 / 365 | `draft → planned → active` |
| **ONDA** | `PROJECT` | `ikigai:project:` | 30 / 60 / 90 / 120 / 150 / 180 | `draft → planned → active` |
| **ENTREGA** | `DELIVERABLE` | `ikigai:deliverable:` | 1–30 | `draft → planned → in_progress → done` |
| **TAREFA** | `TASK` | `ikigai:task:` | 1–7 | `todo → in_progress → done` |

**Forward-compat (placeholders, sem execução):** `ROUTINE`, `BLOCK`, `RITUAL`, `POMODORO`, `HABIT`, `SKILL`, `TOPIC`, `MATERIAL`, `SESSION`, `JOURNAL`, `NOTE`, `VECTOR`, `PROFILE`.

### UEID — Identificador Universal

```
Formato: <namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>
Exemplo: ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609
```

| Segmento | Conteúdo | Exemplo |
|---|---|---|
| `namespace` | Origem | `ikigai`, `tw`, `obsidian`, `external` |
| `entity_type` | Tipo da entidade | `dream`, `objective`, `project`, `deliverable` |
| `slug` | Nome legível (2–64 chars, imutável) | `vaga-remota-2026` |
| `uuid_short` | 8 hex chars de `uuid.uuid4()` | `4f6a202a` |
| `content_hash_short` | Primeiros 8 hex de SHA-256 do frontmatter canônico | `2cb24609` |

Métodos: `UEID.generate(ns, type, slug, content)`, `.with_new_content_hash()`, `.short()` → `namespace:entity_type:slug`.

### Os 5 Vetores IKIGAI

| Vetor | Descrição | Peso default (fundacao) |
|---|---|---|
| `passion` | Motivação intrínseca | 0.15 |
| `skill` | Competência técnica | 0.40 |
| `market` | Demanda de mercado | 0.15 |
| `revenue` | Potencial de receita | 0.10 |
| `course` | Trajetória de aprendizado | 0.20 |

Sub-vetores fracionais: `skill.python`, `market.freelance`, `skill.polars` (raiz deve ser um dos 5 canonicos).

**Phase default weights:**

| Phase | passion | skill | market | revenue | course |
|---|---|---|---|---|---|
| `fundacao` | 0.15 | 0.40 | 0.15 | 0.10 | 0.20 |
| `busca` | 0.10 | 0.15 | 0.45 | 0.20 | 0.10 |
| `hackathon` | 0.10 | 0.20 | 0.20 | 0.40 | 0.10 |
| `recuperacao` | 0.50 | 0.10 | 0.05 | 0.05 | 0.30 |
| `overclocking` | 0.15 | 0.15 | 0.15 | 0.50 | 0.05 |

### Status — Valores e Transições

**Base `StatusType`:** `draft`, `seed`, `planned`, `active`, `paused`, `blocked`, `in_progress`, `review`, `done`, `completed`, `achieved`, `fulfilled`, `cancelled`, `abandoned`, `archived`, `mastered`

**Canonização (Migration Phase 0):**
- `seed → ACTIVE`
- `planned → ACTIVE`
- `draft → DRAFT`

**Transições por tipo:**

| Entidade | Estado inicial | Transições principais |
|---|---|---|
| `Dream` | `seed` | `seed→active` (begin), `active→fulfilled` (achieve), `active→abandoned` |
| `Objective` | `draft` | `draft→planned` (plan), `planned→active` (start), `active→done` |
| `Project` | `draft` | `draft→planned`, `planned→active`, `active→completed` |
| `Task` | `todo` | `todo→in_progress`, `in_progress→done` |
| `Deliverable` | `draft` | `draft→planned`, `planned→in_progress`, `in_progress→done` |

**Prioridade de Tarefa:** `urgent` (<7d), `high` ([7,30)d), `medium` ([30,90)d), `low` (≥90d).

### Campos Comuns de Frontmatter (PlanEntity base — 23 campos)

```
ueid · entity_type · slug · parent_ueid · related_ueids · title · description
status · created_at · updated_at · last_reviewed_at · archived_at
ikigai_vectors · vector_weights_snapshot · phase_at_creation · regime_at_creation
horizon_days · primary_score · is_placeholder · placeholder_owner · claimed_by
source · source_md_path · custom · tags
```

### Phase e Regime (criação)

**`Phase` (5 valores):** `fundacao`, `busca`, `hackathon`, `recuperacao`, `overclocking`

**`RegimeType` (4 valores):** `push`, `maintain`, `reduce`, `recover`

### Regime Setpoints (IKIGAI — used at entity creation)

| Regime | hardwork_budget_h | pause_min | sleep_target_h | Q_HE_target |
|---|---|---|---|---|
| `push` | 4.0 | 10 | 7.5 | 0.85 |
| `maintain` | 2.5 | 15 | 8.0 | 0.65 |
| `reduce` | 1.5 | 20 | 8.5 | 0.45 |
| `recover` | 0.5 | 30 | 9.0 | 0.25 |

### Campos Específicos por Entidade

| Entidade | Campos específicos |
|---|---|
| `Dream` | `horizon_days ∈ {547,1825,2190,2555,2920,3285,3650}`, `motivation`, `success_metric`, `core_values` |
| `Goal` | `horizon_days ∈ {365,547,730,913,1095}`, `success_metrics`, `review_frequency_days` |
| `Objective` | `horizon_days ∈ {90,120,150,180,240,365}`, `key_results`, `progress_pct` |
| `Project` | `horizon_days ∈ {30,60,90,120,150,180}`, `tech_stack`, `repo_url`, `target_revenue_brl`, `actual_revenue_brl` |
| `Task` | `horizon_days ∈ {1–7}`, `priority`, `rice_reach/impact/confidence/effort`, `due_date`, `tw_uuid` |
| `Deliverable` | `horizon_days ∈ {1,2,3,4,5,6,7,14,30}`, `artifact_path`, `artifact_type`, `is_public` |
| `Profile` | `snapshot_date`, `vector_scores_snapshot` (0–1 ratio), `linked_*_ueid`, `next_review_date` |

### RICE Score (Tarefa)

```
RICE = (R × I × C) / max(E, 0.5)
R = reach, I = impact, C = confidence, E = effort (horas)
```

### Profile — Snapshot Fields

`ProfileSnapshot`: `date`, 5 vector scores (percent), 4 zone scores (P∩S, P∩M, S∩M∩R, M∩R), `ikigai_score`, `alignment_label` (ALIGNED≥75, CONVERGING[50,75), MISALIGNED[25,50), CRITICAL<25), `weakest_vector`, `biggest_opportunity`, `alerts`.

**AlignmentLabel:** `aligned`, `converging`, `misaligned`, `critical`

**`ScoreValue` unit literals:** `percent`, `ratio`, `raw`, `index`, `currency_brl`, `hours`

---

## Parte III — PAV (Produtividade Algorítmica Visual)

*Fontes: `life-ops/operational/packages/core/src/operational/`*

### Entidades Persistentes (15)

| Entidade | UEID prefix | Descrição |
|---|---|---|
| `Routine` | `rou_*` | Bloco de rotina recorrente (manhã/tarde/noite) |
| `RoutineLog` | `rlog_*` | Log de execução de uma rotina num dia |
| `TimeBlock` | `blk_*` | Bloco de tempo com horário start/end |
| `JournalEntry` | `day_*` | Entry diário com narrativa + métricas |
| `Habit` | `hab_*` | Hábito com resistência e λ de aprendizado |
| `SleepRecord` | `slp_*` | Registro de sono (bedtime, wake, quality, source) |
| `PomodoroRound` | `pmor_*` | Uma rodada de pomodoro (WORK/BREAK/etc) |
| `PolicyDecision` | `pol_*` | Decisão de regime para um dia |
| `PolicySetpoints` | `set_*` | Setpoints ativos de um regime |
| `AjusteFino` | `aju_*` | Ajuste de tempo granular num período |
| `PortfolioArtifact` | `port_*` | Artefato de portfólio (deploy status, tech stack) |
| `DayContext` | `ctx_*` | Contexto do dia (tipo, orçado, realizado) |
| `DailyReflection` | `ref_*` | Reflexão OKR daily (parar/repetir/sempre_fazer) |
| `LunchRecord` | `lun_*` | Registro de almoço/descanso |
| `TransicaoRegistrada` | `trn_*` | Transição T1–T9 entre períodos |

### Enums Principais

**`Period`:** `MANHA`, `TARDE`, `NOITE`
- MANHA: start=3, end=5 · TARDE: start=8, end=17 · NOITE: start=18, end=21
- `is_work_period` → só TARDE

**`RoutineType`:** `ENTRY`, `CORE`, `TRANSITION`, `EXIT`

**`RitualType`:** `HYDRATION`, `MEDITATION`, `SHUTDOWN`, `REVIEW`, `MORNING`, `EVENING`

**`HabitCategory`:** `PHYSIOLOGICAL`, `COGNITIVE`, `SOCIAL`, `CREATIVE`, `RITUAL`
- `is_body` → PHYSIOLOGICAL · `is_mind` → COGNITIVE | CREATIVE

**`EnergyLevel`:** `HIGH` (numeric=2), `MEDIUM` (1), `LOW` (0)
- Ordenável: LOW < MEDIUM < HIGH

**`QualityLabel` (sono):** `EXCELENTE` (≥9h), `BOM` (≥8h), `ACEITAVEL` (≥7h), `HARDCORE` (≥4h), `CRITICO` (<4h)

**`PomodoroState`:** `IDLE`, `WORK`, `BREAK`, `LONG_BREAK`, `PAUSED`, `SKIPPED`, `COMPLETE`
- `is_terminal` → IDLE | SKIPPED | COMPLETE
- `is_active` → WORK | BREAK | LONG_BREAK

**`PolicyState`:** `PUSH`, `MAINTAIN`, `REDUCE`, `RECOVER` (ordinal: 0,1,2,3)
- `is_protective` → REDUCE | RECOVER
- `is_productive` → PUSH | MAINTAIN
- `is_critical` → RECOVER

**`Severity` (policy engine):** `INFO`, `WARNING`, `CRITICAL`

**`Severity` (exceptions — 5-tier):** `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

**`TipoDia`:** `CURSO` (240min), `LIVRE` (540min), `HARDCORE` (660min), `DESCANSO` (120min)

**`EstadoPsicomatico`:** `EXCELENTE` (9–10), `BOM` (7–8), `REGULAR` (5–6), `RUIM` (3–4), `CRITICO` (1–2)

**`NivelInfracao`:** `LEVE` (<30min), `MEDIA` (30–60min), `GRAVE` (60–120min), `GRAVISSIMA` (>120min)

**`Scenario`:** `PERFEITO`, `DESVIADO`, `HARDCORE`

**`ArtifactType`:** `HACKATHON`, `SIDE_PROJECT`, `WORK_EXPERIENCE`, `CV_CONTENT`, `HTML_OUTPUT`, `APP`

**`DeploymentStatus`:** `DEPLOYED_PRODUCTION`, `COMPLETED`, `UI_READY_NOT_DEPLOYED`, `IN_PROGRESS`, `PLANNED`, `TO_FILL`

**`OpportunityStatus`:** `detected`, `evaluating`, `pursuing`, `won`, `lost`

**`SkillLevel`:** `beginner` (25), `intermediate` (50), `advanced` (75), `expert` (95)

**`SkillCategory`:** `programming`, `data`, `cloud`, `devops`, `soft_skill`, `domain`, `tool`, `other`

**`TaskPriority`:** `urgent`, `high`, `medium`, `low`

**`TaskStatus`:** `todo`, `in_progress`, `blocked`, `done`, `cancelled`

---

## Parte IV — Algoritmos Centrais (PAV)

### H(t) — Habit Level (Consistência)

```
H(t) = 1 - e^(-λ · s)
habit_level = compute_habit_level(lambda_learning, streak)

λ (lambda_learning)  = resistência ao hábito (0–1, default 0.093)
s (streak)           = dias consecutivos de execução
H(t) ∈ [0, 1)       = 0 nunca, 1 nunca na prática (assíntota)
```

### E_req — Energia Necessária

```
E_req = R · (1 - H(t))
energy_required = compute_energy_required(resistance, habit_level)

R = resistance (0–10)
E_req ∈ [0, 10]
```

### Eficiência do Hábito

```
efficiency = H(t) / (1 + E_req)
```

### Q_HE — Quality Habit Effectiveness (Média Ponderada)

```
Q_HE = H_avg · (E/E_max) · (1 + η · S_bonus)

H_avg   = Σ(w_i · H_i) / Σ(w_i)     (média ponderada de H(t) por weight)
E       = energia média do dia
E_max   = 10
η (eta) = 0.5 (default)
S_bonus = min(s_cur / s_max, 1.0)   (bonus de streak, s_max=90 dias)
```

**Valor teórico máximo:** 2.0

**Outputs derivados:**
- `regime_predicted`: `PUSH` se Q_HE≥0.85, `RECOVER` se Q_HE<0.60, senão `MAINTAIN`
- `MAINTAIN → PUSH`: só com 3+ dias consecutivos acima de 0.85

### Consistência

```
C = completed / total
consistency = compute_consistency(habit_states)
```

### Streak Bonus

```
S_bonus = min(s_cur / s_max, 1.0)
streak_bonus = compute_streak_bonus(current_streak, max_streak)
max_streak default = 90 dias (STREAK_MAX_DEFAULT)
```

---

## Parte V — Regime e Hysteresis (PAV)

### Setpoints por Regime (PolicySetpoints.from_pav_defaults)

| Regime | hardwork_budget_h | max_pomodoros/dia | sleep_target_h | Q_HE target | pausa_min | fases permitidas |
|---|---|---|---|---|---|---|
| **PUSH** | 8.0 | 10 | 7.0 | 0.85 | 10 | DEEP_WORK, SHALLOW_WORK |
| **MAINTAIN** | 6.0 | 8 | 8.0 | 0.75 | 10 | DEEP_WORK, SHALLOW_WORK |
| **REDUCE** | 4.0 | 5 | 8.0 | 0.65 | 15 | SHALLOW_WORK, RECOVERY |
| **RECOVER** | 2.0 | 2 | 9.0 | 0.50 | 20 | RECOVERY |

> **Nota:** Estes valores são do PAV `PolicySetpoints.from_pav_defaults`. O IKIGAI usa um setpoint diferente (Q_HE 0.25 para RECOVER vs 0.50 no PAV).

### Máquina de Estados da Política (FSM)

```
Transições (ordem de prioridade):

1. RECOVER entry (emergência):
   infractions ≥ 3 OR qhe < 0.30  →  RECOVER (CRITICAL)

2. RECOVER exit:
   RECOVER + 3+ dias consecutivos qhe > 0.60  →  REDUCE (INFO)
   else  →  RECOVER (CRITICAL)

3. REDUCE:
   ≥3 dias qhe > 0.85              →  MAINTAIN (INFO)
   ≥2 dias qhe < 0.60              →  RECOVER (WARNING)
   else                              →  REDUCE (WARNING)

4. MAINTAIN:
   ≥3 dias qhe > 0.85               →  PUSH (INFO)
   ≥2 dias qhe < 0.60              →  REDUCE (WARNING)
   else                              →  MAINTAIN (INFO)

5. PUSH:
   ≥2 dias qhe < 0.60              →  MAINTAIN (WARNING)
   infractions ≥ 2 (early warning)   →  REDUCE (WARNING)
   else                              →  PUSH (INFO)

6. Estado inicial (sem histórico):  →  MAINTAIN (INFO)
```

### Thresholds e Constantes de Hysteresis

| Constante | Valor | Significado |
|---|---|---|
| `POLICY_UPGRADE_DAYS` | 3 | Dias necessários para promoção |
| `POLICY_DOWNGRADE_DAYS` | 2 | Dias necessários para降级 |
| `POLICY_RECOVER_ENTRY_DAYS` | 1 | Dias em RECOVER para sair |
| `QHE_PUSH_THRESHOLD` | 0.85 | Q_HE mínimo para PUSH |
| `QHE_RECOVER_THRESHOLD` | 0.60 | Q_HE máximo para RECOVER entry |
| `_RECOVER_QHE_CRITICAL` | 0.30 | Q_HE crítico (força RECOVER) |
| `_RECOVER_INFRACTION_THRESHOLD` | 3 | Infractions para forçar RECOVER |
| `_PUSH_EARLY_WARNING_INFRACTIONS` | 2 | Infractions para early warning PUSH |

---

## Parte VI — Constantes PAV (PAVConstants)

*Arquivo: `packages/core/src/operational/constants.py` · 21 campos*

### Limites de Horário

| Constante | Valor | Descrição |
|---|---|---|
| `HORARIO_ACORDAR_MIN` | 3 | Mínimo para acordar |
| `HORARIO_ACORDAR_MAX` | 5 | Máximo para acordar |
| `HORARIO_DORMIR_MIN` | 18 | Mínimo para dormir |
| `HORARIO_DORMIR_MAX` | 21 | Máximo para dormir |
| `HORARIO_ULTIMA_REFEICAO_MIN` | 15 | Início da janela de refeição |
| `HORARIO_ULTIMA_REFEICAO_MAX` | 18 | Fim da janela de refeição |
| `LUZ_AZUL_CORTE` | 18 | Corte de luz azul (18h) |

### Pomodoro

| Constante | Valor |
|---|---|
| `POMODORO_WORK_MIN` | 50 |
| `POMODORO_BREAK_MIN` | 10 |
| `POMODORO_LONG_BREAK_MIN` | 30 |
| `POMODORO_ROUNDS_MIN` | 3 |
| `POMODORO_ROUNDS_MAX` | 4 |

### Saúde

| Constante | Valor |
|---|---|
| `SONO_OPCOES_HORAS` | (9, 8, 7, 4) |
| `AGUA_GLASSES_DIA` | 8 |

### Aprendizado de Hábito

| Constante | Valor |
|---|---|
| `LAMBDA_LEARNING_DEFAULT` | 0.093 |

---

## Parte VII — Métricas Compostas

### Daily Score

```
energy     = avg_energy - max(0, (8 - sleep_hours) * 10)
productivity = (tasks_done/max(tasks_created,1))*60 + min(time_tracked/8,1)*25 + min(pomodoros/8,1)*15
health     = sleep_quality*10*0.5 + (25 if exercise_done else 0) + min(water/8,1)*15

daily_score = energy*0.3 + productivity*0.4 + health*0.3
```

### Overall Score (DailyConsolidation)

```
overall_score = 0.3 * energy + 0.4 * productivity + 0.3 * health
sleep_debt    = max(0, 8 - sleep_hours)
```

### Week Score

| week_score | Label |
|---|---|
| ≥85 | `EXCELENTE` |
| ≥70 | `BOM` |
| ≥50 | `MEDIO` |
| ≥30 | `RUIM` |
| <30 | `RECUPERACAO` |

### Productivity Percent

```
productivity_pct = min(100, realizado / orcado * 100)
```

### Efficiency Percent

```
efficiency_pct = min(100, foco_min / total_min * 100)
```

### Budget Classification

| delta | Classificação |
|---|---|
| >60 min | MUITO_ACIMA |
| 20–60 min | ACIMA |
| -20–20 min | DENTRO |
| -60–-20 min | ABAIXO |
| < -60 min | MUITO_ABAIXO |

---

## Parte VIII — Classificação de Cenário

*`core/scenario_classifier.py`*

```
classificar_dia(horas_sono, pomodoros_planejados, pomodoros_completos,
                 infraction_count, energia_nivel, foco_nivel):

  horas_sono < 5 OR infractions ≥ 3  →  HARDCORE (confiança 95/90)
  5 ≤ horas_sono < 7 OR completos/planejados < 0.7 OR infractions ≥ 1  →  DESVIADO (confiança 80/70/75)
  senão  →  PERFEITO (confiança 95)

  HARDCORE_MAX_PER_MONTH = 2
```

---

## Parte IX — Pomodoro FSM

**Estados:** IDLE → WORK → BREAK → WORK → ... → LONG_BREAK → IDLE

**Grafo de Transição:**

| De | Para |
|---|---|
| IDLE | WORK, COMPLETE |
| WORK | BREAK, LONG_BREAK, PAUSED |
| BREAK | WORK, SKIPPED |
| LONG_BREAK | IDLE |
| PAUSED | WORK, IDLE |
| SKIPPED | WORK |
| COMPLETE | (terminal) |

---

## Parte X — Códigos de Erro (PAV)

| Código | Condição | Severidade |
|---|---|---|
| `TIME_001` | Acordou < 3h | — |
| `TIME_002` | Acordou > 12h | — |
| `TIME_003` | Acordou > 5h (light) | — |
| `SLEEP_001` | Sono < 4h | — |
| `SLEEP_002` | Sono > 12h | — |
| `MEAL_001` | Refeição após 18h | — |
| `LIGHT_001` | Luz azul após 18h | — |
| `POMO_001` | Rounds < 3 | — |
| `POMO_002` | Break < 5min | — |
| `ROUTINE_001` | Rotina incompleta | — |

---

## Parte X.5 — IKIGAI Agent Cycle Output (Taxonomia própria do agente)

*Fonte: `ikigai/src/agents/tools.py:318-323` · `ikigai/src/agents/ikigai_maintainer/nodes/observe.py` · `ikigai/src/agents/ikigai_maintainer/state.py`*

### Formato output — `plan cycle` (st ✅)

O agente IKIGAI emite um output formatado ao final de cada ciclo. Estrutura:

```
✅ Plan cycle complete
   Regime: {regime}  |  Q_HE: {qhe:.4f}  |  Meta: {mv:.4f}
   Vectors: {N} scored
   Corrections: {N}  |  Prospective: {N}  |  Retrospective: {N}
```

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `regime` | `str` | PolicyState atual do ciclo (PUSH/MAINTAIN/REDUCE/RECOVER) | `MAINTAIN` |
| `Q_HE` | `float` | Quociente de Hábito Estratégico — 4 casas decimais | `0.6500` |
| `Meta` | `float` | Meta-vector score agregado (média ponderada dos 5 vetores) | `0.7200` |
| `Vectors: {N} scored` | `int` | Quantos vetores IKIGAI foram avaliados neste ciclo | `5` (sempre 5: passion/skill/market/revenue/course) |
| `Corrections: {N}` | `int` | Número de sinais de correção emitidos pelos heuristics H1-H6 | `0` (semCorreções = sistema balanceado) |
| `Prospective: {N}` | `int` | Tamanho do *prospective buffer* (ações futuras draftadas) | `2` |
| `Retrospective: {N}` | `int` | Tamanho do *retrospective log* (aggregação de trabalho completado) | `1` |

### Canais prospectivo e retrospectivo

| Canal | Direcção | Node | Conteúdo |
|-------|----------|------|----------|
| `prospective_buffer` | Forward (futuro) | `plan_node` | Ações propostas para o tier corrente (QUARTERLY/WEEKLY/DAILY) |
| `retrospective_log` | Backward (passado) | `reflect_node` | Work items completados desde o último ciclo |
| `corrections` | Sinal de correcção | `observe_node` | Alertas H1-H6 que detectaram desvio do plano |

**Prospective buffer** —populate por `plan_node` (`nodes/plan.py`). Exemplos de itens:
- `[QUARTERLY] Draft next ONDA from active goals`
- `[WEEKLY] Plan this week's tasks from active projects`

**Retrospective log** —populado por `reflect_node` (`nodes/reflect.py`). Exemplos:
- `ONDA q3-1: 2 deliverables completed`
- `TRIMESTRE Q3: 1 project archived`

### Sinais de correção (Corrections / H1-H6)

| Heuristic | Condição | Ação |
|-----------|----------|------|
| H1 | Q_HE abaixo do target por >2 dias | Alerta de regime |
| H2 | Streak quebrado | Sugere recovery habits |
| H3 | `prospective_buffer` > 5 itens | Sobrecarga — precisa priorização |
| H4 | `retrospective_log` vazio por 3 ciclos | Paralisia — faltan resultados |
| H5 | regime desvio > 1 nível vs setpoint | Transição de regime recomendada |
| H6 | Burnout signals detectados | `kill_switch_triggered = True` |

Output do observe_node para corrections:
```
⚠️  Corrections (N):
   [H3] Prospective buffer overflow — 6 items, max 5
   [H1] Q_HE 0.45 below target 0.65
```

Se não há correções: `✅ No corrections — system balanced`

### Regime emoji output

O output de status do ciclo inclui um emoji de severidade:

| Regime | Emoji | Cor implícita |
|--------|-------|---------------|
| `PUSH` | 🟢 | bright_green — energia alta, Consistent acima do target |
| `MAINTAIN` | 🟡 | yellow — estável, Dentro do target |
| `REDUCE` | 🔴 | red — abaixo do target, requer atenção |
| `RECOVER` | ⚫ | bold — recuperação, abaixo de todos os thresholds |

Formato: `🟡 MAINTAIN | Q_HE: 0.6500` (emoji corresponde ao regime, Q_HE com 4 decimais)

### Meta-vector score

| Campo | Definição | Fórmula |
|-------|-----------|---------|
| `meta_vector_score` | Hybrid mean dos 5 vetores IKIGAI (escala 0-100) | `0.6 × geo_mean + 0.4 × harm_mean` |
| `vector_scores` | Scores individuais de cada vetor IKIGAI (escala 0-100) | `dict[VECTOR_TYPES, float]` |

**Escala: 0-100** (não 0-1). Valores como `39.9439` são normais — indicam vetores em ~40/100.

**Fórmula** (`state.py:175-207`):
```python
# Média geométrica (peso 0.6) — balanceia vetores
geo = exp(Σ(w_norm[k] * ln(max(score[k], 0.01))) for k in active)

# Média harmônica (peso 0.4) — penaliza scores baixos
harm = 1.0 / (Σ(w_norm[k] / max(score[k], 0.01)) for k in active)

meta_vector = 0.6 * geo + 0.4 * harm  # resultado em 0-100
```

**Exemplo numérico** — se todos os 5 vetores estão em ~40:
- geo = 40, harm = 40 → meta_vector ≈ 0.6×40 + 0.4×40 = **40.0**

**Interpretação prática:**
- 80-100 = vetores altos e balanceados (Q_HE ≥ 0.85, regime PUSH)
- 60-80 = vetores bons com leve desbalance
- 40-60 = vetores médios / início de bootstrapping (valor típico: ~40)
- 0-40 = vetores fracos ou bootstrap inicial

> **Bootstrapping:** Na primeira iteração do ciclo (estado vazio), `vector_scores` defaults para `{}` → `meta_vector = 0.0`. Conforme o agente popula scores do vault, o meta-vector sobe para o range ativo. O valor `39.9439` no primeiro ciclo real é normal — reflete vetores ainda não completamente populados no vault.

### Kill switch

Se `kill_switch_triggered = True`, o ciclo de agente halted. Sinaliza burnout severo ou violação de constraints críticos. O agente não prossegue para `plan_node` nem `reflect_node` até que o flag seja resetado manualmente.

---

## Parte XI — Integração IKIGAI ↔ PAV

### Chain de Responsabilidade

```
strategics/ (constituição)
  │
  ├── Define: 4 regimes + hysteresis + 3 níveis
  ├── Define: Sonhos (6-12mês), Ciclos (45d), Ondas (3 sem)
  └── Não executa, não mede
       │
       ▼
IKIGAI (direção estratégica)
  │
  ├── SONHO (horizon_days=547, vector_scores)
  ├── TRIMESTRE (parent_ueid → SONHO, horizon_days=90)
  ├── ONDAs (parent_ueid → TRIMESTRE, horizon_days=30)
  ├── DELIVERABLES (parent_ueid → ONDA, horizon_days=1-30)
  └── Lê: PAV outputs (H(t), Q_HE, policy state)
       │
       ▼
PAV (execução e medição)
  │
  ├── Habits: H(t), E_req, streak, resistance
  ├── Daily: time blocks, journal, sleep, energy
  ├── Q_HE composite: habit_avg · energy_ratio · (1+η·streak_bonus)
  ├── Policy FSM: PUSH / MAINTAIN / REDUCE / RECOVER
  └── Output: JSON/SQLite → consumido por IKIGAI
```

### Quem é responsável pelo quê

| Pergunta | Sistema responsável |
|---|---|
| "Qual é meu sonho de longo prazo?" | IKIGAI (`DREAM`) |
| "Este ciclo de 45 dias avança meu SONHO?" | IKIGAI (leitura) |
| "Quantos dias consecutivos cumpri o hábito X?" | PAV (`habit_engine`: H(t), streak) |
| "Qual é meu Q_HE desta semana?" | PAV (`consolidator`: Q_HE) |
| "Devo transitar de PUSH para MAINTAIN?" | PAV (`policy_engine`: FSM + hysteresis) |
| "Meu portfólio avançou nesta ONDA?" | IKIGAI (leitura de PAV + decisão humana) |
| "Preciso ajustar escopo da ONDA?" | IKIGAI (decisão, guiado por PAV) |

---

## Parte XII — Correspondência de Regimes

| IKIGAI RegimeType | PAV PolicyState | IKIGAI Q_HE target | PAV Q_HE target | IKIGAI hardwork | PAV hardwork |
|---|---|---|---|---|---|
| `push` | `PUSH` | 0.85 | 0.85 | 4.0h | 8.0h |
| `maintain` | `MAINTAIN` | 0.65 | 0.75 | 2.5h | 6.0h |
| `reduce` | `REDUCE` | 0.45 | 0.65 | 1.5h | 4.0h |
| `recover` | `RECOVER` | 0.25 | 0.50 | 0.5h | 2.0h |

> **Observação:** Os setpoints de PAV e IKIGAI diferem. PAV é mais permissivo (targets mais altos). IKIGAI usa seus próprios setpoints no `regime_at_creation` dos entities. O_SYNC entre os dois sistemas ainda não existe (gap arquitetural).

---

## Parte XIII — Glossary Cruzado

| Termo PT-BR | Termo EN | Sistema | Definição curta |
|---|---|---|---|
| Sonho | Dream | IKIGAI | Meta de longo prazo (547d+) com 5 vetores |
| Objetivo | Objective | IKIGAI | Meta trimestral (90d) que avança um SONHO |
| Onda | Project | IKIGAI | Ciclo de 30 dias com 3–4 entregas concretas |
| Entrega | Deliverable | IKIGAI | Artefato concreto de uma ONDA |
| Vetor | Vector | IKIGAI | Uma das 5 dimensões: passion/skill/market/revenue/course |
| UEID | UEID | IKIGAI | Identificador triplo: slug + uuid + content_hash |
| Phase | Phase | IKIGAI | Estágio de vida: fundacao/busca/hackathon/recuperacao/overclocking |
| Horizonte | Horizon days | IKIGAI | Dias até deadline da entidade |
| Snapshot | Snapshot | IKIGAI | Registro pontual dos 5 vetores num momento |
| Hábito | Habit | PAV | Comportamento recorrente com H(t) e resistência |
| H(t) | Habit level | PAV | Consistência do hábito: 1 - e^(-λ·s) |
| Energia necessária | Energy required | PAV | E_req = R · (1 - H(t)) |
| Q_HE | Q_HE | PAV | Quality Habit Effectiveness composite score |
| Bloco de tempo | Time block | PAV | Janela de tempo com start/end e metadata |
| Registro de sono | Sleep record | PAV | bedtime, wake, quality_score, source |
| Ronda | Round | PAV | Uma unidade de pomodoro (WORK ou BREAK) |
| Regime | Policy state | PAV | PUSH/MAINTAIN/REDUCE/RECOVER |
| Hysteresis | Hysteresis | PAV | Regra: promoção exige 3 dias,降级 exige 2 |
| Setpoint | Setpoint | PAV | Valor-alvo de um regime (hardwork, sono, Q_HE) |
| Ciclo | Cycle | strategics | 45 dias úteis (4 por ano) |
| Onda | Wave | strategics | 3 semanas = 15 dias úteis (3 por ciclo) |
| Bloco diário | Daily block | strategics | Manhã / Tarde / Noite |
| Revisão geral | General review | strategics | Correção de trajetória após cada onda |
| Pirâmide | Performance pyramid | strategics | 3 níveis: Estratégico / Tático / Operacional |
| Score composto | Composite score | PAV | daily_score = 0.3·energy + 0.4·productivity + 0.3·health |
| Desvio | Deviation | PAV | Delta entre orçado e realizado em minutos |
| Ajuste fino | Fine adjustment | PAV | Ajuste granular de tempo num período |
| Reflexão | Reflection | PAV | OKR diário (parar/repetir/sempre_fazer) |
| Buffer prospectivo | Prospective buffer | IKIGAI agent | Ações futuras draftadas pelo node `plan` |
| Log retrospectivo | Retrospective log | IKIGAI agent | Work completada desde último ciclo, agregada por `reflect_node` |
| Correção | Correction signal | IKIGAI agent | Alerta H1-H6 de desvio do plano |
| Meta-vector | Meta-vector score | IKIGAI agent | Média ponderada dos 5 vetores IKIGAI |
| Kill switch | Kill switch | IKIGAI agent | Flag que halt o ciclo se True (burnout severo) |
| Plan cycle | Plan cycle | IKIGAI agent | Output formatado do ciclo do agente: "✅ Plan cycle complete" |
