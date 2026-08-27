---
name: pav-agent-spec
description: PAV — Agente de Execução Operacional (produtividade algorítmica visual)
type: spec
---

# PAV — Agente de Execução Operacional

## Posicionamento

PAV é o **agente de execução** — o sensor que alimenta IKIGAI com dados de performance pessoal.
Enquanto IKIGAI é o cérebro (planejamento estratégico), PAV são as mãos (execução visual e rastreamento).

```
IKIGAI (cérebro) ←── QHEMetrics, HabitState, PolicyDecision ──→ PAV (sensor)
```

## Responsibilities

1. **Coletar journaling por bloco de tempo** — narrativa do usuário em cada bloco
2. **Rastrear hábitos + streaks** — completude diária, esforço em minutos
3. **Energy readings** — auto-reportado high/medium/low
4. **Formulários de auto-avaliação** — mini-CBT prompts (inspirado em obsidian-chat-cbt-plugin)
5. **Computar Q_HE local** — feeding IKIGAI's regime FSM
6. **MCP Gateway próprio** — `pav-journal` CLI/TUI como interface

## Inspiração: CBT Journal Prompts

De `obsidian-chat-cbt-plugin/src/prompts/`:

```typescript
// system.ts — prompt de sistema CBT
const system = `...act as a kind, open Cognitive Behavioral Therapist...
  Ask questions one at a time...
  Help users identify troubling situations...
  Identify negative thinking patterns (All-or-Nothing, Overgeneralization, Mental Filter)...
  Guide through cognitive restructuring...`

// summary.ts — template de resumo
const summary = (lang) =>
  `Create a markdown table: belief | emotion | category | reframed thought`
```

PAV adapta esses prompts para:
- **Journaling estruturado** por time-block
- **Auto-avaliação de energia** (não emoção clínica)
- **Extração de métricas** (não reframing terapêutico)

## Arquitetura

```
vault-journal (Rust/CLI)
  ├── journal.db              ← SQLite principal
  ├── PAV MCP Gateway         ← conexão com life/
  └── terminal toolkit        ← CLI de preenchimento
```

### vault-journal.db Schema

```sql
-- Habits
CREATE TABLE habits (
  id          TEXT PRIMARY KEY,  -- hab_<slug>
  name        TEXT NOT NULL,
  description TEXT,
  frequency   TEXT NOT NULL,      -- daily | weekly | custom
  active      INTEGER DEFAULT 1,
  created_at  TEXT
);

-- Habit logs (daily completions)
CREATE TABLE habit_logs (
  id              TEXT PRIMARY KEY,  -- hst_<habit>_<date>
  habit_id        TEXT NOT NULL,
  date            TEXT NOT NULL,    -- YYYY-MM-DD
  completed       INTEGER NOT NULL, -- 0 or 1
  effort_minutes  INTEGER,
  notes           TEXT,
  logged_at       TEXT
);

-- Energy readings
CREATE TABLE energy_readings (
  id         TEXT PRIMARY KEY,  -- erg_<date>_<time>
  date       TEXT NOT NULL,
  time       TEXT,              -- HH:MM
  level      TEXT NOT NULL,     -- high | medium | low
  context    TEXT,              -- opcional: contexto
  logged_at  TEXT
);

-- Journal entries (time-block journaling)
CREATE TABLE journal_entries (
  id          TEXT PRIMARY KEY,  -- jnl_<date>_<block>
  date        TEXT NOT NULL,
  block_start TEXT,              -- HH:MM
  block_end   TEXT,              -- HH:MM
  content     TEXT NOT NULL,      -- narrativa livre
  tags        TEXT,              -- JSON array
  mood        TEXT,               -- high | medium | low (auto or manual)
  extracted   INTEGER DEFAULT 0,  -- já processado para métricas?
  logged_at   TEXT
);

-- QHE metrics (computed daily)
CREATE TABLE qhe_metrics (
  id              TEXT PRIMARY KEY,  -- qhe_<date>
  date            TEXT UNIQUE NOT NULL,
  habit_avg       REAL NOT NULL,     -- 0.0–1.0
  consistency     REAL NOT NULL,     -- 0.0–1.0
  streak_bonus    REAL NOT NULL,     -- 0.0–1.0
  energy_ratio    REAL NOT NULL,     -- 0.0–1.0
  qhe_score       REAL NOT NULL,     -- computed: habit_avg * energy_ratio * (1 + 0.5 * streak_bonus)
  regime_input    TEXT,              -- PUSH | MAINTAIN | REDUCE | RECOVER
  created_at      TEXT
);

-- Policy decisions (regime + workload)
CREATE TABLE policy_decisions (
  id              TEXT PRIMARY KEY,
  date            TEXT UNIQUE NOT NULL,
  regime          TEXT NOT NULL,
  q_he            REAL NOT NULL,
  days_in_regime  INTEGER NOT NULL,
  hardwork_budget INTEGER,   -- minutos
  sleep_target    REAL,      -- horas
  pomodoros       INTEGER,
  set_by          TEXT,       -- auto | manual_override
  created_at      TEXT
);
```

## PAV MCP Gateway Tools

```python
# Habit tracking
pav_log_habit(habit_id, date, completed, effort_minutes, notes) → str
pav_get_habit_streak(habit_id) → dict  # {current_streak, max_streak}
pav_list_habits(active_only=True) → list[dict]
pav_create_habit(name, frequency, description) → habit_id

# Energy
pav_log_energy(date, time, level, context) → str
pav_get_energy_day(date) → dict  # {morning, afternoon, evening}

# Journal
pav_log_journal(date, block_start, block_end, content, tags) → str
pav_get_journal_blocks(date) → list[dict]
pav_cbt_summary(date) → str  # markdown table: belief | emotion | category | reframed

# QHE
pav_compute_qhe(date) → dict  # {habit_avg, consistency, streak_bonus, energy_ratio, qhe_score}
pav_get_qhe_history(days=7) → list[dict]

# Policy
pav_get_policy_decision(date) → dict
pav_override_policy(date, regime) → str  # manual override
```

## CBT-Inspired Journal Prompts

### Time-block journal prompt (adaptado de system.ts)

```text
Você está fazendo um journal de operação pessoal.
Mantenha respostas curtas e diretas.
Pergunte um ponto por vez.

Perguntas por bloco de tempo:
1. "O que você realizou neste bloco?"
2. "Qual foi sua energia durante este período? (high/medium/low)"
3. "Houve algum blocker ou distração?"
4. "O que você aprendeu ou observou sobre seu ritmo?"

Ao final, extraia para mim em formato:
- Energia: H|M|L
- Tarefas realizadas: (lista)
- Blockers: (sim/não)
- Ritmo: (bom/regular/precisa melhorar)
```

### Daily reflection prompt (adaptado de summary.ts)

```text
Crie uma tabela markdown resumindo o dia:
| Bloco | Energia | Tarefas | Blockers | Aprendizado |
|-------|---------|---------|-----------|-------------|
```

## Contexto: vault-journal (Rust CLI)

`code_space/apps/vault-journal` — precisa ser criado/integrado.

PAV MCP Gateway vive em `life/src/pav/mcp_gateway.py` e consome o vault-journal.db.

## Feed para IKIGAI

IKIGAI lê de PAV via:

```python
# Em ikigai_plan_cycle (tools.py)
qhe_metrics = _read_pav_qhe(today)  # lê de vault-journal.db
regime_decision = _read_pav_policy(today)
```

## Status

- [x] Schema definido (este doc)
- [ ] vault-journal CLI (Rust) — `code_space/apps/vault-journal`
- [ ] PAV MCP Gateway em `src/pav/`
- [ ] Formulário de journaling (terminal toolkit)
- [ ] CBT prompt template em `src/pav/prompts/`
- [ ] Integração IKIGAI ← PAV (pull no ciclo)
