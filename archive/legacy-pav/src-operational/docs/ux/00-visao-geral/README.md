# Documentação UX/UI — Operational CLI

> Bem-vindo à pasta `ux/`. Aqui você encontra 16 documentos
> organizados em 3 grupos (visão geral, inventário de telas,
> catálogo de componentes) que complementam a documentação
> técnica em `architecture/`, `algorithms/`, `tui/`, `data/`,
> `debug/`. O foco aqui é a perspectiva do **usuário final**:
> o que cada tela mostra, por que cada componente é como é,
> e como ler o domínio PAV sem jargão.

A documentação UX é a **porta de entrada** para novos usuários do
CLI. Antes de ler o código ou os algoritmos, leia esta pasta: ela
explica o vocabulário, mapeia as telas, e detalha cada pixel de
cada componente. O objetivo é que, ao final da leitura, você
saiba **o que cada coisa faz** e **por que está ali**.

---

## Estrutura da pasta

```
docs/ux/
├── 00-visao-geral/              # Grupo A — contexto e taxonomia
│   ├── 01-objetivos-produto.md
│   ├── 02-perfis-usuario.md
│   ├── 03-principios-usabilidade.md
│   ├── 04-glossario-dominio.md  ★ DOC CRÍTICO
│   └── README.md
│
├── 01-inventario/               # Grupo B — telas e estados
│   ├── 01-telas-inventario.md   # 15 telas catalogadas
│   ├── 02-matriz-estados.md     # 5 estados × 15 telas
│   └── 03-modais-e-abas.md      # 4 tipos de prompt
│
└── 02-componentes/              # Grupo C — 12 widgets Rich
    ├── 01-kpi-card.md
    ├── 02-section-panel.md
    ├── 03-next-step-panel.md
    ├── 04-error-panel.md
    ├── 05-pomodoros-grid.md
    ├── 06-cartesian-plane.md   ★ DOC CRÍTICO
    ├── 07-progress-bar.md
    ├── 08-sparkline.md
    ├── 09-metric-table.md
    ├── 10-severity-text.md
    ├── 11-timeline-h.md
    └── 12-next-step.md
```

---

## Mapa de leitura por persona

| Persona | Leia primeiro | Depois |
|---------|---------------|--------|
| **Dev Solo** (você) | `00-visao-geral/04-glossario-dominio.md` | `01-inventario/01-telas-inventario.md` → `02-componentes/06-cartesian-plane.md` |
| **Estudante** (novato) | `00-visao-geral/02-perfis-usuario.md` → `00-visao-geral/01-objetivos-produto.md` | `01-inventario/03-modais-e-abas.md` (aprender a usar prompts) |
| **Contribuidor open-source** | `00-visao-geral/03-principios-usabilidade.md` | `02-componentes/` (inteiro, para entender os componentes antes de mexer) |
| **Novo no projeto (qualquer)** | **ESTE README** | `00-visao-geral/` em ordem → `01-inventario/` → `02-componentes/` |

---

## Mapa de leitura por objetivo

| Quero... | Leia |
|----------|------|
| Entender o que o sistema faz | `00-visao-geral/01-objetivos-produto.md` |
| Saber para quem ele foi feito | `00-visao-geral/02-perfis-usuario.md` |
| Entender o "porquê" das decisões de design | `00-visao-geral/03-principios-usabilidade.md` |
| **Decifrar termos como Q3, EASE, HARDWORK** | **`00-visao-geral/04-glossario-dominio.md`** ⭐ |
| Ver todas as telas do CLI | `01-inventario/01-telas-inventario.md` |
| Saber o que cada tela mostra com/sem dados | `01-inventario/02-matriz-estados.md` |
| Entender os prompts interativos | `01-inventario/03-modais-e-abas.md` |
| Entender um componente visual específico | `02-componentes/CMP-NNN-*.md` |

---

## Sumário de 1-linha por documento

### Grupo A — Visão Geral (5 docs)

| # | Documento | 1-linha |
|---|-----------|---------|
| 1 | `00-visao-geral/01-objetivos-produto.md` | Os 8 objetivos P0/P1/P2 do CLI, com persona, métrica e status atual. |
| 2 | `00-visao-geral/02-perfis-usuario.md` | 3 personas (Dev Solo, Estudante, Contribuidor) com frequência, comandos favoritos e dores. |
| 3 | `00-visao-geral/03-principios-usabilidade.md` | 8 princípios Nielsen + Norman adaptados para TUI Rich. |
| 4 | `00-visao-geral/04-glossario-dominio.md` | ⭐ Glossário PAV: 25+ termos com fórmula, exemplo, UI, interpretação, armadilha. |
| 5 | `00-visao-geral/README.md` | Este arquivo. |

### Grupo B — Inventário de Telas (3 docs)

| # | Documento | 1-linha |
|---|-----------|---------|
| 6 | `01-inventario/01-telas-inventario.md` | 15 telas catalogadas: comando, tipo, complexidade, modo JSON, estados. |
| 7 | `01-inventario/02-matriz-estados.md` | 5 estados (vazio, loading, com dados, erro, sem permissão) × 15 telas. |
| 8 | `01-inventario/03-modais-e-abas.md` | 4 tipos de prompt (confirmação, escolha, texto, multi-step) com exemplos reais. |

### Grupo C — Componentes (12 docs)

| # | Documento | 1-linha |
|---|-----------|---------|
| 9 | `02-componentes/01-kpi-card.md` | Card de KPI (título + valor + footer) usado em dashboards 2x2. |
| 10 | `02-componentes/02-section-panel.md` | Painel com título colorido e corpo renderizável (genérico). |
| 11 | `02-componentes/03-next-step-panel.md` | Painel de recomendação ("Aplicar este plano: …") no fim de relatórios. |
| 12 | `02-componentes/04-error-panel.md` | Erro padronizado com mensagem, contexto, dica; substitui traceback bruto. |
| 13 | `02-componentes/05-pomodoros-grid.md` | Grid 3×4 com símbolos ▣ (cheio) vs ▢ (vazio) por sessão. |
| 14 | `02-componentes/06-cartesian-plane.md` | ⭐ Plano 2D 18×7 com Q1-Q4, eixos, ponto, glyphs. O componente mais denso. |
| 15 | `02-componentes/07-progress-bar.md` | Barra horizontal `█░` com percent e label. |
| 16 | `02-componentes/08-sparkline.md` | Tendência inline com chars `▁▂▃▄▅▆▇█` (8 níveis). |
| 17 | `02-componentes/09-metric-table.md` | Tabela de métricas com severity-color em cada linha. |
| 18 | `02-componentes/10-severity-text.md` | Wrapper de cor para texto (helper, não painel). |
| 19 | `02-componentes/11-timeline-h.md` | Timeline horizontal de blocos de tempo (com `█` por bloco). |
| 20 | `02-componentes/12-next-step.md` | Variante de `next_step_panel` (mesma visual, parâmetro `color=`). |

---

## Diagrama: como a documentação está organizada

```
┌─────────────────────────────────────────────────────────────────┐
│                    VISÃO GERAL (Grupo A)                         │
│                                                                  │
│  01-objetivos    02-perfis     03-princípios   04-glossário ★  │
│  (O QUÊ)        (PARA QUEM)   (POR QUÊ)       (COMO LER)        │
│       │              │              │                │           │
└───────┼──────────────┼──────────────┼────────────────┼───────────┘
        │              │              │                │
        ▼              ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INVENTÁRIO (Grupo B)                           │
│                                                                  │
│  01-telas-inventário    02-matriz-estados    03-modais-e-abas    │
│  (QUAIS 15)            (5 estados cada)    (4 tipos prompt)     │
│       │                      │                    │             │
└───────┼──────────────────────┼────────────────────┼─────────────┘
        │                      │                    │
        ▼                      ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  COMPONENTES (Grupo C)                           │
│                                                                  │
│  01-kpi  02-section  03-next  04-error  05-pom  06-cartesian ★  │
│  07-bar  08-spark    09-metric 10-sev   11-tl   12-next         │
│                                                                  │
│  12 widgets Rich com wireframe ASCII, signature, severities,    │
│  estados internos, acessibilidade, onde é usado, riscos UX.     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Onde esta pasta NÃO cobre

Esta pasta **não** cobre (em respeito a `docs/AGENTS.md §6.1` e §6.3
sobre "não duplicar"):

- **Arquitetura interna** (MVC, import graph, data flow) →
  `docs/architecture/`
- **Algoritmos específicos** (budget, policy, sleep calc) →
  `docs/algorithms/`
- **Detalhes de implementação Rich/Console** →
  `docs/tui/01-CONSOLE-LIFECYCLE.md`,
  `docs/tui/04-COLOR-PALETTE.md`
- **Schemas de dados** (entidades Pydantic) → `docs/data/`
- **Debugging recipes** → `docs/debug/`
- **Roadmap de features pendentes** → `docs/INTEGRATION-BACKLOG.md`

A documentação UX é uma **layer complementar** — não substitui
nenhuma das pastas acima; ela cruza todas para responder
"como o usuário vê isso?".

---

## Convenções usadas nesta pasta

- **Wireframes em ASCII art** — renderizam em qualquer terminal
  monospace, sem necessidade de fonte Unicode especial
  (apenas `▁▂▃▄▅▆▇█`, `▣ ▢`, `◆ ✗ ▲`, `╭─╮ │ ╰─╯`).
- **Tom didático** — frases curtas, exemplos numéricos sempre
  do `golden.csv`, explicações "por quê" antes de "como".
- **Citações de código** no formato `file:line` (ex:
  `ui/components.py:341-361`) — permite `Ctrl+Click` em IDEs
  modernas para navegar ao código.
- **Português brasileiro** — alinhado com `docs/AGENTS.md`
  (estratégia em PT-BR, código em EN).
- **Markdown ATX** (títulos com `#`) e fenced code blocks
  com ` ```text ` para wireframes, ` ```python ` para
  assinaturas.

---

## Próximos passos

1. **Se você é o Dev Solo** (você): comece pelo
   [`04-glossario-dominio.md`](04-glossario-dominio.md) — esse doc
   foi escrito *para você* responder a pergunta "o que é Q3?".
2. **Se você é contribuidor open-source**: comece pelo
   [`02-componentes/`](../02-componentes/) — entender os 12
   widgets é pré-requisito para modificar a UI sem quebrar o
   layout.
3. **Se você é novo no projeto**: leia os 3 grupos em ordem
   (A → B → C). Leva ~2h, mas ao final você entende 100% do que
   o usuário vê ao rodar `operational home`.

---

## Onde está o código

Cada doc desta pasta aponta para o código fonte via
`file:line`. Mapa rápido:

| Camada | Path |
|--------|------|
| UI factories (componentes) | `src/operational/ui/components.py` |
| UI renderers (alternativos) | `src/operational/cli/renderers.py` |
| Daily report (compositor) | `src/operational/ui/daily_report.py` |
| CLI controllers | `src/operational/cli/commands/*.py` |
| Home menu (interativo) | `src/operational/cli/home.py` |
| Core services (dados) | `src/operational/core/services.py` |
| Console singleton | `src/operational/ui/__init__.py` |
| Color palette | `ui/components.py:31-94` |

---

## Histórico de revisão

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-08 | 1.0 | Criação inicial (16 documentos) |
