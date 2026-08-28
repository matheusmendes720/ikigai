# 05 — Canvas: Contracts Architecture (Pydantic v2 Strict)

> **Categoria:** INDEX (Layer 2 — Architecture Canvas)
> **Anchor canônico:** `src/contracts/`
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Resumo

Os **canonical contracts** são os únicos allowed inter-layer contracts. Todos os módulos (PAV kernel, IKIGAi Deep Agent, mesh adapters, MCP gateway) **importam de `src/contracts/`**. Invariante: `frozen=True, extra="forbid"` em todos os modelos — mudanças aditivas viram recusa explícita do Pydantic, forçando migração.

## §2 — Inventário

| Arquivo | Modelos principais | LOC | Padrão |
|:--------|:-------------------|:---:|:-------|
| `src/contracts/__init__.py` | Package barrel + invariant docstring | ~30 | Padrão #11 (frozen Pydantic) |
| `src/contracts/common.py` | UEID, Period, Priority, EntityType, RegimeState, TimestampMixin | ~250 | UEID regex 4-part |
| `src/contracts/task.py` | Task, Subtask, ChecklistItem, Project, Milestone, Deliverable | ~400 | Hierarchical composition |
| `src/contracts/task_change.py` | TaskAction, TaskStatus, TaskChange, PropagationEvent | ~150 | Review-queue events |
| `src/contracts/planning.py` | Wave, Sprint, PlanningCycle, VaultEvent | ~300 | Temporal hierarchy |
| `src/contracts/metrics.py` | Burndown, ExecutionRate, QHEScore | ~200 | Feedback signals |

## §3 — Invariante load-bearing

**Texto verbatim de `src/contracts/__init__.py`:**

> Contracts are the ONLY allowed inter-layer contracts. Consumers: `src/operational/`, `src/ikigai/`, `data/`, `interfaces/`. All models are `frozen=True, extra="forbid"`.

**Implicações práticas:**
- Qualquer `BaseModel` fora de `src/contracts/` é suspect (provavelmente vale refatorar)
- Adicionar campo a modelo existente = breaking change (consumidores precisam migrar)
- IDE type-checking garante `model.copy(update={...})` em vez de mutação direta

## §4 — Modelos canônicos (referência rápida)

### 4.1 UEID (`common.py`)

```python
class UEID(str):
    """Universal Entity Identifier — 4-part regex: type:slug:uuid:hash"""
    REGEX = r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$"
    # types: tsk, sub, chk, proj, msl, del, hab, hst, qhe, cyc, wave, sprint
```

### 4.2 Task (`task.py`)

```python
class Task(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: UEID
    horizon: Period  # today, tomorrow, this_week, onda, sprint, etc.
    priority: Priority  # critical | high | medium | low
    project_id: UEID | None
    depends_on: list[UEID]
    estimated_minutes: int
    done: bool
    done_at: datetime | None
    
    def mark_done(self) -> "Task":  # retorna novo Task, não muta
        return self.model_copy(update={"done": True, "done_at": datetime.now()})
```

### 4.3 TaskChange + PropagationEvent (`task_change.py`)

```python
class TaskAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DONE = "done"

class TaskStatus(str, Literal["pending", "approved", "rejected", "propagated", "partial_propagation"]):
    ...

class TaskChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    ueid: UEID
    action: TaskAction
    fields: dict[str, Any]
    source_fork: str
    timestamp: datetime
    status: TaskStatus = "pending"
```

### 4.4 VaultEvent (`planning.py`)

```python
class VaultEvent(BaseModel):
    """Markdown vault event from Obsidian frontmatter."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    verb: Literal["created", "updated", "done", "blocked", "unblocked", "archived"]
    source: Literal["deep_agent", "interface", "manual", "vault_sync"]
    ueid: UEID
    planned_date: date | None
    actual_date: date | None
    
    @property
    def is_late(self) -> bool:
        return self.actual_date is not None and self.planned_date is not None and \
               self.actual_date > self.planned_date
```

## §5 — Hierarquia temporal (`planning.py`)

```
PlanningCycle (C{num}_{ANO})
   ├── Wave (W{num}_{MES}_{ANO})  # 15 dias
   │   └── Sprint (SP{num}_...)  # opcional, mais granular
   └── VaultEvent (verb + ueid)
```

**IDs por regex:**
- `W\d+_[A-Za-z]{3}_\d{4}` (Wave)
- `SP\d+_[A-Za-z]{3}_\d{4}` (Sprint)
- `C\d+_[A-Za-z]{3}_\d{4}` (PlanningCycle)

**Wave:** 15 dias úteis. **PlanningCycle:** trimestral (6 waves).

## §6 — QHEScore → RegimeState mapping (`metrics.py` + `common.py`)

```python
class QHEScore(BaseModel):
    qhe: float  # [0.0, 1.0]
    regime_predicted: RegimeState
    # mapeamento: PUSH ≥ 0.85, MAINTAIN 0.65-0.85, REDUCE 0.45-0.65, RECOVER < 0.45
```

**Nota:** Faixas aqui (0.45/0.65) **divergem** das faixas em `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` (0.60/0.70/0.85). Verificar qual é canônica. **GAP #C2** (ver análise crítica).

## §7 — Cross-references

### Code
- `src/contracts/__init__.py` — invariant
- `src/contracts/common.py` — UEID, RegimeState, Priority, Period
- `src/contracts/task.py` — Task, Project
- `src/contracts/task_change.py` — TaskChange, PropagationEvent
- `src/contracts/planning.py` — Wave, Sprint, PlanningCycle
- `src/contracts/metrics.py` — QHEScore, Burndown, ExecutionRate

### Docs
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — UEID propagation
- `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md` — strict mode rationale
- `docs/diagnostics/2026-08-28-phase1-audit/05-open-questions.md:OQ-2` — contracts naming

### Memory
- `[[interfaces-architecture-2026-08-27]]` — frozen invariant
- `[[reorg-bugs-p0-fixed-2026-08-27]]` — UEID format fixed in B6

## §8 — Fontes

- `src/contracts/__init__.py` — package barrel + invariant docstring
- `src/contracts/common.py` — UEID, RegimeState, Priority, Period, EntityType
- `src/contracts/task.py` — Task, Subtask, ChecklistItem, Project, Milestone, Deliverable
- `src/contracts/task_change.py` — TaskAction, TaskStatus, TaskChange, PropagationEvent
- `src/contracts/planning.py` — Wave, Sprint, PlanningCycle, VaultEvent
- `src/contracts/metrics.py` — Burndown, ExecutionRate, QHEScore
- `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md` — strict mode decision
