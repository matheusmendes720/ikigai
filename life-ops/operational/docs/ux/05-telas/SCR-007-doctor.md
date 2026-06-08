# SCR-007 — Doctor

**Comando:** `operational doctor doctor [--json]`
**Arquivo renderizador:** N/A (output inline em `doctor_cmd.py:213-260`)
**Arquivo de comando:** `src/operational/cli/commands/doctor_cmd.py:191-260` (`doctor_cmd`)
**Tipo:** Output diagnóstico (read-only) com ícones ✓/✗
**Modo JSON:** Sim (`--json`)
**Dataset:** N/A (esta tela diagnostica o ambiente, não os dados)

## Propósito

Rodar **7 health checks** sobre o ambiente do `operational` CLI e listar ✓/✗ para cada um, mais um painel de "Issues" com detalhes. O usuário olha esta tela para responder: *"O CLI está saudável? Algum componente está quebrado? Qual é o caminho de configuração?"*. É o equivalente CLI de um "system check" / "self-test".

## Usuário-alvo

O próprio usuário, especialmente ao encontrar erros inexplicáveis (relatório vazio, `ImportError`, JSON corrompido). Momento: primeira vez rodando o CLI, ou após um upgrade de dependências. Objetivo: isolar a falha (Python? packages? state dir? constants? console? encoding?).

## Entradas

- **Do home menu:** opção `10` (ℹ️ Sistema) → submenu → "Doctor" (varia conforme versão do `_menu_system`).
- **Comando direto:** `operational doctor doctor` (note a duplicação: Typer sub-app `doctor` + comando `doctor`).
- **Comando direto com JSON:** `operational doctor doctor --json`.

## Saídas

- **Sair:** `Ctrl+C` ou retorno ao menu.
- **Aplicar correção manual** (esta tela **não** corrige — apenas reporta): ex: `chmod +r ~/.time-tasker/*.json`, `pip install -U typer rich pydantic`.

## Argumentos e flags

| Flag | Tipo | Default | Comportamento se omitido | Exemplo |
|------|------|---------|--------------------------|---------|
| `--json` | `bool` | `False` | Emite dict com `timestamp`, `checks` (7 sub-dicts) e `overall_ok` (bool). Use para integrar com `health-check.sh`. | `--json` |

`doctor doctor` **não aceita** argumentos posicionais.

## Conteúdo principal

Um único painel Rich com 7 linhas (`doctor_cmd.py:218-249`):

1. **`✓ python`** — Versão do Python (ex: `v3.14.0`). `ok=True` se `>= 3.10` (`_check_python` em `doctor_cmd.py:33-40`).
2. **`✓ packages`** — Versões instaladas de `typer`, `rich`, `pydantic` (ex: `typer=0.15.0, rich=14.0.0, pydantic=2.10.0`). `ok=True` se todos instalados (`_check_packages` em `doctor_cmd.py:43-56`).
3. **`✓ state_dir`** — Caminho do `state_dir` e contagem de arquivos JSON existentes (ex: `C:\Users\mathe\.time-tasker (14 files)`). `ok=True` se existe e é gravável (`_check_state_dir` em `doctor_cmd.py:59-100`).
4. **`✓ datasets`** — `active=production` (lê `TIME_TASKER_DATASET`). Sempre `ok=True` (informativo) (`_check_datasets` em `doctor_cmd.py:103-131`).
5. **`✓ constants`** — `6 loaded` (POMODORO_WORK_MIN, POMODORO_BREAK_MIN, etc.). `ok=True` se valores batem com `expected` (`_check_constants` em `doctor_cmd.py:134-155`).
6. **`✓ console`** — `captured=False, encoding=utf-8` (lê `is_captured()` e `sys.stdout.encoding`). Sempre `ok=True` (informativo) (`_check_console` em `doctor_cmd.py:158-166`).
7. **`✓ files_sanity`** — `14 files, 0 issues` (checa BOM UTF-8 e CRLF). `ok=True` se zero issues (`_check_files_sanity` em `doctor_cmd.py:169-188`).

Cabeçalho do painel: `DOCTOR - OK` (verde) ou `DOCTOR - ISSUES` (vermelho), dependendo de `all_ok` (`doctor_cmd.py:208-209, 216-217`).

Se houver issues, lista adicional após o painel:

```
Issues:
  * state_dir: path 'C:\Users\mathe\.time-tasker' does not exist
```

(`doctor_cmd.py:251-256`).

## Hierarquia visual

- **1º:** Cabeçalho `DOCTOR - OK` ou `DOCTOR - ISSUES` (verde/vermelho) — leitura instantânea.
- **2º:** Linhas com `✓` ou `✗` (verde/vermelho) — o 7 checks em < 3s.
- **3º:** Detalhes de cada check (versão, path, contagem) — drill-down textual.
- **4º:** Lista de Issues (se houver) — call-to-action.

## Wireframe ASCII (cenário OK — golden.csv instalado)

```
+==============================================================+
|  DOCTOR - OK                                                 |
+==============================================================+
|                                                              |
|  ✓ python       v3.14.0                                       |
|  ✓ packages     typer=0.15.0, rich=14.0.0, pydantic=2.10.0  |
|  ✓ state_dir    C:\Users\mathe\.time-tasker (14 files)        |
|  ✓ datasets     active=production                              |
|  ✓ constants    6 loaded                                       |
|  ✓ console      captured=False, encoding=utf-8                 |
|  ✓ files_sanity 14 files, 0 issues                              |
+==============================================================+
```

Cenário com **ISSUES** (state_dir sumiu + packages faltando):

```
+==============================================================+
|  DOCTOR - ISSUES                                             |
+==============================================================+
|                                                              |
|  ✓ python       v3.14.0                                       |
|  ✗ packages     pydantic=                                      |
|  ✗ state_dir    C:\Users\mathe\.time-tasker (0 files)         |
|  ✓ datasets     active=production                              |
|  ✗ constants    POMODORO_WORK_MIN=0 (expected 50)              |
|  ✓ console      captured=False, encoding=utf-8                 |
|  ✓ files_sanity 0 files, 0 issues                              |
+==============================================================+

Issues:
  * packages: missing typer, rich, or pydantic
  * state_dir: path does not exist or is not writable
  * constants: 1 constant(s) differ from expected
```

## Estados (5)

### Estado 1 — Vazio (não aplicável — sempre há algo para checar)

- O doctor sempre retorna 7 entradas. No mínimo, todas com `ok=False` (se tudo estiver quebrado).

### Estado 2 — Loading

- **Não aplicável** (síncrono, ~50 ms — 7 checks simples, 14 `Path.exists()` em `files_sanity`).

### Estado 3 — Com dados (wireframe acima)

- 7 linhas + cabeçalho. Verde/vermelho por check.

### Estado 4 — Erro

- **Erro interno em um check** (ex: `importlib.metadata` levanta `Exception`): o check captura e marca `ok=False`. Sem traceback para o usuário.
- **Permissão negada** em `state_dir`: `os.access` retorna `False` → `ok=False`, summary mostra `path does not exist or is not writable`.
- **JSON corrompido em um arquivo do state_dir**: o check individual (`_check_state_dir` em `doctor_cmd.py:77-91`) marca `parseable=False` e inclui o erro. Mas **não** marca `ok=False` no nível do check (apenas no detalhe).

### Estado 5 — Dataset sintético (golden.csv) — não impacta

- O doctor **não consulta** datasets — só checa se o CSV **existe** em disco (`_check_datasets` em `doctor_cmd.py:117-126`). Se o golden.csv existe, o check mostra `[OK] golden`. Se não, `[MISSING]`. Não lê o conteúdo.

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only.
- **Tem prompts?** NÃO.
- **Teclas de atalho?** `Ctrl+C` aborta.
- **Mouse?** Sem suporte.

## Comandos relacionados

- `operational demo show` — entity counts (sobrepõe em 80% ao que `state_dir` do doctor mostra).
- `operational demo import-csv` — recupera de CSV (útil se o state_dir corrompeu).
- `operational home` → opção `10` (ℹ️ Sistema) — onde esta tela é referenciada.

## Riscos de usabilidade

1. **Cabeçalho "DOCTOR - OK" pode ser mal-interpretado** como "o sistema está OK" mesmo se 5 dos 7 checks estão com `✗`. Mitigação: o `all_ok = all(c.get("ok", True) for c in results["checks"].values())` (`doctor_cmd.py:208`) garante que `OK` só aparece se **todos** os 7 estão OK — está correto.
2. **Painel sem `box=` customizado** — usa o default do `rich.panel.Panel` (que pode ser ASCII em terminais sem suporte Unicode). Inconsistência com outras telas que usam `box=SIMPLE_HEAD` ou `box=SIMPLE`.
3. **Não mostra a versão do CLI** (`__version__` em `__init__.py`) — o usuário pode esquecer qual versão está rodando. Mitigação: adicionar ao `✓ python` ou criar um check separado.
4. **Sem help de "como corrigir"** — a seção "Issues" lista o problema, mas não diz como. Ex: `constants: POMODORO_WORK_MIN=0` não diz "rode `pip install -e .` para resetar" (que é o que de fato consertaria). Mitigação: adicionar campo `hint` por check.
5. **`_check_state_dir` não trata o caso `path inacessível` (permissão)** separadamente de "não existe". Os dois viram `ok=False`, mas a mensagem é a mesma. Mitigação: distinguir `permission_denied` vs `not_found` no summary.
6. **`active=production` é o default hardcoded** em `doctor_cmd.py:105` — se a env var não está setada, sempre mostra "production", mesmo se o usuário pensa que está usando outro dataset.

## Métricas de sucesso

- **Tempo até identificar falha crítica**: meta < 5s (ler o cabeçalho + os ✗).
- **Taxa de execução por usuário**: esperado alto na primeira semana de uso (setup), baixo depois.
- **Falsos positivos** (check que falha mas CLI funciona): meta 0%. Hoje há o risco em `state_dir` (falso negativo se `writable=False` mas o CLI só lê).

## Onde aparece

- Home menu: opção `10` (ℹ️ Sistema) → submenu.
- Link direto: `operational doctor doctor`.
- Documentado em `docs/architecture/01-MVC-LAYERS.md` como "the canonical 'is it me or is it the env?' command".

## Notas de implementação

- Entry point: `cli/commands/doctor_cmd.py:191` (`doctor_cmd`).
- Note a duplicação `doctor doctor` — o sub-Typer `app = typer.Typer(...)` é registrado como `doctor` em `cli/app.py`, e o comando dentro dele também se chama `doctor`. O resultado: `operational doctor doctor`.
- 7 checks implementados em funções `_check_*` separadas (`doctor_cmd.py:33-188`).
- Render: `Panel(Table.grid(...))` em `doctor_cmd.py:245-249`. Usa `border_style` dinâmico (`green` se `all_ok`, `red` caso contrário).
- Issues detalhados: itera sobre `results["checks"]` e imprime os que têm `ok=False` (`doctor_cmd.py:251-256`).
- Largura do console: usa o `console` singleton de `operational.ui` (`doctor_cmd.py:28`), que respeita `is_captured()`.
- Performance: ~50 ms (7 checks + 14 `Path.exists()` + encoding detection).
