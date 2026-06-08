# SCR-006 — Demo Dataset List

**Comando:** `operational demo dataset [name] [--json]`
**Arquivo renderizador:** N/A (output via `typer.echo`); usa `list_datasets()` / `resolve_dataset()` de `cli/dataset_selector.py`
**Arquivo de comando:** `src/operational/cli/commands/demo_cmd.py:181-235` (`dataset`)
**Tipo:** Output de catálogo (read-only); com argumento, vira "info de um dataset"
**Modo JSON:** Sim (`--json`)
**Dataset:** N/A (esta tela **lista** os datasets)

## Propósito

Mostrar quais **datasets pré-construídos** estão disponíveis (synthetic, golden, production), o caminho do CSV, e indicar quais existem no disco vs quais estão faltando. Com argumento, troca o dataset ativo (apenas emite a env var a ser setada — não muda estado). O usuário olha esta tela para responder: *"Quais datasets eu posso usar? Qual está ativo agora? Como troco?"*

## Usuário-alvo

O próprio usuário, especialmente em setup inicial ou ao trocar entre golden/synthetic para QA. Momento: depois de clonar o repo, ou antes de rodar `report daily`. Objetivo: confirmar o dataset ativo e copiar o comando para trocar.

## Entradas

- **Do home menu:** opção `9` → submenu → opção "Datasets" (varia conforme versão).
- **Comando direto (sem args):** `operational demo dataset` — lista todos + ativo.
- **Comando direto (com name):** `operational demo dataset golden` — info de um dataset específico.

## Saídas

- **Trocar de dataset (exporta a env var):** o próprio output indica `TIME_TASKER_DATASET=golden` na linha "To activate".
- **Importar o dataset escolhido:** `operational demo import-csv docs/golden.csv`.
- **Ver relatório:** `operational report weekly`.

## Argumentos e flags

| Flag / Arg | Tipo | Default | Comportamento se omitido | Exemplo |
|------------|------|---------|--------------------------|---------|
| `name` | `str` (positional) | `None` | Lista todos os datasets. | `golden` |
| `--json` | `bool` | `False` | Emite dict `{"active": "...", "datasets": [...]}` ou `{"dataset": "...", "env_var": "...", "path": "..."}`. | `--json` |

Quando `name` é passado, `dataset` chama `resolve_dataset(name)` (`cli/dataset_selector.py`). Quando omitido, chama `list_datasets()`. **Não há flag `--set`** — o comando não muda a env var (apenas imprime a instrução).

## Conteúdo principal

**Sem `name`** (`demo_cmd.py:196-222`):

```
Active dataset: production

  [OK]      production — Estado local (padrão, ~/.time-tasker/*.json)
             /home/user/.time-tasker
  [OK]      synthetic   — 30 dias simulados para QA de longo prazo
             /path/to/repo/docs/synthetic.csv
  [OK]      golden      — 7 dias canônicos (CURSO, HARDCORE, DESCANSO, LIVRE)
             /path/to/repo/docs/golden.csv
```

Linhas com `[MISSING]` indicam que o CSV não foi encontrado.

**Com `name=golden`** (`demo_cmd.py:223-235`):

```
Dataset: golden
  Path: /path/to/repo/docs/golden.csv
  To activate: TIME_TASKER_DATASET=golden operational home
```

> Nota: o `name` não ativa o dataset — apenas imprime o caminho e a env var. A ativação real é feita pelo shell antes de invocar o CLI (ou no mesmo comando encadeado, como no exemplo).

## Hierarquia visual

- **1º:** A linha "Active dataset: X" (qual está em uso).
- **2º:** Lista de datasets disponíveis (3 itens: production, synthetic, golden).
- **3º:** Caminho do CSV (para copiar/colar).

## Wireframe ASCII (3 datasets conhecidos)

```
$ operational demo dataset

Active dataset: production

  [OK]      production  — Estado local (padrão, ~/.time-tasker/*.json)
               C:\Users\mathe\.time-tasker
  [OK]      synthetic    — 30 dias simulados para QA de longo prazo
               C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\synthetic.csv
  [OK]      golden       — 7 dias canônicos (CURSO, HARDCORE, DESCANSO, LIVRE)
               C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\golden.csv
```

Com `--json`:

```json
{
  "active": "production",
  "datasets": [
    {
      "name": "production",
      "path": "C:\\Users\\mathe\\.time-tasker",
      "exists": true,
      "description": "Estado local (padrão, ~/.time-tasker/*.json)"
    },
    {
      "name": "synthetic",
      "path": "C:\\Users\\mathe\\code_space\\life-oss\\life\\life-ops\\operational\\docs\\synthetic.csv",
      "exists": true,
      "description": "30 dias simulados para QA de longo prazo"
    },
    {
      "name": "golden",
      "path": "C:\\Users\\mathe\\code_space\\life-oss\\life\\life-ops\\operational\\docs\\golden.csv",
      "exists": true,
      "description": "7 dias canônicos (CURSO, HARDCORE, DESCANSO, LIVRE)"
    }
  ]
}
```

Com `name=golden`:

```
$ operational demo dataset golden
Dataset: golden
  Path: C:\Users\mathe\code_space\life-oss\life\life-ops\operational\docs\golden.csv
  To activate: TIME_TASKER_DATASET=golden operational home
```

## Estados (5)

### Estado 1 — Vazio / `production` dataset sem CSV

- `[OK] production` aparece com path para o `state_dir` local (sempre existe).
- `[MISSING] synthetic` se `docs/synthetic.csv` não foi criado (raro em dev).
- `[MISSING] golden` idem.

### Estado 2 — Loading

- **Não aplicável** (síncrono, ~5 ms — só faz `Path.exists()` em 3 entradas).

### Estado 3 — Com dados (wireframe acima)

- 3 datasets listados. `[OK]` ou `[MISSING]` em cada. Caminho completo do CSV exibido.

### Estado 4 — Erro

- **`name=foo` (dataset inexistente):** `resolve_dataset("foo")` levanta `ValueError` ou `KeyError` — o erro sobe como traceback. Mitigação: implementar validação + `typer.BadParameter` em `demo_cmd.py:224`.
- **CSV corrompido:** esta tela **não lê** o CSV, só checa `Path.exists()`. Sem risco de parse error.

### Estado 5 — Dataset sintético (golden.csv)

- O golden é o "caso feliz" típico: `[OK] golden` com `docs/golden.csv` presente. O usuário pode rodar `TIME_TASKER_DATASET=golden operational home` e o seed do golden aparece em todos os relatórios.

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only.
- **Tem prompts?** NÃO.
- **Teclas de atalho?** `Ctrl+C` aborta.
- **Mouse?** Sem suporte.

## Comandos relacionados

- `operational demo import-csv docs/golden.csv` — importa o golden para o `state_dir`.
- `operational demo export-csv ./out.csv` — exporta o estado atual.
- `operational demo seed` — popula com 7 dias PAV (independente do CSV).
- `operational doctor doctor` — também checa `TIME_TASKER_DATASET` em `_check_datasets` (`doctor_cmd.py:103-131`).

## Riscos de usabilidade

1. **Comando não ativa o dataset** — apenas imprime a env var. Usuário que espera "trocar agora" fica confuso. Mitigação: implementar `--set` ou `demo dataset golden --activate`.
2. **Sem cor, sem painel** — output via `typer.echo` direto, sem `console.print`. Inconsistência visual com `state show` e `report daily`.
3. **`[OK]`/`[MISSING]` parece YAML/INI, não Rich** — pode parecer "amador" comparado às outras telas com bordas Unicode.
4. **Path do Windows com backslashes** pode quebrar scripts bash (`cat $path`). Mitigação: expor caminho POSIX ou flag `--path-posix`.
5. **Lista de datasets é hardcoded** em `list_datasets()` (`cli/dataset_selector.py`). Adicionar um dataset novo exige editar código.
6. **Não há `--help` no sub-comando** que explique o que `name` faz. Mitigação: melhorar docstring em `demo_cmd.py:186-191`.

## Métricas de sucesso

- **Tempo até identificar o dataset ativo**: meta < 2s (1ª linha).
- **Taxa de uso**: esperado < 5% (uso de setup/QA).
- **Erros de "dataset não existe"**: contagem de `name` inválido. Meta: 0 (usuário lê a lista primeiro).

## Onde aparece

- Home menu: opção `9` → submenu.
- Link direto: `operational demo dataset [name]`.
- Usado em setup/README para "como carregar o golden".

## Notas de implementação

- Entry point: `cli/commands/demo_cmd.py:181` (`dataset`).
- Implementação: `cli/dataset_selector.py:list_datasets()` e `cli/dataset_selector.py:resolve_dataset(name)`.
- Output: `typer.echo(...)` direto (sem `console.print`). Não respeita `is_captured()`.
- `TIME_TASKER_DATASET` env var: lida em `doctor_cmd.py:105` e em `seed.py` (na função de seed que escolhe CSV). **Não** lida em `get_day_snapshot` — o `state_dir` é o que importa, não o dataset.
- Largura do console: irrelevante (sem painel).
- Performance: O(1) — só 3 `Path.exists()` checks.
