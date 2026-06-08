# CMP-001 — kpi_card

**Arquivo fonte:** `src/operational/ui/components.py:341-361` (canônico) e `src/operational/cli/renderers.py:135-159` (variante)
**Função Python:** `kpi_card(title, value, *, color="primary", footer="", icon="", width=28) -> Panel`
**Propósito:** Card de KPI com **título colorido**, **valor grande** em branco, e **footer descritivo** em cinza italic. É o building block dos dashboards 2x2 (state, weekly).
**Quando usar:** Quando você quer destacar 1 número/métrica em um card. State Dashboard tem 4 cards (Sono, Pomodoros, Hardwork, Energia/Foco). Weekly Report tem 4 cards.
**Quando NÃO usar:** Quando o valor é parte de uma série (use `metric_table`); quando o valor muda a cada linha (use `severity_text` inline).

## Assinatura

```python
def kpi_card(
    title: str,
    value: str,
    *,
    color: str = "primary",
    footer: str = "",
    icon: str = "",
    width: int = 28,
) -> Panel
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `title` | `str` | — | Label curto, ex: `"Energia"` |
| `value` | `str` | — | O número grande, ex: `"8 / 10"` |
| `color` | `str` | `"primary"` | Key de `COLORS` (cyan) |
| `footer` | `str` | `""` | Sub-texto italic dim, ex: `"+1 vs ontem"` |
| `icon` | `str` | `""` | Emoji líder, ex: `"⚡"` |
| `width` | `int` | `28` (canonical) / `22` (renderer) | Largura fixa do painel |

## Saída ASCII

```text
╭──────────────────────────╮
│  ⚡  Energia              │
│                            │
│  8 / 10                    │
│                            │
│  +1 vs ontem               │
╰──────────────────────────╯
```

**Versão sem ícone:**

```text
╭──────────────────────────╮
│  Pomodoros                │
│                            │
│  11                        │
│                            │
│  completos hoje            │
╰──────────────────────────╯
```

## Severidades disponíveis

| Severidade | Cor (Rich) | Quando usar |
|---|---|---|
| `primary` | cyan | Títulos, marca |
| `ok` | bright_green | Sucesso, dentro do plano |
| `warn` | yellow | Atenção, no limite |
| `crit` | bold red | Crítico, fora do plano |
| `info` | deep_sky_blue1 | Informativo, neutro |
| `muted` | grey58 | Footer, secundário |
| `sleep` | dodger_blue2 | Métricas de sono |
| `hardwork` | green3 | Métricas de trabalho |
| `ease` | magenta | Métricas de recuperação |
| `energy` | yellow1 | Métricas de energia |
| `focus` | deep_sky_blue1 | Métricas de foco |

A cor **resolve** via `COLORS.get(color, color)` (fallback
graceful se a chave não existe). Se você passar uma cor Rich
crua (ex: `"lightgreen"`), ela funciona; mas usar a chave
semântica é mais consistente.

## Estados internos

- **Vazio (sem dados):** o caller passa `value="—"` e
  `footer="não registrado"`, com `color="crit"` ou `muted`.
- **1 item:** o caso normal.
- **N itens:** cada KPI é independente; sem paginação.
- **Erro de dados:** se a cor é `crit` mas o valor é "0", o
  card mostra "0 / 10" em vermelho, o que pode confundir (é
  zero ou é crítico?). **Decisão atual:** caller decide a cor
  baseado no contexto, não no valor.

## Acessibilidade

- **Funciona sem cores?** Sim, parcialmente. O `value` em
  bold white é sempre visível; só a cor da borda some. O
  título e o footer também ficam visíveis (branco/cinza).
- **Funciona com TTY 80-col?** Sim, com `width=22` (renderer)
  ou `width=28` (canonical) — 2 cards em 80 col cabem
  apertado. 4 cards em 80 col **não** cabem; usa-se `width=30`
  e 120-col.
- **Leve para screen reader?** Não testado. A estrutura é
  `Panel` (sem semântica explícita), e o `Text` interno
  concatena com `append` (sem `aria-label`).

## Onde é usado

1. `cli/commands/state_cmd.py:166-200` — 4 cards no State
   Dashboard (Sono, Pomodoros, Hardwork, Energia/Foco)
2. `cli/commands/report_cmd.py:180-188` — 4 cards no Weekly
   Report (Hardwork, Pomodoros, Sono Médio, Reflexões)
3. `cli/commands/policy_cmd.py` — variação para mostrar
   setpoints do regime
4. `ui/daily_report.py` (potencial) — para o Daily Report
   V4 (refator planejada)

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** o `ok`/`warn`/
  `crit` segue convenção universal, mas a diferença entre
  `sleep` (azul) e `focus` (deep_sky_blue1) é quase
  imperceptível para daltônicos. **Mitigação:** sempre
  incluir o `icon` para distinguir.
- **Texto pode ser mal interpretado em outro contexto:** o
  footer "8/10" pode ser "8 de 10" (energia) ou "8 minutos
  de 10" (duração). Sempre use unidades explícitas
  ("Q=8/10", "8min/10min").
- **Layout pode quebrar em terminal narrow:** `width=28` é
  fixo. Em 80-col com 2 cards, fica apertado (sobra 24 col
  que é pouco para conteúdo + padding). **Mitigação:** use
  `width=22` (renderer) para 80-col, ou empilhe vertical em
  vez de 2x2.

## Variação entre `components.py` e `renderers.py`

| Aspecto | `components.py:341-361` | `renderers.py:135-159` |
|---------|------------------------|-------------------------|
| Default `width` | 28 | 22 |
| Ícone | Opcional, no `body` | No início, separado por `\n` |
| `box` | `SIMPLE_HEAD` | `SIMPLE_HEAD` |
| Usado por | (potencial) | State Dashboard, Weekly Report |

A diferença é puramente visual; o contrato é o mesmo. Use
`components.py` para novo código; `renderers.py` é legacy.

---

## Onde ler mais

- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
- **Paleta de cores (COLORS dict)** →
  [`../../tui/04-COLOR-PALETTE.md`](../../tui/04-COLOR-PALETTE.md)
- **Componente irmão `metric_table`** (alternativa para
  listas de KPIs) → [`09-metric-table.md`](09-metric-table.md)
