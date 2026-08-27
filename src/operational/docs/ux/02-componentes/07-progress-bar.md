# CMP-007 — progress_bar

**Arquivo fonte:** `src/operational/ui/components.py:192-202` (canônico) e `src/operational/cli/renderers.py:185-196` (variante)
**Função Python:** `progress_bar(value, total, *, width=18, severity="ok", label="") -> Text`
**Propósito:** Barra horizontal de progresso com caracteres `█` (cheio) e `░` (vazio), percent em cor, e label opcional.
**Quando usar:** Para "X de Y" onde Y é a meta e X é o realizado. State Dashboard "Energia 8/10", Daily Report "Hardwork 240/240min".
**Quando NÃO usar:** Para séries temporais (use `sparkline`); para grid estático (use `pomodoros_grid`); para valores únicos sem meta (use `kpi_card`).

## Assinatura

```python
def progress_bar(
    value: float,
    total: float,
    *,
    width: int = 18,
    severity: str = "ok",
    label: str = "",
) -> Text
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `value` | `float` | — | Valor atual, ex: `8` (energia) |
| `total` | `float` | — | Valor máximo, ex: `10` |
| `width` | `int` | `18` | Largura em caracteres (não inclui percent) |
| `severity` | `str` | `"ok"` | Cor da barra + percent |
| `label` | `str` | `""` | Texto após o percent, ex: `"(8/10)"` |

## Saída ASCII

**Caso típico (value=14, total=20, width=18, severity=ok):**

```text
██████████████░░░░  70%  (14/20h estudo)
```

**100% (completo):**

```text
██████████████████  100%  (20/20h estudo)
```

**0% (vazio):**

```text
░░░░░░░░░░░░░░░░░░  0%  (0/20h estudo)
```

**Severity=warn (yellow):**

```text
██████████░░░░░░░░░  50%  (10/20h meta)        ← barra + percent em yellow
```

**Severity=crit (red):**

```text
███░░░░░░░░░░░░░░░░  15%  (3/20h urgente)     ← barra + percent em bold red
```

## Os 2 caracteres

| Char | Unicode | Significado | Cor (resolvida) |
|------|---------|-------------|-----------------|
| `█` | U+2588 (FULL BLOCK) | Fração **completa** | Cor da severity (e.g., `bright_green`) |
| `░` | U+2591 (LIGHT SHADE) | Fração **vazia** | (não colorido) |

**Cálculo do preenchimento:**

```python
pct = max(0.0, min(1.0, value / total))   # clamp em [0, 1]
filled = int(round(pct * width))            # chars `█`
empty = width - filled                      # chars `░`
```

**Percent:**

```python
f"{int(pct * 100):3d}%"   # sempre 3 dígitos + "%", e.g., " 70%", "100%"
```

## Severidades disponíveis

| Severity | Cor (Rich) | Quando usar |
|----------|------------|-------------|
| `ok` | bright_green | No plano ou acima |
| `warn` | yellow | Atenção, abaixo do esperado |
| `crit` | bold red | Crítico, muito abaixo |
| `info` | deep_sky_blue1 | Informativo |
| `muted` | grey58 | Footer, secundário |
| `primary` | cyan | Default neutro |
| `energy` | yellow1 | Métricas de energia |
| `focus` | deep_sky_blue1 | Métricas de foco |
| `hardwork` | green3 | Métricas de trabalho |
| `sleep` | dodger_blue2 | Métricas de sono |

A cor é resolvida via `SEVERITY_COLOR.get(severity, "white")`.
Fallback gracioso se a chave não existe.

## Estados internos

- **`total = 0`:** a função trata com `pct = 0.0` (sem divisão
  por zero). Barra fica 100% vazia (`░░░░...`). **Caller
  responsibility:** verificar `total > 0` antes.
- **`value > total`:** clamp em `pct = 1.0` (100% cheio).
  Ex: 240min realizado de 240min orçado = 100%.
- **`value < 0`:** clamp em `pct = 0.0`. Raro.
- **`width < 5`:** a barra fica minúscula; percent ainda
  aparece. **Mínimo recomendado:** `width=10`.

## Acessibilidade

- **Funciona sem cores?** Sim, **excelente**. `█` e `░` têm
  **densidades muito diferentes** — distinguíveis em qualquer
  terminal, mesmo monocromático. O percent em texto também
  carrega a info.
- **Funciona com TTY 80-col?** Sim; ~30 chars de largura total.
- **Leve para screen reader?** Não, mas o `label` em texto
  (`"(8/10)"`) ajuda — screen reader lê "8 de 10".

## Onde é usado

1. `ui/daily_report.py:181-189` — "⚡ Energia" e "🎯 Foco"
   do Daily Report (severity=ok fixo)
2. `cli/renderers.py:185-196` — versão alternativa com
   parâmetro `color=` (em vez de `severity=`)
3. (potencial) State Dashboard com mais barras (energia, foco,
   sono, Q_HE)

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** `█` e `░` são
  distinguíveis por luminância (cheio = alto contraste, vazio
  = baixo). Funciona bem mesmo daltônico.
- **Texto pode ser mal interpretado em outro contexto:** o
  `label` é livre, mas o caller controla. **Regra:** sempre
  inclua unidade (`"8/10"`, `"240/240min"`, `"70%"`).
- **Layout pode quebrar em terminal narrow:** o componente
  tem `width=18 + "  100%  (label)" = ~32 chars`. Em 60 col,
  ainda cabe. Em 40 col, wrap.

## Variação entre `components.py` e `renderers.py`

| Aspecto | `components.py:192-202` | `renderers.py:185-196` |
|---------|------------------------|-------------------------|
| Param de cor | `severity` | `color` |
| Fallback de cor | `SEVERITY_COLOR.get(severity, "white")` | `_c(color)` (interno) |
| Largura default | 18 | 18 |
| Comportamento | Idêntico | Idêntico |

A diferença é puramente semântica. Use `components.py` para
novo código (consistência com `kpi_card` e `section_panel`).

---

## Onde ler mais

- **Componente irmão `sparkline`** (tendência inline, em vez
  de valor atual) → [`08-sparkline.md`](08-sparkline.md)
- **Componente irmão `kpi_card`** (valor grande + footer, em
  vez de barra) → [`01-kpi-card.md`](01-kpi-card.md)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
