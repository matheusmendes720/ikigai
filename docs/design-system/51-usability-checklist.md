# 51 — Pre-Launch Usability Checklist (fork-pronta)

> **Categoria:** VALIDATION (Layer 7 — Validation & heuristics, posição #51)
> **Anchor canônico:** `src/operational/docs/ux/08-validacao/02-checklist-usabilidade.md` (30+ itens PAV-era)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (UEID, fork, fork adapter, regime, KPI, SCR, FLOW, checklist, WCAG, contrast ratio, latency, retry, SLA, fork-pronta, dual-layer)
> **Status:** Checklist pré-launch (30 itens em 6 categorias; copy template + preencher por fork)

---

## §1 — Resumo

Este documento é o **checklist pré-launch** que qualquer fork-pronta (tuiboard, taskdog, solverforge-calendar, ou fork-pronta futura) deve passar antes de ser declarada "pronta para uso do usuário". O checklist tem **30 itens agrupados em 6 categorias** (visual, interação, dados, acessibilidade, recoverability, sync), inspirado em `02-checklist-usabilidade.md` (PAV-era, 30+ itens em 8 categorias C/N/A/P/D/I/M/K) e adaptado para a era deep-agent canonical.

**Princípio de aplicação:** cada item tem **critério de pass/fail binário** + **medição concreta** (não subjetivo). Items Alta bloqueiam merge; items Média podem mergir com issue aberto; items Baixa são polimento (backlog). Severidades seguem convenção de `02-checklist-usabilidade.md:40-45`.

**Modo de uso:**
1. Copiar o template do checklist (ver §3.0 abaixo) para o PR description ou comment
2. Preencher todos os 30 itens antes de marcar fork como "ready for user"
3. Anexar output ao PR review
4. Arquivar output em PROPOSTA: `docs/design-system/51-checklist-runs/<fork>-<date>.md` (placeholder checklist output filename template) para audit trail

**Quem audita:** operador (você) + agente de code review. Quem é auditado: dev da fork-pronta antes de PR merge.

---

## §2 — Inventário

### 2.1 As 6 categorias

| # | Categoria | Items | Foco |
|:-:|:----------|:-----:|:-----|
| **CAT-V** | **Visual** | 6 itens (V-1 a V-6) | Tokens, cores, layout, tipografia |
| **CAT-I** | **Interaction** | 5 itens (I-1 a I-5) | Teclado, navegação, fluxo |
| **CAT-D** | **Data** | 5 itens (D-1 a D-5) | Estado vazio, corrupção, validação |
| **CAT-A** | **Accessibility** | 4 itens (A-1 a A-4) | WCAG, cor, encoding, daltonismo |
| **CAT-R** | **Recoverability** | 5 itens (R-1 a R-5) | Erro, undo, retry, circuit breaker |
| **CAT-S** | **Sync** | 5 itens (S-1 a S-5) | Cross-fork consistency, queue, idempotency |

**Total:** 30 itens (Alta: 11, Média: 13, Baixa: 6).

### 2.2 Distribuição de severidade

| Severidade | Items | Bloqueia merge? |
|:-----------|:------|:----------------|
| **Alta** | V-1, V-2, I-1, I-2, I-5, D-1, D-5, R-1, R-4, S-1, S-4 | Sim |
| **Média** | V-3, V-4, I-3, D-2, D-3, D-4, A-1, A-2, R-2, R-3, S-2, S-3, S-5 | Não (com issue aberto) |
| **Baixa** | V-5, V-6, I-4, A-3, A-4, R-5 | Não (backlog) |

### 2.3 Cross-ref para docset canônico

| Categoria | Docs load-bearing |
|:----------|:------------------|
| CAT-V | `docs/design-system/30-tokens-deep-agent-era.md`, `:31-ueid-visual-representation.md`, `:32-component-naming-conventions.md`, `:33-status-matrix-unified.md`, `:34-superseded-pav-era-tokens.md` |
| CAT-I | `:10-pattern-ueid-tri-key.md`, `:13-pattern-fork-adapter-protocol.md`, `:40-index-user-journeys.md`, `:41-journey-morning-startup.md`, `:42-journey-task-create.md` |
| CAT-D | `:11-pattern-frozen-pydantic-strict.md`, `:12-pattern-append-only-queue.md`, `:14-pattern-idempotency-upstream-id.md` |
| CAT-A | `:30-tokens-deep-agent-era.md` §3.4 (glyph repertoire), `:33-status-matrix-unified.md` (text + glyph dual-encoding) |
| CAT-R | `:12-pattern-append-only-queue.md`, `:15-pattern-hysteresis-fsm.md`, `:17-pattern-reliability-decorators.md` |
| CAT-S | `:14-pattern-idempotency-upstream-id.md`, `:04-canvas-mesh-architecture.md`, `:07-canvas-sync-architecture.md`, `:23-fork-status-enum-mapping.md` |

---

## §3 — Conteúdo principal

### 3.0 Template de uso (copy-paste)

```markdown
## Review da Fork: <fork-name> v<x.y.z>

**Revisor:** @<operator>
**Data:** YYYY-MM-DD
**Fork:** life-oss/interfaces/<fork-name>/
**PR:** #NNN

### Visual (CAT-V)
- [ ] V-1: ... PASS / FAIL — <nota>
- [ ] V-2: ...

### Interaction (CAT-I)
- [ ] I-1: ...

### Data (CAT-D)
- [ ] D-1: ...

### Accessibility (CAT-A)
- [ ] A-1: ...

### Recoverability (CAT-R)
- [ ] R-1: ...

### Sync (CAT-S)
- [ ] S-1: ...

## Veredicto
[ ] Aprovado (todos Alta passam)
[ ] Aprovado com comentários (≤3 Média falham)
[ ] Mudanças necessárias (>3 Média falham ou ≥1 Alta falha)

## Métricas observadas
- Latência p50 do menu principal: <NNms> (meta: <200ms)
- WCAG contrast ratio do texto principal: <N.N:1> (meta: ≥4.5:1)
- Tempo de cold start: <NNs> (meta: <3s)
- ...
```

### 3.1 CAT-V — Visual (6 itens)

#### V-1: Tokens canônicos deep-agent era enforced

- **Pass criterion:** Toda cor usada na fork UI vem de `T-color-scr-*` (doc 30 §3.1). Sem hex hard-coded em CSS/style.
- **Como verificar:** grep `#` em `src/styles/` ou equivalente. Se aparecer hex literal sem token, FAIL.
- **Severidade:** Alta (rompe consistência cross-fork)

#### V-2: Status matrix unificada aplicada

- **Pass criterion:** Estados visuais da fork mapeiam para doc 33 §3.1 (6 estados × 4 regimes). Sem estados divergentes ("in_progress" paralelo a "active").
- **Como verificar:** Listar todos os estados renderizados; comparar com tabela doc 33.
- **Severidade:** Alta (quebra H4 consistência)

#### V-3: UEID visual com glyph + slug

- **Pass criterion:** Toda UEID renderizada mostra badge de tipo (� para `tsk:`, ◆ para `proj:`, etc. — doc 31 §3.2) + slug human-readable.
- **Como verificar:** Visualizar 10 UEIDs aleatórias na UI; user identifica domínio sem decodificar hex.
- **Severidade:** Média (H2 match mundo real)

#### V-4: SCR-NNN naming convention

- **Pass criterion:** Toda screen da fork tem ID `SCR-NNN-<kebab>` (doc 32 §3). Cross-link para journey doc correspondente.
- **Como verificar:** `ls src/screens/` ou equivalente; nomes seguem convenção.
- **Severidade:** Média (H4)

#### V-5: Banner PAV-era removido (migrado para deep-agent)

- **Pass criterion:** Nenhum elemento da fork exibe "PAV-OS" ou "TIME-TASKER" como marca visível (cross-ref doc 34).
- **Como verificar:** grep `PAV-OS\|TIME-TASKER` em `src/`. Se aparecer, FAIL.
- **Severidade:** Baixa (polimento pós-pivot)

#### V-6: Whitespace generoso (não denso)

- **Pass criterion:** Padding entre componentes ≥8px (desktop) ou ≥4px (mobile). Sem cards "colados".
- **Como verificar:** Inspeção visual; comparar com screenshot de referência em doc 30.
- **Severidade:** Baixa

### 3.2 CAT-I — Interaction (5 itens)

#### I-1: Teclado funciona sem mouse

- **Pass criterion:** Toda ação primária acessível via teclado (Tab/Enter/atalho). Sem dependência de click para criar/deletar task.
- **Como verificar:** Usar a fork **sem mouse** (trackpad off). Se mouse for necessário para ação crítica, FAIL.
- **Severidade:** Alta (H7)

#### I-2: Emergency exit (q/Ctrl+C/Cancel) funcional

- **Pass criterion:** Em qualquer flow multi-step, Ctrl+C ou botão "cancel" aborta sem persistir partial state. Mensagem "Operação cancelada" aparece.
- **Como verificar:** Iniciar criação de task; cancelar no meio; verificar que nada foi gravado.
- **Severidade:** Alta (H3)

#### I-3: Comando direto disponível (skip menu)

- **Pass criterion:** Toda ação acessível via CLI/command direto (não só via menu). Ex.: `taskdog task create <args>` em vez de só `Menu > Create`.
- **Como verificar:** Tentar reproduzir cada ação via comando direto.
- **Severidade:** Média (H7)

#### I-4: Atalhos de teclado documentados

- **Pass criterion:** Tela "Help" ou `--help` lista atalhos (ex.: `n` para novo, `d` para done, `b` para back).
- **Como verificar:** Abrir help; cross-ref com doc 32.
- **Severidade:** Baixa

#### I-5: Defaults razoáveis em todos os inputs

- **Pass criterion:** Todo prompt tem `default=` razoável (não 0, não ""). User pode aceitar com Enter.
- **Como verificar:** Rodar flow com 5 Enters consecutivos; completa sem pedir valores absurdos.
- **Severidade:** Alta (H5 prevenção)

### 3.3 CAT-D — Data (5 itens)

#### D-1: Estado vazio tratado (não crash)

- **Pass criterion:** Com state vazio (zero tasks, zero projects), fork renderiza placeholders ("Comece criando sua primeira task" + CTA) em vez de crash ou tela em branco.
- **Como verificar:** `rm -rf data/` (ou equivalent); abrir fork; deve mostrar onboarding.
- **Severidade:** Alta (UX-013)

#### D-2: Dados corrompidos graceful degradation

- **Pass criterion:** JSON/SQLite corrompido NÃO crasha fork. Mostra "Dados corrompidos detectados — execute `fork repair`" e continua.
- **Como verificar:** Injetar byte inválido em arquivo de dados; abrir fork.
- **Severidade:** Média (UX-020)

#### D-3: Validação Pydantic UEID enforced

- **Pass criterion:** UEID mal-formado rejeitado no boundary (Pattern #10 regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`). Mensagem PT-BR (UX-012).
- **Como verificar:** Submeter UEID `tsk:invalid` (sem uuid/hash); fork rejeita com msg "UEID deve ter formato `tipo:slug:uuid:hash`".
- **Severidade:** Média

#### D-4: Idempotência UPSERT on UEID

- **Pass criterion:** Submeter mesma UEID 2× não duplica; segunda chamada atualiza (Pattern #14).
- **Como verificar:** Criar task com UEID `tsk:test:abc:def`; submeter novamente; verificar 1 task apenas.
- **Severidade:** Média

#### D-5: Frozen Pydantic (imutabilidade)

- **Pass criterion:** Entities Pydantic são `frozen=True, extra="forbid"` (Pattern #11). Tentativa de mutação levanta erro claro.
- **Como verificar:** Em debug console, tentar `task.title = "novo"`; deve levantar `ValidationError` ou `FrozenInstanceError`.
- **Severidade:** Alta (invariante load-bearing)

### 3.4 CAT-A — Accessibility (4 itens)

#### A-1: WCAG 2.1 AA contrast ratio (≥4.5:1 texto normal)

- **Pass criterion:** Texto principal vs fundo tem contrast ratio ≥4.5:1. Texto grande (≥18pt) tem ≥3:1.
- **Como verificar:** Usar ferramenta (axe, Lighthouse) ou cálculo manual. Doc 30 §3.1 fornece valores canônicos.
- **Severidade:** Média

#### A-2: Funciona sem cor (daltonismo)

- **Pass criterion:** Glyphs transmitem informação independente de cor (◆▲✗▣▢ — doc 30 §3.4). User com deuteranopia distingue estados sem cor.
- **Como verificar:** Rodar com `NO_COLOR=1` ou grayscale filter. Se info só está em cor, FAIL.
- **Severidade:** Média (UX-002)

#### A-3: Encoding UTF-8 sem BOM/CRLF

- **Pass criterion:** Output UTF-8 limpo. Sem `?` ou `[]` no lugar de emoji. Source files em LF (não CRLF).
- **Como verificar:** `file *` em `src/`; se algum arquivo tem "CRLF", converter.
- **Severidade:** Baixa

#### A-4: Funciona em terminal 80 colunas

- **Pass criterion:** Layout adaptativo: 2x2 quando ≥100col, 1-col quando <100col (cross-ref UX-003).
- **Como verificar:** `stty cols 80`; abrir fork; layout não quebra.
- **Severidade:** Baixa

### 3.5 CAT-R — Recoverability (5 itens)

#### R-1: Undo via append-only queue

- **Pass criterion:** Delete task é reversível via replay da fila (`data/review_queue/` — Pattern #12). User pode "desfazer" últimas N ações.
- **Como verificar:** Criar task; deletar; rodar `fork undo`; task reaparece.
- **Severidade:** Alta (UX-006)

#### R-2: Confirmação antes de ação destrutiva

- **Pass criterion:** Delete bulk, clear data, seed → todos pedem confirmação "Tem certeza? (y/n)" com default=N.
- **Como verificar:** Rodar `fork data clear`; deve pedir confirmação.
- **Severidade:** Média (UX-014)

#### R-3: Retry com exponential backoff

- **Pass criterion:** Operações de I/O têm `@with_retry(3, backoff='exponential')` decorator (Pattern #17). Falha transitória não derruba flow.
- **Como verificar:** Simular network blip; fork retenta 3× com backoff 1s/2s/4s.
- **Severidade:** Média

#### R-4: Circuit breaker para dependências externas

- **Pass criterion:** Chamadas a MCP gateway, vault, OU forks externas têm `@with_circuit_breaker(failure_threshold=5)`. Após 5 falhas consecutivas, abre circuit (return cached/error).
- **Como verificar:** Derrubar gateway; 5 calls falham; 6ª retorna cached sem call.
- **Severidade:** Alta (H9 + reliability)

#### R-5: Mensagens de erro com hint actionable

- **Pass criterion:** Todo erro tem mensagem PT-BR + hint concreto (não "Tente novamente"). Ex.: "Tente: `fork task create --help` para ver flags".
- **Como verificar:** Forçar erro; ler hint; se genérico, FAIL.
- **Severidade:** Baixa (UX-012 residual)

### 3.6 CAT-S — Sync (5 itens)

#### S-1: Cross-fork consistency via mesh

- **Pass criterion:** Task criada em fork A aparece em fork B após sync (≤5s). UEID é join key cross-fork.
- **Como verificar:** Criar task em tuiboard; abrir taskdog; task aparece.
- **Severidade:** Alta (mesh contract)

#### S-2: Append-only queue não perde entries

- **Pass criterion:** Crash mid-write não corrompe fila. Atomic rename (Pattern #12 §3.2).
- **Como verificar:** Kill -9 fork mid-write; reiniciar; fila intacta.
- **Severidade:** Média

#### S-3: Idempotency key respeitado (upstream_id)

- **Pass criterion:** Mesmo `upstream_id` (Pattern #14) reproduzível sem side effect.
- **Como verificar:** Replay de evento; verifica que state não muda após 2ª execução.
- **Severidade:** Média

#### S-4: Status-enum mapping cross-fork (doc 23)

- **Pass criterion:** taskdog 4-value enum ↔ solverforge 5-value ↔ tuiboard boolean done, todos mapeiam para doc 33 §3.1 unified matrix.
- **Como verificar:** Criar task "active" em taskdog; ver em solverforge como "scheduled"; ver em tuiboard como coluna "Doing".
- **Severidade:** Alta (H4 + cross-fork)

#### S-5: Latência de sync ≤ SLA

- **Pass criterion:** p95 sync latency ≤2s entre forks locais. p99 ≤5s.
- **Como verificar:** `time` entre criar em fork A e ver em fork B em 100 trials.
- **Severidade:** Média (SLA)

---

## §4 — Cross-references

### 4.1 Dentro deste docset

| Doc | Relação |
|:----|:--------|
| `docs/design-system/00-INDEX.md` | Índice navegável |
| `docs/design-system/50-nielsen-heuristics-coverage.md` | H1-H10 ↔ checklist items |
| `docs/design-system/52-known-risks-mitigations.md` | R1-R12 ↔ checklist items Alta |
| `docs/design-system/53-adr-007-data-first-gate.md` | Gate 5+ logs antes de qualquer fork-pronta nova |
| `docs/design-system/10-pattern-ueid-tri-key.md` | Pattern #10 (UEID) — load-bearing para D-3 |
| `docs/design-system/11-pattern-frozen-pydantic-strict.md` | Pattern #11 — frozen para D-5 |
| `docs/design-system/12-pattern-append-only-queue.md` | Pattern #12 — reversible para R-1 |
| `docs/design-system/13-pattern-fork-adapter-protocol.md` | Pattern #13 — cancel/early-return para I-2 |
| `docs/design-system/14-pattern-idempotency-upstream-id.md` | Pattern #14 — UPSERT para D-4, S-3 |
| `docs/design-system/15-pattern-hysteresis-fsm.md` | Pattern #15 — override + log para R-3 |
| `docs/design-system/17-pattern-reliability-decorators.md` | Pattern #17 — retry + circuit breaker para R-3, R-4 |
| `docs/design-system/23-fork-status-enum-mapping.md` | Cross-fork status para S-4 |
| `docs/design-system/30-tokens-deep-agent-era.md` | Tokens para V-1 |
| `docs/design-system/31-ueid-visual-representation.md` | UEID visual para V-3 |
| `docs/design-system/32-component-naming-conventions.md` | SCR-NNN para V-4 |
| `docs/design-system/33-status-matrix-unified.md` | Status matrix para V-2 |
| `docs/design-system/34-superseded-pav-era-tokens.md` | PAV-era banner para V-5 |
| `docs/design-system/40-index-user-journeys.md` | Index de journeys |
| `docs/design-system/41-journey-morning-startup.md` | Journey 1 |
| `docs/design-system/42-journey-task-create.md` | Journey 2 |
| `docs/design-system/43-journey-policy-decision.md` | Journey 3 |
| `docs/design-system/44-journey-weekly-review.md` | Journey 4 |
| `docs/design-system/45-journey-dataset-switch.md` | Journey 5 |

### 4.2 Catálogo PAV-era (origem)

- `src/operational/docs/ux/08-validacao/02-checklist-usabilidade.md` (284 linhas; 8 categorias C/N/A/P/D/I/M/K; 30+ itens; severidades Alta/Média/Baixa) — **origem deste checklist**, adaptada para era deep-agent.

### 4.3 Memory references

- `[[interfaces-architecture-2026-08-27]]` — forks = user views (este checklist audita forks, não CLI/TUI)
- `[[master-branch-carro-chefe-2026-08-28]]` — Deep Agent valida antes de propagar

---

## §5 — Fontes

### 5.1 Fonte primária

- `src/operational/docs/ux/08-validacao/02-checklist-usabilidade.md` (template original PAV-era; 30+ itens em 8 categorias)

### 5.2 Fontes secundárias

- `src/operational/docs/ux/08-validacao/01-heuristicas-nielsen.md` (10 heurísticas que motivam cada item)
- `src/operational/docs/ux/08-validacao/03-riscos-conhecidos.md` (UX-001 a UX-020; cada item deste checklist referencia um UX-NNN)
- `docs/design-system/50-nielsen-heuristics-coverage.md` (mapeamento Nielsen ↔ checklist)
- `docs/design-system/52-known-risks-mitigations.md` (R1-R12 — riscos que o checklist mitiga)
- `docs/design-system/53-adr-007-data-first-gate.md` (gate antes de fork-pronta nova)
- W3C. (2018). *Web Content Accessibility Guidelines (WCAG) 2.1.* https://www.w3.org/TR/WCAG21/ (referência para A-1)

### 5.3 Notas de leitura

- Quem audita começa por §3.0 (template copy-paste) → §2.2 (severidade) → §3.1-3.6 (itens).
- Itens Alta (V-1, V-2, I-1, I-2, I-5, D-1, D-5, R-1, R-4, S-1, S-4) **bloqueiam merge**.
- Itens Média podem mergir com issue aberto (linkar issue na linha do checklist).
- Items Baixa são backlog (não bloqueiam).
- Checklist runs arquivados em `docs/design-system/51-checklist-runs/` para audit trail.
