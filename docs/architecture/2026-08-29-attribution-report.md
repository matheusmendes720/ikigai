# Attribution Report — IKIGAI × PAV × Forks × Deep Agents × Backend

**Date:** 2026-08-29
**Status:** Canonical (per user /btw draft + peer analysis review)
**Companion spec:** `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`

---

## §0 — Modelo Mental Canônico

```
DEEP AGENTS (AI-native carro-chefe)
└─ leem vault + forks
└─ aplicam strategics + IKIGAI logic
└─ emitem MCP contracts + vault updates

BACKEND APPS (deterministic services)
└─ recebem comandos, persistem estado, expõem MCP tools
└─ B0 Hygiene → B6 Vault sync (Phase A done; B3+B4 SHIPPED, B5+B6 SHIPPED)

FORKS (user views)        VAULT (SOT append-only)
└─ tuiboard               └─ planning cycles
└─ taskdog                └─ MOCs / dashboards
└─ solverforge-calendar   └─ evidence/ / drafts/
```

---

## §1 — Quem É Dono do Quê

| Sistema | Dono | Conta Para | NÃO |
|---|---|---|---|
| `strategics/` | Constituição PT-BR | IKIGAI + PAV | Nunca muta; nunca executa |
| IKIGAI | Estado de objetivo (carro-chefe) | `strategics/` framework | Não executa mecânica |
| PAV | Mecânica de execução (desativado) | Própria medição | Não conhece significado |
| Forks | Views do usuário | MCP contracts | Não é o produto |
| Native CLI/TUI | Plano de controle do operador | Backend kernel | Não é user-facing |

---

## §2 — Backend Apps vs Deep Agents: Fronteira Clara

| Layer | Quem | O quê | Fronteira |
|---|---|---|---|
| Backend apps | Services | CRUD determinístico, expõem MCP tools | Stateless; sem LLM |
| Deep agents | Processos AI | Interpretam intenção, escolhem tools, escrevem vault | Stateful; com LLM |

**Regra de routing (4 critérios):**

```
SE (operação == CRUD determinístico de entidade conhecida)
  → Backend app
SENÃO SE (operação == interpreta intenção + escolhe tools + escreve vault)
  → Deep agent
SENÃO SE (operação == sync entre duas representações dos mesmos dados)
  → Sync daemon (B6)
SENÃO SE (operação == requer contexto histórico de padrões — trajectory,
          hysteresis, regime FSM)
  → Mesmo CRUD-like, é Deep agent  ← (4º critério, adicionado pós-peer-review)
```

---

## §3 — Atribuições Detalhadas (Q&A)

| Pergunta | Dono | Conta Para |
|---|---|---|
| Qual meu sonho de longo prazo? | IKIGAI | `strategics/` |
| O que contém um ciclo de 45 dias? | IKIGAI | `strategics/` estrutura |
| Fiz meu bloco da manhã hoje? | PAV | Própria medição |
| Streak do hábito saudável? | PAV | Própria aritmética |
| Q_HE desta semana? | PAV | Própria aritmética |
| Transição PUSH → MAINTAIN? | PAV | `strategics/` hysteresis |
| Trajetória para o SONHO viável? | IKIGAI (lê PAV) | Dados PAV |
| Ajustar escopo da ONDA? | IKIGAI (decisão humana) | Tendências PAV |
| Quem decide o que entra no vault? | Deep agents (IKIGAi) | Append-only via `vault_write` |
| Quem gerencia os serviços backend? | Operador (CLI nativo B2) | Server-management |
| Quem lê task state de fork? | Backend MCP gateway | Forks emitem eventos |

**Perguntas adicionadas pós-peer-review (gaps detectados):**

| Pergunta implícita | Dono | Risco |
|---|---|---|
| Quem decide frequência sync PAV→IKIGAI? | IKIGAI (policy) | conflita com PAV hysteresis |
| Quem registra UEID canônico de hábito? | PAV (gera) → IKIGAI (valida 5-part) | schema collision |
| Quem migra task entre forks? | Ninguém hoje (v1.3+) | pode ser B6 ou novo B7 |

---

## §4 — Decisões Abertas (DEC-01..05)

Ver `docs/decisions/pending/algorithm-attribution-decisions.md` para o
registro formal. Resumo aqui:

| DEC | Pergunta | Opções | Recomendação |
|---|---|---|---|
| **DEC-01** | Frequência de sync IKIGAI↔PAV | A: Daily / B: A cada hábito / C: On-demand | A com `--sync-now` |
| **DEC-02** | Mecanismo de bridge | A: PAV escreve vault / B: MCP via vault-journal / C: IKIGAI lê store | B (Phase 6b já desenhado) |
| **DEC-03** | Modelo de linkage hábito↔entregável | A: tag IKIGAI / B: PAV Habit.ikigai_ueid / C: Híbrido | C (query speed + auditabilidade) |
| **DEC-04** | Escopo do native CLI/TUI B2 — gerencia PAV? | A: Sim / B: Não / C: Só quando PAV reviver | C (B2 só IKIGAI backend services) |
| **DEC-05** | Deep agent boundaries | Lê PAV store? Escreve vault? Invoca B5? | Lê PAV: sim; escreve vault: via MCP; invoca B5: sim |

**Nenhuma DEC bloqueia Phase B6 (vault sync shipped 2026-08-29).**

---

## §5 — Escopo: Backend Apps

**In Scope (Phase A + rev.3 + B-Phase done):**

| Phase | App | Status |
|---|---|---|
| A | Service foundation | ✅ DONE |
| B0 | Hygiene (git rm + CI fix + Phase A commit) | ✅ DONE |
| B1 | A2UI adapter (4º fork-pronta) | ✅ DONE |
| B2 | Server-management CLI (`life server {...}`) | ✅ DONE |
| B3 | MCP gateway consolidado (13 tools + 6 resources) | ✅ SHIPPED |
| B4 | Review queue worker (run_once + start_worker) | ✅ SHIPPED |
| B5 | Agent consumer + propagator (PAE: APPROVE/REJECT/CLARIFY) | ✅ SHIPPED (B5.B closure) |
| B6 | Vault sync protocol (vault → taskdog) | ✅ SHIPPED |

**Out of Scope (Deferred):**

- ❌ PAV CLI/TUI restoration (PAV desativado 2026-08-26)
- ❌ PAV algorithm refinement (gated em revival criteria per spec)
- ❌ Vector weight tuning (DEC pendente — ver
  [[user-revenue-weight-preference]])
- ❌ Novos adapters além dos 4 (tuiboard, taskdog, solverforge-calendar +
  native CLI/TUI control plane)

---

## §6 — Escopo: Deep Agents

**In Scope:**

| Agent | Role | Lê | Escreve |
|---|---|---|---|
| IKIGAi (mid-design) | Carro-chefe canônico | vault + forks via MCP | vault via `vault_write` MCP tool |
| PAE maintainer | Validador de mudanças | `data/review_queue/<id>.json` | status field |
| Vault sync daemon (B6 future) | Sync bidirecional | markdown + stores | ambos, append-only |

**Out of Scope (Deferred):**

- ❌ PAV-as-deep-agent (PAV desativado)
- ❌ Real-time conversation agents (IKIGAi mid-design)
- ❌ Multi-agent swarm (gated em IKIGAi backbone sólido)

---

## §7 — Fronteiras Confusas: Critérios de Decisão

| Confusão | Critério |
|---|---|
| PAV entities vs algorithms | É Pydantic model? → ok importar. É função que computa? → deferir. |
| Vault SOT vs Forks SOT | Perder o fork state = perder significado? Se sim, sincronizar pro vault. |
| Backend apps vs deep agents | Requer interpretação? Sim → deep agent. CRUD puro? Sim → backend app. |
| Native CLI/TUI vs Forks | Usuário abre pra ver seu trabalho? → fork. Operador abre pra gerenciar backend? → native. |

**Vault write invariant (NOVO, peer §7):**

> **Vault append-only vs vault write:** Deep agent **SEMPRE** escreve
> vault via MCP tool `vault_write` que enforça append-only. UI/CLI
> nativa também passa pelo mesmo tool — nunca direto. Invariant único.
>
> Enforcement duplo:
> 1. MCP server rejects any non-`vault_write` write attempt (tool
>    dispatch table check)
> 2. Filesystem level: `vault/.db` is gitignored to prevent direct
>    file mutation via tooling outside MCP

---

## Cross-references

- Spec: `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`
- DEC-01..05 record: `docs/decisions/pending/algorithm-attribution-decisions.md`
- Memory: `algorithm-attribution-decisions-2026-08-29.md` (in MEMORY.md index)
- Locked decisions referenced: master-branch-carro-chefe-2026-08-28,
  pav-as-ikigai-subsystem-2026-08-28, interfaces-architecture-2026-08-27,
  backend-phase-reordering-2026-08-28,
  algorithm-gate-system-readiness-not-sonho-2026-08-29

---

*Attribution Report — IKIGAI × PAV × Forks × Deep Agents × Backend — 2026-08-29*
