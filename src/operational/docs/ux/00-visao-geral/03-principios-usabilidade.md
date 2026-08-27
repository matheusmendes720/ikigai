# 03 — Princípios de Usabilidade

> Este documento lista os 8 princípios de design que guiam as decisões
> de UX no `operational` CLI. São inspirados em heurísticas de Nielsen
> (1994) e Don Norman (*The Design of Everyday Things*), **adaptados
> para um terminal-based TUI com Rich**. Cada princípio tem 1 parágrafo
> explicativo, 1 exemplo concreto do código, e 1 violação típica.

A motivação é simples: o usuário lê o dashboard a 60fps (mental),
não a 60Hz. Cada caractere Unicode, cada cor, cada espaçamento é
**carga cognitiva** se for redundante, **atalho cognitivo** se for
consistente. Os 8 princípios abaixo garantem que toda escolha de
design contribua para um dos dois.

---

## 1. Visibilidade do estado do sistema

**Princípio:** O usuário deve sempre saber *onde está*, *o que está
logado*, e *o que vai acontecer a seguir*. Em um TUI, "onde estou"
significa: em qual tela, com qual dataset, em qual data, com qual
período do dia (MANHÃ/TARDE/NOITE).

**Exemplo concreto:** O header do `state show` (`cli/commands/state_cmd.py:148-162`)
mostra `STATE · 2026-06-08 · 🌅 MANHA` — três informações em uma linha,
cada uma com cor distinta. O home menu sempre abre com a data de hoje
(`cli/home.py:84-93`) e o `default="5"` (Prompt.ask) significa que
apertar Enter mostra o dashboard, não a primeira opção do menu.

**Violação típica:** Esconder o dataset ativo. O comando
`operational report daily` em modo `--json` omite qual dataset está
em uso; só o `doctor --json` mostra. O Dev Solo pode esquecer que
está em `golden` (teste) e tomar decisões com dados sintéticos.
**Mitigação futura:** incluir `"active_dataset"` no payload JSON de
todo comando que lê state.

---

## 2. Match entre sistema e mundo real (PAV)

**Princípio:** A linguagem do sistema deve ser a linguagem do
usuário. PAV (Produtividade Algorítmica Visual) é o vocabulário do
projeto — CURSO, LIVRE, HARDCORE, DESCANSO são tipos de dia que o
Dev Solo já conhece. PUSH/MAINTAIN/REDUCE/RECOVER são regimes que
ele lê na literatura de cybernetic productivity.

**Exemplo concreto:** O relatório diário chama-se `DIA PERFEITO`
quando o dia cumpre Q1 + sono ≥ 7h + 4 pomodoros; `DESVIO LEVE`
quando Q4 ou sono 5-7h; `MODO HARDCORE` quando Q3 ou sono < 5h. A
narrativa segue a taxonomia PAV V3, não jargão de negócio
(`cli/commands/demo_cmd.py:32-36`).

**Violação típica:** Usar jargão técnico em vez de PAV. Ex: chamar
o regime PUSH de "high-intensity state" (genérico) em vez de "PUSH"
(do PAV). Ou pior, traduzir PUSH para "Empurrar" em português —
quebra o contrato com a literatura. **Regra:** se o termo existe no
glossário PAV, use o termo PAV. Se não existe, crie e adicione ao
glossário (ver [`04-glossario-dominio.md`](04-glossario-dominio.md)).

---

## 3. Controle do usuário e liberdade

**Princípio:** O usuário deve poder desfazer, sobrescrever, e
truncar a saída. Em CLI, isso significa: `--json` para piping,
`--date` para re-registrar, `--replace` para re-importar, e o
`Ctrl+C`/`KeyboardInterrupt` sempre reseta o estado para o
próximo comando.

**Exemplo concreto:** O comando `metric sleep -d 2026-06-08`
permite re-registrar o sono de qualquer data retroativa
(`cli/commands/metric_cmd.py:60-69`). O `metric sleep` faz upsert
pelo `id` derivado da data (`make_sleep_record` em
`meta/factories.py`), então rodar duas vezes com a mesma data
**substitui** o registro anterior — não duplica. Para sair de um
flow interativo, o usuário pode dar `Ctrl+C`; o `home()` loop em
`cli/home.py:100-115` captura via `try/except KeyboardInterrupt`
implicitamente, e o `Prompt.ask` da Rich trata entrada vazia como
default.

**Violação típica:** Não oferecer `--json`. O `state show` aceita
`--json` (`cli/commands/state_cmd.py:96-116`), mas o `home` não
(porque é interativo por design). A pergunta a fazer: *o usuário
pode precisar desta saída em um pipeline?* Se sim, `--json` é
obrigatório (ver regra de arquitetura: "Support `--json` on all
new commands wherever feasible", `docs/AGENTS.md` §6.3).

---

## 4. Consistência e padrões

**Princípio:** Mesma flag, mesma cor, mesma severidade, mesmo ícone
em toda parte. A consistência é o que permite ao usuário
**prever** o comportamento de um comando novo a partir de um que
ele já conhece.

**Exemplo concreto:**
- `--json` aparece em **todos** os 12 sub-comandos
  (`routine`, `block`, `journal`, `habit`, `metric`, `policy`,
  `reflect`, `report`, `state`, `lunch`, `demo`, `doctor`).
- Severidade `ok` = verde, `warn` = amarelo, `crit` = vermelho em
  **todo** lugar (centralizado em `SEVERITY_COLOR`,
  `ui/components.py:87-94`).
- Ícones de período: 🌅 MANHÃ, 💻 TARDE, 🌙 NOITE em **todo**
  lugar (`PERIOD_ICON`, `ui/components.py:53-57`).
- Quadrante emoji 🏆 Q1, 🟢 Q2, 🚨 Q3, ⚠️ Q4 consistente entre
  daily report, weekly report, e state dashboard.

**Violação típica:** Inserir uma nova cor que não está no `COLORS`
dict. Ex: usar `style="lightgreen"` em um controller novo. A
disciplina é "estender, não fork" (ver
`docs/tui/04-COLOR-PALETTE.md` §"How to add a new color").

---

## 5. Prevenção de erro

**Princípio:** É melhor o sistema rejeitar dados ruins na entrada
do que o usuário descobrir 3 dias depois que o sono foi logado com
`quality=88` (fora do range 1-10). Pydantic validation no boundary
é o mecanismo primário; `doctor` é o secundário (auditoria).

**Exemplo concreto:** A entidade `SleepRecord.quality_score` é
`int = Field(ge=1, le=10)` em `entities/...`. Typer CLI adiciona
`min=1, max=10` na flag (`cli/commands/metric_cmd.py:61`). Se o
usuário digitar `--quality 15`, Typer aborta com
`Invalid value for '--quality'` antes mesmo de chamar a entidade.
Para erros mais profundos (ex: horário de acordar impossível), o
`core/services.py:require_sleep_record` levanta `FaltaDadosError`,
que é capturada pelo controller e renderizada como `error_panel`
vermelha.

**Violação típica:** Aceitar entrada livre e validar depois. Ex:
pedir `notas` (texto livre) e tentar processar como data. **Regra:**
toda entrada de usuário que vai virar um campo tipado deve passar
por Pydantic ou Typer validation; nada de `int(input())` cru.

---

## 6. Reconhecimento em vez de recordação

**Princípio:** O usuário não deve precisar memorizar flags,
sub-comandos ou valores válidos. Menus numerados, `--help`
rico, e defaults sensatos reduzem a carga de memorização.

**Exemplo concreto:** O home menu tem 10 opções numeradas (1-10 + `q`),
cada uma com **descrição inline** (`MENU_ITEMS` em `cli/home.py:33-46`).
Em vez de "qual é o sub-comando de check-in?", o usuário lê "4. ⚡
Check-in Rápido — 30s: registrar energia/foco do momento". Para
esquecer qual é a flag de data, ele pode rodar
`operational metric sleep --help` e ver `-d, --date TEXT`. O
doctor tem `--json` documentado, e o
`flag_glossary_panel` em `cli/renderers.py:505-511` é um painel
visual que lista todas as flags do sistema.

**Violação típica:** Usar flags com 1 letra sem motivo. Ex: `-d`
para `--date` é ok (curto e óbvio), mas `-q` para `--quality` é
menos óbvio (q=quality? ou q=query?). A mitigação: `default` no
Prompt.ask (`cli/home.py:170-174`) para flows interativos, e
`flag_legend` em `input_summary` (`cli/renderers.py:441-460`) para
modo não-interativo.

---

## 7. Flexibilidade e eficiência

**Princípio:** O sistema deve servir tanto o usuário casual
(precisa de prompts) quanto o expert (quer 1-liner não-interativo).
A flag `--json` cobre o expert; o menu interativo cobre o casual;
os dois caminhos produzem a mesma persistência (upsert no mesmo
repo), então trocar entre eles é seguro.

**Exemplo concreto:** O comando `metric sleep` tem 2 modos:
1. **Interativo:** `operational home` → opção 1 → 5 prompts
   sequenciais com defaults.
2. **Não-interativo:** `operational metric sleep -q 8 -bh 20 -bm 30 -wh 4 -wm 0`
   em 1 linha.

Os dois caminhos terminam chamando o mesmo `make_sleep_record()`
e o mesmo `sleep_records.upsert()`. O estado é idêntico.

**Violação típica:** Forçar o usuário a passar por todos os prompts,
mesmo quando ele quer editar 1 campo. Ex: se o flow do home menu
sempre pedir "data" (mesmo sendo hoje), o expert fica frustrado.
**Mitigação atual:** o `default="hoje"` implícito em quase todos
os prompts de data (`-d YYYY-MM-DD` é opcional, default `date.today()`
em todos os controllers).

---

## 8. Estética minimalista

**Princípio:** O dashboard é lido em 120 colunas. Cada caractere
conta. Nada de informação redundante, nada de decoração pura.
Os caracteres Unicode (`▁▂▃▄▅▆▇█`, `▣ ▢`, `◆ ✗ ▲`, `╭─╮`) são
**substância** (carregam informação), não decoração.

**Exemplo concreto:** O sparkline `▁▂▃▄▅▆▇█` codifica 7 valores
numéricos em 7 caracteres visuais. A escala de 8 níveis
(▁=min, █=max) é uma escolha deliberada: mais que 8 vira
ilegível; menos que 8 perde precisão. O pomodoros grid usa
`▣` (cheio, verde) vs `▢` (vazio, cinza) — o usuário bate o olho
e conta `▣▣▣▢` = 3/4 sem precisar ler o número.

A escolha de **largura fixa 120 colunas** (`CONSOLE_WIDTH` em
`ui/__init__.py:31`) garante que o dashboard cabe em qualquer
terminal moderno sem wrap, e que o Cartesian plane (18×7) sempre
fica em Q1/Q2/Q3/Q4 correto, sem distorção.

**Violação típica:** Emojis decorativos que não carregam info.
Ex: 🎉 em um "parabéns!" sem cor/severidade. Ou enfeites de
linha (`═══════════`) que ocupam espaço mas não informam.
**Regra:** se o caractere sumir e o sentido continuar intacto, ele
é decoração e deve sair.

---

## Como esses princípios guiam decisões novas

Quando você for adicionar uma feature nova, pergunte-se:

1. **Visibilidade:** O usuário vai saber em que tela está, com
   qual data, em qual dataset? Se não, o header está incompleto.
2. **Match PAV:** O termo que estou usando está no glossário? Se
   não, crie e adicione.
3. **Controle:** Tem `--json`? Tem `--date` retroativo? Tem
   `Ctrl+C` seguro?
4. **Consistência:** A cor é de `COLORS`? O ícone é de
   `PERIOD_ICON`? A severidade é de `SEVERITY_COLOR`?
5. **Prevenção:** O dado é validado por Pydantic/Typer? O
   boundary rejeita entrada ruim?
6. **Reconhecimento:** Tem `--help`? O número do menu é óbvio?
7. **Flexibilidade:** Tem modo interativo E não-interativo?
8. **Estética:** Cada caractere Unicode carrega informação? A
   largura cabe em 120 colunas?

Se a resposta a qualquer uma for "não", revise antes de mergar.

---

## Onde ler mais

- **Glossário dos termos PAV** referenciados nos princípios 2 e 6 →
  [`04-glossario-dominio.md`](04-glossario-dominio.md)
- **Paleta de cores concreta** que o princípio 4 invoca →
  [`../../tui/04-COLOR-PALETTE.md`](../../tui/04-COLOR-PALETTE.md)
- **Catálogo de componentes** que o princípio 8 referencia →
  [`../02-componentes/`](../02-componentes/)
