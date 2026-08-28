# 24 — Integração: Mesh — Propagação UEID

> **Categoria:** §5 Integração
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** mesh/queue.py, mesh/agent_consumer.py, mesh/adapters/

---

## §1 — Intuição em linguagem simples

O **Data Mesh** é a camada que permite uma task existir em **múltiplos forks** (tuiboard, taskdog, solverforge-calendar) simultaneamente, todas referenciando o mesmo UEID canônico. Quando o agente valida uma `TaskChange`, ele propaga um `PropagationEvent` para todos os adapters. Falhas em um adapter são isoladas — não bloqueiam os outros.

## §2 — Enunciado formal

**UEID (Universal Entity Identifier) canônico:**

```
^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$
   ↑         ↑              ↑              ↑
   cluster   entity_type    hash1          hash2
```

**Pipeline de propagação:**

```
fork (qualquer)
   │
   │ CLI enfileira TaskChange
   ▼
data/review_queue/<change_id>.json (append-only, atômico)
   │
   │ Agent valida (PAE rules: APPROVE / REJECT / CLARIFY)
   ▼
PropagationEvent(ueid, action, target_adapters)
   │
   ├─▶ CliAdapter         (data/tasks.jsonl)
   ├─▶ TaskdogAdapter     (SQLite UPSERT on ueid)
   └─▶ SolverforgeCalendarAdapter (UPI ueid column)
```

**Invariantes:**

| Invariante                       | Razão                                                         |
|:--------------------------------:|:--------------------------------------------------------------|
| `upstream_id == ueid`            | chave de junção entre forks                                   |
| `data/review_queue/` append-only | histórico auditável                                            |
| Falha em 1 adapter ≠ bloqueia    | outros adapters processam normalmente                          |
| Adapter recusa ação não-criada   | v1 mesh scope = `create` only; `update`/`delete` em v1.2+     |

## §3 — Justificativa não-técnica

Por que **append-only queue** em vez de RPC síncrono: desacopla o fork (CLI) do agente validador. O fork pode enfileirar offline; o agente consome quando estiver disponível. Isso é crítico para uso em **edge** (PC do usuário que nem sempre tem agente rodando).

Por que **UEID em 4-part regex**: o UEID precisa ser (a) **legível** (cluster prefix + entity_type), (b) **único** (hash duplo garante colisão ~0), (c) **determinístico** (mesma entity sempre gera mesmo UEID). A regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` captura tudo isso.

Por que **falha isolada por adapter**: o fork `tuiboard` pode estar indisponível (banco corrompido), mas `taskdog` e `solverforge-calendar` ainda recebem o evento. Sem isolamento, uma falha em cascata derrubaria o sistema inteiro.

## §4 — Referências cruzadas (consumidores downstream)

- **15-engine-pomodoro-machine** — pomodoros viram TaskChange → mesh
- **19-engine-ikigai-vector-scorer** — vetores IKIGAi viram TaskChange → mesh
- **25-integration-deep-agent-sync** — mesh ↔ vault sync
- **Axioma 03** (FSMs) — TaskChange é uma FSM (PENDING → VALIDATED → PROPAGATED)

## §5 — Fontes

- `src/mesh/queue.py` — filesystem append-only review queue (atomic writes)
- `src/mesh/agent_consumer.py` — Deep Agent validation (PAE rules)
- `src/mesh/agent_propagator.py` — Deep Agent propagation (per-adapter failure isolation)
- `src/mesh/adapters/base.py` — ForkAdapter Protocol (@runtime_checkable)
- `src/mesh/adapters/cli.py` — CliAdapter (data/tasks.jsonl)
- `src/mesh/adapters/taskdog.py` — TaskdogAdapter (SQLite UPSERT on ueid)
- `src/mesh/adapters/solverforge_calendar.py` — SolverforgeCalendarAdapter (UPI ueid column)
- `src/contracts/common.py` — UEID Pydantic model