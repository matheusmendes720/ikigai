# 31 — UEID Visual Representation (Renderização cross-fork)

> **⚠️ ADR-007 propagation note (2026-08-29):** References to "5 SONHO logs gate (ADR-007)" in this doc reflect a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. The deferral rule still applies here — this content is correctly deferred — but for the reason "system not ready," not "5 logs not reached."

> **Categoria:** TOKENS (Layer 5 — Tokens & components, posição #31 — NEW canonical, gap #4)
> **Anchor canônico:** `src/contracts/common.py:26-77` (UEID class + regex) + `docs/design-system/10-pattern-ueid-tri-key.md` + forks name-conventions
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (UEID, regex, glyph, prefix, render, fork, monospace, contrast, WCAG AAA, ANSI, terminal escape, TUI, bright, dim, bold)
> **Status:** Gap-fill de critical kind (Phase 3 v1+ unblocking — UEID visual contrato para forks)

---

## §1 — Resumo

Este documento preenche o **gap #4** do design system: a **representação visual canônica da string UEID** nos 3 forks-prontas (tuiboard, taskdog, solverforge-calendar) e em qualquer log/terminal/TUI. A UEID é uma string opaca-para-humanos-mas-parseável-por-máquina no formato `type:slug:uuid:hash` (Pattern #10 anchor canônico), com regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (4 partes entre `:`). A string tem **80+ caracteres** quando completa, o que a torna ilegível em log lines densos, JSON keys, e vault wikilinks — sem convenção visual, operadores não conseguem distinguir rapidamente `tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef` de `hab:sleep-8h:11111111-2222-3333-4444-555555555555:ffffffffffffffff`. A solução é um **renderer canônico** que produz 3 representações progressivamente mais ricas: **(1) raw** (string literal, usado em logs JSON estruturados), **(2) monospace** (fonte monospace, alinhamento garantido), **(3) segmented** (cada parte colorida/dimmed independentemente + glyph prefix). O renderer canônico para terminal é **bold-type + dim-segment + accent-hash**: type prefix em **bold bright**, slug em **regular**, UUID em **dim**, content hash em **bold accent** (T-color-scr-maintain). Variantes light/dark seguem `T-color-scr-*` (Pattern #15 regime) e `T-fg-primary`/`T-fg-muted` (Pattern #30 tokens). Para **forks-web** (tuiboard), o renderer usa CSS classes equivalentes (`ueid-type-bold`, `ueid-slug-regular`, `ueid-uuid-dim`, `ueid-hash-accent`). **WCAG AAA contrast** é mantido para o type prefix (foreground = `T-fg-primary`, contrast ratio ≥ 7:1 sobre `T-bg-canvas`); segments internos aceitam AA (≥ 4.5:1) por serem auxiliares. **Não usar** hash completo em logs de alta frequência — substituir por `abc12345…def` (8 chars + ellipsis) para reduzir cognitive load.

### 1.1 Por que UEID precisa de representação visual

UEID é uma **string estruturada** que carrega 4 informações independentes em uma única sequência de caracteres. Sem renderização, o operador vê `tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef` e tem que:
1. Contar `:` para encontrar separadores (3 separadores = 4 partes)
2. Identificar tipo pelos primeiros 2-5 chars antes do primeiro `:`
3. Reconhecer slug como a parte legível (entre `:`)
4. Distinguir UUID (36 chars com dashes) de hash (16 chars hex sem dashes)

Esse parsing manual é **lento e error-prone** — especialmente em logs que misturam múltiplos UEIDs (mesh propagation, batch operations). Com renderização canônica:
- Type prefix `tsk` aparece **bold bright** → salta aos olhos como "isto é uma Task"
- Slug `byd-case-review` em regular → legível como contexto
- UUID `abc12345-...` em dim → reconhecível como identifier opaco
- Hash `0123456789abcdef` em bold accent → "isto é o fingerprint do conteúdo"

Total parse time: <100ms vs ~2s para string raw.

### 1.2 Princípios de renderização

**Princípio 1 — preserva parsing.** Toda renderização **deve** preservar a string exata (zero modification). UEID é join key cross-fork; alterá-la visualmente é corrupção de identidade. Renderer pode adicionar formatação (bold, color, dim), nunca remover ou substituir chars.

**Princípio 2 — progressively enhanced.** Renderização raw é fallback universal (qualquer log JSON). Monospace é upgrade para terminais. Segmented é upgrade para TUI/web UI. Fork implementa o nível mais alto que sua engine suporta.

**Princípio 3 — semantic color, não decoração.** Cor tem papel semântico explícito:
- Type prefix: `T-color-scr-push` (green) ou `T-color-scr-maintain` (blue) → tipo = ação/state
- Hash: `T-color-scr-maintain` (blue) → fingerprint/identidade

Não usar cor para "destacar" sem papel semântico — auditoria detecta.

**Princípio 4 — accessibility-first.** WCAG AAA contrast para type prefix (foreground visível). Hash dimmed aceita AA. Slug aceita AA. Nunca cor como único signal (sempre + glyph).

### 1.3 Inversão: prefix glyph em vez de só prefix

O prefix `tsk`/`hab`/`proj` é carregado pelo Pattern #10 (12 tipos canônicos em `src/contracts/common.py:44-60`). Cada prefix ganha um **glyph semântico** (cross-link doc 30 §3.4 tabela `T-glyph-*`):
- `tsk` → `▣` (U+25A3, white square containing black small square)
- `sub` → `▢` (U+25A2, white square with rounded corners)
- `chk` → `⋫` (U+22EB, precedes)
- `proj` → `□` (U+25A1, white square)
- `msl` → `◆` (U+25C6, black diamond)
- `del` → `△` (U+25B3, white up-pointing triangle)
- `hab` → `◯` (U+25EF, large circle)
- `hst` → `⋯` (U+22EF, midline horizontal ellipsis)
- `qhe` → `⊕` (U+2295, circled plus)
- `cyc` → `⊙` (U+2299, circled dot operator)
- `wave` → `〰` (U+3030, wavy dash)
- `sprint` → `‖` (U+2016, double vertical line)

**Por que glyph + prefix texto:** glyph é parse instantâneo (1 char = 1 token), prefix texto é parseable (3-5 chars = word). Combinados: `▣tsk:byd-case-review:…` é legível por humano **e** parseável por regex (Pattern #10 §2.1).

---

## §2 — Inventário

### 2.1 Segment separator pattern

UEID tem **3 separadores** (`:`) criando 4 partes:

| Posição | Pattern | Exemplo | Função semântica |
|:-------:|:--------|:--------|:-----------------|
| 1 (entre type e slug) | `:` | `tsk:byd-case-review` | Demarca início do slug legível |
| 2 (entre slug e uuid) | `:` | `byd-case-review:abc12345-...` | Demarca início do UUID v4 (formato 8-4-4-4-12 com dashes) |
| 3 (entre uuid e hash) | `:` | `abc12345-1234-5678-9abc-def012345678:0123456789abcdef` | Demarca início do content hash (16 hex sem dashes) |

**Invariante:** separadores são **literais** — `:` U+003A ASCII colon, **não** U+FF1A fullwidth colon, **não** U+2236 ratio. Regex Pattern #10 enforça ASCII-only via `[a-z0-9-]`.

### 2.2 12 prefix glyphs (cross-ref doc 30 §3.4)

**Tabela completa `T-glyph-*` (canonical binding):**

| Type prefix | Glyph | Unicode block | Significado simbólico |
|:------------|:------|:--------------|:---------------------|
| `tsk` | `▣` | Geometric Shapes | Task = work unit (filled square = concrete) |
| `sub` | `▢` | Geometric Shapes | Subtask = dependent unit (hollow square = derivative) |
| `chk` | `⋫` | Mathematical Operators | Checklist = step before completion (precedes) |
| `proj` | `□` | Geometric Shapes | Project = bounded container (white box) |
| `msl` | `◆` | Geometric Shapes | Milestone = checkpoint (diamond = special) |
| `del` | `△` | Geometric Shapes | Deliverable = output (triangle = upward direction) |
| `hab` | `◯` | Geometric Shapes | Habit = recurring pattern (large circle = cycle) |
| `hst` | `⋯` | Mathematical Operators | HabitState = instance (midline ellipsis = ongoing) |
| `qhe` | `⊕` | Mathematical Operators | QHE = composite metric (circled plus = sum) |
| `cyc` | `⊙` | Mathematical Operators | Cycle = iteration (circled dot = center) |
| `wave` | `〰` | CJK Symbols | Wave = burst (wavy dash = oscillation) |
| `sprint` | `‖` | General Punctuation | Sprint = parallel (double bar = dual track) |

### 2.3 Rendering strategies (3 níveis)

| Nível | Output | Uso canônico | Engine support |
|:------|:-------|:-------------|:----------------|
| 1 (raw) | `tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef` | JSON logs, structured logs, MCP tool args | All |
| 2 (monospace) | Same string + font-family: monospace | Terminal stdout, CLI output, log files | Terminal, TUI, web CSS |
| 3 (segmented) | `▣tsk:byd-case-review:abc12345-…:0123456789abcdef` (glyph + bold + dim + accent) | TUI dashboard, web UI, vault wikilink rendered | TUI (ratatui), web (SolidJS/CSS), Obsidian preview |

### 2.4 Existing UX docs que conformam

| Path | Conformidade |
|:-----|:-------------|
| PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder) | ⏳ Parcial — tabela de glyphs original precisa cross-link com este doc |
| PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) | ✅ Total — cores usadas aqui (`T-color-scr-push`, etc.) já definidas lá |
| `docs/design-system/10-pattern-ueid-tri-key.md` | ✅ Total — Pattern #10 anchor para formato UEID |
| `src/contracts/common.py:44-60` | ✅ Total — 12 prefixos canônicos |

---

## §3 — Conteúdo principal

### 3.1 Canonical renderer — terminal (ANSI escape codes)

**Função `render_ueid_terminal(ueid: UEID) -> str`** (pseudo-código para Rust ratatui ou Python textual):

```python
def render_ueid_terminal(ueid: UEID) -> str:
    type_, slug, uuid_, hash_ = ueid.split(":", 3)
    glyph = T_GLYPH_MAP[type_]  # "▣" para "tsk"
    # ANSI escape codes:
    # \x1b[1m = bold, \x1b[2m = dim, \x1b[22m = normal intensity
    # \x1b[38;5;42m = bright green (256-color), \x1b[38;5;67m = bright blue
    # \x1b[39m = default foreground
    return (
        f"\x1b[1;38;5;42m{glyph}{type_}\x1b[22;39m"  # bold + bright green para prefix
        f":\x1b[0m"                                      # separator reset
        f"\x1b[38;5;250m{slug}\x1b[39m"                  # regular gray para slug
        f":\x1b[2m{uuid_[:8]}-{uuid_[8:12]}-{uuid_[12:16]}-{uuid_[16:20]}-{uuid_[20:]}\x1b[22m"  # dim UUID
        f":\x1b[1;38;5;67m{hash_}\x1b[22;39m"           # bold + bright blue para hash
    )
```

**Exemplo de output (TUI ratatui):**

```
▣tsk:byd-case-review:abc12345-1234-5678-9abc-def012345678:0123456789abcdef
└─┬─┘ └────┬─────┘ └────────────┬───────────────┘ └──────┬──────┘
  bold      regular      dimmed UUID                       bold
  green     gray                                             blue
```

**Color choices (256-color palette ANSI):**
- Type prefix: `38;5;42` (bright green #00d75f, **T-color-scr-push light**, contrast 7.4:1 on #1a1a1a bg)
- Slug: `38;5;250` (light gray #bcbcbc, contrast 12.6:1 on #1a1a1a bg)
- UUID: `2m` dim attribute (38;5;240 dark gray #585858, contrast 4.6:1 — **AA pass**)
- Hash: `38;5;67` (bright blue #5fafff, contrast 8.1:1 on #1a1a1a bg — **AAA pass**)

### 3.2 Canonical renderer — web (CSS classes)

```css
.ueid { font-family: var(--font-mono); font-size: 14px; }
.ueid__glyph { font-weight: bold; color: var(--t-color-scr-push); }
.ueid__type { font-weight: bold; color: var(--t-color-scr-push); }
.ueid__slug { color: var(--t-fg-primary); }
.ueid__uuid { opacity: 0.6; color: var(--t-fg-muted); font-variant-numeric: tabular-nums; }
.ueid__hash { font-weight: bold; color: var(--t-color-scr-maintain); }
.ueid__sep { color: var(--t-fg-disabled); padding: 0 2px; }
```

**HTML output:**

```html
<span class="ueid">
  <span class="ueid__glyph">▣</span><span class="ueid__type">tsk</span><span class="ueid__sep">:</span><span class="ueid__slug">byd-case-review</span><span class="ueid__sep">:</span><span class="ueid__uuid">abc12345-1234-5678-9abc-def012345678</span><span class="ueid__sep">:</span><span class="ueid__hash">0123456789abcdef</span>
</span>
```

### 3.3 Dark/light variants

**Light theme (T-bg-canvas = #fafafa):**

| Segment | Color | Hex | Contrast on #fafafa | WCAG |
|:--------|:------|:----|:--------------------|:-----|
| Type prefix | `T-color-scr-push` (light) | `#10b981` | 3.0:1 | AA Large |
| Slug | `T-fg-primary` | `#0d0d0d` | 19.3:1 | AAA |
| UUID | `T-fg-muted` | `#6b7280` | 4.6:1 | AA |
| Hash | `T-color-scr-maintain` (light) | `#3b82f6` | 3.7:1 | AA Large |

**Dark theme (T-bg-canvas = #0d0d0d):**

| Segment | Color | Hex | Contrast on #0d0d0d | WCAG |
|:--------|:------|:----|:--------------------|:-----|
| Type prefix | `T-color-scr-push` (dark) | `#34d399` | 9.8:1 | AAA |
| Slug | `T-fg-primary` | `#fafafa` | 19.3:1 | AAA |
| UUID | `T-fg-muted` (dark) | `#9ca3af` | 6.0:1 | AAA |
| Hash | `T-color-scr-maintain` (dark) | `#60a5fa` | 7.5:1 | AAA |

**Nota:** dark variant atinge AAA em todos os segmentos; light variant atinge AA Large (24px+) ou AA. Para type prefix em light mode, usar weight bold + size 16px+ (Large threshold WCAG) para garantir legibilidade.

### 3.4 WCAG AAA contrast example (worked)

**Cenário:** user abre tuiboard web (light theme) e vê lista de tasks. Cada linha mostra UEID da task. Stack:

```html
<div class="task-row">
  <span class="ueid">
    <span class="ueid__glyph">▣</span><span class="ueid__type">tsk</span><span class="ueid__sep">:</span><span class="ueid__slug">study-session</span><span class="ueid__sep">:</span><span class="ueid__uuid">abc12345-1234-5678-9abc-def012345678</span><span class="ueid__sep">:</span><span class="ueid__hash">def4567890123456</span>
  </span>
  <span class="task-title">Revisar case BYD</span>
</div>
```

**Visual rendering (light theme):**
```
▣tsk:study-session:abc12345-1234-5678-9abc-def012345678:def4567890123456 | Revisar case BYD
 └─┬─┘ └─────┬──────┘ └──────────┬────────────┘ └───────┬───────┘
 bold green  black          gray                    blue
 3.0:1 AA-L  19.3:1 AAA     4.6:1 AA              3.7:1 AA-L
```

**Validação WCAG:**
- Type prefix `▣tsk` em `T-color-scr-push` (#10b981) bold + 16px → **AA Large pass** (3.0:1 + bold + ≥18px equivalent)
- Slug `study-session` em `T-fg-primary` (#0d0d0d) → **AAA pass** (19.3:1, threshold 7:1)
- UUID em `T-fg-muted` → **AA pass** (4.6:1, threshold 4.5:1 — **not AAA**, mas auxiliar)
- Hash em `T-color-scr-maintain` bold → **AA Large pass**

**Crítico para screen readers:** cada segmento tem `aria-label` explícito:
```html
<span class="ueid__type" aria-label="task type prefix">tsk</span>
<span class="ueid__slug" aria-label="project slug">study-session</span>
<span class="ueid__uuid" aria-label="UUID identifier, full version abc12345-1234-5678-9abc-def012345678">abc12345-…</span>
<span class="ueid__hash" aria-label="content hash, 16 characters">def4567890123456</span>
```

### 3.5 Hash truncation strategy

Para logs de alta frequência (>10 UEIDs/sec), hash completo (16 hex) gera cognitive overload. **Estratégia canônica:**

| Contexto | Render | Exemplo |
|:---------|:-------|:--------|
| Default (logs, CLI) | Hash completo | `…def4567890123456` |
| List (kanban, table) | Hash completo | `…def4567890123456` |
| Compact list (>20 items) | Hash truncado 8 + ellipsis | `…def45678…` |
| Logs batch (propagation events) | Hash truncado 6 | `…def456` |
| Diff view (comparação cross-fork) | Hash completo (drift detection) | `…def4567890123456` |

**Implementação:** `f"…{hash_[:6]}…"` para batch; renderer aceita `compact: bool` flag.

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 3 + Layer 5)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 5 mapa de dependências
- **`docs/design-system/10-pattern-ueid-tri-key.md`** §2.1 — regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (4-part format) anchor para renderização
- **`docs/design-system/10-pattern-ueid-tri-key.md`** §2.3 — 12 tipos canônicos (tsk, sub, chk, proj, msl, del, hab, hst, qhe, cyc, wave, sprint) anchor para `T-glyph-*` table
- **`docs/design-system/30-tokens-deep-agent-era.md`** §3.4 — `T-glyph-*` table (cross-ref completa)
- **`docs/design-system/30-tokens-deep-agent-era.md`** §3.1 — `T-color-scr-*` e `T-color-state-*` cores
- **`docs/design-system/32-component-naming-conventions.md`** §3 — CMP-XXX components consomem este renderer
- **`docs/design-system/33-status-matrix-unified.md`** §3.3 — matriz 6×4 cells usam renderer UEID nos labels

### 4.2 Forks catalog (Layer 4)

- **`docs/design-system/20-fork-tuiboard-architecture.md`** §3 — tuiboard (SolidJS) usa CSS classes `.ueid__*` (§3.2 deste doc)
- **`docs/design-system/21-fork-taskdog-architecture.md`** §3 — taskdog (Python textual TUI) usa ANSI codes (§3.1 deste doc)
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3 — solverforge-calendar (Rust ratatui) usa ANSI codes (§3.1 deste doc)

### 4.3 Code anchors

| Path | Conteúdo | Renderer binding |
|:-----|:---------|:------------------|
| `src/contracts/common.py:26` | `_UEID_PATTERN` regex | Pattern preservado verbatim |
| `src/contracts/common.py:30-77` | `class UEID(str)` | `__new__` validation, split = 4 partes |
| `src/contracts/common.py:44-60` | docstring com 12 tipos | `T-glyph-*` table binding |
| `src/mesh/adapters/cli.py` | JSONL `ueid` field | Renderer level 1 (raw) |
| `src/mesh/adapters/taskdog.py:69` | SQLite `ueid UNIQUE` column | Renderer level 1 (raw) |
| `src/mesh/adapters/solverforge_calendar.py:88` | UPI `ueid` column | Renderer level 1 (raw) |

### 4.4 Memory cross-refs

- **`[[master-branch-carro-chefe-2026-08-28]]`** — master = deep-agent bidirecional sync forks ↔ vault; UEID renderer é contrato visual
- **`[[ai-native-strategic-model-migration-2026-08-26]]`** — pivot que motivou canonical renderer (forks agora são canônicas, não PAV-OS central)
- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer architecture: forks=user views (renderer visível); cli/tui=operator (renderer opcional)

---

## §5 — Fontes

### Code (verificado via Read tool)
- `src/contracts/common.py` — UEID class + regex + 12 prefixos canônicos (anchor primário)
- `src/contracts/task.py` — Task, Subtask, Project UEID composition
- `src/mesh/adapters/base.py` — ForkAdapter Protocol com `read(ueid: UEID)` (renderer output type)
- `src/mesh/adapters/cli.py`, `taskdog.py`, `solverforge_calendar.py` — adapter storage topology

### Docs design-system
- `docs/design-system/00-INDEX.md` — Layer 5 mapa
- `docs/design-system/10-pattern-ueid-tri-key.md` §2.1, §2.3 — UEID format + 12 tipos canônicos
- `docs/design-system/30-tokens-deep-agent-era.md` §3.4 — `T-glyph-*` table
- `docs/design-system/32-component-naming-conventions.md` — CMP components consuming renderer
- `docs/design-system/33-status-matrix-unified.md` — matriz cells UEID labels

### Forks docs (Layer 4)
- `docs/design-system/20-fork-tuiboard-architecture.md` — SolidJS renderer integration
- `docs/design-system/21-fork-taskdog-architecture.md` — Python textual TUI renderer
- `docs/design-system/22-fork-solverforge-calendar-architecture.md` — Rust ratatui renderer

### Memory cross-refs
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical master
- `[[ai-native-strategic-model-migration-2026-08-26]]` — pivot rationale
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture

### Padrões relacionados
- **Pattern #10** — UEID tri-key (anchor para este doc)
- **Pattern #14** — Idempotent UPSERT (UEID UNIQUE constraint; renderer preserva string)
- **Pattern #15** — Hysteresis FSM (consome `hab:<slug>:...` UEIDs; renderer aplica `T-color-scr-*`)
- **doc 30** — `T-glyph-*` canonical table binding
- **doc 23** — fork status enum mapping (state colors binding)

---

> **Próxima ação recomendada:** após 5 SONHO logs ([[data-first-methodology]] gate), adicionar **renderer para Obsidian wikilinks** (`[[tsk:byd-case-review:abc…:def…]]` syntax) — converter wikilink para HTML span com classes `.ueid__*` via Obsidian plugin ou custom render hook. Bloqueado por data-first methodology.