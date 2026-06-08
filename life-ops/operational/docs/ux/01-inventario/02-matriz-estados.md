# 02 — Matriz de Estados

> Para cada uma das 15 telas do CLI, este documento descreve os
> **5 estados possíveis**: Vazio, Loading, Com Dados, Erro, Sem
> Permissão. A aplicação é **local-only** (sem permissões de
> arquivo remotas), então "Sem Permissão" é raro e geralmente
> mapeia para "Arquivo não encontrado" ou "Permissão negada no
> state dir".
>
> Use esta matriz para validar que cada tela tem um comportamento
> previsível em todos os cenários — não só no "happy path".

---

## Tabela resumo (15 telas × 5 estados)

| Tela | Vazio | Loading | Com Dados | Erro | Sem Permissão |
|------|-------|---------|-----------|------|---------------|
| SCR-001 Home | Menu renderiza (sem deps) | N/A (sync) | Menu renderiza | N/A | N/A |
| SCR-002 Daily | "—" em todos | N/A (sync, 20-80ms) | Dashboard completo | `error_panel` vermelho | N/A (local) |
| SCR-003 Weekly | KPIs zerados | N/A (sync) | Dashboard 7-dias | `error_panel` vermelho | N/A |
| SCR-004 State | Cards "—", "0", "não registrado" | N/A (sync) | 2x2 KPI grid + grids | `error_panel` vermelho | "state dir não existe" |
| SCR-005 Demo Stats | "0 entities of type X" | N/A (sync) | Tabela de counts | "Cannot list state" | "Cannot read state dir" |
| SCR-006 Dataset List | "No datasets found" | N/A (sync) | Lista com status OK/MISSING | "CSV not found" | "Cannot read docs/" |
| SCR-007 Doctor | Sempre tem dados (verifica env) | N/A (sync) | Painel 7 checks | Painel com 1+ FAIL | "Cannot read json file" |
| SCR-008 Routine | "Nenhuma rotina" | N/A (sync) | Tabela | "Cannot list routines" | "Cannot read routines.json" |
| SCR-009 Block | "Nenhum bloco" | N/A (sync) | Tabela | "Cannot list blocks" | "Cannot read time_blocks.json" |
| SCR-010 Journal | "Nenhum journal" | N/A (sync) | Tabela | "Cannot list journals" | "Cannot read journals.json" |
| SCR-011 Habit | "Nenhum hábito" | N/A (sync) | Tabela | "Cannot list habits" | "Cannot read habits.json" |
| SCR-012 Metric Form | N/A (sempre form) | N/A (sync) | Linha de confirmação | ValidationError vermelho (Pydantic) | N/A |
| SCR-013 Policy | "Nenhuma decisão" | N/A (sync) | Tabela | "Cannot list decisions" | "Cannot read policy_decisions.json" |
| SCR-014 Reflect | N/A (sempre form) | N/A (sync) | "✔ OKRs registrados" | ValidationError vermelho | N/A |
| SCR-015 Lunch | N/A (sempre form) | N/A (sync) | "Lunch 2026-06-08" | ValidationError vermelho | N/A |

---

## Loading: a maioria é síncrona

O `operational` CLI **não tem loading states** porque:
1. Os repos são in-memory (`_PersistentRepo` em
   `operational.persistence.memory`).
2. O Console é single-threaded e bloqueia em `console.print()`.
3. Operações de I/O (CSV read em demo seed) são < 100ms.

Quando a operação **pode demorar** (ex: demo seed com 7 dias de
dados sintéticos), o `operational` simplesmente não mostra feedback
intermediário — o usuário vê o output completo em 1-2 segundos.

**Futuro:** se algum dia houver I/O lento (sync com Taskwarrior,
sync com API), a estratégia recomendada é usar
`rich.progress.Progress` com `console.status("...")` para spinners
sutis.

---

## Detalhes por estado (casos não-óbvios)

### SCR-002 Daily Report — Estado Vazio

Quando não há dados para a data (ex: 2026-06-08 sem registro):

```text
╭───  ⚡ DAILY REPORT  ────────────────────────────────────────────╮
│  📅  2026-06-08   ◆ CURSO      ❓ Q3      🍅 0/12                  │
╰─────────────────────────────────────────────────────────────────────╯
╭───  😴 EASE  ──────────────────────────────────────────────────╮
│  ⏰ Acordou        —                                          │
│  🌙 Dormiu         —                                          │
│  😴 Sono           —                                          │
│  ⭐ Qualidade      —                                          │
│  💪 Workout        não feito                                  │
│  🧘 Meditação      não feita                                  │
│  ...                                                         │
╰──────────────────────────────────────────────────────────────────╯
```

**Comportamento:**
- `compute_day_quadrant` retorna Q3 com `(x=0, y=0)` porque
  `realizado/orçado = 0` e `foco/total = 0`.
- O Cartesian plane plota o ponto `✗` no canto inferior-esquerdo.
- O next-step panel sugere "Aplicar plano de recuperação antes
  de continuar" (severity `crit`).
- Todos os campos de input são "—" (cinza muted).

**Mensagem amigável:** "Nenhum dado para esta data. Use
`operational home` → opção 1 para registrar sono, ou opção 2
para iniciar a tarde." (Atualmente NÃO há essa mensagem — gap
de UX. Ver `INTEGRATION-BACKLOG.md`.)

---

### SCR-002 Daily Report — Estado de Erro

Quando `get_day_snapshot` levanta `FaltaDadosError`:

```text
╭────  SISTEMA FALHOU  ────────────────────────────────────────────╮
│  ❌ Erro de Execução                                               │
│                                                                  │
│  FaltaDadosError: Não foi possível montar DaySnapshot.            │
│  day_contexts está vazio para 2026-06-08.                         │
│                                                                  │
│  [Contexto]  date=2026-06-08, repos=14                            │
│  [💡 Dica]  Use `operational demo seed` para popular dados      │
╰──────────────────────────────────────────────────────────────────╯
```

**Comportamento:**
- O traceback completo é logado em `~/.time-tasker/logs/...`.
- O usuário vê apenas o `error_panel` vermelho, sem traceback
  bruto.
- Severity: `crit` (default).
- Exit code: 1 (Typer exit on unhandled).

---

### SCR-004 State Dashboard — Estado Vazio

```text
╭───  ⚡  STATE  ·  2026-06-08  ·  🌅 MANHA  ─────────────────────╮
╰──────────────────────────────────────────────────────────────────╯
╭─────────────────╮  ╭─────────────────╮
│  😴 Sono         │  │  🍅 Pomodoros   │
│  —               │  │  0              │
│  não registrado  │  │  completos hoje │
╰─────────────────╯  ╰─────────────────╯
╭─────────────────╮  ╭─────────────────╮
│  💻 Hardwork     │  │  ⚡ Energia/Foco│
│  0h00            │  │  —/—            │
│  0/180min        │  │  não registrado │
│  0% atingido     │  │                 │
╰─────────────────╯  ╰─────────────────╯

╭───  🍅 Pomodoros (S1 manhã · S2 tarde · S3 noite)  ──────────────╮
│  S1 manhã   ▢ ▢ ▢ ▢   0/4                                        │
│  S2 tarde   ▢ ▢ ▢ ▢   0/4                                        │
│  S3 noite   ▢ ▢ ▢ ▢   0/4                                        │
╰──────────────────────────────────────────────────────────────────╯

╭───  Atividade do Dia  ──────────────────────────────────────────╮
│  🕐 Rotinas logs     0   (warn)                                  │
│  🔧 Ajustes finos    0   (ok)                                    │
│  📓 Journal          pendente  (warn)                            │
│  📦 Blocos           0   (muted)                                 │
╰──────────────────────────────────────────────────────────────────╯
```

**Diferença vs Daily Report:** State é mais compacto, e o
**Período** (MANHA/TARDE/NOITE) é **calculado do relógio** (não
do dia). Em estado vazio de manhã, o budget é 180min (MANHA
budget); de tarde, 240min (TARDE); de noite, 0 (sem hardwork).

---

### SCR-007 Doctor — Estado de Erro

Quando o ambiente tem problemas (Python 3.9, sem rich, etc):

```text
╭───  DOCTOR - ISSUES  ─────────────────────────────────────────────╮
│  [red]FAIL[/red]  python         v3.9.0                          │
│  [red]FAIL[/red]  packages       rich=None, pydantic=None        │
│  [green]OK[/green]  state_dir      C:\Users\...\json (0 files)   │
│  [green]OK[/green]  datasets       active=production              │
│  [green]OK[/green]  constants      6 loaded                       │
│  [green]OK[/green]  console        captured=False                 │
│  [green]OK[/green]  files_sanity   0 files, 0 issues              │
╰──────────────────────────────────────────────────────────────────╯

[bold red]Issues:[/bold red]
  [red]*[/red] python: requires >= 3.10 (found 3.9.0)
  [red]*[/red] packages: missing rich, pydantic
```

**Comportamento:**
- Exit code: 1 quando há `FAIL` (Typer exit).
- Cada check tem `ok: bool` que decide a cor do ícone.
- Mensagens de detalhe aparecem em `[red]*[/red]` no fim.

---

### SCR-007 Doctor — Estado de Erro Crítico (state dir corrompido)

```text
╭───  DOCTOR - ISSUES  ─────────────────────────────────────────────╮
│  [green]OK[/green]  python         v3.14.0                        │
│  [green]OK[/green]  packages       typer=0.12.0, ...              │
│  [red]FAIL[/red]  state_dir      C:\Users\...\json (3 files)     │
│  ...                                                              │
╰──────────────────────────────────────────────────────────────────╯

Issues:
  [red]*[/red] state_dir: routines.json has UTF-8 BOM (should not)
  [red]*[/red] state_dir: journals.json has CRLF line endings
```

**Comportamento:**
- Cada `files_info` reporta o erro específico (BOM, CRLF, parse error).
- O painel mostra contagem de arquivos; o "Issues:" lista os
  problemas com nome do arquivo.

---

### SCR-008/009/010/011/013 (List) — Estado Vazio

Todas as telas de listagem (rotinas, blocos, journals, habits,
policy decisions) têm o mesmo padrão de estado vazio:

```text
Nenhuma rotina cadastrada. Use `routine create`.
```

**Mensagem:** Tom instrutivo, sugere o próximo comando. Cor: `yellow`
(warn — não é erro, é só vazio).

---

### SCR-012 / SCR-014 / SCR-015 (Form) — Estado de Erro (Pydantic)

Quando o usuário digita valor fora do range (ex: `quality=15`):

```text
╭────  SISTEMA FALHOU  ────────────────────────────────────────────╮
│  ❌ Erro de Execução                                              │
│                                                                  │
│  ValidationError: 1 validation error for SleepRecord             │
│  quality_score                                                    │
│    Input should be less than or equal to 10                      │
│    [type=less_than_equal, input_value=15, input_type=int]        │
│                                                                  │
│  [Contexto]  date=2026-06-08                                     │
│  [💡 Dica]  Use --quality entre 1 e 10.                          │
╰──────────────────────────────────────────────────────────────────╯
```

**Comportamento:**
- Typer validation (`min=1, max=10`) aborta **antes** de chamar
  Pydantic. O usuário vê:
  `Invalid value for '--quality': 15 is not in range 1<=x<=10.`
  sem o `error_panel` (mensagem direta do Typer).
- Se Typer **não** valida (ex: campo `notes` texto livre), aí
  Pydantic valida e o `error_panel` aparece.

**Decisão de UX:** preferir **validação Typer** (mensagem curta,
direta) sobre Pydantic validation (mensagem longa com locals) para
inputs de CLI. Pydantic é fallback para casos onde Typer não
consegue validar (ex: cross-field validation).

---

## Sem Permissão — casos raros

O `operational` é local-only, então "sem permissão" é raro.
Os casos típicos:

### State dir não existe

```text
╭────  SISTEMA FALHOU  ────────────────────────────────────────────╮
│  ❌ Erro de Execução                                              │
│  FileNotFoundError: state dir does not exist                     │
│  [Contexto]  TIME_TASKER_STATE_DIR=C:\Users\...\.time-tasker     │
│  [💡 Dica]  Crie o diretório ou ajuste TIME_TASKER_STATE_DIR.     │
╰──────────────────────────────────────────────────────────────────╯
```

**Comportamento:** O `doctor` mostra o state_dir como `exists=False`
na seção `state_dir`. O `_PersistentRepo.__init__` cria o diretório
**automaticamente** ao primeiro `upsert` (ver
`persistence/memory.py:50-80`), então esse erro só aparece se o
**caminho do env var** for inválido.

### JSON file corrompido

Quando `routines.json` tem JSON inválido (ex: edição manual
quebrada):

```text
╭────  SISTEMA FALHOU  ────────────────────────────────────────────╮
│  ❌ Erro de Execução                                              │
│  json.JSONDecodeError: Expecting ',' delimiter: line 42 column 3 │
│  [Contexto]  file=routines.json, size=1234 bytes                 │
│  [💡 Dica]  Restaure de backup ou delete o arquivo (vai recriar).  │
╰──────────────────────────────────────────────────────────────────╯
```

**Mitigação:** O doctor detecta esse caso em
`_check_state_dir` (parsea cada JSON). Se OK=false, o usuário é
avisado antes de tentar ler.

### File system read-only (Windows ACL, Linux chmod)

```text
╭────  SISTEMA FALHOU  ────────────────────────────────────────────╮
│  ❌ Erro de Execução                                              │
│  PermissionError: [Errno 13] Permission denied                    │
│  [Contexto]  file=C:\Users\...\.time-tasker\routines.json        │
│  [💡 Dica]  Verifique permissões: chmod 700 ~/.time-tasker        │
╰──────────────────────────────────────────────────────────────────╯
```

**Comportamento:** O `_PersistentRepo._save()` tenta abrir em
modo "w" e falha. O CLI mostra o `error_panel` com o path
completo, e o `doctor` mostra `state_dir.writable=False`.

---

## Resumo dos padrões de UX para estados

| Estado | Padrão visual | Mensagem | Cor |
|--------|---------------|----------|-----|
| Vazio | "—" / "0" / "não registrado" | "Nenhum(a) X. Use `Y`." | `muted` / `warn` |
| Loading | (não há) | (não há) | N/A |
| Com dados | Renderização normal | (sem mensagem) | (paleta padrão) |
| Erro de validação | `error_panel` | "Input should be..." | `crit` |
| Erro de I/O | `error_panel` | "FileNotFoundError..." | `crit` |
| Sem permissão | `error_panel` | "PermissionError..." | `crit` |
| Doctor FAIL | Painel + Issues list | Detalhe por check | `crit` |

---

## Onde ler mais

- **Detalhes dos componentes que renderizam cada estado** →
  [`../02-componentes/04-error-panel.md`](../02-componentes/04-error-panel.md)
- **Detalhes dos prompts que iniciam estados Form** →
  [`03-modais-e-abas.md`](03-modais-e-abas.md)
- **Wireframes completos de cada tela em estado "com dados"** →
  [`01-telas-inventario.md`](01-telas-inventario.md)
