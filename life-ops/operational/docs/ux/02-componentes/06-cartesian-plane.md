# CMP-006 — cartesian_plane ⭐ (DOC CRÍTICO)

**Arquivo fonte:** `src/operational/ui/components.py:241-327` (canônico, retorna `Table.grid`)
**Função Python:** `cartesian_plane(x, y, *, width=18, height=7) -> Table`
**Propósito:** Plano Cartesiano 2D com **eixos 0/50/100**, **linhas de quadrante 50%**, **ponto colorido por Q1/Q2/Q3/Q4**. É a **representação visual** do regime de produtividade do dia.
**Quando usar:** Daily Report, Weekly Report (resumo por dia), e qualquer lugar onde "onde estou no espaço Produtividade × Eficiência?" importa.
**Quando NÃO usar:** Para dados com eixos não-normalizados (use `progress_bar` ou `sparkline`); para tendências temporais (use `sparkline`).

> **Este é o componente mais denso do CLI.** O usuário disse
> explicitamente que não entende. Por isso este doc tem wireframes
> ASCII completos, explicação de cada char, e exemplos em cada
> quadrante.

---

## Glossário visual: os 9 caracteres do plano

| Char | Nome Unicode | Significado no plano |
|------|--------------|----------------------|
| `┼` | U+253C (BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL) | Cruzamento 0% (origem) |
| `│` | U+2502 (BOX DRAWINGS LIGHT VERTICAL) | Eixo Y (coluna esquerda) |
| `─` | U+2500 (BOX DRAWINGS LIGHT HORIZONTAL) | Eixo X (linha inferior) |
| `┊` | U+250A (BOX DRAWINGS DOUBLE DASH VERTICAL) | Linha vertical de quadrante 50% |
| `┈` | U+2508 (BOX DRAWINGS DOUBLE DASH HORIZONTAL) | Linha horizontal de quadrante 50% |
| `◆` | U+25C6 (BLACK DIAMOND) | Ponto em Q1 ou Q2 (topo) |
| `✗` | U+2717 (BALLOT X) | Ponto em Q3 (crítico) |
| `▲` | U+25B2 (BLACK UP-POINTING TRIANGLE) | Ponto em Q4 (produtivo, otimizar) |
| ` ` | (espaço) | Célula vazia (background) |

**Cores:**
- `┼` em **bold white** (origem, destaque)
- `│`, `─` em **grey58** (eixos)
- `┊`, `┈` em **grey30** (linhas de quadrante, mais sutis)
- `◆` em **bright_green** (Q1) ou **cyan** (Q2)
- `✗` em **bold red** (Q3)
- `▲` em **yellow** (Q4)

---

## Saída ASCII — wireframe completo (Q1, x=80, y=70)

```text
Y%  X% (Produtividade)
100 ◆
 75
 50  ┊
 25
  0 ┼──────────────────────────────────────
     0                50               100
```

**Anatomia linha por linha:**

1. **Header (`Y%  X% (Produtividade)`)** — labels dos eixos
   em grey58, posicionados na coluna esquerda e direita.
2. **`100`** — label Y=100 (topo, "100% eficiência") em grey58.
3. **`◆`** — o ponto do dia (Q1) em bright_green, posicionado em
   (col=14, row=0) para x=80, y=70.
4. **`75`** — label Y=75 (intermediário) em grey58.
5. **`50  ┊`** — label Y=50 + linha vertical de quadrante em
   grey30, na coluna 9 (50% do width=18).
6. **`25`** — label Y=25 em grey58.
7. **`0 ┼──────────────────────────────────────`** — origem (0,0) +
   eixo X horizontal em grey58. `┼` é bold white, `─` é grey58.
8. **`0                50               100`** — labels X em grey58,
   abaixo do plano (0 à esquerda, 50 no meio, 100 à direita).

---

## Os 4 quadrantes — exemplo em cada

### Q1 (x=80, y=70) — 🏆 Excelente

```text
Y%  X% (Produtividade)
100 ◆
 75
 50  ┊
 25
  0 ┼──────────────────────────────────────
     0                50               100
```

Ponto `◆` em bright_green, top-right.

### Q2 (x=30, y=80) — 🟢 Otimizado, pouco output

```text
Y%  X% (Produtividade)
100        ◆
 75
 50  ┊
 25
  0 ┼──────────────────────────────────────
     0                50               100
```

Ponto `◆` em **cyan**, top-left.

### Q3 (x=20, y=30) — 🚨 Crítico

```text
Y%  X% (Produtividade)
100
 75
 50  ┊
 25 ✗
  0 ┼──────────────────────────────────────
     0                50               100
```

Ponto `✗` em **bold red**, bottom-left. O `✗` é o **único
glyph negativo** do sistema — sinaliza "algo está errado".

### Q4 (x=70, y=30) — ⚠️ Produtivo, otimizar

```text
Y%  X% (Produtividade)
100
 75
 50  ┊
 25        ▲
  0 ┼──────────────────────────────────────
     0                50               100
```

Ponto `▲` em **yellow**, bottom-right. Diferente de `◆` para
sugerir "atenção, otimize".

---

## Como o ponto é plotado

```python
# ui/components.py:254-267
x = max(0.0, min(100.0, x))  # clamp X em [0, 100]
y = max(0.0, min(100.0, y))  # clamp Y em [0, 100]

px = round(x / 100 * (width - 1))   # posição em colunas (0 a 17)
py = round((100 - y) / 100 * (height - 1))  # posição em linhas (0=top, 6=bottom)

if x >= 50 and y >= 50:    point_color, point_char = "bright_green", "◆"
elif x <  50 and y >= 50:  point_color, point_char = "cyan",         "◆"
elif x <  50 and y <  50:  point_color, point_char = "bold red",     "✗"
else:                      point_color, point_char = "yellow",       "▲"
```

**Tradução:**
- O ponto é mapeado para uma **grade de células** (18 colunas ×
  7 linhas).
- `py=0` é o **topo** (Y=100), `py=6` é a **base** (Y=0). A
  inversão é necessária porque o eixo Y do terminal cresce para
  baixo, enquanto o Y cartesiano cresce para cima.
- A cor + char são escolhidos pelo **quadrante**, não pela
  posição exata.

---

## Severidades disponíveis

O `cartesian_plane` **não usa severity** para colorir o ponto —
o glyph **já carrega a semântica do quadrante**:

| Glyph | Cor | Quadrante | Interpretação |
|-------|-----|-----------|---------------|
| `◆` (bright_green) | bright_green | Q1 (top-right) | Excelente — manter ritmo |
| `◆` (cyan) | cyan | Q2 (top-left) | Otimizado, pouco output |
| `✗` | bold red | Q3 (bottom-left) | Crítico — revisar sistema |
| `▲` | yellow | Q4 (bottom-right) | Produtivo, otimizar |

**Decisão de design:** Q1 e Q2 usam o mesmo glyph (`◆`), mas
com cores diferentes (verde vs cyan). A diferença sutil indica
"ambos são 'bons' mas Q1 é melhor". Q3 e Q4 têm glyphs
totalmente diferentes (`✗` e `▲`) para garantir
distinguibilidade.

## Estados internos

- **x=0, y=0** (vazio): ponto `✗` em (col=0, row=6), encostado
  na origem. Visualmente: o ponto some na cruz `┼`. **Caller
  responsibility:** alertar via `next_step_panel(severity="crit")`.
- **x=100, y=100** (perfeito): ponto `◆` em (col=17, row=0), no
  canto superior direito. **Caller:** `next_step_panel(severity="ok")`.
- **x ou y fora de [0, 100]:** clamp automático. Valores
  absurdos (> 100) viram 100; valores negativos viram 0.
- **width ou height < 5:** funciona, mas o plano fica ilegível.
  O canonical usa `width=18, height=7` para densidade ideal.

## Acessibilidade

- **Funciona sem cores?** **Parcialmente.** Os glyphs (`◆ ✗ ▲`)
  são distinguíveis, mas a **diferença entre Q1 e Q2** (ambos
  `◆`, mas bright_green vs cyan) some. **Mitigação:** incluir
  o `Quadrant` textual (Q1, Q2, etc.) no caption adjacente
  (`build_quadrant_caption` em `ui/daily_report.py:193-201`).
- **Funciona com TTY 80-col?** Sim; o plano é ~36 chars de
  largura, cabe em 80 col com label lateral.
- **Leve para screen reader?** Não. O `Table.grid` é opaco para
  screen readers.

## Onde é usado

1. `ui/daily_report.py:204-218` — seção "📈 Plano Cartesiano"
   do Daily Report (com caption Q1/Q2/Q3/Q4 + label "Ação")
2. `cli/commands/report_cmd.py:251-275` — tabela "Posição
   Diária" do Weekly Report (X%, Y%, Quadrante) — não usa o
   `cartesian_plane` em si, mas reutiliza
   `classify_quadrant(x, y)` para determinar Q1-Q4
3. (potencial) Future V4 do weekly report com mini-cartesian
   inline

## Riscos de usabilidade

- **Cores podem ser confusas para daltônicos:** bright_green
  vs cyan são distinguíveis pela maioria. **Mitigação:**
  glyphs `◆` vs `◆` são iguais; usar o caption textual
  ("Q1 — Excelente") para inequivocamente distinguir.
- **Texto pode ser mal interpretado em outro contexto:** o
  label "X% (Produtividade)" e "Y%" assume conhecimento.
  **Mitigação:** ver [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#cartesiano--plano-cartesiano)
  (definição completa de X, Y, Q1-Q4).
- **Layout pode quebrar em terminal narrow:** `width=18` é
  fixo. Em 60 col, o label "X% (Produtividade)" wrap.
  **Mitigação:** testar com terminal narrow; considerar
  versão compacta (`width=10`) se necessário.
- **Glyph `◆` é usado para Q1 e Q2:** isso viola "reconhecimento
  > recordação" (mesmo glyph, semântica diferente). **Decisão
  atual:** confiar na cor + caption textual. **Proposta
  futura:** usar `★` (estrela) para Q1 e `◆` para Q2.

## Cálculo de exemplo passo a passo

Dado `x=80, y=70, width=18, height=7`:

1. **Clamp:** `x=80, y=70` (já em [0, 100]).
2. **px:** `round(80/100 × (18-1)) = round(80/100 × 17) = round(13.6) = 14`.
3. **py:** `round((100-70)/100 × (7-1)) = round(30/100 × 6) = round(1.8) = 2`.
4. **Quadrante:** `x=80 >= 50` AND `y=70 >= 50` → Q1.
5. **Glyph + cor:** `◆` em bright_green.
6. **Posição final:** célula (col=14, row=2). No wireframe de
   Q1 acima, isso corresponde à linha `100 ◆` (row=0 no
   array, mas a primeira linha visível é o label Y=100).

---

## Comparação com o componente original (renderers.py:268-349)

`cli/renderers.py:268-349` tem uma versão que retorna `Text` em
vez de `Table.grid`. **Diferenças:**

| Aspecto | `components.py` (canonical) | `renderers.py` (alt) |
|---------|---------------------------|----------------------|
| Retorno | `Table.grid` | `Text` |
| Largura | 18 chars (fixo) | 14 chars (compacto) |
| Header | "Y%  X% (Produtividade)" | "X% X% X%" (sem label) |
| Layout | `Table.grid` com colunas width=2 | `Text.append` + `\n` |
| Estabilidade | Excelente (não wrap) | Frágil (pode quebrar) |
| **Uso** | **Recomendado** | Legacy |

**Recomendação:** use a versão canônica (`components.py`) para
novo código.

---

## Onde ler mais

- **Definição matemática de X, Y, Q1-Q4** (o que cada eixo significa) →
  [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#x--y-eixos-do-cartesiano)
- **Definição matemática de `classify_quadrant`** (fórmula) →
  [`../00-visao-geral/04-glossario-dominio.md`](../00-visao-geral/04-glossario-dominio.md#q1--q2--q3--q4-quadrantes)
- **Catálogo geral de componentes** →
  [`../../tui/02-COMPONENT-CATALOG.md`](../../tui/02-COMPONENT-CATALOG.md)
