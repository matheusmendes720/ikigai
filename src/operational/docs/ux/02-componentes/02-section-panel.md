# CMP-002 — section_panel

**Arquivo fonte:** `src/operational/ui/components.py:364-378`
**Função Python:** `section_panel(title, body, *, color="primary") -> Panel`
**Propósito:** Painel com **título colorido** no header e **corpo renderizável** (qualquer `RenderableType`). É o "container" que estrutura os relatórios: cada seção do Daily Report é um `section_panel`.
**Quando usar:** Sempre que quiser agrupar conteúdo sob um cabeçalho semântico (EASE, HARDWORK, OKRs, etc.).
**Quando NÃO usar:** Para o cabeçalho principal do relatório (use `section_header` de `cli/renderers.py:167-177`, que é uma linha única).

## Assinatura

```python
def section_panel(
    title: str,
    body: RenderableType,
    *,
    color: str = "primary",
) -> Panel
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `title` | `str` | — | Texto do header, ex: `"😴 EASE"` |
| `body` | `RenderableType` | — | Qualquer renderable Rich: `Table`, `Text`, `Group`, `Panel` |
| `color` | `str` | `"primary"` | Key de `COLORS`; define cor do título e da borda |

## Saída ASCII

```text
╭─  🟢 EASE  ────────────────────────────────────────────────────╮
│  ⏰ Acordou        04:00                                          │
│  🌙 Dormiu         20:30                                          │
│  😴 Sono           7.5h 🟢 bom                                    │
│  ⭐ Qualidade      9/10                                           │
│  💪 Workout        10min ✓                                        │
╰──────────────────────────────────────────────────────────────────╯
```

**Versão com `Table.grid` no body:**

```text
╭─  💻 HARDWORK  ────────────────────────────────────────────────╮
│  Tipo de Dia       CURSO                                          │
│  📊 Orçado         240min (4h00m)                                 │
│  ⏱️  Realizado     240min (4h00m)                                 │
│  Δ Desvio          0min (DENTRO)                                   │
╰──────────────────────────────────────────────────────────────────╯
```

## Severidades disponíveis

Mesma paleta do `kpi_card` (12 chaves de `COLORS`).

| Severidade | Uso típico no `section_panel` |
|---|---|
| `primary` | Header principal, cartesiano |
| `sleep` | EASE, sono |
| `hardwork` | HARDWORK, blocos, pomodoros |
| `ease` | OKRs, reflexão |
| `energy` | Estado subjetivo |
| `warn` | Desvios / ajustes / lições |
| `crit` | Erros (raro) |

**Convenção de design:** o `color` do `section_panel` é o mesmo
do **tema** da seção. EASE sempre `sleep`, HARDWORK sempre
`hardwork`, OKRs sempre `ease`. Isso cria **chunking visual**:
o usuário sabe o tema pela cor, sem ler o título.

## Estados internos

- **Vazio (body vazio):** o caller passa `body=Text("(sem dados)",
  style="muted")` ou simplesmente não inclui a seção no Group.
- **1 item / N itens:** o `body` aceita qualquer complexidade;
  o painel não impõe limite.
- **Body muito longo:** o `Panel` não pagina. Em relatórios
  diários, o body de uma seção raramente excede 20 linhas.
  Se exceder, considere dividir em 2 painéis.

## Acessibilidade

- **Funciona sem cores?** Sim, parcialmente. O título fica
  branco, a borda fica branca (sem cor), mas o conteúdo
  interno (que tem suas próprias cores) ainda é visível.
- **Funciona com TTY 80-col?** Sim. O `Panel` se adapta à
  largura do console (que é 120 por padrão, mas cai para 80
  se o terminal for narrow).
- **Leve para screen reader?** Não. `Panel` não tem semântica
  ARIA. O screen reader lê o conteúdo, mas não anuncia "seção:
  EASE".

## Onde é usado

1. `ui/daily_report.py:285-315` — 5+ seções do Daily Report
   (header, EASE, HARDWORK, Pomodoros Grid, Estado Subjetivo,
   Cartesiano, Desvios, OKRs, Next Step)
2. `cli/commands/state_cmd.py:227-247` — Pomodoros Grid e
   Time Blocks panels
3. `cli/commands/report_cmd.py:177-313` — 7 seções do Weekly
   Report
4. `cli/commands/doctor_cmd.py:245-249` — Painel "DOCTOR -
   OK/ISSUES"
5. `ui/components.py` (recursivo) — `next_step_panel` é um
   caso especial de section_panel com layout específico

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** `sleep`
  (dodger_blue2) e `hardwork` (green3) são distinguíveis para
  a maioria, mas em baixa luminosidade podem parecer o mesmo
  tom. **Mitigação:** incluir emoji no título (😴 para sleep,
  💻 para hardwork) garante distinção sem depender só de cor.
- **Texto pode ser mal interpretado em outro contexto:** o
  título "EASE" pode ser confundido com "Ease of use". Em
  PT-BR, a sigla PAV para "EASE" não é óbvia. **Mitigação:**
  ver [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#ease).
- **Layout pode quebrar em terminal narrow:** o `Panel` faz
  wrap, mas se o body tem `Table.grid(expand=False)` com
  colunas fixas largas, o wrap pode ficar feio. **Mitigação:**
  priorizar `expand=False` no `Table.grid`.

---

## Onde ler mais

- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
- **Componente irmão `next_step_panel`** (caso especial
  de seção de recomendação) → [`03-next-step-panel.md`](03-next-step-panel.md)
- **Variação `section_header`** (uma linha, sem painel) →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
