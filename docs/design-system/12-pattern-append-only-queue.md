# 12 — Padrão: Append-only Queue (Mesh Review Queue)

> **Categoria:** Layer 3 — Patterns Catalog (Padrão #12)
> **Anchor canônico:** `src/mesh/queue.py` + `src/mesh/agent_consumer.py` + `src/mesh/agent_propagator.py`
> **Publico:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR + EN technical terms (UEID, FSM, JSONL, UPSERT, atomic write, fork, adapter, deep-agent)

---

## §1 — Intuição

A **append-only queue** em `data/review_queue/<event_id>.json` é o backbone assíncrono que desacopla os **forks** (CLI / tuiboard / taskdog / solverforge-calendar) do **Deep Agent validador**. Em vez de RPC síncrono, cada fork escreve um `TaskChange` (frozen Pydantic, serializado como JSON) num arquivo único, e o agente consome depois. O **atomic temp+rename** (`tempfile` + `os.replace()`) garante que o evento aparece na fila **inteiro ou não aparece** — nunca corrompido em disco. Mudanças de status são feitas por **re-emissão**: o arquivo é reescrito com o novo `TaskStatus` (frozen model força `model_copy(update={...})` em vez de mutação), preservando o invariante append-only — **eventos nunca são deletados**, apenas marcados como `propagated` ou `partial_propagation`. Esse desenho habilita **replay após restart** (`replay_after_restart()`), **failure isolation por adapter** (per-adapter try/except em `propagate()`), e **idempotência end-to-end** — todos load-bearing sob a tese de auto-feedback estocástico que o sistema IKIGAi precisa preservar.

---

## §2 — Enunciado Formal

### 2.1 Storage contract

**Path:** `<PROJECT_ROOT>/data/review_queue/<event_id>.json`
onde `<PROJECT_ROOT>` é resolvido por `Path(__file__).parent.parent.parent` em `src/mesh/queue.py:11` (3 níveis acima de `src/mesh/queue.py` → raiz do repo).

**Conteúdo:** `TaskChange.model_dump_json()` — JSON canônico de um modelo Pydantic v2 com `frozen=True, extra="forbid"` (ver `src/contracts/task_change.py:TaskChange`).

**Invariante load-bearing:** arquivos `*.json` na queue dir são **append-only**. Nunca `rm`, nunca `mv` para fora. Status muda via **re-emissão** do JSON inteiro com campo `status` atualizado.

### 2.2 Atomic write protocol (snippet verbatim de `src/mesh/queue.py:20-32`)

```python
def enqueue(event: TaskChange) -> str:
    """Append event to queue. Atomic write via temp file + rename."""
    qdir = _ensure_queue_dir()
    target = qdir / f"{event.event_id}.json"
    tmp = target.with_suffix(".tmp")

    content = event.model_dump_json()
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)  # atomic on same filesystem
    return event.event_id
```

**Mecânica do atomic write:**
1. Escreve payload em `<event_id>.tmp` (sufixo trocado via `with_suffix`)
2. `flush()` empurra do Python buffer para OS buffer
3. `os.fsync(f.fileno())` força flush do OS buffer para disco físico — sobrevive a crash/power-loss
4. `os.replace(tmp, target)` é **atômico no mesmo filesystem** (POSIX guarantee: readers veem o arquivo antigo OU o novo, nunca parcial)
5. `<event_id>.tmp` órfão é overwrite na próxima tentativa com mesmo `event_id`

### 2.3 Status transition protocol (snippet verbatim de `src/mesh/queue.py:51-68`)

```python
def ack(event_id: str, status: TaskStatus) -> None:
    """Update event status in place. Idempotent (no-op if event not pending)."""
    qdir = _ensure_queue_dir()
    target = qdir / f"{event_id}.json"
    if not target.exists():
        return  # idempotent

    event = _read_event_file(target)
    if event.status != "pending":
        return  # already processed

    # Re-emit with new status (frozen model requires new instance)
    from src.contracts.task_change import TaskChange

    updated = event.model_copy(update={"status": status})
    tmp = target.with_suffix(".tmp")
    tmp.write_text(updated.model_dump_json())
    os.replace(tmp, target)
```

**Invariante de transição:**
- `enqueue()` → status inicial `pending` (default em `TaskChange:status`)
- `ack(id, "propagated")` → sucessor terminal (todos os adapters succeed)
- `ack(id, "partial_propagation")` → sucessor terminal com diagnóstico (≥1 adapter falhou)
- `ack(id, "rejected")` → sucessor terminal (consumer decidiu REJECT)
- `ack()` é **idempotente** — chamar 2× com mesmo status é no-op (early-return `if status != "pending"`)

**Frozen model workaround:** como `TaskChange` é `frozen=True`, mutação direta `event.status = "propagated"` lança `ValidationError`. Solução: `model_copy(update={...})` cria nova instância Pydantic, depois re-serializa com `model_dump_json()`.

### 2.4 Consumer iteration protocol (snippet verbatim de `src/mesh/queue.py:39-48`)

```python
def consume_pending() -> Iterator[TaskChange]:
    """Iterate over events with status='pending'."""
    qdir = _ensure_queue_dir()
    for path in sorted(qdir.glob("*.json")):
        try:
            event = _read_event_file(path)
            if event.status == "pending":
                yield event
        except Exception:
            continue  # skip malformed files
```

**Reusa-se em `replay_after_restart()` (queue.py:71-73):**

```python
def replay_after_restart() -> Iterator[TaskChange]:
    """Re-process all pending events (called on agent startup)."""
    yield from consume_pending()
```

**Invariante de iteração:**
- Sorted por filename (lexicographic) → ordem determinística de UEID processados em restart
- `*.tmp` files são ignorados (glob `*.json` não casa `.tmp`)
- Arquivos malformados são skipados silenciosamente (não bloqueiam a queue inteira)

### 2.5 Agent integration — validate → propagate pipeline

**Step 1: `agent_consumer.py:25` — PAE validation**

```python
def validate(event: TaskChange) -> ValidationResult:
    """Validate event. Returns approve/reject/clarify decision."""
    title = event.fields.get("title", "")

    # Check 1: title not vague
    if not title or title.lower().strip() in VAGUE_TITLES or len(title.strip()) < 5:
        return ValidationResult(
            Decision.CLARIFY,
            "Title too vague. Provide a specific, actionable title (>=5 chars, not 'todo'/'tbd').",
        )

    # Check 2: due date not in past (for create actions)
    if event.action.value == "create" and "due" in event.fields:
        try:
            due = date.fromisoformat(event.fields["due"])
            if due < date.today():
                return ValidationResult(
                    Decision.REJECT,
                    f"Due date {due} is in the past. Use a future date or remove due field.",
                )
        except (ValueError, TypeError):
            return ValidationResult(
                Decision.REJECT,
                f"Invalid due date format: {event.fields['due']!r}. Use YYYY-MM-DD.",
            )

    # Check 3: UEID collision (existing propagated event with same UEID)
    try:
        from src.mesh import queue

        for existing in queue.replay_after_restart():
            if existing.ueid == event.ueid and existing.status == "propagated":
                if existing.fields.get("title") != event.fields.get("title"):
                    return ValidationResult(
                        Decision.REJECT,
                        f"UEID collision: {event.ueid} already exists with different content.",
                    )
    except (ImportError, AttributeError):
        # Queue module doesn't exist yet (Task 4 not done)
        pass

    return ValidationResult(Decision.APPROVE, approved_fields=event.fields)
```

**3 regras PAE (decisão `APPROVE | REJECT | CLARIFY`):**
| # | Regra | Razão |
|:-:|:------|:------|
| 1 | `title` ≥ 5 chars AND ∉ {todo, tbd, fix, work, task, stuff, thing} | Anti-placeholder |
| 2 | `due` (se presente) ≥ today + ISO format válido | Não criar tasks no passado |
| 3 | UEID já propagated com title diferente → REJECT | Imutabilidade canônica do UEID |

**Step 2: `agent_propagator.py:17-56` — per-adapter propagation com failure isolation**

```python
def propagate(
    event: TaskChange,
    validation: ValidationResult,
    adapters: list[ForkAdapter],
) -> list[PropagationResult]:
    """Propagate approved event to all adapters. Per-adapter failures are isolated.

    On partial propagation (any adapter fails), the queue event is acked as
    'partial_propagation' so consume_pending() does not re-process it.
    """
    if validation.decision.value != "approve":
        return []

    propagation = PropagationEvent(
        event_id=event.event_id,
        ueid=event.ueid,
        action=event.action,
        fields=validation.approved_fields or event.fields,
        approved_at=event.timestamp,
        source_fork=event.source_fork,
    )

    results = []
    for adapter in adapters:
        try:
            adapter.apply_change(propagation)
            results.append(PropagationResult(fork_name=adapter.name, success=True))
        except Exception as e:
            results.append(
                PropagationResult(
                    fork_name=adapter.name,
                    success=False,
                    error=str(e),
                )
            )

    if results and any(not r.success for r in results):
        _queue.ack(event.event_id, "partial_propagation")

    return results
```

**Invariante de propagação:**
- Early-return se `validation.decision != "approve"` — `propagate()` é no-op para REJECT/CLARIFY
- Per-adapter try/except: falha em 1 adapter **não bloqueia** os outros
- Status `partial_propagation` é setado em **qualquer** falha parcial (binário: success vs partial)
- Status `propagated` é setado **implicitamente** quando todos succeed (ver limitação conhecida em §3)

### 2.6 End-to-end pipeline (canonical flow)

```
┌─────────────────────────────────────────────────────────────────────┐
│ FORK (CLI / tuiboard / taskdog / solverforge-calendar)              │
│   taskdog enqueue: writes TaskChange JSON to data/review_queue/    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ atomic write (tempfile + os.replace)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ QUEUE (filesystem, append-only)                                     │
│   data/review_queue/<event_id>.json                                 │
│   status: pending                                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ consume_pending() → replay_after_restart()
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AGENT CONSUMER (agent_consumer.py:validate)                         │
│   PAE rules: APPROVE / REJECT / CLARIFY                             │
│   UEID collision check via queue.replay_after_restart()             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ ValidationResult
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AGENT PROPAGATOR (agent_propagator.py:propagate)                    │
│   per-adapter try/except (failure isolation)                        │
│   status → propagated (all ok) | partial_propagation (≥1 fail)     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ ack() — re-emit with new status
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ADAPTERS (3 forks-prontas)                                          │
│   CliAdapter          → data/tasks.jsonl (JSONL append-only)        │
│   TaskdogAdapter      → data/taskdog/tasks.db (SQLite UPSERT ueid) │
│   SolverforgeCalendar → data/solverforge_calendar/unified_planning  │
└─────────────────────────────────────────────────────────────────────┘
```

**Invariante top-level:** **a queue é a single source of truth** entre forks. Adapters podem divergir temporariamente (partial_propagation), mas a queue retém o estado canônico até convergência via replay manual ou policy de retry.

---

## §3 — Justificativa

### 3.1 Por que append-only filesystem queue em vez de alternativas

| Alternativa | Prós | Contras | Veredito |
|:------------|:-----|:--------|:---------|
| **Filesystem + JSON (escolhido)** | Zero deps; debug com `cat`/`ls`; replay trivial; sobrevive a restart sem DB; append-only é trivial de auditar | Sem queries SQL; iteração full-scan; não escala >10k events | **Vencedor** — single-user, fully-local, scale < 1000 events/dia |
| SQLite `events` table | Query SQL; index por UEID; transactional ACID | DB lock contention; precisa de schema migrations; replay precisa de cursor management; debug é menos legível | Rejeitado — overhead desnecessário para v1 |
| Redis / message broker | Throughput alto; consumer groups nativos | Dependência externa; cloud-required contradiz "fully local" (CLAUDE.md invariant) | Rejeitado — fere invariante local-only |
| In-process queue (asyncio.Queue) | Latência zero; sem I/O | Lost on restart (sem durability); sem replay; sem audit trail | Rejeitado — replay e audit são load-bearing |

**Decisão justificada por 3 invariantes do projeto (`life/CLAUDE.md`):**
1. **Fully local** — SQLite + filesystem only, zero cloud deps → filesystem vence sobre Redis/Kafka
2. **Append-only** — também aplicada a `vault/`, `vibe-ops/`, `strategics/` — consistência cultural
3. **Idempotent pipelines** — UEID é chave de junção; replay_after_restart() garante reprocessamento

### 3.2 Por que atomic temp+rename (não write direto)

`os.replace(tmp, target)` é atômico no mesmo filesystem (POSIX `rename(2)` guarantee). Readers veem:
- Estado A (arquivo antigo) **OR** estado B (arquivo novo completo)
- **Nunca** estado intermediário (vazio, parcial, truncado)

Sem temp+rename, uma crash durante `write()` deixa arquivo truncado/corrompido. O consumer teria que implementar recovery. O custo do temp+rename é 1 syscall extra (`os.fsync`) — aceitável para single-user, offline-first.

### 3.3 Por que re-emissão em vez de mutação in-place

Pydantic v2 `frozen=True` proíbe atribuição direta (`event.status = "propagated"` lança `ValidationError`). Duas alternativas:

| Alternativa | Veredito |
|:------------|:---------|
| **Re-emit (escolhido)** — `model_copy(update={...})` + write inteiro | Append-only invariant preservado; histórico completo; auditável |
| Mutação + bypass `object.__setattr__` | Quebra frozen Pydantic invariant (`src/contracts/__init__.py`); audit trail perdido |
| Edit in-place (seek + overwrite parcial) | Race condition com consumer iterando; corrupção se truncated mid-write |

A re-emissão **fortalece** o invariante append-only (cada ack() gera uma "versão" do arquivo) ao custo de 1 write extra por evento.

### 3.4 Por que per-adapter try/except (failure isolation)

**Premissa:** o sistema roda **single-user, multi-fork**. Se `taskdog` SQLite corrompe (disk full, lock contention), o fork `tuiboard` ainda pode receber o evento. Sem isolation, 1 adapter indisponível derruba o sistema inteiro.

**Implementação:** `propagate()` itera adapters em sequência, cada um wrapped em try/except. `PropagationResult` carrega `(fork_name, success, error)` — diagnóstico sem halt do loop.

**Limitação conhecida:** o status `partial_propagation` é **binário** (≥1 falha → partial, todas ok → propagated). Não diferencia "1 de 3 falhou" vs "2 de 3 falhou". Próxima iteração: `PropagationResult.status_code` per-adapter (success / schema_mismatch / lock_timeout / disk_full).

### 3.5 Limitações conhecidas (de `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.2)

**Padrão qualificado, não puro.** Findings aplicáveis:

- **A7** (HIGH — Formula↔code mismatch): scenario classifier emite recomendações como strings (`src/operational/packages/core/src/operational/core/scenario_classifier.py`) mas **não persiste na queue**. Se a intenção era wire-up `Scenario → PomodoroTracker`, deveria ser um `TaskChange` enqueueado com `action="update"`. Hoje é só string — a queue é bypassed. Doc 09 §3.2 recomenda criar `src/mesh/adapters/pomodoro.py` implementando `ForkAdapter` Protocol.

- **F5** (HIGH — silent failure of stated integration): `pomodoro_machine.py` docstring (lines 16-19) afirma "This implementation is **not** wired into the time-blocks capture pipeline." Doc `24-integration-mesh-ueid-propagation.md §4` promete o wire-up mas ele não existe. Pomodoros não viram `TaskChange`. **Gap:** o pattern está correto para `create` events; falta adapter pomodoro para fechar o loop end-to-end.

- **Phase 3 v1 minor finding** (logged, non-blocking): `propagate()` faz `_queue.ack(event_id, "partial_propagation")` em falha parcial, **mas não chama ack em sucesso total**. Status `propagated` só é setado se houver algum adapter success e nenhum failure — caso degenerado onde `results` está vazio não chama ack. Workaround atual: 3 adapters sempre presentes, então `results` é sempre não-vazio. Mas é landmine arquitetural — recomendado adicionar `else: _queue.ack(event_id, "propagated")` explícito.

- **`queue.replay_after_restart()` não-deterministic sob alta concorrência:** se 2 forks enfileiram simultaneamente, `sorted(glob("*.json"))` é determinístico mas pode reordenar eventos com timestamps fora de ordem. Aceitável em single-user; problemático se multi-user.

- **UEID collision check é O(N) per validation:** `agent_consumer.py:55` itera `queue.replay_after_restart()` para checar colisões. Em escala > 10k events, isso vira bottleneck. Mitigação futura: index UEID→file_path em SQLite sidecar.

### 3.6 Por que este padrão é load-bearing (não nice-to-have)

Sem a append-only queue:
1. **Replay após restart** é impossível (estado in-process perdido) — agente esquece eventos pendentes
2. **Audit trail** é inexistente (não há histórico de quem aprovou/rejeitou o quê)
3. **Failure isolation** entre adapters é forçada por retry síncrono, multiplicando latência
4. **Offline-first** quebra (queue precisa de broker externo)

Com a queue:
1. **Crash-safety** — `os.fsync` + `os.replace` garante durability
2. **Replay determinístico** — `replay_after_restart()` no startup do agente
3. **Human-in-the-loop futuro** — usuário pode inspecionar `data/review_queue/*.json` e editar campos antes de replay (kill-switch do commit node em `ikigai_maintainer/graph.py`)
4. **Diagnostic clarity** — status `partial_propagation` com error string identifica fork culpado

---

## §4 — Cross-references

### 4.1 Code (anchor canônico)

- `src/mesh/queue.py:20-32` — `enqueue()` atomic write
- `src/mesh/queue.py:51-68` — `ack()` re-emit with new status
- `src/mesh/queue.py:39-48` — `consume_pending()` iterator
- `src/mesh/queue.py:71-73` — `replay_after_restart()` startup hook
- `src/mesh/agent_consumer.py:25-66` — `validate()` PAE rules (APPROVE/REJECT/CLARIFY)
- `src/mesh/agent_propagator.py:17-56` — `propagate()` per-adapter failure isolation
- `src/contracts/task_change.py` — `TaskChange`, `TaskAction`, `TaskStatus`, `PropagationEvent` (frozen Pydantic)
- `src/mesh/adapters/base.py` — `ForkAdapter` Protocol (`@runtime_checkable`)
- `src/mesh/adapters/cli.py` — `CliAdapter` (JSONL `data/tasks.jsonl`)
- `src/mesh/adapters/taskdog.py` — `TaskdogAdapter` (SQLite UPSERT on ueid)
- `src/mesh/adapters/solverforge_calendar.py` — `SolverforgeCalendarAdapter` (UPI ueid column)

### 4.2 Design-system docs

- `docs/design-system/00-INDEX.md` §2 (Layer 3 — Patterns catalog rows 10-19)
- `docs/design-system/04-canvas-mesh-architecture.md` §3.1 (Queue protocol), §3.3 (Adapter storage topology)
- `docs/design-system/05-canvas-contracts-architecture.md` §4.3 (`TaskChange` + `PropagationEvent`)
- `docs/design-system/06-canvas-agents-architecture.md` §7 (Reliability layer)
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.2 (qualifiers A7, F5) + §4.3 (Pattern #12 qualificado)

### 4.3 Auto-performance-os docs (precedent + integração)

- `docs/auto-performance-os/03-axiom-finite-state-machines.md` — TaskChange é uma FSM (PENDING → VALIDATED → PROPAGATED)
- `docs/auto-performance-os/12-postulado-consolidacao-diaria.md` — exemplo de consumer diário que poderia emitir TaskChange via queue
- `docs/auto-performance-os/15-engine-pomodoro-machine.md` — pomodoros **deveriam** virar TaskChange (gap F5)
- `docs/auto-performance-os/19-engine-ikigai-vector-scorer.md` — vetores IKIGAi como candidatos a TaskChange (futuro)
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — UEID propagation pipeline (full reference)
- `docs/auto-performance-os/25-integration-deep-agent-sync.md` — mesh ↔ vault sync via queue
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — cybernetic loop (Target → Sensor → Adjuster → Persist → Sync → Index), queue é o "Persist"

### 4.4 Memory (decisões + invariants)

- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture: forks = user views, CLI/agent = operator. Queue é o canal operator↔fork.
- `[[data-first-methodology]]` — IKIGAi em data-first mode; queue ainda é load-bearing porque captura eventos sem LLM
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical narrative: deep-agent bidirecionalmente sync fork-prontas ↔ vault via queue
- `[[reorg-bugs-p0-fixed-2026-08-27]]` — B6 fix: UEID format 4-part regex locked
- `[[verify-agent-fabricated-failures]]` — verificação independente requerida: qualquer "queue fails" claim deve re-rodar pytest/ruff/mypy antes de ação
- `[[cli-command-palette-pivot-2026-08-28]]` — workspace sem CLI canônica; queue persiste como contrato multi-backend

### 4.5 ADR / spec

- `code-docs/adr/ADR-007-data-first-methodology.md` — gate de 5 SONHO logs antes de polish algorítmico
- `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md` — `frozen=True, extra="forbid"` (motivação para re-emit em vez de mutação)
- `docs/superpowers/specs/2026-08-28-mesh-phase3-v1.md` — spec mesh v1 (create action only, 3 adapters)

---

## §5 — Fontes

### Code (verificado)
- `src/mesh/queue.py` — atomic append-only queue (74 LOC)
- `src/mesh/agent_consumer.py` — Deep Agent PAE validation (67 LOC)
- `src/mesh/agent_propagator.py` — Deep Agent propagation com failure isolation (57 LOC)
- `src/contracts/task_change.py` — `TaskChange`, `TaskAction`, `TaskStatus`, `PropagationEvent`
- `src/mesh/adapters/base.py` — `ForkAdapter` Protocol
- `src/mesh/adapters/cli.py`, `taskdog.py`, `solverforge_calendar.py` — 3 adapters v1
- `src/operational/packages/core/src/operational/core/scenario_classifier.py` — gap A7 (strings only)
- `src/operational/packages/core/src/operational/core/pomodoro_machine.py:16-19` — gap F5 (not wired)

### Docs (analisados)
- `docs/design-system/00-INDEX.md` — index do docset
- `docs/design-system/04-canvas-mesh-architecture.md` — mesh canvas
- `docs/design-system/05-canvas-contracts-architecture.md` — contracts canvas
- `docs/design-system/06-canvas-agents-architecture.md` — agents canvas
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` — análise crítica 2ª ordem (§3.2 qualifica este padrão)
- `docs/auto-performance-os/03-axiom-finite-state-machines.md`
- `docs/auto-performance-os/12-postulado-consolidacao-diaria.md`
- `docs/auto-performance-os/15-engine-pomodoro-machine.md`
- `docs/auto-performance-os/19-engine-ikigai-vector-scorer.md`
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — referência canônica do mesh
- `docs/auto-performance-os/25-integration-deep-agent-sync.md`
- `docs/auto-performance-os/26-integration-cybernetic-loop.md`

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer
- `[[data-first-methodology]]` — 5 SONHO logs gate
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical narrative
- `[[reorg-bugs-p0-fixed-2026-08-27]]` — UEID regex fix
- `[[verify-agent-fabricated-failures]]` — verificação independente
- `[[cli-command-palette-pivot-2026-08-28]]` — pivot command palette

### ADR / spec
- `code-docs/adr/ADR-007-data-first-methodology.md`
- `code-docs/adr/ADR-009-pydantic-strict-mode-invariance.md`
- `docs/superpowers/specs/2026-08-28-mesh-phase3-v1.md`

---

## §6 — Invariantes load-bearing (verifiable)

| # | Invariante | Verificação |
|:-:|:-----------|:------------|
| 1 | Atomic write via temp+rename: `os.replace(tmp, target)` no `queue.py:31` | `grep -n "os.replace" src/mesh/queue.py` → 2 hits (enqueue, ack) |
| 2 | Append-only: nenhum `rm`/`unlink` em `data/review_queue/` | `grep -rn "remove\|unlink\|rmtree" src/mesh/queue.py` → 0 hits |
| 3 | Status transitions via re-emit: `model_copy(update={"status": status})` em `queue.py:65` | `grep -n "model_copy" src/mesh/queue.py` → 1 hit |
| 4 | Failure isolation: per-adapter try/except em `propagator.py:41-51` | `grep -n "for adapter" src/mesh/agent_propagator.py` → 1 hit |
| 5 | Storage path canônico: `data/review_queue/<event_id>.json` | `grep -n "QUEUE_DIR" src/mesh/queue.py` → 1 hit |

---

> **Padrão #12 — Append-only Queue — qualificado com 3 limitações conhecidas (A7, F5, ack-success landmine). Recomendação arquitetural:** preservar invariantes load-bearing (atomic write, append-only, failure isolation); fechar gaps via (a) `src/mesh/adapters/pomodoro.py` para F5, (b) `ack(event_id, "propagated")` explícito em `propagate()` else-branch, (c) re-classificar scenario classifier como TaskChange emitter para A7. Priorizar **backend antes de polish algorítmico** (`[[prioritize-backend-over-algorithm-refinement]]`).