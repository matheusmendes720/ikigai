# 01 — Heurísticas de Nielsen aplicadas ao CLI

> Avaliação heurística do `operational` CLI à luz das **10 heurísticas de usabilidade de Jakob Nielsen** (1994, rev. 2020). Cada heurística é apresentada com:
> 1. Descrição canônica
> 2. Aplicação específica no CLI
> 3. Exemplos bons (o que está OK)
> 4. Exemplos ruins (o que falta)
> 5. Onde melhorar (ações concretas + file:line refs)
>
> **Status atual:** ⭐⭐⭐ (3/5 estrelas). O CLI é coerente e legível, mas peca em feedback de erro, prevenção e acessibilidade. Ver UX-001 a UX-020 em `03-riscos-conhecidos.md`.

---

## H1 — Visibilidade do status do sistema

> *"The system should always keep users informed about what is going on, through appropriate feedback within reasonable time."*

### Aplicação no CLI

O `operational` CLI mantém o user informado via:

- **Header em toda tela** — `cli/home.py:84-93` (`_header`) mostra `⚡ TIME-TASKER v0.1.0 | 2026-06-08` em painel cyan, sempre visível no topo.
- **Banner de sucesso** — `cli/home.py:188` (`✔ Manhã iniciada!`), `:213` (`✔ Tarde iniciada!`), `:262` (`✔ Dia encerrado!`) em verde bold após cada flow.
- **Confirmação por comando** — `metric_cmd.py:93-94` (`✓ Sono registrado: <id>`), `journal create` similar.
- **Press Enter to continue** — `cli/home.py:76` pausa após cada `_run_cmd`, dando tempo de ler output.

### Exemplos bons

- Header persistente: user sempre sabe em qual "tela" está.
- Banner de sucesso: feedback binário "completou/não completou".
- `default` em prompts: `home.py:170-179` mostra valor sugerido inline; user sabe o que vai preencher.

### Exemplos ruins

- **Sem spinner durante operação longa** — `_check_files_sanity` em `doctor_cmd.py:169-188` itera JSONs. Se houver 100+ arquivos, trava sem feedback.
- **Sem "salvando..." explícito** — `metric sleep` escreve JSON mas user não vê "💾 Gravando em ~/.time-tasker/sleep_records.json".
- **Sem progresso durante `seed`** — `cli/seed.py:seed_demo_data` popula 345 entities. Sem barra de progresso.
- **Sem timestamp da última ação** — após rodar `metric energy`, user não vê "última atualização: 14:32".

### Onde melhorar

1. **Adicionar spinner em checks lentos:** em `doctor_cmd.py:218`, antes do loop de checks, `console.status("[bold green]Running diagnostics...[/bold green]", spinner="dots")`.
2. **Progress bar em `seed`:** usar `rich.progress.Progress` com 7 steps (1 por dia).
3. **Log estruturado de ações:** gravar em `~/.time-tasker/.log` cada `upsert` com timestamp + entity type. Surfacear no `state show`.
4. **Indicador "última sync":** se houver sync com Taskwarrior (não implementado), mostrar "Last sync: 5min ago".

**Refs:** `cli/home.py:84-93`, `cli/home.py:188,213,262`, `metric_cmd.py:93-94`, `doctor_cmd.py:218`.

---

## H2 — Match entre sistema e mundo real

> *"The system should speak the users' language, with words, phrases and concepts familiar to the user, rather than system-oriented terms."*

### Aplicação no CLI

O CLI fala português brasileiro com termos do domínio (PAV — Produtividade Algorítmica Visual):

- **Períodos do dia:** `MANHA` (3-5h), `TARDE` (6-18h), `NOITE` (≥ 18h) — `enums.py:Period`. Mapeiam ciclo circadiano do user.
- **Tipos de rotina:** `ENTRY` (acordar), `CORE` (hardwork), `EXIT` (shutdown) — `enums.py:RoutineType`. Linguagem de ritual.
- **Quadrantes:** `Q1` (bom dia), `Q2`, `Q3`, `Q4` — `ui/components.py:QUADRANT_*`. Visual imediato.
- **Severities:** `ok` (verde), `warn` (amarelo), `crit` (vermelho) — `ui/components.py:SEVERITY_COLOR`. Semáforo universal.
- **Glossário de flags** — `cli/home.py:407-421` (`_FLAG_GLOSSARY`) com emojis `🥗 🎯 💤 🕐 🍽 ⚖️ 📅 📦 🏷`. User vê o que cada flag faz.

### Exemplos bons

- `Continuar? (y/n)` em vez de `Proceed? [Y/n]`. Linguagem PT-BR.
- "Sono registrado: 7.5h · Q=8/10 🟢 bom" em vez de "SleepRecord(id=slp-..., duration=7.5, quality=8)".
- "Bater meta de pomodoros" em vez de "achievement unlocked".
- "Lanche pesado" em vez de "high-glycemic meal" (jargão técnico).

### Exemplos ruins

- **Erros Pydantic em inglês** — `metric_cmd.py` levanta `ValidationError: 1 validation error for SleepRecord` (puro inglês). UX-012.
- **"TypeError" sem tradução** — se algo quebra, user vê `TypeError: 'NoneType' object is not subscriptable` (jargão Python). `_run_cmd` em `home.py:49-67` captura mas não traduz.
- **Nomes de campo em snake_case** — `hardwork_orcado_min` aparece em alguns payloads JSON. User não-programador confunde.
- **"Pydantic ValidationError"** — termo técnico. User não sabe o que fazer.

### Onde melhorar

1. **Localizar ValidationError:** criar `ui/i18n.py:translate_pydantic_error(exc) -> str` que mapeia mensagens comuns para PT-BR.
2. **Substituir "TypeError" por mensagem user-friendly:** em `_run_cmd` (`home.py:68-75`), wrap exception em Panel com `f"O comando falhou: {type(e).__name__}"` + hint genérico.
3. **Renomear campos JSON para camelCase em --json output:** `hardworkOrcadoMin` em vez de `hardwork_orcado_min`. (Trade-off: quebra scripts existentes.)
4. **Adicionar `--explain` flag em Pydantic errors:** traduzir "Input should be 'X'" para "Por favor, digite um dos: X, Y, Z".

**Refs:** `cli/home.py:68-75` (exception capture), `enums.py:Period,RoutineType`, `ui/components.py:QUADRANT_*`, `home.py:407-421` (glossary).

---

## H3 — Controle e liberdade do usuário

> *"Users often choose system functions by mistake and need a clearly marked 'emergency exit' to leave the unwanted state without having to go through an extended dialogue."*

### Aplicação no CLI

- **`q` para sair** — `home.py:108` adiciona `"q"` em `choices`. `home.py:111-114` faz `sys.exit(0)`. Saída limpa.
- **`b` para voltar em submenus** — `home.py:308,311` adiciona `"b"` em choices de `_submenu`.
- **`Ctrl+C` em qualquer prompt** — `home.py:477-480` captura `KeyboardInterrupt`, imprime `Até logo! 🚀`, sai com exit 0.
- **"Continuar? (y/n)"** nos 4 fluxos principais — `home.py:166,200,228`. User pode abortar antes de começar.

### Exemplos bons

- `_flow_morning` aborta cleanly se user digita `n` em "Continuar?" (`home.py:166-167`).
- `Prompt.ask` com `choices=["y","n"]` re-prompts em input inválido (não trava).
- `_run_cmd` captura `Exception` (`home.py:68-75`) e mostra `error_panel` em vez de crashar.
- `_submenu` aceita `b` (back) sem ação destrutiva.

### Exemplos ruins

- **`demo clear` SEM confirmação** — `home.py:363` chama `["demo", "clear"]` direto. UX-014. User pode perder dados por typo.
- **Sem undo em `routine delete`** (se existir). UX-006. Ação irreversível.
- **Sem "voltar" mid-flow** — FLOW-001 a FLOW-003 são atômicos. User não pode "desfazer" a etapa 1 após confirmar etapa 2. Decisão consciente (`docs/tui/05-HOME-MENU.md:175-176`).
- **Sem "abortar fluxo" via Ctrl+C mid-flow** — parcialmente funciona (state parcial), mas user pode não saber o que ficou gravado.
- **`report --date 2026-13-99` aborta com `BadParameter`** — sem fallback para "usar hoje?".

### Onde melhorar

1. **Adicionar `--force` flag em `demo clear`** com confirmação por padrão (UX-014). Padrão CLI: destrutivo = confirmação; `--force` = pula.
2. **Implementar undo via JSON snapshot:** antes de qualquer `repo.upsert`, copiar arquivo para `~/.time-tasker/.undo/<timestamp>`. `operational undo` reverte.
3. **Adicionar "voltar" em FLOW-001/002/003:** após cada step, perguntar "Continuar para próximo? (y/n)". Trade-off: +1 prompt por step.
4. **Catch `BadParameter` em `--date`:** oferecer default `date.today()` como fallback.

**Refs:** `home.py:108-114` (q), `home.py:308-318` (b), `home.py:477-480` (Ctrl+C), `home.py:166,200,228` (Continuar?), `home.py:363` (clear sem confirmação).

---

## H4 — Consistência e padrões

> *"Users should not have to wonder whether different words, situations, or actions mean the same thing."*

### Aplicação no CLI

- **Convenção de nomes:** `camelCase` em Python público, `snake_case` em JSON/dict. Consistente dentro do escopo.
- **Convenção de flags:** `-q` (quality), `-bh`/`-bm` (bedtime hour/min), `-wh`/`-wm` (wake hour/min) — `metric_cmd.py:60-66`. Abreviação consistente.
- **Convenção de cores:** `ok`=verde, `warn`=amarelo, `crit`=vermelho — `ui/components.py:SEVERITY_COLOR`. Usado em todo render.
- **Convenção de ícones:** ✅ ❌ 💡 🔧 para categorias de reflexão — `home.py:243-251`. Consistente dentro do FLOW-003.
- **Convenção de prompts:** `Prompt.ask(..., default=...)` em todos os inputs numéricos. Mesma forma.

### Exemplos bons

- Header sempre começa com `⚡ TIME-TASKER v0.1.0` — user reconhece a "marca".
- Severity `ok`/`warn`/`crit` em **toda** KPI card, section panel, e next-step.
- `default` em `Prompt.ask` em **todo** input numérico.
- `_run_cmd` sempre termina com `Press Enter to continue` — user sabe que vai pausar.

### Exemplos ruins

- **Incoerência: opção 10 do menu não é doctor** — `home.py:44` diz "Sistema: Versão · Constantes · Tipos · Categorias" mas não inclui doctor. UX-009. Doctor é comando direto.
- **Incoerência: "Routine" em vez de "Rotina"** — entities Pydantic são em inglês (`Routine`, `TimeBlock`, `JournalEntry`), mas UI está em PT-BR. Mistura.
- **Incoerência: emoji 🌅/💻/🌙/⚡ nos 4 flows** — bonito, mas ⚡ é também ícone de "energia" em kpi_card. Ambíguo.
- **Incoerência: `-q` em `metric sleep` significa `quality`** mas em outros contextos poderia ser "query". Sem doc cross-ref.
- **Layout 2x2 vs 3x2 vs inline** — `state show` (FLOW-005) usa 2x2 grid; `report daily` (FLOW-006) usa layout diferente. Sem padrão único.

### Onde melhorar

1. **Mover doctor para opção 11 do menu** (ou reordenar para opção 5 — antes de Relatórios). UX-009.
2. **Padronizar nomes em PT-BR** nas entities (breaking change) ou criar aliases (`Rotina` = `Routine`).
3. **Reservar emojis:** 🌅=MANHÃ, 💻=TARDE, 🌙=NOITE, ⚡=energia. Documentar em `docs/tui/04-COLOR-PALETTE.md` (estender).
4. **Cross-ref de flags:** adicionar `--help` com exemplos para cada comando Typer.
5. **Layout factory único:** extrair `ui/dashboard.py` que produz layout 2x2 ou 3x2 parametrizado. Usar em `state show` e `report daily`.

**Refs:** `home.py:44` (opção 10), `ui/components.py:SEVERITY_COLOR`, `metric_cmd.py:60-66` (flags), `home.py:243-251` (reflexão).

---

## H5 — Prevenção de erros

> *"Even better than good error messages is a careful design which prevents a problem from occurring in the first place."*

### Aplicação no CLI

- **Validação de range em Typer Options:** `metric_cmd.py:61` (`min=1, max=10` em `--quality`). Typer rejeita antes do controller rodar.
- **Date parse robusto:** `report_cmd.py:51` usa `date.fromisoformat()` que lança `ValueError` em formato errado.
- **`choices` em Prompt.ask:** `home.py:166,200,228` (`choices=["y","n"]`) impede input inválido.
- **Defaults razoáveis:** `home.py:170-179` sugere valores plausíveis; user pode aceitar com Enter.
- **Idempotência:** `metric energy` é upsert (último vence). User não acumula duplicatas.

### Exemplos bons

- `typer.Option(..., min=1, max=10)` em `metric_cmd.py:61` — Typer bloqueia `-q 99` antes do controller.
- `Prompt.ask(..., choices=["y","n"], default="y")` — user não digita valor inválido.
- `date.fromisoformat()` em `report_cmd.py:51` — formato `YYYY-MM-DD` é canônico ISO, sem ambiguidade.
- `default="8"` em `Prompt.ask("Qualidade do sono (1-10)", default="8")` — user com sono padrão completa em 5 Enters.

### Exemplos ruins

- **`demo clear` destrutivo sem `--dry-run`** — UX-014. User pode rodar por acidente.
- **`Prompt.ask` aceita string em campos numéricos** — `home.py:170` lê `q` como string, controller valida. UX-009. `IntPrompt.ask` seria mais seguro.
- **Sem validação de "data futura"** — user pode digitar `--date 2099-01-01` e o sistema aceita. Sem warning.
- **Sem confirmação em `seed`** — `home.py:359` chama `["demo", "seed"]` direto. Adiciona 345 entities sem aviso. UX-015.
- **JSON corrupto é silenciosamente pulado** — `JSONRepository._load_all` (não lido) faz `try/except` que engole erro. User não sabe que arquivo foi ignorado.
- **"Continuar?" pode ser pulado com Enter (default y)** — UX-009. User distraído pode aceitar sem ler.

### Onde melhorar

1. **Adicionar `--dry-run` em `demo clear` e `demo seed`:** print "would delete 14 files" sem executar.
2. **Usar `IntPrompt.ask` em campos numéricos:** `home.py:170-174, 209-210, 258-259, 270-271`. Trocar `Prompt.ask` por `IntPrompt.ask` com `choices=[str(i) for i in range(1, 11)]`.
3. **Validar data < hoje:** em `metric_cmd.sleep:69`, `if d > date.today(): raise typer.BadParameter("Data futura não permitida")`.
4. **Warning em `seed` se state não-vazio:** "State já tem 200 entities. Adicionar mais 345? (y/n)".
5. **Log de JSON ignorado:** quando `JSONRepository._load_all` pula arquivo, gravar warning em `logs/operational.log` E imprimir nota visual ao user.

**Refs:** `metric_cmd.py:61` (range), `report_cmd.py:51` (date parse), `home.py:166-180` (Prompts), `home.py:363` (clear sem dry-run), `home.py:359` (seed sem warning).

---

## H6 — Reconhecimento em vez de recordação

> *"Minimize the user's memory load by making objects, actions, and options visible. The user should not have to remember information from one part of the dialogue to another."*

### Aplicação no CLI

- **Menu numerado visível** — `home.py:118-131` renderiza Rich Table com 10 opções + descrições. User vê tudo, não precisa memorizar.
- **Glossário de flags** — `home.py:407-421` lista todas as flags com emoji + descrição. Acessível via opção 10.
- **Default em prompts** — `home.py:170-179` mostra valor sugerido. User não precisa lembrar formato.
- **Header com data** — `home.py:90` mostra `2026-06-08`. User sabe em qual dia está.
- **Preview de flow** — `home.py:161-164` ("Esta rotina cobre:") lista 3 etapas antes de pedir confirmação. User sabe o que vem.

### Exemplos bons

- Menu numerado: user não precisa lembrar "1 era manhã?" — lê na hora.
- Glossário: `home.py:407-421` cobre todas as flags; user consulta antes de digitar.
- Preview: FLOW-001 mostra "1. Registrar sono, 2. Criar rotina ENTRY, 3. Criar bloco MANHA" antes de "Continuar?".
- `-h`/`--help` em todo comando Typer — auto-gerado.

### Exemplos ruins

- **Comando `metric sleep` tem 5 flags** (`-q -bh -bm -wh -wm`) sem doc inline. User tem que rodar `--help` ou consultar glossário.
- **Cartesian plane sem legenda** — `◆` para Q1, `▲` para Q4. Sem caption "Q1 = alta produtividade + alta qualidade", user decora ou chuta. UX-008.
- **Status de "qual dataset está ativo"** — user tem que rodar `demo dataset` para ver. Não aparece no header. UX-009.
- **Sequência de `metric energy`** — se user quer ver histórico, tem que rodar `metric list` (separado). Não há "ver últimas 5 medições" inline.
- **Senha de dataset?** — não há, mas se houvesse, sem `password=True` em `Prompt.ask` (ver `06-INTERACTIVITY.md:35`).

### Onde melhorar

1. **Adicionar legenda inline no Cartesian plane:** `ui/daily_report.py` deve incluir caption `◆ Q1 (bom)  ▲ Q4 (recuperar)  ✗ Q3 (alerta)`.
2. **Mostrar dataset ativo no header:** `cli/home.py:90` deve incluir `[synthetic]` ou `[production]` ao lado da data.
3. **Adicionar `--recent N` em `metric list`:** mostrar últimas N medições inline.
4. **Exemplos em `--help`:** Typer suporta `typer.Option(..., help="Qualidade do sono (1-10). Ex: -q 8 para noite boa")`.

**Refs:** `home.py:118-131` (menu), `home.py:407-421` (glossário), `home.py:161-164` (preview), `home.py:90` (header).

---

## H7 — Flexibilidade e eficiência de uso

> *"Accelerators — unseen by the novice user — may often speed up the interaction for the expert user such that the system can cater to both inexperienced and experienced users."*

### Aplicação no CLI

- **Comando direto sempre disponível** — `operational metric sleep -q 8 ...` é o "accelerator" para quem pula o menu. Coberto em FLOW-001 A1.
- **`--json` flag em todo comando** — para piping em scripts. FLOW-001 A4.
- **Defaults em prompts** — novato usa defaults; expert sobrescreve.
- **Aliases via shell** — user pode criar `alias manha="operational home"`. FLOW-008 A4.
- **Submenu "b" para voltar** — expert navega rapidamente.

### Exemplos bons

- Comandos diretos: `operational report daily --json` é 1 linha, sem menu.
- `--json` em todos os comandos: `metric_cmd.py:67`, `report_cmd.py:48`, etc. Pipe-friendly.
- Defaults: 5 Enters completam sono. Expert usa `default=` para pular.
- `Enter` no prompt = `default="5"` (dashboard) — atalho de 1 tecla.

### Exemplos ruins

- **Sem aliases built-in** — `tt-morning` etc não existem. User precisa criar no shell.
- **Sem atalho de teclado para home menu** — user tem que rodar `operational home` toda vez. UX-017.
- **Sem "comandos recentes"** — não há histórico de comandos rodados (apesar de shell history cobrir isso).
- **Sem `--quiet` flag** — todo comando imprime confirmação. Em loop, polui.
- **Sem batch operation** — `metric energy -e 7 -f 8 && metric journal --text "..."` exige encadear. Não há `metric batch`.

### Onde melhorar

1. **Adicionar `~/.time-tasker/aliases.yaml`:** user define aliases. `tt` (sem args) lê aliases e executa.
2. **Detectar `operational` no PS1:** se user está em shell,提示 "operational>" como prompt secundário.
3. **Histórico de comandos:** gravar últimos 50 comandos em `~/.time-tasker/.history`. `operational recent` lista.
4. **Adicionar `--quiet` em comandos destrutivos:** `operational demo clear --quiet` imprime só "OK" em vez de banner.
5. **Adicionar `operational batch <file.yaml`:** lê arquivo com sequência de comandos, executa em ordem.

**Refs:** `metric_cmd.py:67` (--json), `report_cmd.py:48` (--json), `home.py:109` (Enter=5).

---

## H8 — Estética e design minimalista

> *"Dialogues should not contain information which is irrelevant or rarely needed. Every extra unit of information in a dialogue competes with the relevant information units and diminishes their relative visibility."*

### Aplicação no CLI

- **Painéis com border `SIMPLE_HEAD`** — `ui/components.py:341-361` (kpi_card), `ui/daily_report.py`. Visual limpo.
- **Cores semânticas** — `ok`/`warn`/`crit` em vez de "azul/vermelho aleatório".
- **Whitespace generoso** — Rich `Table.grid(padding=(0, 2))` em todo lugar.
- **Sem ícones redundantes** — `Q1` é só texto + emoji 1 (🏆), não "Q1 Bom Dia 🏆✓".
- **Hierarquia visual** — Header > KPIs > Detalhe > Next-step.

### Exemplos bons

- KPI cards: título + valor + footer. Só 3 linhas de informação. Fácil de escanear.
- Cartesian plane: 1 ponto + 4 quadrantes com labels de eixo. Sem poluição.
- Section panels: título colorido + body. Body pode ser Table ou Text, mas é separado.
- `default` em prompts aparece em dim. Não compete com a pergunta.

### Exemplos ruins

- **`_FLAG_GLOSSARY` em opção 10** — 14 flags listadas. Se user só precisa de 1, é info demais. Sem busca. UX-009.
- **Doctor Panel mistura OK + summary em uma row** — `_check_state_dir` mostra "ok /home/user/.time-tasker (14 files)". Mix de status + path + count. Poluído. UX-010.
- **Header repete "TIME-TASKER"** — `home.py:90` tem "⚡ TIME-TASKER v0.1.0 | 2026-06-08". Toda tela. Visual heavy.
- **Sem "modo compacto"** — user em terminal pequeno (80×24) não tem layout alternativo. UX-003.
- **Output JSON às vezes é verbose** — `state show --json` retorna 30+ campos. Filtro `--fields` não existe.

### Onde melhorar

1. **Adicionar `--compact` flag:** em relatórios, esconde seções vazias (sem dados) automaticamente.
2. **Refatorar Doctor Panel:** seção "✓ OK" (resumo) + seção "✗ Issues" (detalhe). UX-010.
3. **Header opcional:** `operational home --minimal` mostra só "v0.1.0 · 2026-06-08".
4. **`--fields` em JSON:** `state show --json --fields=date,period_now,sleep` filtra payload.
5. **Auto-detectar largura do terminal:** se < 100 col, usar layout 1-col em vez de 2x2. UX-003.

**Refs:** `ui/components.py:341-361` (kpi_card), `home.py:90` (header), `home.py:407-421` (glossary), `doctor_cmd.py:218-244` (panel).

---

## H9 — Ajude usuários a reconhecer, diagnosticar e recuperar erros

> *"Error messages should be expressed in plain language (no codes), precisely indicate the problem, and constructively suggest a solution."*

### Aplicação no CLI

- **`error_panel` padronizado** — `ui/components.py:390-426`. Todo erro renderiza neste formato.
- **Hint opcional** — `error_panel(mensagem, contexto, severity, hint)`. Última linha "💡 Dica" sugere ação.
- **Log estruturado** — `ui/logging_setup.py:log_error` grava traceback completo em `logs/operational.log`.
- **Doctor como ferramenta de diagnóstico** — `operational doctor` é o "primeiro socorros" para erros persistentes.

### Exemplos bons

- `error_panel` tem 4 seções: mensagem, contexto, severity, hint. UX consistente.
- Traceback completo em log; user vê só resumo.
- `operational doctor` cobre 90% dos bugs estruturais.
- Pydantic ValidationError renderiza com field name + value + expected.

### Exemplos ruins

- **Mensagens Pydantic em inglês** — `ValidationError: 1 validation error for SleepRecord\nquality\n  Input should be 'X'`. UX-012. Sem tradução.
- **"TypeError: 'NoneType' object is not subscriptable"** — jargão Python. User leigo não sabe o que fazer.
- **Hint genérico em alguns casos** — `error_panel(mensagem, hint="Verifique os dados e tente novamente")` (não-actionable).
- **Sem "o que fazer agora"** — após erro, user tem que consultar `--help` ou docs. Próxima ação não é clara.
- **Doctor não tem `--fix`** — `operational doctor --fix` auto-corrigiria CRLF, recriaria state dir, etc. Não implementado.
- **Sem correlation ID** — se user reporta bug, suporte não tem como rastrear. `error_panel` não inclui request_id.

### Onde melhorar

1. **Localizar Pydantic errors:** wrap `ValidationError` em handler que traduz `Input should be 'X'` para "Esperado um dos: X, Y, Z".
2. **Substituir "TypeError" por mensagem user-friendly:** mapear exceptions comuns para PT-BR + hint actionable.
3. **Adicionar `operational doctor --fix`:** auto-corrige CRLF, recria state dir faltante, etc.
4. **Incluir "próxima ação" em error_panel:** "Tente: `operational metric sleep --help` para ver flags."
5. **Adicionar correlation_id:** UUID gerado por sessão, incluído em logs e error_panel.

**Refs:** `ui/components.py:390-426` (error_panel), `ui/logging_setup.py:log_error`, `doctor_cmd.py` (diagnosis).

---

## H10 — Ajuda e documentação

> *"Even though it is better if the system can be used without documentation, help and documentation may be necessary. Such information should be easy to search, focused on the user's task, list concrete steps, and not be too long."*

### Aplicação no CLI

- **`--help` em todo comando** — Typer auto-gera. `operational --help`, `operational metric sleep --help`.
- **Help do home menu opção 10** — `home.py:434-466` mostra versão, constants, tipos, glossário de flags.
- **Documentação em `docs/`** — `tui/`, `architecture/`, `ux/`. PT-BR para estratégia; EN para comments.
- **OBJ-01 a OBJ-08** — `docs/ux/00-visao-geral/01-objetivos-produto.md` lista objetivos com status.
- **`AGENTS.md`** no root do monorepo — guia de contribuição.

### Exemplos bons

- `--help` Typer: documenta cada flag, type, default. Funciona offline.
- Opção 10 do menu: user fica no CLI e consulta sem sair.
- `docs/architecture/05-DATA-FLOW.md`: trace end-to-end de 1 comando. Didático.
- `docs/ux/04-fluxos/`: este doc + FLOW-001 a FLOW-010.

### Exemplos ruins

- **`--help` não lista exemplos** — Typer mostra `Usage: operational metric sleep [OPTIONS]`. Sem "Exemplo: -q 8 -bh 23 -bm 30".
- **Glossário de flags em opção 10 não tem busca** — user que procura `-q` tem que rolar 14 linhas. UX-009.
- **Sem `operational cheatsheet`** — comando que imprime 1 página com tudo (flags, atalhos, exemplos).
- **Docs em PT-BR mas mensagens em EN** — assimetria. User leigo em inglês fica perdido.
- **Sem "tour guiado"** — primeira execução mostra menu sem onboarding. UX-013.
- **Sem FAQ** — "Como troco de dataset?" está em FLOW-008 mas não há índice.
- **AGENTS.md é para contribuidores, não end-users** — `docs/ux/` cobre o gap, mas disperso.

### Onde melhorar

1. **Adicionar `Examples` em `--help`:** Typer suporta `typer.Option(..., help="Ex: -q 8 -bh 23")`.
2. **Criar `operational cheatsheet`:** comando que imprime 1 página com tudo.
3. **Buscar em opção 10:** `_system_info` aceita `--filter` para grep no glossário.
4. **Onboarding na primeira execução:** detectar `~/.time-tasker/` vazio e mostrar "Bem-vindo! Comece com 1 (Iniciar Manhã)".
5. **FAQ em `docs/ux/09-faq.md`:** responder as 20 perguntas mais comuns.

**Refs:** `home.py:434-466` (system info), `docs/ux/00-visao-geral/01-objetivos-produto.md`, `docs/architecture/05-DATA-FLOW.md`.

---

## Resumo da avaliação

| # | Heurística | Status | Notas |
|---|-----------|--------|-------|
| H1 | Visibilidade do status | ⭐⭐⭐ | Bom header/banner; falta spinner/progress |
| H2 | Match mundo real | ⭐⭐⭐ | PT-BR bom; erros técnicos em inglês (UX-012) |
| H3 | Controle e liberdade | ⭐⭐⭐ | q/b/Ctrl+C OK; `clear` sem confirmação (UX-014) |
| H4 | Consistência | ⭐⭐ | Incoerência: opção 10 ≠ doctor; emojis ambíguos |
| H5 | Prevenção de erros | ⭐⭐ | Range Typer OK; sem dry-run; sem IntPrompt |
| H6 | Reconhecimento > recordação | ⭐⭐⭐ | Menu numerado + glossário; Cartesian sem legenda (UX-008) |
| H7 | Flexibilidade | ⭐⭐⭐ | Comando direto + --json; sem aliases built-in |
| H8 | Estética minimalista | ⭐⭐ | Header pesado; doctor panel misturado (UX-010) |
| H9 | Diagnóstico de erros | ⭐⭐ | error_panel bom; mensagens em EN (UX-012) |
| H10 | Ajuda e documentação | ⭐⭐⭐ | --help + opção 10; sem onboarding (UX-013) |

**Pontuação:** 27/50 (54%). Áreas prioritárias para próxima sprint:

1. **H5/H9 — Localizar erros e adicionar `--dry-run`** (resolveria UX-012, UX-014, UX-015 em conjunto).
2. **H4/H8 — Refatorar Doctor Panel e mover para menu** (resolveria UX-009, UX-010).
3. **H8 — Auto-detectar largura do terminal** (resolveria UX-003).

**Ver também:** `03-riscos-conhecidos.md` para o catálogo UX-001 a UX-020.
