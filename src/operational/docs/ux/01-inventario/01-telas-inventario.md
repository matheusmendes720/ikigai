# 01 — Inventário de Telas

> Este documento cataloga as **15 telas** do `operational` CLI
> (consolidadas: variantes `--json` contam como o mesmo "tela em
> modo JSON"). Para cada tela: comando de acesso, tipo, complexidade,
> modo JSON, dataset, estados vazio/com-dados, e wireframe ASCII.
>
> O número de telas é **15** (não 28, que é o total de sub-comandos
> Typer) porque:
> - `routine list` + `routine create` = mesma tela (form/tabela)
> - `--json` em qualquer comando = mesma tela em modo JSON
> - `reflect entrada` + `reflect saida` = mesma tela (form OKR)

A organização segue o **fluxo do usuário** (home menu 1-10), não a
hierarquia técnica dos sub-typers.

---

## Convenções

- **SCR-NNN**: ID da tela (SCR = "screen")
- **Tipo:**
  - **Interativa** — exige entrada do usuário (menu, prompt, form)
  - **Form** — coleta dados estruturados (cria/atualiza entidade)
  - **Output tabular** — exibe lista/tabela de entidades
  - **Diagnóstico** — health-check / introspection
- **Complexidade:**
  - **Alta** — múltiplos painéis, dados cruzados, lógica de agregação
  - **Média** — 1-2 painéis, 1 fonte de dados
  - **Baixa** — 1 linha de output, 1 fonte de dados
- **Dataset:** qual dataset é usado (production, golden, synthetic, qualquer)
- **JSON:** `Sim (--json)` se suporta saída estruturada

---

## SCR-001 — Home Menu

**Comando de acesso:** `operational home`
**Tipo:** Interativa
**Arquivo renderizador:** `src/operational/cli/home.py:33-46` (MENU_ITEMS)
**Complexidade:** Média
**Modo JSON:** Não (interativa por design)
**Dataset requerido:** Nenhum
**Estado vazio:** Menu é renderizado normalmente; choices sem dependência de dados
**Estado com dados:** Mesma renderização (o menu não muda com dados)

### Wireframe

```text
╭─────────────────────────────────────────────────────────────────────╮
│  ⚡ TIME-TASKER  v0.1.0  |  2026-06-08                              │
╰─────────────────────────────────────────────────────────────────────╯
Key  Action                       Description
─────────────────────────────────────────────────────────────────────
1    🌅  Iniciar Manhã             Acordou → sleep retroativo → ENTRY → workout
2    💻  Iniciar Tarde             Almoço → pomodoros → foco principal
3    🌙  Encerrar Dia              Jantar → shutdown → reflexão (OKRs)
4    ⚡  Check-in Rápido           30s: registrar energia/foco do momento
5    📊  Dashboard do Dia          Onde estou · o que está logado · estou no plano?

6    📈  Relatórios                Diário · Semanal · Estado consolidado
7    📚  Dados & Histórico         Rotinas · Blocos · Journal · Habits · Métricas
8    ⚙️   Política & Ajuste        Setpoints PUSH/MAINTAIN/REDUCE/RECOVER · Decisões
9    🎬  Demo & Testes             Seed 7 dias PAV · Limpar · Show · Run tests
10   ℹ️   Sistema                  Versão · Constantes · Tipos · Categorias
q    🚪  Sair                      Exit

Choose [5]: █
```

---

## SCR-002 — Daily Report

**Comando de acesso:** `operational report daily [-d YYYY-MM-DD] [--json]`
**Tipo:** Output tabular alto (dashboard completo)
**Arquivo renderizador:** `src/operational/ui/daily_report.py:281-316`
**Complexidade:** Alta
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio:** Mostra "—" em todos os campos, quadrante calculado a partir de zeros (Q3 ou indefinido)
**Estado com dados:** Ver wireframe abaixo (do `golden.csv`, dia 2026-06-02)

### Wireframe

```text
╭───  ⚡ DAILY REPORT  ───────────────────────────────────────────────╮
│  📅  2026-06-02   ◆ CURSO      🏆 Q1      🍅 11/12                   │
╰─────────────────────────────────────────────────────────────────────╯
╭───  😴 EASE  ─────────────────────────────────────────────────────╮
│  ⏰ Acordou        04:00                                          │
│  🌙 Dormiu         20:30                                          │
│  😴 Sono           7.5h 🟢 bom                                    │
│  ⭐ Qualidade      9/10                                           │
│  💪 Workout        10min ✓                                        │
│  🧘 Meditação      8min ✓                                         │
│  🍽️  Lunch         5min eat + 30min rest = 35min                   │
│  🌆 Jantar < 18h   sim ✓                                          │
│  📱 Luz azul       cortada ✓                                      │
│  🔄 Transições     5/5                                            │
╰─────────────────────────────────────────────────────────────────────╯
╭───  💻 HARDWORK  ─────────────────────────────────────────────────╮
│  Tipo de Dia       CURSO                                          │
│  📊 Orçado         240min (4h00m)                                 │
│  ⏱️  Realizado     240min (4h00m)                                 │
│  Δ Desvio          0min (DENTRO)                                   │
│  🍅 Pomodoros      11/12 rounds                                   │
╰─────────────────────────────────────────────────────────────────────╯
╭───  🍅 Pomodoros Grid — S1 manhã · S2 tarde · S3 noite  ────────╮
│  S1 manhã   ▣ ▣ ▣ ▣   4/4                                        │
│  S2 tarde   ▣ ▣ ▣ ▣   4/4                                        │
│  S3 noite   ▣ ▣ ▣ ▢   3/4                                        │
╰─────────────────────────────────────────────────────────────────────╯
╭───  ⚡ Estado Subjetivo  ─────────────────────────────────────────╮
│  ⚡ Energia   ████████░░  80%  (8/10)                            │
│  🎯 Foco      █████████░  90%  (9/10)                            │
╰─────────────────────────────────────────────────────────────────────╯
╭───  📈 Plano Cartesiano — X: Produtividade · Y: Eficiência · Point: (100%, 100%)  ╮
│       Y%  X% (Produtividade)                                          │
│      100                                                          ◆  │
│       75                                                           │
│       50  ┊                                                        │
│       25                                                           │
│        0 ┼──────────────────────────────────────                   │
│           0                50               100                     │
│  Q1  —  Excelente — manter ritmo                                      │
│  Ação: Manter                                                         │
╰─────────────────────────────────────────────────────────────────────╯
╭───  🎯 OKRs V3 — Reflexão do dia  ────────────────────────────────╮
│  ❌ Parar de fazer    Assistir serie apos 19h                       │
│  ✅ Repetir           Acordar sem alarme                            │
│  🏆 Big-Win           Feature JWT completa + testada                 │
│  💡 Maior aprendizado  Sono define o dia - qualidade 9 leva a ...   │
╰─────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────╮
│  ✓  Dia dentro do padrão ouro. Manter ritmo, monitorar fadiga.  │
╰──────────────────────────────────────────────────────────────────╯
```

---

## SCR-003 — Weekly Report

**Comando de acesso:** `operational report weekly [-s YYYY-MM-DD] [-e YYYY-MM-DD] [--json]`
**Tipo:** Output tabular alto (dashboard semanal)
**Arquivo renderizador:** `src/operational/cli/commands/report_cmd.py:106-315` (inline Table construction)
**Complexidade:** Alta
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio:** Mostra "0" em todos os KPIs, sparklines "(sem dados)"
**Estado com dados:** Ver wireframe abaixo (7 dias típicos do golden.csv)

### Wireframe

```text
╭───  ⚡ WEEKLY  ·  2026-06-02 → 2026-06-08  ·  7 dias  ─────────────╮
╰─────────────────────────────────────────────────────────────────────╯
╭─────────────────╮  ╭─────────────────╮
│  💻 Hardwork    │  │  🍅 Pomodoros   │
│  16h30          │  │  45             │
│  orçado 18h     │  │  média 6.4/dia  │
│  92%            │  │                 │
╰─────────────────╯  ╰─────────────────╯
╭─────────────────╮  ╭─────────────────╮
│  😴 Sono Médio  │  │  🎯 Reflexões   │
│  6.8h           │  │  5/7            │
│  min 4.0h       │  │  dias com OKRs  │
│  max 7.5h       │  │                 │
╰─────────────────╯  ╰─────────────────╯

╭───  📈 Tendências 7-dias  ─────────────────────────────────────────╮
│  😴 Sono           ▃▅▂▁▃█▅   min 4h / max 8h                      │
│  📈 Produtividade  ▅▄▃▃▅▆▆   média 75%                            │
│  🍅 Pomodoros      █▅▃▃▅▆▆   total 45                             │
│    Seg  Ter  Qua  Qui  Sex  Sab  Dom                              │
╰─────────────────────────────────────────────────────────────────────╯
╭───  🗓️ Distribuição por TipoDia  ─────────────────────────────────╮
│  CURSO     4   ████████████                                       │
│  LIVRE     1   ███                                                 │
│  HARDCORE  1   ███                                                 │
│  DESCANSO  1   ███                                                 │
╰─────────────────────────────────────────────────────────────────────╯
╭───  📊 Distribuição por Quadrante  ────────────────────────────────╮
│  Q1     4   ████████████                                          │
│  Q2     1   ███                                                   │
│  Q3     1   ███                                                   │
│  Q4     1   ███                                                   │
╰─────────────────────────────────────────────────────────────────────╯
╭───  🗓️ Posição Diária (X, Y, Quadrante)  ─────────────────────────╮
│  Data       Tipo       X     Y     Quadrante  🍅                  │
│  2026-06-02 CURSO     100%  100%  Q1          11                  │
│  2026-06-03 CURSO      75%   75%  Q1           6                  │
│  2026-06-04 HARDCORE  100%  100%  Q1           9                  │
│  2026-06-05 CURSO      60%   60%  Q1           8                  │
│  2026-06-06 CURSO      40%   40%  Q3           4                  │
│  2026-06-07 LIVRE      80%   80%  Q1           5                  │
│  2026-06-08 DESCANSO   —     —     —           0                  │
╰─────────────────────────────────────────────────────────────────────╯
╭───  😴 Distribuição do Sono (7 dias)  ─────────────────────────────╮
│  Média           6.8h                                              │
│  Mínimo          4.0h  (yellow)                                    │
│  Máximo          7.5h  (bright_green)                              │
│  Dias < 6h       2     (bold red)                                  │
│  Dias 7-9h       3     (bright_green)                              │
╰─────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────╮
│  !  1 dia(s) em Q3 (Crítico). Revisar padrão sono+trabalho urgente.  │
╰──────────────────────────────────────────────────────────────────╯
```

---

## SCR-004 — State Dashboard

**Comando de acesso:** `operational state show [-d YYYY-MM-DD] [--json]`
**Tipo:** Output tabular médio
**Arquivo renderizador:** `src/operational/cli/commands/state_cmd.py:71-130`
**Complexidade:** Média
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio:** Cards mostram "—" / "0" / "não registrado" em cinza
**Estado com dados:** Ver wireframe (do `golden.csv`, dia 2026-06-02)

### Wireframe

```text
╭───  ⚡  STATE  ·  2026-06-08  ·  🌅 MANHA  ────────────────────────╮
╰─────────────────────────────────────────────────────────────────────╯
╭─────────────────╮  ╭─────────────────╮
│  😴 Sono         │  │  🍅 Pomodoros   │
│  7.5h            │  │  11             │
│  Q=9/10          │  │  completos hoje │
│  20:30→04:00     │  │                 │
╰─────────────────╯  ╰─────────────────╯
╭─────────────────╮  ╭─────────────────╮
│  💻 Hardwork     │  │  ⚡ Energia/Foco│
│  4h00            │  │  8/9            │
│  240/240min      │  │  média 8/10     │
│  100% atingido   │  │  E8 F9          │
╰─────────────────╯  ╰─────────────────╯

╭───  🍅 Pomodoros (S1 manhã · S2 tarde · S3 noite)  ──────────────╮
│  S1 manhã   ▣ ▣ ▣ ▢   3/4                                        │
│  S2 tarde   ▣ ▣ ▣ ▣   4/4                                        │
│  S3 noite   ▣ ▣ ▢ ▢   2/4                                        │
╰─────────────────────────────────────────────────────────────────────╯
╭───  📦 Time Blocks (5 blocos, 240min)  ───────────────────────────╮
│  ████ 04h Sleep                                                   │
│  ████████████ 06h Workout                                         │
│  ████████ 10h Deep Work                                           │
│  █████ 14h Lunch + Rest                                           │
╰─────────────────────────────────────────────────────────────────────╯
╭───  Atividade do Dia  ──────────────────────────────────────────╮
│  🕐 Rotinas logs     8   (ok)                                    │
│  🔧 Ajustes finos    1   (ok)                                    │
│  📓 Journal          ✓   (ok)                                    │
│  📦 Blocos           5   (ok)                                    │
╰──────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────╮
│  →  Iniciar Manhã → opção 1 do menu (sleep retroativo + ...)    │
╰──────────────────────────────────────────────────────────────────╯
```

---

## SCR-005 — Demo Stats

**Comando de acesso:** `operational demo show`
**Tipo:** Output tabular (estatísticas agregadas)
**Arquivo renderizador:** `src/operational/cli/seed.py` (saída via `typer.echo`)
**Complexidade:** Baixa
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio:** Lista vazia / "0 entities of type X"
**Estado com dados:** Tabela compacta com count por entity_type

### Wireframe

```text
Demo data — entity counts:
  routine:        28
  routine_log:    28
  time_block:     35
  journal_entry:  7
  habit:          8
  sleep_record:   7
  pomodoro_round: 45
  policy_decision: 7
  policy_setpoints: 4
  ajuste_fino:    7
  day_context:    7
  daily_reflection: 5
  lunch_record:   7
  transicao:      35
```

---

## SCR-006 — Demo Dataset List

**Comando de acesso:** `operational demo dataset [NOME]`
**Tipo:** Output tabular (lista de datasets disponíveis)
**Arquivo renderizador:** `src/operational/cli/commands/demo_cmd.py:182-235`
**Complexidade:** Baixa
**Modo JSON:** Sim (--json)
**Dataset requerido:** Nenhum (a tela LISTA os datasets)
**Estado vazio:** Mostra "No datasets found" se a pasta `docs/` estiver ausente
**Estado com dados:** Lista cada dataset com status (OK/MISSING) e caminho

### Wireframe

```text
Active dataset: production

  [OK]      synthetic   — 7 days of synthetic PAV mock data
                 C:\...\docs\synthetic.csv
  [OK]      golden      — 7 days of golden PAV reference data
                 C:\...\docs\golden.csv
  [MISSING] production  — current production data (lives in ~/.time-tasker/)
                 C:\Users\...\json\routines.json
```

---

## SCR-007 — Doctor

**Comando de acesso:** `operational doctor [--json]`
**Tipo:** Diagnóstico
**Arquivo renderizador:** `src/operational/cli/commands/doctor_cmd.py:191-250`
**Complexidade:** Média
**Modo JSON:** Sim (--json)
**Dataset requerido:** Nenhum
**Estado vazio:** Sempre tem dados (verifica o ambiente)
**Estado com dados:** Painel Rich com 7 checks (Python, packages, state_dir, datasets, constants, console, files_sanity)

### Wireframe

```text
╭───  DOCTOR - OK  ──────────────────────────────────────────────────╮
│  [green]OK[/green]  python         v3.14.0                         │
│  [green]OK[/green]  packages       typer=0.12.0, rich=13.7.0, ...  │
│  [green]OK[/green]  state_dir      C:\Users\...\json (14 files)    │
│  [green]OK[/green]  datasets       active=golden                   │
│  [green]OK[/green]  constants      6 loaded                        │
│  [green]OK[/green]  console        captured=False, encoding=utf-8  │
│  [green]OK[/green]  files_sanity   14 files, 0 issues              │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## SCR-008 — Routine List / Create

**Comando de acesso:** `operational routine list` / `operational routine create NOME PERÍODO TIPO`
**Tipo:** Form + tabela
**Arquivo renderizador:** `src/operational/cli/commands/routine_cmd.py`
**Complexidade:** Média
**Modo JSON:** Sim (--json em list e create)
**Dataset requerido:** qualquer
**Estado vazio (list):** "Nenhuma rotina cadastrada. Use `routine create`."
**Estado com dados (list):** Tabela com Nome, Período, Tipo, Mandatory, Duração
**Estado vazio (create):** Form interativo com prompts
**Estado com dados (create):** Linha "✓ Rotina criada: {id}"

### Wireframe (list com dados)

```text
╭───  📋 Rotinas (4)  ──────────────────────────────────────────────╮
│  Nome                  Período  Tipo      Mandatória  Duração      │
│  Acordar + Hidratação  MANHA    ENTRY     sim         25min         │
│  Deep Work Feature     MANHA    CORE      sim         210min        │
│  Code Review           TARDE    CORE      não         120min        │
│  Shutdown              NOITE    EXIT      sim         30min         │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## SCR-009 — Block List / Create

**Comando de acesso:** `operational block list` / `operational block create PERÍODO [-l LABEL]`
**Tipo:** Form + tabela
**Arquivo renderizador:** `src/operational/cli/commands/block_cmd.py`
**Complexidade:** Média
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio (list):** "Nenhum bloco. Use `block create`."
**Estado com dados (list):** Tabela com Período, Label, Início, Fim, Duração

### Wireframe (list com dados)

```text
╭───  📦 Blocos de Tempo (5)  ──────────────────────────────────────╮
│  Período  Label                          Início    Fim       Min  │
│  MANHA    Deep Work - JWT                04:00     08:00     240  │
│  TARDE    Code Review + Refatoração      08:30     12:00     210  │
│  MANHA    Workout + Meditação            04:25     04:30      5   │
│  NOITE    Shutdown + Reflexão            21:00     21:30     30   │
│  TARDE    Admin + Email                  14:00     15:30     90   │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## SCR-010 — Journal List / Create

**Comando de acesso:** `operational journal list` / `operational journal create --text TEXTO`
**Tipo:** Form + tabela
**Arquivo renderizador:** `src/operational/cli/commands/journal_cmd.py`
**Complexidade:** Baixa
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio (list):** "Nenhum journal. Use `journal create`."
**Estado com dados (list):** Tabela com Data, Energia, Foco, Humor manhã, Humor noite, Texto (preview)

### Wireframe (list com dados)

```text
╭───  📓 Journals (5)  ────────────────────────────────────────────╮
│  Data       E   F   Manhã  Noite  Preview                          │
│  2026-06-02 8   9   bom    bom    DIA PERFEITO. Acordei 04:00...  │
│  2026-06-03 6   6   regular regular  DESVIO LEVE. Acordei 05:30.  │
│  2026-06-04 5   4   ruim   regular  Modo Hardcore. Dormi 4h.     │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## SCR-011 — Habit List / Create

**Comando de acesso:** `operational habit list` / `operational habit create`
**Tipo:** Form + tabela
**Arquivo renderizador:** `src/operational/cli/commands/habit_cmd.py`
**Complexidade:** Baixa
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio (list):** "Nenhum hábito. Use `habit create`."
**Estado com dados (list):** Tabela com Nome, Categoria, Resistência, Peso Q_HE, Frequência

### Wireframe (list com dados)

```text
╭───  💪 Habits (8)  ───────────────────────────────────────────────╮
│  Nome                  Categoria      Resistência  Peso QHE  Freq.  │
│  Beber 2L de Agua      physiological  2.0          0.8       DAILY  │
│  Meditar 10min         ritual         3.0          0.6       DAILY  │
│  Alongamento Matinal   physiological  4.0          0.5       DAILY  │
│  Ler 30min Técnico     cognitive      5.0          0.7       DAILY  │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## SCR-012 — Metric Form (Sleep / Energy)

**Comando de acesso:** `operational metric sleep [-q -bh -bm -wh -wm]` / `operational metric energy -e E -f F`
**Tipo:** Form (criação de métrica)
**Arquivo renderizador:** `src/operational/cli/commands/metric_cmd.py`
**Complexidade:** Baixa
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio:** N/A (form é sempre bem-sucedido se Typer valida)
**Estado com dados:** Linha de confirmação "✓ Sono registrado: id"

### Wireframe (modo verboso, com input_summary)

```text
╭───  📝 Registrando sono  ──────────────────────────────────────────╮
│  Parâmetro   Valor          Flag                                  │
│  date        2026-06-08     -d / --date                           │
│  quality     8              -q / --quality                        │
│  bedtime     20:30          -bh / --bed-hour + -bm / --bed-minute │
│  wake        04:00          -wh / --wake-hour + -wm / --wake-minute│
╰─────────────────────────────────────────────────────────────────────╯
  [bold blue]✓[/bold blue] Sono registrado: [bold]sle_2026_06_08[/bold]
    [dim]data: 2026-06-08  ·  Q=8/10 🟢 bom  ·  7.5h[/dim]
```

---

## SCR-013 — Policy Decisions

**Comando de acesso:** `operational policy list` / `operational policy setpoints`
**Tipo:** Output tabular (decisões históricas e setpoints)
**Arquivo renderizador:** `src/operational/cli/commands/policy_cmd.py`
**Complexidade:** Média
**Modo JSON:** Sim (--json em list)
**Dataset requerido:** qualquer
**Estado vazio (list):** "Nenhuma decisão. Use `policy record`."
**Estado com dados (list):** Tabela com Data, State, Severity, Rationale

### Wireframe (list com dados)

```text
╭───  ⚙️  Policy Decisions (3)  ──────────────────────────────────────╮
│  Data       State      Sev     Rationale                           │
│  2026-06-02 MAINTAIN   [ok]    Dentro do padrao ouro. Manter.      │
│  2026-06-03 REDUCE     [warn]  Desvio leve. Recomendar sono extra. │
│  2026-06-04 MAINTAIN   [info]  Recuperado. Regime estavel.         │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## SCR-014 — Reflect (OKR Form)

**Comando de acesso:** `operational reflect entrada [-d YYYY-MM-DD]` / `operational reflect saida [-d YYYY-MM-DD]`
**Tipo:** Form interativo (multi-prompt)
**Arquivo renderizador:** `src/operational/cli/commands/reflect_cmd.py`
**Complexidade:** Média
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio:** Form é sempre mostrado; prompts têm `default=""` para skip
**Estado com dados:** "✔ OKRs de saída registrados!"

### Wireframe (modo interativo)

```text
🌙 OKRs de Saída — 2026-06-08

Reflita sobre HOJE para alimentar o sistema

  O que deu certo hoje (execução sistemática) (separar por ;) ['']: Feature JWT completa
  O que deu errado (equívocos) (separar por ;) ['']: Tentei compensar workout a tarde
  Maior aprendizado do dia (antítese + síntese) ['']: Sono define o dia
  Ajustes finos para amanhã (separar por ;) ['']: Dormir 20:00
  Estado final do dia (1-10) [6]: 8

[bold green]✔ OKRs de saída registrados![/bold green]
```

---

## SCR-015 — Lunch Form

**Comando de acesso:** `operational lunch create [-d -e -r -p -n]`
**Tipo:** Form (registro estruturado)
**Arquivo renderizador:** `src/operational/cli/commands/lunch_cmd.py`
**Complexidade:** Baixa
**Modo JSON:** Sim (--json)
**Dataset requerido:** qualquer
**Estado vazio:** N/A
**Estado com dados:** "Lunch 2026-06-08 / eat=5min rest=30min total=35min (✓) / ✅ OK"

### Wireframe

```text
╭───  📝 Registrando almoço  ──────────────────────────────────────╮
│  Parâmetro   Valor     Flag                                       │
│  date        2026-06-08 -d / --date                                │
│  eat         5         -e / --eat                                  │
│  rest        30        -r / --rest                                 │
│  pesado      False     -p / --pesado                               │
╰──────────────────────────────────────────────────────────────────╯

  [bold]Lunch 2026-06-08[/bold]
    eat=5min  rest=30min  total=35min  (✓)
    ✅ OK
```

---

## Onde ler mais

- **Estados de cada tela (vazio, loading, com dados, erro)** →
  [`02-matriz-estados.md`](02-matriz-estados.md)
- **Detalhes dos prompts interativos das telas Form** →
  [`03-modais-e-abas.md`](03-modais-e-abas.md)
- **Componentes visuais por trás de cada wireframe** →
  [`../02-componentes/`](../02-componentes/)
