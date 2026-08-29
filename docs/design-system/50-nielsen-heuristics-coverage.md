# 50 — Nielsen Heuristics Coverage (deep-agent era fork-prontas)

> **Categoria:** VALIDATION (Layer 7 — Validation & heuristics, posição #50)
> **Anchor canônico:** `src/operational/docs/ux/08-validacao/01-heuristicas-nielsen.md` (H1–H10)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (UEID, fork, fork adapter, regime, KPI, SCR, FLOW, Nielsen, heurística, kanban, taskdog, solverforge-calendar, dual-layer)
> **Status:** Checklist de avaliação (não é implementação; é lente de leitura para auditoria)

---

## §1 — Resumo

As **10 heurísticas de usabilidade de Jakob Nielsen (1994, rev. 2020)** são o gabarito canônico usado neste docset para auditar qualquer **fork-pronta** (tuiboard, taskdog, solverforge-calendar) antes de ser declarada "pronta para uso do usuário". A camada nativa CLI/TUI (`interfaces/cli/`, `interfaces/tui/`) **não é coberta** por este checklist — ela é operador-only (cross-ref [[interfaces-architecture-2026-08-27]]) e segue governança própria em `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md` e `:05-interfaces-tui.md`.

A ideia-força é: **cada heurística mapeia para um ou mais enforcement mechanisms load-bearing** já documentados nas Layers 3 (patterns), 4 (forks) e 5 (tokens) deste docset. O mapeamento explícito transforma "princípio geral" em "auditoria verificável" — quem audita uma fork abre doc 50, percorre as 10 linhas, e verifica se os mecanismos indicados estão implementados ou referenciados. A pontuação Nielsen histórica do PAV-era (`01-heuristicas-nielsen.md` §H1–H10) é **27/50 (54%, ⭐⭐⭐ médio)** — referência de comparação para a era deep-agent.

**3 forks-prontas in-scope:**
1. **tuiboard** — Bun + SolidJS + OpenTUI; markdown boards + atomic rename (cross-ref `01-fork-tuiboard.md:332`).
2. **taskdog** — Python 3.11+ uv workspace; SQLite + SQLAlchemy 2.0 + 26 MCP tools (cross-ref `02-fork-taskdog.md:497`).
3. **solverforge-calendar** — Rust 2021 + rmcp 3.1; rusqlite + UPI superset + 30 MCP tools (cross-ref `03-fork-solverforge-calendar.md:418`).

**Princípio de cobertura:** **H1–H10 são obrigatórias**, mas a profundidade de aplicação varia. H5 (prevenção) e H9 (diagnóstico de erros) são **bloqueantes** (Severidade Alta per UX-012, UX-014). H6 (reconhecimento vs recordação) e H10 (ajuda) são **P1** (Sprint 2-3). Demais são **P2** (polimento, backlogs). A ordem de prioridade segue `01-heuristicas-nielsen.md:417-422`.

---

## §2 — Inventário

### 2.1 As 10 heurísticas verbatim (de `01-heuristicas-nielsen.md:14-398`)

| # | Heurística | Enunciado canônico (verbatim) |
|:-:|:-----------|:-------------------------------|
| **H1** | Visibilidade do status do sistema | *"The system should always keep users informed about what is going on, through appropriate feedback within reasonable time."* |
| **H2** | Match entre sistema e mundo real | *"The system should speak the users' language, with words, phrases and concepts familiar to the user, rather than system-oriented terms."* |
| **H3** | Controle e liberdade do usuário | *"Users often choose system functions by mistake and need a clearly marked 'emergency exit' to leave the unwanted state without having to go through an extended dialogue."* |
| **H4** | Consistência e padrões | *"Users should not have to wonder whether different words, situations, or actions mean the same thing."* |
| **H5** | Prevenção de erros | *"Even better than good error messages is a careful design which prevents a problem from occurring in the first place."* |
| **H6** | Reconhecimento em vez de recordação | *"Minimize the user's memory load by making objects, actions, and options visible. The user should not have to remember information from one part of the dialogue to another."* |
| **H7** | Flexibilidade e eficiência de uso | *"Accelerators — unseen by the novice user — may often speed up the interaction for the expert user such that the system can cater to both inexperienced and experienced users."* |
| **H8** | Estética e design minimalista | *"Dialogues should not contain information which is irrelevant or rarely needed. Every extra unit of information in a dialogue competes with the relevant information units and diminishes their relative visibility."* |
| **H9** | Ajude usuários a reconhecer, diagnosticar e recuperar erros | *"Error messages should be expressed in plain language (no codes), precisely indicate the problem, and constructively suggest a solution."* |
| **H10** | Ajuda e documentação | *"Even though it is better if the system can be used without documentation, help and documentation may be necessary. Such information should be easy to search, focused on the user's task, list concrete steps, and not be too long."* |

### 2.2 Elementos do docset que satisfazem cada heurística

Resumo cross-ref (carga detalhada em §3):

| # | Enforcement mechanisms (cross-refs) |
|:-:|:--------------------------------------|
| **H1** | Pattern #17 (reliability decorators); token `T-color-scr-*` em doc 30; doc 34 PAV-era banner; doc 31 UEID visual com status |
| **H2** | Doc 32 (component naming) PT-BR/EN; doc 33 (status matrix) 6×4 ortogonal; doc 23 (fork status-enum mapping) |
| **H3** | Doc 13 (ForkAdapter protocol) early-return; doc 12 (append-only queue) reversible; doc 23 undo via UEID |
| **H4** | Doc 32 SCR-NNN naming convention; doc 33 status matrix unificada; doc 30 token system cross-fork |
| **H5** | Doc 31 UEID visual representation; UEID regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (doc 10 §2.1) |
| **H6** | Doc 31 UEID glyph repertoire; doc 30 §3.4 glyph encoding; journeys 40-45 cross-link |
| **H7** | Pattern #14 idempotency; Pattern #15 hysteresis FSM; doc 23 enum flexibility |
| **H8** | Doc 30 §3.5 component slots; minimalismo em doc 32 (sem ícones redundantes) |
| **H9** | Doc 33 status matrix (precisa indicar problema); doc 31 UEID validation msg |
| **H10** | Doc 40 (index journeys); docs 41-45 (journeys específicas); doc 51 (checklist pre-launch) |

---

## §3 — Conteúdo principal

### 3.1 Tabela de auditoria — heurística → enforcement mechanism

A tabela abaixo é o **gabarito de auditoria**. Para cada heurística, lista-se:
- **Mecanismo load-bearing** (token, pattern, contrato, doc canônico)
- **Onde está implementado** (path ou doc)
- **Como verificar** (manual ou programático)
- **Severidade** se faltar (Alta/Média/Baixa)
- **Cross-refs**

#### H1 — Visibilidade do status do sistema

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| Banner persistente | Pattern #17 reliability decorators — `@with_banner` decorator envolve tools MCP com banner PT-BR | doc 17 §2.3 (`docs/design-system/17-pattern-reliability-decorators.md`) | Inspecionar 3 forks: cada tool MCP exposta tem header `⚡ <tool> v0.x` | Média |
| Confirmação após ação | Token `T-color-scr-*` (success = green bold, error = red bold) | doc 30 §3.1 (`docs/design-system/30-tokens-deep-agent-era.md`) | Inspecionar render de `task_create` em cada fork | Alta (UX-013) |
| Feedback de progresso | Doc 34 PAV-era banner (preservado como SUPERSEDED para audit) + novo pattern: `--progress` flag em tools longos | doc 34 §3 + ADR-007 §Decision.4 | Rodar `taskdog batch import 1000 tasks` e observar spinner | Média |
| Timestamp da última ação | Doc 33 status matrix — campo `last_updated_at` carregado em todo fork adapter | doc 33 §3.1 | Inspecionar SQLite schema de cada fork | Baixa |

#### H2 — Match entre sistema e mundo real

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| PT-BR sem jargão | Doc 32 component naming — `SCR-NNN` prefix + kebab-case PT-BR onde possível | doc 32 §3 (`docs/design-system/32-component-naming-conventions.md`) | grep `SCR-` em fork UI; user fora do time deve entender | Alta |
| Glossário de símbolos | Doc 30 §3.4 glyph repertoire (◆▲✗ + UPI badges) | doc 30 §3.4 | User daltônico deve distinguir sem cor (UX-002) | Média |
| Severities familiares | Doc 33 status matrix — `ok`/`warn`/`crit`/`pending`/`active`/`done` | doc 33 §3.1 | Inspecionar 3 forks; mesmas cores/ícones | Média |
| UEID legível | Doc 31 UEID visual — slug human-readable (`byd-case-review` em vez de UUID truncado) | doc 31 §3 (`docs/design-system/31-ueid-visual-representation.md`) | Visualizar UEID em log; operador identifica domínio sem decodificar hex | Baixa |

#### H3 — Controle e liberdade do usuário

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| Emergency exit (q/Ctrl+C) | Doc 13 ForkAdapter protocol — todo tool expõe `--cancel` ou equivalente | doc 13 §2 (`docs/design-system/13-pattern-fork-adapter-protocol.md`) | Rodar fork tool longo e pressionar Ctrl+C; deve sair limpo | Alta |
| Undo via UEID | Doc 12 append-only queue — PROPOSTA: `data/review_queue/` (runtime dir; created by mesh/queue.py when enqueue first runs) preserva histórico; doc 23 enum permite `archived` state | doc 12 + doc 23 §3 (`docs/design-system/12-pattern-append-only-queue.md`) | Criar task, deletar, verificar que fila permite replay | Alta (UX-006) |
| Confirmação destrutiva | Pattern #14 idempotency — `--force` flag obrigatória para delete | doc 14 §3 (`docs/design-system/14-pattern-idempotency-upstream-id.md`) | Tentar delete sem `--force`; fork deve pedir confirmação | Alta (UX-014) |
| Voltar mid-flow | Doc 30 §3.5 component slots — slot `footer_actions` tem botão `cancel` | doc 30 §3.5 | Abrir flow multi-step; cada step tem botão "voltar" | Média |

#### H4 — Consistência e padrões

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| SCR-NNN naming | Doc 32 §3 — `SCR-001-dashboard`, `SCR-042-task-create` | doc 32 §3 | Listar todas as screens de fork; nomes seguem convenção | Média |
| Status matrix unificada | Doc 33 §3 — 6 estados × 4 regimes (PUSH/MAINTAIN/REDUCE/RECOVER) | doc 33 §3 (`docs/design-system/33-status-matrix-unified.md`) | Inspecionar SQLite schema de taskdog; solverforge UPI; tuiboard boards | Média |
| Cross-fork status-enum mapping | Doc 23 §3 — mapeamento fork-status ↔ UEID-state ↔ regime | doc 23 §3 (`docs/design-system/23-fork-status-enum-mapping.md`) | taskdog 4-value enum ↔ solverforge 5-value ↔ tuiboard boolean done | Média |
| Color tokens | Doc 30 §3.1 `T-color-scr-*` enforced across 3 forks | doc 30 §3.1 | Comparar screenshot de "task overdue" em 3 forks; mesma cor | Baixa |

#### H5 — Prevenção de erros

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| UEID validation | UEID regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (anchor `common.py:26`) | doc 10 §2.1 (`docs/design-system/10-pattern-ueid-tri-key.md`) | Tentar criar task com UEID mal-formado; fork rejeita antes de persistir | Alta |
| Idempotência UPSERT | Pattern #14 idempotency — `INSERT … ON CONFLICT (ueid) DO UPDATE` em taskdog + solverforge | doc 14 §3 | Re-criar mesma UEID 100×; estado não duplica | Alta |
| Append-only queue | Doc 12 — fila em PROPOSTA: `data/review_queue/` (runtime dir; created by mesh/queue.py when enqueue first runs) rejeita duplicatas via UEID | doc 12 §3 | Submeter mesma task 2×; segunda entrada ack'd sem propagar | Média |
| Hysteresis FSM | Pattern #15 — 4-state FSM (PUSH/MAINTAIN/REDUCE/RECOVER) com hysteresis previne flicker | doc 15 §3 (`docs/design-system/15-pattern-hysteresis-fsm.md`) | Simular oscilação de regime; transição não é instantânea | Média |

#### H6 — Reconhecimento em vez de recordação

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| Glyph repertoire | Doc 30 §3.4 — `◆▲✗▣▢┃━` com legenda inline | doc 30 §3.4 | User decora 5 glifos; reconhece sem tooltip | Média |
| UEID glyphs (badge) | Doc 31 §3.2 — `tsk:` → ▸, `proj:` → ◆, `hab:` → �, `del:` → ✓ | doc 31 §3.2 | Inspecionar fork UI; badge de tipo aparece ao lado do slug | Baixa |
| Menu numerado / breadcrumb | Doc 30 §3.5 component slots — slot `header_breadcrumb` sempre presente | doc 30 §3.5 | Abrir qualquer fork screen; breadcrumb mostra path atual | Média (UX-008) |
| Journeys canônicas | Docs 41-45 — 5 jornadas canônicas (morning, task-create, policy, weekly, dataset-switch) | doc 40 §2 + docs 41-45 | Auditar fork: cada jornada canônica é completável | Média |

#### H7 — Flexibilidade e eficiência de uso

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| Comando direto vs menu | Doc 23 enum — `life mesh show <ueid>` é accelerator para experts | doc 23 §3 + doc 02 §2 | Rodar `taskdog list_tasks --status=active` direto (skip menu) | Média |
| Hysteresis permite override | Pattern #15 — FSM permite user override via `--force-policy` | doc 15 §3 | User pode pular transição MAINTAIN→REDUCE se tiver justificativa | Média |
| Hybrid meta-vector | Pattern #16 — combina 5 vetores IKIGAI; user pode customizar pesos (deferred per memory) | doc 16 §3 (`docs/design-system/16-pattern-hybrid-meta-vector.md`) | Pesos customizáveis em `~/.config/ikigai/weights.json` | Baixa |
| `--json` em todo comando | Pattern #17 reliability decorators — `--json` flag para scripting | doc 17 §3 | Inspecionar fork CLI; `--json` em todos os comandos | Baixa |

#### H8 — Estética e design minimalista

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| Component slots | Doc 30 §3.5 — 5 slots (header / body / footer / breadcrumbs / actions) | doc 30 §3.5 | Inspecionar fork screen; tem exatamente 5 zonas visuais | Média |
| Doc 32 minimalismo | Doc 32 §3 — sem ícones redundantes; 1 ícone = 1 significado | doc 32 §3 | Comparar 3 forks; nenhum ícone duplicado | Baixa |
| Doc 34 PAV-era banner | Doc 34 §3 — banner original PAV-OS preservado como histórico (não deletado) | doc 34 §3 (`docs/design-system/34-superseded-pav-era-tokens.md`) | Audit: banner PAV existe em fork? Se sim, deve migrar para deep-agent banner | Baixa |
| Whitespace generoso | Pattern #17 — `@with_padding` decorator injeta padding consistente | doc 17 §3 | Inspecionar 3 forks; margens/paddings uniformes | Baixa |

#### H9 — Reconhecer, diagnosticar, recuperar erros

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| Status matrix indica problema | Doc 33 — status `BLOCKED` mostra motivo (FK inválida, recurso faltando) | doc 33 §3.1 | Tentar `task complete <ueid-without-project>`; status BLOCKED + razão | Alta |
| UEID validation msg | Doc 31 §3.1 — UEID mal-formado retorna PT-BR: "UEID deve ter formato `tipo:slug:uuid:hash`" | doc 31 §3.1 | Submeter UEID truncado; mensagem PT-BR clara | Alta (UX-012) |
| Hysteresis log | Pattern #15 — toda transição de regime loga `before_state` → `after_state` com timestamp | doc 15 §3 | Inspecionar SQLite `audit_log`; transições rastreáveis | Média |
| Reliability decorators | Pattern #17 — `@with_retry(3)` + `@with_circuit_breaker` envolvem tools MCP | doc 17 §3 | Falhar 3× consecutivas; circuit breaker abre | Média |

#### H10 — Ajuda e documentação

| Aspecto | Mecanismo | Doc/Path | Verificação | Severidade |
|:--------|:----------|:---------|:------------|:-----------|
| Index de journeys | Doc 40 §2 — índice navegável das 5 jornadas canônicas | doc 40 §2 (`docs/design-system/40-index-user-journeys.md`) | Abrir doc 40; encontrar journey por caso de uso | Média |
| Journey docs 41-45 | Docs 41-45 — narrativa step-by-step com screenshot refs | docs 41-45 | Cada journey tem passos numerados + cross-link para fork doc | Média |
| Pre-launch checklist | Doc 51 §3 — 30 itens para validar fork antes de "ready for user" | doc 51 §3 (`docs/design-system/51-usability-checklist.md`) | PR de fork nova passa por todos os 30 itens | Média |
| Risk catalog | Doc 52 §3 — R1–R12 conhecidos + mitigações | doc 52 §3 (`docs/design-system/52-known-risks-mitigations.md`) | Auditor verifica se R1–R12 estão mitigados em fork | Baixa |

### 3.2 Matriz de severidade cruzada (Nielsen � UX-001..020)

| Heurística | UX-NNN correlato | Severidade herdada |
|:-----------|:-----------------|:-------------------|
| H1 (status) | UX-013 (onboarding cold), UX-016 (auto-load CSV) | Média |
| H2 (mundo real) | UX-001 (Q3 sem definição), UX-009 (pomodoros sem tooltip), UX-012 (Pydantic errors EN) | Alta (UX-012) |
| H3 (controle) | UX-006 (sem undo), UX-014 (clear sem confirmação) | Alta |
| H4 (consistência) | UX-002 (cor invisível daltônicos), UX-003 (layout <100col), UX-018 (S1/S2 indistinguíveis) | Média |
| H5 (prevenção) | UX-005 (--help incompleto), UX-014, UX-015 (seed sem warning) | Alta |
| H6 (reconhecimento) | UX-008 (Cartesian sem label Q?) | Média |
| H7 (flexibilidade) | UX-007 (JSON sem pretty), UX-017 (sem alias) | Baixa |
| H8 (estética) | UX-003 (width), UX-010 (Doctor misturado) | Média |
| H9 (diagnóstico) | UX-020 (TypeError raw) | Média |
| H10 (ajuda) | UX-013 (sem onboarding), UX-005 | Média |

Cross-ref completo UX-NNN: `03-riscos-conhecidos.md:1-326` (20 riscos catalogados).

### 3.3 Estado atual vs meta (PAV-era vs deep-agent era)

**Estado PAV-era (referência histórica):** ⭐⭐⭐ (27/50, 54%) — `01-heuristicas-nielsen.md:417-422`. Áreas prioritárias: H5/H9 (localizar erros + `--dry-run`), H4/H8 (refatorar Doctor + mover para menu), H8 (auto-detect width).

**Estado deep-agent era (meta Batch 8+):**
- H1: ⭐⭐⭐⭐ (4/5) — patterns de banner + reliability decorators implementados
- H2: ⭐⭐⭐⭐ — PT-BR enforced via doc 32; UEID legível via doc 31
- H3: ⭐⭐⭐ — fork adapters têm cancel + append-only queue; undo parcial (gatekeeper via doc 12)
- H4: ⭐⭐⭐⭐ — SCR-NNN naming + status matrix unificada em doc 33
- H5: ⭐⭐⭐⭐⭐ (5/5) — UEID regex + idempotency UPSERT são load-bearing
- H6: ⭐⭐⭐ — glyph repertoire + breadcrumb implementados; legend caption pendente (UX-008)
- H7: ⭐⭐⭐⭐ — comando direto + `--json` + hysteresis override
- H8: ⭐⭐⭐⭐ — component slots + minimalismo enforced
- H9: ⭐⭐⭐⭐ — status matrix indica problema; UEID msg PT-BR
- H10: ⭐⭐⭐⭐ — index de journeys + checklist + risk catalog

**Pontuação esperada:** ~38/50 (76%) se todas as pendências forem fechadas.

---

## §4 — Cross-references

### 4.1 Dentro deste docset

| Doc | Relação |
|:----|:--------|
| `docs/design-system/00-INDEX.md` | Índice navegável (Layer 0) |
| `docs/design-system/02-interfaces-dual-layer-architecture.md` | Define forks-prontas (in-scope) vs native CLI/TUI (out-of-scope) |
| `docs/design-system/10-pattern-ueid-tri-key.md` | Pattern #10 (UEID) — load-bearing para H5/H9 |
| `docs/design-system/11-pattern-frozen-pydantic-strict.md` | Pattern #11 — frozen + extra=forbid |
| `docs/design-system/12-pattern-append-only-queue.md` | Pattern #12 — reversible para H3 undo |
| `docs/design-system/13-pattern-fork-adapter-protocol.md` | Pattern #13 — cancel/early-return para H3 |
| `docs/design-system/14-pattern-idempotency-upstream-id.md` | Pattern #14 — UPSERT para H5 |
| `docs/design-system/15-pattern-hysteresis-fsm.md` | Pattern #15 — override + log para H7/H9 |
| `docs/design-system/16-pattern-hybrid-meta-vector.md` | Pattern #16 — customização pesos para H7 |
| `docs/design-system/17-pattern-reliability-decorators.md` | Pattern #17 — banner + retry + circuit breaker para H1/H9 |
| `docs/design-system/20-fork-tuiboard-architecture.md` | Fork 1 in-scope |
| `docs/design-system/21-fork-taskdog-architecture.md` | Fork 2 in-scope |
| `docs/design-system/22-fork-solverforge-calendar-architecture.md` | Fork 3 in-scope |
| `docs/design-system/23-fork-status-enum-mapping.md` | Cross-fork status mapping para H4 |
| `docs/design-system/30-tokens-deep-agent-era.md` | Tokens canônicos para H1/H4/H6 |
| `docs/design-system/31-ueid-visual-representation.md` | UEID visual + PT-BR validation msg para H5/H9 |
| `docs/design-system/32-component-naming-conventions.md` | SCR-NNN naming para H2/H4 |
| `docs/design-system/33-status-matrix-unified.md` | Status matrix unificada para H4/H9 |
| `docs/design-system/34-superseded-pav-era-tokens.md` | PAV-era banner preservado para H8 |
| `docs/design-system/40-index-user-journeys.md` | Index de journeys para H10 |
| `docs/design-system/41-journey-morning-startup.md` | Journey 1 |
| `docs/design-system/42-journey-task-create.md` | Journey 2 |
| `docs/design-system/43-journey-policy-decision.md` | Journey 3 |
| `docs/design-system/44-journey-weekly-review.md` | Journey 4 |
| `docs/design-system/45-journey-dataset-switch.md` | Journey 5 |
| `docs/design-system/51-usability-checklist.md` | Checklist 30 itens para H10 |
| `docs/design-system/52-known-risks-mitigations.md` | Risk catalog R1–R12 |
| `docs/design-system/53-adr-007-data-first-gate.md` | ADR-007 gate (5+ SONHO logs) |

### 4.2 Forks-prontas (in-scope, externas ao repo)

| Path | Tipo |
|:-----|:-----|
| `life-oss/interfaces/tuiboard/` | Fork-pronta Layer A — Bun + SolidJS |
| `life-oss/interfaces/taskdog/` | Fork-pronta Layer A — Python + SQLite |
| `life-oss/interfaces/solverforge-calendar/` | Fork-pronta Layer A — Rust + rmcp |

### 4.3 Memory references

- `[[interfaces-architecture-2026-08-27]]` — dual-layer (forks = user views; CLI/TUI = operador)
- `[[master-branch-carro-chefe-2026-08-28]]` — Deep Agent mediador
- `[[ai-native-strategic-model-migration-2026-08-26]]` — PAV desativado
- `[[docs-superseded-trailer-2026-08-28]]` — trailer pattern para doc 34
- `[[data-first-methodology]]` — gate de 5+ logs

---

## §5 — Fontes

### 5.1 Fonte primária

- `src/operational/docs/ux/08-validacao/01-heuristicas-nielsen.md` (424 linhas; verbatim §1 Intuição, §2 Aplicação, §3 Exemplos bons, §4 Exemplos ruins, §5 Onde melhorar para H1-H10; resumo final 27/50 em §6)

### 5.2 Fontes secundárias (cross-refs)

- `src/operational/docs/ux/08-validacao/02-checklist-usabilidade.md` (284 linhas; 30+ itens em 8 categorias — C/N/A/P/D/I/M/K — base para doc 51)
- `src/operational/docs/ux/08-validacao/03-riscos-conhecidos.md` (326 linhas; UX-001 a UX-020 — base para doc 52)
- `docs/design-system/02-interfaces-dual-layer-architecture.md` (definição forks-prontas Layer A)
- `docs/design-system/34-superseded-pav-era-tokens.md` (banner PAV-OS preservado)
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (estado atual das 3 forks)
- `code-docs/adr/ADR-007-data-first-methodology.md` (constraint 5+ SONHO logs)
- Nielsen, J. (1994, rev. 2020). *"10 Usability Heuristics for User Interface Design."* Nielsen Norman Group. https://www.nngroup.com/articles/ten-usability-heuristics/

### 5.3 Notas de leitura

- Quem audita uma fork deve começar por §3.1 (mecanismos load-bearing) antes de §2 (inventário).
- §3.2 (matriz Nielsen ↔ UX-NNN) é o atalho para quem já conhece o catálogo de riscos PAV-era.
- §3.3 (estado atual vs meta) é leitura executiva — 30 segundos dá visão geral.
- Doc 51 (checklist) e doc 52 (risks) são **complementares** a este — não substituem.
