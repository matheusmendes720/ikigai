# PRD-01: Temporal Engine (Wave / Cycle / Phase)
**Versão:** 1.0.0 | **Status:** Draft | **Data:** 2026-05-10

> **Standalone Memory Machine** — Especificação autônoma do subgrafo temporal. Um agente CLI pode ler apenas este PRD e operar o domínio sem depender de outros documentos.

---

## 1. Domínio & Escopo

O **Temporal Engine** define os containers de tempo nos quais toda atividade humana é ancorada.

### Hierarquia Canônica
```
Phase (180 dias)  →  Cycle (45 dias)  →  Wave (15 dias)  →  ReviewEvent
```

### Responsabilidades
- Definir e validar períodos temporais
- Gerar chaves FK (`anchor_wave`, `parent_cycle`, `parent_phase`) para outros domínios
- Disparar ReviewEvents nos checkpoints (mid-wave, wave-end, mid-cycle, cycle-end)
- Gerenciar transições de estado (`active → completed → archived`)

---

## 2. Entidades & Schema

### Phase
```python
class Phase(BaseModel):
    id: str                    # ^P\d+$  Ex: "P1"
    entity_type: Literal["phase"] = "phase"
    start_date: date
    duration_days: int = 180   # range [90, 365]
    status: Literal["active", "completed", "aborted"] = "active"
    cycles: List[str]          # FKs → Cycle.ids
    mastery_target: str        # min 5 chars
    # computed: end_date, mid_phase_date
```

### Cycle
```python
class Cycle(BaseModel):
    id: str                    # ^C\d+_[A-Za-z]{3}_\d{4}$  Ex: "C1_Jan_2026"
    entity_type: Literal["cycle"] = "cycle"
    start_date: date
    duration_days: int = 45    # range [30, 90]
    status: Literal["active", "completed", "aborted"] = "active"
    parent_phase: str          # FK → Phase.id
    waves: List[str]           # FKs → Wave.ids
    # computed: end_date, half_quarter_date
```

### Wave
```python
class Wave(BaseModel):
    id: str                    # ^W\d+_[A-Za-z]{3}_\d{4}$  Ex: "W1_Jan_2026"
    entity_type: Literal["wave"] = "wave"
    start_date: date
    duration_days: int = 15    # range [1, 30]
    status: Literal["active", "completed", "aborted"] = "active"
    habit_focus: List[str]     # IDs de hábitos focados
    target_consistency: float = 0.90  # [0.0, 1.0]
    # computed: end_date, mid_wave_date
```

### ReviewEvent
```python
class ReviewEvent(BaseModel):
    id: str                    # ^rev_[a-z0-9_]+$
    review_type: Literal["MID_WAVE","WAVE_END","MID_CYCLE","CYCLE_END","MID_PHASE","PHASE_END"]
    target_id: str             # FK → Wave/Cycle/Phase
    target_type: Literal["wave","cycle","phase"]
    scheduled_date: date
    completed_date: Optional[date] = None
    status: Literal["scheduled","completed","skipped","overdue"] = "scheduled"
    qhe_at_review: Optional[float] = None
    consistency_at_review: Optional[float] = None
    narrative: str = ""
    adjustments: List[str] = []
```

---

## 3. Frontmatter Contracts (YAML)

### Phase
```yaml
---
entity_type: phase
id: P1
start_date: 2026-01-01
duration_days: 180
status: active
mastery_target: "Python Data Engineering & AI Agents"
cycles: [C1_Jan_2026, C2_Mar_2026, C3_Mai_2026]
---
```

### Cycle
```yaml
---
entity_type: cycle
id: C1_Jan_2026
start_date: 2026-01-01
duration_days: 45
status: active
parent_phase: P1
waves: [W1_Jan_2026, W2_Jan_2026, W3_Fev_2026]
---
```

### Wave
```yaml
---
entity_type: wave
id: W1_Jan_2026
start_date: 2026-01-01
duration_days: 15
status: active
habit_focus: [habit_sono, habit_meditacao, habit_deep_work]
target_consistency: 0.90
---
```

---

## 4. Fluxos no Data-Mesh

### Upstream (Obsidian → SQLite)
```
Markdown frontmatter → FrontmatterParser → Pydantic Validation → FK Resolution → SQLite
```

### Downstream (TW/Timew → Reviews)
```
Timewarrior intervals → TW Adapter → ReviewEvent trigger → MetricsEngine → PolicyEngine
```

### Chaves de Integração
| Entidade | FK Exportada | FK Consumida |
|:---------|:------------|:------------|
| Phase | `P1` | — |
| Cycle | `C1_Jan_2026` | `parent_phase: P1` |
| Wave | `W1_Jan_2026` | implícita via Cycle |
| StudyPlan | — | `anchor_wave: W1_Jan_2026` |
| DailyMetrics | — | `parent_wave: W1_Jan_2026` |

---

## 5. SQLite Schema

```sql
CREATE TABLE temporal_entities (
    id            TEXT PRIMARY KEY,
    entity_type   TEXT NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    duration_days INTEGER,
    status        TEXT DEFAULT 'active',
    parent_id     TEXT,
    metadata_json TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE review_events (
    id              TEXT PRIMARY KEY,
    review_type     TEXT NOT NULL,
    target_id       TEXT NOT NULL,
    target_type     TEXT NOT NULL,
    scheduled_date  DATE NOT NULL,
    completed_date  DATE,
    status          TEXT DEFAULT 'scheduled',
    qhe_at_review   REAL,
    consistency_val REAL,
    narrative       TEXT,
    adjustments_json TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_temporal_status ON temporal_entities(entity_type, status);
CREATE INDEX idx_review_target ON review_events(target_id, status);
```

---

## 6. KPIs do Domínio

| KPI | Fórmula | Alvo |
|:----|:--------|:-----|
| Cycle Completion Rate | completed/started | ≥ 0.85 |
| Review Adherence | reviews_done/scheduled | ≥ 0.90 |
| Wave Consistency | days_exec/wave_days | ≥ 0.90 |
| Overdue Reviews | COUNT(status='overdue') | = 0 |

---

## 7. CLI Commands

```bash
# Estado temporal atual
python3 -m vibe_ops.cli temporal status

# Criar nova Wave
python3 -m vibe_ops.cli temporal create-wave \
  --id W2_Jan_2026 --start 2026-01-16 \
  --parent-cycle C1_Jan_2026 \
  --habit-focus habit_sono,habit_meditacao

# Reviews pendentes
python3 -m vibe_ops.cli temporal reviews --status overdue,scheduled

# Completar review
python3 -m vibe_ops.cli temporal complete-review rev_w1_jan_mid \
  --qhe 0.78 --consistency 0.85 \
  --narrative "Boa semana, sono regular"

# Linha do tempo da Phase
python3 -m vibe_ops.cli temporal timeline --phase P1
```

---

## 8. Anti-Patterns

### Proibido
- `wave: "semana 3 de fev"` (string livre)
- Cycle sem `parent_phase` válido
- 2 entidades do mesmo tipo `active` simultaneamente
- Pular ReviewEvents sem marcar `skipped`

### Obrigatório
- Cada Cycle → FK válida para Phase existente
- ReviewEvents schedulados na criação de Wave/Cycle
- Transição `active → completed` requer ReviewEvent `WAVE_END` completado

---

## 9. Roadmap de Implementação

| Fase | Entregável | Estimativa |
|:-----|:-----------|:-----------|
| MVP | Pydantic models + parser | ✅ Feito |
| v0.2 | SQLite schema + insert adapter | 4h |
| v0.3 | CLI `temporal status` + `timeline` | 6h |
| v0.4 | ReviewEvent auto-scheduler | 8h |
| v1.0 | TW tags temporais integradas | 12h |

---
> **Regra Append-Only:** Novas descobertas devem ser anexadas. Nada pode ser deletado.
