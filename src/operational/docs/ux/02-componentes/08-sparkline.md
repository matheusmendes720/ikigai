# CMP-008 — sparkline

**Arquivo fonte:** `src/operational/ui/components.py:205-219` (canônico) e `src/operational/cli/renderers.py:360-384` (variante com resampling)
**Função Python:** `sparkline(values, *, color="primary", label="") -> Text`
**Propósito:** Tendência **inline** (1 linha, N valores) usando os 8 caracteres de bloco Unicode `▁▂▃▄▅▆▇█`. Cada char representa 1 valor normalizado no range [min, max] dos valores.
**Quando usar:** Weekly Report (sono 7d, produtividade 7d, pomodoros 7d), State Dashboard (trendline inline).
**Quando NÃO usar:** Para valor atual isolado (use `kpi_card` ou `progress_bar`); para grid estático (use `pomodoros_grid`); para séries com gaps temporais (resample pode distorcer).

## Assinatura

```python
def sparkline(
    values: Sequence[float],
    *,
    color: str = "primary",
    label: str = "",
) -> Text
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `values` | `Sequence[float]` | — | Lista de valores numéricos (e.g., 7 floats = 7 dias) |
| `color` | `str` | `"primary"` | Key de `COLORS`; cor dos chars |
| `label` | `str` | `""` | Texto após a sparkline, ex: `"min 4h / max 8h"` |

## Saída ASCII

**7 valores crescentes (tendência positiva):**

```text
  ▁▂▃▄▅▆▇█  sono 7d
```

**7 valores decrescentes (tendência negativa):**

```text
  █▇▆▅▄▃▂▁  produtividade 7d
```

**7 valores com alta variação (V shape):**

```text
  ▁▅▇▅▂▁▂  sono 7d
```

**Lista vazia (sem dados):**

```text
  (sem dados)
```

**Exemplo real (Weekly Report com 7 dias de sono):**

```text
  😴 Sono           ▃▅▂▁▃█▅   min 4h / max 8h
  📈 Produtividade  ▅▄▃▃▅▆▆   média 75%
  🍅 Pomodoros      █▅▃▃▅▆▆   total 45
```

## Os 8 caracteres Unicode

| Char | Unicode | Nome | Nível (0-7) |
|------|---------|------|-------------|
| `▁` | U+2581 | LOWER ONE EIGHTH BLOCK | 0 (mínimo) |
| `▂` | U+2582 | LOWER ONE QUARTER BLOCK | 1 |
| `▃` | U+2583 | LOWER THREE EIGHTHS BLOCK | 2 |
| `▄` | U+2584 | LOWER HALF BLOCK | 3 |
| `▅` | U+2585 | LOWER FIVE EIGHTHS BLOCK | 4 |
| `▆` | U+2586 | LOWER THREE QUARTERS BLOCK | 5 |
| `▇` | U+2587 | LOWER SEVEN EIGHTHS BLOCK | 6 |
| `█` | U+2588 | FULL BLOCK | 7 (máximo) |

**Por que 8 níveis?**

- **Menos que 8** (e.g., 4) perde precisão visual — você não
  distingue "pouco acima da média" de "muito acima".
- **Mais que 8** (e.g., 16) vira ilegível em terminais 1×
  (cada bloco seria 1 linha, e o alinhamento vertical vira
  difícil de ler).
- **8 é o sweet spot** testado pela comunidade de TUIs.

## Algoritmo de mapeamento

```python
chars = "▁▂▃▄▅▆▇█"
lo = min(values)
hi = max(values)
span = max(1e-9, hi - lo)   # evita divisão por zero

for v in values:
    idx = int((v - lo) / span * (len(chars) - 1))
    # idx ∈ {0, 1, 2, 3, 4, 5, 6, 7}
    text.append(chars[idx], style=COLORS.get(color, color))
```

**Cuidado:** o sparkline **normaliza** para o range [min, max]
dos próprios valores. Se os valores são [4, 8] (sono em horas),
a sparkline mostra `▁█` (4 chars), mas se são [4, 4.5] (variação
pequena), ela mostra `▁█` igualmente — a **forma** é
preservada, mas a **escala absoluta** é perdida.

**Para contexto:** sempre inclua um `label` com min/max
(`"min 4h / max 8h"`).

## Severidades disponíveis

| Cor | Uso típico |
|-----|-----------|
| `primary` (cyan) | Default |
| `sleep` (dodger_blue2) | Tendência de sono |
| `hardwork` (green3) | Tendência de produtividade/pomodoros |
| `energy` (yellow1) | Tendência de energia |
| `focus` (deep_sky_blue1) | Tendência de foco |
| `ok` / `warn` / `crit` | Para sparklines com tom (raro) |

A cor é resolvida via `COLORS.get(color, color)`. Sparklines
de grandezas diferentes devem ter cores diferentes para não
confundir o usuário.

## Estados internos

- **Lista vazia (`values = []`):** retorna `Text("  (sem dados)",
  style="grey58")` — placeholder amigável.
- **1 valor (`values = [5]`):** `lo=hi=5`, `span=1e-9`. Para
  qualquer `v=5`, `idx = int(0/1e-9 × 7) = 0`. Resultado:
  `▁`. **Limitação:** sparkline com 1 valor é `▁`, não `█`
  (porque `v - lo = 0`). **Workaround:** caller passa 2+
  valores ou aceita `▁` como "1 ponto, sem tendência".
- **Todos os valores iguais (`values = [5, 5, 5]`):** mesmo
  caso acima. `lo=hi=5`, todos viram `▁`.
- **Valley/Peak com outlier:** se 6 valores são 5-7 e 1 valor é
  100, a sparkline mostra `▁▁▁▁▁▁▁█` — o outlier domina.
  **Mitigação:** caller pode pré-processar (clamp, winsorize).

## Acessibilidade

- **Funciona sem cores?** **Sim, excelente.** Os 8 níveis de
  bloco são **densidade visual**, não cor. Mesmo em terminal
  monocromático, a sparkline `▁▂▃▄▅▆▇█` é **perfeitamente
  legível** — a altura do bloco codifica o valor. **Decisão
  de design:** o sparkline é **robusto sem cor**.
- **Funciona com TTY 80-col?** Sim; 1 linha, ~10-15 chars.
- **Leve para screen reader?** Não. Screen reader lê "lower
  one eighth block, lower one quarter block, ..." — sem
  semântica de tendência.

## Onde é usado

1. `cli/commands/report_cmd.py:202-204` — Weekly Report
   (3 sparklines: Sono, Produtividade, Pomodoros)
2. `ui/components.py:205-219` — definição canônica
3. `cli/renderers.py:360-384` — versão com resampling
   (interpola para N valores)

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** a tendência
  é carregada pelos **chars**, não pela cor. Daltônicos leem
  a sparkline tão bem quanto não-daltônicos. **Decisão:** o
  sparkline é o componente **mais acessível** do CLI.
- **Texto pode ser mal interpretado em outro contexto:** o
  `label` deve explicitar o range (`"min 4h / max 8h"`).
  Sem label, a sparkline é ambígua.
- **Layout pode quebrar em terminal narrow:** a sparkline é
  compacta (1 linha). Risco zero de quebra.
- **Outliers dominam:** se 1 valor é 100x maior que os outros,
  a sparkline vira "1 pico + linha de base". **Mitigação:**
  caller deve winsorizar ou documentar.

## Variação entre `components.py` e `renderers.py`

| Aspecto | `components.py:205-219` | `renderers.py:360-384` |
|---------|------------------------|-------------------------|
| Param de cor | `color` | `color` (igual) |
| Resampling | Não | Sim (`_resample` se `len != width`) |
| Largura | Implícita (1 char por valor) | Configurável (`width=`) |
| Comportamento | 1 char por valor | N chars, com média por bin |

A versão com resampling é útil quando você tem **mais valores
que espaço** (e.g., 30 dias em 7 chars). Usa média por bin.
**Recomendação:** use `components.py` para 7 valores típicos
(semana); use `renderers.py` para séries longas com resampling.

---

## Onde ler mais

- **Componente irmão `progress_bar`** (valor atual com meta) →
  [`07-progress-bar.md`](07-progress-bar.md)
- **Onde o sparkline aparece no Weekly Report** →
  [`../01-inventario/01-telas-inventario.md`](../01-inventario/01-telas-inventario.md#scr-003--weekly-report)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
