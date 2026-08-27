# CMP-009 — metric_table

**Arquivo fonte:** `src/operational/cli/renderers.py:406-433`
**Função Python:** `metric_table(title, rows, *, title_color="primary", show_header=True) -> Table`
**Propósito:** Tabela **colorida** de métricas em 2 colunas (`Métrica` | `Valor`) com severity por linha. É a alternativa "compacta" ao `kpi_card` para listas de KPIs.
**Quando usar:** Para listar 3-7 métricas relacionadas (distribuição do sono, atividade do dia). State Dashboard "Atividade do Dia", Weekly Report "Distribuição do Sono".
**Quando NÃO usar:** Para 1 métrica isolada (use `kpi_card`); para série temporal (use `sparkline`); para CRUD tabular de entidades (use `Table` direto).

## Assinatura

```python
def metric_table(
    title: str,
    rows: Sequence[tuple[str, str, str | None]],
    *,
    title_color: str = "primary",
    show_header: bool = True,
) -> Table
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `title` | `str` | — | Título da tabela, ex: `"😴 Distribuição do Sono (7 dias)"` |
| `rows` | `Sequence[(label, value, severity)]` | — | Lista de tuplas; `severity` pode ser `None` para linha sem cor |
| `title_color` | `str` | `"primary"` | Cor do título (resolve via `COLORS`) |
| `show_header` | `bool` | `True` | Mostra cabeçalho "Métrica \| Valor" |

## Saída ASCII

**Caso típico (Dist. do Sono, 6 linhas):**

```text
  😴 Distribuição do Sono (7 dias)
╭──────────────────────┬────────────╮
│ Métrica              │ Valor      │
├──────────────────────┼────────────┤
│ Média                │ 7.2h       │
│ Mínimo               │ 5.8h       │  (yellow)
│ Máximo               │ 8.5h       │  (bright_green)
│ Noites < 6h          │ 1          │  (bold red)
╰──────────────────────┴────────────╯
```

**Versão sem header (show_header=False):**

```text
  ⚡ Atividade do Dia
╭──────────────────────┬────────────╮
│ 🕐 Rotinas logs      │ 8          │  (bright_green)
│ 🔧 Ajustes finos     │ 1          │  (bright_green)
│ 📓 Journal           │ ✓          │  (bright_green)
│ 📦 Blocos            │ 5          │  (bright_green)
╰──────────────────────┴────────────╯
```

## Os 3 elementos de uma `row`

Cada `row` é uma tupla `(label, value, severity)`:

```python
rows = [
    ("Média", "7.2h", "ok"),       # valor verde
    ("Mínimo", "5.8h", "warn"),    # valor amarelo
    ("Máximo", "8.5h", "ok"),      # valor verde
    ("Noites < 6h", "1", "crit"),  # valor vermelho
]
```

- `label`: texto bold white, justificado à esquerda
  (min_width=22, no_wrap=True).
- `value`: texto com a cor da `severity`. Se `severity` é
  `None`, fica branco (sem cor).
- `severity`: chave de `SEVERITY_COLOR` ou `None`.

## Severidades disponíveis

A severity é resolvida via `COLORS.get(severity or "", "white")`.
Para `None` ou string vazia, a cor é branca.

| Severity | Cor | Quando usar |
|----------|-----|-------------|
| `ok` | bright_green | Dentro do esperado |
| `warn` | yellow | Atenção |
| `crit` | bold red | Crítico |
| `info` | deep_sky_blue1 | Informativo |
| `muted` | grey58 | Footer, secundário |
| `None` | white | Sem cor (neutro) |

## Estados internos

- **Lista vazia (`rows = []`):** tabela com header mas sem
  dados. Caller responsibility: verificar `len(rows) > 0`.
- **1 linha:** funciona, mas `metric_table` com 1 linha é
  overkill — use `kpi_card` ou `severity_text` inline.
- **N linhas:** suporta qualquer N. Acima de 10, fica denso;
  caller deve considerar paginação.
- **`show_header=False`:** omite "Métrica | Valor" no topo.
  Útil quando o `title` já descreve o conteúdo (ex:
  "Atividade do Dia").

## Acessibilidade

- **Funciona sem cores?** **Parcialmente.** As cores do
  `value` somem em no-color mode, mas o `label` em bold
  white e o `value` em plain text permanecem. A
  distinção "Mínimo: 5.8h" vs "Máximo: 8.5h" ainda é
  clara pelo número.
- **Funciona com TTY 80-col?** Sim; cada linha tem ~30 chars.
- **Leve para screen reader?** Não, mas o `label` + `value`
  como colunas separadas facilitam a leitura sequencial.

## Onde é usado

1. `cli/commands/state_cmd.py:257` — "Atividade do Dia"
   (4 linhas: rotinas logs, ajustes, journal, blocos)
2. `cli/commands/report_cmd.py:280-293` — "Distribuição do
   Sono (7 dias)" (6 linhas: média, mín, máx, dias < 6h,
   dias 7-9h, dias > 9h)
3. (potencial) Policy decisions summary, Habit summary

## Riscos de usabilidade

- **Cores podem ser confundas para daltônicos:** o padrão
  `ok` (verde) / `warn` (amarelo) / `crit` (vermelho) é
  universal. Funciona bem.
- **Texto pode ser mal interpretado em outro contexto:** o
  `label` é livre. **Regra:** primeira letra maiúscula,
  sem abreviações obscuras.
- **Layout pode quebrar em terminal narrow:** `label` tem
  `min_width=22, no_wrap=True` — em 60 col, pode wrap.
  **Mitigação:** aceitar `min_width` parametrizado (gap
  atual).

## Diferença para `kpi_card`

| Aspecto | `kpi_card` | `metric_table` |
|---------|-----------|----------------|
| Densidade | 1 métrica por card | N métricas em 1 tabela |
| Visual | Card com border | Table com border |
| Footer descritivo | Sim (1 linha) | Não |
| Severity por linha | 1 (a do card) | 1 (a da row) |
| Quando usar | Métrica **isolada** com contexto rico | Lista de métricas **comparáveis** |

**Regra de bolso:** se você tem **1 métrica importante** com
footer, use `kpi_card`. Se tem **3+ métricas relacionadas** com
severity, use `metric_table`.

---

## Onde ler mais

- **Componente irmão `kpi_card`** (1 métrica, com footer) →
  [`01-kpi-card.md`](01-kpi-card.md)
- **Componente irmão `severity_text`** (1 valor colorido,
  sem painel) → [`10-severity-text.md`](10-severity-text.md)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
