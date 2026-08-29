# 34 — SUPERSEDED Trailer: PAV-OS Era Tokens (2026-08-26 pivot)

> **Categoria:** TOKENS (Layer 5 — Tokens & components, posição #34 — SUPERSEDED trailer)
> **Anchor canônico:** `src/operational/docs/design-system/DESIGN-SYSTEM.md` (PAV-era, 676 LOC, sendo marcado SUPERSEDED)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (PAV-OS, SUPERSEDED, trailer, append-only, PAV kernel, deep-agent, token, regime, fork, palette, PUSH, MAINTAIN, REDUCE, RECOVER)
> **Status:** SUPERSEDED trailer (conteúdo preservado append-only; canonical novo em doc 30/31/32/33)

---

## §1 — Resumo

Este documento é o **trailer SUPERSEDED** do doc PAV-era `src/operational/docs/design-system/DESIGN-SYSTEM.md` (676 LOC), aplicado após o **pivot 2026-08-26** que desativou o **PAV-OS (Produtividade Algorítmica Visual — Operating System)** como marca/design system canônico. PAV-OS foi a primeira encarnação do design system híbrido IKIGAi (2024–2026), quando o PAV kernel (`src/operational/`) era a peça central do sistema e tokens visuais centralizavam em `colors.py` (módulo Python) + tabela markdown de referência. O pivot reconhece que **deep-agent canonical** substituiu PAV como carro-chefe (cross-ref [[master-branch-carro-chefe-2026-08-28]] + [[ai-native-strategic-model-migration-2026-08-26]]), e que **tokens precisam migrar para contracts Pydantic** (cross-ref doc 30) em vez de ficarem centralizados em módulo Python. **Não deletar conteúdo** (invariante append-only do design system — cross-ref [[docs-superseded-trailer-2026-08-28]]); o trailer marca defasagem sem remover história. O conteúdo PAV-era original permanece em `src/operational/docs/design-system/DESIGN-SYSTEM.md` para audit/referência histórica; este doc serve como **migration map** explícita do que sobrevive, do que se torna obsoleto, e do que é PAV-específico (não migrável).

### 1.1 O que é PAV-OS

**PAV-OS** = Produtividade Algorítmica Visual — Operating System. Marca/design system usado entre 2024-01 e 2026-08 para descrever o conjunto integrado:
- **PAV kernel** (`src/operational/`) — backend de produtividade algorítmica (tasks, habits, scoring QHE, policy engine)
- **PAV TUI** (`src/operational/packages/tui/`) — interface terminal Ratatui (Rust)
- **PAV CLI** (`src/operational/packages/cli/`) — comandos Typer (Python)
- **PAV UI tokens** (PROPOSTA: `src/operational/packages/ui/src/operational/ui/colors.py` (path place-holder — module referenced by PAV-era, does not exist in deep-agent canonical; tokens live in markdown + Pydantic contracts)) — centralização de cores em módulo Python
- **PAV docs** (`src/operational/docs/`) — design system + UX research

PAV-OS **não é deletado** (invariante append-only); é **desativado como peça canônica** e substituído por **deep-agent canonical + forks-prontas**.

### 1.2 Por que SUPERSEDED (não DELETE)

3 razões para trailer em vez de delete:

1. **Invariante append-only do design system** — todos os docs em `docs/design-system/` e `src/operational/docs/` são append-only. Trailer é o mecanismo canônico de marcar defasagem (cross-ref [[docs-superseded-trailer-2026-08-28]]).

2. **Audit trail / historical reference** — PAV-OS foi o sistema em produção por 30+ meses. Engineers futuros (ou eu mesmo daqui a 1 ano) precisam entender **por que** as decisões foram tomadas, **o que** foi tentado, e **o que** falhou. Trailer preserva contexto sem alocar como canonical.

3. **Migration reversibility** — se deep-agent canonical mostrar-se inviável em 6-12 meses, PAV-OS pode ser revivido (ou adaptado). Trailer permite "undo" sem reescrever do zero.

### 1.3 Cross-link para canonical novo

**Tokens canônicos em era deep-agent:** `docs/design-system/30-tokens-deep-agent-era.md` (canonical novo — gap #3 fill). UEID visual: `docs/design-system/31-ueid-visual-representation.md` (gap #4 fill). Naming conventions: `docs/design-system/32-component-naming-conventions.md` (gap #7 fill). Status matrix unificada: `docs/design-system/33-status-matrix-unified.md` (consolidação gap #5).

---

## §2 — Inventário

### 2.1 O que SOBREVIVE (reutilizado em era deep-agent)

| Componente PAV-era | Onde é reusado | Doc canonical |
|:-------------------|:---------------|:---------------|
| Princípios de usabilidade (5 canônicos) | `src/operational/docs/ux/00-visao-geral/03-principios-usabilidade.md` | Token enforcement mechanism em doc 30 §1.4 |
| Paleta semântica SCR (PUSH/MAINTAIN/REDUCE/RECOVER) | PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) | Doc 30 §3.1 tabela `T-color-scr-*` |
| Tipografia monospace primary | PROPOSTA: `src/operational/docs/ux/02-componentes/02-tipografia.md` (path place-holder) | Doc 30 §3.2 typography tokens |
| Spacing scale 4/8/16/24/32 | PROPOSTA: `src/operational/docs/ux/02-componentes/03-spacing.md` (path place-holder) | Doc 30 §3.3 spacing tokens |
| Glyph repertoire (UEID prefix + status) | PROPOSTA: `src/operational/docs/ux/02-componentes/04-glifos.md` (path place-holder) | Doc 30 §3.4 + doc 31 §3.2 (split em 2 docs) |
| Component slots (KPI card, Section, Error panel, Timeline, Sparkline) | PROPOSTA: `src/operational/docs/ux/02-componentes/05-componentes-slots.md` (path place-holder) | Doc 30 §3.5 component slots |
| Matriz de estados (PENDING/ACTIVE/DONE/BLOCKED/CANCELLED/ARCHIVED) | `src/operational/docs/ux/01-inventario/02-matriz-estados.md` | Doc 33 §3.1 matriz 6×4 unificada |
| Glossário PAV-era (termos como `Q_HE`, `hardwork`, `pause`) | PROPOSTA: `src/operational/docs/glossary.md` (path place-holder — actual glossary is `src/operational/docs/ux/00-visao-geral/04-glossario-dominio.md`) | Reusado verbatim em deep-agent era |

### 2.2 O que se torna OBSOLETO (não migrado)

| Componente PAV-era | Por que obsoleto |
|:-------------------|:------------------|
| PROPOSTA: `src/operational/packages/ui/src/operational/ui/colors.py` (path place-holder — module referenced by PAV-era, does not exist in deep-agent canonical; tokens live in markdown + Pydantic contracts) | Centralização em Python colors.py; substituído por tokens em doc 30 + implementação local em cada fork |
| PAV TUI/CLI como apps canônicos (Phase 1-2-3 reorg) | Apps deleted intencionalmente em reorg 2026-08-26 (apps/cli, apps/tui removidos); substituído por forks-prontas (tuiboard, taskdog, solverforge-calendar) |
| `pav-os` naming convention (e.g., `pav-os-design-system.md`) | Substituído por `SCR-NNN`/`CMP-NNN`/`T-*` (cross-ref doc 32) |
| `time-tasker → pav migration` references | time-tasker foi precursor pré-2024; pav kernel absorveu; agora PAV desativado → references mortas |
| PAV-era glyphs customizados (e.g., `▰▱`) | Substituídos por Unicode block geometric shapes padronizados (doc 30 §3.4) |

### 2.3 O que é PAV-ESPECÍFICO (não migra)

| Componente | Razão |
|:-----------|:------|
| `pav-os-brand/` (logo, cores de marca PAV) | Marca desativada; IKIGAi é a marca canônica |
| `pav-os-app-store/` listings | Apps em apps/cli, apps/tui deleted; store vazia |
| PAV-era screenshots em `src/operational/docs/ux/screenshots/` | TUI/CLI antigos não rodam mais; screenshots históricos |
| PAV-era release notes (v0.1-v2.4) | Histórico preservado em `CHANGELOG.md` para audit, não canônico |
| PAV-era agent (`pae_maintainer` graph stub) | Cross-ref [[q3-q4-resolved-2026-08-27]] — stub removido; pae_graph real implementado |
| PAV-era `dashboard.json` schema | Substituído por SCR-001 dashboard rendering com tokens canônicos |
| PAV-era 4 state cycle (PUSH/MAINTAIN/REDUCE/RECOVER sem DONE) | Expandido para 6×4 matriz em doc 33 (status orthogonal a regime) |

### 2.4 Origem verbatim

**Path original PAV-era:** `src/operational/docs/design-system/DESIGN-SYSTEM.md:1-50` (primeiras 50 linhas como amostra histórica preservada):

```markdown
# DESIGN-SYSTEM — Sistema de Design PAV-OS

> **Categoria:** DESIGN-SYSTEM (canônico centralizado em colors.py)
> **Público:** time PAV + forks
> **Stack:** Python (colors.py) + CSS variables (web forks) + ANSI codes (TUI)

## §1 — Paleta PAV

A paleta canônica é centralizada em `src/operational/packages/ui/src/operational/ui/colors.py:1-89`:

```python
PAV_PALETTE = {
    "push": "#10b981",       # PUSH regime (green)
    "maintain": "#3b82f6",   # MAINTAIN regime (blue)
    "reduce": "#f59e0b",     # REDUCE regime (orange)
    "recover": "#ef4444",    # RECOVER regime (red)
    "pending": "#94a3b8",    # PENDING status
    "active": "#3b82f6",     # ACTIVE status
    "done": "#10b981",       # DONE status
    "blocked": "#f59e0b",    # BLOCKED status
    "cancelled": "#6b7280",  # CANCELLED status
    "archived": "#9ca3af",   # ARCHIVED status
    "bg_canvas": "#fafafa",  # background
    "fg_primary": "#0d0d0d", # foreground
    ...
}
```

(50 linhas amostradas; total = 676 LOC no arquivo original)
```

---

## §3 — Conteúdo principal

### 3.1 Migration map table (PAV-era concept → deep-agent era concept)

| PAV-era concept | Onde vivia | Deep-agent era equivalent | Doc canonical |
|:----------------|:-----------|:--------------------------|:--------------|
| `PAV_PALETTE["push"]` (hex string em Python dict) | `colors.py:5` | `T-color-scr-push` (token ID em markdown table) | Doc 30 §3.1 |
| `PAV_PALETTE["recover"]` | `colors.py:8` | `T-color-scr-recover` | Doc 30 §3.1 |
| `PAV_PALETTE["bg_canvas"]` | `colors.py:11` | `T-bg-canvas` | Doc 30 §3.1 |
| Regime label "PUSH" | `colors.py` + enums | `RegimeState.PUSH` (Pydantic enum) + `T-color-scr-push` binding | Doc 30 + Pattern #15 §2.1 |
| Status label "DONE" | `TaskStatus.COMPLETED` (taskdog local enum) | `TaskStatus.DONE` (canonical 6-state cycle) | Doc 23 + Pattern #23 |
| 4-state regime cycle | Policy FSM (PUSH/MAINTAIN/REDUCE/RECOVER) | Mesmo cycle, agora **cruzado** com 6-status em matriz 6×4 | Doc 33 §3.1 |
| Glyph `▣` para tasks (PAV-era custom) | `colors.py` glyph map | `T-glyph-tsk` Unicode U+25A3 | Doc 30 §3.4 + doc 31 §1.3 |
| UEID prefix `tsk` (sem glyph) | `Task.id: UEID` field | `T-glyph-tsk + "tsk" + ":" + slug + ":" + uuid + ":" + hash` (full renderer) | Doc 31 §3.1 |
| File naming `01-paleta-cores.md` | PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) | `CMP-001-paleta-cores.md` (canonical) ou seção em doc 30 | Doc 32 §3.4 |
| File naming `FLOW-001-iniciar-manha.md` | Já conforme | Manter como está (já compliant) | Doc 32 §2.3 |
| Hardcoded hex `#10b981` em fork code | `colors.py` import | Fork-local `tokens.ts` / `tokens.rs` / `tokens.css` referencing `T-color-scr-push` | Doc 30 §1.1 |
| `pav-os` brand reference | Marketing/docs | `IKIGAi` brand (canonical) | Cross-ref [[master-branch-carro-chefe-2026-08-28]] |
| Matriz 4×1 (status only) | `02-matriz-estados.md` original | Matriz 6×4 (status × regime) | Doc 33 §3.1 |
| PAV agent `pae_maintainer` (stub) | `langgraph.json` graph | Real `pae_maintainer` graph (Q3 resolved) + `ikigai_maintainer` | Cross-ref [[q3-q4-resolved-2026-08-27]] |
| `colors.py` centralizado em Python | `src/operational/packages/ui/` | Tokens em markdown (doc 30) + local implementation per fork | Doc 30 §1.1 |

### 3.2 Trailer blockquote (template a ser inserido em DESIGN-SYSTEM.md)

**Path do arquivo a receber trailer:** `src/operational/docs/design-system/DESIGN-SYSTEM.md` (linha 1, após título principal)

**Blockquote template:**

```markdown
> **⚠️ SUPERSEDED 2026-08-26** — Este documento é a versão PAV-era do design system,
> pre-pivot deep-agent canonical. **NÃO USAR** para forks ativas ou novos desenvolvimentos.
>
> **Canonical novo (era deep-agent):**
> - `docs/design-system/30-tokens-deep-agent-era.md` — tokens canônicos (paleta, typography, spacing, glyphs, components)
> - `docs/design-system/31-ueid-visual-representation.md` — UEID rendering cross-fork
> - `docs/design-system/32-component-naming-conventions.md` — naming conventions (SCR/FLOW/CMP/KPI/T)
> - `docs/design-system/33-status-matrix-unified.md` — matriz 6×4 (status × regime)
> - `docs/design-system/34-superseded-pav-era-tokens.md` — este trailer
>
> **Migration map completa:** ver `docs/design-system/34-superseded-pav-era-tokens.md` §3.1.
>
> **Razão do SUPERSEDED:** pivot 2026-08-26 desativou PAV-OS como marca/design system canônico;
> deep-agent canonical + forks-prontas (tuiboard/taskdog/solverforge-calendar) substituíram.
> PAV kernel continua rodando como subsystem, mas não é mais canonical.
>
> **Invariante append-only preservada:** conteúdo histórico deste arquivo não foi deletado;
> trailer marca defasagem sem remover história.
```

### 3.3 Migration workflow (append-only)

**Step-by-step para adicionar trailer:**

1. **Não modificar conteúdo existente** do DESIGN-SYSTEM.md (preserva audit trail).
2. **Inserir blockquote** (template §3.2) na linha 1 do arquivo, após o título principal.
3. **Commit:** `chore(design-system): add SUPERSEDED trailer to PAV-era DESIGN-SYSTEM.md (post 2026-08-26 pivot)`.
4. **Atualizar cross-refs** em outros docs do docset (`grep -r "DESIGN-SYSTEM.md"` → adicionar link para doc 34).
5. **Não deletar** o arquivo DESIGN-SYSTEM.md. Conteúdo preserva como histórico.

**Step-by-step para migration de consumers:**

1. Para cada consumer de `colors.py`:
   - Identificar qual `PAV_PALETTE[key]` é usado
   - Mapear para token ID correspondente em doc 30 (cross-ref §3.1 tabela)
   - Substituir import: `from operational.ui.colors import PAV_PALETTE` → fork-local tokens file (CSS/TS/Rust)
2. Para cada componente visual em `01-paleta-cores.md` etc.:
   - Conteúdo migra para doc 30 §3.1-3.5 OU para `CMP-NNN-{name}.md` (canonical)
   - Arquivo original recebe trailer `> SUPERSEDED → {novo path}`
3. Para matriz de estados original (`02-matriz-estados.md`):
   - Conteúdo migra para doc 33 §3.1 (matriz 6×4 unificada)
   - Arquivo original recebe trailer `> SUPERSEDED → docs/design-system/33-status-matrix-unified.md`

### 3.4 Audit checklist (post-migration)

Após migration completa, validar:

- [ ] Nenhum import ativo de PROPOSTA: `src/operational/packages/ui/src/operational/ui/colors.py` (path place-holder — module referenced by PAV-era, does not exist in deep-agent canonical; tokens live in markdown + Pydantic contracts) em forks
- [ ] Nenhum hex literal hardcoded (`#[0-9a-f]{6}`) em fork code fora de `tokens.*` files
- [ ] Todos os consumers de tokens usam fork-local `tokens.ts` / `tokens.rs` / `tokens.css`
- [ ] Token IDs referenciados em código existem em doc 30 §3.1-3.5 (sem IDs órfãos)
- [ ] `02-matriz-estados.md` original tem trailer SUPERSEDED → doc 33
- [ ] `01-paleta-cores.md` a `12-button.md` originais têm trailers SUPERSEDED → CMP-NNN ou doc 30
- [ ] DESIGN-SYSTEM.md original tem trailer SUPERSEDED (template §3.2)
- [ ] CI verifica `grep -r "PAV_PALETTE" src/` retorna 0 hits (apenas comentários históricos permitidos)

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 5 canonical novo)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 5 mapa (este doc é peça de trailer)
- **`docs/design-system/30-tokens-deep-agent-era.md`** — canonical tokens (paleta, typography, spacing, glyphs, components)
- **`docs/design-system/31-ueid-visual-representation.md`** — canonical UEID rendering
- **`docs/design-system/32-component-naming-conventions.md`** — canonical naming conventions
- **`docs/design-system/33-status-matrix-unified.md`** — canonical status × regime matrix

### 4.2 PAV-era docs preservados (append-only)

- **`src/operational/docs/design-system/DESIGN-SYSTEM.md`** — PAV-era design system original (receber trailer §3.2)
- **PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created)** a **`12-button.md`** — 12 components PAV-era (receber trailers → CMP-NNN)
- **`src/operational/docs/ux/01-inventario/02-matriz-estados.md`** — matriz PAV-era (receber trailer → doc 33)
- **PROPOSTA: `src/operational/docs/glossary.md` (path place-holder — actual glossary is `src/operational/docs/ux/00-visao-geral/04-glossario-dominio.md`)** — glossário PAV-era (preservado verbatim, reusado)
- **PROPOSTA: `src/operational/packages/ui/src/operational/ui/colors.py` (path place-holder — module referenced by PAV-era, does not exist in deep-agent canonical; tokens live in markdown + Pydantic contracts)** — centralização PAV-era (NÃO deletar; trailer no header)

### 4.3 Code anchors

| Path | Conteúdo | Status |
|:-----|:---------|:-------|
| `src/operational/packages/ui/src/operational/ui/colors.py:1-89` | `PAV_PALETTE` dict | Obsoleto (canonical migrado para doc 30) |
| `src/operational/docs/design-system/DESIGN-SYSTEM.md:1-676` | PAV-era design system completo | SUPERSEDED (trailer §3.2) |
| `src/contracts/common.py:150-156` | `RegimeState` enum | Canonical cross-ref Pattern #15 |
| `src/contracts/task.py` | `TaskStatus`, `Task.done` | Canonical cross-ref Pattern #23 |

### 4.4 Memory cross-refs

- **`[[master-branch-carro-chefe-2026-08-28]]`** — canonical master = deep-agent; PAV-OS desativado
- **`[[ai-native-strategic-model-migration-2026-08-26]]`** — pivot que motivou SUPERSEDED
- **`[[legacy-pav-ui-era-2026-08-28]]`** — abandoned era: PAV TUI/CLI built-from-scratch; deprecated 2026-08-26
- **`[[pav-as-ikigai-subsystem-2026-08-28]]`** — PAV desativado como subsystem-extension; IKIGAI = canonical
- **`[[docs-superseded-trailer-2026-08-28]]`** — canonical trailer pattern (este doc segue)
- **`[[doc-migration-2026-08-28]]`** — doc migration workflow (mesmo padrão)

---

## §5 — Fontes

### Code (verificado via Read tool)
- `src/operational/docs/design-system/DESIGN-SYSTEM.md:1-50` — primeiras 50 linhas amostradas (origem PAV-era; trailer a inserir)
- `src/operational/packages/ui/src/operational/ui/colors.py:1-89` — `PAV_PALETTE` (origem PAV-era; obsoleto)
- `src/contracts/common.py:150-156` — `RegimeState` enum (canonical cross-ref)
- `src/contracts/task.py` — `TaskStatus`, `Task.done` (canonical cross-ref)

### Docs design-system (canonical novo)
- `docs/design-system/00-INDEX.md` — Layer 5 mapa
- `docs/design-system/30-tokens-deep-agent-era.md` — canonical tokens
- `docs/design-system/31-ueid-visual-representation.md` — canonical UEID rendering
- `docs/design-system/32-component-naming-conventions.md` — canonical naming
- `docs/design-system/33-status-matrix-unified.md` — canonical matrix

### Docs PAV-era (preservados, a receber trailers)
- `src/operational/docs/design-system/DESIGN-SYSTEM.md` — recebe trailer §3.2
- PROPOSTA: `src/operational/docs/ux/02-componentes/01-paleta-cores.md` (path place-holder — gap-fill target, file not yet created) a `12-button.md` — recebem trailers → CMP-NNN
- `src/operational/docs/ux/01-inventario/02-matriz-estados.md` — recebe trailer → doc 33
- PROPOSTA: `src/operational/packages/ui/src/operational/ui/colors.py` (path place-holder — module referenced by PAV-era, does not exist in deep-agent canonical; tokens live in markdown + Pydantic contracts) — recebe trailer no header Python

### Memory cross-refs
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical master
- `[[ai-native-strategic-model-migration-2026-08-26]]` — pivot rationale
- `[[legacy-pav-ui-era-2026-08-28]]` — abandoned era
- `[[pav-as-ikigai-subsystem-2026-08-28]]` — PAV as subsystem
- `[[docs-superseded-trailer-2026-08-28]]` — trailer pattern canonical
- `[[doc-migration-2026-08-28]]` — migration workflow

### ADR / BRD / PRD (PAV-era)
- `code-docs/BRDs/BRD-001-pav-os.md` (se existir) — adicionar trailer pointer
- `code-docs/ADRs/ADR-001-deep-agent-canonical.md` (se existir) — anchor para este doc

---

> **Próxima ação recomendada:** aplicar trailer blockquote (§3.2) ao `src/operational/docs/design-system/DESIGN-SYSTEM.md` linha 1, sem modificar conteúdo existente. Não deletar arquivo. Bloqueado por data-first methodology (5 SONHO logs gate de ADR-007) para qualquer migration ativa de consumers; trailer em si é append-only e pode ser aplicado imediatamente.