# 02 — Interfaces Dual-Layer Architecture (Forks vs Native)

> **Categoria:** NEW (gap-fill #2)
> **Público:** Eu mesmo + agentes futuros
> **Localização:** `docs/design-system/02-interfaces-dual-layer-architecture.md`
> **Origem:** codifica decisão documentada apenas em memory `[[interfaces-architecture-2026-08-27]]`

---

## §1 — Intuição em linguagem simples

Existem **duas categorias distintas** de interface no IKIGAi, com **propósitos opostos**:

1. **Forks-prontas** (tuiboard, taskdog, solverforge-calendar) — são **as views do usuário**. O usuário **vê e interage** com seus dados através delas. Externas ao repo, consumidas via MCP.

2. **Native CLI/TUI** (`interfaces/cli/`, `interfaces/tui/` planejado) — são **o painel de controle do operador** (você, ou um agente). Usadas para administração, debugging, scripts, e configuração do agente. **Não são views do usuário.**

Confundir as duas é o anti-pattern mais comum: construir CLI nativo tentando ser "view do usuário" desperdiça esforço porque forks-prontas já fazem isso melhor.

## §2 — Enunciado formal

**Dual-layer matrix:**

| Camada | Propósito          | Quem usa        | Onde roda               | Exemplo                  |
|:------:|:-------------------|:----------------|:------------------------|:-------------------------|
| **Layer A** | User view (visualização + interação) | O usuário (você) | Tuiboard / taskdog / solverforge-calendar (externos) | Abrir tuiboard, marcar task como done |
| **Layer B** | Operator control plane | Operador (você) ou agente | `interfaces/cli/`, `interfaces/tui/` (nativos) | `life mesh show <ueid>`, `life task add`, doctor, seed |

**Regras de fronteira:**

- Forks-prontas **só leem** de `data/` (JSONL, SQLite, vault)
- Forks-prontas **só escrevem** via MCP gateway → Deep Agent valida → mesh propaga
- Native CLI/TUI **escreve diretamente** em `data/` ou invocam mesh/adapters (sem passar pelo Deep Agent)
- Native CLI/TUI **nunca** é a interface primária que o usuário abre durante o dia

**Anti-patterns documentados:**

- ❌ Construir TUI/CLI nativo tentando substituir forks-prontas
- ❌ Forks-prontas escrevendo diretamente em `data/` (bypass do MCP gateway)
- ❌ Native CLI expondo UI bonita para usuário final (deveria ser forks-prontas)
- ❌ Vault-journal como view do usuário (deferred — inconsistente com dual-layer)

## §3 — Justificativa não-técnica

Por que **duas camadas explícitas** em vez de uma só:

1. **Princípio de especialização** — forks-prontas são otimizadas para a tarefa específica (kanban, tasks, calendário). Native CLI é otimizado para scripting e controle. Misturar = pior dos dois mundos.

2. **HITL explícito** — mudanças via forks-prontas passam por Deep Agent (validação PAE antes de persistir). Native CLI escreve direto (assume que operador sabe o que faz). Sem distinção, não dá pra ter HITL seguro.

3. **Agnóstico de plataforma** — forks-prontas podem ser web, desktop, mobile. Native CLI é sempre terminal. Mantê-los separados permite trocar fork sem reescrever CLI.

4. **Anti-over-engineering** — `interfaces/tui/` está planned/scaffolded (44-line README only) porque PAV era a era de "construir tudo". Agora é claro: native CLI/TUI é operador-only, mínimo necessário.

Por que **vault-journal foi deferido**: a ideia original era vault como view pessoal de journaling. Mas vault é source-of-truth do Deep Agent; misturar journaling pessoal com planejamento viola separação. Decisão: vault = planning only; journaling fica em Obsidian separado (não commitado).

## §4 — Referências cruzadas

### Code
- `src/mesh/adapters/cli.py` — CliAdapter (JSONL store, fork-pronta Layer A)
- `src/mesh/adapters/taskdog.py` — TaskdogAdapter (SQLite, fork-pronta Layer A)
- `src/mesh/adapters/solverforge_calendar.py` — SolverforgeCalendarAdapter (SQLite, fork-pronta Layer A)
- `interfaces/cli/read_tasks.py` — native CLI Layer B (única UI nativa existente)
- `interfaces/tui/README.md` — native TUI Layer B (planned, stub)

### Docs
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` — fork RE Layer A
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` — fork RE Layer A
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` — fork RE Layer A
- `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md` — native TUI gap inventory

### Memory
- `[[interfaces-architecture-2026-08-27]]` — decisão original dual-layer
- `[[master-branch-carro-chefe-2026-08-28]]` — Deep Agent como mediador entre camadas

## §5 — Fontes

- `src/mesh/adapters/base.py` — ForkAdapter Protocol (interface comum Layer A)
- `src/mesh/adapters/cli.py` — CliAdapter (JSONL, atomic temp+rename)
- `src/mesh/adapters/taskdog.py` — TaskdogAdapter (SQLite, UPSERT on ueid)
- `src/mesh/adapters/solverforge_calendar.py` — SolverforgeCalendarAdapter (UPI ueid column)
- `interfaces/cli/read_tasks.py` — única UI nativa em produção
- `interfaces/tui/README.md` — planned (Layer B operador)
- `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md` — RE do CLI nativo
- `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md` — RE do TUI planejado (4 P0 gaps)
