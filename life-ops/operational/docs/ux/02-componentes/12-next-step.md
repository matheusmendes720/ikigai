# CMP-012 — next_step

**Arquivo fonte:** `src/operational/cli/renderers.py:468-478`
**Função Python:** `next_step(text, *, color="ok", icon="→") -> Panel`
**Propósito:** Variante "irmã" do `next_step_panel` (`ui/components.py:381-387`). **Mesma visual**, **parâmetro `color=` em vez de `severity=`**. Existe por motivos históricos (v3 report renderers foram escritos antes da consolidação em `ui/components.py`).
**Quando usar:** Em código que vive em `cli/renderers.py` ou em código que prefere o nome `color=` (mais natural para o vocabulário de paleta).
**Quando NÃO usar:** Em código novo que vive em `ui/components.py` — use `next_step_panel` (consistência).

## Assinatura

```python
def next_step(
    text: str,
    *,
    color: str = "ok",
    icon: str = "→",
) -> Panel
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `text` | `str` | — | A recomendação em 1-2 frases |
| `color` | `str` | `"ok"` | Chave de `COLORS` (não `SEVERITY_COLOR`) |
| `icon` | `str` | `"→"` | Emoji/glyphe líder |

## Saída ASCII

**Idêntica a `next_step_panel`** — ver [`03-next-step-panel.md`](03-next-step-panel.md).

```text
╭─────────────────────────────────────────╮
│  ✓  Dia dentro do padrão ouro. Manter.  │
╰─────────────────────────────────────────╯
```

## Por que 2 componentes fazem a mesma coisa?

História:
1. O `next_step` foi criado em `cli/renderers.py` durante o
   v3 report workstream.
2. O `next_step_panel` foi criado em `ui/components.py`
   durante a consolidação da UI.
3. Os 2 têm **a mesma visual**, mas **API ligeiramente
   diferente** (`color` vs `severity`).
4. Refator para unificar é uma **miss atarefada** (toca
   múltiplos controllers). Por isso coexistem.

**Decisão atual:** para novo código, use `next_step_panel`
(consistência com `kpi_card`, `section_panel`, `error_panel`).
Use `next_step` apenas se você está em `cli/renderers.py`.

## Diferença técnica

| Aspecto | `next_step_panel` (`components.py:381-387`) | `next_step` (`renderers.py:468-478`) |
|---------|--------------------------------------------|--------------------------------------|
| Param de cor | `severity: str` | `color: str` |
| Resolução da cor | `SEVERITY_COLOR.get(severity, "ok")` | `_c(color)` (= `COLORS.get(color, color)`) |
| Default da cor | `"ok"` | `"ok"` |
| `box` | `SIMPLE_HEAD` | `SIMPLE_HEAD` |
| `padding` | `(0, 1)` | `(0, 1)` |
| Visual | Idêntico | Idêntico |

**Implicação:** se você passar `severity="ok"` em
`next_step_panel`, a cor resolve para `bright_green` (de
`SEVERITY_COLOR`). Se você passar `color="ok"` em `next_step`,
a cor também resolve para `bright_green` (de `COLORS`).
Coincidentemente, são iguais, mas **as duas funções podem
divergir no futuro** se alguém editar só uma das dicts.

## Severidades disponíveis

| Severity (panel) | Color (step) | Cor (Rich) | Equivalência |
|------------------|--------------|------------|--------------|
| `ok` | `ok` | bright_green | Idêntica |
| `warn` | `warn` | yellow | Idêntica |
| `crit` | `crit` | bold red | Idêntica |
| `info` | `info` | deep_sky_blue1 | Idêntica |
| `muted` | `muted` | grey58 | Idêntica |
| (não tem) | `primary` | cyan | Só `next_step` |
| (não tem) | `energy` | yellow1 | Só `next_step` |
| (não tem) | `hardwork` | green3 | Só `next_step` |

**Implicação:** `next_step` aceita qualquer chave de
`COLORS` (12 chaves); `next_step_panel` aceita só as 6
severities canônicas.

## Onde é usado

1. `cli/commands/state_cmd.py:267-277` — final do State
   Dashboard (usa `next_step` por estar em `renderers.py`)
2. `cli/renderers.py:468-478` — definição
3. Espalhado em controllers que importam de `renderers.py`

## Quando NÃO usar `next_step`

- Quando você está em `ui/components.py` ou em uma função que
  importa de `ui/components.py`. Use `next_step_panel`.
- Quando você quer **forçar** o uso da paleta de severities
  (mais restritiva). `next_step_panel` te obriga a usar uma
  das 6 severities canônicas; `next_step` deixa você usar
  qualquer cor da paleta.

## Migração recomendada

```python
# Antes (em renderers.py)
from operational.cli.renderers import next_step
console.print(next_step("...", color="ok"))

# Depois (em components.py)
from operational.ui.components import next_step_panel
console.print(next_step_panel("...", severity="ok"))
```

A visual é idêntica; a única diferença é o vocabulário
(`color` vs `severity`).

---

## Onde ler mais

- **Componente canônico `next_step_panel`** (use este em novo código) →
  [`03-next-step-panel.md`](03-next-step-panel.md)
- **Decisões de copy para next-step** →
  [`03-next-step-panel.md`](03-next-step-panel.md#padrões-de-copy)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
