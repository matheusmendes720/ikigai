# 32 — Component Naming Conventions (Single Source of Truth)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** TOKENS (Layer 5 — Tokens & components, posição #32 — NEW canonical, gap #7)
> **Anchor canônico:** `src/operational/docs/ux/04-fluxos/FLOW-001...FLOW-005` + `src/operational/docs/ux/02-componentes/01-12` + ADR-003 (naming pattern)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (SCR, FLOW, CMP, KPI, T, prefix, suffix, kebab-case, slug, flow, journey, snapshot, component slot, token, fork, adapter)
> **Status:** Gap-fill de critical kind (Phase 3 v1+ unblocking — single source of truth para naming)

---

## §1 — Resumo

Este documento preenche o **gap #7** do design system ao definir a **convenção canônica de naming** para arquivos `.md` no docset `docs/design-system/` e em `src/operational/docs/ux/`. A convenção atual é **inconsistente**: alguns arquivos seguem `NN-categoria-nome-kebab.md` (Pattern #10, #11, #12), outros seguem `FLOW-001-iniciar-manha.md` (sem NN prefix), e componentes individuais usam `01-paleta-cores.md` (sem prefix type). Sem convenção unificada, **grep cross-file fica ambíguo** (`grep "flow"` retorna 23 hits sem distinção entre SCR, FLOW, ou arquivo histórico) e **autocomplete em IDE falha** (`FLOW-001-iniciar-manha` vs `flow-001-iniciar-manha` são treated diferentes). A solução proposta é **5 prefix types canônicos** + **2 state suffix patterns**: **`SCR-NNN-...`** (screen = tela renderizada, ex.: `SCR-001-dashboard-dia`), **`FLOW-NNN-...`** (user flow = jornada, ex.: `FLOW-001-iniciar-manha`), **`CMP-NNN-...`** (component = slot visual reutilizável, ex.: `CMP-001-kpi-card`), **`KPI-NNN-...`** (metric = métrica observável, ex.: `KPI-001-qhe-mean`), e **`T-...`** (token = valor atômico em design system, ex.: `T-color-scr-push`). Os 2 state suffix são **`-snapshot.md`** (vault snapshot de um SCR/FLOW em momento específico, ex.: `SCR-001-dashboard-dia-2026-08-28-snapshot.md`) e **`-flows.md`** (agrupamento de FLOWs em jornada, ex.: `SCR-001-onboarding-flows.md`). Toda migration é **append-only**: arquivos antigos recebem trailer `SUPERSEDED → SCR-NNN-novo-nome` mas não são deletados (preserva invariante append-only do design system).

### 1.1 Por que 5 prefix types (não 1 genérico)

Naming único (ex.: `dashboard.md`, `kpi-card.md`, `flow-iniciar-manha.md`) é mais simples mas **perde signal semântico**. Pattern: prefix type torna **busca por tipo trivial**:
- `ls docs/design-system/SCR-*` → todas as screens
- `ls docs/design-system/FLOW-*` → todas as user flows
- `ls docs/design-system/CMP-*` → todos os componentes
- `ls docs/design-system/KPI-*` → todas as métricas
- `ls docs/design-system/T-*` (em arquivos de tokens, não em filenames)

Filenames mantêm **NNN zero-padded 3-digit** para sorting cronológico estável (`FLOW-001`, `FLOW-002`, ..., `FLOW-010`, ..., `FLOW-100`). 3 digits comporta até 999 docs por categoria — espaço mais que suficiente para 5 forks-prontas × ~20 anos de evolução.

### 1.2 Por que `-snapshot` e `-flows` são state suffixes

**`-snapshot.md`** captura estado de uma SCR ou FLOW em timestamp específico. Exemplo: `SCR-001-dashboard-dia-2026-08-28-snapshot.md` é o dashboard do dia 2026-08-28 (renderizado, exported para auditoria). Snapshots são **imutáveis** (append-only); novo snapshot não sobrescreve antigo. Use case: compliance audit, debugging "como estava o dashboard naquele dia?".

**`-flows.md`** agrupa múltiplos FLOWs que compõem uma jornada maior. Exemplo: `SCR-001-onboarding-flows.md` contém FLOW-001 (signup), FLOW-002 (verify email), FLOW-003 (first task). Flows são **read-only references** (FLOWs individuais têm seus próprios arquivos). Use case: navegação "ver todos os flows da tela X".

### 1.3 Cross-link com tokens

`T-` prefix é **reservado para tokens** (cross-ref doc 30). Não usar `T-` para SCR/FLOW/CMP/KPI. Tokens vivem em **tabelas dentro de arquivos de padrão** (não têm filename próprio); `T-color-scr-push` é ID dentro de doc 30 §3.1.

---

## §2 — Inventário

### 2.1 Os 5 prefix types canônicos

| Prefix | Categoria | Propósito | Quantidade atual |
|:-------|:----------|:----------|:------------------|
| `SCR-NNN-...` | Screen | Tela renderizada (UI completa, ex.: dashboard, settings) | 0 (a migrar de `01-...`, `02-...`) |
| `FLOW-NNN-...` | User flow | Jornada do usuário (sequência de ações, ex.: login, criar task) | 5 (`FLOW-001...FLOW-005` em `ux/04-fluxos/`) |
| `CMP-NNN-...` | Component | Slot visual reutilizável (ex.: KPI card, Timeline, Error panel) | 12 (`01-paleta-cores` até `12-glifos`) |
| `KPI-NNN-...` | Metric | Métrica observável (ex.: QHE mean, execution rate, burndown) | 0 (a criar) |
| `T-...` | Token | Valor atômico de design system (dentro de tabelas, não filenames) | 38 (em doc 30) |

### 2.2 Os 2 state suffix patterns

| Suffix | Quando usar | Exemplo | Invariante |
|:-------|:------------|:--------|:------------|
| `-snapshot.md` | Captura de SCR/FLOW em timestamp específico | `SCR-001-dashboard-dia-2026-08-28-snapshot.md` | Imutável; novo snapshot não sobrescreve |
| `-flows.md` | Agrupamento de FLOWs em jornada | `SCR-001-onboarding-flows.md` | Read-only reference; FLOWs têm arquivos próprios |

### 2.3 Existing UX docs que conformam (parcialmente)

| Path atual | Rename proposto | Status |
|:-----------|:----------------|:-------|
| `src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md` | ✅ Já conforme | Manter |
| PROPOSTA: `src/operational/docs/ux/04-fluxos/FLOW-002-criar-task.md` (path place-holder — gap-fill target) | ✅ Já conforme | Manter |
| PROPOSTA: `src/operational/docs/ux/04-fluxos/FLOW-003-marcar-como-done.md` (path place-holder) | ✅ Já conforme | Manter |
| PROPOSTA: `src/operational/docs/ux/04-fluxos/FLOW-004-revisar-qhe.md` (path place-holder) | ✅ Já conforme | Manter |
| PROPOSTA: `src/operational/docs/ux/04-fluxos/FLOW-005-bloco-deep-work.md` (path place-holder) | ✅ Já conforme | Manter |
| PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) | ⏳ Migrar para `CMP-001-paleta-cores.md` (gap-fill doc 30) | Adicionar trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/02-tipografia.md` (path place-holder) | ⏳ Migrar para `CMP-002-tipografia.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/03-spacing.md` (path place-holder) | ⏳ Migrar para `CMP-003-spacing.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder) | ⏳ Migrar para `CMP-004-glifos.md` (parcialmente sobrescrito por doc 31) | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/05-componentes-slots.md` (path place-holder) | ⏳ Migrar para `CMP-005-component-slots.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/06-kpi-card.md` (path place-holder; existing file is `src/operational/docs/ux/02-componentes/01-kpi-card.md`) (a verificar) | ⏳ Migrar para `CMP-006-kpi-card.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/07-section.md` (path place-holder; existing file is `02-section-panel.md`) | ⏳ Migrar para `CMP-007-section.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/08-error-panel.md` (path place-holder; existing file is `04-error-panel.md`) | ⏳ Migrar para `CMP-008-error-panel.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/09-timeline.md` (path place-holder; existing file is `11-timeline-h.md`) | ⏳ Migrar para `CMP-009-timeline.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/10-sparkline.md` (path place-holder; existing file is `08-sparkline.md`) | ⏳ Migrar para `CMP-010-sparkline.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/11-form-field.md` (path place-holder) | ⏳ Migrar para `CMP-011-form-field.md` | Trailer |
| PROPOSTA: `src/operational/docs/ux/02-componentes/12-button.md` (path place-holder; existing files are `01-kpi-card.md` through `12-next-step.md`, no `button.md`) | ⏳ Migrar para `CMP-012-button.md` | Trailer |
| `src/operational/docs/ux/01-inventario/02-matriz-estados.md` | ⏳ Migrar para `SCR-002-matriz-estados.md` (consolidação doc 33) | Trailer |
| `src/operational/docs/design-system/DESIGN-SYSTEM.md` | ⏳ Manter como está + trailer SUPERSEDED (cross-ref doc 34) | Trailer |

### 2.4 Existing SCR candidates (a promover)

| Path candidato | Rename proposto | Razão |
|:---------------|:----------------|:------|
| PROPOSTA: `src/operational/docs/ux/00-visao-geral/01-telas-principais.md` (path place-holder) | `SCR-001-telas-principais.md` | Lista de screens canônicas |
| PROPOSTA: `src/operational/docs/ux/00-visao-geral/02-componentes-globais.md` (path place-holder) | `CMP-013-componentes-globais.md` | Componente global = header, sidebar |
| PROPOSTA: `src/operational/docs/ux/01-inventario/01-telas-cadastradas.md` (path place-holder) | `SCR-002-telas-cadastradas.md` | Inventory de screens |
| PROPOSTA: `src/operational/docs/ux/01-inventario/03-fluxos-cadastrados.md` (path place-holder) | `SCR-003-fluxos-cadastrados.md` | Inventory de flows |
| PROPOSTA: `src/operational/docs/ux/03-layout/01-grid-principal.md` (path place-holder) | `SCR-004-grid-principal.md` | Layout principal |

---

## §3 — Conteúdo principal

### 3.1 Rules table per prefix

**SCR (Screen) — regras:**

| Rule | Description | Example |
|:-----|:------------|:--------|
| Format | `SCR-NNN-kebab-name.md` | `SCR-001-dashboard-dia.md` |
| NNN | 3-digit zero-padded (001-999) | `SCR-001`, `SCR-042`, `SCR-100` |
| Name | kebab-case, lowercase, semantic | `dashboard-dia` ✓; `dash` ✗ (abbrev) |
| Scope | Uma tela = um SCR. Não dividir telas em SCRs | `SCR-001` = dashboard inteiro, não `SCR-001a-header` |
| Content | Wireframe ASCII + componentes usados + FLOWs起点 | §1 descrição, §2 wireframe, §3 CMP list, §4 FLOWs |

**FLOW (User Flow) — regras:**

| Rule | Description | Example |
|:-----|:------------|:--------|
| Format | `FLOW-NNN-kebab-name.md` | `FLOW-001-iniciar-manha.md` |
| NNN | 3-digit zero-padded | `FLOW-001`, `FLOW-002` |
| Name | kebab-case, action-oriented (verbo + objeto) | `iniciar-manha` ✓; `manhã` ✗ (noun sem verbo) |
| Scope | Jornada linear (1 happy path). Edge cases em FLOW separado | `FLOW-001-criar-task-error.md` para error path |
| Content | Passos numerados + SCR involved + exit conditions | §1 trigger, §2 passos, §3 SCRs, §4 exit |

**CMP (Component) — regras:**

| Rule | Description | Example |
|:-----|:------------|:--------|
| Format | `CMP-NNN-kebab-name.md` | `CMP-001-paleta-cores.md` |
| NNN | 3-digit zero-padded | `CMP-001`, `CMP-006` |
| Name | kebab-case, lowercase, noun (componente = coisa) | `kpi-card` ✓; `kpi` ✗ (abbrev) |
| Scope | Um componente reutilizável = um CMP. Variações em CMP separado | `CMP-006-kpi-card.md` ≠ `CMP-006b-kpi-card-compact.md` |
| Content | Spec visual + tokens usados + estados + accessibility | §1 papel, §2 tokens, §3 estados, §4 a11y |

**KPI (Metric) — regras:**

| Rule | Description | Example |
|:-----|:------------|:--------|
| Format | `KPI-NNN-kebab-name.md` | `KPI-001-qhe-mean.md` |
| NNN | 3-digit zero-padded | `KPI-001`, `KPI-002` |
| Name | kebab-case, lowercase, metric formula | `qhe-mean` ✓; `qhe` ✗ (abbrev) |
| Scope | Uma métrica observável = um KPI. Composição em KPI pai | `KPI-001-qhe-mean.md`; composição `KPI-002-qhe-composite.md` |
| Content | Fórmula matemática + data source + intervalo + threshold | §1 fórmula, §2 source, §3 thresholds, §4 alerts |

**T (Token) — regras:**

| Rule | Description | Example |
|:-----|:------------|:--------|
| Format | `T-{category}-{role}` (dentro de tabelas em outros docs, não em filenames) | `T-color-scr-push`, `T-text-mono-md`, `T-space-md` |
| Category | `color`, `text`, `space`, `glyph`, `density`, `border`, `bg`, `fg` | `T-color-...` para cores |
| Role | kebab-case, semantic (state, regime, action) | `scr-push` (regime PUSH), `state-pending` (status PENDING) |
| Scope | Um valor atômico = um T. Variações (light/dark) são **mesmo T** com 2 hex | `T-color-scr-push` (light + dark variants) |
| Content | Hex + papel semântico + uso canônico (em tabelas de doc 30) | Doc 30 §3.1-3.5 tabelas |

### 3.2 State suffix rules

**`-snapshot.md`:**

| Rule | Description | Example |
|:-----|:------------|:--------|
| Format | `{SCR|FLOW}-NNN-name-YYYY-MM-DD-snapshot.md` | `SCR-001-dashboard-dia-2026-08-28-snapshot.md` |
| Timestamp | ISO date YYYY-MM-DD | `2026-08-28` ✓; `2026-8-28` ✗ |
| Imutável | Não sobrescrever snapshot existente. Novo snapshot = novo filename | `SCR-001-...-2026-08-29-snapshot.md` separado |
| Use case | Compliance audit, debugging "como estava?", regression baseline | "Dashboard do dia antes do bug X" |

**`-flows.md`:**

| Rule | Description | Example |
|:-----|:------------|:--------|
| Format | `SCR-NNN-name-flows.md` (sempre SCR-pai, não FLOW-pai) | `SCR-001-onboarding-flows.md` |
| Content | Read-only index de FLOWs que compõem a SCR | Lista de FLOW-NNN + link + descrição 1-linha |
| Atualização | Ao adicionar FLOW novo na SCR, atualizar `-flows.md` | Append-only: adicionar linha, nunca remover |

### 3.3 Examples completos

**SCR example:**

```
docs/design-system/SCR-001-dashboard-dia.md
├── §1 — Description: dashboard principal do dia, renderiza regime + tasks + KPIs
├── §2 — Wireframe ASCII: 
│       ┌────────────────────────────────────┐
│       │ [Policy Banner: PUSH/MAINTAIN/...] │
│       ├────────────────────────────────────┤
│       │ [KPI Cards: QHE Mean | Burndown | Execution Rate] │
│       ├────────────────────────────────────┤
│       │ [Timeline: hoje events]            │
│       └────────────────────────────────────┘
├── §3 — Components used: CMP-006 (KPI card), CMP-009 (Timeline), CMP-007 (Section)
├── §4 — Flows起点: FLOW-001 (iniciar-manha), FLOW-003 (marcar-como-done)
└── §5 — Fontes: doc 30, doc 31
```

**FLOW example:**

```
docs/design-system/FLOW-001-iniciar-manha.md
├── §1 — Trigger: usuário abre o app às 06:00
├── §2 — Passos:
│       1. Tap "iniciar dia" na SCR-001 dashboard
│       2. System registra regime do dia via Pattern #15 hysteresis FSM
│       3. Renderiza task list priorizada
│       4. Marca primeira task como ACTIVE (Pattern #23)
├── §3 — SCRs involved: SCR-001 (dashboard), SCR-005 (task-list)
├── §4 — Exit: usuário fecha app OU completa primeira task
```

**CMP example:**

```
docs/design-system/CMP-006-kpi-card.md
├── §1 — Papel: exibir métrica única com label + value + delta
├── §2 — Tokens usados: T-bg-surface, T-color-scr-push, T-text-mono-xxl
├── §3 — Estados: default, hover (T-bg-overlay 5%), loading (skeleton T-bg-surface)
├── §4 — Accessibility: aria-label obrigatório, contrast AAA para value (T-fg-primary)
```

**KPI example:**

```
docs/design-system/KPI-001-qhe-mean.md
├── §1 — Fórmula: mean(Q_HE_values, period=7d)
├── §2 — Data source: src/ikigai/core/scoring/qhe.py:compute_qhe_mean()
├── §3 — Thresholds: PUSH ≥ 0.85, MAINTAIN [0.65, 0.85), REDUCE [0.45, 0.65), RECOVER < 0.45
├── §4 — Alerts: < 0.45 → trigger SCR-PUSH-downgrade notification
```

**T example (in table):**

```markdown
| Token ID | Hex light | Hex dark | Papel semântico |
|:---------|:---------:|:--------:|:----------------|
| `T-color-scr-push` | `#10b981` | `#34d399` | Regime PUSH — alta intensidade permitida |
```

### 3.4 Migration map (non-compliant → compliant)

**Estratégia:** append-only. Arquivo antigo recebe trailer `> SUPERSEDED → {novo path}`. Não deletar.

| Arquivo atual | Trailer | Novo path |
|:--------------|:--------|:----------|
| PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) | `> SUPERSEDED → docs/design-system/CMP-001-paleta-cores.md` | `CMP-001-paleta-cores.md` |
| PROPOSTA: `src/operational/docs/ux/02-componentes/02-tipografia.md` (path place-holder) | `> SUPERSEDED → CMP-002-tipografia.md` | `CMP-002-tipografia.md` |
| PROPOSTA: `src/operational/docs/ux/02-componentes/03-spacing.md` (path place-holder) | `> SUPERSEDED → CMP-003-spacing.md` | `CMP-003-spacing.md` |
| PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder) | `> SUPERSEDED → CMP-004-glifos.md (parcialmente sobrescrito por doc 31)` | `CMP-004-glifos.md` |
| PROPOSTA: `src/operational/docs/ux/02-componentes/05-componentes-slots.md` (path place-holder) | `> SUPERSEDED → CMP-005-component-slots.md` | `CMP-005-component-slots.md` |
| PROPOSTA: `src/operational/docs/ux/02-componentes/06-12-{rest}.md` (path place-holder — refers to existing files `06-cartesian-plane.md` through `12-next-step.md`) | `> SUPERSEDED → CMP-00X-{name}.md` | (mapeamento individual) |
| `src/operational/docs/ux/01-inventario/02-matriz-estados.md` | `> SUPERSEDED → docs/design-system/33-status-matrix-unified.md` | Consolidado em doc 33 |
| `src/operational/docs/design-system/DESIGN-SYSTEM.md` | `> SUPERSEDED → docs/design-system/34-superseded-pav-era-tokens.md` | Doc 34 trailer |

**Workflow de migration:**

1. Criar arquivo novo no path compliant com conteúdo migrado
2. Adicionar trailer SUPERSEDED ao arquivo antigo (1-2 linhas, anchor link)
3. Commit: `chore(design-system): rename UX component to CMP-NNN convention (preserve append-only)`
4. Atualizar cross-refs em outros docs (grep por old path → replace)
5. Após 6+ months de stability, mover arquivo antigo para `archive/` (NÃO deletar)

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 5)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 5 mapa (este doc é peça load-bearing)
- **`docs/design-system/30-tokens-deep-agent-era.md`** §3.4 — `T-glyph-*` table; este doc define naming `T-*` convention
- **`docs/design-system/31-ueid-visual-representation.md`** §3.1 — renderer `T-glyph-*` references
- **`docs/design-system/33-status-matrix-unified.md`** §3 — usa SCR-NNN convention para matrizes state × regime

### 4.2 UX docs (origem PAV-era, a serem migradas)

- **`src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md`** a **`FLOW-005-bloco-deep-work.md`** — 5 flows já conformes; references em SCRs
- **PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created)** a **`12-button.md`** — 12 components a migrar para CMP-NNN
- **PROPOSTA: `src/operational/docs/ux/00-visao-geral/01-telas-principais.md` (path place-holder)** — candidato a SCR-001
- **PROPOSTA: `src/operational/docs/ux/01-inventario/01-telas-cadastradas.md` (path place-holder)** — candidato a SCR-002
- **`src/operational/docs/ux/01-inventario/02-matriz-estados.md`** — consolidado em doc 33

### 4.3 ADR (Architecture Decision Record)

- **ADR-003** — naming pattern kebab-case + NNN zero-padded (referência direta a este doc; este doc detalha aplicação)

### 4.4 Code anchors

| Path | Conteúdo | Naming binding |
|:-----|:---------|:----------------|
| `src/contracts/common.py` | `UEID.REGEX`, prefixos | `T-glyph-*` table reference |
| `src/contracts/task.py:42-77` | `Task`, `Project` | SCR/FLOW template |
| `src/mesh/adapters/cli.py` | JSONL storage | CMP-011 (form-field) reference |
| `src/mesh/adapters/taskdog.py:69` | SQLite schema | CMP-006 (KPI card) reference |

### 4.5 Memory cross-refs

- **`[[cli-command-palette-pivot-2026-08-28]]`** — workspace = command palette sobre MCP contracts; SCR/FLOW/CMP/KPI naming ancora command palette structure
- **`[[doc-migration-2026-08-28]]`** — doc migration workflow com trailers SUPERSEDED (mesmo padrão aplicado aqui)
- **`[[docs-superseded-trailer-2026-08-28]]`** — canonical trailer pattern (este doc segue o padrão)

---

## §5 — Fontes

### Code (verificado via Read tool)
- `src/contracts/common.py` — UEID regex + prefix types
- `src/contracts/task.py` — Task, Project (templates para SCR)
- `src/mesh/adapters/base.py` — ForkAdapter Protocol

### Docs design-system
- `docs/design-system/00-INDEX.md` — Layer 5 mapa
- `docs/design-system/30-tokens-deep-agent-era.md` — `T-*` convention canonical
- `docs/design-system/31-ueid-visual-representation.md` — UEID renderer usando `T-glyph-*`
- `docs/design-system/33-status-matrix-unified.md` — matriz usa SCR-NNN convention
- `docs/design-system/34-superseded-pav-era-tokens.md` — SUPERSEDED trailer (este doc segue padrão)

### Docs UX (origem, a migrar)
- `src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md` a `FLOW-005` — 5 flows já conformes
- PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) a `12-button.md` — 12 components a migrar
- PROPOSTA: `src/operational/docs/ux/00-visao-geral/01-telas-principais.md` (path place-holder) — candidato a SCR-001
- `src/operational/docs/ux/01-inventario/02-matriz-estados.md` — consolidado em doc 33

### ADR
- **ADR-003** — kebab-case + NNN naming pattern

### Memory cross-refs
- `[[cli-command-palette-pivot-2026-08-28]]` — command palette structure
- `[[doc-migration-2026-08-28]]` — migration workflow pattern
- `[[docs-superseded-trailer-2026-08-28]]` — SUPERSEDED trailer canonical pattern

---

> **Próxima ação recomendada:** criar arquivos `CMP-001` a `CMP-012` (migrar conteúdo de `src/operational/docs/ux/02-componentes/01-12`), adicionar trailers SUPERSEDED nos arquivos originais, atualizar cross-refs em todos os docs do docset. Bloqueado por data-first methodology (5 SONHO logs gate de ADR-007).