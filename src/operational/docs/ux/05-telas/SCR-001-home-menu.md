# SCR-001 — Home Menu (Tela Inicial Interativa)

**Comando:** `operational home` (também: `operational` sem sub-comando, ou `operational menu`)
**Arquivo renderizador:** `cli/home.py:118-131` (`_show_menu`) + `cli/home.py:100-115` (loop principal `home()`)
**Arquivo de comando:** `src/operational/cli/home.py`
**Tipo:** Menu interativo numerado (não é form, é dispatcher de flows)
**Modo JSON:** Não aplicável (é UI de navegação; nenhum sub-comando aceita `--json` no nível do menu)
**Validação:** `rich.prompt.Prompt.ask(..., choices=[...])` — Rich re-prompt automático em entrada inválida (`home.py:106-110`)

## Propósito

O **Home Menu** é a porta de entrada do `operational` CLI. Diferente de centralizar CRUDs por entidade (`routine`, `block`, `journal`, ...), o menu agrupa por **momento do dia** (acordar, almoçar, encerrar, check-in) e por **tipo de leitura** (dashboard, relatórios, dados, política, demo, sistema). O valor gerado é:

- **Aterrissagem rápida** — `default="5"` no prompt principal (`home.py:109`) faz Enter abrir o Dashboard, então o usuário sempre cai em "onde estou" se não decidir nada.
- **Workflows compostos** — opções `1-4` orquestram 3-6 sub-comandos em sequência (morning flow: sleep + ENTRY routine + MANHA block).
- **Descoberta** — opções `6-9` abrem sub-menus numerados com o mesmo padrão de `Prompt.ask`, mantendo a UX consistente em profundidade.
- **Escape determinístico** — `q` (sub-comando "Sair") ou `b` (em sub-menus) é a saída; o loop `while True` (`home.py:102`) garante que o menu sempre volta.

## Usuário-alvo

- **Primário:** operador solo do `operational` (PAV practitioner). Usa o CLI 2-5× por dia: manhã (iniciar), tarde (almoço + foco), noite (encerrar), e em momentos oportunos (check-in rápido).
- **Momento de uso:** logo após `operational` no terminal — é a primeira tela renderizada.
- **Frequência:** alta no início do dia, média no meio, alta no encerramento.

## Entradas

- **Linha de comando:** `operational home` ou simplesmente `operational` (porque `home` é o callback default; ver `cli/app.py`).
- **Padrão de uso:** o usuário digita `1-10` ou `q` no prompt "Choose". Em sub-menus, `b` significa "voltar".

## Saídas

- **Persistência:** indireta — o menu não escreve em arquivo; delega para sub-comandos via `_run_cmd(args)` (`home.py:49-77`), que roda o Typer app **in-process** e captura stdout.
- **Confirmação:** cada sub-comando (`routine create`, `block create`, etc.) imprime seu próprio "✓ Criado" com ID.
- **Redirecionamento:** sempre volta ao menu após `Prompt.ask("\n[dim]Press Enter to continue[/dim]")` (`home.py:76`).

## Modos de uso

O Home Menu **só tem um modo**: interativo. Não há flags que pulem o menu — para isso, invoque diretamente o sub-comando:

```bash
operational                        # abre o Home Menu (loop infinito)
operational home                   # mesmo que acima
operational routine create "X" MANHA CORE  # pula o menu, vai direto
operational report daily --json    # pula o menu, gera relatório
```

A escolha entre "abrir menu" e "comando direto" é por conveniência, não por flag. O menu é um **atalho de discovery**; quem já sabe o que quer ignora o menu.

## Argumentos e flags (TODOS)

O comando `operational home` **não aceita argumentos nem flags** (`home.py:100`). Toda a interação é via `Prompt.ask` no loop.

| Parâmetro | Tipo | Default | Obrigatório | Validação | Exemplo |
|---|---|---|---|---|---|
| `choice` (interno) | str | `"5"` | sim | choices=`["1","2","3","4","5","6","7","8","9","10","q"]` | `5` → Dashboard |

A validação é feita pelo próprio Rich: `Prompt.ask(..., choices=...)` re-promptiza se o input não estiver na lista (`home.py:106-110`).

## Wireframe passo-a-passo

### Estado: Tela principal (loop primeira iteração)

```
╭─────────────────────────────────────────────────────────────────────╮
│  ⚡ TIME-TASKER  v0.1.0  |  2026-06-08                              │
╰─────────────────────────────────────────────────────────────────────╯
Key  Action                       Description
─────────────────────────────────────────────────────────────────
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

Note que `Choose [5]` é o `default` mostrado por Rich. Apertar Enter aceita "5" → Dashboard.

### Estado: Após escolher opção `1` (Iniciar Manhã — flow)

```
╭─────────────────────────────────────────────────────────────────────╮
│  ⚡ TIME-TASKER  v0.1.0  |  2026-06-08  |  🌅 Iniciar Manhã         │
╰─────────────────────────────────────────────────────────────────────╯

Esta rotina cobre:
  1. Registrar sono (retroativo)
  2. Criar rotina ENTRY (acordar)
  3. Criar bloco MANHA (workout + meditação)

Continuar? [y]: y
? Qualidade do sono (1-10) [8]: 8
? Hora que dormiu (0-23) [20]: 23
? Minuto que dormiu (0-59) [30]: 45
? Hora que acordou (0-23) [4]: 6
? Minuto que acordou (0-59) [0]: 30
  ✓ Sono registrado: sle_2026_06_08
  ✓ Rotina criada: Acordar (MANHA · ENTRY)
  ✓ Bloco criado: Morning Workout + Meditação
✔ Manhã iniciada!

Press Enter to continue █
```

### Estado: Após escolher opção `6` (sub-menu Relatórios)

```
╭─────────────────────────────────────────────────────────────────────╮
│  ⚡ TIME-TASKER  v0.1.0  |  2026-06-08  |  📈 Relatórios           │
╰─────────────────────────────────────────────────────────────────────╯
1  Relatório diário — hoje
2  Relatório diário — 2026-06-08 (--date)
3  Relatório diário — JSON
4  Relatório semanal
5  Relatório semanal — JSON
6  Dashboard do dia
7  Dashboard JSON

b  🔙 Back to main menu

Choose [1]: █
```

Note a linha `b` — é o escape hatch para sub-menus (`home.py:308`, `home.py:314-315`).

### Estado: Entrada inválida (re-prompt automático do Rich)

```
Choose [5]: x
# (Rich re-promptiza silenciosamente — o terminal mostra o mesmo prompt)
Choose [5]: 11
Choose [5]: 0
Choose [5]: 5   # entrada aceita
```

`Prompt.ask(choices=...)` re-promptiza sem mensagem de erro visível; o terminal apenas mostra o prompt de novo. Isso é o comportamento default do Rich.

## Validação e erros

| Cenário | Comportamento |
|---|---|
| Input não-numérico (`"x"`, `"cinco"`) | Rich re-promptiza silenciosamente |
| Número fora do range (`"0"`, `"11"`, `"42"`) | Rich re-promptiza silenciosamente |
| `Ctrl+C` (KeyboardInterrupt) | `run()` em `home.py:474-479` captura, limpa tela, imprime "Até logo! 🚀" e sai. Nenhuma persistência ocorre porque o menu não escreve direto. |
| `Ctrl+D` (EOF) | Mesma rota que `Ctrl+C` — `KeyboardInterrupt` ou `EOFError` tratado por `run()` |
| Comando interno falha (sub-comando joga exception) | `_run_cmd` (`home.py:68-75`) captura e imprime Panel vermelho: `[red]TypeError: ...[/red]` com título "Error". Volta ao menu após "Press Enter to continue". |

> **Aviso didático:** o re-prompt silencioso do Rich é elegante mas confunde novatos — se você digitar errado, não aparece mensagem "Opção inválida, tente de novo". O prompt reaparece *idêntico* ao anterior.

## Estados (5)

| Estado | Wireframe | Notas |
|---|---|---|
| **Inicial** (1ª iteração do loop) | Tela principal acima | Cabeçalho cyan + tabela de 12 linhas + prompt |
| **Em sub-menu** | Sub-menu Relatórios acima | Cabeçalho cyan + tabela numerada + linha `b` de escape |
| **Em flow** (1-4) | Flow Manhã acima | Cabeçalho com subtítulo + sequência de `Prompt.ask` + execução in-process |
| **Erro interno** (sub-comando falhou) | Painel vermelho "Error: ..." | `_run_cmd` mostra `Panel(f"[red]{type(e).__name__}: {e}", ...)` (`home.py:69-75`) |
| **Saída** (`q` ou `Ctrl+C`) | Tela limpa + "Até logo! 🚀" | `_clear()` + `console.print("[green]Até logo! 🚀[/green]")` + `sys.exit(0)` |

## Comportamento interativo

- **Tipo de prompt:** exclusivamente `rich.prompt.Prompt.ask` com `choices=[...]` (`home.py:106-110`).
- **Validação inline:** Sim — Rich re-promptiza imediatamente em input inválido (sem mensagem de erro).
- **Defaults:** `default="5"` no prompt principal força o usuário a cair no Dashboard se apertar Enter; sub-menus usam `default="1"` (`home.py:312`).
- **Histórico:** não há (Rich `Prompt.ask` não tem readline-like history). O `typer` e o Rich não compartilham histórico entre prompts.
- **Ctrl+C:** abort clean — `run()` (`home.py:474-479`) captura `KeyboardInterrupt` no nível mais alto, imprime despedida e sai.
- **Ctrl+D (EOF):** mesma rota; cai em `EOFError` ou no `KeyboardInterrupt` propagado.
- **Timeout:** não há — `Prompt.ask` bloqueia indefinidamente. Se você precisa de timeout, não use o menu; invoque sub-comandos via `subprocess.run` externo.

> **⚠ Atenção:** o menu é `while True` (`home.py:102`) e **não tem idle timeout**. Se você abrir o menu e sair do terminal, o processo fica pendurado.

## Comandos relacionados

- `state show` — dashboard que o item `5` invoca (`home.py:283`).
- `report daily` / `report weekly` — alvo do item `6` (sub-menu Relatórios).
- `routine create`, `block create`, `metric sleep`, `metric energy`, `journal create` — alvos dos flows 1-4.
- `demo seed`, `demo clear` — alvos do item `9` (sub-menu Demo).

## Riscos de usabilidade

Específicos do Home Menu:

1. **Re-prompt silencioso do Rich** — input inválido não emite mensagem; o prompt reaparece idêntico. Inexperiente pode pensar que "não está respondendo".
2. **Default `"5"` no prompt principal** — útil para "aterrissagem rápida", mas **se o usuário digitar 5 pensando ser o número 5 explícito**, o Enter é equivalente. Considere remover o default em produção.
3. **Header com `date.today()`** — congelado no momento do `_header()` (`home.py:84-93`). Se a sessão cruza meia-noite, o header mente. Mitigação: `sub-menu` com refresh de header a cada iteração.
4. **Sem breadcrumbs em sub-menus** — ao entrar em "Relatórios" via item `6`, não há indicação visual de "você está em Menu > Relatórios". A linha `b` é o único hint.
5. **Sem undo** — `demo clear` é destrutivo sem confirmação (a confirmação está em `_menu_demo` se o usuário for ao item `5` mas a flag `--yes` não existe).
6. **Texto truncado em colunas de 28 chars** — "Política & Ajuste" cabe, mas "Diffs de Estado" não. Strings longas são cortadas.
7. **Número `10` (2 dígitos) vs `1`-`9`** — única exceção; a tecla `1` pode ser confundida com `10` se o usuário digitar rápido. Mitigação: `choices` força a string completa.

## Métricas de sucesso

- **Tempo médio para escolher opção:** target <2s. (Apenas uma tecla + Enter.)
- **Taxa de erro de input:** target <5%. (Re-prompt silencioso não é visível, então o usuário erra, vê o prompt de novo, e corrige.)
- **Taxa de uso de sub-comando direto vs menu:** target 40% menu / 60% direto. (Usuário expert deve preferir `operational routine create ...` direto.)
- **Número de iterações de loop até exit:** observacional. Mediana target = 1-2 iterações para quem vai ao dashboard; 5-10 para quem explora.

## Onde aparece

- **Auto-trigger:** `operational` sem argumentos abre o menu (`home` é o callback default; ver `cli/app.py:callback`).
- **Não há invocação programática** — o menu é interativo por design.

## Notas de implementação

- **File:line refs:**
  - `cli/home.py:33-46` — `MENU_ITEMS` (lista das 12 opções incluindo `q`).
  - `cli/home.py:100-115` — loop `home()` principal.
  - `cli/home.py:118-131` — `_show_menu()` (renderização da tabela).
  - `cli/home.py:49-77` — `_run_cmd()` (orquestrador in-process).
  - `cli/home.py:134-150` — `_route()` (dispatcher para handlers).
  - `cli/home.py:297-318` — `_submenu()` (genérico para opções 6-9).
- **Como adicionar uma nova opção:** (1) adicionar tupla em `MENU_ITEMS` (`home.py:33-46`); (2) registrar handler em `_route` (`home.py:136-147`); (3) se for `1X` (2 dígitos), adicionar `"1X"` em `choices` do prompt (`home.py:108`). Para sub-menus, basta adicionar item em `_menu_*` correspondente.
- **Como mudar validação:** `Prompt.ask` aceita `choices=[...]` e `default=...` — ambos controlam entrada. Para validar com regex ou lógica custom, envolva em `try/except ValueError`.
- **Onde fica o estado:** o menu é stateless (não tem `id` próprio). Cada sub-comando persiste em `routines.json`, `time_blocks.json`, etc., no `state.py` registry.
