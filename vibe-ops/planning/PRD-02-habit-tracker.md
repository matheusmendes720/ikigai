# PRD-02: Habit Tracker
**Versão:** 1.0.0 | **Status:** Draft | **Data:** 2026-05-10

> **Standalone Memory Machine** — Especificação autônoma do subgrafo de hábitos. Cobre tracking de rotinas, automação comportamental, streaks e o cálculo do QHE (Quociente de Eficiência Habitual).

---

## 1. Domínio & Escopo

O **Habit Tracker** é o subgrafo que transforma comportamentos discretos em **ativos biológicos/cognitivos mensuráveis**. A premissa central é que hábitos são investimentos com curva de depreciação e ROI calculável.

### Responsabilidades
- Registrar e rastrear execução diária de hábitos (streaks)
- Calcular automação comportamental via função H(t) — curva de aprendizado
- Computar o QHE (Quociente de Eficiência Habitual) agregado
- Derivar a política operacional diária (PUSH/MAINTAIN/REDUCE/RECOVER)
- Fornecer custo energético estimado de cada hábito

### Fora do Escopo
- Scheduling de tarefas (Temporal Engine)
- Tracking de tempo efetivo (Timewarrior)
- Decisões financeiras (Revenue Vector)

---

## 2. Entidades & Schema

### Habit — Entidade Central
```python
class Habit(BaseModel):
    id: str                    # ^habit_[a-z0-9_]+$  Ex: "habit_sono"
    name: str                  # min 3, max 100 chars
    entity_type: Literal["habit"] = "habit"
    category: Literal["sleep","meditation","workout","nutrition","study","work"]
    resistance: float          # 1.0-10.0 (dificuldade percebida)
    lambda_learning: float     # >0, default 0.1 (taxa de automação)
    streak_current: int        # ≥ 0, dias consecutivos
    streak_previous: int       # ≥ 0 (para calcular delta_S)
    streak_max: int            # ≥ 0, maior streak histórico
    habit_level: float         # 0.0-1.0 (automação atual H(t))
    weight_in_qhe: float       # 0.0-1.0 (peso no cálculo do QHE)
    status: Literal["active","paused","archived"] = "active"
    created_at: date
```

### Propriedades Computadas
```python
@property
def deficit(self) -> float:
    """Quanto falta para automação total: 1.0 - H(t)"""
    return 1.0 - self.habit_level

@property
def energy_required(self) -> float:
    """Custo energético: Resistência × Déficit"""
    return self.resistance * self.deficit

@property
def efficiency_index(self) -> float:
    """ROI do hábito: (H × delta_S) / (R × Deficit)"""
    delta_s = self.streak_current - self.streak_previous
    if self.deficit <= 0:
        return float('inf')
    return (self.habit_level * delta_s) / (self.resistance * self.deficit)
```

### QHEMetrics — Agregado de Eficiência
```python
class QHEMetrics(BaseModel):
    date: date
    habits: List[str]           # FKs → Habit.ids considerados
    weighted_avg_habit_level: float   # soma(H_i × w_i) / soma(w_i)
    consistency_score: float    # dias_executados / dias_possíveis
    streak_bonus: float         # streak_atual / 30 (normalizado)
    qhe: float                  # score final [0.0, 1.0]
    regime: Literal["PUSH","MAINTAIN","REDUCE","RECOVER"]
```

### Fórmula QHE
```
QHE = α·H_avg + β·Consistency + γ·StreakBonus

Onde:
  H_avg      = média ponderada do habit_level de todos os hábitos ativos
  Consistency = dias executados / dias possíveis (na Wave atual)
  StreakBonus = min(streak_max / 30, 1.0)
  α = 0.45, β = 0.35, γ = 0.20 (pesos calibráveis)

Regimes (Histerese ±5% para evitar oscilação):
  QHE ≥ 0.85  →  PUSH
  QHE ≥ 0.70  →  MAINTAIN
  QHE ≥ 0.50  →  REDUCE
  QHE < 0.50  →  RECOVER
```

### H(t) — Curva de Aprendizado de Hábito
```python
def compute_habit_level(streak: int, resistance: float, lambda_l: float) -> float:
    """
    H(t) = 1 - e^(-lambda * t / R)
    Onde:
      t = streak atual (dias)
      lambda_l = taxa de aprendizado (default 0.1)
      R = resistência do hábito (1-10)
    """
    import math
    return 1 - math.exp(-lambda_l * streak / resistance)
```

---

## 3. Frontmatter Contract (YAML)

```yaml
---
entity_type: habit
id: habit_sono
name: "Sono Regulado (18h-21h/3h-5h)"
category: sleep
resistance: 4.0
lambda_learning: 0.12
streak_current: 14
streak_previous: 13
streak_max: 21
habit_level: 0.72
weight_in_qhe: 0.30
status: active
created_at: 2026-01-01
---
```

### Catálogo de Hábitos Base (Sistema Padrão)

| ID | Nome | Categoria | Resistência | Peso QHE |
|:---|:-----|:----------|:-----------|:---------|
| `habit_sono` | Sono 18h-21h | sleep | 4.0 | 0.30 |
| `habit_meditacao` | Meditação 10min | meditation | 3.5 | 0.15 |
| `habit_treino` | Treino/Workout | workout | 6.0 | 0.20 |
| `habit_almoco_leve` | Almoço leve ≤35min | nutrition | 2.0 | 0.10 |
| `habit_deep_work` | Deep Work 90min | work | 7.0 | 0.25 |

---

## 4. Fluxos no Data-Mesh

### Upstream (Input Manual → Pipeline)
```
[Day Logger / Obsidian daily note]
  → streak_current += 1 (se executado)
  → habit_level = compute_habit_level(streak, resistance, lambda)
  → FrontmatterParser → Pydantic → SQLite habits table
```

### Downstream (Hábitos → Política)
```
[Habit records today]
  → QHEMetrics.compute()
  → regime = derive_regime(qhe)
  → PolicyDecision.create(policy=regime)
  → Setpoints do dia ajustados (deep_work_minutes, etc.)
```

### Integração com Temporal Engine
```
Wave.habit_focus → define quais hábitos focados na quinzena
Wave.target_consistency → meta de consistência da Wave atual
ReviewEvent.consistency_at_review → valor real no checkpoint
```

---

## 5. SQLite Schema

```sql
CREATE TABLE habits (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    resistance      REAL DEFAULT 5.0,
    lambda_learning REAL DEFAULT 0.1,
    streak_current  INTEGER DEFAULT 0,
    streak_max      INTEGER DEFAULT 0,
    habit_level     REAL DEFAULT 0.0,
    weight_in_qhe   REAL DEFAULT 0.1,
    status          TEXT DEFAULT 'active',
    created_at      DATE,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE habit_daily_log (
    id          TEXT PRIMARY KEY,
    habit_id    TEXT NOT NULL REFERENCES habits(id),
    log_date    DATE NOT NULL,
    executed    BOOLEAN NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(habit_id, log_date)
);

CREATE TABLE qhe_metrics (
    id                  TEXT PRIMARY KEY,
    date                DATE NOT NULL UNIQUE,
    qhe                 REAL NOT NULL,
    regime              TEXT NOT NULL,
    consistency_score   REAL,
    streak_bonus        REAL,
    habits_json         TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_habit_log_date ON habit_daily_log(log_date, habit_id);
CREATE INDEX idx_qhe_date ON qhe_metrics(date);
```

---

## 6. KPIs do Domínio

| KPI | Fórmula | Alvo |
|:----|:--------|:-----|
| QHE Score | weighted H(t) + consistency + streak | ≥ 0.75 (MAINTAIN) |
| Streak Longest Active | max(streak_current) across active habits | > 21 dias |
| Habit Automation Rate | habits com habit_level ≥ 0.80 / total | ≥ 60% |
| Daily Execution Rate | habits_done / habits_active | ≥ 0.90 |
| Cognitive Load Index | sum(energy_required) / total_habits | < 4.0 |

---

## 7. CLI Commands

```bash
# Estado de todos os hábitos hoje
python3 -m vibe_ops.cli habits status

# Registrar execução de hábito
python3 -m vibe_ops.cli habits log habit_sono --done
python3 -m vibe_ops.cli habits log habit_treino --skip --reason "lesao"

# Calcular QHE do dia
python3 -m vibe_ops.cli habits qhe --date today

# Ver curva de automação
python3 -m vibe_ops.cli habits automation-curve habit_sono

# Ranking de eficiência (efficiency_index)
python3 -m vibe_ops.cli habits rank --by efficiency

# Hábitos da Wave atual (habit_focus)
python3 -m vibe_ops.cli habits wave-focus

# Histórico de streaks (últimos 30 dias)
python3 -m vibe_ops.cli habits streaks --days 30
```

### Output esperado de `habits status`:
```
═══════════════════════════════════════════════════════════
  HABIT TRACKER — 2026-01-10 | QHE: 0.78 [MAINTAIN]
═══════════════════════════════════════════════════════════
  ID                  H(t)   Streak  Energy  Today
  habit_sono          0.72   14d     1.12    ✅
  habit_meditacao     0.45   7d      1.93    ✅
  habit_treino        0.31   4d      4.14    ⏳
  habit_almoco_leve   0.88   28d     0.24    ✅
  habit_deep_work     0.22   3d      5.46    ⏳
═══════════════════════════════════════════════════════════
  Regime: MAINTAIN | Consistency: 0.84 | Streak Bonus: 0.47
═══════════════════════════════════════════════════════════
```

---

## 8. Anti-Patterns

### Proibido
- Registrar streak sem log diário correspondente (inflação artificial)
- `habit_level` hardcoded (deve ser calculado via H(t))
- `weight_in_qhe` com soma > 1.0 entre todos os hábitos
- Mudar `resistance` sem narrativa de justificativa

### Obrigatório
- Log diário antes das 23:59 para contar no streak do dia
- `habit_level` recalculado após cada log
- QHE computado uma vez por dia (ao final)
- `streak_previous` atualizado quando streak_current muda

---

## 9. Roadmap de Implementação

| Fase | Entregável | Estimativa |
|:-----|:-----------|:-----------|
| MVP | Pydantic Habit model | ✅ Feito |
| v0.2 | SQLite schema + daily log | 3h |
| v0.3 | QHE calculator script | 4h |
| v0.4 | CLI `habits status` + `habits log` | 5h |
| v0.5 | H(t) curve visualization | 6h |
| v1.0 | Auto-trigger PolicyDecision pós-QHE | 8h |

---
> **Regra Append-Only:** Novas descobertas devem ser anexadas. Nada pode ser deletado.
