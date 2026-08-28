# 26 — Integração: Cybernetic Loop — Target→Sensor→Adjuster

> **Categoria:** §5 Integração
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** daily_loop.py, sync_engine.py, ADR-002 §3

---

## §1 — Intuição em linguagem simples

O **Cybernetic Loop** é a peça mais macro: fecha o ciclo **Target → Sensor → Adjuster → Persist → Sync → Index** continuamente. Tudo que calculamos (Q_HE, regime, meta-vetor, IKIGAi 5 vetores) é input do loop. Tudo que produzimos (tasks, pomodoros, SONHOs) é output que realimenta os inputs.

## §2 — Enunciado formal

**Loop canônico:**

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   TARGET: SONHO + regime atual + Q_HE atual              │
│       │                                                  │
│       ▼                                                  │
│   SENSOR: lê estado real (vault, tasks, pomodoros)       │
│       │                                                  │
│       ▼                                                  │
│   ADJUSTER: calcula deltas (gap planejado vs executado)  │
│       │                                                  │
│       ▼                                                  │
│   PERSIST: grava em data/feedback/                       │
│       │                                                  │
│       ▼                                                  │
│   SYNC: propaga via mesh para todos os forks             │
│       │                                                  │
│       ▼                                                  │
│   INDEX: vetoriza + indexa (chroma_db)                   │
│       │                                                  │
│       └─────────────── (próximo ciclo) ───────────────────│
└──────────────────────────────────────────────────────────┘
```

**Política do PolicyEngine com 4 estados:**

```
PUSH / MAINTAIN / REDUCE / RECOVER
```

(histerese assimétrica: 3 dias subindo, 2 descendo, 1 dia emergência).

**Frequência:**

| Loop                          | Frequência              |
|:-----------------------------:|:-----------------------:|
| `run-daily` (target diário)   | 1× por dia              |
| `run-pomodoro` (target bloco) | a cada 25 min           |
| `run-feedback` (gap update)   | 1× por hora             |

## §3 — Justificativa não-técnica

Por que **6 etapas explícitas** (em vez de 3 ou 4): cada etapa tem **observabilidade distinta**. Se o sistema travar, dá pra saber se foi no SENSOR (dados não chegaram), no ADJUSTER (cálculo falhou), no PERSIST (disco cheio), no SYNC (mesh offline), ou no INDEX (chroma_db corrompido). Sem granularidade, debugging vira adivinhação.

Por que **3 frequências distintas** (diário/pomodoro/feedback): o loop diário é **planejamento macro** (regime do dia); o loop pomodoro é **execução micro** (bloco de 25 min); o loop feedback é **observação contínua** (gap). Misturar tudo em uma frequência única gera ruído — diário olha plano macro, feedback olha sinais fracos.

Por que **INDEX com chroma_db** (vetorização): permite **busca semântica** sobre o histórico. Se o usuário perguntar "quais SONHOs envolveram aprendizado de Rust?", chroma_db responde mesmo sem keywords exatas. É a camada que torna o sistema **consultável**, não só executável.

## §4 — Referências cruzadas (consumidores downstream)

- **23-meta-decision-flow** — implementação concreta do loop
- **25-integration-deep-agent-sync** — sync é a etapa 5 do loop
- **24-integration-mesh-ueid-propagation** — sync = propagação mesh
- **13-engine-habit-engine** — TARGET inclui H(t)
- **18-engine-consolidator** — SENSOR lê overall diário

## §5 — Fontes

- `src/cybernetics/daily_loop.py` — Target→Sensor→Adjuster→Persist→Sync→Index
- `src/middleware/sync_engine.py` — Obsidian ↔ SQLite ↔ Taskwarrior
- `vibe-ops/architecture/ADR-002-cybernetic-loop.md` §3 — política + frequências
- `data/vibe_ops.db` — estado persistido
- `data/chroma_db/` — índice vetorial
- `vault/ikigai/meta/algorithmic-loop-overview.md` — visão geral do loop