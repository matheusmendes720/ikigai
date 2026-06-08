# CMP-010 — severity_text

**Arquivo fonte:** `src/operational/ui/components.py:330-333`
**Função Python:** `severity_text(value, severity) -> Text`
**Propósito:** Wrapper **mínimo** que aplica cor de severity a uma string. É o helper de baixo nível usado por TODA função que quer colorir um valor sem construir um `Text` à mão.
**Quando usar:** Em `Table.grid` ou `Table` regular quando você quer uma célula colorida inline (sem `kpi_card` nem `metric_table`).
**Quando NÃO usar:** Quando você quer um painel com border (use `section_panel`); quando você quer 1 métrica em destaque (use `kpi_card`).

## Assinatura

```python
def severity_text(value: str, severity: str | None) -> Text
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `value` | `str` | — | A string a colorir |
| `severity` | `str \| None` | — | Chave de `SEVERITY_COLOR`; `None` = branco |

## Saída

O retorno é um `Text` (objeto Rich), não uma string. Ele é
usado dentro de `Table.add_row()`, `Grid.add_row()`, ou
`Text.append()`.

**Exemplo de uso:**

```python
# Dentro de build_ease_table (ui/daily_report.py:91-95)
def row(label: str, value: str, sev: str | None) -> None:
    grid.add_row(
        Text(label, style="bold white"),
        severity_text(value, sev),
    )

row("😴 Sono", f"{hours:.1f}h", "ok")     # value em bright_green
row("😴 Sono", f"{hours:.1f}h", "warn")   # value em yellow
row("😴 Sono", f"{hours:.1f}h", "crit")   # value em bold red
row("😴 Sono", f"{hours:.1f}h", None)     # value em white
```

**Renderização inline:**

```text
  ⏰ Acordou        04:00           ← "04:00" em white (severity="ok")
  😴 Sono           7.5h            ← "7.5h" em bright_green (severity="ok")
  ⭐ Qualidade      9/10            ← "9/10" em bright_green (severity="ok")
  💪 Workout        10min ✓         ← "10min ✓" em bright_green
  🍽️  Lunch         5min + 30min   ← "5min + 30min" em yellow (severity="warn")
```

## As 6+1 severities

| Severity | Cor | Quando usar |
|----------|-----|-------------|
| `ok` | bright_green | Sucesso, dentro do plano |
| `warn` | yellow | Atenção, no limite |
| `crit` | bold red | Crítico, fora do plano |
| `info` | deep_sky_blue1 | Informativo, neutro |
| `muted` | grey58 | Footer, secundário |
| `primary` | cyan | Títulos, marca |
| `None` | white | Sem cor (fallback) |

A cor resolve via `SEVERITY_COLOR.get(severity, "white")`. Se
a chave não existe, cai em `"white"` (fallback gracioso).

## Por que `severity_text` é importante

Sem ele, o caller teria que fazer:

```python
# Sem severity_text (ruim):
color = SEVERITY_COLOR.get(sev, "white")
return Text(value, style=color)

# Com severity_text (bom):
return severity_text(value, sev)
```

A função encapsula o fallback e torna o caller mais limpo. É
usada em **dezenas de lugares** no `daily_report.py`.

## Estados internos

- **`severity = None`:** retorna `Text(value, style="white")`.
  Equivalente a "sem cor especial".
- **`severity` inválida** (não está em `SEVERITY_COLOR`):
  fallback para `"white"`. Caller responsibility: usar chaves
  válidas.
- **String vazia (`""`):** `severity_text("", "ok")` retorna
  `Text("", style="bright_green")` — string vazia, inofensivo.

## Acessibilidade

- **Funciona sem cores?** **Sim** — o `value` permanece como
  string, só a cor some. **Decisão:** `severity_text` é
  seguro em no-color mode.
- **Funciona com TTY 80-col?** Sim; é inline, sem painel.
- **Leve para screen reader?** Sim (o screen reader lê o
  `value` como string normal).

## Onde é usado

1. `ui/daily_report.py:91-95` — `build_ease_table`,
   `build_hardwork_table` (cada row tem um value colorido)
2. `ui/daily_report.py:152-156` — `build_hardwork_table`
   (row do "Δ Desvio")
3. `cli/commands/report_cmd.py:291-292` — "Distribuição do
   Sono" (6 valores com severity)
4. Espalhado em 5+ outras funções do UI

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** o padrão
  `ok`/`warn`/`crit` é universal. **Decisão:** `severity_text`
  é robusto.
- **Texto pode ser mal interpretado em outro contexto:** o
  `value` é livre. **Regra:** inclua unidade
  (`"7.5h"` em vez de `"7.5"`).
- **Layout pode quebrar em terminal narrow:** o `Text` é
  inline, sem border. Não tem risco de quebra.

## Diferença para outras formas de colorir

| Forma | Quando usar |
|-------|-------------|
| `Text(value, style="...")` | Construtor cru; use quando precisa compor múltiplos estilos |
| `severity_text(value, sev)` | Quando você tem uma `severity` (enum) |
| `kpi_card(...)` | Quando quer 1 valor grande em painel |
| `severity` em `metric_table` | Quando quer valor colorido em tabela |

**Regra:** prefira `severity_text` em vez de construir
`Text(value, style=...)` à mão — é mais consistente.

---

## Onde ler mais

- **Catálogo de severities completo** →
  [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#severity-primary-ok-warn-crit-info-muted)
- **Componente irmão `kpi_card`** (valor grande em painel) →
  [`01-kpi-card.md`](01-kpi-card.md)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
