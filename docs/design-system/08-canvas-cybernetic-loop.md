# 08 — Canvas: Cybernetic Loop (Target → Sensor → Adjuster → Persist → Sync → Index)

> **Categoria:** INDEX (Layer 2 — Architecture Canvas)
> **Anchor canônico:** `vibe-ops/src/cybernetics/daily_loop.py` + `src/operational/docs/TERMINAL_DESIGN_AUDIT.md`
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Resumo

O **Cybernetic Loop** é a peça mais macro: fecha o ciclo **Target → Sensor → Adjuster → Persist → Sync → Index** continuamente. Tudo que calculamos (Q_HE, regime, meta-vetor, IKIGAi 5 vetores) é input do loop. Tudo que produzimos (tasks, pomodoros, SONHOs) é output que realimenta os inputs. Opera em **3 frequências** distintas (diário, pomodoro, feedback) com diferentes níveis de granularidade.

## §2 — Inventário

| Arquivo | Função | LOC | Notas |
|:--------|:-------|:---:|:------|
| `vibe-ops/src/cybernetics/daily_loop.py` | `CyberneticDailyLoop.execute_daily_cycle(date)` | ~400 | Implementa Target→Sensor→Adjuster |
| `src/operational/docs/TERMINAL_DESIGN_AUDIT.md` | 3-layer terminal conceptual model | ~250 | Padrão conceitual |
| `docs/auto-performance-os/26-integration-cybernetic-loop.md` | Docset math doc | ~80 | Cross-ref canônico |
| `data/vibe_ops.db` | SQLite state | runtime | Persistido |
| `data/chroma_db/` | ChromaDB vector index | runtime | Semantic search |

## §3 — CyberneticDailyLoop class

```python
class CyberneticDailyLoop:
    def __init__(self, db_path, tw_path, vault_path, tw_client=None):
        self.db = Path(db_path)              # data/vibe_ops.db
        self.tw = Path(tw_path)
        self.vault = Path(vault_path)
        self.policy_engine = PolicyEngine()
        self.ikigai_scorer = IkigaiScorer()
        self.sync = SyncEngine(vault_path, db_path, tw_path, tw_client)
        self.indexer = HybridRAGIndexer()
    
    def execute_daily_cycle(self, target_date: date) -> PolicyDecision:
        # 1. TARGET
        target = self._compute_target(target_date)
        # 2. SENSOR
        sensor = self._read_sensor_data(target_date)
        # 3. ADJUSTER
        prev = self._read_prev_decision(target_date)
        decision = self.policy_engine.evaluate(metrics=sensor, prev_decision=prev, target_date=target_date)
        # 4. PERSIST
        self._persist_decision(decision, target_date)
        # 5. SYNC
        self.sync.sync_sqlite_to_taskwarrior(decision.policy.value)
        # 6. INDEX
        self.indexer.index_vault(self.vault)
        return decision
```

## §4 — 6 etapas do loop

### 4.1 TARGET (`_compute_target`)

```python
def _compute_target(self, date: date) -> dict:
    score = self.ikigai_scorer.compute_score(date)
    return {
        "qhe_target": 0.8,
        "c_comp_target": 0.9,  # IKIGAi competência composta
        "ikigai_global": score["meta_vetor"],
    }
```

**Outputs:** `qhe_target`, `c_comp_target`, `ikigai_global`.

### 4.2 SENSOR (`_read_sensor_data`)

```python
def _read_sensor_data(self, date: date) -> dict:
    rows = self.db.execute("""
        SELECT 
            SUM(duration_minutes) as actual_minutes,
            COUNT(*) as sessions_count
        FROM study_sessions
        WHERE date = ?
    """, (date,)).fetchone()
    
    habit_rows = self.db.execute("""
        SELECT executed, streak_broken
        FROM habit_states
        WHERE date = ?
    """, (date,)).fetchall()
    
    return {
        "actual_hours": rows["actual_minutes"] / 60,
        "consistency": sum(1 for h in habit_rows if h["executed"]) / max(len(habit_rows), 1),
        "infractions": sum(1 for h in habit_rows if h["streak_broken"]),
        "hours_deviation": (rows["actual_minutes"] / 60) - self.target_hours,
    }
```

**Inputs:** `study_sessions`, `habit_states` (executed + streak_broken).

### 4.3 ADJUSTER (PolicyEngine.evaluate)

**Já documentado em Layer 3 (pattern #15 hysteresis FSM).** Resumo: 4-state FSM PUSH/MAINTAIN/REDUCE/RECOVER com histerese assimétrica (3-up / 2-down / 1-emergência).

### 4.4 PERSIST

```python
def _persist_decision(self, decision: PolicyDecision, date: date):
    self.db.execute("""
        INSERT INTO policy_decisions (date, regime, qhe, target_qhe, decision_json, decided_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date, decision.policy.value, decision.qhe, self.target_qhe, 
          decision.model_dump_json(), datetime.now()))
```

**Storage:** `policy_decisions` table (1 row per day).

### 4.5 SYNC

`self.sync.sync_sqlite_to_taskwarrior(decision.policy.value)` — propaga decisão para Taskwarrior (throttle em RECOVER).

### 4.6 INDEX (Semantic)

`HybridRAGIndexer.index_vault(self.vault)` — re-indexa vault markdown em ChromaDB. Permite busca semântica sobre histórico.

## §5 — 3 frequências do loop

| Loop                  | Frequência       | Granularidade              | Output |
|:----------------------|:-----------------|:---------------------------|:-------|
| `run-daily`           | 1× por dia       | Dia inteiro (target/sensor/adjuster) | `PolicyDecision` + sync + index |
| `run-pomodoro`        | A cada 25 min    | Pomodoro individual        | Event em `data/pomodoro_log.jsonl` |
| `run-feedback`        | 1× por hora      | Janela deslizante          | Update em `policy_decisions` (ajuste fino) |

**3 frequências distintas** evitam ruído: diário olha plano macro, pomodoro olha execução micro, feedback olha sinais fracos.

## §6 — 3-layer terminal conceptual model (TERMINAL_DESIGN_AUDIT.md)

**Cross-link conceitual importante:** `src/operational/docs/TERMINAL_DESIGN_AUDIT.md` documenta um modelo conceitual de 3 layers para apps terminal:

```
┌────────────────────────────────────────────────┐
│ Layer 3: Presentation (UI)                     │  ← forks-prontas
├────────────────────────────────────────────────┤
│ Layer 2: Orchestration (cybernetic loop)       │  ← Deep Agent + IKIGAi
├────────────────────────────────────────────────┤
│ Layer 1: Domain (auto-performance math)        │  ← PAV kernel (desativado)
└────────────────────────────────────────────────┘
```

**Invariante:** layers nunca se cruzam diretamente. Presentation fala com Orchestration via MCP; Orchestration fala com Domain via contratos Pydantic.

## §7 — Cross-references

### Code
- `vibe-ops/src/cybernetics/daily_loop.py` — CyberneticDailyLoop
- `vibe-ops/src/middleware/sync_engine.py` — sync engine
- `src/operational/packages/core/src/operational/core/policy_engine.py` — PolicyEngine
- `src/operational/packages/core/src/operational/core/habit_engine.py` — habit scoring

### Docs
- `src/operational/docs/TERMINAL_DESIGN_AUDIT.md` — 3-layer conceptual model
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — math doc
- `docs/auto-performance-os/23-meta-decision-flow.md` — 4-stage decision flow
- `vibe-ops/architecture/ADR-002-mesh-contracts-state-machines.md` — state machines

### Memory
- `[[graph-orchestration-checkpoint-2026-08-27]]` — checkpoint
- `[[q3-q4-resolved-2026-08-27]]` — Q1 (trace_id logging + --dry-run)

## §8 — Fontes

- `vibe-ops/src/cybernetics/daily_loop.py` — CyberneticDailyLoop
- `src/operational/docs/TERMINAL_DESIGN_AUDIT.md` — 3-layer model
- `vibe-ops/src/middleware/sync_engine.py` — SyncEngine
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — cross-ref canônico
