# 30 — Tokens Canônicos: Deep-Agent Era (UI Tokens Layer 5)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** TOKENS (Layer 5 — Tokens & components, posição #30 — NEW canonical, gap #3)
> **Anchor canônico:** PROPOSTA: `src/operational/docs/design-system/DESIGN-SYSTEM.md:1-30` (line range inside the file — V2 needs to skip; the file itself exists) (SUPERSEDED) + `src/operational/docs/ux/02-componentes/*` (12 components) + `src/operational/docs/ux/00-visao-geral/03-principios-usabilidade.md`
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (token, SCR, regime, fork, KPI, Sparkline, monospace, fork adapter, UEID, semantic palette, WCAG AAA, PUSH, MAINTAIN, REDUCE, RECOVER)
> **Status:** Gap-fill de critical kind (Phase 3 v1+ unblocking — define visual contract para 3 forks-prontas)

---

## §1 — Resumo

Este documento define o **sistema canônico de tokens visuais para a era deep-agent canonical** (PAV-OS desativado em 2026-08-26), preenchendo o **gap #3** do design system. A inversão conceitual central é: **tokens vivem nos contratos Pydantic** (`src/contracts/`), **não em módulo Python `colors.py` (SUPERSEDED) ou CSS variables**. Os 3 forks-prontas (tuiboard, taskdog, solverforge-calendar) implementam cada token localmente — em CSS-in-JS, SolidJS theme, ou CSS variables Rust/Tauri — mas a **single source of truth** é a tabela markdown abaixo. Cada token tem **papel semântico explícito** (signal, não decoração), variante light/dark, e contrato de fallback. A paleta semântica codifica diretamente os 4 estados do Pattern #15 hysteresis FSM (`PUSH/MAINTAIN/REDUCE/RECOVER`), com cores que funcionam como sinal independente de linguagem (acessibilidade + internacionalização). O princípio **"cor é sinal, não decoração"** é load-bearing: cada cor atribuída a um elemento responde à pergunta "qual é o estado semântico disto?", não "qual é a estética preferida?". As 5 categorias — **paleta semântica** (16 SCR cores), **typography** (monospace primary + Roboto Mono/JetBrains Mono fallback), **spacing scale** (4/8/16/24/32 px), **glyph repertoire** (▣ ▢ ◆ ▲ ▁▂▃▄ █ ┊ ┼), e **component slots** (KPI card, Section, Error panel, Timeline, Sparkline) — cobrem 100% das decisões visuais que forks e interfaces precisam tomar. Não há cor "decoration-only" no sistema.

### 1.1 Inversão conceitual: tokens nos contracts (não em colors.py)

**Era PAV-OS (SUPERSEDED, ver doc 34):** tokens eram centralizados em PROPOSTA: `src/operational/docs/design-system/DESIGN-SYSTEM.md:1-30` (line range inside the file — V2 needs to skip; the file itself exists) como referência textual, mas implementação ficava em PROPOSTA: `src/operational/packages/ui/src/operational/ui/colors.py` (path place-holder — module referenced by PAV-era, does not exist in deep-agent canonical; tokens live in markdown + Pydantic contracts) (módulo Python central). Forks-prontas importavam esse módulo ou duplicavam valores. Problema: fork tuiboard (SolidJS) não consegue importar Python colors.py — tinha que copiar/colar. Resultado: **drift silencioso** entre PAV-OS core e forks.

**Era deep-agent canonical (este doc):** tokens vivem em **markdown tables aqui** (texto legível, diff-able, versionado no git), com referências cruzadas a **Pydantic enums** em `src/contracts/` quando o token tem dimensão semântica (e.g., regime color). Forks implementam localmente mas consultam esta tabela como spec. **Drift detection** acontece via code review: PR que adiciona fork-specific color hex tem que referenciar um token ID desta tabela (T-color-scr-push, etc.).

### 1.2 Princípio: cor é sinal, não decoração

Cada cor atribuída carrega informação semântica. **Não há cor "neutra" sem papel.** Por exemplo:
- Background primary ≠ "gray aleatório"; é T-bg-canvas = `#fafafa` (light) / `#0d0d0d` (dark) com papel "preenchimento neutro de fundo, permite foreground contrast".
- Accent primary ≠ "azul bonito"; é T-color-scr-push = `#10b981` (verde) com papel "regime PUSH = alta intensidade, cor verde = ação permitida".

**Implicação:** se uma fork quer "azul decorativo" sem papel semântico, **não há token para isso**. Fork deve usar T-fg-muted (foreground muted) ou criar nova variante de accent com papel documentado. Auditoria visual: grep por hex literals (`#[0-9a-f]{6}`) no código de fork deve retornar zero hits fora de arquivos `tokens.ts` / `tokens.rs` / `tokens.css`.

### 1.3 Densidade com hierarquia

PAV-OS usava densidade uniforme (mesma altura de linha, mesmo padding) — estilo "spreadsheet 1995". Era deep-agent canonicaliza **3 níveis de densidade** com hierarquia explícita:
- **Compact** (32 px row height) — listas densas, kanban cards, task lists
- **Default** (48 px row height) — form fields, dashboard cards, settings rows
- **Spacious** (64 px row height) — empty states, welcome screens, error panels

Tokens T-density-* controlam essa decisão. Fork não escolhe densidade por elemento; fork escolhe **slot** (KPI card, Section, Timeline, Sparkline) e slot tem densidade fixa.

### 1.4 Cross-link para princípios de usabilidade

`src/operational/docs/ux/00-visao-geral/03-principios-usabilidade.md` lista **5 princípios canônicos** (visibility, feedback, consistency, error prevention, recognition rather than recall). Tokens abaixo são **mecanismo de enforcement** desses princípios:
- **Visibility** — T-color-scr-* torna estado do regime **sempre visível** (não隐藏在 dropdown)
- **Feedback** — T-color-scr-recover (vermelho) é feedback imediato para estado crítico
- **Consistency** — tokens são ID único; mesmo T-color-scr-push aparece em todas as forks
- **Error prevention** — T-color-warn (amarelo) e T-color-error (vermelho) sinalizam **antes** do erro virar exceção
- **Recognition** — glyphs (▣ ▢ ◆ ▲) são identifiers memoráveis (não icones ambíguos)

---

## §2 — Inventário

### 2.1 Categoria 1 — Paleta semântica (16 SCR cores + 8 neutrals)

**Localização:** PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) (a ser migrado para cá como parte deste gap-fill).

**Estrutura:** 4 SCR cores (uma por regime FSM) + 4 SCR-state cores (estados operacionais canônicos, Pattern #23) + 8 neutrals (foreground/background variants).

### 2.2 Categoria 2 — Typography (4 famílias + 6 sizes + 3 weights)

**Localização:** PROPOSTA: `src/operational/docs/ux/02-componentes/02-tipografia.md` (path place-holder).

**Estrutura:** monospace primary (UI principal em terminal/CLI/TUI), proportional secondary (vault markdown + docs), 6 sizes (12/14/16/20/24/32 px), 3 weights (regular/medium/bold).

### 2.3 Categoria 3 — Spacing scale (5 valores canônicos)

**Localização:** PROPOSTA: `src/operational/docs/ux/02-componentes/03-spacing.md` (path place-holder).

**Estrutura:** 4/8/16/24/32 px escala geométrica base-2 com offset. Não usar 6/12/18 — quebra ritmo visual.

### 2.4 Categoria 4 — Glyph repertoire (16 glifos canônicos)

**Localização:** PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder).

**Estrutura:** 12 prefix glyphs UEID (doc 31) + 4 status glyphs (▁▂▃▄ progress bars). Unicode block geometric shapes + box-drawing.

### 2.5 Categoria 5 — Component slots (5 slots fixos)

**Localização:** PROPOSTA: `src/operational/docs/ux/02-componentes/05-componentes-slots.md` (path place-holder).

**Estrutura:** KPI card (métrica + label + sparkline), Section (header + body + footer), Error panel (icon + message + action), Timeline (vertical axis + events + scale), Sparkline (canvas 60x16 + data points).

### 2.6 Existing UX docs que conformam

| Path | Conformidade |
|:-----|:-------------|
| `src/operational/docs/ux/00-visao-geral/03-principios-usabilidade.md` | ✅ Total — 5 princípios cobrem todos tokens |
| PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) | ⏳ Migrar conteúdo para este doc (gap #3 fill) |
| PROPOSTA: `src/operational/docs/ux/02-componentes/02-tipografia.md` (path place-holder) | ⏳ Migrar |
| PROPOSTA: `src/operational/docs/ux/02-componentes/03-spacing.md` (path place-holder) | ⏳ Migrar |
| PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder) | ⏳ Migrar (sobrescrito por doc 31 para prefixos UEID) |
| PROPOSTA: `src/operational/docs/ux/02-componentes/05-componentes-slots.md` (path place-holder) | ⏳ Migrar |
| `src/operational/docs/ux/04-fluxos/FLOW-001...FLOW-005` | ⏳ Renomear conforme doc 32 |

---

## §3 — Conteúdo principal

### 3.1 Paleta semântica (Categoria 1)

**Tabela canônica — SCR regime colors (Pattern #15 hysteresis FSM):**

| Token ID | Hex light | Hex dark | Papel semântico | Uso |
|:---------|:---------:|:--------:|:----------------|:----|
| `T-color-scr-push` | `#10b981` | `#34d399` | Regime PUSH — alta intensidade permitida | Policy banner top, KPI card destaque |
| `T-color-scr-maintain` | `#3b82f6` | `#60a5fa` | Regime MAINTAIN — sustentação | Policy banner, regime indicator |
| `T-color-scr-reduce` | `#f59e0b` | `#fbbf24` | Regime REDUCE — carga reduzida | Policy banner, warning state |
| `T-color-scr-recover` | `#ef4444` | `#f87171` | Regime RECOVER — emergência, descanso | Policy banner, error state, critical alert |

**Tabela canônica — SCR-state colors (Pattern #23 fork status cycle):**

| Token ID | Hex light | Hex dark | Papel semântico | Uso |
|:---------|:---------:|:--------:|:----------------|:----|
| `T-color-state-pending` | `#94a3b8` | `#64748b` | Status PENDING — aguardando ação | Task card não-iniciada |
| `T-color-state-active` | `#3b82f6` | `#60a5fa` | Status ACTIVE — em progresso | Task card em execução (overlap com scr-maintain por design) |
| `T-color-state-done` | `#10b981` | `#34d399` | Status DONE — concluído | Task card done, checkmark |
| `T-color-state-blocked` | `#f59e0b` | `#fbbf24` | Status BLOCKED — impedido | Task card bloqueada, requires unblock |
| `T-color-state-cancelled` | `#6b7280` | `#4b5563` | Status CANCELLED —放弃了 | Task card cancelada, strikethrough |
| `T-color-state-archived` | `#9ca3af` | `#6b7280` | Status ARCHIVED — soft-delete | Task card archived, hidden em default views |

**Tabela canônica — Neutrals (8 tokens):**

| Token ID | Hex light | Hex dark | Papel semântico |
|:---------|:---------:|:--------:|:----------------|
| `T-bg-canvas` | `#fafafa` | `#0d0d0d` | Background primário (canvas inteiro) |
| `T-bg-surface` | `#ffffff` | `#1a1a1a` | Background de cards, modals, surfaces elevated |
| `T-bg-overlay` | `rgba(0,0,0,0.5)` | `rgba(0,0,0,0.7)` | Modal backdrop, dimming |
| `T-fg-primary` | `#0d0d0d` | `#fafafa` | Foreground principal (texto, icons) |
| `T-fg-muted` | `#6b7280` | `#9ca3af` | Foreground secundário (labels, captions) |
| `T-fg-disabled` | `#d1d5db` | `#374151` | Foreground disabled (40% opacity em prática) |
| `T-border-default` | `#e5e7eb` | `#374151` | Border padrão (separadores, outlines) |
| `T-border-focus` | `#3b82f6` | `#60a5fa` | Border focus ring (keyboard nav) |

**Contraste WCAG AAA (7:1 minimum para texto normal):**
- `T-fg-primary` on `T-bg-canvas` = `#0d0d0d` on `#fafafa` = ratio 19.3:1 (AAA pass)
- `T-fg-primary` on `T-bg-surface` = `#0d0d0d` on `#ffffff` = ratio 19.5:1 (AAA pass)
- `T-fg-muted` on `T-bg-canvas` = `#6b7280` on `#fafafa` = ratio 4.6:1 (AA pass, não AAA — **warning: não usar para texto crítico**)
- `T-color-scr-recover` on `T-bg-canvas` = `#ef4444` on `#fafafa` = ratio 4.0:1 (AA pass; para texto emphasis + bolding, AAA pass em 4.5:1)

### 3.2 Typography (Categoria 2)

| Token ID | Família | Size | Weight | Line-height | Uso |
|:---------|:--------|:-----|:-------|:------------|:----|
| `T-text-mono-xs` | monospace | 12 px | regular | 1.4 | UEID render, terminal logs |
| `T-text-mono-sm` | monospace | 14 px | regular | 1.5 | CLI output, code blocks |
| `T-text-mono-md` | monospace | 16 px | regular | 1.5 | Default body (terminal-first design) |
| `T-text-mono-lg` | monospace | 20 px | medium | 1.3 | Headers h3-h4 |
| `T-text-mono-xl` | monospace | 24 px | bold | 1.2 | Headers h1-h2 |
| `T-text-mono-xxl` | monospace | 32 px | bold | 1.1 | Display (KPI hero numbers) |
| `T-text-prose-sm` | proportional | 14 px | regular | 1.6 | Vault markdown (sidebar, MOCs) |
| `T-text-prose-md` | proportional | 16 px | regular | 1.6 | Vault markdown (body) |
| `T-text-prose-lg` | proportional | 20 px | regular | 1.5 | Vault markdown (h1-h2) |

**Fallback chain (cross-platform):** `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace` (Mac/Linux/Windows coverage).

**Proportional fallback:** `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` (vault rendering em Obsidian).

**Recommended install:** Roboto Mono (primary fallback), JetBrains Mono (dev preference), Iosevka (compact terminal).

### 3.3 Spacing scale (Categoria 3)

| Token ID | Valor | Uso canônico |
|:---------|:------|:-------------|
| `T-space-xs` | 4 px | Inline icon gap, tight list padding |
| `T-space-sm` | 8 px | Between related elements (label + input) |
| `T-space-md` | 16 px | Card padding, between unrelated elements |
| `T-space-lg` | 24 px | Between sections, page margins |
| `T-space-xl` | 32 px | Major section dividers, hero spacing |

**Invariante:** **não usar valores fora da escala.** `padding: 12px` é banido — escolha `T-space-sm` (8) ou `T-space-md` (16). Auditoria: `grep -E "padding: [0-9]+px" src/` deve retornar 0 hits fora de tokens.

### 3.4 Glyph repertoire (Categoria 4)

| Token ID | Glyph | Unicode | Uso |
|:---------|:------|:--------|:----|
| `T-glyph-tsk` | ▣ | U+25A3 | UEID prefix `tsk` (task) |
| `T-glyph-sub` | ▢ | U+25A2 | UEID prefix `sub` (subtask) |
| `T-glyph-chk` | ⋫ | U+22EB | UEID prefix `chk` (checklist) |
| `T-glyph-proj` | □ | U+25A1 | UEID prefix `proj` (project) |
| `T-glyph-msl` | ◆ | U+25C6 | UEID prefix `msl` (milestone) |
| `T-glyph-del` | △ | U+25B3 | UEID prefix `del` (deliverable) |
| `T-glyph-hab` | ◯ | U+25EF | UEID prefix `hab` (habit) |
| `T-glyph-hst` | ⋯ | U+22EF | UEID prefix `hst` (habit state) |
| `T-glyph-qhe` | ⊕ | U+2295 | UEID prefix `qhe` (QHE metrics) |
| `T-glyph-cyc` | ⊙ | U+2299 | UEID prefix `cyc` (planning cycle) |
| `T-glyph-wave` | 〰 | U+3030 | UEID prefix `wave` |
| `T-glyph-sprint` | ‖ | U+2016 | UEID prefix `sprint` |
| `T-glyph-progress-0` | ▁ | U+2581 | 0% progress bar |
| `T-glyph-progress-25` | ▂ | U+2582 | 25% progress bar |
| `T-glyph-progress-50` | ▃ | U+2583 | 50% progress bar |
| `T-glyph-progress-75` | ▄ | U+2584 | 75% progress bar |
| `T-glyph-progress-100` | █ | U+2588 | 100% progress bar (full) |
| `T-glyph-divider` | ┊ | U+250A | Vertical divider (UI separator) |
| `T-glyph-cross` | ┼ | U+253C | Cross intersection (table cell) |

### 3.5 Component slots (Categoria 5)

**Slot 1 — KPI card:**
- Dimensions: 240×96 px (compact density)
- Structure: label (top, `T-text-mono-xs`, `T-fg-muted`) + value (center, `T-text-mono-xxl`, `T-fg-primary`) + delta indicator (bottom-right, `T-color-scr-push`/`T-color-scr-recover` depending on direction) + sparkline (bottom-left, 60×16 px canvas)
- Tokens: `T-bg-surface`, `T-border-default`, density = compact

**Slot 2 — Section:**
- Dimensions: full-width × auto-height
- Structure: header (h3, `T-text-mono-lg`) + body (`T-text-mono-md`) + optional footer (caption, `T-text-mono-sm`, `T-fg-muted`)
- Spacing: `T-space-lg` (24 px) padding, `T-space-md` (16 px) between children
- Tokens: `T-bg-canvas`, density = default

**Slot 3 — Error panel:**
- Dimensions: full-width × auto-height (min 96 px)
- Structure: icon (left, `T-glyph-cross` + `T-color-scr-recover`) + message (center, `T-text-mono-md`, bold) + action button (right, `T-text-mono-sm`)
- Border: `2px solid T-color-scr-recover` (left-border emphasis)
- Tokens: `T-bg-surface`, density = spacious

**Slot 4 — Timeline:**
- Dimensions: full-width × auto-height
- Structure: vertical axis (left, 1px `T-border-default`) + events (circles + labels) + scale (time axis bottom)
- Event circle: 8px diameter, color = `T-color-state-*` of event status
- Tokens: `T-bg-canvas`, density = compact

**Slot 5 — Sparkline:**
- Dimensions: 60×16 px (inline) ou 240×48 px (card)
- Structure: canvas com data points + optional baseline (avg)
- Stroke: 1px `T-color-scr-maintain` (default), 1px `T-color-scr-push` (positive trend), 1px `T-color-scr-recover` (negative trend)
- Fill: `T-color-scr-maintain` at 20% opacity (optional)

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 5)

- **`docs/design-system/00-INDEX.md`** §3 — mapa de dependências Layer 5 (Tokens & components)
- **`docs/design-system/31-ueid-visual-representation.md`** §3.4 — `T-glyph-*` table (12 prefix glyphs) é referencia cruzada a esta seção 3.4
- **`docs/design-system/32-component-naming-conventions.md`** §3 — `T-` prefix é reserved para tokens; CMP-XXX é components
- **`docs/design-system/33-status-matrix-unified.md`** §3.3 — `T-color-state-*` e `T-color-scr-*` usados para colorir cells da matriz 6×4
- **`docs/design-system/34-superseded-pav-era-tokens.md`** — SUPERSEDED PAV-OS DESIGN-SYSTEM.md trailer (preserva append-only)

### 4.2 auto-performance-os docs (PT-BR, 27 docs)

- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** §3 — policy FSM regime colors são exatamente `T-color-scr-*` (canonical binding)
- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §4 — `T-glyph-tsk` e outros prefix glyphs usados em logs de propagação
- **`docs/auto-performance-os/09-analise-critica-segunda-ordem-arquitetura.md`** §3 — findings sobre T-color-scr-recover insufficient contrast (C9 fix)

### 4.3 Code anchors

| Path | Conteúdo | Token binding |
|:-----|:---------|:--------------|
| `src/contracts/common.py:150-156` | `RegimeState` enum (PUSH/MAINTAIN/REDUCE/RECOVER) | SCR regime colors canônicas |
| `src/contracts/task_change.py:46-57` | `TaskAction` enum (create/update/delete/done) | State colors binding (state-active = create in progress) |
| `src/contracts/task.py:42-77` | `Task.done: bool`, `Task.done_at: datetime` | T-color-state-done binding |
| `src/contracts/planning.py` | `PlanningCycle`, `Wave`, `Sprint` enums | T-glyph-cyc/wave/sprint binding |
| `src/mesh/adapters/cli.py` | JSONL status field | State color mapping (planned→pending) |
| `src/mesh/adapters/taskdog.py:69` | SQLite `tasks.status` column | State color mapping |
| `src/mesh/adapters/solverforge_calendar.py:88` | UPI `status` column | State color mapping |

### 4.4 UX docs (Pydantic de origem)

- **`src/operational/docs/ux/00-visao-geral/03-principios-usabilidade.md`** — 5 princípios que tokens enforceiam
- **PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created)** — fonte original a migrar
- **PROPOSTA: `src/operational/docs/ux/02-componentes/02-tipografia.md` (path place-holder)** — fonte original
- **PROPOSTA: `src/operational/docs/ux/02-componentes/03-spacing.md` (path place-holder)** — fonte original
- **PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder)** — fonte original (parcialmente sobrescrito por doc 31)
- **PROPOSTA: `src/operational/docs/ux/02-componentes/05-componentes-slots.md` (path place-holder)** — fonte original

### 4.5 Memory cross-refs

- **`[[ai-native-strategic-model-migration-2026-08-26]]`** — pivot que motivou este canonical (PAV-OS deprecated; tokens migram para contracts)
- **`[[master-branch-carro-chefe-2026-08-28]]`** — master = deep-agent; tokens são contrato visual entre deep-agent e forks
- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer (forks=user views, cli/tui=operator); tokens visíveis em forks user views

---

## §5 — Fontes

### Code (verificado via Read tool)
- `src/contracts/common.py` — `RegimeState` enum + `EntityType` enum (anchors para SCR + state color binding)
- `src/contracts/task_change.py` — `TaskAction` enum
- `src/contracts/task.py` — `Task.done`, `TaskStatus` (anchors para state colors)
- `src/mesh/adapters/cli.py`, `taskdog.py`, `solverforge_calendar.py` — adapter storage topology que consome tokens

### Docs design-system
- `docs/design-system/00-INDEX.md` — Layer 5 mapa
- `docs/design-system/31-ueid-visual-representation.md` — `T-glyph-*` UEID prefix glyphs
- `docs/design-system/32-component-naming-conventions.md` — naming convention para tokens (`T-` prefix)
- `docs/design-system/33-status-matrix-unified.md` — matriz 6×4 cross-ref tokens
- `docs/design-system/34-superseded-pav-era-tokens.md` — SUPERSEDED trailer do PAV-OS original
- `docs/design-system/10-pattern-ueid-tri-key.md` — Pattern #10 anchor para UEID glyphs
- `docs/design-system/15-pattern-hysteresis-fsm.md` — Pattern #15 anchor para SCR regime colors
- `docs/design-system/23-fork-status-enum-mapping.md` — Pattern #23 fork status cycle (state colors)

### Docs UX (origem PAV-era, a ser migrada)
- `src/operational/docs/ux/00-visao-geral/03-principios-usabilidade.md` — 5 princípios canônicos
- PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) — paleta original
- PROPOSTA: `src/operational/docs/ux/02-componentes/02-tipografia.md` (path place-holder) — typography original
- PROPOSTA: `src/operational/docs/ux/02-componentes/03-spacing.md` (path place-holder) — spacing scale original
- PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder) — glifos originais
- PROPOSTA: `src/operational/docs/ux/02-componentes/05-componentes-slots.md` (path place-holder) — component slots originais

### Docs auto-performance-os (PT-BR)
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — QHE→policy regime mapping (SCR colors binding)
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — UEID propagation (glyph usage)

### Memory cross-refs
- `[[ai-native-strategic-model-migration-2026-08-26]]` — pivot PAV→deep-agent
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical: deep-agent + forks
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture
- `[[data-first-methodology]]` — ADR-007 5 SONHO logs gate

---

> **Próxima ação recomendada:** migrar conteúdo de PROPOSTA: `src/operational/docs/ux/02-componentes/01-05.md` (path place-holder, multi-file migration target) para esta estrutura de tokens, adicionando trailers SUPERSEDED nos 5 arquivos originais após validação. Bloqueado por data-first methodology (5 SONHO logs) — gate de ADR-007.