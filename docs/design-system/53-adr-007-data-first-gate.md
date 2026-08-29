# 53 — ADR-007 Data-First Gate (5+ SONHO logs validation)

> **⚠️ STATUS CLARIFICATION (2026-08-29):** This doc was built around the "5+ SONHO logs gate" framing, which is a **propagated misconception** of ADR-007. ADR-007's "5+ manual logs per workflow" rule is **observation depth** (observe before designing), NOT a release gate.
>
> The actual gate for IKIGAi agent runs is **system readiness** (backend + data + agent layers functional), not a counter of SONHO logs. The SONHO counter (1/5 as of 2026-08-28) is a measurement of user discipline, NOT a release gate.
>
> The deferral rule still applies — IKIGAi agent runs should not happen until system layers are ready — but for the reason "system not ready," not "5 logs not reached." Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`.
>
> **This doc is preserved (NOT deleted) for historical/audit value.** The §1-§6 content remains accurate as a description of WHAT the gate-mechanism was. The WHY in §1 is now wrong; refer to the STATUS blockquote above for the correct rationale.

> **Categoria:** VALIDATION (Layer 7 — Validation & heuristics, posição #53)
> **Anchor canônico:** `code-docs/adr/ADR-007-data-first-methodology.md` (ADR-007, Accepted 2026-07-02)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (UEID, fork, fork adapter, regime, KPI, SCR, FLOW, gate, ADR, SONHO, IKIGAi, agent, data-first, math-first, validation, methodology)
> **Status:** Gate institucional (counter 1/5; bloqueia IKIGAi agent runs até 5+ SONHO logs)

---

## §1 — Resumo

A **ADR-007 (Data-First Methodology)**, aceita em **2026-07-02**, estabelece que o **IKIGAi agent NÃO pode rodar em produção** até que **5+ SONHO logs manuais** sejam preenchidos pelo operador (humano) em PROPOSTA: `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/YYYY-MM-DD-sonho.md` (path template per ADR-007 — daily SONHO report). Esta é uma decisão institucional — **não negociável** — que reverte 30+ meses de "design-from-math-first" (PAV era) para "data-first" (deep-agent era). O rationale canônico está em `code-docs/adr/ADR-007-data-first-methodology.md:1-137`.

**Estado atual do gate (2026-08-28):** **counter 1/5**. Apenas 1 SONHO log manual foi commitado (2026-07-09 — ver `[[ikigai-persona-vault-bootstrap]]`). Faltam **4+ SONHO logs** antes que o gate abra. Sem o gate aberto, o **Deep Agent** (carro-chefe canônico — cross-ref [[master-branch-carro-chefe-2026-08-28]]) opera em **modo limitado** (somente MCP primitives; sem decision logic de IKIGAi).

**Princípio:** o gate existe porque a história do PAV kernel demonstrou que **design sem evidência empírica produz over-engineering** — 2.518 tests em fórmulas que o usuário raramente invoca. A ADR-007 corrige a ordem: **5+ observações manuais ANTES de qualquer código novo**. O gate é o mecanismo institucional que torna esta correção vinculante.

**Quem valida:** o operador (você). Não há agente automatizado verificando; é disciplina pessoal + audit trail via vault markdown (commit history).

---

## §2 — Inventário

### 2.1 Os 5 requisitos do log SONHO

Cada SONHO log deve:

| # | Requisito | Template path | Validação |
|:-:|:----------|:--------------|:----------|
| **1** | Path canônico | PROPOSTA: `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/YYYY-MM-DD-sonho.md` (path template per ADR-007 — daily SONHO report) | Naming convention: `YYYY-MM-DD-sonho.md` (data + `-sonho.md` literal) |
| **2** | Conteúdo mínimo | 7 seções (OBJ-01 a OBJ-07 do template SONHO) | Cada seção tem ≥1 parágrafo ou bullet point |
| **3** | Commit manual | Git commit com mensagem `manual: SONHO YYYY-MM-DD` | `git log` mostra commit humano (não agent-generated) |
| **4** | Audit trail | Sem edição retroativa após commit | `git log --follow` mostra criação + ausência de rebase |
| **5** | Distribuição temporal | ≥7 dias entre logs consecutivos | Diff `date(commit_N) - date(commit_N-1) ≥ 7d` |

### 2.2 Template SONHO (origem verbatim)

**Origem:** `vibe-ops/planning/_templates_periodos_v2/01-sonho.md` (template PAV-era, preservado append-only — ver ADR-007 §Decision.1).

Estrutura canônica (7 seções obrigatórias):

| # | Seção | Conteúdo esperado |
|:-:|:------|:-------------------|
| **OBJ-01** | Sonho do dia | 1-3 frases declarativas; aspiracional, não tactico |
| **OBJ-02** | Métricas de sono | bedtime, wake_time, quality (1-10), dream_recall |
| **OBJ-03** | Pomodoros completados | contagem manhã/tarde/noite + regime observado |
| **OBJ-04** | Regimes observados | qual FSM state (PUSH/MAINTAIN/REDUCE/RECOVER) + justificação |
| **OBJ-05** | Reflexões | 3-5 bullets; o que funcionou, o que falhou, o que ajustar |
| **OBJ-06** | Tasks abertas | quantas tasks ativas, quantas done, quantas blocked |
| **OBJ-07** | Próximo dia | intenção + 1-3 metas específicas |

**Cross-ref:** `code-docs/adr/ADR-007-data-first-methodology.md:39` referencia os 9 templates em `_templates_periodos_v2/`; SONHO é o primeiro (`01-sonho.md`).

### 2.3 Counter status (atual vs meta)

| Métrica | Atual | Meta | Gap |
|:--------|:------|:-----|:----|
| SONHO logs commitados | 1 (2026-07-09) | 5 | -4 |
| Janela desde primeiro log | 50 dias (2026-07-09 → 2026-08-28) | ≥35 dias (5×7d) | OK |
| Distribuição temporal | 1/5 logs em 50 dias | 5/5 em ≥35 dias | Falta cadência |
| Audit trail limpo | Sim (sem retro-edits) | Sim | OK |
| Gate aberto? | NÃO (1/5) | SIM (≥5/5) | -4 |

**Cadência esperada:** ~7-10 dias entre logs. Para abrir o gate até final de 2026-Q3 (~2026-09-30), faltam ~4 logs em ~33 dias → cadência de ~8 dias/log. Realista.

---

## §3 — Conteúdo principal

### 3.1 Gate state table (current)

| Componente | Estado | Notes |
|:-----------|:-------|:------|
| **ADR-007 status** | Accepted (2026-07-02) | Não revogado; não modificado |
| **Counter** | 1/5 | 1 SONHO log commitado (2026-07-09) |
| **Gate aberto?** | NÃO | Deep Agent roda em modo limitado |
| **Próximo threshold** | 5 SONHO logs | Data estimada abertura: ~2026-10-15 (cadência 8d/log) |
| **Re-evaluation checkpoints** | 6 meses (2026-12-31) + 3 meses (2026-10-31) | per ADR-007 §Roll-back |
| **Owner** | operador (você) | Nenhum agent automatizado |
| **Audit trail** | git log + vault markdown | Cross-ref `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/` |

### 3.2 Checklist para destravar o gate

Para mover de **1/5 → 5/5**, são necessárias **4 SONHO logs adicionais**. Cada log deve:

- [ ] **Path correto:** PROPOSTA: `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/<YYYY-MM-DD>-sonho.md` (path template per ADR-007) (não `~/notes/...` ou `vault/drafts/...` — path é institucional).
- [ ] **Data YYYY-MM-DD** reflete o dia do sonho, não o dia do commit.
- [ ] **7 seções (OBJ-01 a OBJ-07)** todas presentes e com ≥1 linha de conteúdo.
- [ ] **Linguagem PT-BR** (prose); termos técnicos em EN (UEID, regime, FSM).
- [ ] **Sem retro-edits** após primeiro commit (verificável via `git log --follow <file>`).
- [ ] **Mensagem de commit manual** (não `chore: automated log` — deve soar humano).
- [ ] **≥7 dias desde último SONHO** (cadência).
- [ ] **Reflete uso real**, não aspiração. Se o dia foi ruim, OBJ-05 lista o que falhou honestamente.

**Workflow recomendado:**

```bash
# 1. Criar arquivo do SONHO do dia
touch "vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/$(date +%Y-%m-%d)-sonho.md"

# 2. Preencher 7 seções (OBJ-01 a OBJ-07)

# 3. Revisar 1× antes de commit (audit pessoal)

# 4. Commit manual
cd vault
git add "ikigai/closing-2026/01-q3-2026/04-relatórios-diários/$(date +%Y-%m-%d)-sonho.md"
git commit -m "manual: SONHO $(date +%Y-%m-%d) — <1-line summary>"

# 5. Push (se houver remote)

# 6. Atualizar counter em [[ikigai-persona-vault-bootstrap]] memory
```

### 3.3 Consequências de bypass (NÃO RECOMENDADO)

Bypassar o gate (rodar IKIGAi agent antes de 5/5) tem **4 consequências documentadas**:

1. **Viola decisão institucional aceita.** ADR-007 foi explicitamente aceita para corrigir ordem math-first → data-first. Bypass reverte o aprendizado de 2026-Q2 sem nova evidência.

2. **Reproduz over-engineering.** Sem 5+ observações, qualquer decisão do agent será **especulativa** — exatamente o problema que a ADR-007 visa evitar. Histórico PAV: 2.518 tests em fórmulas raramente invocadas.

3. **Compromete audit trail.** Vault markdown é a "source of truth" da metodologia. Agent rodando sem logs = estado paralelo inconsistente com o vault.

4. **Dificulta revisão posterior.** Quando alguém auditar "por que esta decisão foi tomada?", a resposta deve ser rastreável ao vault + SONHO logs. Sem logs, decisão é orfanã.

**Mitigação aceita (escape hatch):** se bypass é absolutamente necessário (ex.: demo, P0 fire), documentar **explicitamente** no commit message + ADR amendment proposal:

```bash
git commit -m "agent run: BYPASS ADR-007 (counter 1/5) — <justificativa>
- Razão: <fire / demo / one-off>
- Duração: <1h>
- Output: <summary>
- Proposal ADR-008: <link ou 'none'>"
```

ADR-008 (proposed) documentaria o bypass; aceitação/rejeição é decisão do operador (você).

### 3.4 Roll-back criteria (per ADR-007)

A própria ADR-007 tem **2 checkpoints de roll-back**:

| Checkpoint | Data | Critério |
|:-----------|:-----|:---------|
| **3 meses** | 2026-10-31 | Se "too much manual work" é fricção recorrente → revisitar 5+ threshold (talvez baixar para 3+) |
| **6 meses** | 2026-12-31 | Se <10 SONHO logs totais (incluindo outros templates) → premise falhou; reconsiderar methodology |

**Status em 2026-08-28:** checkpoint 3 meses em **64 dias**; checkpoint 6 meses em **125 dias**. Não urgente.

### 3.5 Por que 5+ logs (não 3+ ou 10+)

Justificativa vem de `ADR-007-data-first-methodology.md:99-104`:
- **3 logs = anedotal** — pode ser coincidência
- **5 logs = padrão inicial** — começo de signal estatístico
- **10 logs = over-evidence** — overhead sem ganho marginal

5 é o sweet spot: **2 meses a 8d/log** (~56 dias) para signal confiável sem overhead excessivo.

---

## §4 — Cross-references

### 4.1 Dentro deste docset

| Doc | Relação |
|:----|:--------|
| `docs/design-system/00-INDEX.md` | Índice navegável |
| `docs/design-system/50-nielsen-heuristics-coverage.md` | H1-H10 (gate não audita heurística; audita processo) |
| `docs/design-system/51-usability-checklist.md` | Checklist fork (gate audita antes de fork-pronta nova) |
| `docs/design-system/52-known-risks-mitigations.md` | R10 ↔ este doc (gate é R10) |

### 4.2 ADRs e specs

- `code-docs/adr/ADR-007-data-first-methodology.md` (anchor canônico, 137 linhas)
- `code-docs/adr/ADR-001..ADR-006` (autoritativos; não invalidados pela ADR-007 — ADR-007 §Related Decisions)
- `vibe-ops/planning/_templates_periodos_v2/01-sonho.md` (template SONHO, preservado append-only)

### 4.3 Vault

- `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/` (diretório institucional; target para SONHO logs)
- `vault/ikigai/meta/` (MOCs, indexes, dashboards)

### 4.4 Memory references

- `[[data-first-methodology]]` — memória canônica (sempre atualizar quando status muda)
- `[[ikigai-persona-vault-bootstrap]]` — SONHO 1/5 (2026-07-09)
- `[[master-branch-carro-chefe-2026-08-28]]` — Deep Agent mediador (gate bloqueia em modo limitado)
- `[[algorithm-decisions-defer-2026-08-28]]` — ADR-007 reforça "defer until empirical" (M01/N01/A02/A06)
- `[[prioritize-backend-over-algorithm-refinement]]` — gate alinha com priorização backend

### 4.5 Pitfalls noted

- **Não contar arquivos `*.md` em `vault/drafts/`** como SONHO logs (drafts ≠ relatório fechado).
- **Não usar `git commit --amend`** para "ajeitar" SONHO logs após commit (viola audit trail).
- **Não criar SONHO logs retroativos** para "preencher gap" — falsifica signal.
- **Não confundir** com outros templates (`02-trimestral.md`, `03-onda.md`, etc.) — gate conta apenas SONHO (`01-sonho.md`).

---

## §5 — Fontes

### 5.1 Fonte primária

- `code-docs/adr/ADR-007-data-first-methodology.md` (137 linhas; Status, Context, Decision, Consequences, Alternatives, Implementation Rules, Roll-back criteria, Related Decisions, Notes)

### 5.2 Fontes secundárias

- `vibe-ops/planning/_templates_periodos_v2/01-sonho.md` (template SONHO — 7 seções OBJ-01..OBJ-07)
- `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/` (target path para SONHO logs)
- `[[data-first-methodology]]` (memória canônica; status counter)
- `[[ikigai-persona-vault-bootstrap]]` (SONHO 1/5; 2026-07-09; GAP-01 closed)
- `docs/design-system/52-known-risks-mitigations.md` (R10 — gate institucional como blocker Phase 3)

### 5.3 Cross-era references

- **PAV era (pre-2026-07-02):** math-first design (2.518 tests em fórmulas raramente invocadas) — motivador da ADR-007.
- **Deep-agent era (2026-07-02 → presente):** data-first methodology; IKIGAi agent em modo limitado até gate abrir.
- **Post-gate era (estimativa 2026-Q4+):** Deep Agent + IKIGAi decision logic habilitados; spec-only first, code after 5+ observações adicionais por workflow (per ADR-007 §Decision.2).

### 5.4 Notas de leitura

- Quem entra novo no projeto deve ler **§3.1 (gate state)** + **§3.3 (consequences of bypass)** antes de qualquer code suggestion.
- Quem quer abrir o gate foca em **§3.2 (checklist)** — 8 requisitos por SONHO log.
- Quem audita o gate periodicamente: §2.3 (counter status) + §3.4 (roll-back criteria).
- Gate é **institucional** (não técnico). Não há bypass automático; é decisão humana.
