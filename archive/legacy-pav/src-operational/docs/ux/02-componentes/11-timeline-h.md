# CMP-011 — timeline_h

**Arquivo fonte:** `src/operational/cli/renderers.py:238-260`
**Função Python:** `timeline_h(blocks, *, width=60, color="hardwork") -> Text`
**Propósito:** Timeline **horizontal** de blocos de tempo, com cada bloco representado por um run de `█` de comprimento proporcional, seguido de `HHh label`. Mostra "o que aconteceu entre 04h e 22h hoje".
**Quando usar:** State Dashboard (seção "Time Blocks"), onde o usuário quer ver a distribuição do dia.
**Quando NÃO usar:** Para dias com muitos blocos pequenos (< 30min) — fica poluído. Para tendências temporais de métricas (use `sparkline`).

## Assinatura

```python
def timeline_h(
    blocks: Sequence[tuple[int, int, str]],
    *,
    width: int = 60,
    color: str = "hardwork",
) -> Text
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `blocks` | `Sequence[(start_h, end_h, label)]` | — | Lista de tuplas em horas 24h |
| `width` | `int` | `60` | Largura total em chars (para 1 linha só) |
| `color` | `str` | `"hardwork"` | Cor dos `█` |

## Saída ASCII

**Caso típico (5 blocos, do golden.csv dia 2026-06-02):**

```text
  ████ 04h Sleep
  ████████████ 06h Workout
  ████████ 10h Deep Work
  █████████ 14h Lunch + Rest
  ██████████ 16h Admin
  █████ 20h Shutdown
```

**Anatomia linha por linha:**

1. **Largura da barra (`████`):** proporcional à duração do
   bloco. `min=4` chars (visual) para garantir visibilidade.
2. **`HHh` label:** hora de início do bloco (e.g., `04h`).
3. **Texto descritivo:** label do bloco (e.g., `Sleep`,
   `Workout`).
4. **Sequência:** blocos ordenados por hora de início.

**Versão compacta (1 linha, width=60):**

```text
  ████████████████████████████████████  04h-22h (5 blocos)
```

(Não implementado atualmente — `timeline_h` sempre 1 bloco por
linha. **Gap de UX:** versão single-line seria útil para
resumo.)

## Os 2 elementos visuais

| Char | Unicode | Significado | Cor |
|------|---------|-------------|-----|
| `█` | U+2588 (FULL BLOCK) | Duração do bloco | `COLORS[color]` (e.g., `green3`) |
| ` ` | (espaço) | Background | (sem cor) |

A **largura** de `█` é calculada como:

```python
span = max(1, max_h - min_h)  # range total em horas
left = int((start_h - min_h) / span * width)
right = int((end_h - min_h) / span * width)
length = max(1, right - left)  # mínimo 1 char
```

A timeline **escala automaticamente** para o range dos blocos
(e.g., se min=4h e max=22h, span=18h). Blocos maiores ficam
visualmente maiores.

## Severidades disponíveis

| Cor | Uso típico |
|-----|-----------|
| `hardwork` (green3) | Blocos de trabalho |
| `ease` (magenta) | Blocos de recovery |
| `sleep` (dodger_blue2) | Blocos de sono |
| `primary` (cyan) | Default |
| `transition` (deep_pink1) | Blocos de transição |

A cor é resolvida via `_c(color)` (interno do `renderers.py`).

## Estados internos

- **Lista vazia (`blocks = []`):** retorna `Text("  (sem
  blocos no período)", style="grey58")` — placeholder
  amigável.
- **1 bloco:** a timeline mostra 1 linha com o bloco. Funciona,
  mas o componente é overkill para 1 bloco.
- **N blocos:** suporta qualquer N. Acima de 8-10, a timeline
  fica longa; caller deve considerar filtrar.
- **Blocos sobrepostos:** o componente não detecta. Se você
  tem blocos `[4, 8]` e `[6, 10]`, eles vão aparecer
  sequencialmente, não sobrepostos. **Caller responsibility:**
  filtrar ou detectar sobreposição.
- **Blocos fora de ordem:** o caller deve pré-ordenar por
  `start_h`. O componente não ordena.

## Acessibilidade

- **Funciona sem cores?** **Sim.** `█` em quantidade relativa
  é robusto em escala de cinza. A duração é visual, não
  cromática.
- **Funciona com TTY 80-col?** Sim, com `width=60` ou menor.
- **Leve para screen reader?** Não; a estrutura de blocos é
  visual, não textual.

## Onde é usado

1. `cli/commands/state_cmd.py:236-247` — "📦 Time Blocks (N
   blocos, Xmin)" no State Dashboard

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** `hardwork`
  (verde) é universalmente "trabalho". Funciona.
- **Texto pode ser mal interpretado em outro contexto:** o
  `label` é livre. **Regra:** primeira letra maiúscula, sem
  abreviações obscuras.
- **Layout pode quebrar em terminal narrow:** `width=60` é o
  default. Em 60 col, fica apertado. **Mitigação:** aceitar
  `width=` parametrizado (atualmente sim, default 60).
- **Muitos blocos pequenos:** se você tem 20 blocos de 15min
  cada, a timeline vira 20 linhas curtas. **Mitigação:**
  agregar por período (MANHA/TARDE/NOITE) antes de plotar.

## Diferença para `pomodoros_grid`

| Aspecto | `timeline_h` | `pomodoros_grid` |
|---------|-------------|------------------|
| Visual | Run de `█` por bloco + label | Grid `▣ ▢` por sessão |
| Granularidade | 1 linha por bloco | 3 linhas (S1/S2/S3) |
| Quando usar | Visão geral do dia | Foco do dia (pomodoros) |
| Cor | `hardwork` (verde) | `green3` (cheio) / `grey50` (vazio) |

**Regra:** `timeline_h` para "quais blocos eu fiz?", `pomodoros_grid`
para "quantos pomodoros eu fiz?".

---

## Onde ler mais

- **Componente irmão `pomodoros_grid`** (foco por sessão) →
  [`05-pomodoros-grid.md`](05-pomodoros-grid.md)
- **Estado "Time Blocks" no State Dashboard** →
  [`../01-inventario/01-telas-inventario.md`](../01-inventario/01-telas-inventario.md#scr-004--state-dashboard)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
