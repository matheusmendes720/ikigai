# 03 — Riscos Conhecidos (UX-001 a UX-020)

> Catálogo de **problemas de UX já conhecidos** no `operational` CLI. Cada risco tem:
> - **ID:** UX-NNN
> - **Severidade:** Alta | Média | Baixa
> - **Categoria:** Acessibilidade | Clareza | Performance | Consistência
> - **Sintoma:** O que o user vê/sente
> - **Causa raiz:** Onde no código
> - **Workaround:** Como contornar agora
> - **Fix proposto:** Como resolver
> - **Prioridade:** Quando resolver
>
> **Total:** 20 riscos documentados (P0: 5, P1: 10, P2: 5). Manter atualizado à medida que novos issues forem descobertos.

---

## UX-001 — Q3 "Crítico" sem definição clara para novo usuário

- **Severidade:** Média
- **Categoria:** Clareza
- **Sintoma:** User novo vê `Quadrant: Q3 (crítico)` no relatório e não entende o que Q3 significa, por que é crítico, ou o que fazer.
- **Causa raiz:** `ui/components.py:QUADRANT_*` (provavelmente) tem labels inline curtos. Sem tooltip ou doc.
- **Workaround:** User lê `docs/architecture/01-MVC-LAYERS.md` ou consulta opção 10 do menu.
- **Fix proposto:** Adicionar caption inline no Cartesian plane: "Q1 = alta produtividade + alta qualidade (bom dia)". Adicionar tooltip em `--help`.
- **Prioridade:** P1 (resolver em sprint 2)

---

## UX-002 — Cor `crit` (red) pode ser invisível para daltônicos (~8% homens)

- **Severidade:** Média
- **Categoria:** Acessibilidade
- **Sintoma:** User com deuteranopia (daltonismo vermelho-verde) não consegue distinguir "Q1 verde" de "Q3 vermelho" no Cartesian plane ou KPI cards.
- **Causa raiz:** `ui/components.py:87-94` (`COLORS` dict) usa `bright_green` para `ok` e `bold red` para `crit`. Diferença depende de matiz, não luminância.
- **Workaround:** User daltônico decora glyph (◆ = Q1, ▲ = Q4, ✗ = Q3) ou consulta `--json` para dados estruturados.
- **Fix proposto:** Adicionar ícone além de cor: ✓ para ok, ⚠ para warn, ✗ para crit. Garantir luminância distinta (high contrast mode).
- **Prioridade:** P1 (resolver em sprint 2)

---

## UX-003 — Layout quebra em terminal < 100 col (assume 120)

- **Severidade:** Média
- **Categoria:** Consistência
- **Sintoma:** User com terminal 80×24 (default Windows) vê layout cortado, tabelas largas quebradas, ou texto truncado.
- **Causa raiz:** `ui/__init__.py:43` define `CONSOLE_WIDTH = 120`. `kpi_card` width=28 assume 2 cards por row + padding. Em 80 col, 1 row com 2 cards = 56 + 2 = 58 col — aperta mas cabe. Em 80 col com 3 cards = 84 col — quebra.
- **Workaround:** User redimensiona terminal para ≥ 120 col antes de rodar relatório. Ou usa `--json`.
- **Fix proposto:** Auto-detectar largura via `shutil.get_terminal_size()`. Se < 100, usar layout 1-col em vez de 2x2.
- **Prioridade:** P1 (resolver em sprint 3)

---

## UX-004 — Prompt sem timeout: user pode abandonar form a meio

- **Severidade:** Baixa
- **Categoria:** Performance
- **Sintoma:** User abre FLOW-001 (Iniciar Manhã), digita "1", vai atender o telefone, esquece. Prompt `Prompt.ask("Qualidade do sono (1-10)")` fica esperando indefinidamente.
- **Causa raiz:** Rich `Prompt.ask` é blocking sem timeout. `cli/home.py:170-179` não envolve com timer.
- **Workaround:** User lembra de voltar. `Ctrl+C` cancela flow. State preservado (atomicidade do step).
- **Fix proposto:** Wrapper custom `Prompt.ask(..., timeout=60)` usando `prompt_toolkit` ou `pexpect`. Após timeout, exit com warning.
- **Prioridade:** P2 (nice-to-have)

---

## UX-005 — `--help` não lista todos os flags (Typer auto-gera)

- **Severidade:** Baixa
- **Categoria:** Clareza
- **Sintoma:** User roda `operational metric sleep --help` e vê flags básicos (`-q`, `-bh`, `-bm`, `-wh`, `-wm`, `--date`, `--json`) mas não sabe que `-q` aceita 1-10, ou que `--date` requer `YYYY-MM-DD`.
- **Causa raiz:** `metric_cmd.py:60-67` define flags com `help=` curto. Typer não adiciona exemplos automaticamente.
- **Workaround:** User consulta `_FLAG_GLOSSARY` em opção 10 do menu (`home.py:407-421`) ou `docs/architecture/05-DATA-FLOW.md`.
- **Fix proposto:** Estender `help=` com exemplos: `typer.Option(..., help="Qualidade do sono (1-10). Ex: -q 8 para noite boa")`.
- **Prioridade:** P2 (nice-to-have)

---

## UX-006 — Sem undo: deletar rotina é permanente

- **Severidade:** Alta
- **Categoria:** Consistência
- **Sintoma:** User roda `operational routine delete <id>` (se existir) e perde a rotina sem aviso. Sem `undo`, sem `restore`, sem backup.
- **Causa raiz:** `cli/commands/routine_cmd.py` (não lido) tem `delete` que remove do repo. Sem snapshot antes.
- **Workaround:** User exporta state antes: `operational demo export-csv /tmp/backup.csv`. Se deletar, re-importa.
- **Fix proposto:** Implementar `operational undo` que mantém últimos N estados em `~/.time-tasker/.undo/`. `operational undo` reverte para último snapshot.
- **Prioridade:** P0 (resolver antes de GA)

---

## UX-007 — JSON output é dump bruto (não formatted)

- **Severidade:** Baixa
- **Categoria:** Clareza
- **Sintoma:** User roda `operational state show --json` e recebe 1 linha de 2KB sem indentação. Difícil de ler.
- **Causa raiz:** `cli/formatters/base.py:format_as_json` (não lido) usa `json.dumps(...)` sem `indent=2`.
- **Workaround:** User pipe para `jq .` ou `python -m json.tool`.
- **Fix proposto:** Adicionar `--pretty` flag (default False para preservar pipe-friendly; True para humanos).
- **Prioridade:** P2 (nice-to-have)

---

## UX-008 — Cartesian plane sem label "Q?" no próprio ponto (precisa legenda)

- **Severidade:** Média
- **Categoria:** Clareza
- **Sintoma:** User olha o Cartesian plane, vê `◆` em Q1, e precisa adivinhar (ou rolar para cima) o que `◆` significa.
- **Causa raiz:** `ui/components.py:241-327` (cartesian_plane) plota glyph (`◆` cyan/bright_green, `▲` yellow, `✗` bold red) mas sem label textual "Q1", "Q4" no próprio ponto.
- **Workaround:** User decora ou consulta legenda em `docs/architecture/01-MVC-LAYERS.md` ou `docs/ux/01-inventario/01-telas-inventario.md` (ref futura).
- **Fix proposto:** Plotar glyph + label `Q1` ao lado. Ex: `◆ Q1` em vez de só `◆`.
- **Prioridade:** P1 (resolver em sprint 2)

---

## UX-009 — Pomodoros grid ▢/■ não tem tooltip

- **Severidade:** Baixa
- **Categoria:** Clareza
- **Sintoma:** User vê `S1 manhã   ▣ ▣ ▣ ▢   3/4` e não sabe se `▣` é "completado" e `▢` é "pendente", ou se é meta vs realizado.
- **Causa raiz:** `ui/components.py:222-238` (pomodoros_grid) usa ▣/▢ mas sem legenda inline.
- **Workaround:** User deduz por posição (completos à esquerda, pendentes à direita).
- **Fix proposto:** Adicionar legenda abaixo do grid: "▣ completo · ▢ pendente". Ou usar cor (verde/grey30) que é semanticamente óbvio.
- **Prioridade:** P2 (nice-to-have)

---

## UX-010 — Doctor output mistura status bom/ruim sem agrupamento visual

- **Severidade:** Média
- **Categoria:** Consistência
- **Sintoma:** User roda `operational doctor`, vê 7 rows em sequência: `[OK] python`, `[OK] packages`, `[FAIL] state_dir`, `[OK] datasets`, ... Sem seção "✓ OK" e "✗ Issues" separadas.
- **Causa raiz:** `cli/commands/doctor_cmd.py:218-244` renderiza `Table.grid` com todos os checks em uma única lista.
- **Workaround:** User rola até o fim, procura por `[FAIL]` e `[red]Issues:[/red]`.
- **Fix proposto:** Renderizar 2 Panels: `Panel(ok_section, title="✓ OK", border_style="green")` + `Panel(fail_section, title="✗ Issues", border_style="red")`.
- **Prioridade:** P1 (resolver em sprint 3)

---

## UX-011 — Sem dark mode toggle (Rich auto-detect)

- **Severidade:** Baixa
- **Categoria:** Acessibilidade
- **Sintoma:** User com tema claro (terminal branco) vê texto em bright_green que vira amarelo-claro, quase invisível. Ou user com tema escuro vê bold_red que é indistinguível de cinza.
- **Causa raiz:** `ui/__init__.py:35-37` detecta `is_captured()` e define `no_color`. Mas não há toggle manual de "tema claro vs escuro".
- **Workaround:** User configura `NO_COLOR=1` ou `FORCE_COLOR=1` no ambiente.
- **Fix proposto:** Adicionar `--theme` flag: `operational home --theme=light` ou `dark` ou `auto`. Mapeia para `Console(theme=...)` do Rich.
- **Prioridade:** P2 (nice-to-have)

---

## UX-012 — Mensagens de erro Pydantic em inglês (não localizadas)

- **Severidade:** Alta
- **Categoria:** Clareza
- **Sintoma:** User digita `-q 99` e vê `BadParameter: Invalid value for '-q': 99 is not in the range 1<=x<=10`. Jargão inglês.
- **Causa raiz:** `metric_cmd.py:61` define `typer.Option(..., min=1, max=10)`. Typer gera mensagem em inglês hard-coded.
- **Workaround:** User decora o range ou consulta `--help`. Em flows via menu, `_run_cmd` (`home.py:49-67`) captura e mostra `error_panel` (que tem título PT-BR, mas corpo em inglês).
- **Fix proposto:** Wrap Typer exceptions em `ui/i18n.py:translate_error(exc) -> str` que mapeia mensagens comuns. Adicionar locale files (`locale/pt_BR.json`).
- **Prioridade:** P0 (resolver antes de GA)

---

## UX-013 — Sem onboarding (primeira execução é cold)

- **Severidade:** Média
- **Categoria:** Clareza
- **Sintoma:** User instala `operational`, roda `operational home`, vê menu numerado sem saber por onde começar. Pode escolher 6 (Relatórios) e ficar confuso com state vazio.
- **Causa raiz:** `home.py:100-115` (`home`) não detecta primeira execução (state vazio) nem mostra tutorial.
- **Workaround:** User lê `docs/ux/00-visao-geral/01-objetivos-produto.md` ou segue OBJ-01 (FLOW-001) por intuição.
- **Fix proposto:** Detectar `~/.time-tasker/*.json` ausente/vazio. Na primeira execução, mostrar "🎉 Bem-vindo! Vamos começar com 1 (Iniciar Manhã)" em vez do menu direto. Após 7+ dias, esconder onboarding.
- **Prioridade:** P1 (resolver em sprint 2)

---

## UX-014 — `demo clear` sem confirmação (perigoso)

- **Severidade:** Alta
- **Categoria:** Consistência
- **Sintoma:** User escolhe opção 9 (Demo) → 5 (Limpar todos dados) por engano ou curiosidade. State de produção é apagado **imediatamente**, sem aviso.
- **Causa raiz:** `home.py:363` define `["demo", "clear"]` como submenu item. `cli/commands/demo_cmd.py:42-51` (clear) executa `clear_demo_data()` sem confirmação.
- **Workaround:** User faz backup manual antes: `cp -r ~/.time-tasker/ ~/.time-tasker.backup.$(date +%Y%m%d)`. Ou usa `TIME_TASKER_DATASET=synthetic operational home` para isolar.
- **Fix proposto:** Adicionar `Confirm.ask("Apagar todos os 14 JSON files?", default=False)` em `demo_cmd.clear`. Adicionar `--force` flag para pular em scripts de CI.
- **Prioridade:** P0 (resolver antes de GA)

---

## UX-015 — `demo seed` polui state dir sem aviso

- **Severidade:** Média
- **Categoria:** Consistência
- **Sintoma:** User roda `operational demo seed` e 345 entities são adicionadas ao state. Próximo `report daily` confunde dados reais com mock.
- **Causa raiz:** `home.py:359` chama `["demo", "seed"]` direto. `cli/commands/demo_cmd.py:30-39` (seed) executa `seed_demo_data()` sem checar se state já tem dados.
- **Workaround:** User roda `demo clear && demo seed` para começar limpo. Ou usa `TIME_TASKER_DATASET=synthetic` para isolar.
- **Fix proposto:** Detectar state não-vazio. Mostrar "State já tem N entities. Adicionar mais 345? (y/n)". Default `n`.
- **Prioridade:** P1 (resolver em sprint 2)

---

## UX-016 — Auto-load CSV só roda com state vazio (não recarrega)

- **Severidade:** Média
- **Categoria:** Performance
- **Sintoma:** User muda `TIME_TASKER_DATASET=synthetic` enquanto o CLI está rodando. Próximo `state show` ainda mostra dados antigos (não recarrega).
- **Causa raiz:** `cli/state.py` (auto-loader, não lido) só lê CSV se `_loaded is False` ou similar. Após primeira carga, não recarrega.
- **Workaround:** User fecha e reabre o CLI com nova env var. Ou roda `demo clear` antes de nova sessão.
- **Fix proposto:** Adicionar comando `operational reload` que força re-leitura de CSV. Detectar mudança de mtime do CSV e sugerir reload.
- **Prioridade:** P1 (resolver em sprint 3)

---

## UX-017 — Sem atalho de teclado para home menu

- **Severidade:** Baixa
- **Categoria:** Performance
- **Sintoma:** User em shell quer voltar ao `operational home` mas tem que digitar o comando inteiro.
- **Causa raiz:** Não há alias built-in. Depende de shell alias do user (FLOW-008 A4).
- **Workaround:** User cria alias no shell: `alias tt="operational home"`.
- **Fix proposto:** Instalar shell completion + alias via `operational install --alias`. Ou detectar `operational` rodando em background como daemon.
- **Prioridade:** P2 (nice-to-have)

---

## UX-018 — Pomodoros em diferentes sessões (S1/S2/S3) sem distinção visual

- **Severidade:** Baixa
- **Categoria:** Clareza
- **Sintoma:** User vê `S1 manhã   ▣ ▣ ▣ ▢   3/4` e `S2 tarde   ▣ ▣ ▣ ▣   4/4` mas não distingue manhã/tarde/noite visualmente (só pelo label).
- **Causa raiz:** `ui/components.py:222-238` (pomodoros_grid) usa mesmo glyph ▣/▢ para todas as sessões. Diferenciação só por label textual.
- **Workaround:** User decora que S1=manhã, S2=tarde, S3=noite (citado em `02-COMPONENT-CATALOG.md:155-165`).
- **Fix proposto:** Usar cor distinta por sessão: S1=cyan, S2=magenta, S3=grey. Ou ícone: ☀ S1, ☼ S2, ☾ S3.
- **Prioridade:** P2 (nice-to-have)

---

## UX-019 — Sleep bedtime = 23:00 vs wake = 23:00 (duração 0)

- **Severidade:** Baixa
- **Categoria:** Consistência
- **Sintoma:** User registra sono com `bed_hour=23, bed_minute=0, wake_hour=23, wake_minute=0`. Duração calculada = 0h. Mas user dormiu "ontem à noite" e acordou "hoje de manhã" — pode querer duração 8h.
- **Causa raiz:** `meta/factories.py:make_sleep_record` (não lido) calcula `duration_hours` como `wake_time - bed_time` sem cruzar meia-noite. Se ambos são 23:00, retorna 0.
- **Workaround:** User registra com horários diferentes (ex: 23:00 → 07:00). Ou preenche `--date` corretamente.
- **Fix proposto:** Em `make_sleep_record`, se `bed_time > wake_time`, somar 24h (atravessou meia-noite). Validar que `duration_hours > 0`.
- **Prioridade:** P2 (nice-to-have)

---

## UX-020 — TypeError em alguns fluxos (já é pre-existing test failure)

- **Severidade:** Média
- **Categoria:** Performance
- **Sintoma:** User roda `operational report daily --date 2026-06-08` em state com entities corrompidas e recebe `TypeError: 'NoneType' object is not subscriptable` em vez de mensagem user-friendly.
- **Causa raiz:** `core/services.py:139-238` (`get_day_snapshot`) itera `repo.list()` que pode retornar entidades com campos `None`. Renderização subsequente em `ui/daily_report.py:50-340` acessa `snap.sleep.duration_hours` sem null check.
- **Workaround:** User roda `operational doctor` para detectar corrupção. Se persistir, `operational demo clear` regenera.
- **Fix proposto:** Em `get_day_snapshot`, normalizar campos None para defaults. Em `render_daily_report`, validar cada campo antes de acessar. Adicionar teste de regressão.
- **Prioridade:** P1 (resolver em sprint 2, marcar como pre-existing)

---

## Resumo por severidade

| Severidade | IDs | Conclusão |
|-----------|-----|-----------|
| **Alta** | UX-006, UX-012, UX-014 | Bloqueiam GA. Resolver antes de release. |
| **Média** | UX-001, UX-002, UX-003, UX-008, UX-010, UX-013, UX-015, UX-016, UX-020 | UX degradada mas funcional. Sprint 2-3. |
| **Baixa** | UX-004, UX-005, UX-007, UX-009, UX-011, UX-017, UX-018, UX-019 | Polimento. Nice-to-have. |

## Resumo por categoria

| Categoria | IDs |
|-----------|-----|
| **Acessibilidade** | UX-002, UX-003, UX-011 |
| **Clareza** | UX-001, UX-005, UX-007, UX-008, UX-009, UX-012, UX-013, UX-018, UX-019 |
| **Performance** | UX-004, UX-016, UX-017, UX-020 |
| **Consistência** | UX-006, UX-010, UX-014, UX-015 |

## Roadmap sugerido

### Sprint 2 (P0 + P1 prioritários)

1. **UX-014** — Adicionar confirmação em `demo clear` (1h)
2. **UX-012** — Localizar erros Pydantic (4h)
3. **UX-006** — Implementar `undo` (8h)
4. **UX-013** — Onboarding primeira execução (4h)
5. **UX-015** — Warning em `seed` se state não-vazio (1h)
6. **UX-008** — Label Q1/Q2/Q3/Q4 no Cartesian (2h)
7. **UX-001** — Caption inline explicativo Q? (1h)
8. **UX-020** — Null-safety em `get_day_snapshot` (4h)

**Total:** ~25h (3 dias).

### Sprint 3 (P1 restantes)

9. **UX-002** — Glyph + ícone além de cor (4h)
10. **UX-003** — Auto-detect width < 100 col (4h)
11. **UX-010** — Refatorar Doctor Panel em 2 seções (2h)
12. **UX-016** — Comando `reload` (4h)

**Total:** ~14h (2 dias).

### Backlog (P2)

UX-004, UX-005, UX-007, UX-009, UX-011, UX-017, UX-018, UX-019. Sem prazo. Adicionar a `INTEGRATION-BACKLOG.md`.

## Como adicionar novo risco

```markdown
### UX-NNN — Título curto

- **Severidade:** Alta | Média | Baixa
- **Categoria:** Acessibilidade | Clareza | Performance | Consistência
- **Sintoma:** O que o user vê/sente
- **Causa raiz:** Onde no código (file:line)
- **Workaround:** Como contornar agora
- **Fix proposto:** Como resolver
- **Prioridade:** P0 | P1 | P2
```

**Convenção de IDs:** Próximo número disponível (UX-021, UX-022, ...).

## Referências cruzadas

- **Heurísticas:** `01-heuristicas-nielsen.md` (H1-H10).
- **Checklist:** `02-checklist-usabilidade.md` (30+ itens de review).
- **Fluxos:** `docs/ux/04-fluxos/FLOW-001-...md` a FLOW-010.
- **Componentes:** `docs/tui/02-COMPONENT-CATALOG.md` (CMP-001 a CMP-019).
- **Telas:** `docs/ux/05-telas/SCR-001-...md` (refs futuras).
- **Backlog integração:** `INTEGRATION-BACKLOG.md` (root).
