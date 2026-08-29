# 13 — Pattern: ForkAdapter Protocol (Cross-Fork Storage Contract)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** Pattern #13 (Layer 3 — Patterns Catalog)
> **Anchor canônico:** `src/mesh/adapters/base.py` + `src/mesh/adapters/{cli,taskdog,solverforge_calendar}.py`
> **Origem:** Phase 3 v1 mesh readiness (synthesis 2026-08-28) + análise crítica segunda ordem (F5)
> **Idioma:** PT-BR prose + EN technical terms (UEID, Pydantic, Protocol, @runtime_checkable, UPSERT, PK, JSONL, FK)
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Intuição

O **ForkAdapter Protocol** é o contrato mínimo que todo fork-pronta (tuiboard, taskdog, solverforge-calendar e futuros) deve implementar para participar da data mesh. Sua intuição é **duck typing estrutural via `typing.Protocol`** com `@runtime_checkable` — qualquer classe que exponha `name`, `read(ueid)`, `apply_change(event)`, `supports_field(field_name)` é um adapter válido, sem herança explícita. O protocolo ancora a tese de **idempotência universal**: chamar `apply_change` duas vezes com o mesmo `PropagationEvent` deve ter o mesmo efeito que chamar uma vez — propriedade que permite replay seguro após restart, convergência eventual em fork offline, e per-adapter failure isolation sem bloqueio em cascata. É o elo arquitetural que sustenta o **UEID-UNIQUE pattern**: o mesmo UEID canônico vira coluna `UNIQUE` em três storages heterogêneos (JSONL append-only, SQLite com UPSERT nativo, SQLite com PK reuse), permitindo que a mesma task exista em múltiplas visualizações simultaneamente.

---

## §2 — Enunciado formal

### 2.1 Protocol definition (verbatim de `src/mesh/adapters/base.py`)

```python
@runtime_checkable
class ForkAdapter(Protocol):
    """Every fork adapter implements read() + apply_change() + supports_field()."""
    name: str

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        """Return slice for this UEID, or None if not found."""
        ...

    def apply_change(self, event: PropagationEvent) -> None:
        """Apply change to fork store. Idempotent (safe to retry)."""
        ...

    def supports_field(self, field_name: str) -> bool:
        """Return True if this adapter persists this field."""
        ...
```

**Invariantes carregadas pelo protocolo (3):**

| # | Invariante | Verificável |
|:--|:-----------|:-----------|
| I1 | `apply_change(event)` idempotente: 2× com mesmo `event.ueid` ≡ 1× | por leitura de cada adapter abaixo |
| I2 | `read(ueid)` retorna `None` se UEID ausente; nunca levanta exceção | `cli.py:22`, `taskdog.py:32`, `solverforge_calendar.py:22` (todos checam `.exists()` antes de query) |
| I3 | `supports_field(field)` é declaração estática (set literal) — não introspecção runtime | `cli.py:14`, `taskdog.py:13-23`, `solverforge_calendar.py:14` (módulos-level `SUPPORTED_FIELDS`) |

### 2.2 CliAdapter — JSONL append-only com atomic temp+rename

`CliAdapter` persiste em `data/tasks.jsonl` (JSONL append-only). A idempotência vem de duas camadas: (1) o protocolo `PropagationEvent` carrega o UEID como identidade, e (2) o storage é append-only sem UNIQUE constraint — o que significa que re-chamadas produzem **linhas duplicadas** (não convergência). Este é um trade-off conhecido: simplicidade de write > deduplicação rigorosa. Ver §3 para limitation analysis.

```python
# src/mesh/adapters/cli.py (verbatim)
def apply_change(self, event: PropagationEvent) -> None:
    if event.action.value != "create":
        return  # v1 only supports create

    TASKS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ueid": event.ueid,
        "title": event.fields.get("title"),
        "due": event.fields.get("due"),
        "priority": event.fields.get("priority", "medium"),
        "written_at": event.approved_at.isoformat(),
        "source_fork": event.source_fork,
    }
    line = json.dumps(record) + "\n"

    # Atomic append via temp + rename (works on Windows + Unix)
    tmp = TASKS_JSONL.with_suffix(".tmp")
    existing = TASKS_JSONL.read_text() if TASKS_JSONL.exists() else ""
    tmp.write_text(existing + line)
    os.replace(tmp, TASKS_JSONL)
```

**Storage topology:**

| Aspect | Valor |
|:-------|:------|
| Path | `data/tasks.jsonl` (relativo a `PROJECT_ROOT`) |
| Schema | JSON Lines: `{ueid, title, due, priority, written_at, source_fork}` |
| Concurrency | Atomic `temp + os.replace` (Windows + POSIX-safe) |
| Idempotency key | UEID (mas sem dedup — ver §3 limitação) |
| SUPPORTED_FIELDS | `{title, due, priority, ueid, written_at, source_fork}` |

### 2.3 TaskdogAdapter — SQLite com UPSERT nativo

`TaskdogAdapter` usa o **idempotent UPSERT idiom** do SQLite (`INSERT ... ON CONFLICT(ueid) DO UPDATE`). Aqui a idempotência é **garantida pelo schema**: `ueid UNIQUE` no DDL força o SQLite a fazer upsert em vez de criar duplicata. É o adapter mais próximo do "ForkAdapter ideal" porque combina simplicidade (1 SQL statement) com semântica correta (convergência por chave).

```python
# src/mesh/adapters/taskdog.py (verbatim, abreviado)
def apply_change(self, event: PropagationEvent) -> None:
    if event.action.value != "create":
        return  # v1 only supports create

    TASKDOG_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(TASKDOG_DB)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ueid TEXT UNIQUE,
                name TEXT,
                status TEXT,
                priority INTEGER,
                planned_start TEXT,
                planned_end TEXT,
                deadline TEXT,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
        """)

        priority = event.fields.get("priority")
        if isinstance(priority, str):
            priority_map = {"high": 1, "medium": 2, "low": 3}
            priority = priority_map.get(priority.lower(), 2)

        conn.execute(
            """INSERT INTO tasks (ueid, name, status, priority, deadline, created_at)
               VALUES (?, ?, 'planned', ?, ?, ?)
               ON CONFLICT(ueid) DO UPDATE SET
                   name=excluded.name,
                   priority=excluded.priority,
                   deadline=excluded.deadline""",
            (event.ueid, event.fields.get("title"), priority,
             event.fields.get("due"), event.approved_at.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
```

**Storage topology:**

| Aspect | Valor |
|:-------|:------|
| Path | `data/taskdog/tasks.db` |
| Schema | `tasks(id PK AUTOINCREMENT, ueid UNIQUE, name, status, priority, planned_start, planned_end, deadline, created_at)` |
| Concurrency | Single-writer (SQLite); UPSERT atômico por statement |
| Idempotency key | UEID UNIQUE constraint (DB-enforced) |
| SUPPORTED_FIELDS | `{title, due, priority, status, ueid, planned_start, planned_end, actual_end, tags}` |

### 2.4 SolverforgeCalendarAdapter — UPI com PK reuse

`SolverforgeCalendarAdapter` é o caso mais sutil: o UPI (`unified_planning_items`) tem `id TEXT PRIMARY KEY` (fork-internal) **separado** de `ueid TEXT UNIQUE` (canônico join key). A idempotência vem de uma **SELECT-then-INSERT/UPDATE** branch:

```python
# src/mesh/adapters/solverforge_calendar.py (verbatim, abreviado)
def apply_change(self, event: PropagationEvent) -> None:
    if event.action.value != "create":
        return  # v1 only supports create

    UPI_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(UPI_DB)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS unified_planning_items (
                id TEXT PRIMARY KEY,
                ueid TEXT UNIQUE,
                status TEXT,
                start_at TEXT,
                end_at TEXT,
                blocked_by TEXT,
                tags TEXT,
                ikigai TEXT,
                provenance TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_upi_ueid ON unified_planning_items(ueid);
        """)

        ikigai = {
            "title": event.fields.get("title"),
            "due": event.fields.get("due"),
            "source_fork": event.source_fork,
            "approved_at": event.approved_at.isoformat(),
        }
        ikigai_json = json.dumps(ikigai)

        # PK stability: ueid é o canonical join key; id é fork-internal.
        # On re-runs with the same UEID, reuse the existing id instead of
        # generating a fresh one (preserva history, previne PK churn).
        existing_id = conn.execute(
            "SELECT id FROM unified_planning_items WHERE ueid = ?",
            (event.ueid,),
        ).fetchone()

        if existing_id is not None:
            conn.execute(
                """UPDATE unified_planning_items
                   SET status = 'planned', ikigai = ?
                   WHERE ueid = ?""",
                (ikigai_json, event.ueid),
            )
        else:
            new_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO unified_planning_items (id, ueid, status, blocked_by, tags, ikigai, provenance)
                   VALUES (?, ?, 'planned', '[]', '[]', ?, '{}')""",
                (new_id, event.ueid, ikigai_json),
            )
        conn.commit()
    finally:
        conn.close()
```

**Storage topology:**

| Aspect | Valor |
|:-------|:------|
| Path | `data/solverforge_calendar/unified_planning.db` |
| Schema | `unified_planning_items(id PK TEXT, ueid UNIQUE, status, start_at, end_at, blocked_by, tags, ikigai, provenance)` |
| Concurrency | Single-writer; SELECT-then-INSERT/UPDATE em transação implícita |
| Idempotency key | UEID UNIQUE (DB-enforced) + PK reuse no `id` |
| SUPPORTED_FIELDS | `{title, status, start_at, end_at, rrule, blocked_by, tags, ueid}` |

### 2.5 Padrão UEID-UNIQUE (3 storages, 1 chave)

A **convenção recorrente** nos três adapters é que `ueid` é coluna `UNIQUE` em todas as tabelas, e o `id` interno do fork (quando existe) é PK separada. Isso permite **trocar UEID sem perder identidade** (cenário de migration de schema futuro) e garante que um fork possa responder "já tenho esse UEID" via `SELECT ... WHERE ueid = ?` antes de aceitar um novo write.

| Adapter | UEID storage | Idempotency mechanism |
|:--------|:-------------|:----------------------|
| `CliAdapter` | campo `ueid` em cada line JSONL | **nenhuma** (append-only, sem dedup) |
| `TaskdogAdapter` | coluna `ueid UNIQUE` | SQLite UPSERT via `ON CONFLICT(ueid) DO UPDATE` |
| `SolverforgeCalendarAdapter` | coluna `ueid UNIQUE` + `id TEXT PK` | SELECT-then-INSERT/UPDATE (PK reuse) |

---

## §3 — Justificativa

### 3.1 Por que `Protocol` em vez de ABC?

`typing.Protocol` com `@runtime_checkable` permite **structural subtyping** (duck typing estático). Não há `class CliAdapter(ForkAdapter)` — basta a classe expor os 4 membros com signatures compatíveis. Vantagens:

1. **Zero coupling**: cada adapter vive em arquivo separado sem precisar importar a base
2. **IDE type-checking**: mypy valida conformidade sem herança
3. **Runtime check**: `isinstance(adapter, ForkAdapter)` funciona (graças a `@runtime_checkable`)
4. **Testabilidade**: mocks podem implementar o Protocol sem subclass

Alternativas rejeitadas:
- **ABC com `abstractmethod`**: força herança, cria acoplamento vertical, dificulta mock isolation
- **Duck typing puro (sem Protocol)**: perde static type safety, mypy não detecta drift de signature
- **Plugin registry com auto-discovery**: over-engineering para 3 adapters; complica testes

### 3.2 Por que `@runtime_checkable`?

Permite que o propagator (`src/mesh/agent_propagator.py`) faça `for adapter in adapters: ... isinstance(adapter, ForkAdapter)` se quiser defesa em profundidade. Hoje o propagator confia na lista `adapters: list[ForkAdapter]` (typing-level), mas o `@runtime_checkable` é **rede de segurança** para casos onde adapters são injetados via DI ou plugin loader.

### 3.3 Por que `apply_change` MUST ser idempotente?

A propagação opera em **3 fases com 3 failure modes**:

1. **Happy path**: 1 chamada, 3 adapters, 3 sucessos
2. **Partial failure**: 1 chamada, adapter X falha, Y e Z processam; queue fica `partial_propagation`
3. **Replay**: agent restart reprocessa pending events; cada adapter recebe o **mesmo** `PropagationEvent` novamente

Em (3), se `apply_change` não fosse idempotente, o replay criaria **duplicatas** (no caso do JSONL) ou **PK churn** (no caso do UPI). A idempotência garante **convergência eventual**: replay → mesmo estado final que happy path.

Este é o invariante que viabiliza o **append-only queue** (`data/review_queue/`): se a queue é append-only e os adapters são idempotentes, então qualquer replay converge.

### 3.4 Por que UEID UNIQUE em vez de FK cross-fork?

Cross-fork **foreign keys** entre `data/tasks.jsonl`, `data/taskdog/tasks.db`, e `data/solverforge_calendar/unified_planning.db` exigiriam:
- Sincronização de DBs (multi-database transactions — não suportado em SQLite)
- Schema coordination (qualquer migration quebra os 3)
- Causalidade temporal (qual é o source-of-truth?)

A escolha de **UEID como logical join key** (sem FK físico) é pragmática:
- **Convergência eventual**: cada fork tem seu próprio `ueid UNIQUE` local; cross-fork join é via mesh reader
- **Schema independence**: cada fork evolui independentemente (taskdog pode adicionar colunas sem afetar solverforge)
- **Drift tolerance**: fork X pode estar 1 dia defasado do fork Y; ambos retornam o "mesmo" UEID

### 3.5 Limitações conhecidas (de `09-analise-critica-segunda-ordem-arquitetura.md` §3.3)

A análise crítica de segunda ordem identificou **1 issue HIGH** e **2 issues de schema** relevantes a este padrão:

#### F5 — Silent failure: pomodoro adapter ausente
> "fork pomodoro não existe. Não há adapter, não há fork, não há Protocol instance. Doc 24 §4 afirma integração `pomodoro → TaskChange → mesh` mas nenhum adapter implementa `ForkAdapter` para pomodoros."

`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md §4` cita "15-engine-pomodoro-machine — pomodoros viram TaskChange → mesh", mas `pomodoro_machine.py:16-19` declara explicitamente "not wired into the time-blocks capture pipeline". O ForkAdapter Protocol está completo para tasks, mas não cobre pomodoros/habits/study_sessions — que são os outros 3 sinais de feedback do modelo unificado (Layer C, `10-modelo-unificado-auto-feedback-estocastico.md §2`).

**Recomendação:** introduzir `src/mesh/adapters/pomodoro.py`, `habit.py`, `study_session.py` implementando `ForkAdapter`. Hoje, este pattern é **parcialmente aplicado** — 3 adapters para 1 dos 4 signals de feedback.

#### Limitação L1 — `CliAdapter` não é idempotente na prática
O Protocol declara `apply_change` como idempotente, mas `CliAdapter.apply_change` faz **append** sem dedup. Em replay, o `data/tasks.jsonl` cresce com linhas duplicadas para o mesmo UEID. O Protocol `read()` retorna a **primeira** ocorrência (`for line in TASKS_JSONL.read_text().splitlines(): if task.get("ueid") == ueid: return task` — primeira match wins), mas o arquivo acumula lixo.

**Recomendação:** ou (a) aceitar a limitação e documentar que JSONL é **append-only event log**, não fork state-of-truth; ou (b) adicionar dedup por UEID no write (rewrite file filter). A escolha (a) é mais alinhada com append-only invariant do sistema.

#### Limitação L2 — `partial_propagation` não auto-ack
`agent_propagator.py:53-55` ack apenas quando `results and any(not r.success for r in results)`. Se `results == []` (zero adapters), nenhum ack acontece — o evento fica pending para sempre. Edge case raro mas real (ex.: registry vazio durante bootstrap).

---

## §4 — Cross-references

### 4.1 Design system

- `docs/design-system/00-INDEX.md` §3 — mapa de dependências (Pattern #13 → ForkAdapter)
- `docs/design-system/04-canvas-mesh-architecture.md` §3.2 (Protocol verbatim) + §3.3 (storage topology table) + §6 (propagation semantics)
- `docs/design-system/05-canvas-contracts-architecture.md` §4.3 (TaskAction, TaskStatus, TaskChange, PropagationEvent) + §4.1 (UEID)
- `docs/design-system/06-canvas-agents-architecture.md` §3 (Deep Agent 18 tools, 4 taskdog + 4 tuiboard + 3 solverforge)
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3.3 (F5 — pomodoro fork ausente) + §3.4 (C4 — policy thresholds drift)

### 4.2 Auto-performance OS (matemática + integração)

- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` §2 (pipeline de propagação), §3 (justificativa não-técnica), §4 (consumidores downstream incluindo pomodoro — referência stale vs F5)
- `docs/auto-performance-os/00-INDEX.md` §1-§2 (stack conceitual: axiomas → postulados → engines → meta → integração)

### 4.3 Code (verificado)

- `src/mesh/adapters/base.py:8-23` — `@runtime_checkable class ForkAdapter(Protocol)`
- `src/mesh/adapters/cli.py:17-54` — `CliAdapter` (JSONL append-only)
- `src/mesh/adapters/taskdog.py:26-103` — `TaskdogAdapter` (SQLite UPSERT)
- `src/mesh/adapters/solverforge_calendar.py:17-104` — `SolverforgeCalendarAdapter` (UPI PK reuse)
- `src/mesh/agent_propagator.py:17-56` — propagação per-adapter com failure isolation
- `src/contracts/task_change.py:46-57` — `PropagationEvent` (frozen, extra=forbid)
- `src/contracts/common.py:30-43` — UEID 4-part regex

### 4.4 Memory

- `[[interfaces-architecture-2026-08-27]]` — forks = user views (Layer A); agent/CLI = operator (Layer B); ForkAdapter Protocol é o bridge
- `[[data-first-methodology]]` — ADR-007 gate de 5 SONHO logs; F5 não pode ser resolvido até empirical evidence
- `[[prioritize-backend-over-algorithm-refinement]]` — pomodoro adapter (F5) é backend build (não algorithm polish)
- `[[algorithm-issues-registry]]` — 31 inconsistencies + 12 novos findings em doc 09 (F5 incluso)
- `[[master-branch-carro-chefe-2026-08-28]]` — master = deep-agent bidirectionally syncing forks; ForkAdapter Protocol é o mecanismo
- `[[legacy-pav-ui-era-2026-08-28]]` — pomodoro machine é legado PAV-era; precisa de trailer SUPERSEDED + adapter fresh

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/mesh/adapters/base.py` (24 LOC) — Protocol definition
- `src/mesh/adapters/cli.py` (55 LOC) — CliAdapter JSONL
- `src/mesh/adapters/taskdog.py` (104 LOC) — TaskdogAdapter SQLite UPSERT
- `src/mesh/adapters/solverforge_calendar.py` (105 LOC) — SolverforgeCalendarAdapter UPI PK reuse
- `src/mesh/agent_propagator.py` (57 LOC) — per-adapter failure isolation
- `src/contracts/task_change.py` (58 LOC) — TaskChange, PropagationEvent, TaskAction enum
- `src/contracts/common.py` (260 LOC) — UEID Pydantic str subclass com regex 4-part

### Docs (analisados)
- `docs/design-system/00-INDEX.md` (113 LOC) — INDEX + Layer 3 patterns catalog
- `docs/design-system/04-canvas-mesh-architecture.md` (127 LOC) — mesh canvas com Protocol verbatim
- `docs/design-system/05-canvas-contracts-architecture.md` (160+ LOC) — contracts canvas
- `docs/design-system/06-canvas-agents-architecture.md` (200+ LOC) — agents canvas
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` (262 LOC) — análise crítica F5 + 46 findings
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` (200+ LOC) — Layer C = ForkAdapter
- `docs/auto-performance-os/00-INDEX.md` — 27 docs PT-BR template
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` (74 LOC) — UEID propagation integration

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture (forks vs operator)
- `[[data-first-methodology]]` — 5 SONHO logs gate
- `[[prioritize-backend-over-algorithm-refinement]]` — backend > algorithm
- `[[algorithm-issues-registry]]` — 31 inconsistencies + 12 novos (F1-F12)
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical master narrative
- `[[legacy-pav-ui-era-2026-08-28]]` — PAV-era superseded trailer pattern

### Métricas de cobertura
- **3 snippets Python reais** (verbatim): base.py Protocol + cli.py apply_change + taskdog.py apply_change + solverforge_calendar.py apply_change (= 4 snippets, excede mínimo 1-3)
- **5 invariantes carregadas** documentadas (3 do Protocol + 2 do UEID-UNIQUE pattern)
- **5 cross-refs design-system** (00, 04, 05, 06, 09)
- **2 cross-refs auto-performance-os** (00-INDEX, 24-integration)
- **6 cross-refs memory** (interfaces, data-first, prioritize-backend, algorithm-issues, master-branch, legacy-pav)
- **Honest rigor:** F5 (pomodoro ausente) + L1 (CliAdapter append-only sem dedup) + L2 (partial_propagation zero-adapter edge case) citados em §3.5