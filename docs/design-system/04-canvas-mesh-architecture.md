# 04 — Canvas: Mesh Architecture (Cross-Fork Propagation)

> **Categoria:** INDEX (Layer 2 — Architecture Canvas)
> **Anchor canônico:** `src/mesh/` + `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Resumo

A **Data Mesh** é a camada que permite uma task existir em **múltiplos forks** (tuiboard, taskdog, solverforge-calendar) simultaneamente, todas referenciando o mesmo UEID canônico. Implementa o **padrão fork-pronta dual-layer**: forks são user views (Layer A), agent/CLI é operator (Layer B). Falhas em 1 adapter são isoladas — não bloqueiam os outros.

## §2 — Inventário

| Arquivo | Função | Linhas | Padrão |
|:--------|:-------|:------:|:-------|
| `src/mesh/__init__.py` | Module docstring | 5 | — |
| `src/mesh/queue.py` | Append-only filesystem queue (atomic temp+rename) | ~120 | Padrão #12 (append-only queue) |
| `src/mesh/agent_consumer.py` | Valida `TaskChange` (PAE rules) | ~180 | Decision.APPROVE/REJECT/CLARIFY |
| `src/mesh/agent_propagator.py` | Propaga `PropagationEvent` para adapters (per-adapter try/except) | ~150 | Failure isolation pattern |
| `src/mesh/adapters/__init__.py` | Empty | 1 | — |
| `src/mesh/adapters/base.py` | `ForkAdapter` Protocol | ~80 | Padrão #13 (ForkAdapter contract) |
| `src/mesh/adapters/cli.py` | `CliAdapter` (JSONL store) | ~100 | Atomic temp+rename |
| `src/mesh/adapters/taskdog.py` | `TaskdogAdapter` (SQLite UPSERT) | ~140 | ON CONFLICT(ueid) idiom |
| `src/mesh/adapters/solverforge_calendar.py` | `SolverforgeCalendarAdapter` (UPI ueid column) | ~160 | Idempotent PK reuse |

## §3 — Protocolos-chave

### 3.1 Queue protocol (`queue.py`)

```python
def enqueue(event: TaskChange) -> str          # atomic temp+rename → data/review_queue/<event_id>.json
def consume_pending() -> Iterator[TaskChange]  # yields events where status == "pending"
def ack(event_id: str, status: TaskStatus)     # re-emits with new status (idempotent)
def replay_after_restart()                     # re-processes pending events on agent startup
```

**Storage:** `data/review_queue/{event_id}.json` (atomic write: temp file → rename).

### 3.2 ForkAdapter Protocol (`adapters/base.py`)

```python
@runtime_checkable
class ForkAdapter(Protocol):
    name: str
    def read(self, ueid: UEID) -> dict[str, Any] | None: ...
    def apply_change(self, event: PropagationEvent) -> None: ...  # MUST be idempotent
    def supports_field(self, field_name: str) -> bool: ...
```

**Invariante:** `apply_change` é idempotente — chamar 2× com mesmo evento tem mesmo efeito que 1×.

### 3.3 Adapter storage topology

| Adapter | Storage backend | Schema | Idempotency key |
|:--------|:----------------|:-------|:----------------|
| `CliAdapter` | `data/tasks.jsonl` (append-only JSONL) | `{title, due, priority, ueid, written_at, source_fork}` | UEID |
| `TaskdogAdapter` | `data/taskdog/tasks.db` SQLite | `tasks(id, ueid UNIQUE, name, status, priority, ...)` | UEID UNIQUE constraint |
| `SolverforgeCalendarAdapter` | `data/solverforge_calendar/unified_planning.db` SQLite | `unified_planning_items(id PK, ueid UNIQUE, status, ...)` | UEID UNIQUE + `id` PK reuse |

**Padrão recorrente:** UEID é coluna UNIQUE em todas as tabelas; PK interna do fork é separada. Permite trocar UEID sem perder identidade.

## §4 — Cross-references

### Code
- `src/mesh/queue.py` — ver §3.1
- `src/mesh/agent_consumer.py` — PAE validation rules
- `src/mesh/agent_propagator.py` — per-adapter try/except
- `src/mesh/adapters/base.py` — ver §3.2
- `src/contracts/task_change.py` — `TaskChange`, `TaskAction`, `TaskStatus`, `PropagationEvent`

### Docs
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` — mesh readiness synthesis
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` — adapter #1 details
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` — adapter #2 details
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` — adapter #3 details
- `src/contracts/__init__.py` — frozen + extra=forbid invariant
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — UEID semantics

### Memory
- `[[interfaces-architecture-2026-08-27]]` — dual-layer
- `[[q3-q4-resolved-2026-08-27]]` — Q2 (4 stubs removidos)

## §5 — Validation rules (`agent_consumer.py`)

| Regra | Razão |
|:------|:------|
| Title ≥ 5 chars | Evitar titles vazios/placeholder |
| Title ≠ {todo, tbd, fix, work, task, stuff, thing} | Anti-placeholder |
| `due` (se presente) ≥ hoje | Não criar tasks no passado |
| UEID collision + status propagated + title diferente → REJECT | Imutabilidade de UEID |
| Action ∉ {create, update, delete, done} → REJECT | Whitelist |
| Status ∉ {pending, approved, rejected, propagated, partial_propagation} → REJECT | Whitelist |

**Decision enum:** `APPROVE | REJECT | CLARIFY`. CLARIFY pede human-in-the-loop antes de decidir.

## §6 — Propagation semantics (`agent_propagator.py`)

```python
def propagate(event: TaskChange) -> None:
    adapters = get_adapters()  # 3 instâncias
    results = {}
    for adapter in adapters:
        try:
            adapter.apply_change(event)        # idempotente
            results[adapter.name] = "ok"
        except Exception as e:
            results[adapter.name] = str(e)     # NÃO bloqueia outros adapters
    if any(v != "ok" for v in results.values()):
        ack(event.id, "partial_propagation")    # status parcial
    else:
        ack(event.id, "propagated")
```

**Invariante:** se 1 adapter falhar, outros ainda processam. Replay (idempotência) garante convergência eventual.

## §7 — Fontes

- `src/mesh/queue.py` — atomic append-only queue
- `src/mesh/agent_consumer.py` — PAE validation
- `src/mesh/agent_propagator.py` — per-adapter failure isolation
- `src/mesh/adapters/base.py` — ForkAdapter Protocol
- `src/mesh/adapters/cli.py` — CliAdapter (JSONL)
- `src/mesh/adapters/taskdog.py` — TaskdogAdapter (SQLite UPSERT)
- `src/mesh/adapters/solverforge_calendar.py` — SolverforgeCalendarAdapter (UPI)
- `src/contracts/task_change.py` — TaskChange + PropagationEvent
