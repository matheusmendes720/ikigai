# CMP-005 — pomodoros_grid

**Arquivo fonte:** `src/operational/ui/components.py:222-238` (canônico) e `src/operational/cli/renderers.py:204-230` (variante Text)
**Função Python:** `pomodoros_grid(s1, s2, s3, *, max_per_session=4) -> Table`
**Propósito:** Grid **3×4** que mostra quantos pomodoros foram completados em cada sessão (S1 manhã, S2 tarde, S3 noite). É a visualização **escaneável** do foco do dia.
**Quando usar:** Daily Report, State Dashboard, e qualquer lugar onde o foco diário importa.
**Quando NÃO usar:** Para séries temporais (use `sparkline`); para detalhamento por round individual (use tabela CRUD).

## Assinatura

```python
def pomodoros_grid(
    s1: int,
    s2: int,
    s3: int,
    *,
    max_per_session: int = 4,
) -> Table  # canonical
# OR
# Text  # renderer variant
```

| Param | Tipo | Default | Notas |
|-------|------|---------|-------|
| `s1` | `int` | — | Pomodoros completos na S1 manhã, ex: `3` |
| `s2` | `int` | — | Pomodoros completos na S2 tarde, ex: `4` |
| `s3` | `int` | — | Pomodoros completos na S3 noite, ex: `1` |
| `max_per_session` | `int` | `4` | Limite de pomodoros por sessão (clamp em 0..max_per_session) |

## Saída ASCII

**Caso típico (s1=3, s2=4, s3=1, max=4):**

```text
  S1 manhã   ▣ ▣ ▣ ▢   3/4
  S2 tarde   ▣ ▣ ▣ ▣   4/4
  S3 noite   ▣ ▢ ▢ ▢   1/4
```

**Dia perfeito (4/4 em todas):**

```text
  S1 manhã   ▣ ▣ ▣ ▣   4/4
  S2 tarde   ▣ ▣ ▣ ▣   4/4
  S3 noite   ▣ ▣ ▣ ▣   4/4
```

**Dia vazio (0/4 em todas):**

```text
  S1 manhã   ▢ ▢ ▢ ▢   0/4
  S2 tarde   ▢ ▢ ▢ ▢   0/4
  S3 noite   ▢ ▢ ▢ ▢   0/4
```

**Overflow (s1=6, max_per_session=4) — clamp visual:**

```text
  S1 manhã   ▣ ▣ ▣ ▣   4/4    ← clampado em max_per_session
```

(Atenção: o número `n/max_per_session` na direita reflete o
clamp; valor real é 6 mas o display mostra 4. Caller deve
documentar isso no JSON.)

## Os 2 símbolos Unicode

| Char | Unicode | Significado | Cor |
|------|---------|-------------|-----|
| `▣` | U+25A3 (WHITE SQUARE CONTAINING BLACK SMALL SQUARE) | Pomodoro **completo** | `green3` (bold) |
| `▢` | U+25A2 (WHITE SQUARE WITH ROUNDED CORNERS) | Pomodoro **planejado mas não completo** | `grey50` |

**Diferença visual:** `▣` tem um quadrado preto dentro do
branco; `▢` é um quadrado vazio. O contraste é alto e
permite "ler" a contagem em < 1s.

## Severidades disponíveis

O `pomodoros_grid` **não usa severity** diretamente. A cor é
fixa: `green3` para `▣`, `grey50` para `▢`, `bold white` para
o contador (`n/max_per_session`).

A informação de "completou" vs "não completou" **já é binária**;
não há espaço para "warn" (parcialmente completo).

## Estados internos

- **0 items (vazio):** todos `▢` em todas as 3 sessões. Comum
  no início do dia (state dashboard de manhã antes de começar).
- **1-11 items:** o caso normal; distribuição típica 4-4-3
  (8h de foco distribuído).
- **12+ items:** possível mas raro. O caller deve alertar
  (provável erro de registro).
- **Erro de dados (s1 ou s2 ou s3 negativo):** o componente
  faz clamp via `max(0, min(max_per_session, n))`, então
  valores inválidos viram 0.

## Acessibilidade

- **Funciona sem cores?** Sim, **excelente**. Os símbolos
  `▣` vs `▢` são distinguíveis mesmo em preto-e-branco.
  Isso é **proposital** — o grid sobrevive ao no-color mode
  sem perder informação.
- **Funciona com TTY 80-col?** Sim. Cada linha tem ~26 chars;
  3 linhas + header cabem em qualquer terminal.
- **Leve para screen reader?** Não, mas o `n/max_per_session`
  ao fim de cada linha dá a informação em texto também
  (redundância com os símbolos).

## Onde é usado

1. `ui/daily_report.py:319-327` — seção "🍅 Pomodoros Grid"
   do Daily Report
2. `cli/commands/state_cmd.py:225-233` — "🍅 Pomodoros
   (S1 manhã · S2 tarde · S3 noite)" do State Dashboard
3. `ui/components.py:222-238` — definição canônica

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** `green3`
  (cheio) e `grey50` (vazio) têm **luminância muito
  diferente** — distinguível para a maioria dos daltônicos.
  Mas o diferenciador universal é o **símbolo** (`▣` vs
  `▢`), não a cor. **Decisão:** componente é robusto
  mesmo em escala de cinza.
- **Texto pode ser mal interpretado em outro contexto:** o
  label "S1 manhã" assume conhecimento do PAV. **Mitigação:**
  ver [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#pomodoros-grid-símbolos).
- **Layout pode quebrar em terminal narrow:** o grid é
  compacto (~26 chars/linha). Em 80-col, cabe sem
  problemas. Em 60-col, começa a apertar (mas o componente
  não testa isso).
- **Overflow silencioso:** se `s1=6`, o display mostra `4/4`
  sem avisar. **Caller responsibility:** alertar via
  `next_step_panel` ou via JSON.

## Detalhes técnicos

### Componente canônico (`components.py:222-238`)

Retorna um `Table.grid(expand=False, padding=(0, 1))` com:
- Coluna 1: label (min_width=11, justify=left)
- Colunas 2-5: 4 células de pomodoros (min_width=2 cada)
- Coluna 6: contador `n/max` (min_width=6, justify=right)

Cada célula é um `Text` com 1 char + espaço (2 chars de largura).
Linhas: 3 (S1, S2, S3).

### Variante (`renderers.py:204-230`)

Retorna um `Text` com 3 linhas, uma por sessão. Layout
manual via `\n` e `Text.append`. **Por que ainda existe?**
Legado; pode ser removido em refator futura.

**Recomendação:** use a versão canônica (`components.py`)
para novo código.

---

## Onde ler mais

- **Símbolos Unicode ▣ vs ▢** →
  [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#pomodoros-grid-símbolos)
- **Componente irmão `sparkline`** (tendência inline, em vez
  de grid estático) → [`08-sparkline.md`](08-sparkline.md)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
