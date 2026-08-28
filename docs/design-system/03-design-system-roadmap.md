# 03 — Design System Roadmap (PAV → Deep-Agent Migration)

> **Categoria:** NEW
> **Público:** Eu mesmo + agentes futuros
> **Localização:** `docs/design-system/03-design-system-roadmap.md`
> **Origem:** narrativa da migração PAV → era deep-agent

---

## §1 — Intuição em linguagem simples

O design system passou por **3 fases distintas**:

1. **Era PAV-built-from-scratch** (até 2026-08-26) — tokens, componentes, telas construídas em `src/operational/` com Pydantic + Rich + Textual. 1976-line `PAV_INVENTORY.md` documenta tudo.

2. **Era de transição** (2026-08-26 a 2026-08-28) — fork-prontas reconhecidas como superiores; PAV marcado como deprecated; reorg P0 bugs corrigidos.

3. **Era deep-agent canonical** (2026-08-28 em diante) — Deep Agent carro-chefe, forks-prontas como user views, native CLI/TUI apenas operador. PAV é **reference implementation matemática**, não sistema canônico.

Esta doc é o **roadmap vivo** do design system: o que mudou, por que, e o que vem a seguir.

## §2 — Enunciado formal

**Comparação entre eras:**

| Aspecto                  | Era PAV (≤2026-08-26)        | Era deep-agent (≥2026-08-28) |
|:-------------------------|:-----------------------------|:------------------------------|
| Carro-chefe              | PAV TUI/CLI                  | Deep Agent (LangGraph)        |
| User views               | PAV TUI nativo               | forks-prontas (tuiboard/taskdog/solverforge) |
| Token source-of-truth    | `src/operational/docs/design-system/DESIGN-SYSTEM.md` | Este docset (Layer 5)         |
| Componentes              | 12 UX components + 11 v2 refactors | Cross-link para PAV-era + UEID visual novo |
| Token implementation    | Python classes (Severity/Style) | Markdown (intenção) + fork-specific |
| Padronização             | 120-col fixed terminal width  | Por fork (Bun/Python/Rust)    |
| HITL                     | Não tinha                    | `interrupt_on={"write_file": True}` |
| Daily-driver fork        | PAV TUI                      | tuiboard (Kanban)             |
| Backlog de UI            | 4 P0 gaps em `interfaces/tui/` | Deferido até demanda empírica |

**Status pós-pivot (2026-08-28):**

| Componente                    | Status pós-pivot          |
|:------------------------------|:--------------------------|
| `src/operational/docs/design-system/DESIGN-SYSTEM.md` | SUPERSEDED — trailer a ser adicionado no Batch 6 |
| `src/operational/docs/ux/`    | Mantido como **reference** (não canonical) |
| `src/operational/packages/core/src/operational/ui/` | Sem código (referências em docs são pseudocódigo) |
| `interfaces/cli/read_tasks.py` | Único nativo Layer B operacional |
| `interfaces/tui/`              | Stub (4 P0 gaps) |
| `docs/diagnostics/2026-08-28-phase2-interface-re/` | **Anchors canônicos** para forks-prontas |

## §3 — Justificativa não-técnica

**Por que a migração foi necessária:**

1. **PAV TUI/CLI tinha 9 telas, 14 repos, 2518 testes, 4-state FSM** — investimento massivo sem uso diário observado. ADR-007 data-first methodology inverteu a política.

2. **Forks-prontas são maduras** — tuiboard/taskdog/solverforge-calendar são projetos open-source MIT/Apache com anos de desenvolvimento. Construir paralelo era desperdício.

3. **Vault é source-of-truth** — sempre foi a verdade canônica para planejamento (markdown human-readable). Deep Agent lê/escreve markdown nativamente; PAV exigia transformação.

4. **HITL explícito** — mudanças em vault via Deep Agent passam por aprovação humana antes de persistir. PAV não tinha essa camada.

**O que mudou na prática para o usuário:**

| Antes (PAV)                                | Depois (deep-agent)                  |
|:-------------------------------------------|:-------------------------------------|
| Abrir PAV TUI como primeira tela do dia    | Abrir tuiboard (Kanban)              |
| Tasks marcadas direto no SQLite            | Tasks via tuiboard → MCP → Deep Agent → mesh |
| Q_HE calculado em Python, plot em terminal | Q_HE consultado via `ikigai_score` MCP tool |
| Pomodoros tinham SM de 7 estados próprio    | Pomodoros viram TaskChange → mesh    |
| Templates de planejamento em `apps/cli/`    | Templates em vault markdown          |

**O que NÃO mudou (continua válido):**

- Toda a matemática auto-performance (H(t), Q_HE, hysteresis FSM, hybrid meta-vector, UCB) documentada em `docs/auto-performance-os/`
- Contratos Pydantic em `src/contracts/`
- UEID como canonical join key
- Sync Engine (Obsidian ↔ SQLite ↔ Taskwarrior)
- Append-only invariant em vault/, vibe-ops/, strategics/

**Próximos marcos (post-2026-08-28):**

- 5+ SONHO logs manuais (gate ADR-007) antes de qualquer nova entidade
- Fechamento Q3-2026 em `vault/ikigai/closing-2026/01-q3-2026/`
- 2 graphs reais (ikigai_maintainer + pae_maintainer) estáveis
- 3 forks-prontas integradas via MCP com mesh propagando

## §4 — Referências cruzadas

### Code
- `src/operational/` — PAV kernel (desativado, reference only)
- `src/ikigai/src/agents/deepagents_harness.py` — Deep Agent
- `src/ikigai/src/mcp_server/server.py` — MCP gateway
- `src/mesh/adapters/*.py` — 3 forks adapters

### Docs
- `docs/PAV_INVENTORY.md` (1976 linhas, SUPERSEDED)
- `src/operational/docs/design-system/DESIGN-SYSTEM.md` (676 linhas, SUPERSEDED)
- `vault/ikigai/meta/agents.md` — meta-learning IKIGAI
- `docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md` — 95 docs classificados

### Memory
- `[[ai-native-strategic-model-migration]]` — pivot 2026-08-26
- `[[legacy-pav-ui-era-2026-08-28]]` — era PAV deprecated
- `[[master-branch-carro-chefe-2026-08-28]]` — novo canônico
- `[[data-first-methodology]]` — ADR-007 constraint

## §5 — Fontes

- `src/operational/docs/design-system/DESIGN-SYSTEM.md` (676 linhas) — a ser trailer'd
- `docs/PAV_INVENTORY.md` (1976 linhas) — inventory PAV
- `src/operational/packages/core/src/operational/core/` — código matemático auto-performance
- `vault/ikigai/meta/agents.md` — meta-learning IKIGAI (9 telas audit)
- `vault/ikigai/meta/cycle-bootstrap-analysis-2026-08-26.md` — primeiro ciclo IKIGAi
- `docs/diagnostics/2026-08-28-structure-audit/00-INDEX.md` — 40 achados estruturais
- `docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md` — 95 docs classificados
