# 52 — Known Risks & Mitigations (Phase 3 readiness)

> **Categoria:** VALIDATION (Layer 7 — Validation & heuristics, posição #52)
> **Anchor canônico:** `src/operational/docs/ux/08-validacao/03-riscos-conhecidos.md` (UX-001..UX-020) + Phase 2 synthesis `06-synthesis-mesh-readiness.md` (B-01..B-08)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (UEID, fork, fork adapter, regime, KPI, SCR, FLOW, risk, mitigation, mesh, gateway, Phase 3, ADR-007, data drift, SONHO, gatekeeper, pattern mismatch)
> **Status:** Catálogo de riscos conhecidos para Phase 3 mesh readiness (12 riscos R1-R12)

---

## §1 — Resumo

Este documento cataloga os **12 riscos conhecidos (R1–R12)** que bloqueiam ou degradam a **Phase 3 mesh readiness** das 3 forks-prontas (tuiboard, taskdog, solverforge-calendar). Cada risco tem: **descrição, impacto, mitigação proposta, owner, e status atual**. Os riscos combinam duas fontes primárias:

1. **UX-001..UX-020** (catálogo PAV-era `03-riscos-conhecidos.md:1-326`) — 20 riscos de UX priorizados P0/P1/P2.
2. **Phase 2 RE synthesis** (`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md:189-195`) — 6 achados técnicos (B-01 gateways.yaml stale, B-04 data/tasks.jsonl missing, B-05 taskdog_* prefix dead, B-07 contracts drift, B-08 CLI install drift) + 4 fork-specific bugs (`01-fork-tuiboard.md:243-247`, `02-fork-taskdog.md:244-253`, `03-fork-solverforge-calendar.md:222-237`).

**Princípio:** R1–R12 são **específicos da era deep-agent + Phase 3**; o catálogo UX-NNN PAV-era é **histórico** (aponta para issues pré-pivot) e este doc R-NNN é o catálogo **ativo**. Onde houver overlap (ex.: R4 ↔ UX-014 `clear sem confirmação`), cite ambos.

**3 blockers top-priority (Phase 3 não ship sem resolver):**
- **R1 — `gateways.yaml` cwd stale** (B-01): caminhos apontam para `apps/{kanban,dev-tools,calendar}` (deletados); forks em `life-oss/interfaces/{tuiboard,taskdog,solverforge-calendar}`.
- **R4 — `taskdog_*` prefix dead + `archive_task` dead token** (B-05): 20/26 tools taskdog inalcançáveis; gateway tem entradas mortas.
- **R10 — ADR-007 data-first gate não respeitado** (`code-docs/adr/ADR-007-data-first-methodology.md`): IKIGAi agent não pode rodar antes de 5+ SONHO logs manuais.

---

## §2 — Inventário

### 2.1 Risk matrix (severidade × likelihood)

| | **Likelihood: Baixa** | **Likelihood: Média** | **Likelihood: Alta** |
|:---|:---|:---|:---|
| **Severidade: Alta** | R10 (gate) | R1, R2, R3, R4, R5 | R11 (data drift) |
| **Severidade: Média** | R12 (docs stale) | R6, R7, R8 | R9 |
| **Severidade: Baixa** | — | — | — |

### 2.2 Inventário verbatim R1–R12

| ID | Título | Sev | Lik | Status |
|:---|:-------|:----|:----|:-------|
| **R1** | `gateways.yaml` cwd paths stale | Alta | Média | OPEN (Phase 3 P0) |
| **R2** | `data/tasks.jsonl` MISSING | Alta | Média | OPEN (Phase 3 P0) |
| **R3** | `solverforge google_sync` stub | Alta | Média | OPEN (Phase 3 P0) |
| **R4** | `taskdog_*` prefix dead + 20 tools unreachable | Alta | Média | OPEN (Phase 3 P0) |
| **R5** | `archive_task` dead entry + FALLBACK misroute risk | Alta | Média | OPEN (Phase 3 P0) |
| **R6** | solverforge HTTP+SSE compile-dead | Média | Média | OPEN (Phase 3 P1) |
| **R7** | tuiboard MCP entry path errado (`bin/tuiboard.ts --mcp`) | Média | Média | OPEN (Phase 3 P1) |
| **R8** | taskdog OTel zero em client/server/UI | Média | Média | OPEN (Phase 3 P1) |
| **R9** | Pattern mismatch: fork status enum divergence | Média | Alta | OPEN (Phase 3 P1) |
| **R10** | ADR-007 data-first gate (5+ SONHO logs) | Alta | Baixa | BLOCKED (counter 1/5) |
| **R11** | Data drift entre forks (UEID não compartilhado) | Alta | Alta | OPEN (Phase 3 P1) |
| **R12** | Docs stale pós-pivot (docs PAV-era sem trailer) | Média | Baixa | PARTIAL (doc 34 trailer applied) |

---

## §3 — Conteúdo principal

### R1 — `gateways.yaml` cwd paths stale (Phase 3 P0)

- **Descrição:** `apps/mcp-gateway/config/gateways.yaml:4,9,14` referencia paths `apps/{kanban,dev-tools,calendar}/` (diretórios **deletados** no reorg 2026-08-28 — ver `[[windows-orphan-dir-delete]]`). Forks foram migrados para `life-oss/interfaces/{tuiboard,taskdog,solverforge-calendar}/`. Gateway tenta spawn de subprocess em paths inexistentes.
- **Impacto:** Gateway MCP **não alcança nenhuma fork-pronta** hoje. Phase 3 mesh readiness é zero.
- **Mitigação:** Reparar `gateways.yaml:4,9,14` com paths novos. Validar via `mcp-gateway status` (ou equivalente).
- **Owner:** operador + agente de code review
- **Status:** OPEN (Phase 3 P0; pre-launch blocker)
- **Refs:** `06-synthesis-mesh-readiness.md:189`; `01-fork-tuiboard.md:243-245`; `02-fork-taskdog.md:458`; `03-fork-solverforge-calendar.md:402`
- **Severidade herdada:** Alta (Phase 3 readiness = zero até resolver)

### R2 — `data/tasks.jsonl` MISSING (Phase 3 P0)

- **Descrição:** `data/tasks.jsonl` (intercâmbio canônico mesh) **não existe** hoje (`04-interfaces-cli.md:140-142`). 3 writers (`daily_consolidator.py:108, 327, 352, 402`; `_write_tasks_to_data` em `src/ikigai/src/mcp_server/server.py:287-327`) nunca foram invocados.
- **Impacto:** `interfaces/cli/` (Layer B operador) **não pode ler tasks**. 14-field schema flat (`04-interfaces-cli.md:34-53`) está orfanão.
- **Mitigação:** Decidir entre (a) **regenerate** `data/tasks.jsonl` a partir de taskdog SQLite via ETL único; (b) **abandonar JSONL** e adotar UPI (solverforge-calendar) como mesh interchange (cross-ref `06-synthesis-mesh-readiness.md:88`). Recomendação Phase 2: **Option B (UPI)**.
- **Owner:** operador + agente de migração
- **Status:** OPEN (Phase 3 P0; decision pending)
- **Refs:** `06-synthesis-mesh-readiness.md:194`; `04-interfaces-cli.md:79-82,140-142`
- **Severidade herdada:** Alta

### R3 — `solverforge google_sync` MCP stub (Phase 3 P0)

- **Descrição:** `solverforge-calendar`'s `google_sync` MCP tool (`mcp.rs:773`) é **stub** retornando `not_implemented`. Sync real com Google Calendar é **CLI-only** em `src/cli.rs` (`03-fork-solverforge-calendar.md:179`).
- **Impacto:** Agent MCP-driven não pode sincronizar com Google Calendar; precisa spawnar subprocess CLI. Adiciona latência + quebra HITL pattern.
- **Mitigação:** Implementar `google_sync` MCP tool real (delegar para `src/cli.rs` internamente OU reescrever para usar API direto). Dependência `google-calendar3 7.0` está unused (`03-fork-solverforge-calendar.md:143, 400`).
- **Owner:** solverforge-calendar fork maintainer
- **Status:** OPEN (Phase 3 P0)
- **Refs:** `06-synthesis-mesh-readiness.md:192`; `03-fork-solverforge-calendar.md:179`
- **Severidade herdada:** Alta

### R4 — `taskdog_*` prefix dead + 20/26 tools unreachable (Phase 3 P0)

- **Descrição:** `gateways.yaml:8-10` declara prefixo `taskdog_*` (morta — nenhuma tool MCP taskdog usa este prefixo) + 7 exact tokens. Tools taskdog reais são **unprefixed** (`list_tasks`, `start_task`, `complete_task`, etc. — `02-fork-taskdog.md:233-242`). **20 de 26 tools taskdog são inalcançáveis** hoje.
- **Impacto:** Gateway roteia unprefixed taskdog tools via FALLBACK para solverforge-calendar (router.py:24) — misroute silencioso.
- **Mitigação:** (a) Atualizar `gateways.yaml:8-10` para listar prefixos corretos (`taskdog.*` namespace OU adicionar 20 tools ao `exact_map` antes do FALLBACK solverforge-calendar). (b) Adicionar `taskdog.*` prefix em todos os tools MCP. Recomendação Phase 2: **Option B** (exact_map primeiro).
- **Owner:** operador + gateway maintainer
- **Status:** OPEN (Phase 3 P0)
- **Refs:** `06-synthesis-mesh-readiness.md:191`; `02-fork-taskdog.md:235,244-253`
- **Severidade herdada:** Alta

### R5 — `archive_task` dead entry + FALLBACK misroute risk (Phase 3 P0)

- **Descrição:** `gateways.yaml` tem `archive_task` no `exact_map`, mas MCP expõe `delete_task(hard=False)` (`02-fork-taskdog.md:240-242`). Token morto. Além disso, router FALLBACK (`router.py:24`) roteia unknown para solverforge-calendar — risco de misroute se nova tool `events_query` aparecer em fork errada.
- **Impacto:** Confusão operacional; possível misroute silencioso em produção.
- **Mitigação:** (a) Remover `archive_task` morto. (b) Adicionar log quando FALLBACK é usado (audit trail). (c) Considerar fail-closed para unknown tokens (rejeitar com erro claro em vez de rotear).
- **Owner:** gateway maintainer
- **Status:** OPEN (Phase 3 P0)
- **Refs:** `06-synthesis-mesh-readiness.md:64-65`; `02-fork-taskdog.md:241`
- **Severidade herdada:** Alta

### R6 — solverforge HTTP+SSE compile-dead (Phase 3 P1)

- **Descrição:** `solverforge-calendar` tem código HTTP+SSE em `mcp.rs:916-958`, mas feature `http` **não está em `Cargo.toml` features list** (`03-fork-solverforge-calendar.md:199, 399`). Branch é compile-dead (não compilado, não distribuído).
- **Impacto:** Hoje irrelevante (todos os forks são stdio-only — OQ-8 Option A). Risco futuro se remote agents forem introduzidos.
- **Mitigação:** (a) Adicionar `http` feature explicitamente OU remover código morto. (b) Decidir remote agent strategy antes de precisar.
- **Owner:** solverforge-calendar fork maintainer
- **Status:** OPEN (Phase 3 P1; defer)
- **Refs:** `06-synthesis-mesh-readiness.md:193`; `03-fork-solverforge-calendar.md:199`
- **Severidade herdada:** Média

### R7 — tuiboard MCP entry path errado (Phase 3 P1)

- **Descrição:** Gateway command para tuiboard é `["bun", "run", "src/bin/tuiboard.ts", "--mcp"]` — errado. MCP entry real é `bin/tuiboard-mcp.ts:16`, não o launcher (`01-fork-tuiboard.md:327`).
- **Impacto:** Mesmo com R1 resolvido, tuiboard falha ao spawnar MCP server (entry path errado).
- **Mitigação:** Corrigir `gateways.yaml` para usar `bin/tuiboard-mcp.ts`. Validar spawn + handshake MCP.
- **Owner:** operador + gateway maintainer
- **Status:** OPEN (Phase 3 P1; depende de R1)
- **Refs:** `06-synthesis-mesh-readiness.md:190`; `01-fork-tuiboard.md:327`
- **Severidade herdada:** Média

### R8 — taskdog OTel zero em client/server/UI (Phase 3 P1)

- **Descrição:** OTel só existe em `taskdog-mcp`; client, server, UI têm **zero** observabilidade (`02-fork-taskdog.md:396-407`). Tuiboard e solverforge-calendar têm OTel condicional (gateado por env var).
- **Impacto:** Debugging distribuído difícil; impossível correlacionar request flow cross-fork.
- **Mitigação:** (a) Adicionar OTel em client/server/UI taskdog. (b) Padronizar OTel config cross-fork (mesmo exporter, mesmo propagator). (c) Habilitar por padrão em dev (env var `OTEL_ENABLED=true` por fork).
- **Owner:** taskdog fork maintainer
- **Status:** OPEN (Phase 3 P1)
- **Refs:** `06-synthesis-mesh-readiness.md:31` (matrix); `02-fork-taskdog.md:396-407`
- **Severidade herdada:** Média

### R9 — Pattern mismatch: fork status enum divergence (Phase 3 P1)

- **Descrição:** 3 forks têm 3 status enum shapes diferentes — taskdog `TaskStatus` 4-value (`02-fork-taskdog.md:74`), solverforge `UPI.status` 5-value (`03-fork-solverforge-calendar.md:84`), tuiboard boolean `done` + column position (`01-fork-tuiboard.md:261-264`). Cross-fork join requer mapping layer.
- **Impacto:** Mesh queries cross-fork precisam de translation table. Risco de mis-mapping silencioso.
- **Mitigação:** (a) Implementar PROPOSTA: `mesh_ueid` (column name — taskdog task table) join field (OQ-7 Option C — `06-synthesis-mesh-readiness.md:106`). (b) Aplicar `docs/design-system/23-fork-status-enum-mapping.md` (cross-fork status mapping canônico). (c) Test cross-fork: criar task em fork A, ler em B, validar status correto.
- **Owner:** operador + fork maintainers
- **Status:** OPEN (Phase 3 P1)
- **Refs:** `06-synthesis-mesh-readiness.md:78`; doc 23 §3; `04-interfaces-cli.md:46-47`
- **Severidade herdada:** Média

### R10 — ADR-007 data-first gate (5+ SONHO logs) (BLOCKED)

- **Descrição:** ADR-007 (`code-docs/adr/ADR-007-data-first-methodology.md`) **proíbe** qualquer código IKIGAi agent até 5+ SONHO logs manuais em `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/YYYY-MM-DD-sonho.md`. Counter atual: **1/5** (per `[[ikigai-persona-vault-bootstrap]]`, SONHO log de 2026-07-09).
- **Impacto:** IKIGAi agent **não pode rodar em produção** sem o gate. Phase 3 mesh readiness fica parcial (mesh existe mas agent validador central está pausado).
- **Mitigação:** (a) Continuar logging manual SONHO (1 a cada 7-10 dias). (b) Após 5/5, solicitar revisão do gate (re-affirm ou revogar). (c) **Não bypassar** — ADR-007 foi explicitamente aceito para corrigir ordem (math-first → data-first).
- **Owner:** operador (você — quem loga)
- **Status:** BLOCKED (counter 1/5; esperado ≥5/5 antes de Q1-2027)
- **Refs:** `code-docs/adr/ADR-007-data-first-methodology.md`; `[[data-first-methodology]]`; `[[ikigai-persona-vault-bootstrap]]`
- **Severidade herdada:** Alta (gate institucional; não negociável)

### R11 — Data drift entre forks (UEID não compartilhado) (Phase 3 P1)

- **Descrição:** Apenas `interfaces/cli` tem UEID 5-part (`tsk:slug:uuid:hash` — `04-interfaces-cli.md:48`). taskdog usa `id: int`, solverforge usa UUID v4, tuiboard usa board-path + position. **Mesh não tem UEID hoje** — cada fork inventa sua própria identidade.
- **Impacto:** Cross-fork join é estruturalmente impossível sem tradução; queries mesh requerem mapping layer (PROPOSTA: `mesh_ueid` (column name — taskdog task table)). Drift inevitável se entities editadas em paralelo.
- **Mitigação:** (a) Adicionar coluna UEID em todas as 3 forks como **second key** (não PK). (b) Manter PK local (int / UUID v4 / position). (c) Criar PROPOSTA: `mesh_ueid` (column name — taskdog task table) mapping table no mesh layer. (d) OQ-7 Option C (`06-synthesis-mesh-readiness.md:106`).
- **Owner:** operador + fork maintainers
- **Status:** OPEN (Phase 3 P1; data drift risk)
- **Refs:** `06-synthesis-mesh-readiness.md:33,89,106`; doc 10 §2.3; `04-interfaces-cli.md:48`
- **Severidade herdada:** Alta

### R12 — Docs stale pós-pivot (PAV-era sem trailer) (PARTIAL)

- **Descrição:** Alguns docs PAV-era ainda não têm trailer SUPERSEDED aplicado. `docs/design-system/34-superseded-pav-era-tokens.md` já tem trailer. Outros docs (em `src/operational/docs/design-system/DESIGN-SYSTEM.md` — alvo do trailer Task C) ainda pendentes.
- **Impacto:** Confusão para agents futuros: "este doc é canônico ou histórico?".
- **Mitigação:** Aplicar trailer SUPERSEDED em todos os docs PAV-era (batch trailer campaign). Pattern em `[[docs-superseded-trailer-2026-08-28]]`.
- **Owner:** operador
- **Status:** PARTIAL (doc 34 aplicado; outros em campanha)
- **Refs:** `docs/design-system/34-superseded-pav-era-tokens.md`; `src/operational/docs/design-system/DESIGN-SYSTEM.md` (Task C)
- **Severidade herdada:** Média

---

## §4 — Cross-references

### 4.1 Dentro deste docset

| Doc | Relação |
|:----|:--------|
| `docs/design-system/00-INDEX.md` | Índice navegável |
| `docs/design-system/50-nielsen-heuristics-coverage.md` | H1-H10 ↔ R-NNN (cross-walk) |
| `docs/design-system/51-usability-checklist.md` | Checklist 30 itens ↔ R-NNN (mitigação) |
| `docs/design-system/53-adr-007-data-first-gate.md` | Gate ADR-007 ↔ R10 (gate principal) |
| `docs/design-system/10-pattern-ueid-tri-key.md` | UEID ↔ R11 (data drift) |
| `docs/design-system/13-pattern-fork-adapter-protocol.md` | ForkAdapter ↔ R4, R5 (gateway routing) |
| `docs/design-system/14-pattern-idempotency-upstream-id.md` | Idempotency ↔ R4 (misroute risk) |
| `docs/design-system/23-fork-status-enum-mapping.md` | Status matrix ↔ R9 (enum divergence) |

### 4.2 Phase 2 RE docs

- `docs/diagnostics/2026-08-28-phase2-interface-re/00-INDEX.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` (332 linhas; fonte para R7, R9, R11)
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` (497 linhas; fonte para R4, R5, R8, R9, R11)
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` (418 linhas; fonte para R3, R6, R9, R11)
- `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md` (197 linhas; fonte para R2, R11)
- `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md` (~165 linhas)
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (síntese canônica; fonte para R1-R9, R11-R12)

### 4.3 UX-NNN overlap (PAV-era)

- R4 ↔ UX-009 (pomodoros sem tooltip — parcialmente)
- R5 ↔ UX-014 (`clear` sem confirmação — parcialmente)
- R11 ↔ UX-020 (TypeError raw) — derivado
- R12 ↔ UX-013 (sem onboarding) — derivado

Cross-ref completo UX-NNN: `03-riscos-conhecidos.md:1-326`.

### 4.4 Memory references

- `[[interfaces-architecture-2026-08-27]]` — forks = user views (R1-R12 audita forks)
- `[[master-branch-carro-chefe-2026-08-28]]` — Deep Agent mediador (R10 gate)
- `[[data-first-methodology]]` — ADR-007 gate (R10)
- `[[ikigai-persona-vault-bootstrap]]` — SONHO 1/5 (R10 counter)
- `[[windows-orphan-dir-delete]]` — apps/{kanban,dev-tools,calendar} deletados (R1)
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway unmerged (R4, R5)
- `[[docs-superseded-trailer-2026-08-28]]` — trailer pattern (R12)

---

## §5 — Fontes

### 5.1 Fonte primária

- `src/operational/docs/ux/08-validacao/03-riscos-conhecidos.md` (326 linhas; UX-001 a UX-020; P0/P1/P2 priorizados)
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (síntese; 6 B-NN findings + 4 fork bugs)

### 5.2 Fontes secundárias

- `code-docs/adr/ADR-007-data-first-methodology.md` (R10 gate institucional)
- `docs/design-system/50-nielsen-heuristics-coverage.md` (mapeamento H1-H10 ↔ R-NNN)
- `docs/design-system/51-usability-checklist.md` (checklist mitiga R-NNN)
- `docs/design-system/53-adr-007-data-first-gate.md` (detalhamento R10)
- `src/operational/docs/architecture/` (arquitetura PAV-era para context histórico)

### 5.3 Notas de leitura

- Quem audita Phase 3 começa por §3.1 (R1, R2, R3, R4, R5 — Phase 3 P0 blockers).
- R10 é gate institucional (não bypass); respeitar ADR-007.
- R11 (data drift) é o risco mais sneaky — silencioso, cross-fork, requer UEID propagation.
- R12 é polimento pós-pivot — não bloqueia Phase 3, mas limpa audit trail.
- Phase 3 readiness = **0%** até R1-R5 fechados; ≈80% após R1-R5 + R9-R11 fechados.
