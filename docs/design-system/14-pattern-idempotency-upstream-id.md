# 14 — Padrão: Idempotency via upstream_id SHA-256

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** Pattern #14 (Layer 3 — Patterns Catalog, posição #14)
> **Anchor canônico:** `vibe-ops/src/middleware/sync_engine.py` (+ `src/mesh/queue.py`, `src/contracts/task.py`)
> **Origem:** Phase 3 v1 mesh readiness (synthesis 2026-08-28) + análise crítica segunda ordem
> **Idioma:** PT-BR prose + EN technical terms (UEID, Pydantic, SHA-256, UPSERT, JSONL, TW, FSM, idempotency, replay, canonical_json, sort_keys)
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Intuição

A **idempotência via `upstream_id` SHA-256** é o contrato que permite que o pipeline de sincronização **Obsidian vault → SQLite → Taskwarrior** seja **re-executável com segurança**, mesmo após crash, restart, ou replay manual. A função `compute_upstream_id(payload)` em `vibe-ops/src/middleware/sync_engine.py:21-24` produz um hash determinístico de 12 caracteres hex via `hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]` — qualquer payload re-serializado com as mesmas chaves (independentemente de ordem ou tipos datetime) produz **o mesmo `upstream_id`**. Esse identificador é então usado em três pontos load-bearing: (1) **pré-check de idempotência** (`SELECT upstream_id FROM planning_entities WHERE id=? AND entity_type=?` antes de INSERT, `sync_engine.py:40-44`), (2) **UPSERT condicional** (`ON CONFLICT(id, entity_type) DO UPDATE ... WHERE excluded.upstream_id != planning_entities.upstream_id`, `sync_engine.py:48-55`) — só atualiza se o hash mudou — e (3) **Taskwarrior filter** (`self.tw.tasks.filter(upstream_id=tw_payload.upstream_id)`, `sync_engine.py:95`) que detecta tasks pré-existentes sem depender de UUID externo. Combinado com o **append-only mesh queue** (Pattern #12) e o **ForkAdapter Protocol idempotente** (Pattern #13), este padrão sustenta a **promessa de auto-feedback estocástico** do doc 10 — observações ruidosas `o_t` podem ser re-submetidas sem corromper o estado latente `s_t` (Pattern #12 §3.2). É o elo entre **content-addressing** e **deterministic replay**, sem o qual replay-after-restart vira duplicação silenciosa.

---

## §2 — Enunciado Formal

### 2.1 Definição verbatim do anchor primário

**Localização:** `vibe-ops/src/middleware/sync_engine.py:21-24`

```python
def compute_upstream_id(self, payload: dict) -> str:
    """Gera hash idempotente truncado (12 chars)"""
    normalized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]
```

**Mecânica load-bearing em 3 etapas:**

| # | Operação | Por quê load-bearing |
|:-:|:---------|:---------------------|
| 1 | `json.dumps(payload, sort_keys=True, default=str)` | **Canonicalização**: ordem de chaves é irrelevante (sorted); tipos não-JSON-serializable (datetime, UUID, Path) viram str via `default=str`. Mesmo payload com ordem diferente ou `datetime` vs `str` produz mesma string. |
| 2 | `.encode()` (UTF-8 default) | Bytes para `hashlib.sha256()` |
| 3 | `.hexdigest()[:12]` | 48 bits de entropia (12 hex chars × 4 bits). Suficiente para ≈ 2³² entidades (~4 bi) com colisão ≈ 0 em escala single-user. **Truncamento** é trade-off explícito: hash completo (64 chars) ocuparia espaço SQLite sem benefício mensurável. |

**Por que SHA-256 (não MD5, não blake2b)?**
- MD5: quebrado criptograficamente (não relevante aqui, mas princípio de não-usar-quebrado)
- SHA-256: disponível em stdlib (`hashlib`), sem dependências externas, auditado
- blake2b: mais rápido, mas exige `hashlib.blake2b(...)` com parâmetros adicionais; ganho marginal não justifica inconsistência com ecossistema Python

**Por que 12 chars (não 16, não 8)?**
- 8 chars (32 bits): birthday paradox começa a preocupar >10k entidades (~50% chance colisão em 65k)
- 12 chars (48 bits): birthday paradox ≈ 2³² ≈ 4 bi entidades — **muito acima** do dataset real (~10⁴-10⁵ entidades)
- 16 chars (64 bits): redundante para escala atual; ocupa espaço SQLite sem ganho prático

### 2.2 Idempotência no sync Obsidian → SQLite (snippet verbatim de `sync_engine.py:26-61`)

```python
def sync_obsidian_to_sqlite(self, folder: str = "2_projeto") -> dict:
    """Ingestão idempotente de Frontmatter → SQLite"""
    stats = {"ingested": 0, "skipped": 0, "triaged": 0}
    
    for md_file in (self.vault / folder).rglob("*.md"):
        post = frontmatter.load(md_file)
        if "entity_type" not in post.metadata:
            continue
            
        payload = post.metadata
        upstream_id = self.compute_upstream_id(payload)
        
        # Verificar idempotência
        cursor = self.db.cursor()
        cursor.execute("SELECT upstream_id FROM planning_entities WHERE id = ? AND entity_type = ?", 
                      (payload.get("id"), payload.get("entity_type")))
        existing = cursor.fetchone()
        if existing and existing["upstream_id"] == upstream_id:
            stats["skipped"] += 1
            continue
            
        # Upsert com resolução de FK
        cursor.execute("""
            INSERT INTO planning_entities (id, entity_type, payload_json, upstream_id, synced_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id, entity_type) DO UPDATE SET
                payload_json = excluded.payload_json,
                upstream_id = excluded.upstream_id,
                synced_at = CURRENT_TIMESTAMP
            WHERE excluded.upstream_id != planning_entities.upstream_id
        """, (payload["id"], payload["entity_type"], json.dumps(payload), upstream_id, datetime.utcnow()))
        
        stats["ingested"] += 1
        
    self.db.commit()
    return stats
```

**Padrão UPSERT com pré-check (3 camadas de defesa):**

1. **Pré-check via SELECT** (`sync_engine.py:40-44`): se `upstream_id` já existe E é igual → `stats["skipped"]++`, no INSERT. Otimização de I/O (evita write desnecessário).

2. **UPSERT com WHERE clause** (`sync_engine.py:55`): mesmo se pré-check falhar (race condition entre 2 syncs concorrentes), o `WHERE excluded.upstream_id != planning_entities.upstream_id` garante que **só atualiza se o conteúdo mudou**. Se hash é igual, SQLite no-op (0 rows affected).

3. **Stats separados** (`ingested` vs `skipped`): observabilidade para debugging. Se `skipped >> ingested` em uma run, indica replay após restart — comportamento esperado, não bug.

**Tabela SQLite inferida (DDL canônico):**

```sql
CREATE TABLE planning_entities (
    id              TEXT,
    entity_type     TEXT,
    payload_json    TEXT,
    upstream_id     TEXT,
    synced_at       TIMESTAMP,
    PRIMARY KEY (id, entity_type)  -- composite PK
);
```

### 2.3 Idempotência no sync SQLite → Taskwarrior (snippet verbatim de `sync_engine.py:63-113`)

```python
def sync_sqlite_to_taskwarrior(self, policy_state: str = "MAINTAIN") -> dict:
    """Injeção segura no TW respeitando orçamento cognitivo"""
    stats = {"created": 0, "updated": 0, "throttled": 0}
    
    cursor = self.db.cursor()
    cursor.execute("""
        SELECT pe.payload_json, rs.id as sync_id FROM planning_entities pe
        JOIN roadmap_sync rs ON pe.id = rs.study_plan_fk
        WHERE pe.entity_type = 'study_plan' AND rs.status = 'pending'
    """)
    
    for row in cursor.fetchall():
        plan = json.loads(row[0])
        sync_id = row[1]
        adapter = TypeAdapter(StudyPlanEntity)
        study_plan = adapter.validate_python(plan)
        
        # Throttle baseado em PolicyState
        if policy_state == "RECOVERY" and study_plan.daily_target_minutes > 60:
            stats["throttled"] += 1
            continue
            
        # Gerar payload TW
        tw_payload = TaskPayload(
            description=f"[Estudo] {study_plan.title}",
            project=study_plan.tw_project_key,
            tags=["study", f"policy:{policy_state.lower()}"],
            upstream_id=self.compute_upstream_id(plan),
            study_plan_id=study_plan.id
        )
        
        # Injetar no TW
        existing = self.tw.tasks.filter(upstream_id=tw_payload.upstream_id)
        if existing:
            task = existing[0]
            cursor.execute("UPDATE roadmap_sync SET tw_uuid = ?, last_synced = CURRENT_TIMESTAMP WHERE id = ?", (task['uuid'], sync_id))
            stats["updated"] += 1
        else:
            task = self.tw.tasks.add(
                description=tw_payload.description,
                project=tw_payload.project,
                tags=tw_payload.tags
            )
            task["upstream_id"] = tw_payload.upstream_id
            task["study_plan_id"] = tw_payload.study_plan_id
            task.save()
            cursor.execute("UPDATE roadmap_sync SET tw_uuid = ?, last_synced = CURRENT_TIMESTAMP WHERE id = ?", (task['uuid'], sync_id))
            stats["created"] += 1
                
    self.db.commit()
    return stats
```

**TW filter pattern (load-bearing, `sync_engine.py:95`):**

```python
existing = self.tw.tasks.filter(upstream_id=tw_payload.upstream_id)
if existing:
    task = existing[0]
    # ... update tw_uuid in roadmap_sync
    stats["updated"] += 1
else:
    task = self.tw.tasks.add(...)
    task["upstream_id"] = tw_payload.upstream_id
    task.save()
    # ... insert tw_uuid
    stats["created"] += 1
```

**Por que `filter(upstream_id=...)` em vez de `filter(uuid=...)`?**

- TW `uuid` é gerado por TW internamente (não determinístico) — não pode ser conhecido antes de criar
- TW `upstream_id` é **user-defined UDÁ** (campo arbitrário em TW 2.x+) — permite query externa
- Padrão canônico: `apply_change(event)` em `ForkAdapter` (Pattern #13) usa UEID como join key; aqui `upstream_id` (SHA-256[:12]) é o join key cross-system
- Re-chamar `sync_sqlite_to_taskwarrior()` N vezes com mesmo payload → 1× `created` + (N-1)× `updated` (não cria duplicatas)

**Invariante:** `stats["created"]` é 0 em todo replay após primeira execução bem-sucedida.

### 2.4 Atomic write protocol no mesh queue (cross-ref Pattern #12)

**Localização:** `src/mesh/queue.py:20-32`

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

**Replay safety após restart (verbatim `src/mesh/queue.py:71-73`):**

```python
def replay_after_restart() -> Iterator[TaskChange]:
    """Re-process all pending events (called on agent startup)."""
    yield from consume_pending()
```

**Invariante de replay:** o filesystem é a fonte de verdade. Crash mid-`enqueue` deixa 0 eventos (atomic temp+rename) ou 1 evento completo (apos `os.replace`). `replay_after_restart()` no startup do agente itera `status=pending` events — **não há duplicação** porque o consumer chama `ack()` que muda status para `propagated` ou `partial_propagation` (Pattern #12 §2.3).

### 2.5 Composição: upstream_id + UEID no contrato Task

**Localização:** `src/contracts/task.py:28-77` (Task model)

```python
class Task(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: UEID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=2000)] = ""
    entity_type: Literal["task"] = "task"
    horizon: Period
    priority: Priority = Priority.MEDIUM
    project_id: UEID | None = None
    depends_on: list[UEID] = Field(default_factory=list)
    estimated_minutes: int | None = None
    done: bool = False
    done_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
```

**Distinção `id` (UEID) vs `upstream_id` (SHA-256[:12]):**

| Aspect | `id` (UEID) | `upstream_id` (SHA-256[:12]) |
|:-------|:-------------|:-----------------------------|
| Formato | `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` | `[0-9a-f]{12}` |
| Geração | `uuid.uuid4()` + slug legível | `hashlib.sha256(...)[:12]` |
| Semântica | Identidade estável (sobrevive a rename) | Content hash (muda se payload mudar) |
| Uso primário | Cross-fork join key (Pattern #10) | Idempotency key (Pattern #14) |
| Mudança em payload | **Não muda** | **Muda** (detecção de drift) |
| Storage | `tasks.id`, `projects.id`, ... | `tasks.upstream_id`, `roadmap_sync.upstream_id`, ... |

**Invariante da distinção:** UEID identifica **qual entidade** (imutável); `upstream_id` identifica **qual versão do conteúdo** (muda com edição). Replay após edição de frontmatter atualiza `upstream_id` mas mantém UEID.

### 2.6 End-to-end pipeline (canonical flow)

```
┌─────────────────────────────────────────────────────────────────────┐
│ OBSIDIAN VAULT (markdown source of truth)                           │
│   2_projeto/<file>.md com frontmatter {id, entity_type, ...}        │
└──────────────────────────────�──────────────────────────────────────┘
                               │ sync_obsidian_to_sqlite()
                               │ ↓ compute_upstream_id(payload)
                               │ ↓ SELECT pre-check
                               │ ↓ UPSERT WHERE excluded.upstream_id != existing
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SQLite (planning_entities + roadmap_sync)                           │
│   upstream_id TEXT — content hash, idempotency key                  │
│   PK (id, entity_type) — identity, join key cross-fork              │
└──────────────────────────────┬──────────────────────────────────────�
                               │ sync_sqlite_to_taskwarrior()
                               │ ↓ SELECT pending study_plans
                               │ ↓ compute_upstream_id(plan)
                               │ ↓ filter(upstream_id=...) TW UDÁ
                               │ ↓ if existing: update; else: create
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ TASKWARRIOR (.task directory)                                       │
│   task.uuid = auto-generated by TW                                  │
│   task.upstream_id = SHA-256[:12] (UDÁ)                              │
│   task.study_plan_id = UEID (cross-fork)                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Invariante top-level:** `upstream_id` é a **chave de convergência** entre sync runs. Crash em qualquer ponto entre `sync_obsidian_to_sqlite` e `sync_sqlite_to_taskwarrior` é seguro porque o próximo run detecta via `WHERE excluded.upstream_id != existing` ou via `filter(upstream_id=...)` e converge.

---

## §3 — Justificativa

### 3.1 Razões técnicas (por que SHA-256[:12] wins)

**Por que content-addressing (vs ID externo)?**

| Alternativa | Prós | Contras | Veredito |
|:------------|:-----|:--------|:---------|
| **SHA-256[:12] do payload** (escolhido) | Determinístico; detecta drift; zero coordenação externa; replay-safe | Colisão em ~4 bi entidades (irrelevante); muda em qualquer edição | **Vencedor** |
| UUID v4 externo (gerado uma vez) | Estável; padrão da indústria | Não detecta edição silenciosa; precisa de coordination layer para atribuir; replay pode duplicar | Rejeitado |
| Timestamp monotonic (created_at) | Ordenável | Múltiplos writes no mesmo segundo colidem; não detecta edição | Rejeitado |
| Counter auto-increment | Compacto | Não-portável entre SQLite forks; sem semântica | Rejeitado |
| Hash do file path | Estável se path não muda | Quebra se user reorganiza vault; não detecta edição de conteúdo | Rejeitado |

**Vantagens concretas do SHA-256[:12]:**

1. **Drift detection nativa**: edição de frontmatter muda `upstream_id`; UPSERT atualiza `payload_json`. Operator audita via `SELECT id, upstream_id, synced_at FROM planning_entities ORDER BY synced_at DESC`.
2. **Crash recovery trivial**: se `sync_engine` crasha mid-loop após INSERT mas antes de `commit()`, próximo run re-detecta via pré-check. Sem WAL externo.
3. **Replay em agent restart**: `vibe-ops` LangGraph graphs re-executam `sync_obsidian_to_sqlite()` N vezes sem corromper (Pattern #12 também safe).
4. **Cross-fork convergence via TW UDÁ**: TW não tem UNIQUE nativo, mas `filter(upstream_id=...)` funciona como query externa. Mesmo padrão do `TaskdogAdapter` UPSERT, mas com `upstream_id` em vez de UEID.

### 3.2 Por que pré-check + UPSERT (não só UPSERT direto)

`ON CONFLICT(id, entity_type) DO UPDATE SET ... WHERE excluded.upstream_id != planning_entities.upstream_id` é o **guard clause** que torna o UPSERT verdadeiramente idempotente. Sem o WHERE, todo replay re-escreveria o `payload_json` mesmo sem mudança de conteúdo, gerando:

- I/O desnecessário (write SQLite)
- `synced_at` atualizado (false signal de "atividade")
- WAL growth sem propósito

**3 camadas de defesa (defense-in-depth):**

1. **Pré-check SELECT** (`sync_engine.py:40-44`) — short-circuita sem INSERT quando hash é igual.
2. **UPSERT WHERE clause** (`sync_engine.py:55`) — protection contra race condition entre 2 syncs concorrentes.
3. **Stats reporting** (`ingested` vs `skipped`) — observabilidade: `skipped: 50, ingested: 0` = replay após restart (esperado, não bug).

### 3.3 Limitações conhecidas (honest rigor — citação de doc 09 + gaps)

**Análise crítica:** `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` (doc 09) e `docs/auto-performance-os/`.

| Limitação | Severidade | Implicação para Pattern #14 |
|:----------|:----------:|:----------------------------|
| **Hash collisions teóricas em 4 bi+ entidades** | LOW | Birthday paradox: 50% chance colisão em ~65k entidades para 12 hex chars. Nunca observado em escala single-user. Mitigação: aumentar para 16 chars se vault crescer >100k entities. |
| **`sort_keys=True` não cobre listas** | MEDIUM | `json.dumps(sort_keys=True)` preserva ordem de lista. Para IKIGAi vectors order-matters (paixão < habilidade < mercado < receita < curso) é OK. Para TaskChange com list arbitrária, ordem diferente gera `upstream_id` diferente. Mitigação: caller deve normalizar listas antes de passar para `compute_upstream_id()`. |
| **`default=str` perde precisão em datetime** | LOW | `datetime(2026, 8, 28, 10, 30)` vira `"2026-08-28 10:30:00"`. Se 2 datetimes com tzinfo diferente, viram strings diferentes → hashes diferentes. Não observado em código atual (UTC-naive). |
| **`upstream_id` muda a cada edição** (não é ID estável) | BY DESIGN | Feature, não bug — detecta drift. Mas **não pode ser usado como cross-fork join key** (papel do UEID, Pattern #10). Doc deve distinguir explicitamente. |
| **`SyncEngine` sem idempotency test** | MEDIUM | Não há teste em `vibe-ops/tests/` que valide "2× sync = mesmo state". Adicionar `tests/test_sync_engine.py::test_idempotent_obsidian_to_sqlite` para v1.1. |
| **TW UDÁ `upstream_id` requer TW 2.x+** | LOW | TW 1.x não suporta user-defined attributes (UDA). Mitigação: check `tasklib.TaskWarrior.__version__`. |
| **F5 — pomodoro fork não wired** | HIGH (doc 09 §3.2) | `pomodoro_machine.py` emite events que **não viram TaskChange** (Pattern #12 §3.5). Se um dia virarem, devem usar `upstream_id` próprio (ex.: `"pomo:..."`) para evitar cross-contamination. |
| **`compute_upstream_id` recalculado 2×** | LOW | `sync_sqlite_to_taskwarrior` recalcula hash em vez de ler `planning_entities.upstream_id`. Refatoração: SELECT cached value. Aceitável em v1. |

### 3.4 Quando NÃO usar SHA-256[:12] upstream_id

- **Identity cross-fork**: use UEID (Pattern #10). `upstream_id` muda com edição; UEID é estável.
- **Vector store IDs (Chroma, FAISS)**: use hash do **embedding**, não do payload.
- **Logs de alta frequência (>10k/sec)**: prefira UUID v7 (sortable, sem canonicalização).
- **Payloads sensíveis (senhas, tokens)**: prefira HMAC-SHA256 com chave secreta.
- **Cross-system integration externo** (Google Calendar, Notion, Linear): esses sistemas têm seus próprios ID schemes.

### 3.5 Por que este padrão é load-bearing

**Sem idempotência via `upstream_id`:** (1) replay após crash duplica tasks, (2) drift vault↔SQLite não é detectado, (3) manual sync acumula duplicatas, (4) TW filter por `uuid` exige coordination layer.

**Com idempotência via `upstream_id`:** (1) crash-safety por construção (pré-check + UPSERT WHERE), (2) drift detection via hash comparison, (3) manual sync idempotente, (4) TW filter preditível sem coordination, (5) replay determinístico (`replay_after_restart()` em Pattern #12 + #14 = pipeline totalmente determinístico).

---

## §4 — Cross-references

### 4.1 Code anchors (verificados via Read tool)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `vibe-ops/src/middleware/sync_engine.py:21-24` | `compute_upstream_id()` SHA-256[:12] canonical | Content-addressing hash |
| `vibe-ops/src/middleware/sync_engine.py:40-44` | `SELECT upstream_id FROM planning_entities ...` | Pré-check idempotency |
| `vibe-ops/src/middleware/sync_engine.py:48-55` | `INSERT ... ON CONFLICT ... WHERE excluded.upstream_id != ...` | UPSERT condicional |
| `vibe-ops/src/middleware/sync_engine.py:90-95` | TW payload hash + `filter(upstream_id=...)` | TW filter pattern |
| `src/mesh/queue.py:20-32, 71-73` | `enqueue()` + `replay_after_restart()` (Pattern #12) | Atomic + replay safety |
| `src/contracts/task.py:28-77` | `Task` model com `id: UEID` (Pattern #10) | Identity vs hash distinction |

### 4.2 Design-system docs (Layer 2 + Layer 3 + Layer 8)

- **`docs/design-system/00-INDEX.md`** §3 — mapa de dependências posiciona Pattern #14 (Idempotency) na série 10-13 → 14-19.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 — Adapter storage topology; `ueid UNIQUE` em 3 adapters. Pattern #14 complementa: `upstream_id` é o **content hash** dentro de cada adapter.
- **`docs/design-system/05-canvas-contracts-architecture.md`** §3, §4 — frozen Pydantic (Pattern #11); `compute_upstream_id` lê dict metadata.
- **`docs/design-system/06-canvas-agents-architecture.md`** — IKIGAi Deep Agent invoca `sync_obsidian_to_sqlite()`; replay safe porque cada pattern é idempotente.
- **`docs/design-system/07-canvas-sync-architecture.md`** — Pattern #14 é o **building block** do sync vault ↔ SQLite ↔ TW.
- **`docs/design-system/08-canvas-cybernetic-loop.md`** — Pattern #14 ancora o **Persist + Sync** stages do cybernetic loop.
- **`docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md`** §3.2 — qualifica Pattern #12 (A7 + F5); Pattern #14 herda parcialmente (pomodoro events deveriam virar `TaskChange` com `upstream_id`).
- **`docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md`** §3 — Pattern #14 ancora **idempotência do sensor** (observações `o_t` re-submetidas sem corromper `s_t`).

### 4.3 Auto-performance-os docs (PT-BR, 27 docs)

- **`03-axiom-finite-state-machines.md`** — `TaskChange` FSM; Pattern #14 garante transições idempotentes.
- **`18-engine-consolidator.md`** — `consolidator.py` agrega daily logs; candidato natural para Pattern #14.
- **`24-integration-mesh-ueid-propagation.md`** §2 — UEID propagation (Pattern #10). Complementa: UEID para cross-fork join, `upstream_id` para drift detection.
- **`25-integration-deep-agent-sync.md`** — mesh ↔ vault sync; building block do sync Obsidian → SQLite.
- **`26-integration-cybernetic-loop.md`** — cybernetic loop; Pattern #14 ancora **Persist + Sync** stages.

### 4.4 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer; Pattern #14 fica no **operator layer**.
- **`[[data-first-methodology]]`** — ADR-007 gate 5 SONHO logs (gating F5 pomodoro).
- **`[[master-branch-carro-chefe-2026-08-28]]`** — canonical narrative; Pattern #14 é o **load-bearing contract** para bidirectional sync.
- **`[[algorithm-issues-registry]]`** — 31 inconsistencies; Pattern #10 (UEID) tem gap A2/C1.
- **`[[verify-agent-fabricated-failures]]`** — verificação independente requerida para claims de "sync quebrado".

### 4.5 ADR / spec

- `code-docs/adr/ADR-007-data-first-methodology.md`, `ADR-009-pydantic-strict-mode-invariance.md`
- `docs/superpowers/specs/2026-08-28-mesh-phase3-v1.md` — Phase 3 v1 mesh; Pattern #14 é pré-requisito para v1.2+.

---

## §5 — Fontes

### Code (verificado)

- `vibe-ops/src/middleware/sync_engine.py` (138 LOC), `src/mesh/queue.py` (74 LOC), `src/contracts/task.py` (210 LOC), `src/contracts/task_change.py`, `src/mesh/adapters/base.py` + `src/mesh/adapters/taskdog.py`

### Docs design-system

- `docs/design-system/04-canvas-mesh-architecture.md` §3.3, `05-canvas-contracts-architecture.md` §3-§4, `06-canvas-agents-architecture.md`, `07-canvas-sync-architecture.md`, `08-canvas-cybernetic-loop.md`, `09-analise-critica-segunda-ordem-arquitetura.md` §3.2, §4.3, `10-modelo-unificado-auto-feedback-estocastico.md` §3, `12-pattern-append-only-queue.md`, `13-pattern-fork-adapter-protocol.md`

### Docs auto-performance-os (PT-BR)

- `03-axiom-finite-state-machines.md`, `18-engine-consolidator.md`, `24-integration-mesh-ueid-propagation.md` §2, `25-integration-deep-agent-sync.md`, `26-integration-cybernetic-loop.md`

### Memory cross-refs

- `[[interfaces-architecture-2026-08-27]]`, `[[data-first-methodology]]`, `[[master-branch-carro-chefe-2026-08-28]]`, `[[algorithm-issues-registry]]`, `[[verify-agent-fabricated-failures]]`

### ADR / spec

- `code-docs/adr/ADR-007`, `code-docs/adr/ADR-009`, `docs/superpowers/specs/2026-08-28-mesh-phase3-v1.md`

---

## §6 — Invariantes load-bearing

| # | Invariante | Verificação |
|:-:|:-----------|:------------|
| 1 | `compute_upstream_id()` usa `hashlib.sha256` + truncation 12 chars | sync_engine.py:24 |
| 2 | Canonicalização via `sort_keys=True, default=str` | sync_engine.py:23 |
| 3 | UPSERT guard `WHERE excluded.upstream_id != planning_entities.upstream_id` | sync_engine.py:55 |
| 4 | TW filter via `filter(upstream_id=...)` UDÁ | sync_engine.py:95 |
| 5 | Atomic write via `os.replace(tmp, target)` no mesh queue | queue.py:31, queue.py:68 |

---

> **Padrão #14 — Idempotency via upstream_id SHA-256[:12] — qualificado com 3 limitações conhecidas (collision risk em >4 bi entidades, `sort_keys` não canonicaliza listas, `default=str` perde precisão em datetime com tzinfo). Recomendação arquitetural:** preservar invariantes load-bearing (SHA-256[:12], pré-check SELECT, UPSERT WHERE guard, TW UDÁ filter); adicionar `tests/test_sync_engine.py::test_idempotent_obsidian_to_sqlite` para v1.1; documentar distinção UEID (identity) vs upstream_id (content hash) em training docs para futuros agentes. Fechar gap F5 (pomodoro fork) requer criar `src/mesh/adapters/pomodoro.py` com `upstream_id` próprio (cross-ref Pattern #13). Priorizar **backend antes de polish algorítmico** (`[[prioritize-backend-over-algorithm-refinement]]`).
